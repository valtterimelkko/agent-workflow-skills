# watch-wake — parent-wake for a bare agent CLI

`watch-wake` lets a session that Pi Web UI does **not** manage — a bare `pi` CLI
process, a bare `claude` CLI session — register a durable **Pi Web UI Internal API
watch on a child session**, end its turn, and be **woken with a new turn** when
that watch fires.

It is the local counterpart of the server-side `onFire` wake in the Internal API,
which can only prompt sessions the server itself manages. Both watch the **child**;
neither ever prompts the session being watched.

```
parent (bare CLI, goes idle at zero token cost)
   │  watch_wake_register(child)
   ▼
server-side durable watch on the child  (pure observer: no onFire, no prompt)
   │  the child emits agent_end / a tool result / a text match / a timer
   ▼
the server's ledger records the firing
   │  ←── the companion polls the ledger on an interval (a timer, no model call)
   ▼
new firing since the local cursor
   ▼
busy parent → the wake joins the current turn (Pi: steer; Claude: queued)
idle parent → the wake starts a turn of its own
   ▼
parent reconciles the child against durable evidence and continues
```

The important part is the middle: **the wait itself costs no tokens.** The client
polls one cheap authenticated request per interval, and the server did the
watching. A parent that goes idle stays idle until there is something to read.

## The four tools

| Tool | Pi extension | Claude Code mod | What it does |
|---|---|---|---|
| register | `watch_wake_register` | `mcp__watch-wake__watch_wake_register` | Create a pure-observer watch on a **child** session and deliver the wake here. |
| list | `watch_wake_list` | `mcp__watch-wake__watch_wake_list` | Show local registrations (child, status, wakes sent, cursor, generation, last error) and the deadline state. |
| cancel | `watch_wake_cancel` | `mcp__watch-wake__watch_wake_cancel` | Stop local delivery first, then delete the server-side watch — only if its generation is still ours. |
| deadline | `wake_deadline` | `mcp__watch-wake__wake_deadline` | `arm` / `status` / `cancel` one model-free local wait-window backstop. |

Both ports expose the same parameters and the same message placeholders, so a
parent's orchestration text can be written once.

## Register parameters

```json
{
  "session_id": "<child internal session id>",
  "conditions": [{ "id": "done", "type": "event_type", "eventType": "agent_end" }],
  "message": "Your child {{sessionId}} fired {{conditionId}} at {{firedAt}} — go look, do not assume success.",
  "max_wakes": 1,
  "interval_seconds": 30
}
```

### Conditions

Conditions use the same generic spec as `POST /api/v1/sessions/:id/watch`:

| `type` | Fields | Matches |
|---|---|---|
| `event_type` | `eventType` (required), optional `dataMatch` | a normalised event, e.g. `agent_end`, `goal_end` |
| `tool` | `toolName`, `phase` (`start` / `end`, default `start`), optional `argIncludes` | a specific tool call or its result |
| `text` | `contains` or `pattern` (+ `patternFlags`, `source`) | assistant output, or any text |
| `deadline` | `afterSeconds` (integer 1–86400) | a server-side timer |

`dataMatch` is a **shallow** primitive comparison (`event.data[key] === value`).
A dotted key or a nested object can never match, so it is refused locally instead
of being accepted and never firing.

**Condition choice matters more than anything else here.** `event_type: agent_end`
is the safe default: it fires exactly once per child turn, so a child given five
tasks in one prompt wakes the parent once, after all five — and it also fires
when the child stops early to ask a question. Text sentinels wake mid-turn, but
only if the child emits the exact string, so the sentinel has to be named in the
child's own task prompt. Tool conditions (`phase: "end"` plus `argIncludes`) match
a specific tool result, not prose.

### Message placeholders

`{{sessionId}}`, `{{conditionId}}`, `{{eventType}}`, `{{firedAt}}`,
`{{firingCount}}`.

### Bounds

| Setting | Range | Default |
|---|---|---|
| `max_wakes` | 1–10 | 1 |
| `interval_seconds` | 5–3600 | 30 |
| `wake_deadline` `delay_seconds` | 0–86400 | — |
| `message` | the harness tool caps it (4000 characters on the Pi register tool, 2000 on `wake_deadline`); the Claude Code mod requires only a non-empty string | — |

A registration that would fire once (`max_wakes: 1`) may leave `once` alone. With
`max_wakes > 1` the conditions must be able to fire repeatedly, so the mod sets
`once: false` for you and refuses an explicit `once: true`; a `deadline` condition
stays one-shot by design.

## Invalid conditions are refused before the request

A condition whose shape can never match is rejected **locally, before any API
call**, with the correct shape in the error. The server would otherwise accept
it, answer "watching", and strand the parent forever:

- an event name used as the type — `{ "type": "goal_end" }` becomes
  `{ "type": "event_type", "eventType": "goal_end" }` (the event name is the
  `eventType` field, never the `type`);
