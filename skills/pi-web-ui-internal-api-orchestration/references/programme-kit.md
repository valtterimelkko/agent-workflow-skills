<!-- Loaded from references/multi-phase.md. The concrete operating kit for a multi-lane programme: copy these templates rather than re-inventing them. Principles live in multi-phase.md; this file is the templates and the runbooks. -->

# Programme kit: templates and runbooks for a multi-lane programme

`multi-phase.md` says *what* a programme needs and *why*. This file is the *kit*: the
templates and sequences that make a multi-lane programme repeatable. Copy, trim to fit,
and keep the section names so another agent can find things.

Contents: operations directory · live checkpoint · common brief · lane brief · correction
brief · reviewer brief · parent verification checklist · worktrees and shared dependencies ·
merge and integration · deploy and restart runbook · wave close-out.

## Operations directory

One directory per programme, **outside every work tree** (e.g. `coordination/<programme>/`):

```text
COMMON-BRIEF[-<wave>].md       binding rules for every child in the wave
STATE[-<wave>].md              live checkpoint (one per wave; the previous wave's stays as history)
<lane>/brief.md                lane brief (frozen)
<lane>/create.json, dispatch-N.req.json, dispatch-N.json   request + receipt of every create/dispatch
<lane>/NN-question.md | NN-answer.md | NN-blocked.md | NN-correction.md | 01-design.md
<lane>/complete.md             the child's completion block, FROZEN last
reviews/REVIEWER-BRIEF[-<wave>].md, reviews/<lane>-review[-rN].md
<gates-output>.txt             integrated-gate output saved to a file, not scrollback
deploy-backup-<what>-<utc>/    backups taken before a deploy
```

Numbering is shared per lane: questions, answers and corrections take the next free `NN`,
so the directory reads as the lane's history in order. **Never overwrite a superseded
file**; add the next number.

## Live checkpoint (`STATE.md`) template

```markdown
# STATE: <programme> <WAVE> — current state, not a completion claim; read before acting

Parent: <harness> session <id> ("<name>"), <bare CLI | managed>. Wake: <exact delivery> + <backstop kind>.
Plan: <path to the strategy/plan file and section>. Previous wave: <STATE file> (history).
Socket <path>; token <path>.

## Approval record (verbatim, dated; append as new grants arrive)
- <date> "<authorisation text>" — scope: <what it covers>. Protocol still: <the gates that still apply>.

## Lanes
| lane | session | run | lease | watch | worktree(s) | status |
|---|---|---|---|---|---|---|

Hand-back files: <ops dir>/<lane>/{NN-question,NN-blocked,01-design,complete}.md; answers NN-answer.md.
Briefs: COMMON-BRIEF-<wave>.md + <lane>/brief.md. Reviewer brief: reviews/REVIEWER-BRIEF-<wave>.md.

## Dependencies and deploy order (add each one the moment you discover it)
- <lane B> waits for <data from lane A | lane A's interface | lane A deployed>.
- Deploy <X> BEFORE the restart that activates <Y>.
- Predicted conflicts: <lane A and lane B both edit <file> — parent resolves at merge>.

## Next sequence
1. On each wake: reconcile ALL lanes (receipt, coordination dir, git log in each worktree).
2. ...

## Lessons carried from the previous wave
- ...

## Backstop
Deadline: <id> due <HH:MM UTC>.   ← rewrite on every arm

## <HH:MM UTC from `date -u`> wake #N (<which child>)
- <what the evidence says, what you decided, what you dispatched, new ids>
- If <no progress by HH:MM>: <the pre-committed response>.
```

Rules that keep it honest:

- **Stamp every entry from the clock**: `date -u +%H:%M` at the moment of writing. A parent
  that has just woken does not know how long it slept; inferred times drifted by up to six
  hours in the reference programme.
- **Record ids as they are created** (session, run, lease, watch, deadline) — never
  reconstruct them later.
- **Write the stall response before you idle**, with a time: "if no further turn by 21:25
  while its soak is finished: prompt it to finish (`follow_up`)".
- Keep counters honest: reviews performed vs lanes accepted vs objectives not achieved.

## Common brief template (`COMMON-BRIEF-<wave>.md`)

