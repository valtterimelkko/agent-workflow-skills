---
name: pi-web-ui-internal-api-orchestration
description: "Drive real agent work through Pi Web UI's local Internal API from any directory or harness: run a task on several models and compare, spin up child or sub-agent sessions, split work across runtimes, score or classify batch items with one model, hand a job to another model, start something and check back later, get woken when a child finishes or a condition fires, answer a child agent's question, monitor or clean up running sessions, transfer context between sessions, adopt an existing session as a child, or automate Pi Web UI without the browser. Use it as a parent orchestrator or multi-agent orchestrator managing children, or when the user mentions the Internal API, Unix-socket orchestration, session fan-out, session adoption, runtime comparison, watch-wake, or dispatching by voice. Every child you dispatch must be told to follow the `orchestrated-child-worker` skill, and the waiting discipline is in `long-horizon-waiting-strategies`: use all three together. To prove a change to Pi Web UI itself works, use the Pi Web UI repository's live-validation docs instead."
---

# Pi Web UI Internal API Orchestration

Pi Web UI is a browser interface and backend sitting in front of several agent
runtimes. The part that matters here is that it exposes a **local-only Internal
API over a Unix socket**, which turns it into an orchestration control plane you
can drive from anywhere on the machine — a different repo, a terminal, a script,
a voice assistant — without being inside the web UI at all. Sessions you create
land in the same registry the browser uses, so the operator can open them later.

## Which job do you want?

The two Pi Web UI jobs split on one question: **are you *using* Pi Web UI, or
*testing* it?**

| You are… | Approach | Default target |
|---|---|---|
| Dispatching real agent work — fan-out, comparison, a long task to check back on | **this skill** | the **production** socket |
| Proving a change to Pi Web UI or a runtime actually works | the repository's live-validation docs | a **disposable** server, always |

That distinction decides the safety posture, so get it right before your first
call. Using production here is correct and expected — these sessions are *meant*
to be visible in the operator's Web UI. What is never acceptable is validating a
code change against production, or stopping, restarting, redeploying, or
reconfiguring the Pi Web UI service on your own initiative — the one exception is a
programme whose owner authorised a restart, run by the parent under the protocol in
`references/orchestrator-governance.md`. If the task is "does my change work?",
stop and read the live-validation docs.

## How to read this skill

This is a reference, not a tutorial — read only what the current job needs,
not everything. The usual path: **Connect → Golden rule → Choosing the route**
once, then straight to the numbered step you're on.

This file holds the workflow and the rules that keep you out of trouble. The
reference files hold the field-level detail, organised in three reading tiers:
must-read on every run, must-read when the situation matches, and optional.
**Tier 1 is not advisory** — skipping it before dispatching is the most common
way an orchestration run goes wrong (stale model lists, wrong routes,
exhausted provider quota). Tier 2 rows are mandatory *within* their stated
situation and skippable outside it. Tier 3 is genuinely optional.

**Tier 1 — Must read, every orchestration run (before you dispatch anything):**

| Must-read | Why |
|---|---|
| `long-horizon-waiting-strategies` skill (separate skill) | roughly all Internal API orchestration is long-horizon: the pre-idle checklist, backstop selection, supervision and liveness rules. Read it before your first idle window |
| `orchestrated-child-worker` skill (separate skill) — **you do not follow it, you mandate it** | every child prompt must carry the child directive in §3, for implementers, researchers and reviewers alike. Nothing injects it automatically |
| *Golden rule* section (above), including the **provider quota check** | live capability/capacity/model discovery, plus provider headroom — `/capacity` and `/sessions/usage` are **not** provider quota, and subscription peak windows change the right route |
| `references/routing.md` | **model routing principles — mandatory**: choosing an exact live selector, checking provider quota, reviewer families, and the rules that no longer hold |

**Tier 2 — Must read when the situation matches:**

| Reference | Mandatory when… | What it holds |
|---|---|---|
| `references/pi-orch.md` | **before your first `pi-orch` call in a run**, and before dispatching a programme through it | verbs and flags, goal budget, owner-id convention, `status --owner`, idle vs in-turn waiting, route caps, exit codes |
| `references/adoption.md` | **before adopting any session as a child** — registered or native CLI; includes the operator's CLI-exit confirmation gate | discovery, payloads, responses, errors, post-adoption supervision wiring, worked example |
| `references/claude-code-orchestrator.md` | **MANDATORY when orchestrating from Claude Code** (interactive `claude` CLI, `claude -p`, or a managed Claude session) | Internal API side for Claude parents: which-Claude wake route, dispatch-and-idle with a watch-wake mod, fan-in, `onFire` for managed Claude, Claude-parent routing notes. Wake mechanics, backstops and zero-token discipline: `long-horizon-waiting-strategies/references/claude-code-watch-wake-and-background-watcher.md` |
| `references/antigravity-orchestrator.md` | **MANDATORY when orchestrating from Antigravity CLI / IDE** | Zero-token reactive waiting protocol, persistent wait-watch helper, no-in-turn-polling invariant, milestone notification standards, post-compaction checkpoint anchor |
| `references/orchestrator-governance.md` | **when running several children** — competing priorities, production restarts, or defect handling | autonomous boundaries, defect design & dispatch, single-writer repository staging, restart protocol & recovery, check-in discipline, notifications |
| `references/multi-phase.md` | **before the first child of a multi-wave programme** — dependent phases, shared repositories, concurrent writers, or another agent lineage owning overlapping scope | programme artefacts, wave derivation and dependency kinds, interim waves, design gates, the reviewer child, ownership contracts, correction cycles |
| `references/programme-kit.md` | **with `multi-phase.md`, when you write the programme's files** | copyable templates (checkpoint, common and lane briefs, correction brief), parent verification checklist, worktree and shared-dependency rules, merge order, deploy and restart runbook, close-out |
| `references/walk-away.md` | **before your first detached dispatch** | retention, the watch-wake payload, fan-in under parallelism, every condition type, notification edges, bare-CLI wake paths |
| `references/goals.md` | **before arming a goal** on a child, or dispatching while your own session runs under a goal; also high-value for complex or longer child tasks | goal API, per-runtime honesty matrix, read-back discipline, parent-goal parking |
| `references/evidence.md` | **before declaring a child complete** | the evidence ladder, receipt dispositions, transcript scope traps, the Claude `/events` caveat |
| `references/sessions.md` | binding a model to a session, answering a child's question or permission request, or finding/identifying sessions | control payloads, model-binding verification, request/response shapes, identifier forms |

**Tier 3 — Optional reads:**

