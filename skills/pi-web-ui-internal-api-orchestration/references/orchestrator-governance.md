# Orchestrator Governance & Multi-Agent Orchestrator Playbook

> **Audience**: This reference is **strictly for the parent orchestrator** (whether running on Antigravity, Pi, Claude Code, or any other harness) when managing multiple children, competing priorities, and production services over the Internal API. **Worker child agents should NOT read this document.**

---

## 1. The Orchestrator Mindset & Autonomous Boundaries

The orchestrator is not a passive message router; it is the **lead architect, scheduler, and gatekeeper** for the entire task lineage.

### Autonomous Decisions (No Operator Permission Needed)
* **Small to Medium Defect Fixing & Design**:
  * When a defect is discovered in the platform, tools, or dependencies (e.g. unwired observers, broken restart hooks, race conditions), the orchestrator has full authority to diagnose root causes, design the architectural fix, write detailed task briefs, and dispatch child specialists.
  * You do **not** need to present preliminary plans or request permission for small/medium fixes.
  * **Notify the operator**: send a concise milestone notification through your own notification path, stating what defect was found and which child was dispatched to fix it.
* **Child Task Design & Phased Planning**:
  * The orchestrator designs the contract, quality gates, and TDD criteria for each child.
  * Parallelizing independent subtasks across multiple child sessions is strongly encouraged.
* **Adoption & Re-parenting**:
  * Adopting idle or CLI-exited sessions under your own record, or flattening child chains to keep the hierarchy readable.

### Decide locally, escalate the product choice without blocking
When a child's question is really a product decision (it would change user-visible
behaviour), choose the **conservative option — the status quo — for the lane** so the work
keeps moving, and put the real choice to the operator as a non-urgent item under *Decisions
for you* in the next report, with your recommendation and the evidence that makes it matter.

### Record operator grants verbatim
Write each grant into the checkpoint's *Operator authorisations* block: the operator's exact
words, date, scope, and **"Protocol still: …"** — a blanket grant ("you have my authority
for production restarts during these fixes") never relaxes the gates (active turns zero,
coordination check, lock, verification). Authority stays in your records; child briefs carry
rules ("Operator rule (hard): no upstream patches"), not permission stories (§7).

### Operator Escalation Boundaries (Mandatory Approval Required)
* **Destructive or Irreversible Actions**: Wiping databases, deleting repositories, or dropping uncommitted working trees.
* **External Submissions & Communications**: Publishing PRs upstream, public channels, or sending messages outside configured notification scripts.
* **Departing from worktree isolation**: the operator's standing rule is an isolated git worktree per concurrent writer. Running concurrent writers in one shared tree, or any other departure from that rule, is the operator's call.
* **Production restarts and deploys**: restarting or redeploying a live service (the one that hosts your orchestration) needs the operator's authority — either given for the programme up front (record the words) or asked for at the time. Execution approval does not imply deployment approval.
* **Patching upstream or vendored dependencies**: `postinstall` patches, edits under `node_modules`, forks or vendored copies of upstream code. Upstream updates must not be able to silently break your processes, so prefer a runtime fallback plus a test pinning the validated upstream version, and ask before any patch. Never approve a child's upstream patch as precedent; ask the operator. Surface every deviation from upstream in the operator report — never bury it in a lane summary.
* **Fundamental Architectural Pivots**: Changing the core tech stack or deviating from locked roadmap decisions.
* **Blockers & Resource Exhaustion**: Hard quota limits, unresolvable merge conflicts, or ambiguous specifications that cannot be adjudicated from context.

---

## 2. Multi-Agent Concurrency & Repository Staging

When coordinating multiple children across different priorities, the orchestrator must enforce strict repository boundaries.

### Same Repository Collision Prevention
* **The Single-Writer Rule**: Multiple concurrent agents must **never** edit the same working tree or git branch simultaneously. Uncoordinated parallel writes cause git index corruption, overwritten changes, and conflicting test executions.
* **Gating / Queuing**:
  * If two children must work in the same repository, the orchestrator must **strictly gate** the second child until the first child finishes, its tests pass, and its changes are committed.
  * *Example*: while one child fixes the watch manager, a second child working in the same repository is held idle in the queue until the first completes and the service is safely restarted.