- an `event_type` with no non-empty `eventType`;
- a `text` condition with neither `contains` nor `pattern`;
- a `dataMatch` key containing a dot, or a `dataMatch` value that is an object,
  array or null.

The same guard refuses a session watching **itself**: an idle session emits no
events, so a self-watch can only ever be a silent dead end.

## Step by step: a parent and a Pi Web UI child

1. **Create and dispatch the child** through the Internal API, and keep the
   internal `sessionId` (and `runId`) from the responses — not the title, not a
   session title. Creation and dispatch are separate calls:

   ```bash
   SOCK="$HOME/.pi-web-ui/internal-api.sock"
   TOK="$HOME/.pi-web-ui/internal-api-token"

   # create the child session
   curl -sS --unix-socket "$SOCK" \
     -H @<(printf 'Authorization: Bearer %s\n' "$(cat "$TOK")") \
     -H 'content-type: application/json' \
     -d '{"runtime":"pi","model":"<model id from /api/v1/models>"}' \
     http://localhost/api/v1/sessions

   # dispatch the brief to it (detached: the call returns a runId)
   curl -sS --unix-socket "$SOCK" \
     -H @<(printf 'Authorization: Bearer %s\n' "$(cat "$TOK")") \
     -H 'content-type: application/json' \
     -d '{"message":"<task brief>","detach":true}' \
     http://localhost/api/v1/sessions/<sessionId>/prompt
   ```

   The bearer header is read from a process-substitution file rather than put
   in `argv`: an argument list is world-readable through the process table.
   `pi-orch` wraps this and is the better default when you have it.

2. **Register the watch** with `event_type: agent_end` and a message that says
   what to reconcile, not what to conclude:

   ```json
   { "session_id": "<child id>",
     "conditions": [{ "id": "done", "type": "event_type", "eventType": "agent_end" }],
     "message": "Child {{sessionId}} ended ({{conditionId}}, count {{firingCount}}) — verify its commits and read its final report before acting." }
   ```

3. **Arm a backstop** for the window you actually expect:

   ```json
   { "action": "arm", "delay_seconds": 1800, "message": "No child wake arrived — reconcile every owned child and check watch health.", "wait_label": "implementation-wave" }
   ```

   The deadline is a *bound on silence*, not a second way of knowing when the
   child finished.

4. **End your turn.** Do not sleep, do not poll, do not hold the turn open.

5. **On the wake, reconcile.** The wake means "go look", never "done". Read the
   child's report, its commits and its changed paths; a child that stopped to ask
   a question fires `agent_end` too.

6. **Cancel or let it finish.** `max_wakes: 1` completes by itself. Cancel
   explicitly when you no longer want the wake, so the server's one-watch-per-
   session slot is released.

7. **Check for staleness if the wait is long.** `watch_wake_list` shows `stale`
   when the server watch vanished, was replaced, or reloaded detached after a
   server restart. A stale registration will never wake you: re-register after
   reconciling.

## Safety properties

These are the properties the code is built to preserve. Do not weaken them when
adapting it.

**The poll is a timer, not a model call.** Nothing in either port asks a model to
decide whether to poll. The cost of waiting is one small authenticated GET per
interval per registration.

**A wake is delivered once per new firing batch, bounded by `max_wakes`.** A
failed delivery does not consume the budget and does not advance the cursor, so
the firing is retried on the next poll. A wake whose delivery races a turn
boundary is retried once down the idle path (Pi) or held until the session is
idle (Claude Code).

**Generation CAS when the server supports it.** If
`GET /api/v1/capabilities` advertises `features.watchGenerationPreconditions`, the
companion uses conditional mutation:

- register reads the existing watch and sends `expectedGeneration` — `null` when
  there is none, the exact observed token otherwise;
- cancel sends the observed generation and reports deletion as confirmed **only**
  on `200` with `success: true` and the matching returned generation;
- a `409 WATCH_GENERATION_MISMATCH` means someone else's watch now occupies that
  URL. Local delivery stops, the remote delete is **not** attempted again, and the
  deletion is not reported as confirmed.

A client pre-read is not CAS on its own; the server has to check the precondition
atomically with the mutation. Servers that do not advertise the capability keep
legacy unconditional semantics, and the companion labels those acknowledgements
as unconfirmed rather than pretending otherwise. A registration that knows it was
CAS is refused if the capability disappears — no silent downgrade.

**A known foreign watch is never clobbered.** Registering replaces the server's
one-watch-per-session ledger for that child. The Claude Code mod refuses to
replace a watch with a foreign label or an `onFire` action unless `replace: true`
is passed explicitly.

**Cancel cannot delete a replacement.** The delete authority belongs to one
generation and is consumed by acknowledgement; repeating an old cancellation
reuses that acknowledgement instead of deleting whatever now sits at the URL.
Records kept only as diagnostics carry no remote-delete authority at all.

**Tokens are never configured, printed or passed in arguments.** The token is
read from its file at call time, per request, and is never logged. The Claude Code
port's `curl` fallback passes the bearer header on **stdin**, not in `argv`.

