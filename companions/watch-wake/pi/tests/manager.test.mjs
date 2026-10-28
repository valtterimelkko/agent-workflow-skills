import assert from 'node:assert/strict';
import { describe, it } from 'node:test';
import { WatchWakeManager } from '../manager.ts';

function fakeApi(routes = []) {
  const calls = [];
  const stripQuery = (p) => p.split('?')[0];
  const lookup = (method, path) =>
    routes.find((r) => r.method === method && r.path === stripQuery(path));
  return {
    calls,
    async callApi(method, path, body) {
      calls.push({ method, path, body });
      const route = lookup(method, path);
      if (!route) return { status: 404, json: { error: 'no route' } };
      if (route.impl) return route.impl({ method, path, body });
      return { status: route.status ?? 200, json: typeof route.json === 'function' ? route.json() : route.json };
    },
  };
}

function makeManager(routes = [], wakeResult = true) {
  const api = fakeApi(routes);
  const wakes = [];
  const manager = new WatchWakeManager({
    callApi: api.callApi,
    sendWake: (text) => { wakes.push(text); return wakeResult; },
    now: () => 1_787_000_000_000,
  });
  return { manager, api, wakes };
}

const conditions = [{ id: 'done', type: 'event_type', eventType: 'agent_end' }];

describe('WatchWakeManager — register (watch the child, wake this host)', () => {
  it('refuses a session id that could change the API path (dot segments, separators) before any API call', async () => {
    const { manager, api } = makeManager([]);
    for (const bad of ['..', '.', 'a/b', '../x', 'a\\b', '?x']) {
      await assert.rejects(manager.register({ sessionId: bad, conditions, message: 'x' }), /sessionId/);
    }
    assert.equal(api.calls.length, 0);
  });

  it('registers a server-side watch without onFire and baselines from firingCount', async () => {
    const { manager, api } = makeManager([
      { method: 'POST', path: '/api/v1/sessions/child-1/watch', status: 201, json: { watchId: 'watch-child-1', firingCount: 2, status: 'active' } },
    ]);
    const reg = await manager.register({
      sessionId: 'child-1',
      conditions,
      message: 'Child {{sessionId}} fired {{conditionId}} — continue.',
    });
    assert.equal(reg.status, 'watching');
    assert.equal(api.calls[0].body.onFire, undefined, 'local wake must not request the server-side onFire action');
    assert.equal(api.calls[0].body.pin, true);
    assert.equal(api.calls[0].body.label, 'watch-wake:child-1');
    assert.equal(manager.get(reg.id).sinceIndex, 2, 'baseline must skip firings that predate registration');
  });

  it('refuses a bare event name used as the type, naming the correct shape', async () => {
    const { manager, api } = makeManager();
    const err = await manager.register({ sessionId: 'child-1', conditions: [{ type: 'goal_end' }], message: 'w' })
      .then(() => null, (e) => e);
    assert.ok(err, 'a bare goal_end type must be refused');
    assert.match(err.message, /\{"type":"event_type","eventType":"goal_end"\}/);
    assert.equal(api.calls.length, 0, 'refused locally, no API call');
  });

  it('refuses an unknown condition type and lists the server-known ones', async () => {
    const { manager } = makeManager();
    const err = await manager.register({ sessionId: 'child-1', conditions: [{ type: 'text_match' }], message: 'w' })
      .then(() => null, (e) => e);
    assert.ok(err, 'an unknown type must be refused');
    assert.match(err.message, /event_type/);
    assert.match(err.message, /deadline/);
  });

  it('refuses event_type without a non-empty eventType', async () => {
    const { manager } = makeManager();
    await assert.rejects(manager.register({ sessionId: 'child-1', conditions: [{ type: 'event_type' }], message: 'w' }), /eventType/);
    await assert.rejects(manager.register({ sessionId: 'child-1', conditions: [{ type: 'event_type', eventType: ' ' }], message: 'w' }), /eventType/);
  });

  it('refuses a dotted dataMatch key (server match is shallow) with the reason', async () => {
    const { manager, api } = makeManager();
    const err = await manager.register({
      sessionId: 'child-1',
      conditions: [{ type: 'event_type', eventType: 'goal_state', dataMatch: { 'interruption.autoContinued': true } }],
      message: 'w',
    }).then(() => null, (e) => e);
    assert.ok(err, 'a dotted dataMatch key must be refused');
    assert.match(err.message, /shallow|top-level/);
    assert.equal(api.calls.length, 0);
  });

  it('refuses a nested object dataMatch value (never shallow-matches)', async () => {
    const { manager } = makeManager();
    const err = await manager.register({
      sessionId: 'child-1',
      conditions: [{ type: 'event_type', eventType: 'goal_state', dataMatch: { interruption: { autoContinued: true } } }],
      message: 'w',
    }).then(() => null, (e) => e);
    assert.ok(err, 'a nested object dataMatch value must be refused');
    assert.match(err.message, /primitive/);
  });

  it('still accepts the valid shapes: agent_end, goal_end with a primitive dataMatch, and deadline', async () => {
    const { manager, api } = makeManager([
      { method: 'POST', path: '/api/v1/sessions/child-1/watch', status: 201, json: { firingCount: 0 } },
    ]);
    const reg = await manager.register({
      sessionId: 'child-1',
      conditions: [
        { type: 'event_type', eventType: 'agent_end' },
        { type: 'event_type', eventType: 'goal_end', dataMatch: { objective: 'x' } },
        { type: 'deadline', afterSeconds: 600 },
      ],
      message: 'w',
    });
    assert.equal(reg.status, 'watching');
    assert.equal(api.calls.at(-1).body.conditions.length, 3);
  });

  it('sends exactly one interpolated wake when new firings appear', async () => {
    let firingCount = 0;
    const { manager, wakes } = makeManager([
      { method: 'POST', path: '/api/v1/sessions/child-1/watch', status: 201, json: { firingCount: 0 } },
      { method: 'GET', path: '/api/v1/sessions/child-1/watch', json: () => ({ firingCount, firings: firingCount > 0 ? [{ conditionId: 'done', eventType: 'agent_end', firedAt: 123, evidence: 'event agent_end' }] : [] }) },
    ]);
    const reg = await manager.register({ sessionId: 'child-1', conditions, message: 'WAKE {{sessionId}} {{conditionId}} {{eventType}}' });

    await manager.pollOnce(reg.id); // no firings yet
    assert.equal(wakes.length, 0);

    firingCount = 1;
    await manager.pollOnce(reg.id);
    assert.equal(wakes.length, 1);
    assert.match(wakes[0], /WAKE child-1 done agent_end/);
    assert.equal(manager.get(reg.id).wakesSent, 1);
    assert.equal(manager.get(reg.id).status, 'done', 'default maxWakes=1: one wake then stop');

    await manager.pollOnce(reg.id); // poll after done is a no-op
    assert.equal(wakes.length, 1);
  });

  it('advances sinceIndex so old firings never re-wake', async () => {
    let firingCount = 1;
    const { manager, wakes } = makeManager([
      { method: 'POST', path: '/api/v1/sessions/child-1/watch', status: 201, json: { firingCount: 0 } },
      { method: 'GET', path: '/api/v1/sessions/child-1/watch', json: () => ({ firingCount, firings: [{ conditionId: 'done', eventType: 'agent_end', firedAt: 1 }] }) },
    ]);
    const reg = await manager.register({ sessionId: 'child-1', conditions, message: 'W' });
    await manager.pollOnce(reg.id); // wakes on the 1 firing
    await manager.pollOnce(reg.id); // same firingCount → nothing new
    assert.equal(wakes.length, 1);
    assert.equal(manager.get(reg.id).sinceIndex, 1);
  });

  it('keeps maxWakes budget across polls and retries a failed delivery', async () => {
    let firingCount = 1;
    let wakeFails = true;
    const api = fakeApi([
      { method: 'POST', path: '/api/v1/sessions/child-1/watch', status: 201, json: { firingCount: 0 } },
      { method: 'GET', path: '/api/v1/sessions/child-1/watch', impl: ({ path }) => {
        const sinceIndex = Number(new URL(`http://local${path}`).searchParams.get('sinceIndex') ?? 0);
        return {
          status: 200,
          json: {
            firingCount,
            firings: sinceIndex < firingCount ? [{ conditionId: 'done', eventType: 'agent_end', firedAt: 1 }] : [],
          },
        };
      } },
    ]);
    const wakes = [];
    const manager = new WatchWakeManager({
      callApi: api.callApi,
      sendWake: (text) => { wakes.push(text); return !wakeFails; },
      now: () => 1,
    });
    const reg = await manager.register({ sessionId: 'child-1', conditions, message: 'W', maxWakes: 2 });
    await manager.pollOnce(reg.id); // delivery fails
    assert.equal(manager.get(reg.id).wakesSent, 0, 'a failed delivery must not consume the wake budget');
    assert.equal(manager.get(reg.id).sinceIndex, 0, 'a failed delivery must not consume the firing cursor');
    assert.equal(manager.get(reg.id).status, 'watching');
    wakeFails = false;
    await manager.pollOnce(reg.id); // same firing, delivery succeeds
    assert.equal(manager.get(reg.id).wakesSent, 1);
    assert.equal(manager.get(reg.id).status, 'watching', 'maxWakes=2 leaves budget');
  });

  it('marks the registration stale when the watch disappears (server restart)', async () => {
    const { manager } = makeManager([
      { method: 'POST', path: '/api/v1/sessions/child-1/watch', status: 201, json: { firingCount: 0 } },
      { method: 'GET', path: '/api/v1/sessions/child-1/watch', status: 404, json: { code: 'WATCH_NOT_FOUND' } },
    ]);
    const reg = await manager.register({ sessionId: 'child-1', conditions, message: 'W' });
    await manager.pollOnce(reg.id);
    assert.equal(manager.get(reg.id).status, 'stale');
    const stale = await manager.pollOnce(reg.id);
    assert.equal(stale.status, 'stale', 'polling a stale registration is a no-op');
  });

  it('marks a restored registration stale when the server reloads its watch detached', async () => {
    const { manager } = makeManager([
      { method: 'GET', path: '/api/v1/sessions/child-1/watch', status: 200, json: { status: 'detached', firingCount: 0, firings: [] } },
    ]);
    const report = await manager.reconcile([{ sessionId: 'child-1', message: 'W', sinceIndex: 0, wakesSent: 0 }]);
    assert.equal(report.attached, 1, 'the detached ledger remains readable and can be attached without replacing it');
    const reg = manager.list()[0];
    await manager.pollOnce(reg.id);
    assert.equal(manager.get(reg.id).status, 'stale');
    assert.match(manager.get(reg.id).lastError, /WATCH_DETACHED/);
  });
});

