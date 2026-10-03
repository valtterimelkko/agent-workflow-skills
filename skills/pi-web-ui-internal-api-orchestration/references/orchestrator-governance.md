# Orchestrator Governance & Multi-Agent Orchestrator Playbook

> **Audience**: This reference is **strictly for the parent orchestrator** (whether running on Antigravity, Pi, Claude Code, or any other harness) when managing multiple children, competing priorities, and production services over the Internal API. **Worker child agents should NOT read this document.**

---

## 1. The Orchestrator Mindset & Autonomous Boundaries

The orchestrator is not a passive message router; it is the **lead architect, scheduler, and gatekeeper** for the entire task lineage.

### Autonomous Decisions (No Operator Permission Needed)
* **Small to Medium Defect Fixing & Design**:
  * When a defect is discovered in the platform, tools, or dependencies (e.g. unwired observers, broken restart hooks, race conditions), the orchestrator has full authority to diagnose root causes, design the architectural fix, write detailed task briefs, and dispatch child specialists.
  * You do **not** need to present preliminary plans or request permission for small/medium fixes.
  * **Optional notification**: Use the harness's own notification path to report what defect was found and which child was dispatched to fix it.
* **Child Task Design & Phased Planning**:
  * The orchestrator designs the contract, quality gates, and TDD criteria for each child.
  * Parallelizing independent subtasks across multiple child sessions is strongly encouraged.
* **Adoption & Re-parenting**:
  * Adopting idle or CLI-exited sessions under the parent board, or flattening child chains to keep hierarchy clean.

### Decide locally, escalate the product choice without blocking
When a child's question is really a product decision (it would change user-visible
behaviour), choose the **conservative option — the status quo — for the lane** so the work
keeps moving, and put the real choice to the responsible operator as a non-urgent item
under *Decisions and recommendations* in the next report, with your recommendation and
the evidence that makes it matter.

### Record approvals verbatim
Write each approval into the checkpoint's *Approval record* block: the approving operator's
exact words, date, scope, and **"Protocol still: …"** — a blanket approval never relaxes
the gates (activeTurns 0, coordination check, lock, verification). Authority stays in
your records; child briefs carry project rules, not permission stories (§7).

### Operator Escalation Boundaries (Mandatory Approval Required)
* **Destructive or Irreversible Actions**: Wiping databases, deleting repositories, or dropping uncommitted working trees.
* **External Submissions & Communications**: Publishing PRs upstream, public channels, or sending messages outside configured notification scripts.
* **Departing from worktree isolation**: the operator's standing rule is an isolated git worktree per concurrent writer. Running concurrent writers in one shared tree, or any other departure from that rule, is the operator's call.
* **Production restarts and deploys**: restarting or redeploying a live service (e.g. `pi-web-ui.service`) needs the responsible operator's authority — either given for the programme up front (record the words) or asked for at the time. Execution approval does not imply deployment approval.
* **Patching upstream or vendored dependencies**: `postinstall` patches, edits under `node_modules`, forks or vendored copies of upstream code (e.g. pi-core, pi-ai). Upstream updates must not be able to silently break our processes, so prefer a runtime fallback plus a test pinning the validated upstream version, and require explicit approval before any patch. Surface every deviation from upstream in the programme report — never bury it in a lane summary.
* **Fundamental Architectural Pivots**: Changing the core tech stack or deviating from locked roadmap decisions.
* **Blockers & Resource Exhaustion**: Hard quota limits, unresolvable merge conflicts, or ambiguous specifications that cannot be adjudicated from context.

---

## 2. Multi-Agent Concurrency & Repository Staging

When coordinating multiple children across different priorities, the orchestrator must enforce strict repository boundaries.

### Same Repository Collision Prevention
* **The Single-Writer Rule**: Multiple concurrent agents must **never** edit the same working tree or git branch simultaneously. Uncoordinated parallel writes cause git index corruption, overwritten changes, and conflicting test executions.
* **Gating / Queuing**:
  * If two children must work in the same repository (e.g. `path/to/pi-web-ui`), the orchestrator must **strictly gate** the second child until the first child finishes, its tests pass, and its changes are committed.
  * *Example*: While Child A fixes `WatchManager` in `pi-web-ui`, Child B (working on `background-shell`) is held idle in the queue until Child A completes and production is safely restarted.
