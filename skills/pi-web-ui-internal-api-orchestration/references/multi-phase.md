<!-- Loaded from SKILL.md stub after "Choosing the route". Read when planning a multi-wave programme: dependent phases, shared repositories, concurrent child writers, or another agent lineage owning overlapping scope — before dispatching the first child. -->

# Multi-phase programmes: plan the organisation before the first dispatch

Most runs are **one wave**: dispatch, watch, fan in, done — SKILL.md §1–§9 plus
`patterns.md` cover that. A **programme** is different: a sequence of dependent
improvements executed over multiple waves, usually with fan-in, integration and
review phases between them, often in shared repositories alongside other active
agents. Orchestrators fail at the *joins* between waves, not inside them, so the
organisation is planned up front.

**Templates and runbooks** — the checkpoint, common and lane briefs, correction brief,
parent verification checklist, worktree/shared-dependency rules, merge order, deploy and
restart runbook and close-out — are in **`programme-kit.md`**. This file holds the principles.

## Is this a programme?

| Signal | Programme shape |
|---|---|
| Improvements form a dependency chain (later work needs an earlier interface stable) | **yes** — sequence into gated waves |
| Several waves with fan-in, integration or review between them | **yes** |
| Children (or the parent) write concurrently in shared repositories | **yes** — needs ownership contracts |
| Another agent lineage owns overlapping scope (check the board) | **yes** — needs a collision boundary |
| The supervision machinery itself is suspect (watch transport, goal lifecycle) | **yes** — plus a parent bootstrap wave |
| One comparison, one batch, one fan-out of independent items | **no** — use `patterns.md`; this file adds nothing |

## The three durable artefacts

The core trick: **write the programme down so it survives parent compaction and
restarts**. In-context memory does not survive; files do. Point the parent's
goal objective at the strategy file path, and re-read both after any compaction
or restart instead of trusting recalled context.

| Artefact | Mutability | What it holds |
|---|---|---|
| **Strategy document** | Stable; amended in place | Scope, waves, ownership, gates (see below) |
| **Live checkpoint** (`STATE.md`) | Rewritten at every fan-in/dispatch | Current state only (see below) |
| **Per-child brief + evidence directory** | One brief per child; evidence grows | The child's contract and its proof (see below) |

**Strategy document** — one authoritative file, never competing versions.
Carries a **status header with an approval-gated lifecycle**:
`PLANNING ONLY` → `READY, NOT STARTED` (the responsible operator endorses) → `EXECUTING` (the responsible operator
activates execution). Planning performs no dispatch; that activation is the
execution gate, and after it there is no redundant re-confirmation screen.
Amendments are **recorded in the file itself** ("latest amendment … supersedes
…"), so there is exactly one current truth. Contents: authority (including what
it does *not* permit), the **collision boundary** (what other active lineages
own, derived from the board and their checkpoints), the **team allocation**
(one bounded outcome + owned paths per child, plus a cap on concurrent
implementation workers), the **execution waves** with their gates, non-regression
gates, and stop/question boundaries. It **records scope, not completion**.

**Live checkpoint** — the strategy's mutable twin. Banner rule: *"current
state, not a completion claim — read before acting."* Holds: current stage;
committed/pushed evidence (with commit ids); per-child status
(accepted / rework running / rejected, with reasons and receipts); actual
wake-delivery ids; the **next sequence**; and honest counters (reviews
performed vs phases accepted vs objective-not-achieved). It is what a resumed
or compacted parent reads first, and what another agent reads to coordinate.

