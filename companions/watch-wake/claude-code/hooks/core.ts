// watch-wake core — pure policy for the Claude Code watch-wake mod.
//
// No imports and no I/O: every effect is an injected dependency, so the same
// file runs inside the Claude Code hooks environment (no Node) and under
// `node --test` (tests/core.test.mjs).
//
// Two independent parts:
//   WatchWakeCore  — pure-observer Pi Web UI Internal API watch on a CHILD
//                    session; polls the durable ledger and delivers one wake per
//                    new firing batch (bounded by maxWakes) into THIS session.
//   DeadlineCore   — one model-free local wait-window backstop (wake_deadline).
//
// Delivery is whatever the host injects: in the mod it is `$.prompt.submit`,
// which starts a turn of its own once the session is idle — so a Claude Code
// parent may END its turn and go fully idle.

export interface WatchConditionSpec {
  id?: string
  type: 'event_type' | 'tool' | 'text' | 'deadline'
  eventType?: string
  dataMatch?: Record<string, unknown>
  toolName?: string
  phase?: 'start' | 'end'
  argIncludes?: string
  contains?: string
  pattern?: string
  patternFlags?: string
  source?: 'assistant' | 'any'
  /** For type 'deadline': seconds until the server-side timer fires (integer 1..86400). */
  afterSeconds?: number
  once?: boolean
}

/** The complete set of condition types the Pi Web UI server can ever match. */
export const KNOWN_CONDITION_TYPES = ['event_type', 'tool', 'text', 'deadline'] as const

const PRIMITIVE_DATAMATCH = new Set(['string', 'number', 'boolean'])

/**
 * Registration-time validation. A condition whose shape can NEVER match must be
 * refused locally, before any API call, with a message spelling out the correct
 * shape — instead of registering, answering "Watching", and stranding the parent
 * forever.
 *
 * Live incident: a parent registered `{ "type": "goal_end" }` (an
 * event name used AS the type) and `{ "type": "text_match" }`; the watch was
 * accepted and the wake never came.
 *
 * The known-type set mirrors the server's own `KNOWN_CONDITION_TYPES`
 * (condition evaluator): `event_type`, `tool`,
 * `text`, `deadline`. The server's shallow `data[k] === v` match is why a
 * dotted key or a nested object value can never fire.
 */
export function validateConditions(conditions: WatchConditionSpec[]): void {
  for (const spec of conditions) {
    const type = (spec as { type?: unknown })?.type
    if (typeof type !== 'string' || !(KNOWN_CONDITION_TYPES as readonly string[]).includes(type)) {
      const name = typeof type === 'string' ? type : String(type)
      const bare = /^[a-z][a-z0-9_]*$/.test(name)
      throw new Error(
        `unknown condition type "${name}" — valid types are ${KNOWN_CONDITION_TYPES.join(', ')}. ` +
          (bare
            ? `If "${name}" is an event name, use {"type":"event_type","eventType":"${name}"} (the event name is the eventType field, not the type). `
            : '') +
          'For text, use {"type":"text","contains":"…"} or {"type":"text","pattern":"…"}.',
      )
    }
    if (type === 'event_type' && (typeof spec.eventType !== 'string' || spec.eventType.trim().length === 0)) {
      throw new Error(
        'event_type conditions require a non-empty string eventType, e.g. {"type":"event_type","eventType":"agent_end"}. ' +
          'Without it the condition can never match.',
      )
    }
    if (type === 'text' && spec.contains === undefined && spec.pattern === undefined) {
      throw new Error('text conditions require contains or pattern — without one the condition can never match')
    }
    if (spec.dataMatch !== undefined) {
      if (spec.dataMatch === null || typeof spec.dataMatch !== 'object' || Array.isArray(spec.dataMatch)) {
        throw new Error('dataMatch must be an object of top-level primitive key/value pairs, e.g. {"status":"paused"}')
      }
      for (const [key, value] of Object.entries(spec.dataMatch)) {
        if (key.includes('.')) {
          throw new Error(
            `dataMatch key "${key}" is dotted, but the server's match is shallow (a top-level event-data key only): ` +
              `it can never match. Use the top-level key (e.g. "${key.split('.').pop()}"), or watch the eventType itself.`,
          )
        }
        if (!PRIMITIVE_DATAMATCH.has(typeof value) || value === null) {
          throw new Error(
            `dataMatch value for "${key}" must be a primitive (string, number or boolean): the server compares ` +
              `event.data[key] === value shallowly, so an object, array or null value can never match.`,
          )
        }
      }
    }
  }
}

