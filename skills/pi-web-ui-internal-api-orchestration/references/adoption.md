# Session adoption — linking existing sessions as children (contract 1.40.0)

Adoption links a session under a parent **after the fact** — the same registry
`parentSessionId` linkage and `child_dispatched` / `child_turn_ended` fan-out
that create-time linkage (`X-Parent-Session`) produces, but applied to a
session that already exists. Two forms:

- **Registered session** — the child already exists in the registry (e.g. it
  was created earlier without parent linkage): `POST /sessions/:id/adopt`.
- **Native CLI session** — the child ran outside Pi Web UI entirely and only
  exists as an artefact on disk: `POST /sessions/adopt-native`.

Adoption itself is display-only registry metadata. It never moves transcripts,
restarts runtimes, or changes session ownership, and it never modifies the
native artefact (resolution is read-only: bounded preview, ≤5 MiB line count).
But linked children are full supervision targets: `child_dispatched` publishes
on the parent's broker key and browser surface, and `child_turn_ended` is
watchable via the normal watch surface — exactly as for create-time children.

Canonical server-side reference: the *Session adoption* section of the
[Pi Web UI Internal API documentation](https://github.com/valtterimelkko/pi-web-ui/blob/master/docs/INTERNAL-API.md)
(contract 1.40.0).

## The operator gate — read this before any adoption

> **If a session you are about to adopt was initiated or used in a CLI tool
> (`claude`, `cmdc`, `agy`, `opencode`, `pi`), you MUST ask the operator and
> wait for their explicit confirmation that they have exited that CLI tool
> successfully — before you adopt it.**

Why this is a hard gate rather than politeness: after adoption, the parent
dispatches into the child and Pi Web UI **resumes the same native artefact in
its own subprocess** — `claude --resume <native-id>` (or the SDK `resume:`),
`cmdc --resume <native-id>`, or Antigravity conversation continuation. If the
operator's interactive CLI is still open on that session, two live owners are
writing to one conversation:

- Claude CLI session files carry a `last-prompt` lock entry; an active or
  uncleanly closed interactive CLI blocks any `--resume` with
  `Session ID already in use`. (The server strips stale locks left by *its
  own* killed subprocesses; it will not fight a live interactive session.)
- Concurrent writers append to the same JSONL/db artefact and continuation
  diverges — transcripts split, context disagrees, runs corrupt.

Gate checklist:

1. **Ask** before adopting: "I'm about to adopt session X as a child. Was it
   started or used in a CLI tool? If so, please exit that CLI and confirm it
   exited cleanly."
2. **Wait for the explicit confirmation.** No confirmation → no adoption;
   record the blocked state and move on.
3. Only then adopt. **Do not dispatch into the child until the gate is
   satisfied** — if there is any sign the CLI may have been re-opened, ask
   again before the first prompt.

Sessions created through Pi Web UI or the Internal API have no interactive CLI
attached; they need no ask. If you cannot tell how a session was started, ask
rather than assume.

## Ownership status and fenced sessions (contract 1.45.0)

A Pi session the web UI loaded while a CLI owned its lease stays **fenced**:
input swallowed, goal mutations refused. From contract 1.45.0 the API handles
both outcomes mechanically on the next prompt/goal/control action:

- **Live foreign owner** → `409 SESSION_OWNED_BY_OTHER_RUNTIME` with
  `ownerPid`, `ownerMode`, `reason` — no run is created and nothing is touched.
  Stop the other runtime or do an intentional `/autocompact75 handoff` +
  `/autocompact75 claim` transfer, then retry.
- **Dead owner** (including a recycled pid — liveness is proven by pid AND the
  lease's recorded process-start identity, and uncertain evidence fails
  closed) → the API **recovers automatically** (dispose→rehydrate, pins
  preserved, model binding re-applied) and the action proceeds.
- `GET /sessions/:id` and both adopt responses carry a display-only `ownership`
  snapshot (`status`: unknown/unmanaged/owned/conflict/uncertain, plus
  `reason`/`ownerPid`/`ownerMode`/`leaseState`; `unknown` on older extensions
  never gates). Adoption stays display-only — it reports ownership but never
  recovers or modifies leases.

For brand-new long work on a big finished session, prefer a fresh child with a
file handoff brief over adopting the finished session — recovery or fencing
then never touches the original artefact.

## Discover what exists

Registered sessions (ended ones included; liveness is `status`/`lastActivity`,
never mere presence):

```text
GET $API_BASE/sessions?limit=&runtime=&since=&cwd=
```

Unmanaged native CLI sessions on disk (contract 1.30.0 scan — read-only,
never mutates the registry):

```text
GET $API_BASE/sessions/native[?runtime=claude,commandcode,opencode,antigravity&limit=&since=]
```

- Antigravity discovery includes the **desktop** conversation root as well as the CLI one
  (contract 1.42.0); each item's `nativeId` is still the bare base name, and `runtime`
  says which agy it is.
- `limit` is 1–200 (default 20, applied after mtime sort); `since` filters on
  file mtime (ISO 8601 or epoch-ms).
- `runtime=pi` is refused with a `400`: native pi sessions are auto-discovered
  into the registry by the SessionWatcher — use `GET /sessions?runtime=pi`.
- Each item: `runtime`, `nativePath`, `mtime`, `size`, best-effort `cwd`,
  bounded `preview`, and `knownInRegistry` / `registrySessionId` when the
  registry already tracks it.

Each item also names the artefact path, so you can read a discovered session's
content directly before adopting (JSONL is line-delimited JSON; opencode items
are small JSON documents; antigravity items are SQLite conversation databases —
use the `agy` CLI for those).

## Adopt a registered session

```text
POST /api/v1/sessions/:id/adopt
{"parentSessionId": "<parent>", "alias": "worker-1", "role": "db-migration"}
```

- The parent may also arrive via the `X-Parent-Session` header (header wins;
  a registry id or session path is accepted).
- `alias` becomes the child-card label; `role` is an advisory echo.
- Response 200: `{success, childSessionId, parentSessionId, runtime}`.
- Same operation via the P1 control lane:
  `POST /sessions/:id/control` `{"action": "adopt", "parentSessionId": "…"}`.
- Errors: `404 SESSION_NOT_FOUND` (child or parent unknown); `400
  INVALID_REQUEST` (missing parent identity, self-adoption, or an adoption
  that would close a parent cycle).

## Adopt a native CLI session

```text
POST /api/v1/sessions/adopt-native
{"runtime": "claude", "nativeId": "<native-id>", "cwd": "/path/to/project",
 "parentSessionId": "<parent>", "alias": "worker-1", "role": "scout"}
```

- `runtime` — one of `claude`, `commandcode`, `opencode`, `antigravity`. `pi`
  is rejected (auto-discovered; adopt a registered pi session via `/adopt`).
- `nativeId` — the **bare artefact base name** (claude/commandcode/antigravity
  identifier, opencode `ses_*`). Path separators and `..` are refused, and every
  candidate path is containment-checked against its runtime root before any
  read.
- `cwd` — optional; narrows the artefact search to that project directory
  (cross-project fallback stays bounded) and seeds the registry `cwd`.
- An already-registered native id is adopted in place — no duplicate entry;
  the response reports `adopted: "existing"` vs `"created"`.
- Response 200: `{success, sessionId, runtime, parentSessionId?, adopted,
  nativePath, cwd?, alias?, role?}`.
- Errors: `404 NATIVE_SESSION_NOT_FOUND` (artefact not on disk), `404
  SESSION_NOT_FOUND` (parent unknown), `400 INVALID_REQUEST` (bad body).

The browser UI exposes the same capability (`GET /api/sessions/native`,
`POST /api/sessions/import-native`, "Resume CLI Session" modal); the Internal
API remains the canonical contract surface.

## After adoption

- **Use the returned internal `sessionId`** for prompt, control, watch, and
  evidence calls — not the native id. The identifier-forms warning applies:
  resolve first, never guess (`GET /sessions/:id/info`).
- Dispatch exactly as for any child (`POST /sessions/:id/prompt`, detached
  where the run may outlive you). Adopted children produce normal run receipts
  and idle→running→idle status transitions; `child_dispatched` and
  `child_turn_ended` fan out to the parent as documented in `walk-away.md`.
- Keep tracking the tree yourself: there is still no `GET /sessions?parent=…`
  filter and no orchestration job registry.
- The native transcript is never modified by adoption and is retained on
  registry delete — the operator's history survives cleanup of your entries.

## Coordination notes for adopted children

Adoption links only the Pi Web UI registry tree. If your wider harness has
another coordination surface, record a one-line task/owned-paths note for each
adopted child in your hand-back or coordination directory. Keep the registry
`parentSessionId` as the source of truth for Pi Web UI nesting; do not create a
second hierarchy that can drift.

## Worked example

```bash
SOCKET="${PI_WEB_UI_SOCKET:-$HOME/.pi-web-ui/internal-api.sock}"
TOKEN="$(cat "${PI_WEB_UI_TOKEN_PATH:-$HOME/.pi-web-ui/internal-api-token}")"
API_BASE="${PI_WEB_UI_API_BASE:-http://localhost/api/v1}"
api() { curl --silent --show-error --unix-socket "$SOCKET" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' "$@"; }

# 1. Capability gate — adoption exists from contract 1.40.0
api "$API_BASE/capabilities" | jq '.contract'

# 2. Discover the native CLI session you mean to adopt
api "$API_BASE/sessions/native?runtime=claude&limit=20" \
  | jq '.sessions[] | {runtime, nativePath, cwd, mtime, knownInRegistry, preview}'

# 3. OPERATOR GATE — if this session was used in a CLI, ask the operator to
#    exit that CLI tool and wait for their explicit confirmation. Not optional.

# 4. Adopt it under your session (body parent or X-Parent-Session)
api -X POST "$API_BASE/sessions/adopt-native" \
  -H "X-Parent-Session: $PI_SESSION_ID" \
  -d '{"runtime":"claude","nativeId":"<native-id>","cwd":"/path/to/project","alias":"worker-1"}'
# → {"success":true,"sessionId":"<internal-id>","runtime":"claude",
#    "parentSessionId":"…","adopted":"created","nativePath":"…","alias":"worker-1"}

# 5. Dispatch into the adopted child like any other child; watch yourself as usual
api -X POST "$API_BASE/sessions/<internal-id>/prompt" \
  -d '{"message":"…","verbosity":"answers","detach":true}'
```

Validation evidence: [`live-validate-adopt.mjs`](https://github.com/valtterimelkko/pi-web-ui/blob/master/scripts/live-validate-adopt.mjs)
(18/18 checks on a disposable server) and the cross-runtime parent-child
adoption E2E ([`live-validate-parent-child-e2e.mjs`](https://github.com/valtterimelkko/pi-web-ui/blob/master/scripts/live-validate-parent-child-e2e.mjs)).
