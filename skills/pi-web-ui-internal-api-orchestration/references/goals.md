<!-- Read before arming a child goal or supervising children under a parent goal. -->

# Goal-driven children and deliberate parent pause/resume

A goal keeps a durable objective across runs and compaction. Use it for a bounded
implementation outcome that may need several turns; use a normal prompt for a
short review or one-shot question. A goal does not transfer sign-off authority to
the child.

## Arm a goal to protect the child's aim (why a prompt is not enough)

A plain-prompt child has **no durable aim**, so anything that arrives looking
like an ending can be read as one. A measured case involved a child dispatched
to prove a transport was interrupted mid-task by an automated end-of-session
message injected as a user turn. It stopped, honestly reported
`harness + proxy written; RED/GREEN runs not yet executed`, and began the
end-of-session flow — a reasonable reading of an instruction saying the session
was ending.
The parent finished the work only by steering it back with `mode:"steer"`.

A goal closes that hole: the objective survives the interruption and the loop
re-arms, so ambient traffic becomes context rather than an exit. The same
property covers two further failures:

- **Thread loss across compaction.** A long child without a durable objective
  forgets what it was for.
- **Premature completion.** A verifier forces an outcome check instead of the
  child deciding it is finished. (A start receipt is still not completion.)

**Use a goal when** the aim is clear and verifiable across multiple turns, when a
child executes a specific part of a plan end-to-end, when the work will outlive a
context window, or when the child must not be derailed by ambient messages. **Do
not use one** for a one-shot bounded answer, for work you would rather steer
turn-by-turn, or where you expect frequent operator decisions — a question
sentinel handles those better.

### Write the aim, not the method

State **what must be true when it is done** and how it will be judged; name the
durable record to follow; state the constraints that must not be softened; then
leave the method to the child. A step list goes brittle the moment the situation
on the ground differs from the plan, and it duplicates the plan itself.

Include, in order: the outcome; the evidence that will settle it; where the
durable record lives; and the invariants that must survive (a gate that must not
be widened, a rule that children must not commit). Those are constraints rather
than method, and they are the part that must not be left implicit. The same
applies to a parent's own goal, not only a child's.

If you have a plan file you can hand over to the child, include its path or contents directly in the initial goal objective/brief. This prevents the child from burning tokens searching or wandering before steering arrives.

## Child goal API

```text
POST /api/v1/sessions/:id/goal
  {"action":"start","objective":"…","maxTurns":20,"verifyCommand":"<bounded verifier>"}
GET /api/v1/sessions/:id/goal
POST /api/v1/sessions/:id/goal {"action":"pause"}
POST /api/v1/sessions/:id/goal {"action":"resume"}
POST /api/v1/sessions/:id/goal {"action":"clear"}
```

Create-time `goal: { objective, maxTurns }` can arm a goal atomically with the
session. Pair long work with an explicitly owned retention lease.

**Objective and budget rules (both bite real lanes).** The objective must be a **single line**:
the goal API rejects newlines (`objective must be a single line`), so keep the long text in
the brief file and point at it. `budgetTokens` is the goal engine's token budget: the server
default is 5,000,000 and pauses a long goal mid-run (a `pauseReason: "budget"` pause, not a
failure). Set it explicitly for any child that may run long, sized to the task and the route
(a long lane on a slower subscription route needed tens of millions); `pi-orch` validates
1..1,000,000,000 and prints a stderr note when you omit it. Via `pi-orch`:
`spawn --goal-objective … --goal-budget-tokens N` arms at create;
`pi-orch goal <sessionId> start --goal-objective … --goal-budget-tokens N` arms a child you
already created (same completion-template delivery; exit 22 if it is not delivered). Pause,
resume and clear stay raw API calls. A budget-paused goal needs the budget resolved, not
repeated resumes. Store the session id, exact objective, start receipt and verifier with the child brief.
Canonical statuses include running, paused, wrapping_up, suggested, achieved,
failed, cleared, idle and unknown; capability-gate support per runtime.

| Runtime | Honest semantics |
|---|---|
| Pi | Extension-backed. Start receipt ends at the command boundary, while later goal runs continue separately. Pause/status commands work while busy; the API pause uses immediate `/goal pause-now`. |
| Claude | Native goal plus bounded server auto-continuation. One query may remain active until the goal settles. Pause disarms the nudger; abort without pause can relaunch it. |
| Command Code | Goal control is honoured at the next prompt/stop boundary by its mod. Prefer deterministic verification when available. |
| Antigravity (1.38.0) | Fully server-side goal manager: sweeper verifies each completed turn (`verifyCommand` exit code, or the `GOAL_STATUS: ACHIEVED` self-report sentinel) and dispatches continuation prompts while unmet, bounded by `maxTurns`. `/goal …` text at the prompt boundary is intercepted, even while busy. |
| OpenCode | No standard goal endpoint support; do not infer support from a separate plugin. |

