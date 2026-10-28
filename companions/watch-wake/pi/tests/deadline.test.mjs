import assert from 'node:assert/strict';
import fs from 'node:fs';
import { describe, it } from 'node:test';
import {
  DeadlineManager,
  DEFAULT_MAX_DELAY_MS,
  MAX_MESSAGE_LENGTH,
} from '../deadline.ts';

function settle() {
  return new Promise((resolve) => setImmediate(resolve));
}

function fakeRuntime(start = 1_800_000_000_000) {
  let now = start;
  const timers = [];
  const writes = [];
  const wakes = [];

  const schedule = (callback, delayMs) => {
    const entry = { at: now + delayMs, callback, cancelled: false, called: false };
    timers.push(entry);
    return entry;
  };
  const cancel = (entry) => {
    if (entry) entry.cancelled = true;
  };
  const advance = async (ms) => {
    assert.ok(Number.isFinite(ms) && ms >= 0);
    now += ms;
    let progressed = true;
    while (progressed) {
      progressed = false;
      for (const entry of [...timers].sort((a, b) => a.at - b.at)) {
        if (!entry.cancelled && !entry.called && entry.at <= now) {
          entry.called = true;
          progressed = true;
          entry.callback();
          await settle();
        }
      }
    }
  };
  const latest = () => timers.at(-1);

  return {
    now: () => now,
    schedule,
    cancel,
    advance,
    latest,
    timers,
    writes,
    wakes,
  };
}

function managerFor(runtime, overrides = {}) {
  return new DeadlineManager({
    ownerSessionId: 'host-session-1',
    now: runtime.now,
    schedule: runtime.schedule,
    cancelSchedule: runtime.cancel,
    sendWake: (text) => {
      runtime.wakes.push(text);
      return true;
    },
    persist: (record) => {
      runtime.writes.push(JSON.parse(JSON.stringify(record)));
    },
    ...overrides,
  });
}

function storedRecord(extra = {}) {
  return {
    version: 1,
    id: 'deadline-fixture',
    ownerSessionId: 'host-session-1',
    message: 'fixture wake',
    armedAt: 1_000,
    deadlineAt: 1_010,
    status: 'armed',
    expiryAttempted: false,
    deliveryAttempts: 0,
    maxDeliveryAttempts: 1,
    ...extra,
  };
}

describe('DeadlineManager — replacement and cancellation races', () => {
  it('gives every arm a fresh identity and stale callbacks cannot wake the replacement', async () => {
    const runtime = fakeRuntime();
    const manager = managerFor(runtime);
    const first = await manager.arm({ delayMs: 10, message: 'old wait', waitLabel: 'old' });
    const staleTimer = runtime.latest();
    const second = await manager.arm({ delayMs: 20, message: 'new wait', waitLabel: 'new' });

    assert.notEqual(first.id, second.id);
    staleTimer.callback();
    await settle();
    assert.equal(runtime.wakes.length, 0);

    await runtime.advance(20);
    assert.equal(runtime.wakes.length, 1);
    assert.match(runtime.wakes[0], new RegExp(second.id));
    assert.match(runtime.wakes[0], /new/);
    assert.match(runtime.wakes[0], /NOT completion/);
  });

  it('cancels the local timer and invalidates a callback already queued by the scheduler', async () => {
    const runtime = fakeRuntime();
    const manager = managerFor(runtime);
    await manager.arm({ delayMs: 10, message: 'cancel me' });
    const queued = runtime.latest();

    const result = await manager.cancel();
    assert.equal(result.cancelled, true);
    assert.equal(result.reason, 'cancelled');
    queued.callback();
    await runtime.advance(100);

    assert.equal(runtime.wakes.length, 0);
    assert.equal(manager.inspect().status, 'cancelled');
  });

  it('does not claim to retract a wake that was already accepted for delivery', async () => {
    const runtime = fakeRuntime();
    const manager = managerFor(runtime);
    await manager.arm({ delayMs: 0, message: 'accepted wait' });
    await runtime.advance(0);

    const result = await manager.cancel();
    assert.equal(runtime.wakes.length, 1);
    assert.equal(result.cancelled, false);
    assert.equal(result.reason, 'already-delivered');
    assert.equal(manager.inspect().status, 'delivered');
  });

  it('rejects unsupported thenable persistence promptly instead of hanging arm', async () => {
    const runtime = fakeRuntime();
    const manager = managerFor(runtime, { persist: () => new Promise(() => {}) });
    const outcome = await Promise.race([
      manager.arm({ delayMs: 10, message: 'async adapter' }).then(
        () => 'resolved',
        (error) => `rejected:${error.message}`,
      ),
      new Promise((resolve) => setTimeout(() => resolve('still-pending'), 250)),
    ]);
    assert.notEqual(outcome, 'still-pending');
    assert.match(outcome, /rejected:.*synchronous|rejected:.*thenable|rejected:.*async/i);
    assert.equal(runtime.timers.length, 0, 'unsupported async persistence must not leave an unpersisted timer armed');
    manager.dispose();
  });
});

