// watch-wake — cross-session parent-wake for a bare Claude Code CLI session.
//
// The Claude Code port of the Pi extension in ../pi/, and the local equivalent
// of the Pi Web UI Internal API server-side `onFire` wake, which can only prompt
// sessions the server manages.
//
//   parent (this claude session) ── watch_wake_register(child) ──► server watch
//        ▲                                     (pure observer, durable ledger)
//        │ $.prompt.submit(wake)  ◄── $.clock.every poll of GET /watch?sinceIndex=N
//
// `$.prompt.submit` starts a turn of its own once the session is idle, so the
// parent may END its turn and go fully idle: no sleeping, no open turn, no
// tokens while waiting. A busy parent receives the wake when its turn ends.
//
// Also: `wake_deadline`, one model-free local wait-window backstop.
//
// Policy lives in ./core.ts (pure, unit-tested). This file is engine wiring
// only: tools, transport, delivery, persistence, the timer and a status line.

import type { Register } from 'claude-code'
import { canLocalWake, DeadlineCore, Outbox, WatchWakeCore, type ApiResult, type DeadlineSnapshot, type Registration, type WatchSnapshot } from './core.ts'


const TOOL_REGISTER = 'mcp__watch-wake__watch_wake_register'
const TOOL_LIST = 'mcp__watch-wake__watch_wake_list'
const TOOL_CANCEL = 'mcp__watch-wake__watch_wake_cancel'
const TOOL_DEADLINE = 'mcp__watch-wake__wake_deadline'
const TICK_MS = 5000
const STORE_PREFIX = 'session:'
const STORE_RETENTION_MS = 7 * 24 * 3600 * 1000


interface Runtime {
  sessionId: string
  interactive: boolean
  localWake: boolean
  watch: WatchWakeCore
  deadline: DeadlineCore
  ensureTimer: () => void
  refreshNow: () => Promise<void>
  stop: () => void
  outbox: Outbox
  setBusy: (busy: boolean) => void
}

function parse(text: string): any {
  try {
    return text ? JSON.parse(text) : {}
  } catch {
    return { error: text.slice(0, 400) }
  }
}

interface Persisted { updatedAt: number; watch?: WatchSnapshot; deadline?: DeadlineSnapshot }

function renderRegistration(r: Registration): string {
  const lines = [
    `id: ${r.id}`,
    `child_session: ${r.sessionId}`,
    `status: ${r.status}`,
    `wakes_sent: ${r.wakesSent}/${r.maxWakes}`,
    `interval_s: ${r.intervalSeconds}`,
    `ledger_cursor: ${r.sinceIndex}`,
    `generation: ${r.generation ?? 'legacy (no CAS)'}`,
  ]
  if (r.pendingSince) lines.push(`pending_wake_since: ${new Date(r.pendingSince).toISOString()} (held until this session is idle)`)
  if (r.warning) lines.push(`warning: ${r.warning}`)
  if (r.lastError) lines.push(`last_error: ${r.lastError}`)
  return lines.join('\n')
}

function statusLine(watch: WatchWakeCore, deadline: DeadlineCore): string | undefined {
  const watching = watch.list().filter((r) => r.status === 'watching').length
  const d = deadline.status()
  const parts: string[] = []
  if (watching) parts.push(`watching ${watching} child${watching === 1 ? '' : 'ren'}`)
  if (d?.status === 'armed') parts.push(`deadline ${new Date(d.dueAt).toISOString().slice(11, 16)}Z`)
  // The engine already prefixes a plugin's status line with its name.
  return parts.length ? parts.join(' · ') : undefined
}

const IDLE_INSTRUCTION =
  'You may now END your turn and go idle: the wake arrives as a new prompt in this session (it starts a turn once the session is idle; while you are busy it waits for your turn to end). No sleeping or polling needed. ' +
  'Before idling, also arm a backstop for this window (wake_deadline), per the long-horizon-waiting-strategies skill.'

// ─── Registration ───────────────────────────────────────────────────────────
//
// The engine requires `$` to be spelled `$.noun.call(...)` at every call site
// (never stored, passed or returned), so every engine effect below is a
// closure inside the session.start hook; the tool hooks reach them through
// the runtime record. Background work outliving a dispatch is started from
// session.start, as the engine documents.