**Read back, do not infer:** a completed goal-start receipt or HTTP 200/202 is
not goal completion. Read `/goal`, receipt evidence and the handback; independently
verify the deliverable. `goal_end` means a terminal transition, not acceptance.
Pi plain pause reasons are exposed through `pausedReason`/`lastReason` on the
repaired server; question/error classifications retain their precedence.

### Goal actions tell the truth (contract 1.45.0)

On Pi, a goal action that ran but **did not apply** now answers
`409 GOAL_ACTION_NOT_APPLIED` with `observedGoal` (the fresh projection) and
`extensionWarnings` (the extension's own warning text — e.g. the goal-engine's
read-only fence notice) and the receipt ends `failed`. Before 1.45.0 the same
call answered `200 accepted:true` with a `completed` receipt even when nothing
changed — never treat an old transcript's `accepted:true` as proof of effect.
Honest no-ops answer `200` with `applied:false` plus a `reason`:
`already_inactive` (clear on an inactive/achieved goal), `already_paused`,
`not_paused` (resume on a running goal). A verified start carries `applied:true`
— and `start` on an `achieved` goal verifiably **replaces** it (read-back shows
the new objective `running`). Busy-session queued commands keep the accepted
shape, because the goal state may legitimately lag the queued command.
Consumer rule: handle the 409 (read `observedGoal`/`extensionWarnings`, resolve
the underlying reason — usually an ownership fence — and retry); do not retry
blindly.

## Watch the right goal, including reuse and questions

Prefer `goal_end` over per-run `agent_end` for goal children, plus a paused
`goal_state` condition and a question sentinel named in the brief. Do not watch
only successful completion: a capable child still needs a way to stop for a
consequential question.

**Do not add a per-turn `agent_end` condition as a belt-and-braces backstop.**
For a goal-armed child it fires on *every* turn boundary, so it produces false
wakes that read like progress or completion and burn the watch's wake budget.
A verified case showed a P2 watch registered with `agent_end` "just in case"
firing at a plain turn boundary while the child was still busy and its goal
still `running`. A recovery backstop belongs on the **parent's** side — a wake
deadline or a bounded background backstop (see
`long-horizon-waiting-strategies`) — not as extra conditions on the child watch.

**Reusing a child session has an extra edge:** starting its next goal may clear
the old one, producing an old-goal `goal_end` before the new goal starts. An
unfiltered one-shot watcher can consume that event and then miss the real result.
Arm before dispatch, but distinguish the new objective:

```json
{
  "conditions": [
    { "id": "outcome", "type": "event_type", "eventType": "goal_end",
      "dataMatch": { "objective": "<exact dispatched objective>" }, "once": false },
    { "id": "question-pause", "type": "event_type", "eventType": "goal_state",
      "dataMatch": { "objective": "<exact dispatched objective>", "status": "paused" }, "once": false }
  ]
}
```

Use the exact same objective string, not an LLM-transcribed approximation.
`cleared` may omit the objective, so the independent recovery deadline and direct
state reconciliation still matter. Alternatively retain repeated terminal events
and enough wake budget, then reconcile goal identity on every wake. Never treat
the first firing as success. Preserve old ledgers before intentionally replacing
an owned watch for a new phase; do not refresh a live watch merely to check it.

### Pi goal-engine behaviours to plan for (observed behaviour)

- **A goal can read `failed` while the child is still working.** The goal engine
  failed a working child's goal with `pausedReason: "error"` and `lastReason: "run ended
  in under 15000ms"`. The child stayed busy, kept committing and later wrote its FROZEN
  hand-back. Its `goal_end` had already fired as `failed`, so no second `goal_end`
  arrived for the real completion.
  - Treat a `failed` goal_end as "go look", not failure: read `busy`, commits and the
    hand-back file.
  - Restarting the goal can fail the same way.
  - While such a child is still busy, cover the gap with the parent-side backstop, not
    an `agent_end` condition (the churn caveat above). When it stops without a
    hand-back, send the remaining work as a plain `follow_up` prompt.
- **A provider abort mid-turn fails the goal** (`pausedReason: "error"`, transcript
  `stopReason: "aborted"`, "Request was aborted"). The work so far is intact.
  - `{"action":"resume"}` on a `failed` goal answered `applied:false, reason:"not_paused"`.
    The goal read `running` briefly, then `failed` again without continuing.
    Do not trust that resume.
  - Diagnose the abort, then **start a new goal** with the same objective plus a line
    saying what is already done. A correction-round restart (new objective,
    verification looking for the correction marker) is the same move.
- **`POST …/goal {"action":"start"}` on a busy Pi session can hold the HTTP response**
  until the running command ends (observed: about 38 minutes). The command is
  accepted; only the response waits.
  - Always set a client timeout (`curl -m 60`).
  - Read back `GET …/goal` for the new objective instead of waiting on the POST.
