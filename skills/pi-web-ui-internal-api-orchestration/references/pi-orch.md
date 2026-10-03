<!-- Loaded from SKILL.md "Connect from anywhere". Read before your first pi-orch call in a run, and before dispatching a programme through it. Source of truth: the pi-orch README and `pi-orch help`; when they disagree with this file, they win. -->

# `pi-orch`: the parent client for the Internal API

`pi-orch` (https://github.com/valtterimelkko/pi-orch; zero runtime dependencies, Node >= 22.18). It builds every request against a drift-guarded contract snapshot, sends `X-Parent-Session` when it knows your session id (`PI_ORCH_PARENT_SESSION`, `PI_WEB_UI_SESSION_ID`, `PI_SESSION_ID`, or `--parent-session`), honours `Retry-After`, and returns documented exit codes. Programmes dispatch through it, not through hand-written curl: dispatch scripts drift from the contract, and children created outside it never enter its ledger. Use `--json` for machine output and `--id-only` (spawn: session id; prompt: run id; watch register/list: watch id) for `$(...)` capture; never parse the human text.

## Verbs

| Verb | What it does |
|---|---|
| `capabilities`, `capacity`, `models --runtime pi [--match sub]` | contract version, admission preflight, live selectors (exactly one match, or refuse) |
| `spawn --runtime rt --cwd dir` | create a child: `--model-selector SEL`, `--thinking L`, `--owner ID --ttl S [--label L]` (durable retention), goal flags, `--preflight-path/--preflight-tool`, `--route-limit 'SEL=N'`, `--wait-for-slot S` |
| `goal <sessionId> start --goal-objective "…"` | arm a goal on an already-created child, with the same `--goal-max-turns`, `--goal-verify`, `--goal-budget-tokens` flags and the same completion-template delivery as `spawn` (exit 22 if the template is not delivered). Arms only; pause, resume and clear stay raw API calls |
| `prompt <sessionId> --message "…"` | detached dispatch with an idempotency key; `--mode prompt\|follow_up\|steer`; adds the completion instruction unless `--no-completion-template` |
| `wait <sessionId>` / `wait --all\|--any id[@runId] …` | watch-backed long poll; settles on the run or, for a goal child, the goal outcome (pass `--objective` or let it read the goal projection). On contract ≥ 1.60.0 an auto-continue of a restart-interrupted Pi goal child is progress: the wait keeps going and the JSON reports `"autoContinues": <n>`; a visible stop (`paused` + `pausedReason: "interrupted"`) settles exit 5 with `interruption.cause`/`continueCount` in the JSON and a resume-or-re-dispatch note. `--deadline S` (default 1800) |
| `watch <sessionId> register\|list\|delete` | register a server watch (`--conditions agent_end,goal_end,paused,question:TEXT,deadline:S`, `--label`, `--pin`, `--fire-if-settled`), read it back, delete it. Never waits |
| `result <runId>` | final text, parsed `completion` block, `outputClass` (`command` for a slash-command return such as a `/goal` arm, `final_text`, `no_text`) |
| `verify <sessionId> [--run-id] [--since ref] [--rerun "cmd"]` | read-only check of the completion claims: verdict `verified` (exit 0), `contradicted` (20), `unverifiable` (21) |
| `status [--parent id \| --owner id \| <sessionId>]` | children: busy, goal state (interruption facts — cause, continueCount, autoContinued — when the server holds them), last run |
| `cleanup <sessionId> [--lease id --owner id] [--watch id]` | release the owned lease, then delete |

Unknown flags are a usage error (exit 2, before any request): a typo cannot silently change what a child receives. `wait --slice` is a deprecated no-op.

## Dispatching a long-running goal child

```bash
SID=$(pi-orch spawn --runtime pi --cwd <worktree> --model-selector <live-selector> --thinking high \
      --owner orch-<programme>-<parentShort8>-<lane> --ttl 14400 \
      --goal-objective "<one line: the aim, the evidence, the record>" --goal-max-turns 40 \
      --goal-budget-tokens <N> --id-only)
```

- **Always pass `--goal-budget-tokens` for a child that may run long.** The server default is 5,000,000 tokens and pauses long goals mid-run (a budget pause, not a failure); `pi-orch` prints a stderr note when you omit it. Size the budget to the task and the route: a long lane on a slower subscription route needed tens of millions. Validated 1..1,000,000,000.
- **The objective must be a single line**: the goal API rejects newlines (and `pi-orch` refuses them first). Keep the long text in the brief file and point at it.
- Goal flags without an objective, or an empty objective, are exit 2: they never create a plain child by accident.
- The completion template is added to a goal objective by default (a pointer in the objective, the full instructions as one queued follow-up). `spawn` re-sends it only after a provable non-delivery; both attempts failing exits 22 (the child holds only the pointer: re-send or re-dispatch). For a goal child the template tells it to put `Status: GOAL_ACHIEVED` on its own line immediately before the `pi-completion/v1` block (`orchestrated-child-worker` §2).
- Create-then-goal (`spawn` without goal flags, then `goal <sid> start …`) is the right order when you must register the watch before the goal starts.

## Owner ids, lineage and `status --owner`

A Claude Code parent is not a Pi Web UI session, so its children carry no `parentSessionId`; the retention `--owner` is their only lineage. Use `orch-<programme>-<parentShort8>-<lane>` (`parentShort8` = the first 8 hex characters of your session id), unique per parent and lane. `pi-orch status --owner <id>` lists that owner's children from the per-host spawn ledger: best-effort, children of other clients never appear, and an entry is pruned only when its session is deleted, not when it goes idle. Pi parents are linked by `X-Parent-Session` instead (`status --parent <id>`). Keep the convention: the same ids are how route caps count your children.

## Waiting: pick one pattern per dispatch

- **Idle (interactive parents; the default for programmes).** Register a watch on the child and **end your turn**; the wake arrives while you hold no tokens. On Claude Code that registration is the `watch-wake` mod's `mcp__watch-wake__watch_wake_register` plus `wake_deadline` (`references/claude-code-orchestrator.md`, `long-horizon-waiting-strategies`). `pi-orch watch register` only creates a server-side pure-observer watch (no `onFire`): by itself it delivers nothing to a bare CLI, and a foreign watch makes the mod refuse to register its own. Use it where something else supplies the delivery (an exiting background watcher polling the printed watch id, `wait-watch.sh` on Antigravity) or for `list`/`delete`.
- **In-turn (scripts, batch parents).** `pi-orch wait <sid>` blocks the caller until the child settles; exit 3 is the deadline (re-wait, never re-dispatch). It never fits the idle pattern: it holds your turn.
- `watch <sid> delete` is generation-safe: it sends the generation from `--generation` or from a fresh read, a replaced watch is refused (exit 19), and with no generation available it fails closed (exit 19) unless you pass `--force-unconditional` (the legacy blind delete; do not use it on a watch you do not own).

## Per-route concurrency (exit 25)

`pi-orch` caps your live children per model selector: built-in `zai/glm-5.3-flash: 5` (that route stops completing above roughly 5-8 concurrent children), others unlimited until set by `PI_ORCH_ROUTE_LIMITS` (JSON map) or `--route-limit 'SEL=N'` (`0` lifts it). Over the cap `spawn` refuses before creating anything with exit 25; `--wait-for-slot S` waits instead (timeout exit 3). Only spawns that name `--model-selector` are counted. A `prompt` that would start a new turn on an idle child of a limited route is gated the same way; `steer` never is. Bare-CLI callers are counted by `--owner`, so one owner per parent and programme. Spread a large wave across routes rather than queueing it on one.

## Exit codes to branch on

`0` ok · `2` usage (bad verb or flag) · `3` deadline (still working: re-wait) · `5` interrupted — a visible stop the server did not continue (cause + continueCount + a resume-or-re-dispatch note in the JSON), or a run the restart reconciliation cut off · `6` never started · `16` wait target not found · `17` goal cleared · `18` create unknown (the session may exist: reconcile with `status`, never blindly re-spawn) · `19` watch conflict or refused delete · `20`/`21` verify contradicted/unverifiable · `22` goal template not delivered · `25` route limit. Full table in the pi-orch README.

## Receipts and claims

- A refused-then-retried prompt leaves one cancelled, never-started receipt per refused attempt: count a child's runs by settled runs, not receipt totals.
- The completion block is the child's claim. `verify` checks claimed commits exist (and are reachable from `--since`), each `filesChanged` path shows change evidence, and re-runs a test only when you name the exact command with `--rerun`. A `contradicted` verdict is a correction item.
- `pi-orch` warns `SNAPSHOT_STALE` when `/capabilities` reports a different contract version than its bundled snapshot: read the contract's exception table before trusting a shape.
