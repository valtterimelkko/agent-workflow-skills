# Lane <id> — <outcome in one line>

Common rules: `<ops>/COMMON.md` (binding). Worktree `<path>`, branch `<lane branch>`, base `<sha>`. Route: <selector>.

## Objective (≤ 60 words)
<What changes, why it matters, what proves it. Hypotheses labelled as hypotheses.>

## Owned paths
- <path>
Not yours: <path> (<sibling lane or the parent>).

## Frozen success criteria
- [ ] <criterion with its evidence>
Not victory if: <the tempting shortcuts>.

## Hand-back (one marker)
<marker, e.g. `Status: GOAL_ACHIEVED` after `complete.md` is written, or the pushed commit subject>. Questions and blockers: `NN-question.md` / `NN-blocked.md`, then end your turn.

## Completion instructions
<Paste the output of `pi-orch template --goal` (or `template`) here.>

## Stop conditions
Hand back within <N> minutes or <N> tool calls, whichever comes first, with what is done and what is not. Stop and ask (do not guess) on: a contradiction in the contract, scope or authority outside your paths, anything irreversible or touching real data.

GATES: (one `- cmd → exit` per line; `pi-orch verify --gates-file` re-runs them)
- <command> → <expected exit>
- <command> → <expected exit>
