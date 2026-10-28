<!-- Tier 1 for every parent. One page: read it first, and again after every compaction. Detail lives in the references named in section 5; open them only when a line here points there. -->

# Parent card

You orchestrate. This card is what you must not get wrong. Every command here exists in `references/pi-orch.md` or the waiting skill; if a shape is not on this card, copy it from there, never from memory.

## 1. Rules that bit (F1–F19)

1. **F1** Never hand-write watch JSON, especially after compaction. Copy the canonical block (section 2). A watch tool says "Watching" even for a dead condition.
2. **F2** Goal watches always carry the objective (`pi-orch watch register`/`wait` `--objective`, or the `dataMatch` filter): it matches both the raw and the stored (templated) objective. Without it the condition wakes on **any** goal, including an old goal's clear.
3. **F3** A goal can read `running` while its session sits idle and no watch fires. Keep a backstop on every window and check `busy` plus the last receipt when it expires.
4. **F4** Wakes lie: a `goal_end` from a never-started steer, an early `agent_end` from a child's background shell, a goal the child paused itself, a held stale wake. Triage (section 3) before acting.
5. **F5** A child that needs an answer must end its turn with the hand-back marker. Without it a goal loop re-prompts it endlessly.
6. **F6** Use `pi-orch` verbs, not curl scripts: `goal <sid> pause|resume|show`, `reroute`, `prompt --mode deliver`. No verb (clear, adoption)? Use the API form in `goals.md`.
7. **F7** A steer to an idle child is dropped; one queued behind a busy turn duplicates work. Use `prompt --mode deliver` (steer if busy, else follow_up) or check `busy` first.
8. **F8** Some backends cap a profile's concurrency. Read `/capacity` for the advertised per-profile cap (`maxConcurrent - active`, e.g. `claudeProfiles`) before dispatching children on that profile. Over it you get `429 PROFILE_CAPACITY_EXHAUSTED`, or on older servers an accepted run that fails `RUNTIME_ERROR`.
9. **F9** A spawn refused while memory is free is quarantined admission debt: report it, do not retry in a loop.
10. **F10** The completion block and `--goal-verify` check the hand-back's format, not your gates. Run `pi-orch verify <sid> --gates-file <brief>` (red gate exit 20), then check the rest yourself (`evidence.md`).
11. **F11** Agent-tool children share your own model pool, are invisible to any coordination surface, and cannot be woken — only awaited in-turn. Internal API first; Agent tool or cloud only when it is unavailable or the operator asks.
12. **F12** Choose the child path with the table in `SKILL.md` *Choosing the child path* (Internal API, Agent tool, cloud).
13. **F13** A cloud child's clean finish emits nothing watchable. Require a pushed commit whose subject starts `QUESTION|BLOCKED|HANDBACK`, run a capped `git ls-remote` watcher as a background task (Bash timeout 7,200,000 ms) and arm a ≤ 60 min `wake_deadline` that checks `get_session`.
14. **F14** After compaction, read this card and your STATE file's RESUME block before anything else. Do not grep your transcript for old commands.
15. **F15** Antigravity: arm the goal after create (`goal <sid> start`), single-line objectives, and use `wait-watch.sh`; un-goaled long prompts die at the turn ceiling.
16. **F16** Review in proportion. Reject only for a defect that breaks a frozen criterion or safety; list the rest as notes. Set a time-box in the review brief.
17. **F17** Safety-relevant work (confirm gates, shell, credentials) is reviewed by a capability-strong model from a different family than the implementer — never only by the cheapest reviewer available.
18. **F18** Children never touch main checkouts, `node_modules`, `git stash/gc/prune`, or worktree removal. The parent resolves merge conflicts in a scratch worktree, never in a live checkout.
19. **F19** Cancel watches first, then `cleanup --owner <id>` alone cleans every child of that retention id (lease included). `status --owner <id>` lists them until deleted.

## 2. Copy-paste sequences