| Reference | Open it when |
|---|---|
| `references/patterns.md` | designing a fan-out or batch job, or reporting a run to the operator — background reference, not required |

Where things are in this file:

| If you are… | Read |
|---|---|
| Making your first calls | *Connect from anywhere*, *Golden rule: discover first* |
| Picking runtimes/models/roles for children | *Choosing the route* → `references/routing.md` |
| Planning a programme (dependent lanes, shared repos, other lineages) | *Planning a multi-phase programme* → `references/multi-phase.md` |
| Creating, preparing, dispatching; writing the child brief | §1–§3 (child directive and brief: §3) |
| Dispatching an independent reviewer child | §3c → `references/multi-phase.md` (*The reviewer child*) |
| Dispatching long work and walking away; fan-in of several children | §4 → `references/walk-away.md` |
| Arming goals, or pausing your own goal to supervise | §4b–§4c → `references/goals.md` |
| A child question or approval; finding a session by any id | §5, §7 → `references/sessions.md` |
| Proving a child actually finished | §6 → `references/evidence.md` |
| Adopting an existing session as a child | §8 → `references/adoption.md` (operator CLI-exit gate first) |
| Transfers, usage totals, cleanup | §9 |
| Several children, restarts, defects, notifications | §10 → `references/orchestrator-governance.md` |

**Contract versions.** Feature notes below name the Internal API contract version
that introduced them (for example 1.49.0 for the heap and lag refusals). The
Pi Web UI repository's `docs/INTERNAL-API.md` and
`docs/INTERNAL-API-CONTRACT.md` are the authoritative full reference — open them
when a shape below doesn't answer your question. A deployment can declare a
stability window in which the contract takes bug fixes only; `/capabilities`
reports the served version, and a client such as `pi-orch` warns when its bundled
snapshot is stale.

## Connect from anywhere

**Preferred: the `pi-orch` client** (https://github.com/valtterimelkko/pi-orch —
a thin parent client with no runtime dependencies beyond Node). It builds every
request against a drift-guarded contract snapshot, sends `X-Parent-Session` for you
when it knows your session id, and uses documented exit codes. Its `wait` blocks in
the server's long poll and never polls. Programmes dispatch through it, not through
hand-written curl scripts. **Read `references/pi-orch.md` before your first call**:
verbs, goal budget, owner ids, waiting patterns, route caps, exit codes.

```bash
SID=$(pi-orch spawn --runtime pi --cwd /work/dir --model-selector <live-selector> \
      --thinking low --owner <you> --ttl 3600 --id-only)    # + --goal-objective "…" --goal-budget-tokens N for a goal child
RID=$(pi-orch prompt "$SID" --message "…" --id-only)        # detached, idempotency key built in
pi-orch wait "$SID" --run-id "$RID" --deadline 1800 --json  # in-turn wait only; an idle parent registers a watch and ends its turn (§4)
pi-orch result "$RID" --json                                # final text + parsed completion block
pi-orch verify "$SID" --run-id "$RID" --since <base> [--rerun "npm test"] --json   # check the block's claims
pi-orch status --parent <you> --json; pi-orch cleanup "$SID" --lease <id> --owner <you>
```

Rules worth carrying: a goal child that may run long needs `--goal-budget-tokens` (the
5,000,000 default pauses it mid-run) and a single-line objective; a Claude Code parent
names its children `orch-<programme>-<parentShort8>-<lane>` because it has no lineage;
exit `3` is a deadline (re-wait, never re-dispatch), `18` means reconcile with `status`
before any re-spawn, `25` means the route cap refused the spawn (nothing was created);
the completion block is a claim, so run `verify` before accepting it. Spread a large
wave across routes rather than queueing it on one.

**Fallback: raw requests.** Use them for anything the client does not cover
(adoption, transfers, diagnostics, goal pause and resume), or when `pi-orch` is
unavailable. Nothing here assumes a working directory. The socket and token are
absolute paths, overridable by environment variable so the same snippet works in any
harness:

```bash
SOCKET="${PI_WEB_UI_SOCKET:-$HOME/.pi-web-ui/internal-api.sock}"
TOKEN_PATH="${PI_WEB_UI_TOKEN_PATH:-$HOME/.pi-web-ui/internal-api-token}"
TOKEN="$(cat "$TOKEN_PATH")"
API_BASE="${PI_WEB_UI_API_BASE:-http://localhost/api/v1}"
SELF_ID="${PI_WEB_UI_SESSION_ID:-${PI_SESSION_ID:-}}"   # your own internal id, when you are a managed session

api() {
  curl --silent --show-error --unix-socket "$SOCKET" \
    -H "Authorization: Bearer $TOKEN" \
    -H 'Content-Type: application/json' \
    ${SELF_ID:+-H "X-Parent-Session: $SELF_ID"} \
    "$@"
}
```

When you run inside a Pi Web UI-managed session, `PI_WEB_UI_SESSION_ID` (contract
1.47.0; Pi also keeps `PI_SESSION_ID`) is set automatically, and the runtime also
exposes `PI_WEB_UI_SESSION_ORIGIN` and `PI_WEB_UI_PARENT_SESSION_ID` (OpenCode and the
Claude channel backend get none). From a bare CLI there is no internal id: leave
`SELF_ID` empty and omit the header rather than inventing one. It is optional
identification, not auth.

**Parent linkage (contract 1.34.0):** the `X-Parent-Session` header links the
calls you make to your session, so linkage events (`child_dispatched`,
`child_turn_ended`, `watch_registered`, `watch_fired`) are published to your
session's event stream and are watchable like any other event. Linked
children persist `parentSessionId`; `GET /sessions/:id` gains an additive
`children` list. Unresolvable values are ignored. A session that already
exists — created earlier without linkage, or a native CLI session on disk —
can be linked under you after the fact instead of re-created; see §8 and
`references/adoption.md`.

Confirm Pi Web UI is actually present before planning anything:

```bash
ls -l "$SOCKET" "$TOKEN_PATH"
```

Auth is `Authorization: Bearer <token>` over the socket. This is a **trusted
same-host surface, not an RBAC boundary**: any token holder can inspect and
control every session. So be explicit with the operator about target, runtime,
model, thinking level, session count, retention, and likely side effects before
acting, and never delete, abort, transfer, or repurpose sessions your
orchestration does not own.

The repository also ships an experimental seven-tool stdio MCP adapter, but it is
**retained and disabled**. Do not try to route through it; use the socket.

## Golden rule: discover first, every time

