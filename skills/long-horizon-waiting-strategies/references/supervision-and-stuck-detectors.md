# Supervision and stuck-detectors — detailed tables and the goal cases

> Read this when you are designing supervision for a dispatched child and need
> the detailed signal tables, the full hand-back protocol, or the two
> goal-shaped supervision cases. The condensed rules live in
> `long-horizon-waiting-strategies/SKILL.md`.

## The liveness discriminator — independent-signal table

An artefact the child writes by choice cannot measure whether the child is
alive — it measures only whether the child is *choosing to report*. Pick the
independent signal from whatever the environment already publishes rather than
inventing one:

| Situation | Independent liveness signal | "Still running" signal |
|---|---|---|
| Orchestration-API child | session/run `lastActivity`, session status | its dispatched workers' run status |
| Local process | process state, accumulated CPU time | child PIDs alive |
| Build, test, migration | the tool's own log mtime, output artefact growth | the tool's exit status |
| Repo work | commits landing, working-tree mtime | lock files, in-progress markers |
| Remote or queued job | the queue's own record — never the worker's self-report | queue depth, claim records |

On Pi Web UI's Internal API the independent liveness signal for an
orchestration child is one call away: `GET /api/v1/sessions/:id/evidence`
bundles session status, run receipts, and `runChronology`. If you lost the
child's id entirely (next day, after a restart), rediscover it with
`GET /api/v1/sessions?limit=20` — newest-first, restart-surviving registry —
or `GET /api/v1/sessions/native` for direct-CLI runs of other runtimes
(contract 1.30.0; both documented in the pi-web-ui-internal-api-orchestration
skill, §7).

Two more things that matter in practice:

- **Require consecutive observations** before declaring death. One sample races
  against ordinary turn boundaries and will fire on a healthy child mid-handover.
- **Verify your own parsing.** A timestamp format you cannot parse silently
  becomes a garbage age and a detector that fires constantly or never. Test the
  parse against a real value before you rely on it.

## The hand-back protocol — impose it, on any repo, any harness

A watcher cannot see a condition inside the child's head. It sees observable
state only. So **convert the child's questions into observable state by
instructing it to** in the dispatch brief. This is a protocol you impose, not a
capability you go looking for, and it works on any repo, runtime or route:

- **Put it in the brief by mandating `orchestrated-child-worker`.** That skill is not injected into
  Internal API children; it carries the end-the-turn-to-hand-back rule, commit and
  exit-status discipline and the reviewer role. Name it in every dispatch.

- Pick a coordination directory **outside** the work tree, and outside anything
  measured, hash-pinned or committed. A stray coordination file inside a measured
  window becomes an unattributable change and can cost you the window's proof.
- The child writes an **ordered** file there — `01-questions.md`,
  `02-batch-ready.md`, `NN-blocked.md`, `NN-complete.md` — whenever it needs you,
  **and then ends its turn**. It must not wait, poll, or hold the turn open.
- **A new file appearing is the wake.** Ordered names make re-arming trivial: the
  watcher records a baseline count and exits when the count grows, so the same
  script serves every gate in the run.
- Keep a **separate** status/heartbeat artefact that is explicitly **not** a wake
  trigger. That is what you read on wake, and what the operator reads to see
  progress without interrupting anyone. Per the rule above, it is a *context*
  signal and never a *liveness* signal.
- Answer in a matching file the child reads when resumed, so both sides have a
  durable record neither has to reconstruct from a chat transcript.

Tell the child all of this explicitly. A child that has not been told will either
hold its turn open waiting for you or end it silently, and both strand the run.

**But do not make the hand-back file your completion signal.** Notice what it is:
an artefact the child writes *by choice* — the exact category the liveness rule
above tells you never to trust. That is fine for **gates**, because a child that
does not ask has nothing you need to answer, so a missing file is harmless. It is
wrong for **completion**, because there the missing file is the whole event, and
you learn nothing precisely when something did happen.

