# <programme> — common rules, cloud children (binding for every lane)

You are a child worker in a Claude Code cloud container with a fresh clone of <repo>, dispatched by a parent on the operator's host. Follow `agent-os-child` for accountability, TDD and honesty; skip its host-only parts (absolute host paths, systemd, notifications, any coordination-layer commands). Do not emulate them.

## Where you are
- Work only on branch `<claude/lane>`; push to that branch only. Never push `main`, force-push, or open a PR.
- Never `git stash`, `gc`, `prune` or `reflog expire`. Never commit secrets, `.env` or transcripts.
- `npm ci` in your clone is allowed; do not edit `package.json` or the lockfile unless the brief says so.
- Baseline first: run the full test command, save the failing list; your gate is no new failing test.

## Hand-back (the parent is woken only by your branch head)
Directory `docs/handback/<lane>/` (removed at merge). **Every turn ends with a pushed commit** whose subject starts:
- `QUESTION <lane> NN: …` (with `NN-question.md`: options and a recommendation)
- `BLOCKED <lane> NN: …` (with `NN-blocked.md`)
- `HANDBACK <lane>: complete | partial | not finished` (with `complete.md`, `FROZEN` last)
Never end a turn while a command of yours still runs.

## Gates
- `<command>` → <expected exit>
Live proofs that need host data are listed under HOST FOLLOW-UP in `complete.md`; the parent runs them.