Ask the server what exists right now. Machines differ, backends change, and
model lists are live.

```text
GET $API_BASE/capabilities
GET $API_BASE/capacity
GET $API_BASE/models
```

- **`/capabilities`** — verify `contract.name` is `pi-web-ui-internal-api` and
  check `contract.majorVersion`. Capability-gate optional features rather than
  assuming them. **The runtime feature flags are per-runtime, nested under
  `runtimes.<runtime>`** (not top-level): read `supportsFollowUp`,
  `followUpSemantics`, `supportsSteer`, `supportsSteerWhileBusy`,
  `supportsThinkingLevel`, `supportsApprovals`,
  `supportsInteractiveQuestions`, `supportsReplayHistory` from the entry of the
  specific runtime you plan to use.
- **`/capacity`** — a preflight, not a reservation. Prompt admission is
  rechecked at dispatch and can still return `429 ADMISSION_CAPACITY_EXHAUSTED`
  for slot/runtime limits, or `503` for resource pressure, with `Retry-After`.
  Resource refusals include `heap_pressure` and `event_loop_lag` (1.49.0; `/capacity`
  shows `heap` and `eventLoopLag`), and `503 SERVER_DRAINING` while a deploy drains
  (1.51.0). Treat any `429`/`503` with `Retry-After` as "wait and retry" (a drain ends
  in a restart: re-check `/capabilities` afterwards), and never read the wire
  contract's code list as closed.
  An `event_loop_lag` refusal usually means the **host** is overloaded (another agent's
  build or benchmark), not that your request is wrong: `pi-orch` waits out `Retry-After`
  for you; raw callers must too. Heavy work of your own belongs under `nice` and a capped
  scope, so it cannot starve the server's single event loop: on systemd,
  `systemd-run --scope -p CPUQuota=… -p MemoryMax=… -- nice -n 10 <cmd>` (put `nice`
  inside the scope; `-p Nice=10` is rejected by `systemd-run`).
  Read actual tasks, reservations and the limiting reason—not just the nominal
  turn ceiling. Admission permits are not a complete count of browser/native
  work or autonomous goal continuations; separate request receipts can also
  refer to one executing turn.
- **`/models`** — choose exactly one live-advertised entry. Read its `id`,
  `provider`, `thinkingLevels`, and for Claude profiles `backend` and
  `claudeModel`. A missing field is *unknown*, not permission to fill it in from
  memory. Profile ids are opaque strings; since contract 1.25.0 both
  `/models` profile entries and `/capabilities.claudeProfiles` carry the same
  underlying alias in `claudeModel` / `model`. After creating a session with an
  explicit model, trust only the create response's `resolvedModel` /
  `modelBinding` fields (contract ≥ 1.25.0) or a follow-up `/info` read-back —
  never assume the echo means the binding happened.
- **Watch mutation capability** — `features.watchGenerationPreconditions`, when
  present with the documented field names, enables opaque-generation conditional
  register/delete. Use observed tokens and exact ownership; absence means legacy
  non-CAS semantics, not permission to claim atomic deletion. See `walk-away.md`.
- **Provider quota** — `/capacity` is Pi Web UI's local admission capacity and
  `/sessions/usage` is our own recorded consumption; neither is the provider's
  remaining subscription quota. Check that before choosing a route: read the
  provider's remaining quota in its own dashboard or CLI (a zero-model-token,
  read-only check), including per-provider windows, resets, shared pools, and any
  peak-window flag. This is the authoritative, zero-token pre-dispatch check.

**Read `enabled` as well as `available`.** Since contract 1.15.0 they mean
different things: `enabled: false` is an operator-disabled runtime, which is not
the same as uninstalled or unhealthy. Treat disabled as unavailable and never
silently substitute another runtime.

**There are five runtime families, not four**: `pi`, `claude`, `opencode`,
`antigravity`, and the feature-gated `commandcode`. Don't hard-code the old
four-runtime assumption.

**Provider policy** — on contract 1.16.0+,
`capabilities.features.piProviderPolicy.blockedProviders` lists Pi providers
barred from automation to prevent accidental metered spend. Operators can block
exact provider ids via `INTERNAL_API_BLOCKED_PI_PROVIDERS`, and a non-empty
deployment rejects blocked providers with `403 PROVIDER_NOT_ALLOWED`. Don't guess
around an omitted model on deployments that do omit them. Being served is **not**
being authorised: pay-as-you-go providers (metered API keys, gateway catalogues)
need the operator's direct authorisation before any use — see
`references/routing.md`. Subscription-backed providers are distinct from metered
direct providers and are never covered by this policy.

**If a model you expect is missing**, refresh the catalogue rather than
improvising: `POST $API_BASE/models/refresh` with `{"runtime":"pi"}` (refreshes
the OpenRouter catalogue and returns an ids diff) or the default/`"opencode"`
mode (warms the models.dev cache and recycles the idle backend). It returns
public ids and metadata only, never credentials.

Never use a remembered model list, a family-name match, a coarse `reasoning`
flag, a stale contract version, or a guessed fallback. If the exact combination
you need is absent, stop and report why.

---

# Choosing the route

Treat a dispatch route as the complete tuple:

```text
runtime + selector/id + provider + profile/backend/Claude-model (when used)
        + advertised thinking or discovered native effort + invocation role
```

Names are **not** selectors. Immediately before real dispatch, get one fresh
`/models` response, filter the named runtime list, and select exactly one entry
satisfying every predicate; use its returned `selector` (since contract 1.26.0
every entry carries one — the exact string `POST /sessions` accepts, so copy it
rather than constructing `provider/id` yourself). Zero matches, multiple
matches, a missing required field, or an absent required level is a **refusal** —
never a reason to take the first similar entry or another backend. Keep the
matched metadata with the dispatch record.

**→ `references/routing.md`** carries the general principles: choosing from live
metadata, checking provider headroom before dispatch, using a different model
family for reviewers, asserting the served model, and the hard exclusions
(metered providers without authorisation, disabled or suspended backends). Read
it before choosing a model.

---

# Planning a multi-phase programme

Most runs are one wave — dispatch, watch, fan in, done — and §1–§9 below cover
that. When the work is a **programme** (a sequence of dependent improvements
over multiple waves, often in shared repos alongside other active agents),
plan the organisation *before* the first dispatch. Parents fail at the
joins between waves, not inside them. Three rules carry the shape:

