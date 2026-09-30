<!-- Loaded from SKILL.md §6. Read before declaring any child complete. -->

Contents: monitoring endpoints · the evidence ladder · wait-timeout semantics · ruling out your own harness · the Claude channel `/events` caveat.

# Monitor, and know what counts as evidence

| Need | Endpoint |
|---|---|
| Live progress | `GET /sessions/:id/events` (SSE) |
| Event vocabulary | `GET /events/types` — avoid hard-coding event names |
| Completion signal | `GET /sessions/:id/wait?status=idle&timeout=…` |
| Durable dispatch state | `GET /runs/:runId` |
| One bounded troubleshooting read | `GET /sessions/:id/evidence` |
| Scoped logs, no shell needed | `GET /sessions/:id/diagnostics`, `GET /diagnostics` |
| Per-runtime health | `GET /health` (`runtimeHealth`) |

`/events` is **supervision, not durable completion evidence**. For detached or
disconnect-prone work, the receipt is the truth.

**A `/wait` timeout is not a failure.** The route returns
`{"status":"timeout","waitedMs":…}` when the session has not reached the
requested state inside *your* window — which means *still running*, and nothing
more. Re-wait. Restarting, re-dispatching, or alerting the operator on a timeout
is how a healthy long run gets killed and then reported as broken. A long batch
pass routinely records several consecutive 300s timeouts on one session id
before the single `idle` that actually ends it.

**The evidence ladder before declaring anything complete:**

1. `GET /runs/:runId` — `status`, plus on 1.14.0+ payload-free `liveness`:
   `watchdog.reason` is `idle` or `absolute` (a bound was crossed) or, since 1.43.0,
   `no_activity` (a **lost wake**: the run stopped producing activity without a
   terminal event; not the same as a stalled turn, so check the runtime before
   aborting), and `cessation.state` distinguishes confirmed / unconfirmed / unknown gateway
   evidence.
2. On 1.19.0+, `receipt.outputEvidence`: `text` means normalized assistant text
   was observed; `no-text` means a terminal `agent_end` occurred *without* it;
   `unknown` means the lifecycle ended without enough signal. These are
   observation dispositions, not semantic judgements.
3. On 1.33.0+, when the run's MODEL matters (benchmarks, comparisons,
   cost-sensitive work), read `receipt.servedModel` (model actually bound at
   dispatch) and `receipt.modelRebound` (true = a drift was detected and
   corrected before the turn). Never declare a model-comparison datapoint
   complete without checking `servedModel` — an observed model-drift incident
   produced wrong-model "clean" results that receipts would have caught.
4. `GET /sessions/:id/evidence` — canonical aliases, diagnostics, receipt
   summary, retention/residency counts, adapter materialisation, and a compact
   three-run chronology.
5. Since contract 1.47.0 the run receipt carries `finalText` (last assistant text,
   tail 4096 chars, `finalTextTruncated`) — check a reply sentinel there before paying for
   a transcript read. Then
   `GET /sessions/:id/transcript?scope=visible_full` for the complete
   runtime-agnostic projection, and `?view=screen` for what the operator would
   see. **`scope=screen` is not valid** and loosely typed clients silently pick
   the wrong projection with it. `scope=visible_recent` is a compact progress
   read only; since contract 1.25.0 you can widen that window with
   `?limit=<n>` (integer, 1–500) instead of being stuck with the default
   20-item cap. Prefer `/runs/:runId/output` + receipt `workState` first.
   Since contract 1.39.0 the screen view also renders antigravity (agy) tool
   cards — before that it silently dropped them, so a tools-free agy screen
   read on an older server is not evidence the agent did no tool work.
6. Require terminal state and output disposition to hold across the bounded
   grace/readback window. Do not substitute a fixed sleep for evidence.
