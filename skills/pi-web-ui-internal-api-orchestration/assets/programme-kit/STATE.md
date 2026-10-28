# STATE: <programme> <wave> — current state, not a completion claim

## RESUME HERE (rewrite on every wake; stamp from `date -u`)
Now: <HH:MM UTC> · Parent <harness> <session id> · Wake route: <mod | onFire | wait-watch.sh>
Next action: <one line>
If nothing by <HH:MM UTC>: <pre-committed response>
First read after compaction: `references/parent-card.md`, then this file only.

## Lanes
| lane | session | retention id | lease | watch (wakes used) | worktree | route | status |
|---|---|---|---|---|---|---|---|
| <lane> | <sid> | orch-<programme>-<parent8>-<lane> | <lease> | <id> (0/10) | <path> | <selector> | <not started | running | review | accepted> |

## Backstop
| kind | id | due (UTC) |
|---|---|---|
| <wake_deadline | schedule | deadline condition> | <id> | <HH:MM> |

## Dependencies and deploy order
- <lane B waits for lane A's interface>. Predicted conflicts: <file> (<lane A>, <lane B>).

## Operator authority log (verbatim, dated)
- <date> "<operator's exact words>" — scope: <what it covers>.

## Links
Plan <path> · COMMON <path> · briefs <ops>/<lane>/brief.md · reviews <ops>/reviews/ · hand-backs <ops>/<lane>/complete.md

## Wake log (newest first; one line each, trim old entries into <ops>/history.md)
- <HH:MM UTC> wake #<n> (<lane>): <evidence> → <decision>.
