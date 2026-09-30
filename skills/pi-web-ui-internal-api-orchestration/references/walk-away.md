<!-- Loaded from SKILL.md §4. Read before dispatching anything you will not sit and watch. -->

Contents: retention (capacity trap) · detached dispatch · **watch-wake** (parent wake; slash-command, bare-CLI-wake and wait-cursor traps) · **fan-in** (parallel children, two delivery traps) · choosing the condition · notifications.

# Set a long task and walk away

Four pieces combine into "dispatch and check back later":

**Retention** keeps the session alive. `durable` preserves recoverability;
`resident` additionally holds a runtime keepalive claim. Leases default to 24h,
cap at 7d, persist through restart, and expire as crash safety. Several clients
may hold different leases on one session — release only the exact lease id held by
your caller. API and watch claims do not consume the Web UI's five-per-runtime human
pin slots, and deleting a watch cannot clear an API or UI claim. Retention is
**not** an execution permit: preflight `/capacity`, but the prompt route remains the final
admission authority.

**Capacity trap — `ADMISSION_CAPACITY_EXHAUSTED` from leaked validation servers.** Disposable
validation runs (`npm run validate:server` / `scripts/validation-server.ts`) can leak background
processes; once the host task limit is exhausted, the admission controller refuses otherwise-idle
turns with `ADMISSION_CAPACITY_EXHAUSTED`. Diagnosis: `GET /capacity` reports
`reason: "pid_pressure"` while sessions and slots look free. Fix: stop only the leaked
validation-server processes (not the service) with your process supervisor, then re-check
`/capacity`.

**Detached dispatch** starts the turn and returns immediately (above).

**Goal-driven children (contract 1.27.0) change the condition choice.** A child
running under a goal (`POST /sessions/:id/goal {"action":"start",…}`) emits
`goal_state` on every transition and `goal_end` on a terminal transition into
`achieved`/`failed`/`cleared`. Reusing a session can clear the OLD goal during
start: filter the exact new objective or retain repeated events and reconcile
identity, rather than consuming a one-shot watcher on the old clear (see
`goals.md`). Prefer `{"type":"event_type","eventType":"goal_end"}`
over `agent_end` for goal-driven children: one wake at the *outcome* instead of
one per continuation turn. Combine with retention as below; on Claude, budget
exhaustion of the auto-continue loop also ends as `goal_end {failed, budget}` —
a real outcome, not silence. Poll `GET /sessions/:id/goal` when you need
progress between events.

**If the PARENT runs under a goal (Pi coding agent only):** do independent work
while it remains; pause before actually idling — `goal` tool, action `pause`, reason `"supervising
<child>"` — otherwise the goal loop keeps the parent busy and the wake starves
against the continuation prompt (see `goals.md` Part 2 for the full lifecycle and
the `NEEDS_USER_INPUT` trap). Resume with the `goal` tool only when the child
is fully settled; resume before the last child settles and the next wake can
starve again.

**Dispatch trap: a prompt starting with `/` never reaches the model.** Sending `/goal …` (or any
slash command) via `POST /sessions/:id/prompt` hits Pi's synchronous extension slash-command
handler: the run returns in ~18 ms with `cessationBasis: "documented_handler_return"` and
**0 LLM turns** — the receipt looks clean and nothing happened. API goal prompts must start
with `Goal: <objective>` (no leading slash).

**Finding the child later** (next day, after a server restart, or when you lost
the id): the registry survives restarts, so `GET /api/v1/sessions?limit=20`
returns your child newest-first even though it is long dead — add
`?since=<dispatch-time>` or `?cwd=` to narrow, and filter client-side on the
`source`/`archived` fields (contract 1.30.0). Children you created stay in the
registry; only retention/assembly-line cleanup removes them. If the "child"
was a direct CLI run of another runtime (claude/cmdc/opencode/agy), it was
never in the registry — use `GET /api/v1/sessions/native?limit=10` to find it
by mtime with its `nativePath`.

**Watch-wake (contract 1.22.0) wakes the parent agent itself** — the piece that
removes the operator from the loop. Notifications ping the human; watch-wake
prompts the session that dispatched the work, so an idle parent orchestrator
continues autonomously when the child finishes. Pattern: **watch the child,
wake the parent** — never watch yourself (an idle session emits no events; a
streaming one would self-continue):

