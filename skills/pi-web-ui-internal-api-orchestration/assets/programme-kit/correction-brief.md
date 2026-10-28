# NN-correction — lane <id> (parent verification, <date>)

Same worktree, branch and rules as the lane brief. This file amends it; the latest wins. Parent verification so far: <what you re-ran, with results>.

## [blocker|major|minor] <defect in one line>
Evidence: <numbers, file:line, reproduction>. Cause: <why>.
Required fix (TDD): 1. change the expectation or add a failing test and see it fail; 2. fix; 3. gates.

(One block per defect; at most three. Mark the last round FINAL.)

Gates: re-run `<command>` → <expected exit>. Append a "Correction NN" section to the hand-back (commits, red-first evidence, gate results), keep the marker last, and end your turn.