**Headless sessions are refused (Claude Code).** An SDK `-p` run exits or is
driven by its host, so a local wake has nowhere to land. Interactive CLI sessions
and Remote Control bridge sessions are allowed, because their process stays up
between turns and a submitted prompt starts a real turn there.
`allow_headless: true` forces the registration.

**Restore re-attaches, never re-registers.** On a new session start the persisted
registrations are attached to their surviving server watches from the last
consumed cursor — a re-register would wipe the ledger and lose any firing that
happened while the parent was down. A watch whose generation changed meanwhile is
marked stale rather than adopted.

**Stale is loud.** A vanished watch, a changed generation or a detached reload
delivers one bounded notice rather than disappearing silently, so an idle parent
is not stranded. Repeat poll failures escalate to one notice and keep watching.

**Change-only persistence.** Registrations are persisted only when their
persisted content actually changes (cursor advance, budget consumption, add,
cancel). An unchanged poll writes nothing, so a stable watch on an idle session
causes no session-file growth.

**Expiry of a deadline is not completion.** Both the tool description and the
delivered text say so, because it is the failure the mechanism is most likely to
cause: a parent that reads "you were woken" as "the child is done".

## Install

- **Pi Coding Agent extension** — [`pi/README.md`](pi/README.md)
- **Claude Code plugin** — [`claude-code/README.md`](claude-code/README.md)

## Requirements

| Requirement | Detail |
|---|---|
| Pi Web UI | a running server exposing the Internal API (`/api/v1`), with the watch endpoints |
| Socket | `~/.pi-web-ui/internal-api.sock` by default |
| Token | `~/.pi-web-ui/internal-api-token` by default, mode `0600`, sent as `Authorization: Bearer …` |
| Node | Node 23.6+ for the tests (built-in type stripping); the Pi extension runs inside Pi's own runtime |
| Harness | Pi (extension) or Claude Code with function hooks enabled (plugin) |

Environment overrides differ per harness, and this is a genuine trap:

| Harness | Socket override | Token override |
|---|---|---|
| Pi extension | `PI_WEB_UI_WATCH_WAKE_SOCKET` | `PI_WEB_UI_WATCH_WAKE_TOKEN_FILE` |
| Claude Code mod | `PI_WEB_UI_SOCKET` | `PI_WEB_UI_TOKEN_PATH` |

## Honest limits

- **The wake needs a live parent process.** If the CLI process exits, nothing is
  delivered until the session is resumed; the registration is restored then and
  firings recorded meanwhile are consumed.
- **An in-process timer cannot survive its own process.** `wake_deadline` bounds
  a missed watch wake while the parent is alive; it cannot resurrect a dead
  parent, a blocked event loop or a lost server.
- **`wake_deadline` is in-process and single-slot.** Arming replaces the previous
  wait. Exactly-once delivery is not promised: a crash after channel acceptance
  may replay the wake.
- **Hot-reload drops timers.** Replacing either port's files cancels the timers of
  already-running sessions; restart the parent to rebind.
- **A wake is not a verdict.** It says a condition fired. Whether the work is
  finished, correct or complete is a question for the child's report, its
  commits and its receipts.
- **Long waits need a backstop**, not a longer interval: pair the watch with
  `wake_deadline` so silence itself has an expiry.
- **One watch per child session.** Registering a second time replaces the first,
  so a parent that needs two different signals should register a single condition
  set with `max_wakes > 1`, or watch a relay session.

## Tests

```bash
cd companions/watch-wake
node --test pi/tests/*.test.mjs              # 63 tests: manager policy, CAS, wiring, deadlines
node --test claude-code/tests/*.test.mjs     # 33 tests: pure core policy, outbox, deadlines
npm test                                     # both
```

Nothing touches a real home directory, a real socket or a real token: the tests
inject fake transports, a fake clock, and in-memory persistence. The Pi wiring
tests read `index.ts` as text because the harness imports resolve only inside a
real Pi installation.

## Part of the Pi Web UI orchestration set

- Pi Web UI — https://github.com/valtterimelkko/pi-web-ui
  (`docs/ORCHESTRATION-OVERVIEW.md`, `docs/INTERNAL-API-ORCHESTRATION.md`)
- pi-orch — https://github.com/valtterimelkko/pi-orch
- the pack — https://github.com/valtterimelkko/agent-workflow-skills/blob/main/packs/pi-web-ui-orchestration-pack/README.md
- the watch-wake companion — this folder, [`README.md`](README.md)
- skills — [`skills/pi-web-ui-internal-api-orchestration/`](../../skills/pi-web-ui-internal-api-orchestration/SKILL.md),
  [`skills/long-horizon-waiting-strategies/`](../../skills/long-horizon-waiting-strategies/SKILL.md),
  [`skills/orchestrated-child-worker/`](../../skills/orchestrated-child-worker/SKILL.md)