```http
POST /api/v1/sessions/<CHILD_ID>/watch
{
  "conditions": [{ "id": "done", "type": "event_type", "eventType": "agent_end" }],
  "label": "wake-parent",
  "onFire": {
    "type": "prompt",
    "targetSessionId": "<PARENT_ID>",
    "message": "Child {{sessionId}} finished ({{conditionId}}) — inspect and continue."
  }
}
```

- Works cross-runtime in both directions: the child (watch subject) and the
  wake target may each be any managed session — pi, claude, opencode,
  antigravity, **or commandcode** (contract 1.23.0 added Command Code
  subjects; requires a server running ≥ 1.23.0). Live validation has confirmed
  that an antigravity child's `agent_end` can fire the watch and deliver a wake
  turn to an antigravity parent session. A bare-Claude CLI parent
  cannot be an `onFire` **target** — no in-process wake mechanism the server
  can reach — but do not read that as "cannot use watches". It can register and
  read them as an **observer**; see *Bare-CLI parents* below.
- The dispatch is admission-checked and injection-checked. Omitted
  `mode:"follow_up"` remains the default: it queues on a busy Pi parent and
  idle-promotes to a receipted turn. Contract 1.32.0 adds opt-in
  `mode:"steer"`: a busy Pi or SDK-backed Claude parent receives the wake in
  its active turn with no new runId; idle steer promotes to a receipted turn.
  Successful attempts report `deliveryKind` (`turn`, `steer`, or
  `deferred-follow-up`). A busy-parent steer wake holds no execution permit
  and is immune to slot exhaustion (only the emergency memory floor refuses
  it, `503`), so a capacity-full board does not starve wake delivery — but an
  idle-promoted turn is admission-checked like any new turn.
- Policy: `maxWakeups` (default 1) counts dispatched outcomes and permanent
  failures. A transient failure is free and gets one bounded in-memory retry
  after `cooldownSeconds` (default 60). The target is pinned with a
  source-owned `watch-target:` claim so idle eviction cannot kill it before the
  wake. `{{evidence}}` needs `includeEvidence:true` (child-controlled text;
  excluded by default).
- Self-target is a `400`; missing target a `404`. After a server restart an
  `active` watch **rehydrates at boot**: broker subscription, pins and runtime
  observer are restored, and a completion-type watch whose subject settled during
  downtime records a reconciled firing — no re-registration needed. Only
  unresolvable persisted conditions reload `detached` (re-register to resume).