export const register: Register = (on) => {
  let rt: Runtime | undefined

  const runtime = (): Runtime => {
    if (!rt) throw new Error('watch-wake is not bound to a session yet (session.start has not run in this module environment); restart the session after a redeploy')
    return rt
  }

  on('session.start', async ($, e, next) => {
    const started = await next(e)
    const sessionId = await $.session.id()
    const storeKey = `${STORE_PREFIX}${sessionId}`
    // Engine time, not Date.now(): the host owns the clock (and a test mocks it).
    let nowMs = await $.clock.now()
    const refreshNow = async () => {
      nowMs = await $.clock.now()
    }

    // Transport: token-authenticated Internal API over the Unix socket. The
    // documented Pi Web UI defaults live under $HOME/.pi-web-ui; both the
    // socket path and the token path can be overridden by environment.
    const callApi = async (method: string, path: string, body?: unknown): Promise<ApiResult> => {
      const socketOverride = await $.env.get('PI_WEB_UI_SOCKET')
      const tokenOverride = await $.env.get('PI_WEB_UI_TOKEN_PATH')
      let base = ''
      if (!socketOverride || !tokenOverride) {
        base = (await $.env.get('HOME')) ?? ''
        if (!base) {
          throw new Error(
            'watch-wake needs HOME to locate the Pi Web UI Internal API defaults, or set PI_WEB_UI_SOCKET and PI_WEB_UI_TOKEN_PATH explicitly',
          )
        }
      }
      const socketPath = socketOverride ?? `${base}/.pi-web-ui/internal-api.sock`
      const tokenPath = tokenOverride ?? `${base}/.pi-web-ui/internal-api-token`
      let token: string
      try {
        token = (await $.fs.read(tokenPath)).trim()
      } catch (error) {
        throw new Error(`cannot read Internal API token file ${tokenPath}: ${error instanceof Error ? error.message : String(error)}`)
      }
      if (!token) throw new Error(`Internal API token file is empty: ${tokenPath}`)
      const payload = body === undefined ? undefined : JSON.stringify(body)
      const headers: Record<string, string> = { authorization: `Bearer ${token}` }
      if (payload !== undefined) headers['content-type'] = 'application/json'
      try {
        const res = await $.http.fetch(`http://localhost${path}`, { method, headers, body: payload, socketPath })
        return { status: res.status, json: parse(res.text) }
      } catch (fetchError) {
        // Fallback: curl over the socket. The bearer header travels on stdin
        // (`-H @-`), never in argv, so it cannot leak through the process table.
        const argv = ['curl', '-sS', '--max-time', '30', '--unix-socket', socketPath, '-X', method, '-H', '@-', '-w', '\n%{http_code}']
        if (payload !== undefined) argv.push('-H', 'Content-Type: application/json', '--data-binary', payload)
        argv.push(`http://localhost${path}`)
        const out = await $.process.run(argv, { stdin: `Authorization: Bearer ${token}\n`, timeoutMs: 35_000 })
        if (out.exitCode !== 0) {
          throw new Error(`Internal API ${method} ${path} failed (fetch: ${fetchError instanceof Error ? fetchError.message : String(fetchError)}; curl exit ${out.exitCode}: ${out.stderr.slice(0, 200)})`)
        }
        const cut = out.stdout.lastIndexOf('\n')
        return { status: Number(out.stdout.slice(cut + 1)) || 0, json: parse(out.stdout.slice(0, cut)) }
      }
    }

    // Delivery: a turn of its own once the session is idle; queued behind a
    // running turn. Resolves as that turn starts.
    const deliver = async (text: string): Promise<void> => {
      const res = (await $.prompt.submit({ text })) as { drop?: string } | undefined
      if (res && typeof res === 'object' && 'drop' in res && res.drop) throw new Error(`wake dropped by a prompt.submit hook: ${res.drop}`)
    }

    // Persistence: this plugin's $.store, one key per Claude session id.
    const load = async (): Promise<Persisted | undefined> => {
      const value = await $.store.get(storeKey)
      return value && typeof value === 'object' ? (value as Persisted) : undefined
    }
    let saving = Promise.resolve()
    const save = (patch: Partial<Persisted>): Promise<void> => {
      saving = saving.then(async () => {
        const prev = (await load()) ?? { updatedAt: 0 }
        await $.store.set(storeKey, { ...prev, ...patch, updatedAt: nowMs })
      }).catch(() => undefined)
      return saving
    }
    const prune = async (): Promise<void> => {
      for (const key of await $.store.keys()) {
        if (!key.startsWith(STORE_PREFIX) || key === storeKey) continue
        const v = (await $.store.get(key)) as Persisted | undefined
        const active = v?.watch?.registrations?.some((r) => r.status === 'watching') || v?.deadline?.deadline?.status === 'armed'
        if (!active && (!v?.updatedAt || nowMs - v.updatedAt > STORE_RETENTION_MS)) await $.store.delete(key)
      }
    }

    // One outbox for every wake: held while a main-loop turn runs, re-checked
    // just before sending, and coalesced into one prompt when idle.
    let busy = false
    const outbox = new Outbox({ deliver, isBusy: () => busy })
    const watch = new WatchWakeCore({
      callApi,
      deliver,
      outbox,
      now: () => nowMs,
      persist: (snapshot) => save({ watch: snapshot }),
      notify: (text) => {
        try {
          $.ui.toast(text)
        } catch {
          /* headless */
        }
      },
    })
    const deadline = new DeadlineCore({ now: () => nowMs, deliver, outbox, persist: (snapshot) => save({ deadline: snapshot }) })

    let timer: { cancel: () => void } | undefined
    const showStatus = () => {
      try {
        $.ui.status(statusLine(watch, deadline))
      } catch {
        /* headless: no status line */
      }
    }
    const ensureTimer = () => {
      const active = watch.hasActive() || deadline.isArmed()
      // While an orchestrator is waiting on a wake, this flag lets a host hook
      // (for example a session-capture hook) defer work it would otherwise do
      // at the end of a turn.
      void $.env.set('CLAUDE_WATCH_WAKE_ARMED', active ? '1' : undefined)
      if (active && !timer) {
        timer = $.clock.every(TICK_MS, () => {
          void refreshNow().then(() => Promise.allSettled([watch.tick(), deadline.tick()])).then(() => {
            showStatus()
            if (!watch.hasActive() && !deadline.isArmed() && outbox.size === 0 && timer) {
              timer.cancel()
              timer = undefined
              void $.env.set('CLAUDE_WATCH_WAKE_ARMED', undefined)
            }
          })
        })
      }
      showStatus()
    }
    const stop = () => {
      timer?.cancel()
      timer = undefined
    }

    rt = {
      sessionId,
      interactive: e.isInteractive,
      localWake: canLocalWake({
        interactive: e.isInteractive,
        environmentKind: (await $.env.get('CLAUDE_CODE_ENVIRONMENT_KIND').catch(() => undefined)) ?? undefined,
      }),
      watch,
      deadline,
      ensureTimer,
      refreshNow,
      stop,
      outbox,
      setBusy: (b) => {
        busy = b
      },
    }

    for (const tool of TOOLS) await $.tool.register(tool)

    try {
      const saved = await load()
      if (saved?.watch) {
        const summary = await watch.restore(saved.watch)
        if (summary.resumed || summary.stale) $.ui.log(`watch-wake: restored ${summary.resumed} watch(es), ${summary.stale} stale`)
      }
      if (saved?.deadline) deadline.restore(saved.deadline)
      await prune()
    } catch (error) {
      $.ui.log(`watch-wake: restore failed: ${error instanceof Error ? error.message : String(error)}`)
    }
    ensureTimer()
    return started
  })

  // Busy tracking for the outbox: main-loop turns only (a subagent's turn
  // raises no turn.start and carries agentId on turn.complete).
  on('turn.start', async ($, e, next) => {
    rt?.setBusy(true)
    return next(e)
  })

  on('turn.complete', async ($, e, next) => {
    const result = await next(e)
    if (rt && e.agentId === undefined) {
      rt.setBusy(false)
      void rt.outbox.flush()
    }
    return result
  })

  on('session.end', async ($, e, next) => {
    rt?.stop()
    return next(e)
  })

  // The mod's own tools touch only the local Internal API watch registry and a
  // local timer; they never run commands or edit files. Auto-allow them so an
  // orchestrating parent is not stopped by a permission dialog before idling.
  on('tool.check', async ($, e, next) => {
    if (typeof e.tool === 'string' && e.tool.startsWith('mcp__watch-wake__')) {
      return { decision: 'allow', reason: 'watch-wake mod: own local orchestration tool' }
    }
    return next(e)
  })

  on('tool.call', { tool: TOOL_REGISTER }, async ($, e) => {
    const r = runtime()
    const input = e as unknown as Record<string, unknown>
    if (!r.localWake && input.allow_headless !== true) {
      return {
        deny:
          'This is a non-interactive (-p / SDK) session: it exits or is driven by its host, so a local wake has nowhere to land ' +
          '(interactive CLI and Remote Control sessions are supported). ' +
          'If Pi Web UI manages this session, use the server-side onFire wake instead. Pass allow_headless:true to force.',
      }
    }
    try {
      await r.refreshNow()
      const reg = await r.watch.register(
        {
          sessionId: String(input.session_id ?? ''),
          conditions: Array.isArray(input.conditions) ? (input.conditions as never) : [],
          message: typeof input.message === 'string' ? input.message : '',
          maxWakes: typeof input.max_wakes === 'number' ? input.max_wakes : undefined,
          intervalSeconds: typeof input.interval_seconds === 'number' ? input.interval_seconds : undefined,
          label: typeof input.label === 'string' && input.label ? input.label : undefined,
          replace: input.replace === true,
          fireIfSettled: input.fire_if_settled === true,
        },
        { selfSessionId: r.sessionId },
      )
      r.ensureTimer()
      return { result: ['Watching — this session will be woken when a condition fires.', renderRegistration(reg), IDLE_INSTRUCTION].join('\n') }
    } catch (error) {
      return { deny: `watch_wake_register failed: ${error instanceof Error ? error.message : String(error)}` }
    }
  })

  on('tool.call', { tool: TOOL_LIST }, async () => {
    const r = runtime()
    const regs = r.watch.list()
    const d = r.deadline.status()
    const parts = [regs.length ? regs.map(renderRegistration).join('\n\n') : 'No watch-wake registrations.']
    parts.push(d ? `wake_deadline: ${d.id} ${d.status} due ${new Date(d.dueAt).toISOString()}${d.label ? ` (${d.label})` : ''}` : 'wake_deadline: none')
    return { result: parts.join('\n\n') }
  })

  on('tool.call', { tool: TOOL_CANCEL }, async ($, e) => {
    const r = runtime()
    const id = String((e as unknown as Record<string, unknown>).id ?? '')
    try {
      await r.refreshNow()
      const { registration, remote } = await r.watch.cancel(id)
      r.ensureTimer()
      return { result: `Cancelled ${registration.id} (child ${registration.sessionId}). Remote watch: ${remote}.` }
    } catch (error) {
      return { deny: error instanceof Error ? error.message : String(error) }
    }
  })

  on('tool.call', { tool: TOOL_DEADLINE }, async ($, e) => {
    const r = runtime()
    const input = e as unknown as Record<string, unknown>
    try {
      await r.refreshNow()
      if (input.action === 'arm') {
        const d = r.deadline.arm({
          delaySeconds: Number(input.delay_seconds),
          message: typeof input.message === 'string' ? input.message : '',
          label: typeof input.wait_label === 'string' ? input.wait_label : undefined,
        })
        r.ensureTimer()
        return {
          result:
            `Armed ${d.id}: due ${new Date(d.dueAt).toISOString()} (model-free local timer; persisted per session in the plugin store).` +
            (d.replacedId ? ` Replaced the still-armed ${d.replacedId}.` : ''),
        }
      }
      if (input.action === 'cancel') {
        const d = r.deadline.cancel(String(input.id ?? ''))
        r.ensureTimer()
        return { result: `Deadline ${d.id} is ${d.status}.` }
      }
      const d = r.deadline.status()
      return { result: d ? JSON.stringify(d, null, 2) : 'No deadline armed.' }
    } catch (error) {
      return { deny: error instanceof Error ? error.message : String(error) }
    }
  })
}