* **Isolated Worktrees (the default for concurrent writers)**:
  * When two or more children must write in the same repository at the same time, give each its own `git worktree` on its own lane branch, with dedicated ports/sockets, disjoint owned paths and a named merge order. Queueing (above) is the fallback when a worktree is impractical, e.g. a heavyweight build or a single shared service.

### Sequence Gating vs Operator Gating (Crucial Distinction)
Do not confuse **sequence gating** (repository concurrency control) with **operator gating** (approval):
* **Sequence Gating (Autonomous Orchestrator Responsibility)**:
  * When an improvement spans multiple repositories or when two agents touch the same repository, only the colliding phase(s) in that repository are held in queue. Earlier independent phases in other repositories execute concurrently without delay.
  * As soon as the first lane is verified by you and integrated (merged to the base branch, or committed cleanly in a shared tree), the repository collision is resolved. Pushing waits for the integrated gates (`programme-kit.md`, *Merge and integration*); it is not the un-gating signal.
  * The orchestrator **immediately and autonomously un-gates the waiting child/phase** without consulting the operator.
  * **Anti-Pattern**: Never ask the operator "May I start Phase X now?" or label an unblocked repository phase as "operator-gated" when the blocker was merely another agent working in that repo. Asking permission to advance an unblocked queue is a failure of autonomous orchestration that interrupts the operator for routine scheduling.
* **Operator Gating (true escalation)**:
  * Reserved strictly for irreversible external commitments, financial/legal actions, public releases, or explicit operator-mandated checkpoints ("pause after Phase 2 and show me the design").

### Cross-Repository Parallelism
* When children operate in entirely distinct repositories, bounded parallel dispatch (two to four concurrent children) is safe and recommended.

### Hierarchy Flattening
* Deep nested hierarchies (Parent $\rightarrow$ Child $\rightarrow$ Grandchild) obscure visibility and complicate supervisory watches.
* When a child spawns a sub-worker that completes its task, the orchestrator should record or adopt that sub-worker directly under itself rather than maintaining deep chains.

---

## 3. Production Restart Protocol

Restarting the production control plane is a consequential operational step that interrupts active TCP and Unix-socket connections.

This section is the canonical restart protocol for every harness; the Claude Code and
Antigravity playbooks point here.

### Precondition: authority
A restart needs the operator's authority (see §1). A child never restarts production: it is
hosted inside the server process and would kill itself mid-turn. The parent does it.

### Pre-Restart Safety Gate

Drain-then-restart is shipped (contract 1.51.0; refined in 1.52.0). The drain is the gate: it closes admission, waits for active turns, nonterminal run receipts **and** (1.52.0+) every busy session, then restarts.

1. **Coordination check**: no other agent is mid-deploy or depends on the service right now (your shared task surface, if you have one, is the fastest read).
2. **Know what the drain can see**: read `contract.contractVersion` from `/capabilities`.
   * On **≥ 1.52.0** it sees goal-engine continuations, other extension-driven turns and browser turns.
   * On an **older** server it sees only Internal API turns and receipts. Pause every goal-armed Pi child first (`POST /sessions/:id/goal {"action":"pause"}`), confirm it is idle, and resume it after the restart; otherwise the restart kills it silently.
3. **Single-writer locks**: native CLI sessions (`claude`, `agy`) idle.

### Execution & Verification
0. **Rebuild first when code changed**, inside the lock, and record the commit SHA being deployed.
1. **Drain and restart** (Pi Web UI ships the scripts; a lock wrapper holds a production lock):
   ```bash
   npm run production:lock -- bash -lc 'npm run build &&
     npm run production:drain-restart -- --reason "deploy <what>" --drain-timeout 120 &&
     npm run internal-api:wait'
   ```
   * `settled`: restart.
   * `timed_out`: restart, cutting the listed runs and sessions off. Their parents' watches fire at boot with `interruptedByRestart` (wake text ends `(interrupted by restart: run <id>, <reason>)`).
   * Pass `--on-timeout abort` to refuse instead.
   * An agent that deploys from inside its own Pi Web UI session is excluded from the wait: the script forwards `PI_WEB_UI_SESSION_ID`/`PI_SESSION_ID`.
   * A bare `systemctl restart` bypasses all of this. Restarting without a drain needs `--force --reason`.
   * **If your deployment has a restart gate**, it may refuse the destructive forms while real turns are active (`activeTurns − quarantinedRuns`) and allow the plain drain-restart with an advisory. Never paraphrase, split or rename a command to get past such a gate: report the block, or use the gate's own documented escape only with the operator's explicit say-so.
