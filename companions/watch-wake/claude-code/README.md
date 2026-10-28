# watch-wake — Claude Code plugin

Lets a bare `claude` CLI session — which the Pi Web UI server cannot prompt — be
**woken with a new turn** when a Pi Web UI Internal API watch on a **child**
session fires. Plus a model-free `wake_deadline` backstop.

The shared design, the condition specification, the safety properties and the
step-by-step parent workflow are in [`../README.md`](../README.md). This file
covers the Claude Code wiring, install and behaviour.

```
parent (this claude CLI) ── watch_wake_register(child) ──► POST /sessions/<child>/watch
   │                                                        (pure observer, no onFire,
   │  END TURN, idle: zero tokens                            durable ledger, CAS generation)
   │
   │  timer (5 s) → due? GET /sessions/<child>/watch?sinceIndex=N   (local, model-free)
   │                                   │ new firing
   ▼                                   ▼
new turn starts ◄──────────── $.prompt.submit(wake text)
```

## How it differs from the Pi port

| | Pi extension | **Claude Code plugin** |
|---|---|---|
| Idle parent woken? | yes (`followUp` + `triggerTurn`) | **yes** — `$.prompt.submit` starts a turn once the session is idle |
| Busy parent | steer at the next tool boundary | held in one outbox; delivered when the current turn ends |
| Transport | Node `http` over the Unix socket | the plugin's `http.fetch` with `socketPath` (a `curl` fallback for engines without it) |
| Persistence | session custom entries | the plugin store, one key per Claude session id |
| Deadline backstop | `wake_deadline` | `wake_deadline` (same contract) |
| Engine-level tests | a fake Pi host | the real hooks engine |

The two ports implement the same contract against the same server endpoints.

## Tools

| Tool | Purpose |
|---|---|
| `mcp__watch-wake__watch_wake_register` | Pure-observer watch on a CHILD (any runtime Pi Web UI manages) plus a local wake here. |
| `mcp__watch-wake__watch_wake_list` | Registrations (child, status, wakes, cursor, generation, last error) and the deadline state. |
| `mcp__watch-wake__watch_wake_cancel` | Stop waking; delete the server watch only if its generation is still ours. |
| `mcp__watch-wake__wake_deadline` | `arm` / `status` / `cancel` one model-free local wait-window backstop (0–86400 s). |

All four are auto-allowed by the plugin's own tool-check hook: they touch only the
local watch registry and a local timer, so an orchestrating parent is not stopped
by a permission dialog just before it goes idle.

### Register

```json
{
  "session_id": "<child internal session id>",
  "conditions": [{ "id": "done", "type": "event_type", "eventType": "agent_end" }],
  "message": "Child {{sessionId}} fired {{conditionId}} at {{firedAt}} — reconcile it.",
  "max_wakes": 1,
  "interval_seconds": 30
}
```

Additional parameters beyond the shared spec:

| Parameter | Effect |
|---|---|
| `replace` | allow replacing an existing watch you own on that child (a foreign or `onFire` watch is otherwise refused) |
| `fire_if_settled` | if the child is already idle with a finished last run, record one immediate firing — needs server `features.watchFireIfSettled`; use when re-registering after a stale notice |
| `allow_headless` | force registration in a `-p`/SDK session, which is refused by default |

## Policy

- **Pure observer.** Never sets `onFire`; a managed parent and this local parent
  cannot both be woken by accident.
- **CAS when the server supports it** (`features.watchGenerationPreconditions`):
  register sends `expectedGeneration` (`null` when absent); cancel sends the
  observed generation and reports `deleted-confirmed` only on a matching
  acknowledgement. A watch with a foreign label or an `onFire` action is refused
  unless `replace: true`, because registering replaces the server's
  one-watch-per-session ledger. Use the relay pattern — server `onFire` on the
  child pointing at a disposable managed relay session, then watch the relay —
  when a child already carries a watch you must not clobber.
- **Cursor from zero.** A fresh or replaced ledger holds only post-registration
  firings, so a firing that races the POST still wakes you.
- **One outbox for every wake.** Watch firings, stale notices and the deadline are
  held while a main-loop turn runs, re-checked immediately before sending, and
  delivered as **one combined prompt** when the session goes idle — N children
  finishing during one busy turn cost one wake turn, not N. Cancelling a
  registration drops its held wake, so there is no late wake after cancel.
  `watch_wake_list` shows `pending_wake_since` for a held wake.
- **One wake per new firing batch**, bounded by `max_wakes` (1–10). `max_wakes >
  1` makes the conditions repeatable (`once: false`); an explicit `once: true`
  with it is refused. A rejected delivery does not consume the budget and does not
  advance the cursor.
- **A waiting-parent flag.** While anything is armed the plugin exports
  `CLAUDE_WATCH_WAKE_ARMED=1` into the session environment and clears it when
  nothing is left, so any host hook can tell that an orchestrator is waiting on a
  wake and defer work it would otherwise do at the end of a turn.
- **Stale is loud.** A vanished watch, a changed generation or a `detached` reload
  (server restart) marks the registration `stale` and **delivers one notice**, so
  an idle parent is not stranded. Ten consecutive poll failures deliver one notice
  and keep watching.