// ─── Tool declarations ──────────────────────────────────────────────────────

const conditionSchema = {
  type: 'object',
  properties: {
    id: { type: 'string', description: 'Stable condition id (auto c0, c1... when omitted)' },
    type: { type: 'string', enum: ['event_type', 'tool', 'text', 'deadline'], description: 'event_type (e.g. agent_end) | tool | text | deadline (server-side timer). An event name must go in eventType, never in type.' },
    eventType: { type: 'string', description: 'For event_type: the normalized event type, e.g. agent_end, goal_end' },
    dataMatch: { type: 'object', description: 'For event_type: shallow primitive equality on event data, e.g. {"status":"paused"}' },
    toolName: { type: 'string', description: 'For tool: tool name' },
    phase: { type: 'string', enum: ['start', 'end'], description: 'For tool: phase (default start)' },
    argIncludes: { type: 'string', description: 'For tool: substring required in args/result' },
    contains: { type: 'string', description: 'For text: substring to match' },
    pattern: { type: 'string', description: 'For text: regex source' },
    patternFlags: { type: 'string', description: 'For text: regex flags (default "i")' },
    source: { type: 'string', enum: ['assistant', 'any'], description: 'For text: assistant output (default) or any text' },
    afterSeconds: { type: 'integer', minimum: 1, maximum: 86400, description: 'For deadline: seconds until the server-side timer fires (integer 1..86400)' },
    once: { type: 'boolean', description: 'Fire only on first match (default true)' },
  },
  required: ['type'],
}

