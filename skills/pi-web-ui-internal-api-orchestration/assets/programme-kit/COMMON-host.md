# <programme> — common rules, host children (binding for every lane)

Parent: <harness> session <id>. You are an orchestrated child: load and follow the `orchestrated-child-worker` skill (hand-back protocol, commit discipline, host traps, completion block). This file adds only what is specific to this programme.

## Read first, in your worktree
`AGENTS.md` (follow it) · <plan of record: path and section> · <frozen contract, if any: path>.
If the contract is wrong or incomplete, do the sensible thing and record it under "<notes heading>" in <file>; do not edit the contract text.

## Hard rules
- Work only in your worktree and owned paths; start every Bash command with `cd <worktree> && …`. `<production checkout>` is live: never edit it or run installs, builds or git-write there.
- Never touch <production data dir>, restart or stop any service, push, or merge. Commit on your lane branch with explicit `git add <paths>`.
- Strict TDD: see each test fail, then pass. Fakes only: no real model, no live service and no network in tests; invented fixture data.
- Main checkouts are no-go zones: no `cd`, `--prefix`, git-write, npm, build or test there. Before hand-back run read-only `git -C <main> status --porcelain` and `rev-parse --abbrev-ref HEAD` for each repo the lane touches and record both in `complete.md`.
- Disposable servers start with the inherited production placement and tool-root variables removed (`env -u <VAR> …`), in a capped scope, with a credential copy limited to the approved route and deleted afterwards (state the command that confirms none remain).
- Long commands run in the foreground with a timeout.
- Never print, copy or commit secrets or token files.
- Heavy commands run capped: `systemd-run --scope --quiet --collect -p MemoryMax=<cap> -p CPUQuota=400% -- nice -n 10 <cmd>`.
- <Language/style rule, e.g. British English.> <Version bumps: parent only.>

## Gates (exact commands, run before hand-back)
- `<command>` → <expected exit>
Changed-file gates take the lane base explicitly: `<command> --base <lane base commit>`.

## Records
<progress log entry, notes file, changelog rows the lane must update.>

## Hand-back
Directory: `<ops>/<lane>/`. Marker and files: as the lane brief says (one marker).