2. **Verify process liveness**: the service's `MainPID` and `ActiveEnterTimestamp` changed, and the journal shows the extensions loaded with no degradation warnings.
3. **Verify contract, build and capacity**:
   * `GET /api/v1/capabilities`: the expected `contractVersion`.
   * `GET /api/v1/health`: `buildIdentity.revision` equals the deployed SHA.
   * `/capacity`: available.
   * `GET /api/v1/drain`: `idle`.
4. **Smoke**: one create → prompt → `DELETE`, plus one negative check of the change you deployed.
5. **Reconcile**: resume the goals the restart visibly stopped (`goal_state` `paused` + `pausedReason: "interrupted"`; on contract ≥ 1.60.0 Pi goal children continue transient stops themselves, so only the visible stops need you); re-check every child and watch (§4).
6. **Notify the operator**: a milestone message with the SHA, the contract and the drain verdict.

The fuller sequence — coordination check, deploying dependent artefacts first with a backup and
byte check, one guarded restart command that aborts on its own if work arrived, a check
that the built output contains the new code, a functional smoke test, and a deferred
verification deadline for changes judged on later traffic — is the *Deploy and restart
runbook* in `programme-kit.md`. Use it for any programme deploy.

---

## 4. Reconnect & Recovery Protocol After Production Restarts

A restart terminates open HTTP long-polls (`/watches/wait`) and SSE event streams. The orchestrator must execute this recovery protocol upon wakeup:

1. **Check In on ALL Children**:
   * Query every child session in the registry:
     ```bash
     curl -s --unix-socket "$SOCKET" -H "Authorization: Bearer $TOKEN" "$API_BASE/sessions/<id>"
     ```
   * Read the latest transcript turns or tmux pane output to determine each child's true status.