- **Restore on resume.** `session.start` re-attaches persisted registrations from
  their saved cursor (firings recorded while no parent process ran are consumed,
  not skipped), never re-registers, and marks replaced watches stale.
- **Non-interactive sessions are refused** (`-p`, SDK): the process exits or is
  host-driven, so a local wake has nowhere to land; a Pi Web UI-managed session
  should use the server's `onFire` wake instead. `allow_headless: true` forces it.
  **Exception:** Remote Control sessions (`claude remote-control` spawns, marked
  `CLAUDE_CODE_ENVIRONMENT_KIND=bridge`). Each is a long-lived headless SDK process
  that stays up between turns, and a submitted prompt starts a new turn there, so
  registration is allowed (`canLocalWake` in `hooks/core.ts`).

## Install

This is a Claude Code **function-hook plugin** ("mod"): a plugin folder with
`.claude-plugin/plugin.json` plus `hooks/hooks.json` naming one hooks module.

1. Copy the folder into the directory Claude Code loads plugins from:

   ```bash
   mkdir -p ~/.claude/mods
   cp -r companions/watch-wake/claude-code ~/.claude/mods/watch-wake
   ```

2. Enable hooks modules and point Claude Code at that folder. In
   `~/.claude/settings.json` (user scope — a project `.claude/settings.json`
   cannot set the plugin directory):

   ```json
   {
     "env": {
       "CLAUDE_CODE_ENABLE_FUNCTION_HOOKS": "1",
       "CLAUDE_CODE_PLUGIN_DIRS": "/absolute/path/to/.claude/mods"
     }
   }
   ```

   Use an absolute path; settings files do not expand `~`. `CLAUDE_CODE_PLUGIN_DIRS`
   takes a folder of plugins, and each child folder loads as if it had been passed
   with `--plugin-dir`.

3. Start a session. Interactive sessions hot-reload a plugin's files on save; `-p`
   and SDK runs load fresh. `--bare` and `--safe-mode` load no installed hooks
   modules, and `disableAllHooks` turns them off.

4. If your Pi Web UI does not use the documented default socket and token paths,
   set the overrides in the same `env` block:

   ```json
   { "PI_WEB_UI_SOCKET": "/path/to/internal-api.sock",
     "PI_WEB_UI_TOKEN_PATH": "/path/to/internal-api-token" }
   ```

The engine-level test path (`claude plugin test <dir>`) is **not** exercised by
this repository: the published tests are the pure-policy ones, which need no
Claude Code installation. Treat the engine wiring as validated upstream and
verify it in your own environment by registering a watch on a real child and
confirming one wake arrives.

## Structure

```
claude-code/
  .claude-plugin/plugin.json     plugin metadata
  hooks/hooks.json               names the hooks module: ["./register.ts"]
  hooks/register.ts              engine wiring: tools, transport, delivery, persistence, timer, status line
  hooks/core.ts                  pure policy: WatchWakeCore, DeadlineCore, Outbox, condition validation
  tests/core.test.mjs            policy tests (no engine, no network)
```

`core.ts` deliberately has no imports and no I/O — every effect is an injected
dependency — so the same file runs inside the hooks environment (where Node
modules may be unavailable) and under `node --test`. `register.ts` is wiring only:
it never makes a policy decision.

## Configuration

| Env var | Default |
|---|---|
| `PI_WEB_UI_SOCKET` | `~/.pi-web-ui/internal-api.sock` |
| `PI_WEB_UI_TOKEN_PATH` | `~/.pi-web-ui/internal-api-token` |

`HOME` is required to resolve those defaults; if it is unset, set both paths
explicitly. The token is read per request, never logged, and the `curl` fallback
passes the bearer header on stdin (`-H @-`) so it cannot leak through the process
table.

## Honest limits

- The wake needs a **running parent process**. If the `claude` process exits,
  nothing is delivered until the session is resumed, which restores the
  registration and consumes firings recorded meanwhile.
- Hot-reloading the plugin (redeploying its files) cancels its timers and module
  state in running sessions. Do not redeploy under a waiting parent; restart the
  parent to rebind.
- `wake_deadline` is an in-process timer: it bounds a missed watch wake while the
  parent is alive; it cannot resurrect a dead parent (the same limit as the Pi
  tool).
- A wake means "go look", never "done": reconcile receipts and transcripts before
  acting.

## Tests

```bash
cd companions/watch-wake/claude-code
node --test tests/*.test.mjs      # 33 policy tests, fake transport, no engine needed
```

They cover condition validation, foreign-watch refusal, CAS register/cancel,
cursor and budget behaviour, stale notices, outbox coalescing and cancel races,
deadline arm/expiry/restore, and the headless/Remote-Control wake decision.

## Part of the Pi Web UI orchestration set

- Pi Web UI — https://github.com/valtterimelkko/pi-web-ui
  (`docs/ORCHESTRATION-OVERVIEW.md`, `docs/INTERNAL-API-ORCHESTRATION.md`)
- pi-orch — https://github.com/valtterimelkko/pi-orch
- the pack — https://github.com/valtterimelkko/agent-workflow-skills/blob/main/packs/pi-web-ui-orchestration-pack/README.md
- the watch-wake companion — [`../README.md`](../README.md)
