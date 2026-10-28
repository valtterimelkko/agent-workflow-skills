# watch-wake — Pi Coding Agent extension

Lets a bare `pi` CLI process be woken when a **Pi Web UI Internal API watch** on a
**different session** (the child) fires. This is the local counterpart of the
server-side `onFire` wake, which can only prompt sessions the server manages.

The shared design, the condition specification, the safety properties and the
step-by-step parent workflow are in [`../README.md`](../README.md). This file
covers the Pi-specific wiring, install and lifecycle.

```
parent (this pi CLI, goes idle)
   │  watch_wake_register(child)
   ▼
server-side durable watch on the child (pure observer, no onFire)
   │  child emits agent_end / tool / text match
   ▼
ledger records the firing  ←── extension polls this cheaply every interval
   │  new firing since baseline
   ▼
busy parent → sendUserMessage(wake, { deliverAs: "steer" })
 idle parent → sendUserMessage(wake, { deliverAs: "followUp", triggerTurn: true })
   ▼
parent receives the news and continues
```

Busy delivery joins the active turn at its next tool boundary. Idle delivery
starts a turn exactly like a background-completion wake. If the active turn ends
between the state check and the steer, the extension falls back **once** to the
idle follow-up path and records that fallback in the session entries.

## Install

Pi discovers extensions from `~/.pi/agent/extensions/`:

```bash
mkdir -p ~/.pi/agent/extensions/watch-wake
cp -r companions/watch-wake/pi/* ~/.pi/agent/extensions/watch-wake/
```

Then reload Pi. The extension directory should contain `index.ts`, `manager.ts`,
`deadline.ts` and `deadline-host.ts`; `index.ts` is the entry point Pi loads, and
the other three are the policy modules it imports (`manager.ts` owns the watch
registrations, `deadline.ts` the model-free deadline, `deadline-host.ts` the tool
wiring for it). Keep the tests outside the installed folder, or in it — Pi ignores
them either way.

## Tools

| Tool | Purpose |
|---|---|
| `watch_wake_register` | Register a durable watch on a **child** session and be woken here when it fires. The child may be any runtime Pi Web UI manages. |
| `watch_wake_list` | List local registrations (child, status, wakes sent, baseline, last error). |
| `watch_wake_cancel` | Delete the server-side watch (releasing its residency claim) and stop waking. |
| `wake_deadline` | Arm/status/cancel one model-free local wait-window backstop; no API child call and no provider call while waiting. |

### Register

```json
{
  "session_id": "<child internal session id>",
  "conditions": [{ "id": "done", "type": "event_type", "eventType": "agent_end" }],
  "message": "Your child {{sessionId}} finished ({{conditionId}}) — inspect and continue.",
  "max_wakes": 1,
  "interval_seconds": 30
}
```

- Conditions use the same generic spec as `POST /api/v1/sessions/:id/watch`
  (`event_type` / `tool` / `text` / `deadline`); `event_type` also accepts the
  server's `dataMatch` object for primitive shallow equality on event data, passed
  through unchanged.
- A proved fresh server generation starts its local cursor at **zero**: events
  that arrive during registration, before the POST acknowledgement, are new-
  generation events and must still wake the parent. Servers without the CAS
  capability retain response-count baselining. A restored registration resumes
  from its persisted `sinceIndex`, so firings recorded while the local host was
  down are consumed rather than skipped.
- Re-registering the same child supersedes the old local handle. The manager keeps
  the opaque `serverGeneration` separate from its own changing local generation
  and from the legacy `createdAt` evidence. Before each mutation the adapter reads
  `/api/v1/capabilities`; `features.watchGenerationPreconditions` enables
  conditional register/delete. A failed or incompatible discovery refuses the
  mutation rather than silently falling back. Restore and poll refuse a different
  server generation or source session instead of adopting it. The current
  factory's session id is authoritative: a persisted source id from a copied or
  forked branch cannot override the current host identity. Legacy records without
  ownership or generation evidence keep weaker compatibility semantics; the
  checks cannot manufacture missing evidence.
- Self-watch rejection uses the current factory's session id, not ambient process
  environment, so an independent SDK host cannot bypass the guard.
- One wake per new firing batch, bounded by `max_wakes` (1–10, default 1). A
  failed delivery (host channel down) does **not** consume the budget; it retries
  on the next poll.
- The server-side watch is registered as a pure observer — the extension never
  sets the server's `onFire` action, so a managed parent and this local parent
  cannot both be woken by accident.