export type RegistrationStatus = 'watching' | 'done' | 'stale' | 'cancelled'

export interface Registration {
  id: string
  sessionId: string
  conditions: WatchConditionSpec[]
  message: string
  maxWakes: number
  intervalSeconds: number
  label: string
  status: RegistrationStatus
  sinceIndex: number
  wakesSent: number
  createdAt: number
  lastPolledAt: number
  generation?: string
  consecutiveFailures: number
  noticesSent: number
  lastError?: string
  /** When a found wake was queued in the outbox and is not yet delivered (parent busy). */
  pendingSince?: number
  /** Non-fatal advice returned at registration (e.g. an unsupported option). */
  warning?: string
}

export interface ApiResult { status: number; json?: any }

export interface CoreDeps {
  callApi: (method: string, path: string, body?: unknown) => Promise<ApiResult>
  /** Deliver text into the parent session. Resolve = accepted; reject = retry later. */
  deliver: (text: string) => Promise<unknown>
  now: () => number
  persist?: (snapshot: WatchSnapshot) => void | Promise<void>
  notify?: (text: string) => void
  /** Shared outbox; when omitted a private one delivering via `deliver` (never busy) is used. */
  outbox?: Outbox
}

export interface WatchSnapshot { version: 1; seq: number; registrations: Registration[] }

/**
 * Can a wake delivered by `$.prompt.submit` land in this session?
 * - interactive CLI: yes.
 * - Remote Control (`claude remote-control`) spawns one long-lived headless SDK process per
 *   session (`CLAUDE_CODE_ENVIRONMENT_KIND=bridge`); it stays up between turns and
 *   `$.prompt.submit` starts a new turn there (live-checked): yes.
 * - `-p` and other SDK hosts: no — the process exits or its host drives it.
 */
export function canLocalWake(opts: { interactive: boolean; environmentKind?: string }): boolean {
  return opts.interactive || opts.environmentKind === 'bridge'
}

export const LABEL_PREFIX = 'watch-wake:'
export const DEFAULT_INTERVAL_SECONDS = 30
export const MIN_INTERVAL_SECONDS = 5
export const MAX_INTERVAL_SECONDS = 3600
export const MAX_WAKES = 10
export const FAILURE_NOTICE_THRESHOLD = 10
const API = '/api/v1'

export function interpolate(
  template: string,
  firing: { conditionId?: string; eventType?: string; firedAt?: number },
  sessionId: string,
  firingCount: number,
): string {
  const sub = (s: string, find: string, value: string) => s.split(find).join(value)
  let out = sub(template, '{{sessionId}}', sessionId)
  out = sub(out, '{{conditionId}}', firing.conditionId ?? 'unknown')
  out = sub(out, '{{eventType}}', firing.eventType ?? 'unknown')
  out = sub(out, '{{firedAt}}', typeof firing.firedAt === 'number' ? new Date(firing.firedAt).toISOString() : 'unknown')
  out = sub(out, '{{firingCount}}', String(firingCount))
  return out
}

const clamp = (n: number, lo: number, hi: number) => Math.max(lo, Math.min(hi, n))
const errText = (e: unknown) => (e instanceof Error ? e.message : String(e))
const detail = (r: ApiResult) => r.json?.code ?? r.json?.error ?? `HTTP ${r.status}`
const watchPath = (sessionId: string) => `${API}/sessions/${encodeURIComponent(sessionId)}/watch`

// ─── Outbox: hold wakes while the parent is busy, coalesce, drop cancelled ──

export interface OutboxItem {
  key: string
  text: string
  /** Re-checked immediately before delivery; false drops the item (e.g. cancelled). */
  wanted: () => boolean
  accepted: () => void
  failed: (error: string) => void
}

