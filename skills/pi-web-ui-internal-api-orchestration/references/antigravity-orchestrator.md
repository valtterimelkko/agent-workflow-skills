# Antigravity Orchestrator Playbook: Zero-Token Supervision & Token-Efficiency Rules

> **Audience**: This reference is **MANDATORY for Antigravity CLI / IDE orchestrators** (`agy`) when coordinating children, managing background waits, or controlling services over the Pi Web UI Internal API.
> **Non-Antigravity Agents**: Claude Code orchestrators use `references/claude-code-orchestrator.md`; Pi Coding Agent orchestrators use their own layers (`watch-wake`, `bg_run`, `wake_deadline`); they must **skip this document**.

---

## 1. The Antigravity Reactive Orchestration Model

Antigravity cannot run in-process background event loops (like Pi extensions). However, it possesses two **native harness primitives** that make multi-agent orchestration exceptionally cheap when used with strict discipline:

1. **Reactive Background Tasks (`run_command`)**:
   - Any shell command taking longer than `WaitMsBeforeAsync` (set to `1000` ms) is demoted to a tracked background task.
   - When the background process exits, Antigravity dispatches a `<SYSTEM_MESSAGE>` with `priority=MESSAGE_PRIORITY_HIGH` containing the exit code and output, **reactively waking the parent model**.
   - No tokens are consumed while waiting for the task to exit.
2. **Auto-Cancelling Model-Free Timers (`schedule` tool)**:
   - Arms a timer with `DurationSeconds` and `TimerCondition: <taskId>`.
   - The timer **automatically self-cancels** the moment the background task exits (`Timer cancelled: early-termination condition met`).
   - If the task stalls or crashes without exiting, the timer fires at expiry as a high-priority safety wake.

---

### What the host already gives an Antigravity parent

Hooks configured in `~/.gemini/config/hooks.json` (`PreInvocation`, `PreToolUse`, `PostToolUse`, `Stop`) and any MCP server you have attached are available automatically, so a parent can read a child's or a past session's state without parsing raw transcripts. They are synchronous and cannot start a turn, so no wake mechanism exists beyond the two primitives above. **Children you dispatch still need the `orchestrated-child-worker` directive in their prompt** (SKILL.md §3).

---

## 2. Canonical Persistent Watcher: `wait-watch.sh`

Do **not** write ad-hoc bash scripts into scratch to poll watches. Use the persistent helper script in this skill:

```bash
scripts/wait-watch.sh <watchId> [max_iterations] [timeout_ms]
```

### End-to-End Dispatch & Wait Pattern

When dispatching or un-gating a child:

```text
Step 1: Register pure-observer watch on the child
  POST /api/v1/sessions/<childSessionId>/watch
  Payload: { "conditions": [{ "id": "done", "type": "event_type", "eventType": "agent_end" }], "label": "child-watch" }
  Response: { "watchId": "<watchId>" }

Step 2: Launch the canonical watcher in the background via run_command
  Tool Call: run_command(
    CommandLine: "scripts/wait-watch.sh <watchId>",
    Cwd: "<absolute path to the skill directory>",
    WaitMsBeforeAsync: 1000
  )
  Returns: Task id "<taskId>"

Step 3: Arm the native auto-cancelling schedule backstop
  Tool Call: schedule(
    DurationSeconds: 1800,  # e.g. 30 minutes
    Prompt: "Backstop expired: reconcile child session <childSessionId>",
    TimerCondition: "<taskId>"
  )

Step 4: END YOUR TURN IMMEDIATELY
  Do NOT call any more tools. Update the user with a concise one-line note and STOP.
```

---

### Antigravity parent rules

- Pass `--objective` on every goal watch.
- Arm the goal after create (`goal <sid> start`): goal-at-create is refused for antigravity.
- Objectives are single lines.
- Release gates are enforced.
- Never resolve conflicts in a live checkout (scratch worktree, then `--ff-only`).

## 3. The Four Immutable Orchestrator Invariants

### Invariant 1: "Arm the Watcher, End the Turn" (Anti-Polling Rule)
* **Strictly Forbidden**: Calling `tmux capture-pane`, `sleep`, or `curl /sessions/:id` in an iterative loop within the same turn.
* **Why this is toxic**: Terminal screen dumps and repeated tool results accumulate rapidly within a turn. Re-reading hundreds of kilobytes of terminal output every 10 seconds burns hundreds of thousands of tokens, exhausts provider quotas, and triggers aggressive context compactions.
* **The Rule**: Once a dispatch request returns `202 Accepted`, you must register the watch, launch `wait-watch.sh`, arm the `schedule` backstop, and **stop calling tools**. Wait reactively for the harness notification.

### Invariant 2: Milestone-Driven Communication (Not Continuous Peeking)
* When an operator requests "frequent communication", this means reporting at **discrete operational milestones** through your notification path:
  1. Phase dispatched & scope locked (`<notify> milestone ...`).
  2. Verification / TDD suite confirmed green.
  3. Defect discovery or architectural pivot.
  4. Final delivery, commits pushed, and handoff (`<notify> done ...`).
* **Anti-Pattern**: Peeking into tmux or running status checks every 3 seconds to narrate individual lines of code being written is unnecessary noise that drives token waste.

### Invariant 3: Post-Compaction State Anchor (`STATE.md`)
* Context compaction strips in-turn ephemeral memory. A compacted model often suffers disorientation—guessing default HTTP ports (`localhost:3000`) or missing token paths.
* **The Discipline**: Maintain a lightweight 5-line `STATE.md` in the scratch directory:
  ```markdown
  SOCKET=$HOME/.pi-web-ui/internal-api.sock
  TOKEN_PATH=$HOME/.pi-web-ui/internal-api-token
  TARGET_REPO=/work/project
  CHILD_ID=<child session id>
  ACTIVE_WATCH_ID=<watch id>
  ```
  Whenever you wake up after a compaction, read `STATE.md` first. Never guess connection endpoints.

### Invariant 4: Targeted Process Management (No Blanket `pkill`)
* Avoid broad commands like `pkill -f validation-server` or `pkill -f node`.
* Broad kills risk terminating concurrent validation servers or background workers owned by other lineages.
* Read the specific PID from the target's metadata (e.g. `/tmp/pi-validation-<id>/server-process.json`) or kill the exact process group (`kill -- -<pgid>`).

---

## 4. Production Service Restart Protocol

Follow the canonical protocol in `orchestrator-governance.md` §3–§4: the operator's authority
first, the parent (never a child, which the server hosts and would kill mid-turn) restarts
through the deployment's drain-then-restart procedure (the drain is the gate; pause goal-armed
children first on a server older than contract 1.52.0), rebuilds with `npm run build` when code
changed, then verifies the service is active and `/capabilities` answers. Antigravity-specific: existing `active` watches
rehydrate at boot (re-register one that reloads `detached`), and `wait-watch.sh` detects the
restart via `MainPID` — relaunch it with the existing cursor.
