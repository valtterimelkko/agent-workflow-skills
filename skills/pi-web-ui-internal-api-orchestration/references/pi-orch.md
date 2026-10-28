<!-- Loaded from SKILL.md "Connect from anywhere". Read before your first pi-orch call in a run, and before dispatching a programme through it. Source of truth: the pi-orch README (https://github.com/valtterimelkko/pi-orch) and `pi-orch help`; when they disagree with this file, they win. -->

# `pi-orch`: the parent client for the Internal API

`pi-orch` on `PATH` — the bin of the pi-orch repo (github.com/valtterimelkko/pi-orch; zero runtime dependencies, Node >= 22.18). It builds every request against a drift-guarded contract snapshot, sends `X-Parent-Session` when it knows your session id (`PI_ORCH_PARENT_SESSION`, `PI_WEB_UI_SESSION_ID`, `PI_SESSION_ID`, or `--parent-session`), honours `Retry-After`, and returns documented exit codes. Programmes dispatch through it, not through hand-written curl: dispatch scripts drift from the contract, and children created outside it never enter its ledger. Use `--json` for machine output and `--id-only` (spawn: session id; prompt: run id; watch register/list: watch id) for `$(...)` capture; never parse the human text.

## Verbs

| Verb | What it does |
|---|---|
| `capabilities`, `capacity`, `models --runtime pi [--match sub]` | contract version, admission preflight, live selectors (exactly one match, or refuse) |
| `spawn --runtime rt --cwd dir` | create a child: `--model-selector SEL`, `--thinking L`, `--owner ID --ttl S [--label L]` (durable retention), goal flags, `--preflight-path/--preflight-tool`, `--route-limit 'SEL=N'`, `--wait-for-slot S` |
| `goal <sessionId> start --goal-objective "…"` | arm a goal on an already-created child, with the same `--goal-max-turns`, `--goal-verify`, `--goal-budget-tokens` flags and template rule as `spawn` |
| `goal <sessionId> pause [--reason R] \| resume [--note N] \| show` | pause/resume/read a goal (the server ignores reason and note up to 1.62.0). Clear stays a raw API call |
| `reroute <sessionId> --model-selector SEL [--thinking L]` | switch a goal child's model: pause, abort, set_model, resume; the goal stays intact (under 2 s live) |
| `template [--goal]` | print the completion instructions to paste into the brief file |
| `prompt <sessionId> --message "…"` | detached dispatch with an idempotency key; `--mode prompt\|follow_up\|steer\|deliver` (`deliver` = steer if busy and steer-capable, else follow_up); adds the completion instruction unless `--no-completion-template` |
| `wait <sessionId>` / `wait --all\|--any id[@runId] …` | watch-backed long poll; settles on the run or, for a goal child, the goal outcome (pass `--objective` or let it read the goal projection). On contract ≥ 1.60.0 an auto-continue of a restart-interrupted Pi goal child is progress: the wait keeps going and the JSON reports `"autoContinues": <n>`; a visible stop (`paused` + `pausedReason: "interrupted"`) settles exit 5 with `interruption.cause`/`continueCount` in the JSON and a resume-or-re-dispatch note. `--deadline S` (default 1800) |
| `watch <sessionId> register\|list\|delete` | register a server watch (`--conditions agent_end,goal_end,paused,question:TEXT,deadline:S`, `--label`, `--pin`, `--fire-if-settled`), read it back, delete it. Never waits |
| `result <runId> [--final]` | final text, parsed `completion` block, `outputClass` (`command` for a slash-command return such as a `/goal` arm, `final_text`, `no_text`) |
| `verify <sessionId> [--run-id] [--since ref] [--rerun "cmd"] [--gates-file brief [--cwd D] [--gate-timeout S]]` | check the completion claims: verdict `verified` (exit 0), `contradicted` (20), `unverifiable` (21). `--gates-file` re-runs the brief's `GATES:` block (lines `- cmd → exit`): a red gate exits 20, a refused mutating gate 21 |
| `lane run <lane-dir> [--dry-run] [--continue correction] [--deadline S]` | run one lane end to end (see *Lane runner*) |
| `status [--parent id \| --owner id \| <sessionId>] [--json]` | children: busy, status, `lastRun{runId,status,endedAt}`, goal state (interruption facts when the server holds them). `--owner` lists every ledger child until deleted |
| `cleanup <sessionId> [--lease id --owner id] [--watch id]` or `cleanup --owner id` | release the lease, then delete. `--owner` alone cleans every child of that retention id (watch, lease, delete). `spawn --id-only` drops the lease id: use `spawn --json` |

Unknown flags are a usage error (exit 2, before any request): a typo cannot silently change what a child receives. `wait --slice` is a deprecated no-op.

## Lane runner (the default for single-repo lanes with a machine-checkable `GATES:` block; hand-run anything else)

`pi-orch lane run <lane-dir>`: spawn → watch → dispatch → wait → `GATES:` → one correction → cross-family review → one closure. Run it as a background process whose exit is the wake (Claude Code `run_in_background`, a Pi background-shell tool, Antigravity `run_command`), with a backstop; `--dry-run` first.

Lane dir: `lane.json` (template in `assets/programme-kit/`), `brief.md` ending in `GATES:`, `review-brief.md` with a `VERDICT FILE: <path>` line, optional `correction-template.md`.

Exits: `0` done · `3` deadline, re-run · `25` route cap · `40` question · `41` gates red · `42` verdict (`--continue correction`) · `43` runner error. Re-running resumes from the journal.

## Dispatching a long-running goal child

```bash
SID=$(pi-orch spawn --runtime pi --cwd <worktree> --model-selector <live-selector> --thinking high \
      --owner orch-<programme>-<parentShort8>-<lane> --ttl 14400 \
      --goal-objective "<one line: the aim, the evidence, the record>" --goal-max-turns 40 \
      --goal-budget-tokens 60000000 --id-only)
```

- **Always pass `--goal-budget-tokens` for a child that may run long.** The server default is 5,000,000 tokens and pauses long goals mid-run; `pi-orch` prints a stderr note when you omit it. Measured programme lanes needed tens of millions (40–60 million) rather than the default. Validated 1..1,000,000,000.
- **The objective must be a single line**: the goal API rejects newlines (and `pi-orch` refuses them first). Keep the long text in the brief file and point at it.
- Goal flags without an objective, or an empty objective, are exit 2: they never create a plain child by accident.
- A goal child no longer gets the completion template as a queued follow-up: **paste `pi-orch template --goal` into the brief file**. `--template-follow-up` opts back in (a pointer in the objective, the instructions queued); exit 22 only then, when it was not delivered. The goal template puts `Status: GOAL_ACHIEVED` on its own line immediately before the `pi-completion/v1` block (`agent-os-child` §2).
- Create-then-goal (`spawn` without goal flags, then `goal <sid> start …`) is the right order when you must register the watch before the goal starts.

## Retention ids, lineage and `status --owner`

A Claude Code parent is not a Pi Web UI session, so its children carry no managed `parentSessionId`; the retention `--owner` is their only local lineage (a server on contract ≥ 1.63.0 also records the native parent id). Use `orch-<programme>-<parentShort8>-<lane>` (`parentShort8` = the first 8 hex characters of your session id), unique per parent and lane. `pi-orch status --owner <id>` lists that id's children from the per-host spawn ledger (`~/.pi-orch/spawn-ledger.json`): best-effort, children of other clients never appear, and an entry stays until its session is deleted. The ledger is a frozen JSON-array interface other tools read; history is in `spawn-ledger.events.jsonl`, and `~/.pi-orch/audit.jsonl` records every verb. Pi parents are linked by `X-Parent-Session` instead (`status --parent <id>`). Keep the convention: it is the only lineage a bare-CLI parent has.

## Watch JSON: copy, never hand-write

Register with the canonical block for the child kind (`long-horizon-waiting-strategies`, *Canonical watch blocks*). Always pass `--objective` for goal watches: `watch register` and `wait` then match both the raw text and the stored form the server holds. Without it a goal condition wakes on any goal. On contract 1.62.0 goal events carry a top-level `goalId`: match `dataMatch {"goalId":"…"}` (pi-orch keys on it once it ships it).

## Waiting: pick one pattern per dispatch

- **Idle (interactive parents; the default for programmes).** Register a watch on the child and **end your turn**; the wake arrives while you hold no tokens. On Claude Code that registration is the `watch-wake` mod's `mcp__watch-wake__watch_wake_register` plus `wake_deadline` (`references/claude-code-orchestrator.md`, `long-horizon-waiting-strategies`). `pi-orch watch register` only creates a server-side pure-observer watch (no `onFire`): by itself it delivers nothing to a bare CLI, and a foreign watch makes the mod refuse to register its own. Use it where something else supplies the delivery (an exiting background watcher polling the printed watch id, `wait-watch.sh` on Antigravity) or for `list`/`delete`.
- **In-turn (scripts, batch parents).** `pi-orch wait <sid>` blocks the caller until the child settles; exit 3 is the deadline (re-wait, never re-dispatch). It never fits the idle pattern: it holds your turn.
- `watch <sid> delete` is generation-safe: it sends the generation from `--generation` or from a fresh read, a replaced watch is refused (exit 19), and with no generation available it fails closed (exit 19) unless you pass `--force-unconditional` (the legacy blind delete; do not use it on a watch you do not own).

## Per-route concurrency (exit 25)

`pi-orch` caps your live children per model selector: one built-in default of 5 (that route stops completing above roughly five to eight concurrent children), others unlimited until set by `PI_ORCH_ROUTE_LIMITS` (JSON map) or `--route-limit 'SEL=N'` (`0` lifts it). Over the cap `spawn` refuses before creating anything with exit 25; `--wait-for-slot S` waits instead (timeout exit 3). Only spawns that name `--model-selector` are counted. A `prompt` that would start a new turn on an idle child of a limited route is gated the same way; `steer` never is. Bare-CLI callers are counted by `--owner`, so use one retention id per parent and programme.

## Exit codes to branch on

`0` ok · `2` usage (bad verb or flag) · `3` deadline (still working: re-wait) · `5` interrupted — a visible stop the server did not continue (cause + continueCount + a resume-or-re-dispatch note in the JSON), or a run the restart reconciliation cut off · `6` never started · `16` wait target not found · `17` goal cleared · `18` create unknown (the session may exist: reconcile with `status`, never blindly re-spawn) · `19` watch conflict or refused delete · `20`/`21` verify contradicted/unverifiable · `22` goal template not delivered (only with `--template-follow-up`) · `25` route limit, or a full Claude profile (the overflow hint is printed; a server `PROFILE_CAPACITY_EXHAUSTED` is never sat out silently). Full table in the pi-orch README.

## Receipts and claims

- Server 1.62.0: no `goal_end` from a never-started receipt; `goal_state {stalled:true, stalledForMs}` after `GOAL_STALL_MINUTES` (default 10); admission refusals caused by quarantined leases carry `reason:"quarantined_debt"`.
- A refused-then-retried prompt leaves one cancelled, never-started receipt per refused attempt: count a child's runs by settled runs, not receipt totals.
- The completion block is the child's claim. `verify` checks claimed commits exist (and are reachable from `--since`), each `filesChanged` path shows change evidence, and re-runs a test only when you name the exact command with `--rerun`, or the brief's gates with `--gates-file`. A `contradicted` verdict is a correction item.
- `pi-orch` warns `SNAPSHOT_STALE` when `/capabilities` reports a different contract version than its bundled snapshot: read the contract's exception table before trusting a shape.