* **Isolated Worktrees (the default for concurrent writers)**:
  * When two or more children must write in the same repository at the same time, give each its own `git worktree` on its own lane branch, with dedicated ports/sockets, disjoint owned paths and a named merge order. Queueing (above) is the fallback when a worktree is impractical, e.g. a heavyweight build or a single shared service.

### Sequence Gating vs Approval Gating (Crucial Distinction)
Do not confuse **sequence gating** (repository concurrency control) with **approval gating** (operator approval):
* **Sequence Gating (Autonomous Orchestrator Responsibility)**:
  * When an improvement spans multiple repositories or when two agents touch the same repository, only the colliding phase(s) in that repository are held in queue. Earlier independent phases in other repositories execute concurrently without delay.
  * As soon as the first lane is verified by you and integrated (merged to the base branch, or committed cleanly in a shared tree), the repository collision is resolved. Pushing waits for the integrated gates (`programme-kit.md`, *Merge and integration*); it is not the un-gating signal.
  * The orchestrator **immediately and autonomously un-gates the waiting child/phase** without consulting the operator.
  * **Anti-Pattern**: Never ask the operator "May I start Phase X now?" or label an unblocked repository phase as "approval-gated" when the blocker was merely another agent working in that repo. Asking permission to advance an unblocked queue is a failure of autonomous orchestration that interrupts the operator for routine scheduling.
* **Approval Gating (True Operator Escalation)**:
  * Reserved strictly for irreversible external commitments, financial/legal actions, public releases, or explicit operator-mandated checkpoints ("pause after Phase 2 and show me the design").

### Cross-Repository Parallelism
* When children operate in entirely distinct repositories (e.g. Child 1 in `path/to/pi-web-ui`, Child 2 in `path/to/other-repo`, Child 3 in `path/to/skills`), bounded parallel dispatch (2–4 concurrent children) is safe and recommended.

### Hierarchy Flattening
* Deep nested hierarchies (Parent $\rightarrow$ Child $\rightarrow$ Grandchild) obscure visibility and complicate supervisory watches.
* When a child spawns a sub-worker that completes its task, the orchestrator should record that worker directly in the coordination surface (if one exists), or add a one-line task/owned-paths note to the hand-back directory, rather than maintaining deep chains.

---

## 3. Production Restart Protocol (`pi-web-ui.service`)

Restarting the production control plane (`pi-web-ui.service`) is a consequential operational step that interrupts active TCP/Unix-socket connections.

This section is the canonical restart protocol for every harness; the Claude Code and
Antigravity playbooks point here.

### Precondition: authority
A restart needs the responsible operator's authority (see §1). A child never restarts production: it is
hosted inside the `pi-web-ui` process and would kill itself mid-turn. The parent does it.

### Pre-Restart Safety Gate

Drain-then-restart is shipped (B4, contract 1.51.0; B4.1, 1.52.0). The drain is the gate: it closes admission, waits for active turns, nonterminal run receipts **and** (1.52.0+) every busy session, then restarts.

1. **Board check**: no other agent is mid-deploy or depends on the service right now.
2. **Know what the drain can see**: read `contract.contractVersion` from `/capabilities`.
   * On **≥ 1.52.0** it sees goal-engine continuations, other extension-driven turns and browser turns.
   * On an **older** server it sees only Internal API turns and receipts. Pause every goal-armed Pi child first (`POST /sessions/:id/goal {"action":"pause"}`), confirm it is idle, and resume it after the restart; otherwise the restart kills it silently.
3. **Single-writer locks**: native CLI sessions (`claude`, `agy`) idle.

### Execution & Verification
0. **Rebuild first when code changed**, inside the lock, and record the commit SHA being deployed.
1. **Drain and restart** (the lock wrapper holds `~/.pi-web-ui/production-control.lock`):
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
   * **Host command gate:** while real turns are active (`activeTurns − quarantinedRuns` from `/capacity`), the host's command gate refuses the destructive forms — `--force`, `--drain-timeout 0`, and a bare `systemctl restart|stop` of the service — and allows a plain `npm run production:drain-restart` with an advisory. Quoted text, heredoc bodies and comments no longer trip it (an older text-only heuristic did); the gate's own escape is `--override`, for the responsible operator's explicit say-so, not a workaround to reach for.