- **Pausing for a production restart.** On a server older than contract 1.52.0 the
  drain cannot see goal continuation turns. `{"action":"pause"}` before the restart and
  `{"action":"resume"}` after it keep the child's work (the goal stays on disk). On
  1.52.0–1.59.x the drain waits for them, and a cut-off turn fires the goal watch with
  `interruptedByRestart` — resume or re-dispatch after reconciling.

## Wave K: the server continues restart interruptions (contract ≥ 1.60.0)

On 1.60.0+ a **Pi** goal child whose run was cut off by a RESTART interruption — a restart
or drain interruption, or a boot orphan — is continued ONCE by the server itself, at boot,
through the normal prompt path, with a note naming the cause and the tool call that was in
flight. You do nothing:

- the continue emits `goal_state` with `status: "running"`, top-level `autoContinued:
  true` (so a watch can match it) and the nested `interruption` object (`cause`,
  `continueCount`, `continueNote`, `inFlightToolCall`) — **progress, never a `goal_end`**;
  the restart reconciliation suppresses its synthetic `goal_end` for a continued child, so
  the parent is woken once, at the real end;
- a stop the server could NOT continue has exactly one of these causes and surfaces at
  once as `goal_state` with `status: "paused"`, `pausedReason: "interrupted"` and the same
  `interruption` object; the projection on `GET /sessions/:id` carries it too:
  `restart_interruption` or `rehydrate_pause` that could not be continued,
  `second_transient`, `continue_failed` (ambiguous or unverified delivery),
  `unsupported_runtime` (non-Pi goals, boot sweep only). THAT is the parent's queue:
  `POST /goal {"action":"resume"}` (works on the overlay) or re-dispatch.

Everything else is unchanged by wave K: a provider abort mid-turn fails the goal exactly
as before (the `goal_end {failed}` above), and so do budget, turn limits and question
pauses — those were never the server's to continue.

Watch forms (add your objective filter, as always):
`dataMatch {"autoContinued": true}` → continues (the event data carries the top-level
key precisely because the evaluator's dataMatch is a shallow top-level match);
`dataMatch {"status":"paused","pausedReason":"interrupted"}` → visible stops.
`pi-orch wait` on a goal child already registers the continue condition, counts
continues into `autoContinues` in its JSON, and settles a visible stop as exit 5 with
the cause, the continueCount and a resume-or-re-dispatch note; `pi-orch status` shows
the same interruption facts.

## Parent goal lifecycle (Pi parent only)

**Do useful work while it exists; pause when actually going idle.** On the repaired
Goal Engine, an engine-owned continuation remains cancellable until the runtime
settles; it is not an uncancellable shared follow-up. This lets a parent with independent authority remain running for genuinely
independent work, then park before waiting.
Verify the repaired extension is loaded before relying on it; source on disk
alone does not upgrade an old host. Older hosts should retain their conservative
known-good supervision flow rather than hot-reload during a live child window.

1. Dispatch bounded children and establish their actual local/managed wake path.
   Arm one appropriate recovery backstop for the waiting window (see
   `long-horizon-waiting-strategies`). Retention is not wake delivery.
2. While independent parent work remains, do it. Do not poll children for
   entertainment or leave the goal paused merely because work was delegated.
3. Before idling, call `goal { action:"pause", reason:"supervising <children>" }`.
   Busy graceful pause may report wrapping-up: that is requested, not yet parked.
   Read the returned state honestly; do not report applied pause from prose alone.
4. On wake, reconcile **all** work owned by that waiting window: current goal,
   receipt/work state, watch ledger and frozen handback. Deadline expiry is not
   failure. Old cancelled-window notifications need no repeat fan-in.
5. Stay paused while dependent work is outstanding. Once the waiting work is
   fully settled and its outcome handled, cancel the exact backstop and release
   owned resources, then explicitly `goal { action:"resume" }` to re-arm the loop.

Paused wake-processing runs do not consume goal turns/budget or auto-resume the
objective. The repaired host still supplies bounded paused-objective context;
"no active continuation" does not mean "no context". A resume requested while a
graceful pause is still wrapping up is not an applied resume: inspect the result
and wait for the parked boundary rather than claiming the state changed.

### Boundaries that remain unchanged

- Never use `Status: NEEDS_USER_INPUT` as a substitute for supervision pause.
  It is reserved for an actual human decision and has different resume semantics.
- Never resume explicitly requested, budget, error or ownership-fenced pauses from
  an arbitrary wake. Keep three-strike error and compaction/ownership guards intact.
- A hard budget stop needs the appropriate budget resolution, not repeated
  resume calls. Never infer credential, production or publication authority.
- Pause/resume your own goal only through the supported harness tool. Claude and
  Command Code parents use their runtime-specific controls, not Pi tool names.
- A server restart leaves existing watch ledgers detached. Preserve history,
  reconcile current generation/owner and explicitly restore observation.
- Keep a checkpoint with current truth, not competing "paused" and "running"
  sections. Follow `multi-phase.md` for phased programmes and `walk-away.md` for
  retention, CAS and actual wake delivery.
