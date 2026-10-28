// Unit tests for hooks/core.ts — pure policy, fake transport.
// Run: node --test tests/core.test.mjs   (Node >= 23.6 strips types)
import test from 'node:test'
import assert from 'node:assert/strict'
import { WatchWakeCore, DeadlineCore, interpolate, canLocalWake } from '../hooks/core.ts'

const CHILD = 'claude-child-1'
const COND = [{ id: 'done', type: 'event_type', eventType: 'agent_end' }]

function fakeServer({ capable = true, existing = null } = {}) {
  const state = {
    capable,
    watch: existing, // { generation, label, firings: [], onFire? , status }
    calls: [],
    gen: 0,
    failNext: 0,
  }
  const callApi = async (method, path, body) => {
    state.calls.push({ method, path, body })
    if (state.failNext > 0) { state.failNext--; return { status: 503, json: { error: 'busy' } } }
    if (path === '/api/v1/capabilities') {
      return { status: 200, json: { features: state.capable ? { watchGenerationPreconditions: { generationField: 'generation', registerField: 'expectedGeneration', deleteBodyField: 'expectedGeneration' } } : {} } }
    }
    const m = path.match(/^\/api\/v1\/sessions\/([^/]+)\/watch(?:\?sinceIndex=(\d+))?$/)
    if (!m) return { status: 404, json: { code: 'NOT_FOUND' } }
    if (method === 'GET') {
      if (!state.watch) return { status: 404, json: { code: 'WATCH_NOT_FOUND' } }
      const since = Number(m[2] ?? 0)
      return { status: 200, json: { generation: state.watch.generation, label: state.watch.label, status: state.watch.status ?? 'active', onFire: state.watch.onFire, firingCount: state.watch.firings.length, firings: state.watch.firings.slice(since) } }
    }
    if (method === 'POST') {
      if (state.capable && 'expectedGeneration' in body) {
        const cur = state.watch?.generation ?? null
        if (body.expectedGeneration !== cur) return { status: 409, json: { code: 'WATCH_GENERATION_MISMATCH' } }
      }
      const replaced = Boolean(state.watch)
      state.watch = { generation: `g${++state.gen}`, label: body.label, firings: [], status: 'active' }
      return { status: 201, json: { generation: state.watch.generation, firingCount: 0, firings: [], replaced } }
    }
    if (method === 'DELETE') {
      if (!state.watch) return { status: 404, json: { code: 'WATCH_NOT_FOUND' } }
      if (body && body.expectedGeneration !== state.watch.generation) return { status: 409, json: { code: 'WATCH_GENERATION_MISMATCH' } }
      const generation = state.watch.generation
      state.watch = null
      return { status: 200, json: { success: true, generation } }
    }
    return { status: 405, json: {} }
  }
  const fire = (conditionId = 'done') => state.watch.firings.push({ conditionId, eventType: 'agent_end', firedAt: 1_700_000_000_000 })
  return { state, callApi, fire }
}

function harness(opts = {}) {
  const server = fakeServer(opts)
  const delivered = []
  let now = 1_000_000
  let deliverImpl = async (text) => { delivered.push(text) }
  const persisted = []
  const core = new WatchWakeCore({
    callApi: server.callApi,
    deliver: (text) => deliverImpl(text),
    now: () => now,
    persist: (snap) => persisted.push(structuredClone(snap)),
  })
  return {
    core, server, delivered, persisted,
    advance: (ms) => { now += ms },
    setDeliver: (fn) => { deliverImpl = fn },
  }
}

test('register refuses a session id that could change the API path (dot segments, separators)', async () => {
  const h = harness()
  for (const bad of ['..', '.', 'a/b', '../x', 'a\\b', '?x']) {
    await assert.rejects(h.core.register({ sessionId: bad, conditions: COND, message: 'x' }, {}), /session_id/)
  }
  assert.equal(h.server.state.calls?.length ?? 0, 0)
})

test('interpolate fills every placeholder', () => {
  const out = interpolate('{{sessionId}} {{conditionId}} {{eventType}} {{firingCount}} {{firedAt}}', { conditionId: 'done', eventType: 'agent_end', firedAt: 0 }, 's1', 3)
  assert.equal(out, 's1 done agent_end 3 1970-01-01T00:00:00.000Z')
})

