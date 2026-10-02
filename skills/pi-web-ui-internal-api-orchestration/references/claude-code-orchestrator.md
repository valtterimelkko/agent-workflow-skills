# Claude Code Orchestrator Playbook — the Internal API side

> **Audience:** MANDATORY when the parent orchestrator is **Claude Code** — the interactive
> `claude` CLI, `claude -p`, or a Claude session Pi Web UI manages. Pi, Command Code and
> Antigravity parents use `walk-away.md` / `antigravity-orchestrator.md`.
> **Wake mechanics live in the waiting skill:**
> `long-horizon-waiting-strategies/references/claude-code-watch-wake-and-background-watcher.md`
> (the `watch-wake` mod, `wake_deadline`, the exiting background watcher, zero-token and
> compaction discipline, limits). Read it before your first idle window. This file adds only
> what the Internal API needs on Claude Code; runtime-neutral guidance stays in `SKILL.md`.

## 1. Which Claude you are decides the wake route

| You are… | Route |
|---|---|
| Bare interactive CLI | pure-observer watch **via a watch-wake extension/mod for your harness** (register and poll it there; never a hand-rolled `onFire`) |
| Managed Claude session (Pi Web UI created you) | **server `onFire`** targeting your own internal session id (§3) |
| `claude -p` | nothing can wake it: dispatch detached and hand back, or orchestrate from an interactive/managed parent |

A server-side watch armed by a script or curl is not your wake on a bare CLI. Before ending
a turn, name the tool call that starts your next one.

## 2. Bare CLI: dispatch-and-idle

```text
1. Discover capabilities, capacity and models (`pi-orch capabilities|capacity|models`); check the provider's remaining quota in its own dashboard or CLI; pick the route (routing.md).
2. pi-orch spawn --runtime pi --cwd <worktree> --model-selector <sel> --thinking <lvl> \
     --owner orch-<programme>-<parentShort8>-<lane> --ttl <window+headroom> [goal flags] --id-only
     -> sessionId. Goal child that may run long: --goal-objective "<one line>" --goal-budget-tokens <N>
3. Use a watch-wake extension/mod for your harness to register a watch on `<child>`
     **before dispatch**: conditions=[{"id":"done","type":"event_type","eventType":"agent_end"}]
     and message="Child {{sessionId}} fired {{conditionId}} at {{firedAt}} — reconcile it."
4. pi-orch prompt <child> --message "…" --id-only                                         -> runId
5. Arm the watch-wake extension/mod's model-free deadline (window + headroom)
6. STATE file + milestone notification if warranted, then END THE TURN.
```

**Do not hold `pi-orch wait` in your turn** (it blocks the turn; it is for scripts and in-turn
waits), and do not register the child's watch with `pi-orch watch register` as your wake: that
creates a server-side watch with no delivery to a bare CLI, and the mod then refuses to
register over a foreign watch. The mod's tool is the registration. A Claude Code parent is not
a Pi Web UI session, so its children carry no parent lineage: the `--owner` id above is how
`pi-orch status --owner <id>` finds them and how they are counted (`pi-orch.md`). Raw `POST /sessions` remains the
fallback for what `pi-orch` does not cover.

On wake: reconcile **every** owned child against durable evidence (`evidence.md`), cancel
the deadline by its exact id once the window is settled, cancel the watch-wake registration
for work that is done, release the exact lease you own
(`{"action":"release_retention","retentionLeaseId":"<leaseId>"}`), delete disposable children.

- **Fan-in:** one registration per child (one server watch per session); each has its own
  wake budget; any wake → reconcile all children.
- **Multi-turn / goal children:** `max_wakes` > 1 **with `"once": false` on the condition**
  (the server default `once: true` fires only once, making extra wakes unreachable); for
  goals watch `goal_end` plus a state-filtered question/pause (`goals.md`).
- **API-created children normally produce one terminal turn** (contract 1.47.0). If a
  harness-specific setting opts a child into an additional lifecycle turn, expect a
  second `agent_end` minutes later and `abort` before deleting a still-busy child.
- **After a stale notice,** check the child's run receipt before re-registering: a new watch
  cannot see an `agent_end` that already happened.
- **Someone else's watch on the child** (label not `watch-wake:` or has `onFire`): the mod
  refuses, because registering would replace it and wipe its ledger. Use the relay pattern
  (`walk-away.md`); `replace: true` only for a watch you own.
- **Linkage header:** a bare CLI has no internal session id — omit `X-Parent-Session` rather
  than inventing one, and track the child tree yourself.

## 3. Managed Claude parent: server `onFire`

Register the watch on the child **with** `onFire` `{targetSessionId: <your internal id>,
mode: "follow_up"}` (`walk-away.md`). Claude specifics: `follow_up` into a busy Claude session
returns `409 SESSION_BUSY` (no queue) and a transient failure gets one bounded retry after
`cooldownSeconds`, so end your turns promptly; `steer` joins a running turn only on the SDK
backend (`runtimes.claude.supportsSteer`). The mod refuses non-interactive sessions by design.
Your own internal id is `$PI_WEB_UI_SESSION_ID` (contract 1.47.0). Backstop: a second watch
condition `{"type":"deadline","afterSeconds":N}` on the same `onFire` watch — model-free and
server-side, it never keeps your turn busy (`walk-away.md`).

## 4. Routing notes specific to a Claude parent

- `routing.md` is harness-neutral; a Claude parent does **not** imply Claude children.
- A parent may already draw on a scarce provider pool: keep the parent for planning,
  adjudication and verification; check current provider capacity and quota in the
  provider's own dashboard or CLI, send routine children to an available route, and
  reserve specialist routes for work where that capability is load-bearing.
- Claude children: `runtime: "claude"`, the exact live `/models` entry, binding verified from
  the create response or `/info` (`sessions.md`). Claude is **SDK-only** on the API (contract
  1.46.0): `/models?runtime=claude` lists SDK profiles only, and a create, prompt, watch wake,
  goal dispatch or batch item that resolves to any other backend fails
  `403 CLAUDE_BACKEND_NOT_ALLOWED` (`features.claudeBackendPolicy` in `/capabilities`). Do not
  work around it; pick a listed profile, and `steer` is therefore available on Claude children.
- Adopting a Claude CLI session as a child needs the operator's confirmation that they have
  exited that CLI first (`adoption.md`).

## 5. Production restarts

Same protocol as every harness (`orchestrator-governance.md` §3–§4): only with the responsible operator's
authority, through `production:drain-restart` (the drain is the gate; on a server older than
contract 1.52.0 pause goal-armed children first), never from inside a child. Afterwards watches rehydrate; the mod keeps polling with its
cursor, and a watch that reloaded `detached` arrives as a stale-notice wake — re-register it.