describe('DeadlineManager — restore, identity and terminal states', () => {
  it('makes one overdue recovery attempt and does not repeat it on an unchanged restore', async () => {
    const source = fakeRuntime();
    const original = managerFor(source);
    await original.arm({ delayMs: 100, message: 'recover me', waitLabel: 'sleep-window' });
    const stored = source.writes.at(-1);
    stored.armedAt = source.now() - 100;
    stored.deadlineAt = source.now() - 1;

    const restoredRuntime = fakeRuntime(source.now());
    const restored = managerFor(restoredRuntime);
    const view = await restored.restore(stored);
    assert.equal(restoredRuntime.wakes.length, 1);
    assert.equal(view.status, 'delivered');
    await restored.restore(stored);
    assert.equal(restoredRuntime.wakes.length, 1);
    assert.ok(restoredRuntime.writes.some((record) => record.status === 'pending'));
  });

  it('rejects a stored deadline owned by another host session', async () => {
    const source = fakeRuntime();
    const original = managerFor(source);
    await original.arm({ delayMs: 100, message: 'private wait' });
    const stored = source.writes.at(-1);
    const other = new DeadlineManager({
      ownerSessionId: 'different-host-session',
      now: source.now,
      schedule: source.schedule,
      cancelSchedule: source.cancel,
      sendWake: () => true,
    });

    await assert.rejects(() => other.restore(stored), /session identity/i);
    assert.equal(other.inspect(), null);
  });

  it('never schedules terminal cancelled or delivered records during restore', async () => {
    const runtime = fakeRuntime();
    const manager = managerFor(runtime);
    await manager.arm({ delayMs: 100, message: 'terminal wait' });
    const armed = runtime.writes.at(-1);
    await manager.cancel();
    const cancelled = runtime.writes.at(-1);
    assert.equal(cancelled.status, 'cancelled');
    await manager.restore(armed);
    assert.equal(manager.inspect().status, 'cancelled', 'an old same-id armed record must not resurrect cancellation');

    const restored = managerFor(fakeRuntime());
    await restored.restore(cancelled);
    assert.equal(restored.list().length, 1);
    assert.equal(restored.inspect().status, 'cancelled');

    const deliveredRuntime = fakeRuntime();
    const deliveredManager = managerFor(deliveredRuntime);
    await deliveredManager.restore({ ...armed, deadlineAt: deliveredRuntime.now() });
    await deliveredRuntime.advance(0);
    const delivered = deliveredManager.inspect();
    assert.equal(delivered.status, 'delivered');
    const terminalRestoreRuntime = fakeRuntime();
    const terminalRestore = managerFor(terminalRestoreRuntime);
    await terminalRestore.restore(deliveredRuntime.writes.at(-1));
    assert.equal(terminalRestoreRuntime.timers.length, 0);
    assert.equal(terminalRestore.inspect().status, 'delivered');
  });
});

