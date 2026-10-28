# Companions — runtime pieces that make orchestration actually idle

This folder holds small, self-contained runtime pieces that pair with
[Pi Web UI](https://github.com/valtterimelkko/pi-web-ui) and
[pi-orch](https://github.com/valtterimelkko/pi-orch).

The skills in this repository describe *how* to orchestrate agents: dispatch a
child, define frozen success criteria, then go idle and be woken when the child
finishes. The companions are what make that last step real in a harness that the
server cannot prompt.

## Why the companions matter

Pi Web UI's Internal API can wake a session **it manages**: a parent that runs
inside the server receives the completion as a normal turn. A parent that runs as
a bare CLI process (`pi`, `claude`, or any other harness) is outside that set. It
has only two options without a companion:

- **sleep in-turn** until the child is expected to be done, or
- **poll** the child's status in a loop.

Both are bad. Sleeping keeps a turn open and burns wall-clock time whether or not
the child is ready; polling burns tokens on every check and still adds latency
between "child finished" and "parent noticed". Neither survives the parent being
interrupted, and neither gives the parent a bounded backstop if the completion
notification itself is lost.

A companion changes the shape of the wait:

- the **parent ends its turn and goes fully idle** — no open turn, no tokens, no
  process babysitting;
- a **model-free poller** (a timer, not a model call) watches the durable
  server-side ledger and injects a wake message when there is news;
- the wake **starts a turn of its own**, so the parent resumes exactly as if the
  user had typed "your child finished";
- a **model-free deadline** gives the parent a bounded backstop: if nothing
  arrives within the window the parent chose, it is woken anyway and can
  reconcile.

The result is the zero-token wait the skills assume: a parent can sit idle for
tens of minutes across several children, then wake once, reconcile everything
against receipts, and act.

## What is here

| Piece | Harness | What it provides | Entry point |
|---|---|---|---|
| `watch-wake/pi/` | Pi Coding Agent extension | `watch_wake_register` / `watch_wake_list` / `watch_wake_cancel` / `wake_deadline` inside a bare `pi` CLI process | [`watch-wake/pi/README.md`](watch-wake/pi/README.md) |
| `watch-wake/claude-code/` | Claude Code plugin (function hooks) | the same four tools as `mcp__watch-wake__*` inside a bare `claude` CLI session | [`watch-wake/claude-code/README.md`](watch-wake/claude-code/README.md) |
| `watch-wake/README.md` | both | the shared design, data flow, safety properties and step-by-step usage | [`watch-wake/README.md`](watch-wake/README.md) |

Both ports implement the same contract against the same server endpoints, so a
parent written against one is portable to the other. The differences are listed
per harness, because the wake channel is genuinely different: Pi injects into a
live agent loop (`steer` while busy, `followUp` with `triggerTurn` while idle),
while Claude Code submits a new prompt when the session is idle.

## Are they required?

No. They are optional runtime support that the orchestration skills assume when
they say "go idle; do not poll":

- If your parent is a **Pi Web UI-managed session**, the server's own watch
  `onFire` wake does the same job, and you do not need either companion.
- If your parent is a **bare CLI process**, one of these companions is what
  makes the idle wait possible.
- If you have neither, the skills still work, but the parent must stay in-turn
  or poll — and that cost is exactly what the companions remove.

## Requirements

Both ports need the same two things:

1. A running Pi Web UI whose Internal API socket and bearer token are readable
   by the parent process. The documented defaults are
   `~/.pi-web-ui/internal-api.sock` and `~/.pi-web-ui/internal-api-token`
   (mode `0600`); both paths can be overridden by environment variable.
2. A runtime that supports a **wake with nowhere to land**: the companion will
   refuse to register a watch for a session whose process exits between turns
   (an SDK `-p` run), because the wake would be delivered to nobody.

No credential lives in this repository: the token is read from its file at call
time and is never logged, printed or written into an argument list.

## Tests

Every piece ships tests that run standalone with Node's own test runner — no
dependencies, no network, no real socket and no real token, only fake transports
and temporary state:

```bash
cd companions/watch-wake
npm test                                        # both harnesses
node --test pi/tests/*.test.mjs                 # Pi port: 63 tests
node --test claude-code/tests/*.test.mjs        # Claude Code port: 33 tests
```

Node 23.6 or newer is required, because the tests import the TypeScript sources
directly and rely on Node's built-in type stripping.

## Part of the Pi Web UI orchestration set

- Pi Web UI — https://github.com/valtterimelkko/pi-web-ui
  (`docs/ORCHESTRATION-OVERVIEW.md`, `docs/INTERNAL-API-ORCHESTRATION.md`)
- pi-orch — https://github.com/valtterimelkko/pi-orch
- the pack — https://github.com/valtterimelkko/agent-workflow-skills/blob/main/packs/pi-web-ui-orchestration-pack/README.md
- skills — [`skills/pi-web-ui-internal-api-orchestration/`](../skills/pi-web-ui-internal-api-orchestration/SKILL.md),
  [`skills/long-horizon-waiting-strategies/`](../skills/long-horizon-waiting-strategies/SKILL.md),
  [`skills/orchestrated-child-worker/`](../skills/orchestrated-child-worker/SKILL.md)
