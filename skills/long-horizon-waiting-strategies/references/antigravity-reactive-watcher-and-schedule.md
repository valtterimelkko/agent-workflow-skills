# Antigravity CLI / IDE — reactive background watcher and native schedule backstop

> Read this when you are an **Antigravity CLI (`agy`) or IDE** parent waiting on
> a detached dispatch, or need a backstop on that harness. Part of
> `long-horizon-waiting-strategies` — the pre-idle checklist and supervision
> rules live in `SKILL.md`.

**The mechanism in one sentence: a background task that *exits* is the wake,
paired with a native model-free `schedule` backstop that auto-cancels on
completion.**

### Architecture and why in-process push hooks do not apply

Unlike Pi (extensions) and Claude Code (the `watch-wake` mod), Antigravity has no in-process scriptable API capable of maintaining long-lived background interval loops and injecting a prompt into an idle agent session.
Antigravity's customization system supports:
- Rules (`AGENTS.md`, `GEMINI.md`)
- Skills (`SKILL.md`)
- Plugins (`plugin.json` bundling skills, rules, hooks, MCP)
- Hooks (`hooks.json`: `PreToolUse`, `PostToolUse`, `PreInvocation`, `PostInvocation`, `Stop`)
- MCP servers (`mcp_config.json`)
- Sidecars (background services exposing web UI tabs in the IDE)

Crucially, Antigravity's lifecycle hooks are **synchronous command interceptors** that run before or after a tool step or model invocation; they receive JSON on stdin and return JSON on stdout. They *cannot* asynchronously wake an idle agent from outside.
Therefore, a bare Antigravity parent cannot use an in-process watch extension like Pi or Claude Code. Neither lifecycle hooks nor MCP servers can wake an idle session on their own, so the pattern below stays.

However, Antigravity's harness engine provides two **first-class native primitives** that make orchestrating from Antigravity exceptionally clean and token-free:
1. **Reactive Background Tasks (`run_command`)**: When `run_command` is launched with a short `WaitMsBeforeAsync` (e.g. 500–1000 ms), any command taking longer than that duration is automatically demoted to a tracked background task. When that command finishes, Antigravity generates a high-priority system notification (`MESSAGE_PRIORITY_HIGH`) with the command's exit code and output, automatically waking the parent model via Antigravity's **Reactive Wakeup** mechanism. No in-turn polling is needed.
2. **Native One-Shot Timers (`schedule` tool)**: Antigravity includes a built-in `schedule` tool that arms model-free timers. When configured with `DurationSeconds` and `TimerCondition: <taskId>`, the timer **automatically self-cancels** the moment the background watcher task completes (`Timer cancelled: early-termination condition met`). If the watcher hangs or crashes, the timer unconditionally fires at expiry with a `MESSAGE_PRIORITY_HIGH` notification, waking the parent.

### The Antigravity orchestration shape

```bash
# Step 1: Register pure-observer watch on child (no onFire)
# POST /api/v1/sessions/<childId>/watch -> returns { "watchId": "<watchId>" }
```

```json
// Step 2: Launch the persistent canonical watcher via run_command
// Set WaitMsBeforeAsync: 1000 so the command demotes immediately to a background task
{
  "CommandLine": "<pack-root>/skills/pi-web-ui-internal-api-orchestration/scripts/wait-watch.sh <watchId>",
  "Cwd": "<pack-root>",
  "WaitMsBeforeAsync": 1000
}
```

> **Canonical Persistent Script:** Never write ad-hoc inline loops to `/tmp` or scratch scripts. The canonical script at `<pack-root>/skills/pi-web-ui-internal-api-orchestration/scripts/wait-watch.sh` manages Unix socket connections, token resolution, cursor pagination on `/watches/wait`, service restart detection via `MainPID`, and proper exit codes (`0` when fired, `1` on timeout, `3` on error). The restart check snapshots the MainPID of the unit named by `PI_WEB_UI_SERVICE` (default `pi-web-ui.service`) and prints a `reconnecting` message when it changes; when `systemctl` is unavailable or the unit is unknown, the check is a documented no-op and the schedule backstop still covers a hung wait. A scripted check for this behaviour ships next to it (`scripts/test-wait-watch-restart.sh`).

```json
// Step 3: Arm native schedule backstop
// Point TimerCondition to the exact TaskId returned by run_command in Step 2:
{
  "DurationSeconds": 1800,
  "Prompt": "Backstop expired: reconcile child session <childId>",
  "TimerCondition": "<taskId-returned-by-run_command>"
}
```

```markdown
// Step 4: END THE TURN IMMEDIATELY
// Deliver a concise visible status update, and make ZERO further tool calls.
```

### The Four Immutable Orchestrator Invariants

Live incident post-mortems identified that an "anxious supervisor" orchestrator burns model capacity, fills context windows with terminal dumps, triggers cascading compactions, and risks severe disorientation. Future Antigravity orchestrators MUST enforce:

1. **Arm the Watcher, End the Turn (Zero In-Turn Polling)**:
   - Once a child is dispatched and the background watcher + `schedule` backstop are armed, **stop calling tools**.
   - Absolutely NO in-turn loops: no repeated `tmux capture-pane`, no `sleep`, no polling `manage_task(Action='status')`.
   - The exiting background watcher triggers Antigravity's **Reactive Wakeup** mechanism (`MESSAGE_PRIORITY_HIGH`) at **zero token cost** during the wait.
