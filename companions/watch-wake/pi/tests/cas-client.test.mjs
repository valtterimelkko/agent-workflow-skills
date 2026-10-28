import assert from 'node:assert/strict';
import { test } from 'node:test';
import { WatchWakeManager, registrationsFingerprint } from '../manager.ts';
const args = { sessionId: 'child', sourceSessionId: 'parent-session', conditions: [{ type: 'event_type', eventType: 'goal_end' }], message: 'reconcile' };
function fixture() {
  const calls = [], wakes = [];
  let record, sequence = 0, supported = true, ack = undefined;
  const manager = new WatchWakeManager({
    supportsGenerationPreconditions: async () => supported,
    sendWake: text => { wakes.push(text); return true; },
    callApi: async (method, route, body) => {
      calls.push({ method, route, body });
      if (method === 'GET') return record ? { status: 200, json: { ...record } } : { status: 404 };
      if (method === 'POST') {
        if (Object.hasOwn(body, 'expectedGeneration') && body.expectedGeneration !== (record?.generation ?? null)) return { status: 409, json: { code: 'WATCH_GENERATION_MISMATCH' } };
        record = { watchId: 'watch-child', generation: `server-${++sequence}`, createdAt: 'same-timestamp', status: 'active', firingCount: 0, firings: [], sourceSessionId: body.sourceSessionId };
        return { status: 201, json: { ...record } };
      }
      if (method === 'DELETE') {
        if (body?.expectedGeneration && body.expectedGeneration !== record?.generation) return { status: 409, json: { code: 'WATCH_GENERATION_MISMATCH', currentGeneration: record?.generation ?? null } };
        const generation = record?.generation; record = undefined;
        return { status: 200, json: ack ?? { success: true, generation } };
      }
      throw new Error('unexpected call');
    },
  });
  return { manager, calls, wakes, get record() { return record; }, set record(value) { record = value; }, set supported(value) { supported = value; }, set ack(value) { ack = value; } };
}

test('a fresh server generation consumes firings that arrive before registration acknowledgement', async () => {
  let installed = false; const wakes = [], gets = [];
  const record = { generation: 'fresh-generation', sourceSessionId: 'parent-session', createdAt: 'now', status: 'active', firingCount: 1, firings: [{ conditionId: 'done', eventType: 'goal_end', firedAt: 1 }] };
  const manager = new WatchWakeManager({
    supportsGenerationPreconditions: async () => true,
    sendWake: text => { wakes.push(text); return true; },
    callApi: async (method, route) => {
      if (method === 'POST') { installed = true; return { status: 201, json: record }; }
      if (!installed) return { status: 404 };
      const index = Number(new URL(route, 'http://fixture').searchParams.get('sinceIndex') ?? 0);
      gets.push(index); return { status: 200, json: { ...record, firings: record.firings.slice(index) } };
    },
  });
  const registration = await manager.register(args);
  await manager.pollOnce(registration.id);
  assert.equal(wakes.length, 1, 'a new-generation event before POST response must not be baselined away');
  assert.deepEqual(gets, [0]);
});

test('CAS registration creates only if absent, replaces observed generation and persists independent identities', async () => {
  const f = fixture();
  const first = await f.manager.register(args);
  assert.equal(f.calls.find(c => c.method === 'POST').body.expectedGeneration, null);
  assert.equal(first.serverGeneration, 'server-1');
  assert.notEqual(first.generation, first.serverGeneration);
  const second = await f.manager.register(args);
  assert.equal(f.calls.filter(c => c.method === 'POST').at(-1).body.expectedGeneration, 'server-1');
  assert.equal(second.serverGeneration, 'server-2');
  const persisted = f.manager.toEntries();
  assert.equal(persisted[0].serverGeneration, 'server-2');
  assert.notEqual(registrationsFingerprint(persisted), registrationsFingerprint([{ ...persisted[0], serverGeneration: 'other' }]));
});