- **Write the programme into three durable artefacts** that survive parent
  compaction and restarts: a stable **strategy document** (scope, waves,
  ownership, gates; owner-gated status header `PLANNING ONLY` → `READY` →
  `EXECUTING`; amendments recorded in place; records scope, not completion),
  a mutable **live checkpoint** re-read before acting (per-child status,
  receipts, wake-delivery ids, next sequence, honest counters), and a
  **per-child brief + evidence directory** (bounded outcome, owned paths,
  handback format with a FROZEN marker).
- **Brief every child with a bounded, self-contained packet:** frozen success criteria,
  bounded files, exact test commands and guardrails, rather than dumping repo context.
  A child that already holds its context should not re-query or loop.
- **Give every concurrent child an isolated git worktree** with disjoint owned paths;
  the child announces its owned paths (and what it leaves to others) in its
  coordination directory (§3b).
- **Derive waves from the sequence, not from available children**: a
  parent-owned bootstrap wave first when the supervision machinery itself is
  suspect; parallel children only on disjoint owned paths; later phases gated
  on earlier interface stability or another lineage's work landing (postpone
  the seam, don't block); a fresh read-only **reviewer child after each lane** (§3c),
  not only at the end, and a named **reviewer live re-run lane** before the wave closes;
  code/test/deployment reported separately. Declare
  dependencies by what a step needs (interface, data, deploy order), and put a
  **design gate** in the brief of any behaviour-critical lane.
- **Acceptance is a verdict, not a receipt**: the parent independently re-runs
  verifiers and writes its own probes; every defect returns with RED evidence
  as one bounded correction brief; accepted phases freeze.

**→ `references/multi-phase.md`** has the full pattern: the programme trigger
table, the three artefacts in detail, wave derivation, ownership contracts for
concurrent writers, correction cycles, and cross-wave supervision;
**`references/programme-kit.md`** has the templates and runbooks to copy. **Read it
before dispatching the first child of anything longer than one wave.**

---

# The orchestration loop

## 1. Create sessions

`POST /sessions` for one child, `POST /sessions/batch` for several. For anything
long-lived, ask for retention **atomically at creation** so a failure can't leave
an orphan:

```json
{
  "runtime": "claude",
  "model": "profile:<discovery-resolved-id>",   // SDK profiles only, see below
  "thinkingLevel": "max",
  "cwd": "/approved/working/directory",
  "retention": { "mode": "durable", "ttlSeconds": 3600, "ownerId": "<unique-owner>" }
}
```

**Claude on the Internal API is SDK-only** (contract 1.46.0): `/models?runtime=claude`
lists only SDK profiles, and a create or prompt through any other Claude backend fails
`403 CLAUDE_BACKEND_NOT_ALLOWED` (`features.claudeBackendPolicy` in `/capabilities`; it
also covers watch wake, goal dispatch and batch). Take the exact `profile:<id>` from the
live `/models` entry and do not construct one.

Prefer a single create when atomic retention matters — batch creation does not
guarantee leases. Record at minimum the canonical `sessionId`, the exact route
tuple, the invocation role, your `ownerId`, the returned `retention.leaseId`, and
your own orchestration id. Since contract 1.34.0 the create response echoes
`parentSessionId` when you identified yourself via `X-Parent-Session`, and
`GET /sessions/:id` lists linked `children`. Since 1.54.0 every create also records
`parentSource` (`header` | `body` | `bash` | `peer`): without the header the server
resolves the calling session from socket peer credentials, fails closed (no link)
on any ambiguity, and costs a slower create, so still send `X-Parent-Session`
whenever you have an id. `GET /sessions?parent=<id>` lists a parent's children
(404 for an unknown parent). There is still no `orchestrationId`, so keep your own
tree record too.

**Create into a directory that exists** (1.53.0): every create checks the effective
`cwd` (exists, is a directory, writable) and refuses `400 PREFLIGHT_FAILED` with a
`failures[]` list before any model token is spent, so make the child's worktree
first. Add `"preflight": {"paths": [...], "tools": [...]}` (absolute paths, bare tool
names; also accepted on `POST /sessions/:id/prompt`) for the files and tools the
brief depends on: a bad workspace then fails in one cheap round trip instead of
43% of children discovering it mid-task. Batch create answers `200` with
per-entry `PREFLIGHT_FAILED`. Treat it as fix-then-resend, never blind retry.

**The create response's model echo is not proof of binding.** Verify the
effective, provider-qualified model via `/info` (and for Pi, the last
`model_change` entry on disk) before spending a long run — a silent rebind to a
3× costlier model has happened with a correct-looking echo.
**→ `references/sessions.md`** (Model binding) has the verification reads, the
Claude-profile rules, and the observed failure shape.

**Bindings are durable (contract 1.33.0) — the run receipt is authoritative.** After
dispatch read `servedModel` and `modelRebound` on the receipt; a binding that cannot be
applied fails loudly (`MODEL_NOT_APPLIED` / `PROVIDER_NOT_ALLOWED`). Never re-verify by
hand-scraping child session files during a run (`references/sessions.md`).

## 2. Prepare, if needed

Model, thinking-level and effort switches, and retention leases, go through
`POST /sessions/:id/control` (`set_model`, `set_thinking_level`, `set_effort`,
`acquire/renew/release_retention`). Thinking levels are capability-gated; for
Pi the response `level` is the *effective* read-back after SDK clamping, not an
echo. `set_effort` is the **Command Code** axis — idle-only, next-turn, never
changes `thinkingLevel` (models with no adjustable effort take no effort
request). For Claude, pick the backend/provider profile **at session creation**
rather than switching later; backend comparisons are cleaner as one session per
profile.

**→ `references/sessions.md`** (Control actions) has the exact action payloads.

## 3. Dispatch

`POST /sessions/:id/prompt`, `POST /sessions/batch/prompt`.

| Field | Notes |
|---|---|
| `message` | required |
| `verbosity` | `answers` (default, non-streaming, final text only), `tasks` (SSE status headlines), `full` (SSE everything) |
| `mode` | `prompt`, `follow_up`, or `steer` — see below |
| `detach` | fire-and-forget; **only valid with `verbosity=answers`**, otherwise `400` |
| `idempotencyKey` | session-scoped, 1–128 chars. A matching retry reuses the run; a different payload on a live key returns `IDEMPOTENCY_KEY_CONFLICT` |
| `requireActiveTurn` | for `follow_up`, forbid idle promotion |

**Modes** — this is how you redirect a child that's already working, and it's
easy to miss:

| Mode | Meaning | Pi | Claude | OpenCode / Antigravity |
|---|---|---|---|---|
| `prompt` | start a new turn | `409 SESSION_BUSY` if busy. From 1.45.0: a swallowed prompt (extension input-hook swallow / fence) fails fast as `PROMPT_NOT_EXECUTED` after a 2 s grace; a session whose lease a **live foreign runtime** holds refuses up front as `409 SESSION_OWNED_BY_OTHER_RUNTIME` (`ownerPid`/`ownerMode`, no run created); a dead owner is auto-recovered (dispose→rehydrate, pins kept) before dispatch | `409 SESSION_BUSY` if running | `409 SESSION_BUSY` if running |
| `follow_up` | deliver after the current turn | busy with a live turn → queued (receipt `queued`); idle → **promoted** to a new turn with `dispatchMode:"prompt"`; busy with **no** live turn (auto-compaction) → `409 SESSION_BUSY` + `Retry-After` (1.57.0). Pi "busy" (1.57.0) = manager busy/streaming, or `sdkStreaming`, or compacting: the same predicate drives `prompt` refusals, `busy` on `GET /sessions/:id`, and watch settlement | no queue: running → `409 SESSION_BUSY` + `Retry-After`; idle → new turn | OpenCode: same as Claude. Antigravity (contract 1.37.0): busy → **queued** — the write goes into the live agy stdin stream and runs as the next turn |
| `steer` | join the active turn | requires an active turn; idle → `409 SESSION_NOT_STREAMING` | SDK backend only (`backendMode:"sdk"`, contract 1.29.0): delivered at the next tool boundary without interrupting; the receipt completes when the joined turn ends and the response carries the continuation text. Idle → `409 SESSION_NOT_STREAMING`; non-SDK backends → `UNSUPPORTED_OPERATION` | OpenCode → `UNSUPPORTED_OPERATION`; Antigravity → `409 SESSION_BUSY` (no mid-run join in the agy stdin protocol — use `follow_up`, which queues natively) |

Every successful response and receipt carries `dispatchMode`, the operation
*actually* performed, alongside the requested `mode`. `requireActiveTurn: true`
turns idle promotion into `409 SESSION_NOT_STREAMING` everywhere. Capability-gate
the differences with `followUpSemantics` and `supportsSteerWhileBusy` — steering
is a Pi capability and, since contract 1.29.0, a Claude SDK-backend capability
(`runtimes.claude.supportsSteer`).

A busy `steer` is not admission-checked (it joins an existing turn), so steering
a busy parent works even when every slot is full; new turns can still get `429`/`503`
with `Retry-After` — detail in `references/sessions.md` (*Dispatch modes and admission*).

Persist the returned `runId` before doing more work.

**For anything that may outlive your connection, use detached dispatch.** An
attached owner `tasks`/`full` stream disconnect *cancels* its run; use
`verbosity=answers` with `detach:true` for disconnect-safe execution.
A separate `/events` observer is not the execution owner. Repaired SSE helpers
close slow/oversized responses at their buffer limit, so streaming is not a
substitute for durable receipts:

```text
POST /sessions/:id/prompt  {"message":"…","verbosity":"answers","detach":true}   → 202 + runId
GET  /runs/:runId
```

Large or slow fan-outs should prefer detached individual prompts, because
`batch/prompt` holds answer bodies until its response completes.

**Mandatory child skill requirement.** The `orchestrated-child-worker` skill is
**not** injected into API-created sessions by any harness; only your prompt delivers
it. Every child prompt, for implementers, researchers and reviewers alike, must carry
this directive. Without it a worker drifts into narrative, omits command exit
statuses, ignores exclusions and self-signs-off:

> "You are dispatched as an orchestrated child worker. You MUST load and strictly follow the `orchestrated-child-worker` skill. Your session ID is `<sessionId>`. Work strictly inside execution worktree `<cwd>`. Owned paths: `<paths>`. Negative exclusions: `<paths>`. Hand-back directory: `<dir>`. Success criteria are frozen. Announce your task (a one-line note in the hand-back directory) before editing files, and leave a note when you finish. <Push / do not push.> Hand back by ending your turn only when your own commands have finished; never wait or poll."

Put the directive **in the prompt itself**, not only in a brief file it points to, and restate
it inside a goal objective ("follow `orchestrated-child-worker`; mark the goal achieved and end") —
goal-engine dispatches that dropped it produced most of the unmandated children in an
audit of 241 child sessions. The rest of a good brief (each item traces to a
recurring failure in that audit):

- **Its own worktree** for every concurrent child — never two children in one main checkout.
- **Push stance.** Say whether the child may push. Lane branches are often never pushed
  (children commit only; the parent merges) — state the rule anyway.
- **The long commands and how to run them** (foreground with a timeout), and that a child
  must not end its turn while its own job runs — or must start the message `NOT FINISHED:`.
- **The RED method**: test first; no `git stash` (its stack is shared across worktrees).
- **Restarts stay with you**: never delegate a restart of the service that hosts the child.
- **Read-only roles**: say "no edits, no stash, no capture"; add "no lookups" only for a genuine fresh-reader or blind test.
- **A budget for research children** (time or tool calls), a checkpoint cadence and a
  hand-back milestone — unbounded research children ran for thousands of tool calls.
- **An end-of-task report block** (contract 1.58.0), so the server captures the child's
  claims (§6). `pi-orch` appends it for you (for a goal child also the `Status:` marker and
  field-shape instructions); paste it by hand only for raw dispatch, verbatim inside this
  four-backtick fence:

  ````text
  END-OF-TASK REPORT (required): the LAST thing in your final answer must be exactly this kind of fenced block (info string `completion`, JSON body):

  ```completion
  {"schema":"pi-completion/v1","status":"done","summary":"<one line>","commands":[{"command":"<a command you ran>","exitCode":0}],"filesChanged":["<path>"]}
  ```

  Fill in the real values; add "tests", "commits", "openIssues" or "blockedReason" fields only if they apply. Do not end your turn with only a tool call: after your final tool call, always write a short final answer that ends with the report block. Nothing after the closing fence.
  ````

  **Completion-block shape** (learned from a live proof where two blocks were rejected or mis-verified): `commands` entries are `{command, exitCode}` objects; `commits` entries are `{sha, repo, subject?}` (sha is 7–64 hex chars; `repo` is an absolute path); `filesChanged` entries are paths **relative to a claimed repo** — coordination or hand-back files outside the work tree are not part of the claim and should be omitted. A malformed block is still parsed to a typed `completionError` (`fieldPath` names the first bad field), so a rejected block costs one reporting follow-up, not a re-run.