## Lifecycle

- **Busy host**: the timer keeps polling and injects a new firing as
  `deliverAs: "steer"`, so the current turn sees it at the next tool boundary.
- **Idle host**: the same timer injects a follow-up with `triggerTurn: true`. A
  single-flight 5-second tick honours each registration's own cadence (minimum
  5 s), so slow requests cannot overlap and a fast watch does not force every
  watch to poll at the fast cadence. The durable ledger did the waiting.
- **Session switches/restarts**: registrations persist as a session entry and are
  restored on `session_start` by **attaching** to the surviving server watch
  (never re-registering — that would wipe the ledger) from the last consumed
  `sinceIndex`. Cursor, wake budget, cancellation state, local/server generation
  evidence, bounded state-notice accounting and pending remote cleanup are all
  preserved. Cancelled entries restore locally without attaching and therefore
  cannot resurrect.
- **Change-only persistence**: the registration entry is written only when the
  persisted snapshot actually changes — an unchanged poll writes nothing. A stable
  watch on an idle session therefore adds no session-file growth; the earlier
  design appended one identical entry per poll, which grew an idle session file by
  megabytes over a day. The fingerprint is reseeded from the restored state after a
  restart so reconcile does not rewrite it either.
- **Pi Web UI server restart / polling failure**: a detached, missing, replaced or
  repeatedly failing primary watch produces a bounded state notice rather than
  silently disappearing. Restore failures notify during `session_start` even when
  every record becomes stale and no timer starts; one batched notice covers
  concurrent restore failures, and persisted accounting prevents reload storms.
  Terminal cases become `stale`; re-register to resume.
- **Cancellation**: local delivery stops first. On a capable server, DELETE sends
  `{ "expectedGeneration": "<observed token>" }` with an explicit body length.
  Only `success: true` plus the matching returned generation counts as
  `remoteDeleteGenerationConfirmed`. A missing or different acknowledgement is
  explicit ambiguity; a generation mismatch consumes stale deletion authority
  without deleting the replacement. A failed request remains `remote cleanup
  pending`. Legacy-server acknowledgement stays labelled non-CAS; a registration
  that knows it is CAS refuses a capability downgrade. Once DELETE is
  acknowledged, that handle's remote mutation authority is consumed: sequential or
  concurrent repeats reuse the acknowledgement and cannot delete a later external
  replacement. Records retained after a known generation or source-session
  rejection explicitly have no remote-delete authority: cancelling their local
  handle never deletes whatever currently occupies the child's server watch URL.
- **quit/reload/new/resume/fork**: every old factory stops its local timer and
  drops its wake channel. An already-ended factory refuses new registration or
  cancellation mutations. A registration response arriving after shutdown cannot
  restart polling or claim local delivery is active; it reports an ambiguous
  remote result for reconciliation instead of blindly retrying. The server-side
  watch keeps observing until cancelled or the child is deleted.

## Model-free local deadline

Use `wake_deadline` as a bounded backstop alongside the primary child watch:

```json
{ "action": "arm", "delay_seconds": 1500, "message": "Reconcile every child and watch health", "wait_label": "implementation-wave" }
```

`status` reads the current deadline without writing. `cancel` requires the exact
`id` returned by arm/status; a superseded handle cannot cancel a newer wait.
Arming replaces the single active wait. Delay bounds: integer 0–86400 seconds. The
tool respects an already-aborted call and refuses a closed or foreign host.

`deadline-host.ts` connects the tool to `deadline.ts`'s single-session
`DeadlineManager`, using synchronous `appendEntry` for persistence and the same
busy-steer / idle-follow-up channel as watch wakes. The timer itself makes no
model, subprocess or network call; **processing a wake starts or continues an
ordinary model turn**. It never resumes a goal loop and never decides whether a
child succeeded.

The latest `watch-wake-deadline` custom entry is restored session-wide on startup,
before remote watch I/O. This runtime safety state is not branch-rewindable:
reloading an earlier tree position cannot resurrect a later cancelled wait. Forks
have different session ids and cannot inherit the timer. Restore errors are
visible through tool status and next-turn context, not silently ignored.
Active/pending/failed deadline state is included in next-turn context without
extra persistence, including after compaction. Runtime shutdown disposes the
manager without writing a cancellation tombstone.

- One finite deadline (at most 24 hours), fresh identity per arm; replacing or
  cancelling invalidates queued callbacks, so an old callback cannot interfere
  with replacement timer cleanup. A disposed manager cannot mutate persisted
  state.
