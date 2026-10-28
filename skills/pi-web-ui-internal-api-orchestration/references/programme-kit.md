<!-- Loaded from references/multi-phase.md. The concrete operating kit for a multi-lane programme: copy these templates rather than re-inventing them. Principles live in multi-phase.md; this file is the templates and the runbooks. -->

# Programme kit: templates and runbooks for a multi-lane programme

`multi-phase.md` says *what* a programme needs and *why*. This file is the *kit*: the
templates and the sequences that made real programmes run well. Copy, trim to fit, and keep
the section names so another agent can find things.

Contents: operations directory · the templates (files) · reviewer live re-run lane · parent verification checklist · worktrees and shared dependencies ·
merge and integration · deploy and restart runbook · wave close-out.

## Operations directory

One directory per programme, **outside every work tree** (e.g. `<ops root>/<programme>/`):

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

## The templates are files

Copy them from `assets/programme-kit/` (`README.md` there has the commands):

| File | Use |
|---|---|
| `STATE.md` | live checkpoint, ≤ 60 lines: one RESUME HERE block, lane table, backstop row, operator-authority log |
| `COMMON-host.md`, `COMMON-cloud.md` | programme-wide rules; the hand-back protocol and host traps stay in `orchestrated-child-worker` |
| `lane-brief.md` | objective, owned paths, frozen criteria, **one** hand-back marker, stop caps, a final `GATES:` block |
| `review-brief.md` | reviewer verdict format, proportionality line, time-box |
| `correction-brief.md` | one defect block per finding, red-first fix, re-run gates |
| `objectives.sh` | single-line goal objectives per lane |

Rules that keep `STATE.md` honest:

- **Stamp every entry from the clock** (`date -u`); inferred times drifted by up to six hours.
- **Record ids as they are created** (session, run, lease, watch, deadline); never reconstruct them.
- **Write the stall response before you idle**, with a time.
- Keep counters honest: reviews performed vs lanes accepted vs objectives not achieved.
- Rewrite the RESUME block on every wake and move old wake-log lines to a history file, so the file never grows past one screen.

The dispatch prompt stays short: the `orchestrated-child-worker` directive (SKILL.md §3), the session id,
the worktree, and "read `<ops dir>/COMMON.md`, then `<lane>/brief.md`". A goal objective is one
line with an explicit token budget (`--goal-budget-tokens`, tens of millions for long lanes). Keep
permission stories out of text sent to children (`orchestrator-governance.md` §7). Numbering is
shared per lane (`NN-question|answer|blocked|correction.md`); never overwrite a superseded file.
Changed-file gates take the lane base explicitly (`npm run lint:ratchet -- --base <base>` in a repo that has one).

## Reviewer live re-run lane (a named lane in every wave template)

Add it when you write the wave, with its own brief and row. A fresh reviewer (not an
executor of the steps; on a different model family from the implementers) re-runs the
wave's behavioural claims live, read-only on the code:

- a disposable server built from the integrated base, in the isolation the common brief
  defines (placement variables removed, capped scope, isolated agent dir, real extension
  copies, approved cheap route, own credential copy deleted afterwards);
- one **arm per shipped claim**, each with its pass rule and a positive control fixed before
  running (a `review-brief.md` from `assets/programme-kit/` is the shape, with one arm per claim);
- the report states build commit, peak concurrent active turns and sample counts;
- a failing arm comes back with a reproduction and becomes a named correction lane.

The wave is **not shipped** until this lane has run. Waves that closed on code reviews and
focused tests alone had to be followed by a late live proof; put the lane in the plan up front.

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
- A defect you find goes back to the implementer **before** any reviewer tokens are spent.
- Only then spend reviewer tokens.

## Worktrees and shared dependencies

```bash
git -C <repo> worktree add -b orch/<lane> <worktree root>/<prog>/<lane>-<repo> <base>
ln -s <repo>/node_modules <worktree root>/<prog>/<lane>-<repo>/node_modules   # and each workspace's
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
   dropped a neighbouring addition in two waves running — a types file and a batch-entry
   field. After every merge, run a **line-survival check**: every line the
   lane added must still be present, apart from lines you changed on purpose (version
   pins). Fix what is missing before the gates run.
   **Cross-lane interactions surface only after the merge.** Lane suites pass in isolation.
   Examples: a new default-on check breaks another lane's fixtures; a newly async method
   breaks the integration suite of a lane that only ran unit tests. Run the integration
   and client suites too, not only the server unit suite.
4. **Run the integrated gates once after the last merge**, in the background, output to a
   file. Triage a failure by running that test alone and checking whether the wave touched it.
   **Run changed-file gates against the previous base, not the default.** On a merge commit a
   changed-files check with its default base sees no changed files and passes falsely; run
   `npm run lint:ratchet -- --base <previous base branch>`. A merge has passed the default
   local run and gone red in CI on a new non-null assertion.
5. **Push only the integrated base branch, and only after its gates are green** — never the
   lane branches, which usually stay local (state the rule in every brief). Then update the
   plan's status sections in the same change.

## Deploy and restart runbook

Needs the operator's authority (`orchestrator-governance.md` §1) — recorded verbatim in the
checkpoint with its scope. A blanket grant does not relax the protocol.

1. **Coordination check**: is anyone else using the Internal API or the service right now?
   **Then check the production checkout itself** (read-only): `git -C <checkout> rev-parse
   --abbrev-ref HEAD` is the base branch, `git -C <checkout> status --porcelain` is empty, and
   `git -C <checkout> reflog -5 --date=iso` shows only your own merges since the last deploy.
   A foreign `checkout:` entry means a child worked there; find what it changed (and whether
   it rebuilt `dist`) before you build. A child once checked out its lane branch in the
   production checkout and rebuilt `dist`; the parent's later `merge` was a silent no-op
   because HEAD was already the lane branch. Preserve such a state on a local rescue branch
   (commit it there), then switch back; a forced checkout discards it.
2. **Deploy dependent artefacts first** (extensions, mods, config the new code needs), with a
   timestamped backup (`deploy-backup-<what>-<utc>/`) and a byte-identity check of the live
   files against the commit you deployed.
3. **One guarded command** for the restart, so it aborts on its own if work arrived:
   read `activeTurns`, `[ "$A" = 0 ] || exit 1`, then the repo's lock wrapper around
   build → restart → wait-for-API (for Pi Web UI: `production:lock` wrapping the build,
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
7. Notify the operator with the commit deployed and what was verified.

## Wave close-out

- Confirm the reviewer live re-run lane ran and each arm is accounted for.
- Re-read every evidence bundle's residual-risk and blind-spot lists; route each hazard into
  the plan and the defect ledger the same day, with its interim mitigation.
- `watch_wake_list` (or the server list): cancel each watch, confirm deleted.
- Release each retention lease you own; confirm 200.
- Close children's coordination entries if they did not.
- Keep finished sessions **idle for audit** unless the brief made them disposable; delete only
  disposable ones (SKILL.md §9).
- Remove worktrees and lane branches only after the merge is pushed.
- Update the plan's status/evidence sections, write the operator report (`patterns.md`,
  including *Decisions for you*), and send one "done" notification.