- **Live proofs in the child's own disposable server** copy only the credential of
  the approved route into the isolated agent directory, count `models.json` entries
  that carry `apiKey` as credential copies and delete every copy afterwards, name the
  child route explicitly in any inner brief, and assert the served model by script. A
  parent with a full credential copy can silently pick a different model for its children.
- **Host rules the brief must carry** (binding wording in `programme-kit.md`, common
  brief): disposable servers started without the inherited production placement or
  tool-root variables; heavy commands in a `systemd-run --scope` with a hard
  `MemoryMax`; changed-file lint against the lane base; never touch the main checkout.
  The child-side form is `orchestrated-child-worker` §3 and §7.
- Templates for all of this: `references/programme-kit.md`.

For a read-only reviewer, replace the owned-paths, exclusions and push sentences with "You are a read-only reviewer: do not edit, commit, stash or push, and leave the tree untouched; numbered answer and correction files amend the brief", and add the verdict format (§3c), to be returned in the review file and the final message. The harness already delivers the identity packet and scope warnings to the child, so the brief need not restate them.

### 3b. Task announcement ownership: parent vs child

**The child owns runtime presence; the parent defines boundaries and lineage.**

- **The child announces**, from inside its worktree, with owned paths and, optionally, what it leaves to others:
  a one-line note in the coordination directory (for example `00-declared.md`).
  Where the parent's environment provides a shared task surface, use it as well.
  On finishing or blocking the child adds a closing note before handing back.
- **The parent:**
  1. Defines the worktree, owned paths, exclusions and frozen criteria in the brief, mandating the child skill.
  2. Passes the child its `sessionId` (from `POST /sessions`).
  3. Records its own dispatch lineage for the child where its environment supports it
     (the `X-Parent-Session` header / `parentSessionId` is the API-level link).
  4. Closes its record of the child if it crashed, timed out or aborted without a closing note.

### 3c. Reviewer child: a fresh, independent read-only session

After an implementer hands back, and before you accept or merge, dispatch a **fresh**
session to review the change. Fresh context is the point: the implementer's history, and
yours, are polluted by the path taken, while a new session sees only the diff, the brief
and the evidence. Run one per lane and again after each correction; it is not only a last wave.

- **Route (a role, not a model):** one of the recommended worker models, on a **different model family from the implementer**, at the highest thinking level it advertises, never a metered provider without direct authorisation, respecting disabled/suspended backends — rules in `references/routing.md` *Reviewer route*. Check provider quota first and confirm `fallbackApplied:false` on create.
- **Create** with `cwd` = the implementer's worktree and durable retention (`ttlSeconds` sized for the wait, `ownerId:"<prog>-<lane>-reviewer"`; a Claude Code parent uses the `orch-<prog>-<parentShort8>-<lane>-reviewer` convention, `references/pi-orch.md`), dispatch detached, watch `agent_end` with `max_wakes` headroom (each auto-compaction also fires an `agent_end`).
- **Read-only is enforced by the brief only.** Check `git status` is clean afterwards.
- **The verdict is evidence, not sign-off.** You still re-run gates and adjudicate; a defect goes back to the same implementer as a bounded correction, and the same reviewer closes the previous findings.

Cap: one full review, one closure round on the same reviewer, then a final parent-verified correction (no round 3). Brief contents, the verdict format, the closure loop and the compaction gotchas are in `references/multi-phase.md` (Review wave). For several parallel critiques of one draft, use `references/patterns.md` (Reviewer fan-out) instead.

## 4. Set a long task and walk away

Four pieces combine into "dispatch and check back later": **retention** keeps the
session alive, **detached dispatch** starts the turn and returns, **watch-wake**
prompts *you* when the child finishes, and **notifications** ping the human.

**Who are you? Decide this BEFORE any detached dispatch.** Only a *managed* session
(one Pi Web UI created) can be an `onFire` target. A **bare CLI process cannot be
prompted by the server**: a server-side `onFire` armed for it — by you, a script, curl
or a repo dispatcher helper — sits undelivered while you idle. A server-side watch
existing is not a wake being deliverable. Before ending your turn, name the exact tool
call that delivers each wake into this session.

| You are | Wake delivery (plus one model-free backstop) | Playbook |
|---|---|---|
| Managed session, any runtime | server `onFire` on the child targeting your `$PI_WEB_UI_SESSION_ID`, plus a `deadline` condition | `references/walk-away.md` |
| Bare **Pi** CLI | `watch_wake_register` from *this* session + `wake_deadline`; if the tool is unavailable/broken, an owned pure-observer ledger plus a bounded in-harness relay whose **process exit** wakes you (record its actual delivery id; a raw server watch never counts as local delivery) | `long-horizon-waiting-strategies` |
| Bare **Claude Code** CLI | the `watch-wake` mod: `mcp__watch-wake__watch_wake_register` + `wake_deadline` (wakes a fully idle CLI); an exiting background watcher only as fallback | `references/claude-code-orchestrator.md` |
| **Antigravity** `agy` / IDE | `scripts/wait-watch.sh <watchId>` via `run_command` + native `schedule` backstop | `references/antigravity-orchestrator.md` |
| **Command Code** | its watch-wake mod (parks in `sleep`; cannot start an idle run) | `references/walk-away.md` (Bare-CLI parents) |
| `claude -p` / one-shot | cannot wait: hand back instead | — |

The rules worth carrying in your head:

- **Watch the child, wake the parent.** Register the watch on the child with an
  `onFire` action targeting your own session, then return your turn. Never watch
  yourself — an idle session emits no events.
- **Command-shaped work is not child work.** Long shell jobs (test suites,
  builds, watchers, validation scripts) run natively in a harness that provides
  background commands (a background-shell extension or the harness's
  `run_in_background` mechanism): launch, end your turn, and the completion
  wake carries the exit code and output tail — no child session, no watch, no
  tokens while waiting. That is **for you, the parent**: a *child* that ends its turn
  on its own background job wakes you with a false hand-back, which is why children run
  long commands in the foreground (`orchestrated-child-worker` §2). Reserve child dispatch and watch-wake for work that
  needs another model context; cross-runtime waiting rules are unchanged.
- **Bare-CLI parent ⇒ local delivery is mandatory** (table above), then one
  appropriate backstop per `long-horizon-waiting-strategies` **before** idling:
  the loaded `wake_deadline` on a healthy host, an independent fallback when the
  host/tool itself is suspect. Repo scripts that arm their own server-side
  watches serve audit/durability — they do not count toward your wake.
- **`event_type: agent_end` is the default condition.** One wake per child turn,
  and it also fires when the child stops early to ask, which is exactly when you
  should look.