2. **Verify process liveness**: `systemctl show pi-web-ui.service -p MainPID -p ActiveEnterTimestamp` changed, and `journalctl -u pi-web-ui.service` shows the extensions loaded with no degradation warnings.
3. **Verify contract, build and capacity**:
   * `GET /api/v1/capabilities`: the expected `contractVersion`.
   * `GET /api/v1/health`: `buildIdentity.revision` equals the deployed SHA.
   * `/capacity`: available.
   * `GET /api/v1/drain`: `idle`.
4. **Smoke**: one create → prompt → `DELETE`, plus one negative check of the change you deployed.
5. **Reconcile**: resume the goals the restart visibly stopped (`goal_state` `paused` + `pausedReason: "interrupted"`; on contract ≥ 1.60.0 Pi goal children continue transient stops themselves, so only the visible stops need you); re-check every child and watch (§4).
6. **Optionally notify the operator** through the harness's own notification path with the SHA, contract and drain verdict.

The fuller sequence — board check, deploying dependent artefacts first with a backup and
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
3. **Re-establish Gated Queue**:
   * Once the production service settles, check the queue and advance the next gated child into execution.

---

## 5. Zero-Token Waiting & Wakeup Check-in Discipline

* **Zero-Token Discipline**: Never run foreground busy-polling loops in your turn. Dispatch children with `detach: true`, arm the wake and backstop that your harness provides (`long-horizon-waiting-strategies`: Pi `watch-wake`/`onFire`, Claude Code `watch_wake_register` + `wake_deadline`, Antigravity `wait-watch.sh` + `schedule`), and end your turn.
* **The "Arm the Watcher, End the Turn" Invariant**:
  - Once a child is dispatched or un-gated, running iterative `tmux capture-pane`, `sleep`, or `curl /sessions/:id` loops inside your turn is strictly forbidden.
  - In-turn polling causes severe context bloating (re-reading terminal captures on every step), triggering rapid model compactions and wasting provider quota.
  - On Antigravity, invoke the persistent helper script `./scripts/wait-watch.sh <watchId>` in the background via `run_command` (`WaitMsBeforeAsync: 1000`), arm the `schedule` backstop, and stop calling tools immediately.
  - See `references/antigravity-orchestrator.md` for the complete Antigravity orchestrator playbook.
* **The Check-in Rule**:
  - **Whenever you are woken up by ANY event** (a timer expiring, a subagent message, or a background task completion), **always check in on all managed children**.
  - Verify that no child is stalled, waiting for operator confirmation, or stuck in a tool loop.
  - Refresh the harness's coordination state so the operator and peer agents see accurate progress; if no such surface exists, update the one-line task/owned-paths note in the hand-back or coordination directory.
* **Post-Compaction Resilience (`STATE.md`)**:
  - Compactions strip in-turn memory of paths and sockets. Keep a `STATE.md` with `PI_WEB_UI_SOCKET`, `TOKEN_PATH`, and active child session ids, watch ids and lease ids. Read this file first upon wake following a compaction; never guess ports or paths. For a multi-lane programme this is the live checkpoint in `multi-phase.md` (put the connection anchors in its header); for a single child a few lines in the scratch directory suffice.

---

## 6. Harness notification standards

User-facing updates are optional and should use the harness's configured notification
mechanism. Check that each notification was actually delivered; a `202` is queue
acceptance only.

* **Format** (adapt to your harness):
  ```bash
  notify <milestone|done|question|blocked> "<Clear Title>" "<Structured Body>"
  ```
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

## 7. Claude parents dispatching into Pi children

For a Claude parent driving Pi children through this API (Claude children are SDK-only, `CLAUDE_BACKEND_NOT_ALLOWED` otherwise; `claude-code-orchestrator.md`):

- **Keep child briefs in files** (a path under the coordination or vault
  directory) and dispatch with a short, neutral prompt pointing at the brief
  file. The prompt travels through provider safety classifiers; the brief
  file does not.
- **Do not write authority claims into text sent to another agent** (e.g. "approved
  to …"). Keep authority in the parent's own records; the child needs the task and
  brief path, not the permission story.
- Record the 1.45.0 truth semantics in the brief: the child reads
  `GOAL_ACTION_NOT_APPLIED` / `SESSION_OWNED_BY_OTHER_RUNTIME` / `PROMPT_NOT_EXECUTED`
  as actionable failures, not as reasons to improvise retries.