test('register creates a pure-observer watch with a CAS precondition and never sets onFire', async () => {
  const h = harness()
  const reg = await h.core.register({ sessionId: CHILD, conditions: COND, message: 'wake {{sessionId}}' }, { selfSessionId: 'me' })
  assert.equal(reg.status, 'watching')
  assert.equal(reg.sinceIndex, 0)
  assert.equal(reg.generation, 'g1')
  const post = h.server.state.calls.find((c) => c.method === 'POST')
  assert.equal(post.body.expectedGeneration, null)
  assert.equal(post.body.onFire, undefined)
  assert.match(post.body.label, /^watch-wake:/)
  assert.equal(h.persisted.length > 0, true)
})

test('register refuses self-watch, empty conditions and empty message', async () => {
  const h = harness()
  await assert.rejects(h.core.register({ sessionId: 'claude-me', conditions: COND, message: 'x' }, { selfSessionId: 'me' }), /own session/)
  await assert.rejects(h.core.register({ sessionId: CHILD, conditions: [], message: 'x' }, {}), /condition/)
  await assert.rejects(h.core.register({ sessionId: CHILD, conditions: COND, message: ' ' }, {}), /message/)
})

test('register refuses to clobber a foreign or onFire watch unless replace is explicit', async () => {
  const h = harness({ existing: { generation: 'gX', label: 'someone-else', firings: [{}], onFire: { targetSessionId: 'p' } } })
  await assert.rejects(h.core.register({ sessionId: CHILD, conditions: COND, message: 'x' }, {}), /already has a watch/)
  const reg = await h.core.register({ sessionId: CHILD, conditions: COND, message: 'x', replace: true }, {})
  const post = h.server.state.calls.filter((c) => c.method === 'POST').at(-1)
  assert.equal(post.body.expectedGeneration, 'gX')
  assert.equal(reg.status, 'watching')
})

// ─── Refuse conditions that can never fire ─────────────────────────────────
// Live incident: a parent registered {"type":"goal_end"} (an event name used
// AS the type) / {"type":"text_match"}; the server accepted them, the wake
// never came. Validation is local, so nothing is sent to the server.

test('register refuses a bare event name used as the type, naming the correct shape', async () => {
  const h = harness()
  const err = await h.core.register({ sessionId: CHILD, conditions: [{ type: 'goal_end' }], message: 'x' }, {})
    .then(() => null, (e) => e)
  assert.ok(err, 'a bare goal_end type must be refused')
  assert.match(err.message, /\{"type":"event_type","eventType":"goal_end"\}/)
  assert.equal(h.server.state.calls.length, 0, 'refused locally, no API call')
})

test('register refuses an unknown condition type and lists the server-known ones', async () => {
  const h = harness()
  const err = await h.core.register({ sessionId: CHILD, conditions: [{ type: 'text_match', contains: 'x' }], message: 'x' }, {})
    .then(() => null, (e) => e)
  assert.ok(err, 'an unknown type must be refused')
  assert.match(err.message, /event_type/)
  assert.match(err.message, /deadline/)
})

test('register refuses event_type without a non-empty eventType', async () => {
  const h = harness()
  await assert.rejects(h.core.register({ sessionId: CHILD, conditions: [{ type: 'event_type' }], message: 'x' }, {}), /eventType/)
  await assert.rejects(h.core.register({ sessionId: CHILD, conditions: [{ type: 'event_type', eventType: '  ' }], message: 'x' }, {}), /eventType/)
})

test('register refuses a dotted dataMatch key (server match is shallow) with the reason', async () => {
  const h = harness()
  const err = await h.core.register({
    sessionId: CHILD,
    conditions: [{ type: 'event_type', eventType: 'goal_state', dataMatch: { 'interruption.autoContinued': true } }],
    message: 'x',
  }, {}).then(() => null, (e) => e)
  assert.ok(err, 'a dotted dataMatch key must be refused')
  assert.match(err.message, /shallow|top-level/)
  assert.equal(h.server.state.calls.length, 0)
})