**Per-child brief + evidence** — under an operations directory per programme,
one directory per child: `brief.md` (bounded outcome, owned paths, authority
boundaries, TDD/validation requirements, handback format, stop protocol), the
child's `complete.md` handback (with a **FROZEN** marker and a changed-path
inventory), red/green logs, its `verify.sh`, the parent's review probes and
numbered correction briefs, per-fan-in wake records, and per-dispatch preflight
snapshots. **Preserve superseded handbacks** (rename, don't overwrite) — the
history of what was rejected and why is load-bearing evidence.

Brief in **two layers**: a wave-wide **common brief** (binding rules, gates, hand-back
protocol, completion block) and a short **lane brief** that overrides it only where it
says so explicitly. Each lane brief ends with frozen victory criteria **and a "Not victory
if:" line** naming the tempting shortcuts, and names the sibling lanes' paths in its
exclusions. Two more brief features pay for themselves:

- **A planned design gate for behaviour-critical lanes.** Phase A ends with the child
  writing `01-design.md` (or `01-attribution.md`) and ending its turn; you verify it and
  answer in `01-answer.md` before any implementation. In the reference programme this
  caught a design that would have cross-wired sessions before a line of it was written.
  Child-initiated questions are not a substitute: a child does not know which of its
  choices you would reject.
- **Decision rules fixed before measurement.** When a measurement will decide a parameter,
  write the mapping first ("passes at 300/s → 64 KB; only at 90/s → 32 KB; neither →
  16 KB") and base it on realistic load, not a lab worst case.

Templates: `programme-kit.md`.

## Deriving waves from the sequence

Children map onto the improvement sequence; the sequence is never derived from
available children.

1. **Evidence first.** Audit the session records/logs that motivated the work;
   derive a prioritised sequence from observed failures. Exclude anything owned
   by other active lineages (board + their checkpoint) — steal nothing.
2. **Wave 0 — parent bootstrap.** If the machinery the programme depends on
   (watch transport, goal lifecycle, wake delivery) is itself suspect, the
   parent repairs and TDD-proves it *before* any child starts, and commits the
   fix so children start from a clean baseline. **Do not depend on the tools
   being repaired** — supervise the first waves through the known-good path.
3. **Parallel waves.** Dispatch children together **only where owned paths are
   disjoint**. Each child gets a bounded goal (`goals.md`) plus its brief, and
   its own watch (`walk-away.md`).
4. **Gated waves.** A later phase starts only when its gate opens: the earlier
   child's interface is stable, or another lineage's overlapping work has
   landed. If a gate blocks a seam, **postpone the seam and continue
   independent work**; only when no independent work remains, pause with a
   bounded recovery wake — never poll in-turn, never take over ownership.
   Declare every dependency by **what the later step needs**, not only by order — three
   kinds: an **interface/path** (lane B builds on lane A's module), **data/evidence** (a
   threshold waits for lane A's measurement; lane B's unrelated parts can start now), and
   **deploy order** (artefact X must be live before the restart that activates Y). Write
   each into the live checkpoint the moment you discover it.
   **Crucial: sequence gating is parent-autonomous, not owner-gated.**
   When the earlier work lands and the shared repository is clear, the parent
   un-gates the seam wave and dispatches immediately without asking the operator
   for permission. Do not escalate routine single-writer staging to the operator.
5. **Integration wave.** Parent integrates **frozen, accepted** phases, owns
   shared glue/docs, and runs integrated acceptance at stable checkpoints: merge each
   lane as it is accepted, gate the integrated base once, push only when green. Where
   lanes were predicted to conflict, do a **trial integration merge** in a scratch
   worktree while the reviews run (`programme-kit.md`, *Merge and integration*).
6. **Review wave (per lane, not only at the end).** A **fresh, read-only reviewer
   session** — no implementation ownership, no self-sign-off, separate from every
   implementation child — reviews each lane after the implementer hands back and
   again after each correction. Full pattern in *The reviewer child* below.
7. **Review moments and interim waves.** When a review (yours or the owner's) finds that
   the plan's next wave would build on a defect, insert an **interim remediation wave**
   rather than folding the fixes into the next planned wave. Prefer the cheapest decisive
   proof for each fix (a synthetic or bounded run) over repeating a long validation; keep
   one long run only where nothing cheaper decides. Give the interim wave its own common
   brief and checkpoint, carry the previous wave's lessons at the top, and keep the old
   checkpoint as history. Amend the plan in place.
8. **New lanes mid-wave.** When a lane's result shows the scope is bigger than planned
   (the fix works but does not deliver the benefit), open a **new named lane** with its
   own checkpoint row and plan entry rather than stretching the old one. One child may own
   worktrees in two repositories for it; list both.
9. **Report code/test/deployment states separately.** Deployment stays
   separately permission-gated; execution approval never implies it.

## The reviewer child

Why: by the time an implementer hands back, both its context and yours are heavy with the
path taken. A fresh reviewer starts with only the diff, the brief and the evidence, so it
catches what both of you have stopped seeing, and it costs no context of yours.
Defects this has caught that handbacks and green suites missed: a module-scope shared-state
bug, a non-atomic seed/reload race, a claim measured at the wrong commit (15/16 reported
from a 14/16 commit), pending creates invisible to a drain, DELETE errors counted as
success, a confinement hole, and eviction orphaning running children.

**Sequence per lane:**
1. Implementer hands back (`complete.md` plus evidence bundle).
2. **You** read the diff and re-run the gates first; send any parent-found correction before spending reviewer tokens.
3. Create a **fresh** reviewer (route: `routing.md` → *Reviewer route*) and dispatch the review. Do not reuse the implementer, and do not reuse one reviewer across unrelated lanes.
4. Adjudicate the verdict yourself (below). Accept, or send one correction, then a closure review.

**Create and dispatch:**
- `POST /sessions` `{runtime:<the route's runtime>, model:<exact selector>, thinkingLevel:<highest advertised, e.g. "max">, cwd:<the implementer's worktree>, retention:{mode:"durable", ttlSeconds:<window+headroom>, ownerId:"<prog>-<lane>-reviewer"}}`; verify `fallbackApplied:false` and the effective model (`sessions.md`).
- The prompt carries the `orchestrated-child-worker` directive (SKILL.md §3), the role line "you are a read-only reviewer", and the verdict format. Dispatch detached (`verbosity:"answers"`, `detach:true`, an `idempotencyKey`) and save the request and receipt.
- Keep a reusable **reviewer brief file** and a short per-lane prompt (lane, worktree, branch, diff range, focus areas). Tell the reviewer that numbered `NN-answer.md` / `NN-correction.md` files amend the frozen brief, or it judges against stale criteria. Inputs the reviewer reads: the frozen lane brief plus numbered amendments, `complete.md` and the evidence bundle, the plan section, and `git diff <base>...HEAD`.
- Ask for the deliverable as a **file** (`reviews/<lane>-review.md`) and end the turn. Read-only is enforced by the brief alone, so check `git status` is clean afterwards.

**The brief asks for five checks:** (1) correctness: read the diff, not the report; (2) claims against evidence, marking anything not re-checked UNVERIFIED; (3) test quality (a real RED, no mocks hiding the behaviour); (4) scope and safety (owned paths, secrets, production side effects); (5) fitness for the purpose. Verdict format (also in `orchestrated-child-worker` §8):

```text
VERDICT: ACCEPT | ACCEPT WITH FIXES | REJECT
FINDINGS (most severe first): [blocker|major|minor] file:line — defect — failure scenario — suggested fix
UNVERIFIED CLAIMS:
COMMANDS RUN: command → exit code
```
"Be concrete and terse. No praise."

**Watch:** `agent_end` with `once:false`, `max_wakes` ~10, interval 30 s, label `<lane>-reviewer`, plus a local `wake_deadline` (or server `deadline` condition) of 60–90 min as backstop. On wake read the review file, not the run receipt.

**Adjudicate, then loop:**
1. Write an "independent review + parent adjudication" note: each finding confirmed, disputed, or already fixed, with your own RED evidence for the ones you uphold.
2. Send the upheld findings to the **same implementer** as one bounded, numbered correction (`NN-correction.md`, TDD, RED evidence). Re-verify yourself.
3. Send a closure prompt to the **same reviewer session** listing the earlier findings as CLOSED or OPEN with evidence, and ask it to look only at the delta.
4. **Cap at 2–3 rounds.** Mark the last correction FINAL, verified by you only ("no round 4"); recurring bounded-work findings can otherwise loop forever.

**Gotchas seen in practice:**
- **Compaction aborts the first turn.** On a large diff the reviewer crosses the auto-compaction threshold (~75% of context on Pi, `auto-compact-75`) and its turn ends silently as aborted; it resumes by itself. If that happened and the file is missing, **do not re-prompt**: wait for the resumed `agent_end` (25 min backstop). Every wake, including each compaction's `agent_end`, spends `max_wakes`.
- **A prompt sent during compaction is accepted (202) and then fails** with a `RUNTIME_ERROR` receipt ("Cannot submit a prompt while compaction is in progress"), even though `busy` reads false.
- If a reviewer compacts a second time, replace it with **two fresh reviewers on split scope**, and tell them to "keep this focused" to limit context use.
- **Never re-register a watch with `replace`** while waiting; a held wake is dropped (`walk-away.md`).
- Before the wave, check the provider's remaining quota in its own dashboard or CLI and choose a route that fits current capacity.
- **The reviewer is evidence, not the sign-off.** You still re-run everything; your acceptance stands on your own probes.

For several parallel critiques of one draft (a document or plan, not a lane of code), use `patterns.md` (Reviewer fan-out).

## Ownership contracts for concurrent writers

- Enumerate each child's owned paths **in its brief**, exclusions explicit
  ("no edits to X, Y, Z"); the parent must not edit a child's owned paths
  concurrently either.
- Children working in shared checkouts perform **no Git mutations** — the
  parent alone stages, commits and pushes, **path-limited**, never staging
  sibling dirt wholesale. Children hand back changed-path inventories.
- **Symlinked dependencies are shared state**: children never install, patch
  dependencies or `git stash` in a worktree whose `node_modules` point at the main
  checkout — only the parent installs (`programme-kit.md`). Patching an upstream or
  vendored dependency at all requires explicit approval (`orchestrator-governance.md` §1).
- Worktrees prevent file conflicts, **not semantic conflicts or resource
  contention** — where changes overlap semantically, sequence them anyway, and
  cap heavy validation (one disposable server / heavy suite at a time).
- **Sibling agent concurrency on principal branch (`main`)**: If another agent or lineage
  is actively working on `main` in the target repository, all child execution
  MUST happen in an isolated git worktree (`git worktree add ../<repo>-wt-<lane> <branch>`).
  The child runs TDD and commits to its lane branch. The parent coordinates, independently
  verifies in the worktree, and delays merge to `main` until the sibling agent has settled,
  inspecting `git fetch` and manually resolving any interface drifts before merging and teardown.
- **Test store isolation**: When children or parent test suites execute tools or tests
  touching board/presence state (such as `runInject`), configure an isolated temporary
  board store (`BOARD_STORE_DIR: tempRoots.mkdtemp(...)`). Never let automated test suites
  write fixture session IDs into a live coordination store, which can pollute presence
  reports with false zombie or duplicate-session findings.
- The parent owns shared docs, helpers, cross-repo integration and final
  sign-off. Register children on the board (SKILL.md §3b) and read the board
  again at every integration boundary.

## Correction cycles: acceptance is a verdict, not a receipt

- **Never trust a handback.** The parent independently re-runs the child's
  verifier *and* writes its own probe tests for the claimed behaviour — a
  goal-achieved verdict plus a passing child verifier is necessary, not
  sufficient.
- Every claimed defect is **reproduced parent-side with RED evidence** before
  it goes back. No speculative hardening briefs.
- Defects return as **exactly one bounded correction brief per review round**
  (numbered: `parent-review-01.md`, `-02.md`…), addressed only to the owning
  child, with the same owned paths and route as before.
- **Verify before the reviewer** with the parent verification checklist in
  `programme-kit.md` (`git diff --check`, not `-w`; which commit and build produced each
  number; build freshness). Reviewers have caught parents skipping exactly these.
- **Extend the child's verifier to include the parent's probes** each round,
  so a regression cannot pass silently next time.
- **Accepted phases freeze**: the child stops editing owned paths until the
  parent reassigns; the parent commits accepted work before opening new scope.
  For a tiny reproduced integration correction, the parent may explicitly take
  ownership after the child freezes instead of adding another model round.
  Record that allocation amendment and the parent's RED/GREEN evidence; it is
  not permission to edit concurrently or skip independent final review.

## Supervision across waves

- **Taking over from a dead or compacted parent**: recover the old session's record with your harness's own history tools, read the checkpoint and the strategy file, check live state yourself, then act. Never resume from memory of the plan.
- **Log platform defects into the plan.** A defect you find while orchestrating (not in any
  lane's scope) becomes a finding recorded at the right plan step, not an off-plan fix.
- **Refresh shared guidance at its actual phase.** Other agents may have moved
  a skill/document HEAD since planning. Read current files, intervening history
  and active ownership; merge the new learning rather than applying stale text.
- **Re-discover before each dispatch.** Capabilities, capacity, models and
  provider quota are re-read immediately before *every* actual dispatch
  (Golden rule + `routing.md`); a planning-time snapshot is already historical.
  Save the preflight snapshot into the evidence directory.
- **Record before dispatch**: canonical child session id, route tuple, lease
  id/expiry, watch identity, and the exact wake-delivery path. Arm the watch
  before starting the child where possible; one watch per session
  (re-registration replaces — `walk-away.md`).
- **On wake: reconcile all owned children** — receipts, goal state, evidence,
  watch ledger, handbacks — not just the child named in the wake. No blind
  redispatch; a firing is not a verdict; a backstop deadline is not child
  failure; a stale window's timer cancellation does not justify a new fan-in.
- **Pause your own goal while idling** (`goals.md` Part 2) and resume only when
  the waiting work has settled.
- **Release finished children**: cancel their watches and release their
  retention leases (confirm 200), leave their board entries, and stop counting
  them as active — never watch a released child again.
- **Bounded parallelism**: cap simultaneous implementation workers (two is a
  sound default) and count sleeping helper processes toward supervision and
  cleanup rather than hiding them.
- The parent consolidates operator notifications and memory capture; children
  hand back evidence only.

## Worked examples

- **Multi-lane interim wave**: a coordination directory outside the worktree held
  common and lane briefs, a `STATE-interim.md` checkpoint, a time-stamped wake log,
  numbered questions/answers/corrections, reviewer briefs and round-by-round reviews.
  The best current reference for the kit is `programme-kit.md`.
- **Orchestration-repair programme**: a strategy document, checkpoint, evidence tree
  and session records were kept in a coordination directory outside the repository.
  These are method examples, not claims that a particular review or deployment completed.

Values in both are historical; open them for the *shape*, not current state.