describe('DeadlineManager — parent review regression probes', () => {
  it('rejects stored schedules beyond the actual interval and future horizon caps before touching a valid timer', async () => {
    const runtime = fakeRuntime(1_000);
    const manager = managerFor(runtime);
    await manager.arm({ delayMs: 10, message: 'keep this timer' });
    const currentId = manager.inspect().id;
    const activeBefore = runtime.timers.filter((timer) => !timer.cancelled && !timer.called).length;

    await assert.rejects(
      () => manager.restore(storedRecord({ deadlineAt: 1_000 + DEFAULT_MAX_DELAY_MS + 1 })),
      /bound|delay|deadline/i,
    );
    await assert.rejects(
      () => manager.restore(storedRecord({
        status: 'pending',
        expiryAttempted: true,
        nextAttemptAt: 1_000 + DEFAULT_MAX_DELAY_MS + 1,
      })),
      /bound|delay|retry|horizon/i,
    );

    assert.equal(manager.inspect().id, currentId);
    assert.equal(runtime.timers.filter((timer) => !timer.cancelled && !timer.called).length, activeBefore);
    manager.dispose();
  });

  it('bounds internally generated delivery errors so failed records round-trip through restore', async () => {
    const runtime = fakeRuntime(1_000);
    let callback;
    const writes = [];
    const manager = new DeadlineManager({
      ownerSessionId: 'host-session-1',
      now: runtime.now,
      schedule: (fn) => { callback = fn; return 1; },
      cancelSchedule: () => {},
      retryDelaysMs: [],
      persist: (record) => writes.push(JSON.parse(JSON.stringify(record))),
      sendWake: () => { throw new Error('x'.repeat(2_000)); },
    });

    await manager.arm({ delayMs: 0, message: 'error fixture' });
    callback();
    await settle();
    const failed = writes.at(-1);
    assert.equal(failed.status, 'failed');
    assert.ok(failed.lastDeliveryError.length <= 512);

    const restored = new DeadlineManager({ ownerSessionId: 'host-session-1', now: runtime.now, sendWake: () => true });
    await restored.restore(failed);
    assert.equal(restored.inspect().status, 'failed');
    manager.dispose();
    restored.dispose();
  });

  it('round-trips every internally generated status record under synchronous persistence', async () => {
    const cases = [];

    const armedRuntime = fakeRuntime(1_000);
    const armedManager = managerFor(armedRuntime);
    await armedManager.arm({ delayMs: 50, message: 'armed' });
    cases.push(armedRuntime.writes.at(-1));
    armedManager.dispose();

    const pendingRuntime = fakeRuntime(1_000);
    let pendingAttempts = 0;
    const pendingManager = managerFor(pendingRuntime, {
      retryDelaysMs: [10],
      sendWake: () => { pendingAttempts += 1; return false; },
    });
    await pendingManager.arm({ delayMs: 0, message: 'pending' });
    await pendingRuntime.advance(0);
    assert.equal(pendingAttempts, 1);
    cases.push(pendingRuntime.writes.at(-1));
    pendingManager.dispose();

    const deliveredRuntime = fakeRuntime(1_000);
    const deliveredManager = managerFor(deliveredRuntime);
    await deliveredManager.arm({ delayMs: 0, message: 'delivered' });
    await deliveredRuntime.advance(0);
    cases.push(deliveredRuntime.writes.at(-1));
    deliveredManager.dispose();

    const failedRuntime = fakeRuntime(1_000);
    const failedManager = managerFor(failedRuntime, { retryDelaysMs: [], sendWake: () => false });
    await failedManager.arm({ delayMs: 0, message: 'failed' });
    await failedRuntime.advance(0);
    cases.push(failedRuntime.writes.at(-1));
    failedManager.dispose();

    const cancelledRuntime = fakeRuntime(1_000);
    const cancelledManager = managerFor(cancelledRuntime);
    await cancelledManager.arm({ delayMs: 50, message: 'cancelled' });
    await cancelledManager.cancel();
    cases.push(cancelledRuntime.writes.at(-1));
    cancelledManager.dispose();

    for (const record of cases) {
      const restoredRuntime = fakeRuntime(1_000);
      const restored = managerFor(restoredRuntime);
      await restored.restore(record);
      assert.equal(restored.inspect().status, record.status, `status ${record.status} must restore`);
      restored.dispose();
    }
  });
});