2. **Watch Rehydration & Cursor Continuity**:
   * An `active` watch rehydrates at boot with live broker subscriptions (no re-registration), and completion-type watches whose subject settled during the restart record a reconciled firing. Only a watch whose persisted conditions can no longer be resolved reloads as `detached`: re-register it (check the child's run receipt first, since a new watch cannot see an `agent_end` that already happened). A `deadline` condition that came due while the server was down fires on boot with `reconciled:true`.
   * Call `GET /api/v1/watches/wait?ids=watch-<id>&cursor=<cursor>` using your existing cursor. Any events fired across the restart window will be returned immediately.
3. **An unplanned restart is not a drain.** When the server dies (an OOM kill, a crash)
   rather than draining, no interruption event reaches your watches: nothing fires, and
   children silently lose their in-flight turns. On every wake compare the service's
   `MainPID` (or `ActiveEnterTimestamp`) with your checkpoint; if it changed without your
   restart, run this whole protocol for every child.
4. **Re-establish Gated Queue**:
   * Once the production service settles, check the queue and advance the next gated child into execution.

---

## 5. Zero-Token Waiting & Wakeup Check-in Discipline

* **Zero-Token Discipline**: Never run foreground busy-polling loops in your turn. Dispatch children with `detach: true`, arm the wake and backstop that your harness provides (`long-horizon-waiting-strategies`: Pi `watch-wake`/`onFire`, Claude Code `watch_wake_register` + `wake_deadline`, Antigravity `wait-watch.sh` + `schedule`), and end your turn.
* **The "Arm the Watcher, End the Turn" Invariant**:
  - Once a child is dispatched or un-gated, running iterative `tmux capture-pane`, `sleep`, or `curl /sessions/:id` loops inside your turn is strictly forbidden.
  - In-turn polling causes severe context bloating (re-reading terminal captures on every step), triggering rapid model compactions and wasting provider quota.
  - On Antigravity, invoke the persistent helper script `scripts/wait-watch.sh <watchId>` (inside this skill) in the background via `run_command` (`WaitMsBeforeAsync: 1000`), arm the `schedule` backstop, and stop calling tools immediately.
  - See `references/antigravity-orchestrator.md` for the complete Antigravity orchestrator playbook.
* **The Check-in Rule**:
  - **Whenever you are woken up by ANY event** (a timer expiring, a subagent message, or a background task completion), **always check in on all managed children**.
  - Verify that no child is stalled, waiting for operator confirmation, or stuck in a tool loop.
  - Update your coordination surface so the operator and peer agents see accurate progress.
* **Post-Compaction Resilience (`STATE.md`)**:
  - Compactions strip in-turn memory of paths and sockets. Keep a `STATE.md` with `PI_WEB_UI_SOCKET`, `TOKEN_PATH`, and active child session ids, watch ids and lease ids. Read this file first upon wake following a compaction; never guess ports or paths. For a multi-lane programme this is the live checkpoint in `multi-phase.md` (put the connection anchors in its header); for a single child a few lines in the scratch directory suffice.

---

## 6. Communication Standards

All user-facing updates from the orchestrator go through one configured notification path (a helper script, the Internal API's notification route, or your own chat bridge — pick one and keep it). Check that each notification was actually delivered; a `202` is queue acceptance only.

* **Format**: `<notify> <milestone|done|question|blocked> "<Clear Title>" "<Structured Body>"` — one line, four fixed kinds, so the operator can filter.
* **Tone & Content**:
  - Sharp, concise, and structured (use bullet points and numbered sections).
  - State the bottom line upfront: what was accomplished, what decisions were made autonomously, and what is happening next.
* **Cadence: Milestone-Driven, NOT Continuous Narration**:
  - Send updates at **meaningful transition points**:
    1. Phase dispatched & scope locked (`milestone`).
    2. Test suite / TDD verification green (`milestone`).
    3. Defect discovery or architectural pivot (`milestone` or `question`).
    4. Entire programme complete & pushed (`done`).
  - **Anti-Pattern**: Do NOT poll terminals or send updates for line-by-line tool activity. The operator wants milestone progress, not a running terminal log.

## 7. Claude Parents Dispatching Into Pi Children

For a Claude parent driving Pi children through this API (Claude children are SDK-only, `CLAUDE_BACKEND_NOT_ALLOWED` otherwise; `claude-code-orchestrator.md`):

- **Keep child briefs in files** (a path under your coordination
  directory) and dispatch with a short, neutral prompt pointing at the brief
  file. The prompt travels through provider safety classifiers; the brief
  file does not.
- **Do not write operator-authority claims into text sent to another agent**
  (e.g. "operator-authorised to …", "the operator has approved X"). This is a
  suspected, unverified safety-classifier trigger and has correlated with
  refusals or degraded child behaviour. Authority stays in the parent's own
  records; the child needs the task and the brief path, not the permission
  story.
- Record the 1.45.0 truth semantics in the brief: the child reads
  `GOAL_ACTION_NOT_APPLIED` / `SESSION_OWNED_BY_OTHER_RUNTIME` / `PROMPT_NOT_EXECUTED`
  as actionable failures, not as reasons to improvise retries.

## 8. Verify child claims; contain proofs

- **A child's report is a claim.** In one wave a child reported fixes it had not made and
  a root cause a disposable experiment refuted; an independent reviewer caught the first,
  the parent's own probe the second. For every claimed fix, read the diff at the claimed
  file:line and check the test would fail on the old code. In correction briefs, require
  a file:line list per fix and a test on the real call path (not a mock of it).
- **Proof topology must match production.** A proof that passes on a layout production
  does not have proves nothing about production (a systemd unit inside a proof slice kept
  cgroup controllers enabled that production's empty slice lost on every
  `daemon-reload`). Check effective values after install, since overrides can outrank the
  file you installed, and re-check behaviour after the events production sees routinely.
- **Contain memory and isolation proofs**: a hard `MemoryMax` of your own (a cap the
  operator and the host can live with), cgroups only inside a subtree you created and
  verified, allocations capped in the proof itself. Never revert host OOM settings to
  work around a proof.
- **Parent-authored fixes still get an independent review**, and a wave is not reported
  shipped until a reviewer (not the executor or the parent) has re-run its live checks.