/**
 * Every wake (watch firing, stale notice, deadline) goes through one outbox.
 * It delivers only while the parent is idle, re-checks each item just before
 * sending (a cancelled registration's wake is dropped), and merges everything
 * pending into ONE prompt, so N children finishing during one busy turn cost
 * one wake turn, not N.
 */
export class Outbox {
  private readonly deps: { deliver: (text: string) => Promise<unknown>; isBusy?: () => boolean }
  private readonly items = new Map<string, OutboxItem>()
  private flushing: Promise<void> | undefined

  constructor(deps: { deliver: (text: string) => Promise<unknown>; isBusy?: () => boolean }) {
    this.deps = deps
  }

  enqueue(item: OutboxItem): void {
    if (!this.items.has(item.key)) this.items.set(item.key, item)
  }

  hasPrefix(prefix: string): boolean {
    for (const k of this.items.keys()) if (k.startsWith(prefix)) return true
    return false
  }

  get size(): number {
    return this.items.size
  }

  async settled(): Promise<void> {
    while (this.flushing) await this.flushing
  }

  flush(): Promise<void> {
    if (this.flushing) return this.flushing
    if (this.items.size === 0 || this.deps.isBusy?.()) return Promise.resolve()
    const run = async () => {
      for (const [key, item] of this.items) if (!item.wanted()) this.items.delete(key)
      const batch = [...this.items.values()]
      if (batch.length === 0) return
      const text =
        batch.length === 1
          ? batch[0]!.text
          : `[watch-wake] ${batch.length} wakes arrived together — reconcile each, then decide what is still outstanding:\n\n` +
            batch.map((b, i) => `${i + 1}. ${b.text}`).join('\n\n')
      try {
        await this.deps.deliver(text)
        for (const b of batch) {
          this.items.delete(b.key)
          b.accepted()
        }
      } catch (error) {
        for (const b of batch) {
          this.items.delete(b.key)
          b.failed(errText(error))
        }
      }
    }
    const p: Promise<void> = run().finally(() => {
      if (this.flushing === p) this.flushing = undefined
    })
    this.flushing = p
    return p
  }
}

export class WatchWakeCore {
  private readonly deps: CoreDeps
  private readonly regs = new Map<string, Registration>()
  readonly outbox: Outbox
  private seq = 0
  private ticking: Promise<void> | undefined

  constructor(deps: CoreDeps) {
    this.deps = deps
    this.outbox = deps.outbox ?? new Outbox({ deliver: deps.deliver })
  }

  get(id: string): Registration | undefined {
    const r = this.regs.get(id)
    return r ? { ...r } : undefined
  }

  list(): Registration[] {
    return [...this.regs.values()].map((r) => ({ ...r }))
  }

  hasActive(): boolean {
    return [...this.regs.values()].some((r) => r.status === 'watching')
  }

  snapshot(): WatchSnapshot {
    return { version: 1, seq: this.seq, registrations: [...this.regs.values()].map((r) => structuredClone(r)) }
  }

  private async save(): Promise<void> {
    try {
      await this.deps.persist?.(this.snapshot())
    } catch {
      /* best effort: the server-side ledger survives regardless */
    }
  }

  private async capabilities(): Promise<Record<string, unknown>> {
    const res = await this.deps.callApi('GET', `${API}/capabilities`)
    if (res.status !== 200) throw new Error(`capability discovery failed (${detail(res)}); refusing to mutate a watch blind`)
    return (res.json?.features ?? {}) as Record<string, unknown>
  }

  private async capable(): Promise<boolean> {
    return Boolean((await this.capabilities()).watchGenerationPreconditions)
  }