7. On contract 1.45.0+, read the new failure codes honestly:
   `PROMPT_NOT_EXECUTED` on a failed Pi receipt means the prompt was accepted
   but **no turn ever started** (the extension input-hook swallow) — the run
   failed in seconds, not stalled; a `409 SESSION_OWNED_BY_OTHER_RUNTIME`
   means a live foreign runtime owns the session lease (read `ownerPid` /
   `ownerMode`, do not retry until it is resolved); `409 SESSION_FENCED` means
   a dead-owner recovery was attempted and the session remained fenced (it
   follows only a failed recovery, never a healthy handoff); and a
   goal call answered `409 GOAL_ACTION_NOT_APPLIED` means the command ran but
   the transition did not — read `observedGoal` and `extensionWarnings` before
   retrying. Also check `ownership` on `GET /sessions/:id` / adopt responses
   before dispatching into a Pi session that a CLI may have open. `ownership.status`
   is `unknown` (extension not publishing; **never a reason to block**), `unmanaged`,
   `owned`, `conflict` or `uncertain`; act on `conflict` and `uncertain`, with
   `reason`, `ownerPid` and `ownerMode` to hand. Adoption reports ownership but
   never recovers or edits a lease.
8. **A child turn that ended with no text is not necessarily a failure.** On Pi, an
   `auto-compact-75` abort ends the turn silently at about 75% of context and the
   session **resumes by itself**; wait for the resumed `agent_end` and do not re-prompt.
   While it compacts, `busy` reads `false`, so a prompt sent then is accepted (`202`)
   and later fails with a `RUNTIME_ERROR` receipt ("Cannot submit a prompt while
   compaction is in progress"). Each compaction also fires an `agent_end` and spends a
   watch wake, so give `max_wakes` headroom. Judge the outcome by the deliverable file
   or the receipt after the resumed turn, not by the first silent end.

A blank recent or screen projection is **not** proof there was no answer —
compare the full projection, receipt evidence, history, and diagnostics first. If
evidence is `no-text` or `unknown`, report a non-conclusive result rather than
inventing an answer. Receipt terminality releases capacity but does not prove
nested-process, external-side-effect, workspace, or semantic quiescence. Late
terminal observations annotate a receipt without reopening it, and blind
`stream_activity` is deliberately not eligible run activity — don't use it as
progress evidence.

**Before reporting a blocker, rule out your own harness.** Most "the model
failed" alerts from a freshly written orchestration script are the script. The
three that recur: a **route assertion** demanding a field the truthful response
never carries, when the applied model is already recorded correctly; a **parser**
that rejects valid JSON wrapped in a sentence of prose; and a **schema** stricter
than the one you actually asked the child for. Read the raw response against your
own check before escalating. A genuine empty completion is specific and much
rarer — a terminal turn with zero output characters — and a false blocker costs
the operator more attention than a slow run does.

`/history` returns normalized replay events and is for reconstruction and
diagnosis; `/transcript` is the easier surface for reading results.

The diagnostics ring, operational counters, and runtime-health snapshots are
**process-local and reset on restart**. Receipts, transcripts, and runtime-owned
files are the durable record.

### The Claude channel `/events` caveat

For **Claude** sessions, `/events` is less reliable for parallel multi-child
monitoring on one host than it is for Pi, OpenCode, and Antigravity. A single
Claude child streams fine; a fan-out of several that all assume stable
simultaneous SSE is a risky design. For Claude-heavy fan-out: dispatch normally,
monitor completion with `/wait`, collect with `/transcript`, and treat `/events`
as a helpful signal rather than the source of truth. If you want strong live
fan-out monitoring, prefer Pi, OpenCode, or Antigravity.

### Child cards and unknown kinds

A session's child cards (`GET /sessions/:id` `children`) have a `kind`. Since 1.41.0
`background_shell` cards represent a Pi `bg_run` task (`bg_*` ids), not a session:
do not `GET /sessions/<bg_id>` or count them as workers. Tolerate kinds you do not know
and skip them rather than failing the fan-in.