- **Parallel children are supported.** Wake budgets are per watch record, so N
  children give N independent budgets with no cross-child suppression.
- **Two fan-in rules (contract 1.32.0+)**: one watch per session
  (re-registering explicitly returns `replaced:true` and starts a new ledger), and
  only one steer may be pending per target. Use `mode:'steer'` for a busy
  Pi/Claude SDK parent and reconcile every child on any wake; additional
  concurrent steers are recorded as `steer_pending` suppression. Transient
  delivery failures do not consume budget and get one bounded retry.
- **Never poll in-turn.** Holding your turn open to watch a child is the failure
  this whole section exists to remove. That includes a foreground `pi-orch wait`: it is
  for scripts and in-turn waits; an idle parent registers a watch and ends its turn
  (`references/pi-orch.md`, *Waiting*).
- **`202` is queue acceptance, not delivery.** Never report "notified" from it.

**→ `references/walk-away.md`** has the full detail: retention modes and lease
ownership, the watch-wake payload and its cross-runtime matrix, the fan-in
best-practice list, bare-CLI wake paths, every condition type with what it
actually promises, and the notification edges. **Read it before your first
detached dispatch.**

## 4b. Goal-driven children (contract 1.27.0)

A **goal** is a durable objective that survives compaction on every supported runtime —
the strongest primitive for long-horizon children, and protection against ambient traffic
that *sounds* like a session ending (a plain-prompt probe child once stopped mid-task to
obey an automated capture request). Arm one for work that must outlive a context window or
must not be derailed; use a plain prompt for bounded single-turn tasks. **Write the aim,
not the method**: what must be true, the evidence that settles it, where the record lives,
the invariants. Arm via `POST|GET /api/v1/sessions/:id/goal` or atomically at create; watch
terminal `goal_end` (filter a reused session's old-goal clear by the exact new objective),
not per-run `agent_end`. A `start` receipt is **not** completion. The objective must be a
**single line** (the API rejects newlines), and a goal that may run long needs an explicit
token budget (`budgetTokens`; `pi-orch --goal-budget-tokens`): the 5,000,000 default pauses
it mid-run.

**→ `references/goals.md`** — the API, per-runtime honesty matrix, read-back discipline.
**Read it before arming a goal.**

## 4c. Pausing YOUR OWN goal to supervise a child (Pi coding agent only)

Keep the parent goal running while independent work remains. Before idling: arm the watch
and backstop, `goal` **pause** (reason `"supervising <child>"`), end the turn. **Never** end
with a needs-user-input marker for supervision (the wake would auto-resume the goal), and
**resume only when fully settled** (no re-dispatch, questions or child watches outstanding).
Verify the goal engine version you rely on is actually loaded.

**→ `references/goals.md`** (Part 2) — full lifecycle and trigger table. **Read it before
dispatching a child under an active goal.**

## 5. When a child asks a question

A child that stops to ask is otherwise a dead end. Read pending requests with
`GET /sessions/:id/approvals/pending` and answer via
`POST /sessions/:id/approvals/:requestId/respond` — structured answers keyed by
the **exact question text**, `cancelled: true` to dismiss. Never fabricate an
answer on the operator's behalf, and never treat an accepted HTTP response as
resolved work.

**→ `references/sessions.md`** has the exact request/response shapes, error
codes, and the permission-request form. **Open it before answering a child.**

## 6. Monitor, and know what counts as evidence

| Need | Endpoint |
|---|---|
| Live progress | `GET /sessions/:id/events` (SSE) |
| Completion signal | `GET /sessions/:id/wait?status=idle&timeout=…` |
| Durable dispatch state | `GET /runs/:runId` |
| One bounded troubleshooting read | `GET /sessions/:id/evidence` |
| Scoped logs, no shell needed | `GET /sessions/:id/diagnostics`, `GET /diagnostics` |

`/events` is **supervision, not durable completion evidence**. For detached or
disconnect-prone work, the receipt is the truth.

- **A `/wait` timeout means "still running", not "failed".** Re-wait; never
  restart, re-dispatch or alert on one.
- **Before reporting a blocker, rule out your own harness** — over-strict route
  assertions, parsers that reject valid JSON wrapped in prose, schemas stricter
  than the one you asked for. A false blocker costs the operator more than a slow
  run.
- **A blank transcript projection is not proof there was no answer.** Compare the
  full projection, receipt evidence, history and diagnostics first.
- **Terminal codes that are not child failures to retry as-is.**
  - `NEVER_STARTED` (1.57.0): an accepted, dispatched run showed no runtime activity
    inside the start window (default 120 s). The watch fires with `runNeverStarted: true`.
    The dispatch never ran: re-dispatch once, then look at the session. Turns started
    by an extension or the browser (goal continuations, watch-wake deadlines) have no
    receipt, so this does not cover them; keep `goal_end` watches plus a backstop.
  - `RUN_TRANSPORT_LOST` (1.57.0): a synchronous dispatch's receipt went terminal but
    its response chain never returned. The outcome is in the receipt; read it and do
    not re-dispatch blindly.
  - `RUN_BUDGET_EXCEEDED`: the run hit a per-run cap. The caps are streamed tool
    arguments (64 KiB per call, 256 KiB per run), 1,000,000 output tokens, and 4 MiB of
    streamed output. The `run_budget_exceeded` / `tool_args_budget_exceeded` event
    names which cap. Split the task, or ask for files instead of inline output.
  - `interrupted` with `SERVER_RESTART`: a deploy cut the run off. The watch fires with
    `interruptedByRestart: true`, and receipt-less goal or extension turns carry
    `runId: "busy-<sessionId>"` (1.52.0). Re-dispatch, or resume the goal, after the restart.

**Completion blocks (1.58.0).** A child that ends its final answer with a
`pi-completion/v1` block (see §3's brief list) gets it parsed server-side. The receipt
carries `completion` (or `completionError` with a typed code and field path) and
`completionDelimiter`. `GET /sessions/:id` carries `latestCompletion`, which also
covers goal children whose final turns have no receipt. The block is the child's
*claim*, not proof: run `pi-orch verify` (or check commits and files yourself) before
accepting it. A `contradicted` verdict is a correction item, not a retry.
`verify --since <ref>` requires each claimed commit to be an **ancestor of `<ref>`**:
pass the branch head you inspected (the ref that must contain the work), never the
pre-work baseline — the check is inverted from the natural reading of "since".

**→ `references/evidence.md`** has the five-step evidence ladder, the
`receipt.outputEvidence` dispositions, transcript scope semantics (including the
`scope=screen` trap), what receipt terminality does and does not prove, and the
Claude channel `/events` caveat. **Read it before declaring anything complete.**

## 7. Find and identify sessions

```text
GET $API_BASE/sessions            # list: sessionId, runtime, model, status, cwd, messageCount, lastActivity
GET $API_BASE/sessions/:id        # detail
GET $API_BASE/sessions/:id/info   # enriched runtime/session metadata
```

Listing is the natural first move when you arrive cold and need to know what is
already running. **The list returns the full persistent registry — including
long-dead sessions** — ordered newest-first by `lastActivity`; liveness comes
from `busy`/`lastActivity`, never from mere presence.

**→ `references/sessions.md`** has server-side filters (contract 1.30.0), the
native-CLI session scan, and the identifier-forms warning (internal id vs
`sessionPath` vs runtime-native id — resolve first, never guess).

## 8. Adopt existing sessions as children (contract 1.40.0)

Adoption links an already-existing session under you **after the fact**, with the same
linkage and fan-out as create-time children. A registered session: `POST /sessions/:id/adopt`
(or `control` action `adopt`). A native CLI session never registered: discover with
`GET /sessions/native`, then `POST /sessions/adopt-native` and use the returned internal
`sessionId`. Adoption is display-only metadata — it never moves transcripts or changes
ownership — and adopted children are full supervision targets.

> **Operator gate — never skip.** If the session was initiated or used in a CLI tool
> (`claude`, `cmdc`, `agy`, `opencode`, `pi`), **ask the operator and wait for explicit
> confirmation that they have exited that CLI** before adopting or dispatching. Your
> dispatches resume the same native artefact in the server's subprocess; a still-open CLI
> is a second live owner (Claude refuses `--resume` with `Session ID already in use`, and
> concurrent writers diverge the transcript).

**→ `references/adoption.md`** — discovery recipes, payloads, responses, errors,
ownership/fencing, post-adoption wiring, worked example. **Read it before your first adoption.**

## 9. Transfer, aggregate, clean up

- `POST /sessions/:id/transfer` moves visible context into a target session you
  own — cleaner than inventing your own handoff framing. It is a handoff, not
  shared memory; track the target id and send a follow-up instruction after.
- `POST /sessions/usage` aggregates token/cost across the batch. Keep the
  session/run mapping so cost stays attributable.
- After positive quiescence, `release_retention` **only** the exact lease you
  own (payload key `retentionLeaseId`). Then `POST /sessions/:id/abort` if work
  must stop, and `DELETE /sessions/:id` for disposable sessions you created.
- `DELETE` of a Pi session runs its extensions' `session_shutdown` (reason `quit`,
  bounded 5 s; contract 1.5x): the child's background processes (dev servers,
  watchers) and goal/watch timers end with it, and the call can take up to 5 s
  longer. Collect anything a child's background task produced before deleting it.