```markdown
# Common rules for every child in <wave> (<lanes>) (read fully before starting)

You are an orchestrated child worker dispatched by <parent>. You MUST load and strictly follow
the `orchestrated-child-worker` skill.

## Context you must read first
- Plan of record: <path>, sections <…> and your own step.
- Evidence for this wave: <paths>. Repository guide: AGENTS.md in your worktree.

## Hard rules
- Work only inside your assigned worktree(s) and owned paths. Never edit <main checkouts, config dirs>.
- Never restart, stop or reconfigure production; never validate against production.
  Live validation uses disposable servers with <isolation rules>. See the [Pi Web UI live-validation
  guide](https://github.com/valtterimelkko/pi-web-ui/blob/master/docs/LIVE-VALIDATION.md) for repository-specific checks.
- Credentials in a disposable agent dir: copy only the approved provider entry. A
  `models.json` holding `apiKey` entries is a credential copy too; strip unapproved
  providers. Name the child route in any inner brief, assert the served model by script,
  and delete every copy when done. A full copy must never allow a child to select a route
  excluded by the programme.
- Long commands run in the background with a result file; never block your own turn
  in one foreground command for more than about ten minutes.
- Preserve the raw evidence a claim rests on (transcripts, receipts) before any cleanup
  deletes it, redacted, in the coordination dir, so a reviewer can recount.
- Strict TDD: record RED, then GREEN.
- `node_modules` in your worktree are symlinks to the main checkout: never `npm install`/`npm ci`,
  never `git stash`, never patch a dependency. If one is missing or needs a change, ask.
- Commit to your lane branch in small logical commits. Do not push lane branches, merge,
  or rebase; the parent merges them.
- No deployment, no harness notifications, no secrets or run artefacts in commits.

## <Lesson carried> (e.g. build freshness: rebuild in your own worktree before any live run and record the build commit)

## Gates to run before hand-back
<exact commands>. Record each command and exit code.

## Hand-back protocol (the parent is woken by your turn ending)
- Decision needed: `NN-question.md` (question, options, your recommendation), then end your turn.
- Blocked: `NN-blocked.md`, then end your turn.
- Done: `complete.md` (block below), then end your turn.
- Numbered `NN-answer.md` and `NN-correction.md` files amend your brief; the latest wins.
- Ask only about contradictions, scope or authority boundaries, anything irreversible or touching
  real data, or a false premise. Decide engineering details yourself and record them.

## Completion block (`complete.md`)
STATUS: complete | partial | blocked
BRANCH / WORKTREE:
COMMITS: <sha> <subject>
FILES CHANGED: git diff --stat <base>...HEAD
TDD: per behaviour — test, RED command+exit, GREEN command+exit
GATES: command → exit code
LIVE VALIDATION: commands, run dirs, key numbers, positive controls, build commit
DEFINITION OF VICTORY: each item → met / not met / partly, with evidence
NOT DONE AND WHY:
RESIDUAL RISKS:
FROZEN

Also commit the step's evidence bundle to <path>. Do not edit the plan file; the parent keeps it.
You never sign off your own work.
```

The dispatch prompt itself stays short: the `orchestrated-child-worker` directive (SKILL.md §3), the
session id, the worktree, and "read `<ops dir>/COMMON-BRIEF-<wave>.md`, then `<lane>/brief.md`".
Briefs live in files; see `orchestrator-governance.md` §7 on keeping permission stories out
of text sent to children.

## Lane brief template (`<lane>/brief.md`)

```markdown
# Child brief — <step>: <outcome in one line>

Lane: `<lane>`. Coordination dir: <path>. Read ../COMMON-BRIEF-<wave>.md first; it is binding,
except where this brief explicitly says otherwise (say exactly what).

## Worktree (yours alone)
<path> (branch <orch/lane>, from <base sha>)   ← one line per repo if the lane spans two

## Owned paths
- ...
## Negative exclusions
<paths>, naming the sibling lane that owns each (e.g. "session-watcher.ts (lane b1-1)").

## Background
<the evidence and numbers that motivate the lane; hypotheses labelled as hypotheses>

## Phase A — <design | attribution>, then STOP at a gate      ← behaviour-critical lanes only
... write `01-design.md` with <table, evidence, proposed fix: files, approach, risk>, commit, end your turn.
## Phase B — implement (after the parent's `01-answer.md`)

## Decision rule (fixed before measuring)                       ← when a measurement decides
<result> → <choice>; <result> → <choice>; neither → <default>.

## Definition of victory (frozen)
- [ ] ...
**Not victory if:** <the tempting shortcuts: raising a threshold instead of removing the cause,
proof only with mocks, attribution by timing overlap alone, …>
```

## Correction brief template (`<lane>/NN-correction.md`)

```markdown
# NN-correction — <step> (parent verification, <date>)

Parent verification so far: <what you re-ran, with results>.

## [blocker|major|minor] <defect in one line>
**Evidence:** <numbers, file:line, run ids — reproduced parent-side (RED)>.
**Cause:** <why it happens>.
**Required fix (TDD):** 1. … 2. … 3. a failing test first.
**Live proof:** <the run that must show the fix, and the expected number>.

Keep all other behaviour. Update the evidence bundle and `complete.md` (mark this correction;
keep FROZEN last), then end your turn.
```

One correction file per round, addressed to the owning child only, with the same owned
paths and route. Mark the last one **FINAL** (see *The reviewer child* in `multi-phase.md`).

## Reviewer brief

Keep one reusable `reviews/REVIEWER-BRIEF-<wave>.md` (the five checks and verdict format in
`multi-phase.md` *The reviewer child*) and a short per-lane prompt: lane, worktree, branch,
diff range, focus areas, output path. Tell the reviewer that the numbered answer and
correction files **amend** the frozen brief — otherwise it judges against stale criteria.

## Parent verification checklist (before the reviewer, and before acceptance)