describe('DeadlineManager — delivery failures and persistence truth', () => {
  it('keeps a rejected delivery explicit, retries with a finite bound, then stops', async () => {
    const runtime = fakeRuntime();
    let attempts = 0;
    const manager = managerFor(runtime, {
      retryDelaysMs: [5, 7],
      sendWake: () => {
        attempts += 1;
        return false;
      },
    });

    await manager.arm({ delayMs: 0, message: 'retry wait' });
    await runtime.advance(0);
    assert.equal(attempts, 1);
    assert.equal(manager.inspect().status, 'pending');
    assert.ok(manager.inspect().nextAttemptAt > runtime.now());

    await runtime.advance(5);
    assert.equal(attempts, 2);
    await runtime.advance(7);
    assert.equal(attempts, 3);
    assert.equal(manager.inspect().status, 'failed');
    assert.equal(manager.inspect().deliveryAttempts, 3);
    assert.equal(runtime.timers.filter((timer) => !timer.cancelled && !timer.called).length, 0);
  });

  it('keeps retry scheduling finite even when the arm cap is shorter than a retry delay', async () => {
    const runtime = fakeRuntime(1_000);
    let attempts = 0;
    const manager = managerFor(runtime, {
      maxDelayMs: 1,
      retryDelaysMs: [3],
      sendWake: () => { attempts += 1; return false; },
    });
    await manager.arm({ delayMs: 0, message: 'short cap retry' });
    await runtime.advance(0);
    assert.equal(attempts, 1);
    await runtime.advance(3);
    assert.equal(attempts, 2);
    assert.equal(manager.inspect().status, 'failed');
  });

  it('reports persistence failure without claiming the in-memory deadline is durable', async () => {
    const runtime = fakeRuntime();
    const manager = managerFor(runtime, {
      persist: () => {
        throw new Error('storage offline');
      },
    });

    const armed = await manager.arm({ delayMs: 0, message: 'not durable' });
    assert.equal(armed.durable, false);
    assert.match(armed.persistenceError, /storage offline/);
    await runtime.advance(0);
    assert.equal(runtime.wakes.length, 1);
    assert.equal(manager.inspect().durable, false);
    assert.match(manager.inspect().persistenceError, /storage offline/);
  });

  it('writes only changed deadline records, not on inspection or idle time', async () => {
    const runtime = fakeRuntime();
    const manager = managerFor(runtime);
    await manager.arm({ delayMs: 100, message: 'stable wait' });
    const writesAfterArm = runtime.writes.length;
    assert.equal(writesAfterArm, 1);

    manager.inspect();
    manager.list();
    await runtime.advance(50);
    assert.equal(runtime.writes.length, writesAfterArm);
  });
});