  async register(
    args: {
      sessionId: string
      conditions: WatchConditionSpec[]
      message: string
      maxWakes?: number
      intervalSeconds?: number
      label?: string
      replace?: boolean
      fireIfSettled?: boolean
    },
    ctx: { selfSessionId?: string } = {},
  ): Promise<Registration> {
    const sessionId = String(args.sessionId ?? '').trim()
    if (!sessionId) throw new Error('session_id is required')
    // The id goes into a URL path: refuse anything that could change the route.
    if (sessionId === '.' || sessionId === '..' || /[\/\\?#%\s]/.test(sessionId)) {
      throw new Error('session_id is not a valid session id')
    }
    if (ctx.selfSessionId && sessionId.includes(ctx.selfSessionId)) {
      throw new Error('refusing to watch your own session: an idle session emits no events — watch the CHILD')
    }
    if (!Array.isArray(args.conditions) || args.conditions.length === 0) throw new Error('at least one condition is required')
    if (!String(args.message ?? '').trim()) throw new Error('message is required')
    // Refuse a condition whose shape can never match BEFORE any API call: the
    // server would otherwise accept it and the wake would never come (F1).
    validateConditions(args.conditions)
    const maxWakes = clamp(Math.trunc(args.maxWakes ?? 1), 1, MAX_WAKES)
    // The server's conditions default to once:true (fire on first match only), which
    // would make every wake after the first unreachable.
    let conditions = args.conditions
    if (maxWakes > 1) {
      // A deadline fires exactly once by design (the server refuses once:false on it), so it stays one-shot.
      if (conditions.some((c) => c.once === true && c.type !== 'deadline')) {
        throw new Error('max_wakes > 1 needs conditions that can fire repeatedly: remove once:true (or set once:false)')
      }
      conditions = conditions.map((c) => (c.type === 'deadline' ? c : { ...c, once: false }))
    }

    const caps = await this.capabilities()
    const isCapable = Boolean(caps.watchGenerationPreconditions)
    const existing = await this.deps.callApi('GET', watchPath(sessionId))
    const hasExisting = existing.status === 200
    if (hasExisting && !args.replace) {
      const label = String(existing.json?.label ?? '')
      const foreign = existing.json?.onFire || !label.startsWith(LABEL_PREFIX)
      if (foreign) {
        throw new Error(
          `session ${sessionId} already has a watch (label "${label || 'none'}"${existing.json?.onFire ? ', with onFire' : ''}); ` +
            'registering would REPLACE it and wipe its ledger. Pass replace:true only if you own it, or use the relay pattern ' +
            '(server onFire on the child -> disposable managed relay session; watch the relay).',
        )
      }
    }

    const label = args.label ? `${LABEL_PREFIX}${args.label}` : `${LABEL_PREFIX}${sessionId}`
    const body: Record<string, unknown> = { conditions, pin: true, label }
    if (isCapable) body.expectedGeneration = hasExisting ? (existing.json?.generation ?? null) : null
    let warning: string | undefined
    if (args.fireIfSettled) {
      if (caps.watchFireIfSettled) body.fireIfSettled = true
      else warning = 'fireIfSettled ignored: this Pi Web UI does not advertise features.watchFireIfSettled — check the child run receipt yourself'
    }
    const res = await this.deps.callApi('POST', watchPath(sessionId), body)
    if (res.status !== 200 && res.status !== 201) throw new Error(`watch registration failed: ${detail(res)}`)

    // Supersede our own older local handles for the same child: the server
    // keeps one watch per session, so only the newest handle is live.
    for (const r of this.regs.values()) {
      if (r.sessionId === sessionId && r.status === 'watching') {
        r.status = 'cancelled'
        r.lastError = 'superseded by a newer registration on the same child'
      }
    }

    const now = this.deps.now()
    const reg: Registration = {
      id: `ww_${++this.seq}_${now}`,
      sessionId,
      conditions,
      message: args.message,
      maxWakes,
      intervalSeconds: clamp(Math.trunc(args.intervalSeconds ?? DEFAULT_INTERVAL_SECONDS), MIN_INTERVAL_SECONDS, MAX_INTERVAL_SECONDS),
      label,
      status: 'watching',
      // A fresh (or replaced) ledger holds only post-registration firings:
      // start at zero so a firing that raced the POST still wakes us.
      sinceIndex: 0,
      wakesSent: 0,
      createdAt: now,
      lastPolledAt: 0,
      generation: typeof res.json?.generation === 'string' ? res.json.generation : undefined,
      consecutiveFailures: 0,
      noticesSent: 0,
      warning,
    }
    this.regs.set(reg.id, reg)
    await this.save()
    return { ...reg }
  }

  /** One pass over due registrations; single-flight (overlapping ticks join). */
  tick(): Promise<void> {
    if (this.ticking) return this.ticking
    const run = async () => {
      const now = this.deps.now()
      for (const reg of this.regs.values()) {
        if (reg.status !== 'watching') continue
        if (reg.lastPolledAt && now - reg.lastPolledAt < reg.intervalSeconds * 1000) continue
        reg.lastPolledAt = now
        try {
          await this.pollOnce(reg)
        } catch (error) {
          this.recordFailure(reg, errText(error))
        }
      }
      // Start (never await) the flush: a delivery that resolves only when the
      // parent's next turn starts must not block polling.
      void this.outbox.flush()
    }
    // Clear only after assignment (a pass with nothing due completes
    // synchronously and would otherwise leave a stale single-flight handle).
    const p: Promise<void> = run().finally(() => {
      if (this.ticking === p) this.ticking = undefined
    })
    this.ticking = p
    return p
  }

  /** Resolves once every in-flight delivery has settled (tests, shutdown). */
  async settled(): Promise<void> {
    await this.outbox.flush()
    await this.outbox.settled()
  }

  private recordFailure(reg: Registration, message: string): void {
    reg.consecutiveFailures += 1
    reg.lastError = message
    if (reg.consecutiveFailures === FAILURE_NOTICE_THRESHOLD) {
      this.notice(reg, `[watch-wake] polling the watch on child ${reg.sessionId} keeps failing (${reg.consecutiveFailures} in a row: ${message}). ` +
        'Still watching; check Pi Web UI health (GET /capabilities) and the child, then decide whether to keep waiting.')
    }
  }

  private markStale(reg: Registration, why: string): void {
    reg.status = 'stale'
    reg.lastError = why
    this.notice(reg, `[watch-wake] the watch on child ${reg.sessionId} is stale: ${why}. ` +
      'No further wakes will come from it. Reconcile the child now (GET /sessions/:id, /runs/:runId) and re-register with watch_wake_register if you still need to wait.')
    void this.save()
  }

  private notice(reg: Registration, text: string): void {
    reg.noticesSent += 1
    this.deps.notify?.(text)
    this.outbox.enqueue({
      key: `${reg.id}:notice:${reg.noticesSent}`,
      text,
      wanted: () => reg.status !== 'cancelled',
      accepted: () => {},
      failed: (e) => {
        reg.lastError = `notice delivery failed: ${e}`
      },
    })
  }

  private isDelivering(reg: Registration): boolean {
    return this.outbox.hasPrefix(`${reg.id}:`)
  }

  private async pollOnce(reg: Registration): Promise<void> {
    if (this.isDelivering(reg)) return
    const res = await this.deps.callApi('GET', `${watchPath(reg.sessionId)}?sinceIndex=${reg.sinceIndex}`)
    if (res.status === 404) return this.markStale(reg, 'WATCH_NOT_FOUND (deleted, or the child was removed)')
    if (res.status !== 200) return this.recordFailure(reg, `poll failed: ${detail(res)}`)
    reg.consecutiveFailures = 0
    const gen = res.json?.generation
    if (reg.generation && typeof gen === 'string' && gen !== reg.generation) {
      return this.markStale(reg, `watch generation changed (${reg.generation} -> ${gen}): another session replaced it`)
    }
    if (res.json?.status === 'detached') {
      return this.markStale(reg, 'watch reloaded detached after a Pi Web UI restart; new events are not being recorded')
    }
    const total = typeof res.json?.firingCount === 'number' ? res.json.firingCount : reg.sinceIndex
    const fresh: Array<{ conditionId?: string; eventType?: string; firedAt?: number }> = Array.isArray(res.json?.firings) ? res.json.firings : []
    if (fresh.length === 0) {
      reg.sinceIndex = Math.max(reg.sinceIndex, total)
      return
    }
    if (reg.wakesSent >= reg.maxWakes) {
      reg.sinceIndex = Math.max(reg.sinceIndex, total)
      reg.status = 'done'
      await this.save()
      return
    }
    const last = fresh[fresh.length - 1] ?? {}
    const text = interpolate(reg.message, last, reg.sessionId, total)
    reg.pendingSince = this.deps.now()
    this.outbox.enqueue({
      key: `${reg.id}:wake:${reg.wakesSent}`,
      text,
      wanted: () => reg.status === 'watching',
      accepted: () => {
        reg.pendingSince = undefined
        reg.wakesSent += 1
        reg.sinceIndex = Math.max(reg.sinceIndex, total)
        reg.lastError = undefined
        if (reg.wakesSent >= reg.maxWakes) reg.status = 'done'
        this.deps.notify?.(`woke this session for ${reg.sessionId} (${reg.wakesSent}/${reg.maxWakes})`)
        void this.save()
      },
      failed: (e) => {
        reg.pendingSince = undefined
        reg.lastError = `wake delivery failed; will retry next poll (${e})`
      },
    })
  }

  async cancel(id: string): Promise<{ registration: Registration; remote: string }> {
    const reg = this.regs.get(id)
    if (!reg) throw new Error(`no watch-wake registration "${id}"`)
    const wasLive = reg.status === 'watching' || reg.status === 'done'
    reg.status = 'cancelled'
    reg.pendingSince = undefined
    await this.save()
    if (!wasLive) return { registration: { ...reg }, remote: 'not-attempted (registration was not live)' }
    let remote: string
    try {
      const isCapable = await this.capable()
      if (isCapable && reg.generation) {
        const res = await this.deps.callApi('DELETE', watchPath(reg.sessionId), { expectedGeneration: reg.generation })
        if (res.status === 200 && res.json?.success === true && res.json?.generation === reg.generation) remote = 'deleted-confirmed'
        else if (res.status === 409) remote = 'not-deleted-generation-mismatch'
        else if (res.status === 404) remote = 'already-gone'
        else remote = `ambiguous (${detail(res)}) — not retried`
      } else {
        const res = await this.deps.callApi('DELETE', watchPath(reg.sessionId))
        remote = res.status === 200 ? 'deleted-legacy-unconditional' : res.status === 404 ? 'already-gone' : `ambiguous (${detail(res)})`
      }
    } catch (error) {
      remote = `remote cleanup pending: ${errText(error)}`
    }
    reg.lastError = remote.startsWith('deleted') || remote === 'already-gone' ? undefined : remote
    await this.save()
    return { registration: { ...reg }, remote }
  }

  /** Re-attach persisted registrations to their surviving server watches. */
  async restore(snapshot: WatchSnapshot | undefined): Promise<{ resumed: number; stale: number }> {
    let resumed = 0
    let stale = 0
    if (!snapshot || snapshot.version !== 1) return { resumed, stale }
    this.seq = Math.max(this.seq, snapshot.seq ?? 0)
    for (const saved of snapshot.registrations ?? []) {
      const reg: Registration = { ...saved, lastPolledAt: 0 }
      this.regs.set(reg.id, reg)
      if (reg.status !== 'watching') continue
      try {
        const res = await this.deps.callApi('GET', `${watchPath(reg.sessionId)}?sinceIndex=${reg.sinceIndex}`)
        const gen = res.json?.generation
        if (res.status !== 200) {
          reg.status = 'stale'
          reg.lastError = `restore: ${detail(res)}`
          stale++
        } else if (reg.generation && typeof gen === 'string' && gen !== reg.generation) {
          reg.status = 'stale'
          reg.lastError = `restore: watch generation changed (${reg.generation} -> ${gen})`
          stale++
        } else {
          resumed++
        }
      } catch (error) {
        // Transport down at restore: keep watching; the poll loop retries.
        reg.lastError = `restore: ${errText(error)}`
        resumed++
      }
    }
    await this.save()
    return { resumed, stale }
  }
}

// ─── DeadlineCore: one model-free local wait-window backstop ────────────────

export type DeadlineStatus = 'armed' | 'delivered' | 'cancelled' | 'failed'

export interface Deadline {
  id: string
  label?: string
  message: string
  armedAt: number
  dueAt: number
  status: DeadlineStatus
  attempts: number
  nextAttemptAt: number
  lastError?: string
  /** Set on arm when it superseded an earlier still-armed deadline. */
  replacedId?: string
}

export interface DeadlineSnapshot { version: 1; seq: number; deadline?: Deadline }

export const MAX_DEADLINE_SECONDS = 86_400
export const DEADLINE_MAX_ATTEMPTS = 3
export const DEADLINE_RETRY_MS = 30_000

export class DeadlineCore {
  private readonly deps: { now: () => number; deliver: (text: string) => Promise<unknown>; persist?: (s: DeadlineSnapshot) => void | Promise<void>; outbox?: Outbox }
  private readonly outbox: Outbox
  private current: Deadline | undefined
  private seq = 0