Common: `pi-orch` on `PATH`; retention id `orch-<programme>-<parentShort8>-<lane>`; your own session id (for the directive's parent id) is `$CLAUDE_CODE_SESSION_ID` (Claude Code) or `$PI_WEB_UI_SESSION_ID`/`$PI_SESSION_ID` (Pi); `--ttl` = the expected window × 3, ≥ 1800 s; `date -u` before stamping anything. `SNAPSHOT_STALE` on stderr is harmless.

**Canonical watch blocks** (copy exactly):

- Plain turn: `{"id":"done","type":"event_type","eventType":"agent_end"}`
- Goal: `{"id":"outcome","type":"event_type","eventType":"goal_end","dataMatch":{"objective":"<stored objective>"},"once":false}` plus `{"id":"paused","type":"event_type","eventType":"goal_state","dataMatch":{"objective":"<stored objective>","status":"paused"},"once":false}`, `max_wakes` 10. Server 1.62.0: match `{"goalId":"<id>"}` instead of the objective; add `{"id":"stalled","type":"event_type","eventType":"goal_state","dataMatch":{"stalled":true},"once":false}` (a stalled goal is not a finished one: check `busy`).
- Reviewer: `{"id":"done","type":"event_type","eventType":"agent_end","once":false}`, `max_wakes` 4.

**Claude Code** (watch-wake mod; check once that `mcp__watch-wake__*` tools exist):

1. Spawn: `pi-orch spawn --runtime pi --cwd <worktree> --model-selector <SEL> --thinking <lvl> --owner <id> --ttl <s> --id-only`. The brief file carries the completion template (`pi-orch template [--goal]`, pasted).
2. Watch: `mcp__watch-wake__watch_wake_register` with `session_id`, the canonical block as `conditions`, a `message`, `max_wakes`.
3. Backstop: `mcp__watch-wake__wake_deadline` `action=arm` (window plus headroom).
4. Dispatch: `pi-orch prompt <sid> --message "…" --id-only`. The message starts with the child directive: *"You are dispatched as an Agent OS child worker. You MUST load and strictly follow the `agent-os-child` skill. Your session ID is `<sid>`. Your parent session ID is `<yours>`. Work strictly inside `<worktree>`. Owned paths: … Negative exclusions: … Hand-back directory: … Success criteria are frozen. Announce your task once, leave a closing note on completion. Do not push. Hand back by ending your turn only when your own commands have finished; never wait or poll."* (reviewer variant: `SKILL.md` §3c).
5. Idle: write the STATE RESUME block with the ids, then end the turn with no further tool calls.
6. On wake: section 3. Cancel the deadline by its exact id.
7. Verify: `pi-orch verify <sid> --gates-file <brief>`, then your own commands.
8. Cleanup: `watch_wake_cancel id=<registration id>` (a fired one-shot watch may answer `WATCH_GENERATION_MISMATCH`: expected), then `pi-orch cleanup --owner <id>`.

Managed Claude parent: use server `onFire` plus a `deadline` condition instead (`claude-code-orchestrator.md` §3); the mod's deadline never fires there.

**Pi**:

1. Spawn as above.
2. `watch_wake_register` (same arguments as the mod) before dispatch.
3. Backstop: `wake_deadline` (one slot per session). Command-shaped waits: a background-shell tool if your harness has one (otherwise the harness's background execution) with its own time cap; do not peek at its output, you are woken on exit.
4. Dispatch, idle, on-wake, verify and cleanup as above.

**Antigravity** (arm everything before the work can start):

1. Spawn as above.
2. Watch: `pi-orch watch <sid> register --conditions agent_end --label <lane> --id-only` (goal child: `--conditions goal_end,paused --objective "<one line>"`).
3. `run_command` `scripts/wait-watch.sh <watchId>` (inside this skill) with `WaitMsBeforeAsync: 1000`; it returns a task id.
4. Backstop: `schedule` with `DurationSeconds`, a reconcile `Prompt` and `TimerCondition: <taskId>`.
5. Start the work: `pi-orch prompt <sid> --message "…"`, or for a goal child `pi-orch goal <sid> start --goal-objective "<one line>" --goal-budget-tokens 60000000`. Write the STATE RESUME block and end the turn.
6. On wake and cleanup as above (`pi-orch cleanup --owner <id>`, after `watch <sid> delete`).

## 3. On wake

1. `date -u`.
2. Say which signal fired: sentinel/backstop or watch.
3. Reconcile every owned child against durable evidence (`pi-orch status --owner <id>`, run receipt, `busy`, hand-back file, `git log`), not the wake text.
4. A wake with no new receipt since your checkpoint is stale: go idle again.
5. Reject as spurious: a `goal_end` from a receipt that never started, an early `agent_end` from a background shell, a self-paused goal, a dropped steer.
6. An empty first end at about 75 % context is auto-compaction: do not re-prompt, wait for the resumed end.
7. Count wakes used per watch in STATE; refresh near 7/10 only when the child is idle and no wake is held. Never `replace` a live watch.
8. Check the hosting service's `MainPID` against your checkpoint; a changed pid means a crash, so reconcile every child.
9. All terminal: verify. Dependent work running: keep the backstop, go idle. No progress and the window is blown: escalate to the operator.

## 4. Routing

- Classes: **Class 1** routine children (cheap, high-quota models — most child work), **Class 2** more demanding work, **Class 3** the most demanding work, used only when the capability is load-bearing. Exact selectors are live metadata, never memory: `routing.md`.
- Read `/models` and `/capacity`, and check your provider quota dashboards yourself (a zero-token, read-only look at each provider's windows and resets) before **every** dispatch. A refusal is a refusal, not a prompt to take a similar entry.
- Reviewer: fresh, read-only, always a different family than the implementer. Never a metered provider without the operator's say-so.
- **Overflow rule:** when you need more of a capped profile than the cap allows, or other agents hold the slots, **ask the operator** before switching to a metered overflow route. Never automatic.

## 5. When to open which reference

- `routing.md`: before choosing any model (must-read).
- `pi-orch.md`: before your first `pi-orch` call; verbs, flags, exit codes and "Lane runner" (`lane run`, default for gated lanes).
- `walk-away.md`: first detached dispatch; conditions, fan-in, `onFire` payload.
- `claude-code-orchestrator.md`: Claude Code parent; managed vs bare wake route.
- `antigravity-orchestrator.md`: Antigravity parent; invariants and `wait-watch.sh`.
- `goals.md`: before arming a goal, or while yours runs.
- `evidence.md`: before declaring any child complete.
- `sessions.md`: model binding, answering a child's question, identifying sessions.
- `adoption.md`: adopting an existing session.
- `orchestrator-governance.md`: several children, restarts, defects, notifications.
- `multi-phase.md` and `programme-kit.md`: programmes; copy files from `assets/programme-kit/`.
- `patterns.md`: fan-out and operator report.
- `long-horizon-waiting-strategies` skill: backstop choice, supervision, stuck detectors.
- `agent-os-child` skill: you mandate it in every child prompt; you do not follow it.
