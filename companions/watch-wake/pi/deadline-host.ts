import type { ExtensionAPI, ExtensionContext } from '@earendil-works/pi-coding-agent';
import { StringEnum } from '@earendil-works/pi-ai';
import { Type } from 'typebox';
import { DeadlineManager, MAX_MESSAGE_LENGTH, type DeadlineView } from './deadline.ts';

const ENTRY_TYPE = 'watch-wake-deadline';

function describe(deadline: DeadlineView | null, restoreError?: string): string {
  if (restoreError) return `Deadline restore failed: ${restoreError}. No recovered timer is active; reconcile before arming a new wait.`;
  if (!deadline) return 'No local wake deadline.';
  return [
    `id: ${deadline.id}`, `status: ${deadline.status}`,
    `deadline_at: ${new Date(deadline.deadlineAt).toISOString()}`,
    `durable: ${deadline.durable}`,
    ...(deadline.persistenceError ? [`persistence_error: ${deadline.persistenceError}`] : []),
    ...(deadline.lastDeliveryError ? [`delivery_error: ${deadline.lastDeliveryError}`] : []),
    'Expiry is NOT task completion. Delivered means channel acceptance, not host processing.',
  ].join('\n');
}

/** Register the tool now, but start resources only at the actual host lifecycle. */
export function registerDeadlineHost(pi: ExtensionAPI, sendWake: (text: string) => boolean) {
  let manager: DeadlineManager | null = null;
  let hostSession: string | null = null;
  let closed = false;
  let restoreError: string | undefined;

  function current(ctx: ExtensionContext): DeadlineManager {
    if (closed || !manager) throw new Error('Deadline host session ended or has not started.');
    if (ctx.sessionManager.getSessionId() !== hostSession) throw new Error('Deadline host identity changed; refusing mutation.');
    return manager;
  }

  pi.registerTool({
    name: 'wake_deadline',
    label: 'Wake Deadline',
    description: [
      'Arm, inspect or cancel ONE model-free local wake deadline for this session. Use as a bounded backstop alongside a child completion watch, not as a child timer session.',
      'arm replaces the previous wait with a fresh id; delay_seconds is 0–86400. cancel requires the exact current id so an old wait cannot cancel a replacement.',
      'The timer makes no provider/API/process calls; expiry sends a user message here and is NOT completion. Delivery acceptance is not processing; crash recovery may repeat an unacknowledged wake.',
      'Works only while this host event loop is alive; reload restores the latest same-session record, foreign forks refuse recovery. It never resumes a goal engine or decides child success.',
    ].join(' '),
    parameters: Type.Object({
      action: StringEnum(['arm', 'status', 'cancel'] as const),
      delay_seconds: Type.Optional(Type.Integer({ minimum: 0, maximum: 86400, description: 'Required for arm; finite delay in seconds, at most 24 hours.' })),
      message: Type.Optional(Type.String({ minLength: 1, maxLength: MAX_MESSAGE_LENGTH, description: 'Required for arm; bounded reminder, not a completion verdict.' })),
      wait_label: Type.Optional(Type.String({ maxLength: 128 })),
      id: Type.Optional(Type.String({ description: 'Required for cancel: exact deadline id returned by arm/status.' })),
    }),
    async execute(_id, params, signal, _onUpdate, ctx) {
      signal?.throwIfAborted();
      const active = current(ctx);
      let deadline: DeadlineView | null;
      if (params.action === 'arm') {
        if (!Number.isSafeInteger(params.delay_seconds) || params.delay_seconds! < 0 || params.delay_seconds! > 86400) {
          throw new Error('arm requires delay_seconds as a finite integer between 0 and 86400.');
        }
        if (typeof params.message !== 'string') throw new Error('arm requires a message.');
        deadline = await active.arm({ delayMs: params.delay_seconds! * 1000, message: params.message, waitLabel: params.wait_label });
        restoreError = undefined;
      } else if (params.action === 'cancel') {
        const before = active.inspect();
        if (!params.id || params.id !== before?.id) throw new Error('Cancellation id must match the current deadline; the old wait may have been superseded.');
        deadline = (await active.cancel()).deadline;
      } else if (params.action === 'status') {
        deadline = active.inspect();
      } else throw new Error('Unknown deadline action.');
      return { content: [{ type: 'text', text: describe(deadline, restoreError) }], details: { deadline, ...(restoreError ? { restoreError } : {}) } };
    },
  });

  pi.on('before_agent_start', (event) => {
    if (closed) return;
    const deadline = manager?.inspect() ?? null;
    if (restoreError || deadline?.status === 'armed' || deadline?.status === 'pending' || deadline?.status === 'failed') {
      return { systemPrompt: `${event.systemPrompt}\n\nLocal wake deadline (use wake_deadline status/cancel):\n${describe(deadline, restoreError)}` };
    }
  });

  return {
    async start(ctx: ExtensionContext) {
      if (closed) return;
      if (manager) return; // A duplicate lifecycle event must not replay recovery.
      hostSession = ctx.sessionManager.getSessionId();
      manager = new DeadlineManager({ ownerSessionId: hostSession, sendWake, persist: record => pi.appendEntry(ENTRY_TYPE, record) });
      try {
        // Runtime safety state is session-wide, not branch-rewindable: a tree
        // navigation must not resurrect a cancelled/replaced wait on reload.
        const entries = ctx.sessionManager.getEntries?.() ?? ctx.sessionManager.getBranch();
        const latest = [...entries].reverse().find(entry => entry.type === 'custom' && entry.customType === ENTRY_TYPE);
        if (latest && 'data' in latest) await manager.restore(latest.data);
      } catch (error) {
        restoreError = String(error instanceof Error ? error.message : error).slice(0, 512);
        if (ctx.hasUI) ctx.ui.notify(`Deadline restore failed: ${restoreError}`, 'warning');
      }
    },
    dispose() {
      closed = true;
      manager?.dispose();
    },
  };
}