test('register refuses a nested object dataMatch value (never shallow-matches)', async () => {
  const h = harness()
  const err = await h.core.register({
    sessionId: CHILD,
    conditions: [{ type: 'event_type', eventType: 'goal_state', dataMatch: { interruption: { autoContinued: true } } }],
    message: 'x',
  }, {}).then(() => null, (e) => e)
  assert.ok(err, 'a nested object dataMatch value must be refused')
  assert.match(err.message, /primitive/)
})

test('register still accepts the valid shapes: agent_end, goal_end with a primitive dataMatch, and deadline', async () => {
  const h = harness()
  const reg = await h.core.register({
    sessionId: CHILD,
    conditions: [
      { type: 'event_type', eventType: 'agent_end' },
      { type: 'event_type', eventType: 'goal_end', dataMatch: { objective: 'x' } },
      { type: 'deadline', afterSeconds: 600 },
    ],
    message: 'x',
  }, {})
  assert.equal(reg.status, 'watching')
  const post = h.server.state.calls.find((c) => c.method === 'POST')
  assert.equal(post.body.conditions.length, 3)
})

test('a firing after registration delivers exactly one wake and finishes the registration', async () => {
  const h = harness()
  const reg = await h.core.register({ sessionId: CHILD, conditions: COND, message: 'child {{sessionId}} {{conditionId}}' }, {})
  await h.core.tick(); await h.core.settled()
  assert.equal(h.delivered.length, 0, 'no firing yet, no wake')
  h.server.fire()
  h.advance(30_000)
  await h.core.tick(); await h.core.settled()
  assert.equal(h.delivered.length, 1)
  assert.match(h.delivered[0], /child claude-child-1 done/)
  const after = h.core.get(reg.id)
  assert.equal(after.wakesSent, 1)
  assert.equal(after.status, 'done')
  assert.equal(after.sinceIndex, 1)
  h.server.fire(); h.advance(30_000)
  await h.core.tick(); await h.core.settled()
  assert.equal(h.delivered.length, 1, 'done registration never wakes again')
})

test('polling respects each registration interval', async () => {
  const h = harness()
  await h.core.register({ sessionId: CHILD, conditions: COND, message: 'x', intervalSeconds: 60 }, {})
  const gets = () => h.server.state.calls.filter((c) => c.method === 'GET' && c.path.includes('sinceIndex')).length
  await h.core.tick(); await h.core.settled()
  const first = gets()
  h.advance(10_000); await h.core.tick(); await h.core.settled()
  assert.equal(gets(), first, 'not due yet')
  h.advance(60_000); await h.core.tick(); await h.core.settled()
  assert.equal(gets(), first + 1)
})

test('a failed delivery does not consume the budget and retries on the next poll', async () => {
  const h = harness()
  const reg = await h.core.register({ sessionId: CHILD, conditions: COND, message: 'x' }, {})
  h.server.fire()
  h.setDeliver(async () => { throw new Error('channel down') })
  h.advance(30_000); await h.core.tick(); await h.core.settled()
  assert.equal(h.core.get(reg.id).wakesSent, 0)
  assert.match(h.core.get(reg.id).lastError, /channel down/)
  assert.equal(h.core.get(reg.id).sinceIndex, 0, 'cursor not advanced past an undelivered firing')
  h.setDeliver(async (t) => { h.delivered.push(t) })
  h.advance(30_000); await h.core.tick(); await h.core.settled()
  assert.equal(h.delivered.length, 1)
  assert.equal(h.core.get(reg.id).status, 'done')
})

test('a pending delivery is never duplicated by later polls', async () => {
  const h = harness()
  await h.core.register({ sessionId: CHILD, conditions: COND, message: 'x', maxWakes: 3 }, {})
  let release
  h.setDeliver((t) => new Promise((resolve) => { release = () => { h.delivered.push(t); resolve() } }))
  h.server.fire(); h.advance(30_000); await h.core.tick()
  h.advance(30_000); await h.core.tick()
  release(); await h.core.settled()
  assert.equal(h.delivered.length, 1)
})

