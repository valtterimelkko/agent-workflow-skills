import assert from 'node:assert/strict';
import { test } from 'node:test';
import { DeadlineManager } from '../deadline.ts';

function fixture() {
  const timers = [], writes = [];
  const manager = new DeadlineManager({
    ownerSessionId: 'parent-review', now: () => 1000,
    schedule: (callback, delay) => { const timer = { callback, delay, cancelled: false }; timers.push(timer); return timer; },
    cancelSchedule: timer => { timer.cancelled = true; },
    persist: record => { writes.push(record); }, sendWake: () => true,
  });
  return { manager, timers, writes };
}

test('a disposed deadline manager cannot append a cancellation into a replacement host', async () => {
  const { manager, writes } = fixture();
  await manager.arm({ delayMs: 100, message: 'still owned by the resumed host' });
  manager.dispose();
  const before = writes.length;
  await assert.rejects(manager.cancel(), /disposed/i);
  assert.equal(writes.length, before);
  assert.equal(manager.inspect().status, 'armed');
});

test('a queued stale callback cannot hide the new timer from disposal', async () => {
  const { manager, timers } = fixture();
  await manager.arm({ delayMs: 100, message: 'old' });
  const old = timers.at(-1);
  await manager.arm({ delayMs: 200, message: 'new' });
  const current = timers.at(-1);
  old.callback();
  await new Promise(resolve => setImmediate(resolve));
  manager.dispose();
  assert.equal(current.cancelled, true, 'replacement timer must be cancelled even after old callback ran');
});
