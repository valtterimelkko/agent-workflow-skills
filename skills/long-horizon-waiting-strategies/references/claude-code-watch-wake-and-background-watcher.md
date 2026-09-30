# Claude Code — the watch-wake mod, its deadline backstop, and the exiting background watcher

> Read this when you are a **Claude Code** parent (interactive `claude` CLI, `claude -p`,
> or a Claude session Pi Web UI manages) waiting on a detached dispatch, or need a
> backstop on that harness. Part of `long-horizon-waiting-strategies` — the pre-idle
> checklist and supervision rules live in `SKILL.md`. The Internal API side (dispatch,
> fan-in, `onFire` for managed Claude, routing) is in
> `pi-web-ui-internal-api-orchestration/references/claude-code-orchestrator.md`.

**The mechanism in one sentence: the `watch-wake` mod starts a new turn in your idle
session when the child's watch fires, with its `wake_deadline` as the model-free
backstop; where the mod is unavailable, a background task that *exits* is the wake.**

## Which mechanism applies to you

| You are… | Primary wake | Backstop |
|---|---|---|
| Bare interactive `claude` CLI, mods loaded | `watch-wake` mod (below) | `mcp__watch-wake__wake_deadline` |
| Bare interactive CLI, mod tools absent (`--bare`, `--safe-mode`, mods disabled) | exiting background watcher (below) | a second, capped background sleep task |
| Managed Claude session (created by Pi Web UI) | server `onFire` targeting your internal id (`$PI_WEB_UI_SESSION_ID`) | server-side `deadline` watch condition (contract 1.47.0) — **not** the mod's `wake_deadline`: if it remains `armed` past its deadline with no attempts, the SDK host may not keep the mod's timer running between turns |
| `claude -p` | **none** — the process exits after its turn | do not wait from `-p`; hand back instead |
| Claude Code **Remote Control** session (long-lived headless process, `CLAUDE_CODE_ENVIRONMENT_KIND=bridge`) | `watch-wake` mod, as for the interactive CLI. A session **started before** the currently loaded mod may still run an older mod, which refuses: use the exiting background watcher there | `mcp__watch-wake__wake_deadline` (delivers in RC sessions). Registrations and the armed deadline can survive a restart of the RC server itself; still run `watch_wake_list` and check the server-side watch generation after such a restart |

Check once per session whether the tools `mcp__watch-wake__watch_wake_register`,
`…_list`, `…_cancel` and `mcp__watch-wake__wake_deadline` exist. If your Claude setup
provides a mod-status check, use it.

## Why Claude Code can now wake an idle session

Claude Code's settings hooks are synchronous shell processes
per event; like Antigravity's, they cannot start a turn. But Claude Code also ships an
early-access in-process plugin API (**function hooks**, "mods"), when configured for the session.
A mod can keep timers alive for the session (`$.clock.every`) and submit a prompt that
**starts a turn of its own once the session is idle** (`$.prompt.submit`). That is the
same capability Pi's `sendUserMessage(..., {deliverAs: "followUp", triggerTurn: true})`
gives, and more than Command Code's mod (which must park in `sleep`).
Source and contract: your harness's watch-wake extension/mod documentation.

## Primary: the `watch-wake` mod

Tools (auto-allowed by the mod):

| Tool | Use |
|---|---|
| `mcp__watch-wake__watch_wake_register` | pure-observer watch on a CHILD + local wake here (`session_id`, `conditions`, `message`, `max_wakes`, `interval_seconds`) |
| `mcp__watch-wake__watch_wake_list` | registrations + deadline state; read it after any compaction or resume |
| `mcp__watch-wake__watch_wake_cancel` | stop waking; deletes the server watch only if its generation is still ours |
| `mcp__watch-wake__wake_deadline` | `arm` / `status` / `cancel` one model-free local wait window (0–86400 s) |

### The shape

```text
1. watch_wake_register on the child (event_type agent_end; interval 10–60 s)
2. wake_deadline arm  (window + headroom; wait_label = the wave)
3. Record ids in your STATE file.
4. END THE TURN — one short line, zero further tool calls.
   → the wake arrives as a new turn; reconcile everything, then cancel the deadline.
```

In a live test, an idle parent was woken shortly after the child's `agent_end`; the deadline
did not fire.

### Properties worth relying on

- **Zero tokens while waiting:** the polling is local and model-free; no turn is open.
- **Wakes a fully idle session**; a busy parent gets the wake as soon as its turn ends.
  Such a held wake can be **stale** — its event may already be handled; check the receipt
  times against your checkpoint. Several firings may arrive as one coalesced "N wakes
  arrived together" message: reconcile every child once.
- **Survives resume:** registrations and the deadline persist per Claude session id;
  `claude --resume <id>` restores them from the saved cursor, so firings that happened
  while no process ran are consumed, not skipped.