- Restore validates session identity, interval and retry bounds before replacing
  state; cancelled/delivered/failed records remain terminal. Overdue recovery uses
  the existing bounded delivery-attempt state, never a new semantic task queue.
- Persistence writes only changed records. A synchronous write failure leaves an
  explicitly non-durable in-memory deadline; unsupported thenable persistence
  rejects arming promptly, so persistence adapters must be synchronous.
- Delivery acceptance is not processing and not task completion. A rejection or
  thrown delivery has bounded retries and a visible terminal failure. A crash
  after channel acceptance but before persistence may replay the wake:
  exactly-once delivery is not promised.
- `dispose()` clears timers without persisting a cancellation, permitting
  authorised same-session restoration. A stopped process or blocked event loop
  cannot deliver an in-process timer; independent supervision remains necessary.

## Configuration

| Env var | Default | Purpose |
|---|---|---|
| `PI_WEB_UI_WATCH_WAKE_SOCKET` | `~/.pi-web-ui/internal-api.sock` | Internal API Unix socket |
| `PI_WEB_UI_WATCH_WAKE_TOKEN_FILE` | `~/.pi-web-ui/internal-api-token` | Bearer token file (mode `0600`) |

No secrets live in this repository; the token is read at call time from the file
and never logged.

## Relation to the server-side `onFire` wake

| | Server `onFire` | This extension |
|---|---|---|
| Parent can be | any **managed** session (any runtime) | this bare `pi` CLI process |
| Wake path | `steer` into a busy managed turn, or a receipted turn/follow-up | in-process busy `steer`, idle `followUp` + `triggerTurn` |
| Audit | the server's wake-attempt records | local registration state plus the recorded race fallback |
| Use when | the parent is a Pi Web UI session | the parent is a terminal `pi` CLI |

Both watch the **child**; neither ever prompts the session being watched.

The deterministic server watch id is not an ownership credential. When the server
advertises generation preconditions, registration first reads the existing watch:
absence uses `expectedGeneration: null`, and an existing watch registered by this
session uses its exact observed token. Known foreign ownership or an unexpected
replacement is refused. The server must check that precondition atomically with
the mutation; a client pre-read alone is not CAS.

Servers without the advertised capability retain legacy unconditional mutation
semantics and weaker `createdAt` / source-session evidence, and this extension
does not claim atomicity on those endpoints. A legacy local record meeting a
capable server may acquire its token for cancellation only after creation and
source-session checks; unknown ownership is not permission to delete. Each
successive API call also rechecks that its local host is still open, so a delayed
capability or read response cannot start a fresh mutation after shutdown.

## Tests

```bash
cd companions/watch-wake/pi
node --test tests/*.test.mjs
```

63 tests across five files:

| File | Covers |
|---|---|
| `tests/manager.test.mjs` | register/attach/cancel, condition validation, cursor and budget semantics, stale handling |
| `tests/cas-client.test.mjs` | generation CAS, delete authority, refusal of foreign replacement, restore |
| `tests/deadline.test.mjs` | deadline replacement/cancel races, restore validation, bounded retries, real-timer expiry |
| `tests/deadline-parent.test.mjs` | disposal cannot append into a replacement host; a stale callback cannot hide the new timer |
| `tests/extension-wiring.test.mjs` | `index.ts` wiring asserted as text (steer/followUp paths, no `onFire`, env-only token paths) and persistence dedup |

The tests import the TypeScript sources directly (Node 23.6+ type stripping) and
use fake transports, a fake clock and injected schedulers. Nothing touches a real
socket, a real token or the real home directory.

Behaviour that needs a real Pi host — a registered tool actually driving an idle
expiry through a deterministic local provider, restart/compaction composition —
is a separate integration gate. A source change does not activate already-running
hosts: keep their existing backstop until the extension is separately deployed
and reloaded.

## Part of the Pi Web UI orchestration set

- Pi Web UI — https://github.com/valtterimelkko/pi-web-ui
  (`docs/ORCHESTRATION-OVERVIEW.md`, `docs/INTERNAL-API-ORCHESTRATION.md`)
- pi-orch — https://github.com/valtterimelkko/pi-orch
- the pack — https://github.com/valtterimelkko/agent-workflow-skills/blob/main/packs/pi-web-ui-orchestration-pack/README.md
- the watch-wake companion — [`../README.md`](../README.md)