test('a vanished watch goes stale and delivers one bounded notice', async () => {
  const h = harness()
  const reg = await h.core.register({ sessionId: CHILD, conditions: COND, message: 'x' }, {})
  h.server.state.watch = null
  h.advance(30_000); await h.core.tick(); await h.core.settled()
  assert.equal(h.core.get(reg.id).status, 'stale')
  assert.equal(h.delivered.length, 1)
  assert.match(h.delivered[0], /stale/i)
  h.advance(30_000); await h.core.tick(); await h.core.settled()
  assert.equal(h.delivered.length, 1, 'stale registrations are not polled again')
})

test('a replaced watch (different generation) goes stale instead of being adopted', async () => {
  const h = harness()
  const reg = await h.core.register({ sessionId: CHILD, conditions: COND, message: 'x' }, {})
  h.server.state.watch.generation = 'foreign'
  h.advance(30_000); await h.core.tick(); await h.core.settled()
  assert.equal(h.core.get(reg.id).status, 'stale')
  assert.match(h.core.get(reg.id).lastError, /generation/)
})

test('repeated poll failures escalate to one notice but keep watching', async () => {
  const h = harness()
  const reg = await h.core.register({ sessionId: CHILD, conditions: COND, message: 'x', intervalSeconds: 5 }, {})
  h.server.state.failNext = 100
  for (let i = 0; i < 12; i++) { h.advance(5_000); await h.core.tick(); await h.core.settled() }
  assert.equal(h.core.get(reg.id).status, 'watching')
  assert.equal(h.delivered.length, 1)
  assert.match(h.delivered[0], /failing/i)
})

test('cancel sends the observed generation and reports confirmation', async () => {
  const h = harness()
  const reg = await h.core.register({ sessionId: CHILD, conditions: COND, message: 'x' }, {})
  const res = await h.core.cancel(reg.id)
  assert.equal(res.registration.status, 'cancelled')
  assert.equal(res.remote, 'deleted-confirmed')
  const del = h.server.state.calls.find((c) => c.method === 'DELETE')
  assert.deepEqual(del.body, { expectedGeneration: 'g1' })
})

test('cancel never deletes a replacement watch owned by someone else', async () => {
  const h = harness()
  const reg = await h.core.register({ sessionId: CHILD, conditions: COND, message: 'x' }, {})
  h.server.state.watch.generation = 'foreign'
  const res = await h.core.cancel(reg.id)
  assert.equal(res.remote, 'not-deleted-generation-mismatch')
  assert.ok(h.server.state.watch, 'foreign watch survives')
})

test('snapshot/restore resumes from the persisted cursor without re-registering', async () => {
  const h = harness()
  await h.core.register({ sessionId: CHILD, conditions: COND, message: 'x' }, {})
  const snap = h.core.snapshot()
  h.server.fire() // fires while the parent process is down
  const posts = h.server.state.calls.filter((c) => c.method === 'POST').length
  const delivered = []
  const core2 = new WatchWakeCore({ callApi: h.server.callApi, deliver: async (t) => { delivered.push(t) }, now: () => 2_000_000 })
  const summary = await core2.restore(snap)
  assert.deepEqual(summary, { resumed: 1, stale: 0 })
  await core2.tick(); await core2.settled()
  assert.equal(delivered.length, 1, 'firing recorded while down is consumed, not skipped')
  assert.equal(h.server.state.calls.filter((c) => c.method === 'POST').length, posts, 'restore never re-registers')
})

test('restore marks a registration stale when its watch was replaced meanwhile', async () => {
  const h = harness()
  await h.core.register({ sessionId: CHILD, conditions: COND, message: 'x' }, {})
  const snap = h.core.snapshot()
  h.server.state.watch.generation = 'other'
  const core2 = new WatchWakeCore({ callApi: h.server.callApi, deliver: async () => {}, now: () => 0 })
  assert.deepEqual(await core2.restore(snap), { resumed: 0, stale: 1 })
})