- **Loud failure:** a watch deleted, replaced or reloaded `detached` (server restart)
  arrives as one stale-notice wake; ten consecutive poll failures send one notice.
- **One wake per new firing batch**, bounded by `max_wakes`; a failed delivery retries
  without spending the budget.

### What it cannot do

- It needs a **running `claude` process** — keep the terminal/tmux pane open. The deadline
  is an in-process timer too: it bounds a missed watch wake, not a dead parent.
- It refuses `-p`/SDK sessions (their host drives them; use `onFire` if managed).
- A redeploy of the mod (hot reload) drops its timers: never redeploy under a waiting parent.
- Like every watcher, it wakes only on observable state — use the hand-back protocol
  (`SKILL.md`) so a child's questions become observable.

## Zero-token discipline on Claude Code

- **Arm, then end the turn.** No in-turn `sleep`/`curl`/`/wait` loops (foreground `sleep`
  is blocked), no `tmux capture-pane` peeking, no status re-checks of something already armed.
- **One primary and one backstop per window.** With the mod armed, do not add a background
  poller for the same child "just in case"; the deadline is the backstop. Use the background
  watcher as the backstop only when the mod itself is under suspicion.
- **No model-backed timers.** Do not spawn an agent whose job is to sleep; both backstops
  above are model-free.
- **Compaction anchor.** Claude may auto-compact and forget ids. Keep a
  short `STATE.md` in your scratchpad recording the socket location, the credential
  file location, and every id (session, run, lease, registration, deadline); after any
  compaction or resume read it, then `watch_wake_list`.

## Fallback: the exiting background watcher

Claude Code's Bash tool takes `run_in_background: true`. The command runs detached,
survives across turns, and when it **terminates** the harness re-invokes the agent with a
completion notification. A poll loop that exits when its condition is met is therefore a
wake. Use it when the mod tools are absent, as an independent backstop when the mod is
suspect, and for non-Internal-API waits (builds, jobs, measurement windows).

```bash
#!/usr/bin/env bash
# Exits when the thing you care about has happened. Exiting IS the wake.
i=0
while [ $i -lt 420 ]; do                    # hard cap: 420 x 60s = 7h
  if <terminal condition>; then
    echo "TERMINAL after $i min: <what happened>"
    <print the evidence you will want on wake>
    exit 0
  fi
  <renew any lease / heartbeat here, every ~30 iterations>
  [ $((i % 15)) -eq 0 ] && echo "[$i min] <progress>"   # readable log
  sleep 60; i=$((i+1))
done
echo "GAVE UP after 7h; last state: <...>"
```

Launch it with `run_in_background: true` and **return your turn immediately**. For an
Internal API child, the terminal condition is best a held
`GET /api/v1/watches/wait?ids=<watchId>&timeout=300000&cursor=<c>` on a pure-observer watch
(advance the cursor every round) or the `?sinceIndex=N` poll.

Properties: it survives multi-hour interruptions of the parent's usage window (observed),
and it is cheaply re-armable — chain watchers across a long job. A capped watcher polling the child's `busy` flag and its review file can wake the parent when
it exits. Require the deliverable **and** a few consecutive idle polls, since a Pi child can read `busy:false` while
it auto-compacts.

## Things learned the hard way on Claude Code

1. **Watch the deliverable, not the run status.** A child that dispatches its own worker
   and yields reports `status: completed` while the work continues. Prefer a signal that is
   only true when the work is done (a file, a commit, `goal_end`); build stuck-detectors on
   the liveness discriminator, never on a status file the child writes by choice.
2. **Always cap background loops.** An uncapped watcher is a process you will forget; the
   cap is also your "something went wrong" signal.
3. **Renew leases from inside a long background watcher** — your turn is not running. (With
   the mod, give the child durable retention sized for the window instead.)
4. **Never match your own process.** `pgrep -f "string"` matches the shell running it;
   match the executable name or exclude `$$` and `$PPID`.
5. **Do not filter the output you will need.** Piping a watcher through `grep`/`tail`
   discards the detail you wake up wanting and makes failures read as successes.
6. **A server-side watch is not a wake.** Before ending the turn, name the tool call that
   will start your next turn (`watch_wake_register` result, or the background task id).
7. **Assert on stream output in `claude -p` checks.** A stop hook can replace a `-p` run's
   final text with its own prompt.

## Related

- `SKILL.md` — the pre-idle checklist, supervision rules and backstop selection.
- `references/antigravity-reactive-watcher-and-schedule.md` — the Antigravity equivalent.
- `references/supervision-and-stuck-detectors.md` — hand-back protocol, liveness discriminator.
- `pi-web-ui-internal-api-orchestration/references/claude-code-orchestrator.md` — dispatch,
  fan-in, managed-Claude `onFire`, routing and restarts for Claude parents.
