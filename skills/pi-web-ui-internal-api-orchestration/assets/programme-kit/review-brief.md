# Review brief — lane <id> (<what>)

You are a fresh, read-only reviewer of a different model family than the implementer. Do not edit, commit, stash, push or run anything that writes outside a gitignored build dir. Never print secrets.

Subject: branch `<branch>`, `git diff <base>..<head>` in `<worktree>`. Hand-back: `<path>`. Contract and frozen criteria: `<path>`; numbered answer and correction files amend them, the latest wins.

## Check (in order)
1. <highest-risk property, e.g. shell/credential/data safety>
2. <correctness against each frozen criterion>
3. <tests meaningful and not weakened; gates re-run where cheap>
4. <evidence in the hand-back matches the artefacts>

## Proportionality
Reject only for a defect that breaks a frozen criterion or safety, with a concrete failure scenario. Taste, naming and style go under NOTES, not findings. A finding without evidence is a hypothesis: label it.

## Time-box
<20–30> minutes. Checkpoint the verdict file early. If short of time, finish what you reviewed and end with `NOT FINISHED:` naming what is left.

## Output: `<review path>`
VERDICT FILE: verdict.md
(For `pi-orch lane run`: the verdict path relative to the lane dir. Delete this pair of lines for a hand-run review.)
First line `VERDICT: ACCEPT | ACCEPT WITH FIXES | REJECT`. Then numbered findings (file:line, severity blocker|major|minor, failure scenario, evidence), NOTES, commands run with exits. Last line `FROZEN`. You never declare work signed off.