test('legacy server (no generation capability) registers without a precondition', async () => {
  const h = harness({ capable: false })
  const reg = await h.core.register({ sessionId: CHILD, conditions: COND, message: 'x' }, {})
  const post = h.server.state.calls.find((c) => c.method === 'POST')
  assert.equal('expectedGeneration' in post.body, false)
  assert.equal(reg.status, 'watching')
})

// ─── DeadlineCore ────────────────────────────────────────────────────────────

function deadlineHarness() {
  let now = 0
  const delivered = []
  let deliverImpl = async (t) => { delivered.push(t) }
  const core = new DeadlineCore({ now: () => now, deliver: (t) => deliverImpl(t), persist: () => {} })
  return { core, delivered, advance: (ms) => { now += ms }, setDeliver: (f) => { deliverImpl = f } }
}

test('deadline arms, stays silent before due, delivers once when due', async () => {
  const h = deadlineHarness()
  const d = h.core.arm({ delaySeconds: 60, message: 'reconcile', label: 'wave-1' })
  assert.equal(d.status, 'armed')
  await h.core.tick(); assert.equal(h.delivered.length, 0)
  h.advance(60_000); await h.core.tick(); await h.core.settled()
  assert.equal(h.delivered.length, 1)
  assert.match(h.delivered[0], /reconcile/)
  assert.equal(h.core.status().status, 'delivered')
  h.advance(60_000); await h.core.tick(); await h.core.settled()
  assert.equal(h.delivered.length, 1)
})

test('deadline cancel needs the exact current id; re-arm supersedes', async () => {
  const h = deadlineHarness()
  const a = h.core.arm({ delaySeconds: 60, message: 'a' })
  const b = h.core.arm({ delaySeconds: 60, message: 'b' })
  assert.throws(() => h.core.cancel(a.id), /not the current/)
  assert.equal(h.core.cancel(b.id).status, 'cancelled')
  h.advance(120_000); await h.core.tick(); await h.core.settled()
  assert.equal(h.delivered.length, 0)
})

test('deadline bounds delay and retries a failed delivery a bounded number of times', async () => {
  const h = deadlineHarness()
  assert.throws(() => h.core.arm({ delaySeconds: 86_401, message: 'x' }), /delay/)
  h.core.arm({ delaySeconds: 0, message: 'x' })
  h.setDeliver(async () => { throw new Error('down') })
  for (let i = 0; i < 6; i++) { h.advance(31_000); await h.core.tick(); await h.core.settled() }
  assert.equal(h.core.status().status, 'failed')
})

test('deadline restore delivers an overdue wait and keeps terminal ones terminal', async () => {
  const h = deadlineHarness()
  h.core.arm({ delaySeconds: 30, message: 'x' })
  const snap = h.core.snapshot()
  const delivered = []
  const core2 = new DeadlineCore({ now: () => 10_000_000, deliver: async (t) => { delivered.push(t) } })
  core2.restore(snap)
  await core2.tick(); await core2.settled()
  assert.equal(delivered.length, 1)
  const core3 = new DeadlineCore({ now: () => 10_000_000, deliver: async (t) => { delivered.push(t) } })
  core3.restore(core2.snapshot())
  await core3.tick(); await core3.settled()
  assert.equal(delivered.length, 1)
})

// ─── Outbox: busy gating, coalescing, cancel race ──────────────────────────

import { Outbox } from '../hooks/core.ts'

function outboxHarness(opts = {}) {
  const server = fakeServer(opts)
  const delivered = []
  let now = 1_000_000
  let busy = false
  const outbox = new Outbox({ deliver: async (t) => { delivered.push(t) }, isBusy: () => busy })
  const core = new WatchWakeCore({ callApi: server.callApi, deliver: async () => { throw new Error('unused') }, now: () => now, outbox })
  const deadline = new DeadlineCore({ now: () => now, deliver: async () => { throw new Error('unused') }, outbox })
  return { core, deadline, outbox, server, delivered, advance: (ms) => { now += ms }, setBusy: (b) => { busy = b } }
}