Watch completion on a signal the child cannot withhold: a commit landing on the
branch, the run going terminal, an artefact the build itself writes, the
platform's own end-of-turn condition. Keep the hand-back for questions.

Measured failure shape: a child finished, pushed its commit, and went idle
**without** writing its completion hand-back. A stuck-detector caught it —
correctly, and with no false positive — but only minutes later, and only by
inferring an absence. The operator found out first, from the child's own
notification. A watch on the commit, or on the child's `agent_end`, would have
fired the moment it finished.

## Calibrating what the child may ask about

The question-size rules (what a child may decide alone vs what it must ask
about) live in `SKILL.md` §*Calibrate what the child may ask about* — treat
that section as canonical; do not restate them here.

### Goal-driven children: watch the outcome, not the churn

A child dispatched with a **goal** (pi-web-ui Internal API
`POST /sessions/:id/goal {"action":"start","objective":…}`, contract 1.27.0)
is a different supervision target: the objective survives compaction, so the
child keeps re-orienting itself and emits one terminal `goal_end` event when it
reaches `achieved`/`failed`/`cleared` — instead of an `agent_end` per
continuation turn.

Design consequences:

- **Watch `goal_end`, not per-run `agent_end` churn**, plus a state-filtered
  question/pause. A reused session may emit the OLD goal's clear during new
  start: filter the exact new objective or keep repeated terminal events and
  reconcile identity. An unfiltered one-shot watcher can be consumed too early.
  See orchestration `references/goals.md` for the concrete safe shape.
- **A start receipt is not completion.** Goal start dispatches detached; poll
  `GET /sessions/:id/goal` for the canonical status, or rely on the watch.
- **Pause semantics are honest per runtime.** Claude has no native pause — the
  server disarms an auto-continue loop (bounded nudges, backoff); Command Code
  pause arms a control file the goal-runner mod honours at its next stop; Pi
  pause works mid-run. If you abort a goal-driven child and do NOT pause, an
  armed goal may legitimately re-launch it.
- **Budgets are real outcomes.** Claude auto-continue exhaust (20 nudges,
  30s→10m backoff) and Command Code turn budgets end as
  `goal_end {failed, budget}` — treat those as a checkpoint to re-plan, not as
  silence to poll through.

### Parent holding a goal: yield before you wait (Pi coding agent only)

The inverse case: **you** are the one running under a goal and you dispatch a
child. This is a **Pi coding agent function** — the `goal-engine` extension's
`goal` tool; Claude and Command Code parents have no in-session self-pause
(their pause is a server-side control).

A goal-carrying Pi parent never idles on its own: every run end re-arms a
continuation. The watch-wake extension now steers a busy host, but supervision
still needs a clean parked boundary so goal continuations do not race child
handling or spend budget while waiting. Before dispatching and going idle:

1. When no useful independent work remains and you are about to idle, call
   `goal` pause with reason `"supervising <child>"` (graceful: the current run
   finishes before the pause is applied).
2. Have the child and working watch (prefer goal-specific `goal_end`) plus one
   appropriate backstop armed before ending the turn. Do independent parent
   work while available; pause only when actually idling, not merely on dispatch.
3. On each wake: evaluate the child outcome. Paused wake-runs consume **no**
   goal turns, budget or governor — and the goal does **not** auto-resume on
   input. Re-dispatch and stay paused if more child work is needed.
4. Resume (goal tool, action `resume`) **only when fully settled** — outcome
   handled, nothing left to await, no pending children. The loop re-arms at the
   run boundary and you continue toward `GOAL_ACHIEVED`.

**Trap:** never pause for supervision via the question exit
(`Status: NEEDS_USER_INPUT`). It sets `pendingQuestion`, so the wake itself
auto-resumes the goal and the starvation returns. Plain tool-pause never
does.


## Related

- `SKILL.md` — the condensed supervision rules: ask the operator about child
  capability, wake on gates not progress, the three-state liveness table,
  platform-eval-first.
- `pi-web-ui-internal-api-orchestration/references/goals.md` — the goal API and
  per-runtime honesty matrix.