describe('WatchWakeManager — attach, cancel, persistence', () => {
  it('attaches to an existing watch without re-registering (no POST, no ledger reset)', async () => {
    const { manager, api } = makeManager([
      { method: 'GET', path: '/api/v1/sessions/child-1/watch', json: { firingCount: 5, status: 'active', watchId: 'watch-child-1' } },
    ]);
    const reg = await manager.attach({ sessionId: 'child-1', message: 'W' });
    assert.equal(reg.status, 'watching');
    assert.equal(manager.get(reg.id).sinceIndex, 5);
    assert.ok(api.calls.every((c) => c.method === 'GET'), 'attach must never POST (a re-register would wipe the ledger)');
  });

  it('attach fails cleanly when no watch exists', async () => {
    const { manager } = makeManager([
      { method: 'GET', path: '/api/v1/sessions/child-1/watch', status: 404, json: { code: 'WATCH_NOT_FOUND' } },
    ]);
    await assert.rejects(() => manager.attach({ sessionId: 'child-1', message: 'W' }), /no watch/i);
  });

  it('cancels: deletes the watch and stops waking', async () => {
    let firingCount = 1;
    const { manager, wakes, api } = makeManager([
      { method: 'POST', path: '/api/v1/sessions/child-1/watch', status: 201, json: { firingCount: 0 } },
      { method: 'GET', path: '/api/v1/sessions/child-1/watch', json: () => ({ firingCount, firings: [{ conditionId: 'done', eventType: 'agent_end', firedAt: 1 }] }) },
      { method: 'DELETE', path: '/api/v1/sessions/child-1/watch', status: 200, json: { success: true } },
    ]);
    const reg = await manager.register({ sessionId: 'child-1', conditions, message: 'W' });
    await manager.cancel(reg.id);
    assert.ok(api.calls.some((c) => c.method === 'DELETE'));
    assert.equal(manager.get(reg.id).status, 'cancelled');
    await manager.pollOnce(reg.id);
    assert.equal(wakes.length, 0, 'a cancelled registration must not wake');
  });

  it('persists progress and reconciles from the last consumed index so restart-gap firings wake', async () => {
    const { manager } = makeManager([
      { method: 'POST', path: '/api/v1/sessions/child-1/watch', status: 201, json: { firingCount: 0 } },
    ]);
    const reg = await manager.register({ sessionId: 'child-1', conditions, message: 'W {{conditionId}}', label: 'l1' });
    const entries = manager.toEntries();
    assert.ok(Array.isArray(entries) && entries.length === 1);
    assert.equal(entries[0].sessionId, 'child-1');
    assert.equal(entries[0].sinceIndex, 0);
    assert.equal(entries[0].wakesSent, 0);

    // Fresh manager restores the persisted cursor, then consumes firings that
    // accumulated while this host process was down.
    const restored = makeManager([
      { method: 'GET', path: '/api/v1/sessions/child-1/watch', json: {
        firingCount: 3,
        firings: [{ conditionId: 'done', eventType: 'agent_end', firedAt: 3 }],
      } },
    ]);
    const report = await restored.manager.reconcile(entries);
    assert.equal(report.attached, 1);
    assert.equal(restored.manager.list()[0].sinceIndex, 0, 'restored cursor must not skip restart-gap firings');
    await restored.manager.pollOnce(restored.manager.list()[0].id);
    assert.equal(restored.wakes.length, 1);
    assert.equal(restored.manager.list()[0].sinceIndex, 3);
    const bad = makeManager([
      { method: 'GET', path: '/api/v1/sessions/child-1/watch', status: 404, json: { code: 'WATCH_NOT_FOUND' } },
    ]);
    const report2 = await bad.manager.reconcile(entries);
    assert.equal(report2.stale, 1);
    void manager; void reg;
  });
});