test('wakes found while the parent is busy are held, then coalesced into ONE prompt when idle', async () => {
  const h = outboxHarness()
  const a = await h.core.register({ sessionId: 'child-a', conditions: COND, message: 'A {{sessionId}}' }, {})
  // second child needs its own server watch: fake server keeps one watch, so use separate cores' ledgers via fire order
  h.server.fire()
  h.setBusy(true)
  h.advance(30_000); await h.core.tick(); await h.outbox.settled()
  assert.equal(h.delivered.length, 0, 'nothing delivered while busy')
  assert.ok(h.core.get(a.id).pendingSince, 'pending wake is visible on the registration')
  h.deadline.arm({ delaySeconds: 0, message: 'backstop' })
  await h.deadline.tick()
  h.setBusy(false)
  await h.outbox.flush(); await h.outbox.settled()
  assert.equal(h.delivered.length, 1, 'one combined prompt')
  assert.match(h.delivered[0], /2 wakes/)
  assert.match(h.delivered[0], /A child-a/)
  assert.match(h.delivered[0], /backstop/)
  assert.equal(h.core.get(a.id).status, 'done')
  assert.equal(h.core.get(a.id).pendingSince, undefined)
  assert.equal(h.deadline.status().status, 'delivered')
})

test('cancelling a registration drops its held wake (no late wake after cancel)', async () => {
  const h = outboxHarness()
  const reg = await h.core.register({ sessionId: CHILD, conditions: COND, message: 'late?' }, {})
  h.server.fire(); h.setBusy(true)
  h.advance(30_000); await h.core.tick()
  await h.core.cancel(reg.id)
  h.setBusy(false)
  await h.outbox.flush(); await h.outbox.settled()
  assert.equal(h.delivered.length, 0)
  assert.equal(h.core.get(reg.id).status, 'cancelled')
})

test('max_wakes > 1 sends once:false; an explicit once:true with max_wakes > 1 is refused', async () => {
  const h = harness()
  await h.core.register({ sessionId: CHILD, conditions: [{ type: 'event_type', eventType: 'agent_end' }], message: 'x', maxWakes: 3 }, {})
  const post = h.server.state.calls.find((c) => c.method === 'POST')
  assert.equal(post.body.conditions[0].once, false)
  await assert.rejects(
    h.core.register({ sessionId: 'c2', conditions: [{ type: 'event_type', eventType: 'agent_end', once: true }], message: 'x', maxWakes: 2 }, {}),
    /once/,
  )
})

test('max_wakes > 1 leaves a deadline condition one-shot (the server refuses once:false on deadline)', async () => {
  const h = harness()
  await h.core.register({ sessionId: CHILD, conditions: [{ id: 'done', type: 'event_type', eventType: 'agent_end' }, { id: 'bs', type: 'deadline', afterSeconds: 600 }], message: 'x', maxWakes: 3 }, {})
  const post = h.server.state.calls.find((c) => c.method === 'POST')
  assert.equal(post.body.conditions[0].once, false)
  assert.notEqual(post.body.conditions[1].once, false)
})

test('fireIfSettled is passed through only when the server advertises it', async () => {
  const h = harness()
  const reg = await h.core.register({ sessionId: CHILD, conditions: COND, message: 'x', fireIfSettled: true }, {})
  const post = h.server.state.calls.find((c) => c.method === 'POST')
  assert.equal('fireIfSettled' in post.body, false, 'fake server lacks features.watchFireIfSettled')
  assert.match(reg.warning ?? '', /fireIfSettled/)
})

test('deadline arm reports the id it replaced', () => {
  const h = deadlineHarness()
  const a = h.core.arm({ delaySeconds: 60, message: 'a' })
  const b = h.core.arm({ delaySeconds: 60, message: 'b' })
  assert.equal(b.replacedId, a.id)
})

test('canLocalWake: interactive CLI and Remote Control bridge sessions can be woken; -p/SDK cannot', () => {
  assert.equal(canLocalWake({ interactive: true }), true)
  assert.equal(canLocalWake({ interactive: false, environmentKind: 'bridge' }), true)
  assert.equal(canLocalWake({ interactive: false }), false)
  assert.equal(canLocalWake({ interactive: false, environmentKind: '' }), false)
  assert.equal(canLocalWake({ interactive: false, environmentKind: 'something-else' }), false)
})