test('CAS refuses known foreign/external replacement rather than overwriting or delivering its firings', async () => {
  const f = fixture();
  const local = await f.manager.register(args);
  f.record = { ...f.record, generation: 'external', sourceSessionId: 'foreign', firingCount: 1, firings: [{ eventType: 'goal_end' }] };
  const before = f.calls.filter(c => c.method === 'POST').length;
  await assert.rejects(f.manager.register(args), /replaced|ownership|foreign/i);
  assert.equal(f.calls.filter(c => c.method === 'POST').length, before);
  const polled = await f.manager.pollOnce(local.id);
  assert.equal(polled.status, 'stale');
  assert.equal(polled.remoteDeleteAllowed, false);
  assert.ok(f.wakes.every(text => text !== 'reconcile'));
  await f.manager.cancel(local.id);
  assert.equal(f.calls.filter(c => c.method === 'DELETE').length, 0);
});

test('cancel sends exact generation and only matching acknowledgement counts as generation-confirmed', async () => {
  const f = fixture();
  const local = await f.manager.register(args);
  const result = await f.manager.cancel(local.id);
  assert.deepEqual(f.calls.find(c => c.method === 'DELETE').body, { expectedGeneration: 'server-1' });
  assert.equal(result.remoteDeleteAcknowledged, true);
  assert.equal(result.remoteDeleteGenerationConfirmed, true);
  assert.equal(f.manager.toEntries()[0].remoteDeleteGenerationConfirmed, true);
  await f.manager.cancel(local.id);
  assert.equal(f.calls.filter(c => c.method === 'DELETE').length, 1);
});

test('missing or different generation in delete acknowledgement is explicit ambiguity, never confirmed', async () => {
  for (const ack of [{ success: true }, { success: true, generation: 'wrong' }]) {
    const f = fixture(); f.ack = ack;
    const local = await f.manager.register(args);
    const result = await f.manager.cancel(local.id);
    assert.equal(result.remoteDeleteAcknowledged, false);
    assert.equal(result.remoteDeleteGenerationConfirmed, false);
    assert.equal(result.remoteCleanupPending, true);
    assert.match(result.lastError, /generation|acknowledge/i);
  }
});

test('a CAS conflict consumes stale delete authority; retry cannot delete the replacement', async () => {
  const f = fixture(); const local = await f.manager.register(args);
  f.record = { ...f.record, generation: 'new-external' };
  const result = await f.manager.cancel(local.id);
  assert.equal(result.remoteDeleteAllowed, false);
  assert.equal(result.remoteCleanupPending, false);
  assert.equal(result.remoteDeleteAcknowledged, false);
  assert.equal(f.record.generation, 'new-external');
  await f.manager.cancel(local.id);
  assert.equal(f.calls.filter(c => c.method === 'DELETE').length, 1);
});

test('a known CAS registration refuses capability downgrade, while legacy requests remain unconditional and labelled unconfirmed', async () => {
  const f = fixture(); const local = await f.manager.register(args);
  f.supported = false;
  const result = await f.manager.cancel(local.id);
  assert.equal(f.calls.filter(c => c.method === 'DELETE').length, 0);
  assert.equal(result.remoteCleanupPending, true);
  assert.match(result.lastError, /capabilit|precondition|CAS/i);
  const legacy = fixture(); legacy.supported = false;
  const old = await legacy.manager.register(args);
  assert.equal(Object.hasOwn(legacy.calls.find(c => c.method === 'POST').body, 'expectedGeneration'), false);
  // Legacy fixture happens to return a generation, but support was NOT advertised.
  assert.equal(old.serverGeneration, undefined);
  const cancelled = await legacy.manager.cancel(old.id);
  assert.equal(cancelled.remoteDeleteAcknowledged, true);
  assert.equal(cancelled.remoteDeleteGenerationConfirmed, false);
});

test('restore rejects a different server generation even with identical timestamp and source session', async () => {
  const f = fixture(); const local = await f.manager.register(args);
  const persisted = f.manager.toEntries();
  f.record = { ...f.record, generation: 'external' };
  await assert.rejects(f.manager.attach({ ...persisted[0], expectedOwnerSessionId: 'parent-session' }), /generation|replaced/i);
  assert.equal(f.manager.get(local.id).serverGeneration, 'server-1');
});