  constructor(deps: { now: () => number; deliver: (text: string) => Promise<unknown>; persist?: (s: DeadlineSnapshot) => void | Promise<void>; outbox?: Outbox }) {
    this.deps = deps
    this.outbox = deps.outbox ?? new Outbox({ deliver: deps.deliver })
  }

  snapshot(): DeadlineSnapshot {
    return { version: 1, seq: this.seq, deadline: this.current ? { ...this.current } : undefined }
  }

  private save(): void {
    try {
      void this.deps.persist?.(this.snapshot())
    } catch {
      /* best effort */
    }
  }

  status(): Deadline | undefined {
    return this.current ? { ...this.current } : undefined
  }

  isArmed(): boolean {
    return this.current?.status === 'armed'
  }

  arm(args: { delaySeconds: number; message: string; label?: string }): Deadline {
    const delay = Number(args.delaySeconds)
    if (!Number.isInteger(delay) || delay < 0 || delay > MAX_DEADLINE_SECONDS) {
      throw new Error(`delay_seconds must be an integer 0..${MAX_DEADLINE_SECONDS}`)
    }
    if (!String(args.message ?? '').trim()) throw new Error('message is required')
    const now = this.deps.now()
    const replacedId = this.current?.status === 'armed' ? this.current.id : undefined
    this.current = {
      id: `wd_${++this.seq}_${now}`,
      label: args.label,
      message: args.message,
      armedAt: now,
      dueAt: now + delay * 1000,
      status: 'armed',
      attempts: 0,
      nextAttemptAt: now + delay * 1000,
      replacedId,
    }
    this.save()
    return { ...this.current }
  }