const TOOLS = [
  {
    name: 'watch_wake_register',
    description: [
      'Register a durable Pi Web UI Internal API watch on a CHILD session (any runtime) and be woken HERE when it fires — the parent-wake for this bare Claude Code session, which the server-side onFire cannot reach.',
      'The server-side watch is a pure observer; this mod polls its durable ledger locally (no model calls while waiting) and delivers the wake as a new prompt in this session.',
      'After registering you may END your turn and go idle: the wake starts a turn once the session is idle. Arm a wake_deadline backstop for the window too.',
      'Condition choice: event_type agent_end is the safe default (one wake per child turn; early stops to ask fire it too). Text sentinels need the exact string named in the child prompt. Tool conditions use phase end + argIncludes.',
      'Registering REPLACES any existing watch on that child (one watch per session); a foreign/onFire watch is refused unless replace:true.',
      'A wake means "go look", not "done": reconcile the child against receipts/transcript before acting.',
      'Wakes are held while you are busy and delivered together in one prompt when you go idle; cancelling a registration drops its held wake. max_wakes > 1 makes conditions repeatable (once:false).',
    ].join(' '),
    inputSchema: {
      type: 'object',
      properties: {
        session_id: { type: 'string', description: 'The CHILD internal session id (from POST /sessions). Never this session.' },
        conditions: { type: 'array', items: conditionSchema, description: 'Watch conditions (same spec as POST /sessions/:id/watch)' },
        message: { type: 'string', description: 'Wake text. Placeholders: {{sessionId}} {{conditionId}} {{eventType}} {{firedAt}} {{firingCount}}' },
        max_wakes: { type: 'integer', minimum: 1, maximum: 10, description: 'Max wakes from this registration (default 1)' },
        interval_seconds: { type: 'integer', minimum: 5, maximum: 3600, description: 'Ledger poll interval (default 30)' },
        label: { type: 'string', description: 'Optional label suffix for the server-side watch (prefixed watch-wake:)' },
        replace: { type: 'boolean', description: 'Allow replacing an existing watch you own on that child' },
        fire_if_settled: { type: 'boolean', description: 'If the child is already idle with a finished last run, record one immediate firing (needs server features.watchFireIfSettled). Use when re-registering after a stale notice.' },
        allow_headless: { type: 'boolean', description: 'Force registration in a -p/SDK session (normally refused)' },
      },
      required: ['session_id', 'conditions', 'message'],
    },
  },
  {
    name: 'watch_wake_list',
    description: 'List this session\'s watch-wake registrations (child, status, wakes sent, ledger cursor, generation, last error) and the wake_deadline state. "stale" means the server watch vanished, was replaced, or reloaded detached — reconcile and re-register.',
    inputSchema: { type: 'object', properties: {} },
  },
  {
    name: 'watch_wake_cancel',
    description: 'Cancel a watch-wake registration: stops local waking first, then deletes the server-side watch only if its generation is still ours (never a replacement someone else registered). Reports whether deletion was confirmed.',
    inputSchema: { type: 'object', properties: { id: { type: 'string', description: 'Registration id from watch_wake_register' } }, required: ['id'] },
  },
  {
    name: 'wake_deadline',
    description: [
      'One model-free local wait-window backstop for this session: arm | status | cancel.',
      'arm replaces any earlier deadline; when it expires the message is delivered as a new prompt (starting a turn once idle). No model, API or process calls while waiting.',
      'cancel needs the exact current id. Expiry is not completion: reconcile every owned child on delivery.',
      'Survives a session resume (persisted in the plugin store); it cannot fire while no Claude process for this session is running.',
    ].join(' '),
    inputSchema: {
      type: 'object',
      properties: {
        action: { type: 'string', enum: ['arm', 'status', 'cancel'] },
        delay_seconds: { type: 'integer', minimum: 0, maximum: 86400, description: 'For arm' },
        message: { type: 'string', description: 'For arm: what to do on expiry' },
        wait_label: { type: 'string', description: 'For arm: label for this window' },
        id: { type: 'string', description: 'For cancel: the current deadline id' },
      },
      required: ['action'],
    },
  },
]
