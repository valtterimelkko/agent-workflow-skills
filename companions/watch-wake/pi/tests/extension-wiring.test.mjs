import assert from 'node:assert/strict';
import fs from 'node:fs';
import { describe, it } from 'node:test';
import { WatchWakeManager } from '../manager.ts';

/**
 * index.ts wiring is verified statically: its runtime imports (`typebox`, the
 * harness package) resolve only inside a real harness, so the file is read as
 * text, plus manager invariants that the wiring relies on.
 */

const source = fs.readFileSync(new URL('../index.ts', import.meta.url), 'utf8');

describe('watch-wake extension wiring (static)', () => {
  it('default-exports a factory', () => {
    assert.match(source, /export default function \(pi: ExtensionAPI\)/);
  });

  it('steers a wake into a busy host without triggerTurn', () => {
    assert.match(source, /hostContext\?\.isIdle\(\)/);
    assert.match(source, /sendUserMessage\(text, \{ deliverAs: "steer" \}\)/);
  });

  it('keeps followUp + triggerTurn delivery for an idle host', () => {
    assert.match(source, /sendUserMessage\(text, \{ deliverAs: "followUp", triggerTurn: true \}\)/);
  });

  it('falls back once to followUp when steer races the turn boundary and records it', () => {
    assert.match(source, /catch[^]*sendUserMessage\(text, \{ deliverAs: "followUp", triggerTurn: true \}\)/);
    assert.match(source, /sendUserMessage\(text, \{ deliverAs: "followUp", triggerTurn: true \}\);\s*\} catch \{\s*return false;\s*\}\s*try \{\s*pi\.appendEntry\("watch-wake-delivery", \{ delivery: "followUp-fallback"/);
  });

  it('never registers a server-side onFire action (local wake must not double-wake)', () => {
    assert.ok(!/onFire\s*:/.test(source), 'index.ts must not set an onFire property anywhere');
  });

  it('registers the three tools', () => {
    for (const tool of ['watch_wake_register', 'watch_wake_list', 'watch_wake_cancel']) {
      assert.ok(source.includes(`name: "${tool}"`), `missing tool ${tool}`);
    }
  });

  it('persists registrations via appendEntry and restores via session_start reconcile', () => {
    assert.match(source, /appendEntry\(ENTRY_TYPE/);
    assert.match(source, /pi\.on\("session_start"/);
    assert.match(source, /manager\.reconcile/);
  });

  it('stops the timer and drops stale host refs on every session shutdown/replacement', () => {
    assert.match(source, /pi\.on\("session_shutdown", async \(\) =>/);
    assert.match(source, /if \(pollTimer\) clearInterval\(pollTimer\)/);
    assert.ok(!/event\.reason === "quit" \|\| event\.reason === "reload"/.test(source), 'new/resume/fork must not retain the old factory timer');
  });

  it('reads socket/token from env-overridable standard paths (no secrets in code)', () => {
    assert.match(source, /PI_WEB_UI_WATCH_WAKE_SOCKET/);
    assert.match(source, /PI_WEB_UI_WATCH_WAKE_TOKEN_FILE/);
    assert.ok(!/Bearer [A-Za-z0-9]/.test(source), 'must not hardcode a bearer token');
  });

  it('emits no unguarded console.log', () => {
    const offenders = source
      .split('\n')
      .map((line, i) => ({ i: i + 1, t: line.trim() }))
      .filter(({ t }) => t.startsWith('console.log('));
    assert.deepEqual(offenders, []);
  });
});

describe('WatchWakeManager — interval and budget invariants', () => {
  function managerWith(sendWake) {
    return new WatchWakeManager({
      callApi: async (method) => {
        if (method === 'POST') return { status: 201, json: { firingCount: 0 } };
        if (method === 'GET') return { status: 200, json: { firingCount: 0, firings: [] } };
        return { status: 200, json: {} };
      },
      sendWake,
    });
  }

  it('clamps maxWakes into 1..10 and intervalSeconds to >=5', async () => {
    const m = managerWith(() => true);
    const reg = await m.register({
      sessionId: 'c1',
      conditions: [{ type: 'event_type', eventType: 'agent_end' }],
      message: 'W',
      maxWakes: 99,
      intervalSeconds: 1,
    });
    assert.equal(reg.maxWakes, 10);
    assert.equal(reg.intervalSeconds, 5);
  });

  it('rejects empty message / conditions / sessionId', async () => {
    const m = managerWith(() => true);
    await assert.rejects(() => m.register({ sessionId: '', conditions: [{ type: 'event_type', eventType: 'agent_end' }], message: 'W' }));
    await assert.rejects(() => m.register({ sessionId: 'c1', conditions: [], message: 'W' }));
    await assert.rejects(() => m.register({ sessionId: 'c1', conditions: [{ type: 'event_type', eventType: 'agent_end' }], message: '' }));
  });
});

describe('watch-wake extension parent linkage (pi-web-ui contract 1.34.0)', () => {
  it('sends the X-Parent-Session header from the host session id', () => {
    assert.match(source, /hostSessionId/);
    assert.match(source, /"x-parent-session": hostSessionId/);
  });

  it('captures the host session id on session_start and clears it on quit/reload', () => {
    assert.match(source, /hostSessionId = ctx\.sessionManager\.getSessionId\(\)/);
    assert.match(source, /hostSessionId = null/);
  });

  it('threads sourceSessionId into manager.register', () => {
    assert.match(source, /sourceSessionId: hostSessionId \?\? undefined/);
  });
});

// ---------------------------------------------------------------------------
// Persistence dedup: persistRegistrations used to run after EVERY poll,
// appending an identical entry each time — hundreds of entries and megabytes of
// duplicate entries in an idle session file, plus a recurring stat-race hazard
// for the agent's own compaction bookkeeping. Registrations must persist only
// when their persisted content actually changes.
// ---------------------------------------------------------------------------
import { registrationsFingerprint } from '../manager.ts';

describe('watch-wake persistence dedup', () => {
  it('is stable for identical persisted content', () => {
    const entries = [{ sessionId: 'c1', message: 'W', sinceIndex: 3, wakesSent: 1 }];
    assert.equal(registrationsFingerprint(entries), registrationsFingerprint([{ sessionId: 'c1', message: 'W', sinceIndex: 3, wakesSent: 1 }]));
  });

  it('ignores key order', () => {
    const a = registrationsFingerprint([{ sessionId: 'c1', message: 'W', sinceIndex: 0, wakesSent: 0 }]);
    const b = registrationsFingerprint([{ wakesSent: 0, sinceIndex: 0, message: 'W', sessionId: 'c1' }]);
    assert.equal(a, b);
  });

  it('changes when the persisted cursor, budget, or content changes', () => {
    const base = [{ sessionId: 'c1', message: 'W', sinceIndex: 3, wakesSent: 1 }];
    assert.notEqual(registrationsFingerprint(base), registrationsFingerprint([{ sessionId: 'c1', message: 'W', sinceIndex: 4, wakesSent: 1 }]), 'cursor advance must change the fingerprint');
    assert.notEqual(registrationsFingerprint(base), registrationsFingerprint([{ sessionId: 'c1', message: 'W', sinceIndex: 3, wakesSent: 2 }]), 'wake budget consumption must change the fingerprint');
    assert.notEqual(registrationsFingerprint(base), registrationsFingerprint([{ sessionId: 'c2', message: 'W', sinceIndex: 3, wakesSent: 1 }]), 'new registrations must change the fingerprint');
  });

  it('persists only on change (static wiring assertions)', () => {
    assert.match(source, /registrationsFingerprint/, 'index.ts must fingerprint the persisted snapshot');
    assert.match(source, /lastPersistedFingerprint/, 'index.ts must memoise the last persisted fingerprint');
    assert.match(source, /if \(fingerprint === lastPersistedFingerprint\) return;/, 'unchanged polls must skip appendEntry');
    assert.match(source, /pi\.appendEntry\(ENTRY_TYPE, \{ registrations \}\);[^]*lastPersistedFingerprint = fingerprint;/, 'fingerprint must advance only after append succeeds');
  });
});