describe('DeadlineManager — disposal, validation and process boundary', () => {
  it('disposes runtime resources and stale callbacks cannot use the old wake channel', async () => {
    const runtime = fakeRuntime();
    const manager = managerFor(runtime);
    await manager.arm({ delayMs: 10, message: 'dispose wait' });
    const stale = runtime.latest();
    const writesBeforeDispose = runtime.writes.length;

    manager.dispose();
    stale.callback();
    await runtime.advance(100);

    assert.equal(runtime.wakes.length, 0);
    assert.equal(runtime.writes.length, writesBeforeDispose);
    assert.equal(manager.inspect().status, 'armed');
    assert.equal(manager.inspect().durable, true);
    await assert.rejects(() => manager.arm({ delayMs: 1, message: 'nope' }), /disposed/i);
  });

  it('rejects malformed, unbounded and non-finite inputs', async () => {
    const runtime = fakeRuntime();
    const manager = managerFor(runtime, { maxDelayMs: 100 });
    await assert.rejects(() => manager.arm({ delayMs: -1, message: 'bad' }), /delay/i);
    await assert.rejects(() => manager.arm({ delayMs: Number.NaN, message: 'bad' }), /finite|delay/i);
    await assert.rejects(() => manager.arm({ delayMs: Number.POSITIVE_INFINITY, message: 'bad' }), /finite|delay/i);
    await assert.rejects(() => manager.arm({ delayMs: 101, message: 'bad' }), /maximum|bound|delay/i);
    await assert.rejects(() => manager.arm({ delayMs: 1, message: '' }), /message/i);
    await assert.rejects(() => manager.arm({ delayMs: 1, message: 'x'.repeat(MAX_MESSAGE_LENGTH + 1) }), /message/i);
    await assert.rejects(() => manager.arm({ delayMs: 1, deadlineAt: runtime.now() + 1, message: 'both' }), /delay|deadline|one/i);
    await assert.rejects(() => manager.restore({ version: 1, ownerSessionId: 'host-session-1', id: 'bad', status: 'unknown' }), /status|stored|invalid/i);
    await assert.rejects(() => manager.restore({ version: 1, ownerSessionId: 'host-session-1', id: 'bad', status: 'armed', message: 'x' }), /deadline|stored|invalid/i);
    assert.ok(DEFAULT_MAX_DELAY_MS >= 60 * 60 * 1000);
  });

  it('contains no model, child-process or network dispatch path', () => {
    const source = fs.readFileSync(new URL('../deadline.ts', import.meta.url), 'utf8');
    assert.doesNotMatch(source, /child_process|spawn\(|exec\(|fetch\(|subagent|model[-_ ]?call/i);
  });
});

describe('DeadlineManager — real Node timer proof', { timeout: 2_000 }, () => {
  it('expires, cancels and disposes using the real event loop with short bounded waits', async () => {
    const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms));
    const waitFor = async (predicate, timeoutMs = 500) => {
      const started = Date.now();
      while (!predicate()) {
        if (Date.now() - started > timeoutMs) throw new Error('real timer proof timed out');
        await wait(5);
      }
    };

    const expiredWakes = [];
    const expiryManager = new DeadlineManager({
      ownerSessionId: 'real-expiry-host',
      sendWake: (text) => {
        expiredWakes.push(text);
        return true;
      },
    });
    await expiryManager.arm({ delayMs: 25, message: 'real expiry' });
    await waitFor(() => expiredWakes.length === 1);
    assert.match(expiredWakes[0], /NOT completion/);
    expiryManager.dispose();

    const cancelledWakes = [];
    const cancelManager = new DeadlineManager({
      ownerSessionId: 'real-cancel-host',
      sendWake: (text) => {
        cancelledWakes.push(text);
        return true;
      },
    });
    await cancelManager.arm({ delayMs: 30, message: 'real cancellation' });
    await cancelManager.cancel();
    await wait(100);
    assert.equal(cancelledWakes.length, 0);

    const disposedWakes = [];
    const disposeManager = new DeadlineManager({
      ownerSessionId: 'real-dispose-host',
      sendWake: (text) => {
        disposedWakes.push(text);
        return true;
      },
    });
    await disposeManager.arm({ delayMs: 30, message: 'real disposal' });
    disposeManager.dispose();
    await wait(100);
    assert.equal(disposedWakes.length, 0);
  });
});