2. **Milestone-Driven Notifications**:
   - Optionally notify the operator through your harness's own notification path.
   - Never spam periodic progress checks or status queries to the operator.
   - Notify only at genuine milestones: dispatch confirmation, child question/block requiring operator decision, task completion hand-off, or unrecoverable error.
3. **Compaction-Resilient State Anchor (`STATE.md`)**:
   - Long-running multi-child dispatches will trigger context window compactions.
   - To survive compaction without losing orientation, maintain an explicit `STATE.md` in the conversation scratchpad (or workspace root).
   - Record: child session IDs, run IDs, watch IDs, task IDs, owned worktree paths, and current phase status.
   - Read this file on wakeup to immediately reorient without probing unfamiliar ports or guessing session state.
4. **Targeted Process Management**:
   - Never run blanket commands such as `pkill -f` on broad patterns (which can kill independent children, the API server, or supervisor sessions).
   - Always target specific PIDs or service units (e.g. `systemctl restart pi-web-ui.service`, `kill <PID>`).

For the comprehensive Antigravity Orchestrator Playbook, see `pi-web-ui-internal-api-orchestration/references/antigravity-orchestrator.md`.

### The Zero-Token Waiting Protocol

The most critical step on Antigravity is Step 4: **end your turn immediately with ZERO further tool calls.**

1. **Do not poll `manage_task(Action='status')` or run bash loops.**
   - Once a command is sent to the background, Antigravity's task system manages it out-of-band.
   - Repeatedly polling `manage_task` or capturing tmux panes burns model turns, pollutes the context window, and wastes model capacity.
   - When the background process exits, Antigravity automatically dispatches a `<SYSTEM_MESSAGE>` with `priority=MESSAGE_PRIORITY_HIGH` carrying the task ID, exit code, and stdout. This triggers a reactive wake turn at zero token cost during the wait.
2. **Handle the background launch message properly.**
   - When `run_command` sends a command to the background, the harness response explicitly instructs:
     *"YOU MUST TAKE ONE OF THE FOLLOWING TWO ACTIONS: A) either proceed to other relevant work (if any) or, B) simply update the user with a short message (that you have launched the command and will wait for it to finish) and end the turn. DO NOTHING ELSE."*
   - Obey this strictly: inform the user concisely or arm the `schedule` backstop, then stop calling tools.

### Multi-Task Supervision and Backstops

When supervising multiple concurrent background operations (e.g. parallel child watchers, builds, or data jobs):
- **Watchdog via `TimerCondition: "any"`**: Arm a single `schedule` timer with `TimerCondition: "any"` and a safety duration (e.g. 1800s). The timer cancels early as soon as *any* background task or subagent finishes and delivers a message.
- **Single active timer constraint**: Antigravity enforces that you cannot have multiple active timers targeting the same sender or condition. Rely on one consolidated liveness timer rather than arming per-task timers in parallel.
- **Early cancellation is silent**: When a background task completes and satisfies `TimerCondition: <taskId>`, Antigravity cancels the timer early without generating an extra notification — the task completion message itself is your wake.

### Seven things learned the hard way on Antigravity

1. **Keep `WaitMsBeforeAsync` small for background jobs.** Set `WaitMsBeforeAsync` to `500`–`1000` ms when you intend for a watcher to background. If left at `10000` ms, the shell will block your foreground turn for 10 seconds before being demoted. Conversely, set `WaitMsBeforeAsync` to `5000`–`10000` ms for quick commands you expect to complete synchronously.
2. **Use the exact TaskId in `TimerCondition`.** When `run_command` backgrounds, it returns an ID formatted as `<conversationId>/task-<N>`. Pass that exact string to `schedule`. Do not pass a truncated or modified string.
3. **No subagents needed for waiting.** Unlike Pi (which historically ran dead-man background subagents before `wake_deadline`), Antigravity has the native `schedule` tool. Never spawn an `invoke_subagent` simply to sleep — it wastes model capacity, launches extra agent transcripts, and wastes context.
4. **Reconcile all children on wake.** Whether woken by the watcher's exit message or by the timer expiry, verify ground truth via `GET /runs/:runId` or `GET /sessions/:id/evidence`. A task exit means the watcher script finished; it does not guarantee the child succeeded.
5. **Protect shared state stores in tests.** When running tests that touch a live coordination store, point the test store at an isolated temporary directory. Otherwise transient test sessions can pollute production state.
6. **Advance the `/watches/wait` cursor every round and prune fired ids.** The wait returns immediately (`waitedMs: 0`) when *any* watch in `ids` has already fired, so re-arming the same request without `cursor=<nextCursor>` (or leaving fired ids in `ids`) turns the watcher into a hot polling loop that burns the background task and its wake instead of waiting.
7. **Detect a Pi Web UI restart via `MainPID`.** A server restart reloads watches `detached`, so the observer wait can hang forever while looking healthy. Snapshot `systemctl show -p MainPID --value "${PI_WEB_UI_SERVICE:-pi-web-ui.service}"` at watcher start, re-compare it each round, and on a change print a `reconnecting` message and update the snapshot (or exit non-zero and let the `schedule` backstop wake you). `wait-watch.sh` does exactly this. When `systemctl` is unavailable or the unit is unknown, the check is a no-op — rely on the schedule backstop and re-register the watch after a restart.


## Related

- `SKILL.md` — the pre-idle checklist, supervision rules and backstop selection.
- `references/claude-code-watch-wake-and-background-watcher.md` — the Claude Code equivalent.
- Hand-back protocol and the liveness discriminator:
  `references/supervision-and-stuck-detectors.md`.