- Read the diff yourself with `git diff --check` and a plain `git diff` — **not `-w`**, which
  hides whitespace errors a reviewer later catches.
- Re-run the lane's gates and the touched modules' tests yourself; record commands and exits.
- **Provenance of every number**: which commit, which build, which run directory produced it.
  Re-measure from the final clean commit when the child measured at an intermediate one.
- **Build freshness**: a live run executes the built output of *its own checkout*; confirm the
  child rebuilt in its worktree and recorded the build commit.
- Scope: files outside owned paths, the plan file, shared dependencies, production paths.
- Write your own probe for the claimed behaviour; a passing child verifier is necessary, not sufficient.
- Only then spend reviewer tokens.

## Worktrees and shared dependencies

```bash
git -C <repo-root> worktree add -b orch/<lane> <worktree-path> <base>
ln -s <repo-root>/node_modules <worktree-path>/node_modules   # and each workspace's
```

- **Symlinked `node_modules` are shared state.** A child's install, `postinstall` patch or
  dependency edit lands in the main checkout — and therefore in production's copy. Only the
  parent installs, on the main checkout, with the environment the repo expects (e.g.
  `NODE_ENV=development … --ignore-scripts`), verifies upstream files by hash, then merges
  the base into the lane branches.
- `git stash` is one stack per repository, shared by every worktree: children never stash.
- A lane may span two repositories: give it one worktree per repo and list both in its row.

## Merge and integration

1. **Record predicted conflicts at dispatch** (two lanes editing one file) in the checkpoint.
2. **Trial integration while reviews run**: merge the predicted-conflict lanes into a scratch
   worktree (`orch/integration-trial`), resolve, run the full suite. The real merge is then a
   formality — this is the useful critical-path work to do instead of idling.
3. **Merge each lane as it is accepted**, one at a time, `--no-ff` on the local base branch
   (`--ff-only` where a repo's history is linear).
   **Resolve conflicts hunk by hunk, never by taking a whole file or a whole hunk from one
   side.** Shared files (a contract-version constant, a types file, a changelog) put one
   lane's version line next to another lane's new field in the same hunk. Picking "ours"
   dropped a neighbouring addition in two waves running. After every merge, run a
   **line-survival check**: every line the
   lane added must still be present, apart from lines you changed on purpose (version
   pins). Fix what is missing before the gates run.
   **Cross-lane interactions surface only after the merge.** Lane suites pass in isolation.
   Examples: a new default-on check breaks another lane's fixtures; a newly async method
   breaks the integration suite of a lane that only ran unit tests. Run the integration
   and client suites too, not only the server unit suite.
4. **Run the integrated gates once after the last merge**, in the background, output to a
   file. Triage a failure by running that test alone and checking whether the wave touched it.
5. **Push only the integrated base branch, and only after its gates are green** — never the
   local lane branches. Then update the plan's status sections in the same change.

## Deploy and restart runbook

Needs the responsible operator's authority (`orchestrator-governance.md` §1) — recorded
verbatim in the checkpoint with its scope. A blanket grant does not relax the protocol.

1. **Coordination check**: inspect your harness's coordination surface for anyone else
   using the Internal API or service; if none exists, record a one-line task/owned-paths
   note in the hand-back or coordination directory.
2. **Deploy dependent artefacts first** (extensions, mods, config the new code needs), with a
   timestamped backup (`deploy-backup-<what>-<utc>/`) and a byte-identity check of the live
   files against the commit you deployed.
3. **One guarded command** for the restart, so it aborts on its own if work arrived:
   read `activeTurns`, `[ "$A" = 0 ] || exit 1`, then the repo's lock wrapper around
   build → restart → wait-for-API (for pi-web-ui: `production:lock` wrapping the build,
   `npm run production:drain-restart -- --reason …` and `internal-api:wait`; see
   `orchestrator-governance.md` §3 — on a server older than contract 1.52.0 pause
   goal-armed children first).
4. **Verify**: new MainPID and `ActiveEnterTimestamp`; `/capabilities` contract version; a grep
   of the built output proving the new code is what runs; a functional smoke test (create a
   session in a fresh cwd, time it, read the journal line the change added).
5. **Reconcile**: every child and watch (`orchestrator-governance.md` §4).
6. **Deferred verification**: when the change can only be judged on later production traffic,
   arm a model-free deadline whose message *is* the verification recipe (what to compare, in
   which file, against which baseline). See the single-slot rule in
   `long-horizon-waiting-strategies` before arming it.
7. Optionally notify the operator through the harness's own notification path with the
   deployed commit and what was verified.

## Wave close-out

- `watch_wake_list` (or the server list): cancel each watch, confirm deleted.
- Release each retention lease you own; confirm 200.
- Leave children's board entries if they did not.
- Keep finished sessions **idle for audit** unless the brief made them disposable; delete only
  disposable ones (SKILL.md §9).
- Remove worktrees and lane branches only after the merge is pushed.
- Update the plan's status/evidence sections, write the programme report (`patterns.md`,
  including *Decisions and recommendations*), optionally notify the operator through the
  harness's own notification path, and capture outcomes.