- **Bare-CLI parents** (a terminal process the server cannot prompt): use a
  `watch-wake` extension for your harness (`watch_wake_register/list/cancel` —
  polls the ledger in-process, steers a busy host, and starts an idle host via
  `followUp` + `triggerTurn`) or a `watch-wake` mod for Command Code (parks the
  run in the built-in `sleep` tool and wakes via `queueMessage` follow-up; it
  cannot start a fully idle run — park, don't exit).
- **Bare Claude CLI: a `watch-wake` mod for your harness (primary).**
  `mcp__watch-wake__watch_wake_register` registers the pure-observer watch on
  the child and wakes a fully idle `claude` CLI with a new turn;
  `mcp__watch-wake__wake_deadline` is its backstop. Use the public Internal API
  contract at https://github.com/valtterimelkko/pi-web-ui/blob/master/docs/INTERNAL-API.md
  and `long-horizon-waiting-strategies` for mechanics and recovery limits.
- **Bare Claude CLI fallback: still use the watch as an observer.**
  Without the mod nothing can deliver a wake into a bare Claude CLI, so
  `onFire` is unavailable to it. That is a delivery limit, **not** a reason to
  hand-roll your own liveness logic. Register a pure-observer watch on the child
  (`POST /sessions/:id/watch` with **no** `onFire`), then wait on it with
  `GET /api/v1/watches/wait?ids=<watchId>&timeout=300000&cursor=<lastCursor>`
  (contract 1.26.0) — one held request returns the firing the moment it is
  recorded, `204` on timeout, and the returned `nextCursor` makes replays
  at-least-once across reconnects. Where you cannot hold a connection open,
  `GET /sessions/:id/watch?sinceIndex=N` remains the polled fallback. You get
  the server's own condition evaluation and its durable ledger; the watcher
  supplies only the delivery the server cannot.

  This matters because the alternative is reconstructing "is the child alive?"
  from `lastActivity`, run status and status files — which is subtle, and wrong
  in ways that are not obvious. Orchestrators have done exactly that and written
  several incorrect stuck-detectors before getting it right, having read "bare
  Claude CLI has no path" as meaning the watch system was closed to them. It
  was not; only the push delivery was.

- **Bare Antigravity CLI / IDE: pure-observer watch + exiting background task (`run_command`) + native `schedule` backstop.**
  Bare Antigravity (`agy` CLI or IDE session) cannot be an `onFire` push target directly (its lifecycle hooks in `hooks.json` are synchronous interceptors, not background turn injectors). However, Antigravity has first-class native harness primitives for both sides of the pattern:
  1. **Primary wake (canonical persistent watcher)**: Register a pure-observer watch on the child (`POST /sessions/:id/watch` with **no** `onFire`). Launch your harness's `wait-watch.sh <watchId>` in the background via `run_command` with low `WaitMsBeforeAsync` (for example, `1000` ms). When the child finishes or the condition fires, `wait-watch.sh` exits (`exit 0`), and the harness can deliver a high-priority task-completion notification, reactively waking the parent model at zero token cost.
  2. **Model-free backstop (`schedule` tool)**: Arm a native one-shot timer with `DurationSeconds` (for example, `1800`) and `TimerCondition: <taskId>` (pointing to the watcher task). When the watcher finishes early, the timer automatically self-cancels (`Timer cancelled: early-termination condition met`). If the watcher hangs or crashes, the timer fires at expiration and wakes the parent.
  3. **Zero-token waiting discipline & anti-polling**: Crucially, **end your turn immediately with zero further tool calls**. Never run `tmux capture-pane`, `sleep`, or `manage_task(Action='status')` loops inside your turn. Peeking in-turn burns context, triggers compactions, and wastes quota. Follow your harness's watcher guidance and `long-horizon-waiting-strategies` for recovery.
- **Bare-CLI interactive parent/child wake trap — `deferred-follow-up` that never arrives.** If a
  registered session is *also* live in an interactive CLI (e.g. pi running in a tmux pane), that
  runtime owns the session. A prompt dispatched at it — `POST /sessions/:id/prompt` or an
  `onFire` server-side watch wake — queues in MultiSessionManager as a `deferred-follow-up`
  against an auto-compact-75 ownership conflict ("session is owned by another live runtime") and
  never reaches the interactive terminal reading stdin; the process just sits idle waiting for an
  event. Diagnosis: the run receipt shows `deliveryKind: "deferred-follow-up"` while the
  tmux/terminal pane is idle and no turn appears. Resolution: deliver through the owning runtime —
  type into the pane directly (tmux `send-keys` / paste-buffer) or use the in-process
  `watch-wake` extension, which injects from inside the live host instead of relying on
  server-side delivery.
- **`/watches/wait` cursor discipline on re-arm.** `GET /api/v1/watches/wait?ids=…` returns
  immediately (`waitedMs: 0`) if *any* watch in `ids` has already fired — id matching is
  all-or-nothing. Re-arming the same request without advancing state therefore gives a hot,
  tight polling loop, not a long poll. Always pass `cursor=<nextCursor>` from the previous
  response, or prune already-fired watch ids out of `ids` before waiting again (the Antigravity
  watcher pattern in `long-horizon-waiting-strategies` does both).

**Watch surfacing (contract 1.34.0):** registering a watch with the
`X-Parent-Session` header publishes `watch_registered` onto your session's
event stream, and each wake publishes `watch_fired` (`deliveryKind` included
for `onFire` watches). `/events` and durable watches can observe them like
any other event. The wake rails described here are unchanged.

**Server-side backstop and late registration (contract 1.47.0).** A watch condition
`{"type":"deadline","afterSeconds":N}` (1–86400) fires once after N seconds as
`eventType:"deadline"`, survives restarts (overdue at boot → `reconciled:true`) and works
with `onFire` — the model-free backstop for **managed** parents and for any local watcher.
Register option `fireIfSettled:true` records one `reconciled:true` firing for
`agent_end`/`goal_end` conditions when the child is already idle with a terminal last run —
use it when re-registering after a stale/replaced watch; do not use it on a watch registered
before dispatch of a reused child (its previous run would fire it immediately). Text
conditions (default `source`) match assistant text only and fire once per occurrence since
contract 1.47.1 — before it they matched prompt echoes and re-fired on every later event
(11× in 10 s observed). They still fire when the child merely *mentions* the sentinel in its
own prose ("I'll print X if blocked"), so prefer `goal_end`/`agent_end` or a tool condition
for wakes and keep text sentinels for "print it as a standalone line" escalations.

**Verify the wake and its recovery path.** Every primary wake chain has observed failure modes —
a relay wake that never surfaces or `steer_pending` fan-in suppression
(watches themselves rehydrate `active` after a server restart, with downtime
reconciliation for completions). Contract 1.32.0 removes the old
transient-failure budget burn and adds one bounded retry, but this is not a
persistent scheduler. For waits
that matter, arm one appropriate backstop alongside the primary. A loaded
`wake_deadline` is model-free while waiting; an independent process fallback
remains useful when the host/tool itself is suspect. Neither can promise to
resurrect a dead parent. See **`long-horizon-waiting-strategies`** for selection,
activation checks, cancellation, sizing and re-arm rules.

## Generation-safe watch mutations

Read `features.watchGenerationPreconditions` from live `/capabilities`. The exact
supported fields are `generationField:"generation"`,
`registerField:"expectedGeneration"`, `deleteBodyField:"expectedGeneration"`.
Keep the opaque server generation separate from any local handle/cursor.

- Register with `expectedGeneration:null` to create only if absent, or with the
  exact observed generation to replace an owned watch. Omission is legacy
  unconditional replacement. A GET followed by an unconditional POST is not CAS.
- DELETE can send JSON `{ "expectedGeneration":"<observed token>" }`. Supply
  valid body framing (e.g. Content-Length in a Node HTTP client); do not let an
  unframed body disappear and turn the operation into legacy deletion.
- A stale precondition returns 409 `WATCH_GENERATION_MISMATCH` without changing
  the current ledger/subscriptions/pins. Reconcile ownership, not blind retry.
- A successful conditional DELETE returns `success:true` and the removed
  `generation`; require an exact match before claiming generation-confirmed
  cleanup. Missing/mismatched acknowledgement is ambiguous, not success.
- Generation survives a detached restart; accepted replacement creates a new
  generation. Persisted firing history is not a live observer. Preserve the old
  ledger before an intentional new-phase replacement and reset its cursor.
  A fresh generation can record events before its POST response arrives: consume
  those firings, or begin at cursor zero. Do not mark the returned firingCount
  consumed merely because registration was acknowledged.
- Legacy servers keep weaker semantics. The repaired local extension refuses
  known foreign/replaced watches and capability downgrade for a known CAS
  registration. Do not manufacture atomicity from an old timestamp/watchId.

The canonical full contract lives in Pi Web UI's public
[Internal API documentation](https://github.com/valtterimelkko/pi-web-ui/blob/master/docs/INTERNAL-API.md).
A harness-specific `watch-wake` extension or mod may document its own tool and
lifecycle contract separately. Code delivery and host activation are separate:
capability-gate the server and check the actual local tool schema rather than
assuming source is loaded.

**Fan-in — several children, one parent. Parallel orchestration is supported.**
Run several children at once, give each its own watch
targeting you, and return your turn. Budgets and cooldowns are held **per watch
record**. Contract 1.32.0 deliberately adds one cross-watch backpressure rule:
only one steer dispatch may be pending per target; another is recorded as
`steer_pending` suppression rather than invisibly queued. The Pi `watch-wake`
extension is the same shape: a map of registrations, each with its own child,
baseline and budget, all polled together.

What needs care is *delivery*, not capability. Two traps bite exactly when you
start running children in parallel:

- **One watch per session.** An unconditional `POST /sessions/:id/watch`
  **replaces** the existing watch and its ledger/budget, returning `replaced:true`.
  Generation preconditions fence this mutation when advertised (below), but do
  not make replacement harmless. Never "re-register to refresh" mid-flight.
- **Only one steer may be pending per target.** Child B can fire while child A's
  steer is still being delivered; B's attempt is then recorded as suppressed
  with `reason:"steer_pending"`. This avoids an unbounded hidden queue. Treat any
  wake as a prompt to reconcile every child, not only the child named in it.

Best practice when more than one child reports to you:

- Keep `maxWakeups` at the number of genuine wake outcomes you want. Transient
  failures no longer consume it and receive exactly one bounded retry; do not
  mistake that for a durable retry scheduler.
- **On any wake, reconcile every child** — `GET /runs/:runId` for each, not only
  the one named in the message. A wake means "something changed", never "this
  child, and only this child, finished".
- **Prefer steer-capable parents for wide fan-in**: Pi and SDK-backed Claude can
  accept `mode:"steer"` while busy. Other runtimes still fail busy.
- **Diagnose before blaming the runtime.** `GET /sessions/<child>/watch` carries
  `wakeAttempts[]` with `deliveryKind` or the suppression reason —
  `max_wakeups_reached`, `cooldown`, or `steer_pending`. A parent that "never
  woke" is almost always visible there.
- The Pi `watch-wake` extension is more forgiving on this specific point: a failed
  delivery does **not** consume its budget and retries on the next poll.

Fan-in working is not a reason to fan out. Many homogeneous items still belong in
one durable worker — see **Batch processing** under *Orchestration patterns* in
`SKILL.md`.

**Choosing the condition — what each trigger actually promises.** Agents
register watches themselves, so pick deliberately:

- `{ "type": "event_type", "eventType": "agent_end" }` — **the safe default;
  prefer it.** Fires exactly once per child *turn*: a prompt containing five
  tasks yields one wake, after all five finish. It also fires when the child
  stops early — to ask a question or on error — which is exactly when a parent
  should look. Every runtime emits it, so it is guaranteed; no child
  cooperation required.
- `{ "type": "text", "contains": "SENTINEL" }` — mid-turn wake ("the child is
  blocked while still streaming"). Only as reliable as the child emitting the
  exact string: name the sentinel in the task prompt itself and make it
  machine-checkable ("the moment you cannot proceed, print BLOCKED-NEEDS-INPUT
  as a standalone line"). Matching spans streamed deltas (rolling buffer), ignores
  user/prompt text, and fires once per new occurrence (1.47.1); `once:true`
  (default) stops repeats altogether.
- `{ "type": "tool", "toolName": "Bash", "phase": "end", "argIncludes": "PASS" }`
  — a precise milestone: a specific tool *result* matched, not prose.
- Conditions OR together; each defaults to firing once. For "wake on completion
  OR early escalation", register `agent_end` **and** the sentinel.

Full field reference: the Watch section of
[Internal API documentation](https://github.com/valtterimelkko/pi-web-ui/blob/master/docs/INTERNAL-API.md)
and the [long-horizon validation documentation](https://github.com/valtterimelkko/pi-web-ui/blob/master/docs/LONG-HORIZON-VALIDATION.md).

**Notifications** tell the operator it's done, so nobody has to poll:

```text
POST   $API_BASE/sessions/:id/notifications/opt-in     {"label":"Overnight refactor"}
DELETE $API_BASE/sessions/:id/notifications/opt-in
GET    $API_BASE/sessions/:id/notifications
POST   $API_BASE/notifications                          (explicit emit)
GET    $API_BASE/notifications
GET    $API_BASE/notifications/:notificationId
```

Optional: notify the operator through your harness's own notification path on
its next `agent_end` — which is both "finished" and "stopped to ask a question",
since those are the same event with different content. For milestones from your
own tooling, emit explicitly:

```http
POST /api/v1/notifications
Idempotency-Key: <uuid>
{ "title": "Orchestration", "body": "Review requested", "deepLink": "/?session=abc" }
```

A durable acceptance returns `202` with `Location` and `{notification, duplicate,
statusUrl}`. Reusing the key with the same payload returns the original; reusing
it with a different payload returns `409 IDEMPOTENCY_KEY_CONFLICT`.

Three edges that cause real confusion:

- **`202` is queue acceptance, not channel delivery.** Poll the status URL or
  `GET /notifications` — `pending` can persist while notifications are disabled
  or no channel is configured, and delivery is at-least-once. Never report
  "notified" from the `202` alone.
- **Opt-in is not retroactive.** The manager only reacts to a *live* `agent_end`
  arriving after it attaches. Opt in *before* dispatching, or that turn's
  notification is permanently missed — there is no catch-up.
- **Don't double-notify.** Sessions the operator manages in the Web UI already
  have the `agent_end` path; reserve explicit emits for meaningful milestones,
  blockers, and one final completion.