- If release or deletion is unconfirmed, preserve that uncertainty in the
  handoff. Never blanket-unpin, broad-kill processes, or delete an
  operator-owned session.

## 10. Orchestrator governance

For the parent only (children follow `orchestrated-child-worker`). The full playbook, with the
decision boundaries, restart protocol and notification standards, is
**`references/orchestrator-governance.md`**; the rules to carry:

- **Decide and fix autonomously within scope.** Diagnose defects, design fixes, write
  briefs and dispatch small-to-medium corrections without asking; keep the operator
  informed at milestones. Escalate only what the governance file lists (destructive or
  irreversible steps, external submissions, production restarts and deploys unless the
  programme's authority already covers them, locked-decision pivots, quota exhaustion,
  unadjudicable ambiguity).
- **One writer per working tree.** Concurrent children in one repository each get an
  isolated git worktree with disjoint owned paths; where a worktree is impractical, queue
  the second child until the first has committed. Cross-repository parallelism is safe.
- **Sequence gating is yours, not the owner's.** When an earlier lane lands and the tree
  is clear, un-gate the queued lane at once; never ask "may I start phase X?".
- **Production restarts** of the service that hosts your orchestration: only with the
  owner's authority for the programme, only by the parent (never from inside a child it
  hosts), and through the deployment's drain-then-restart procedure. Pi Web UI ships
  `production:drain-restart` under a production lock; adapt it to your deployment.
  - On contract ≥ 1.52.0 the drain waits for every busy session, goal continuations and
    browser turns included.
  - On an older server, pause goal-armed children first: its drain cannot see their turns.
  - Afterwards verify `/capabilities` and reconcile every child and watch
    (`references/orchestrator-governance.md` §3).
- **On every wake, check every child**, not only the one named in the wake.
- **Flatten child chains**: re-parent finished sub-workers under your own record.
- **Mandate the child skill** in every dispatch (§3) and require child-side
  task announcement with owned paths.
- **Notify at milestones** through your own notification path — a short milestone /
  question / blocked / done message, never a running commentary.

# Current limitations

- Parent linkage and child surfacing exist from contract 1.34.0 (automatic
  lineage and `?parent=` since 1.54.0), but there is no general orchestration job
  registry. Keep the programme checkpoint and exact
  session/run/watch/lease mapping; linkage is not execution or completion proof.
- Run receipts are dispatch-scoped; there is no general job queue or scheduler.
- `/approvals/pending` is backend-specific; runtimes without a synchronous
  pending surface return an empty list.
- Command Code exposes only its attested shadow profile through the Internal
  API. Browser-contained Command Code sessions are deliberately invisible to
  Internal API session, diagnostic, notification, receipt, and transfer routes.

# Related

- **`long-horizon-waiting-strategies`** — going idle safely during long waits:
  the pre-idle checklist, harness-specific wake and backstop mechanics (Pi, Claude
  Code, Antigravity, Command Code), and the supervision and liveness rules.
- **`orchestrated-child-worker`** — the skill every child must follow; you mandate it (§3).
- **`secret-scanning`** — the credential-scanning companion for work that produces
  artefacts, evidence bundles or repositories.
- **pi-orch** — the thin parent client: https://github.com/valtterimelkko/pi-orch.
- **Pi Web UI** — https://github.com/valtterimelkko/pi-web-ui. When the repo is
  checked out, the canonical docs are `docs/INTERNAL-API.md`,
  `docs/INTERNAL-API-ORCHESTRATION.md`, `docs/INTERNAL-API-CONTRACT.md`,
  `docs/LIVE-VALIDATION.md`, `docs/TROUBLESHOOTING.md`;

If the repo is not checked out, this skill plus live `/capabilities` is enough.