  cancel(id: string): Deadline {
    if (!this.current || this.current.id !== id) throw new Error(`"${id}" is not the current deadline (current: ${this.current?.id ?? 'none'})`)
    if (this.current.status === 'armed') this.current.status = 'cancelled'
    this.save()
    return { ...this.current }
  }

  async settled(): Promise<void> {
    await this.outbox.flush()
    await this.outbox.settled()
  }

  tick(): Promise<void> {
    const d = this.current
    if (!d || d.status !== 'armed') return Promise.resolve()
    if (this.deps.now() < d.nextAttemptAt || this.outbox.hasPrefix(`${d.id}:`)) return Promise.resolve()
    const text =
      `[wake_deadline] local wait window ${d.label ? `"${d.label}" ` : ''}expired (armed ${new Date(d.armedAt).toISOString()}, id ${d.id}). ` +
      `${d.message}\nExpiry is NOT completion: reconcile every owned child and watch against durable evidence before acting.`
    this.outbox.enqueue({
      key: `${d.id}:${d.attempts}`,
      text,
      wanted: () => this.current === d && d.status === 'armed',
      accepted: () => {
        d.status = 'delivered'
        this.save()
      },
      failed: (e) => {
        d.attempts += 1
        d.lastError = e
        if (d.attempts >= DEADLINE_MAX_ATTEMPTS) d.status = 'failed'
        else d.nextAttemptAt = this.deps.now() + DEADLINE_RETRY_MS
        this.save()
      },
    })
    void this.outbox.flush()
    return Promise.resolve()
  }

  restore(snapshot: DeadlineSnapshot | undefined): void {
    if (!snapshot || snapshot.version !== 1) return
    this.seq = Math.max(this.seq, snapshot.seq ?? 0)
    const d = snapshot.deadline
    if (!d || typeof d.dueAt !== 'number' || typeof d.id !== 'string') return
    this.current = { ...d }
    // Overdue armed waits fire on the next tick; terminal ones stay terminal.
  }
}
