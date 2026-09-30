<!-- Loaded from SKILL.md §1/§3/§5/§7 stubs (create-time options, dispatch admission, model binding, questions, finding sessions). Open when binding a model to a session, when a child asks a question or permission, or when finding/identifying sessions. -->

# Session identity, child questions, and finding sessions

## Control actions (prepare)

`POST /sessions/:id/control`:

```json
{ "action": "set_model", "modelId": "opus" }
{ "action": "set_thinking_level", "level": "high" }
{ "action": "set_effort", "effort": "low" }
{ "action": "acquire_retention", "retention": { "mode": "durable", "ttlSeconds": 7200, "ownerId": "owner-b" } }
{ "action": "renew_retention",  "retentionLeaseId": "<uuid>", "ownerId": "<owner>", "pinTtlSeconds": 7200 }
{ "action": "release_retention","retentionLeaseId": "<uuid>", "ownerId": "<owner>" }
```

For Pi, `set_thinking_level` currently requires the runtime session to be loaded;
an unloaded but durable session can return 404 `Pi session not loaded`. Prefer
create-time binding, inspect the existing binding before acting, and do not
interpret a refused control as applied or blindly repeat it. Do not spend an
unrelated model turn just to warm a session whose intended binding is already
correct; verify the real dispatch receipt when authorised work starts.

`set_thinking_level` accepts `off | minimal | low | medium | high | xhigh | max`;
check the model's `thinkingLevels` first. For Pi, the response `level` is the
*effective* read-back after SDK clamping, not an echo. Since contract 1.33.0,
Pi `set_model` / `set_thinking_level` also **persist** to the session's stored
binding, so a rebind survives eviction and server restarts — you no longer need
to re-apply a model after a control change just because the server recycled.

`set_effort` is the **Command Code** control and is a different axis — it is
idle-only, applies to the next turn, returns the canonical binding plus requested
and accepted aliases and a capability hash, and never changes `thinkingLevel`.

## Create-time options

Runtime subprocesses created through the Internal API receive
`PI_WEB_UI_SESSION_ID`, `PI_WEB_UI_SESSION_ORIGIN` and
`PI_WEB_UI_PARENT_SESSION_ID`, so a managed session can learn its own id and parent.

## Dispatch modes and admission

The modes table is in SKILL.md §3.

A busy `steer` joins an existing turn, so it is not subject to execution
admission: it holds no execution permit, gets its own request receipt, and
cannot be refused for exhausted execution slots — steering a busy parent works
even when `/capacity` reports every slot full, which is exactly when you need
it. Only the emergency memory floor still applies (`503 memory_pressure`).
New-turn `prompt`/promoted-`follow_up` dispatches remain admission-checked
(`429` slot exhaustion, `503` resource pressure; read `Retry-After`).

## Model binding — the create echo is not proof

Claude on the API is **SDK-only** (contract 1.46.0): `/models?runtime=claude` lists SDK
profiles only, and any other backend fails `403 CLAUDE_BACKEND_NOT_ALLOWED`
(`features.claudeBackendPolicy`). For a profile-backed Claude route, create with only `model: "profile:<id>"`. Do
not also send a conflicting `profileId`, and do not create a broad alias then
assume a later model switch preserved the intended backend. Verify identity
before prompting: the create response should echo `runtime`, the same
`model`/`modelSelector`, and `executionInstanceId`; then `GET /sessions/:id/info`
should agree and add `claudeProfileId`, `claudeProfileBackend`,
`claudeProviderId`, and the effective `model`. A mismatch fails closed — clean up
the unused session rather than prompting it.

**The create response's model echo is not proof of binding — for any runtime.**
It can echo exactly what you asked for while the session binds to the backend's
default. Two reads settle it, and you want both before spending a long run:

- `GET /sessions/:id/info` — the effective `model`, which is **provider-qualified**
  (`provider/model-id`, not `model-id`). A bare id here is unverified, not
  confirmed.
- For Pi sessions, the on-disk record at `sessionPath` carries `model_change`
  entries with `provider` and `modelId`. **The LAST one binds.** A session that
  initialises on the default and rebinds milliseconds later produces two entries;
  reading only the first tells you the opposite of the truth.

Observed failure shape: one session showed `provider-a/model-a` followed
milliseconds later by `provider-b/model-b`. A run silently bound a child to a
materially more expensive model than intended, with a create response that read
correctly throughout. Creating with `model` in the create body bound cleanly in
one entry; create-then-`set_model` produced the default-first pattern. Prefer the
former, and verify regardless.

Why bindings drift at all: the Pi SDK restores history bindings only for sessions
that already carry messages, so before 1.33.0 a session unloaded between create
and dispatch rehydrated silently on the runtime default — a benchmark drift
incident that receipts would have exposed.

**Since contract 1.33.0 the verification shortcut is the run receipt**: every
dispatch re-applies a drifted Pi binding before the turn and records
`servedModel` (model actually bound) + `modelRebound` (drift corrected) on the
receipt, and emits a `model_rebound` broker event. Read `GET /runs/:runId` after
dispatch instead of scraping `model_change` entries. A stored binding that can
no longer be applied fails the run loudly (`MODEL_NOT_APPLIED` for an
unresolvable model, `PROVIDER_NOT_ALLOWED` for a provider blocked by
`INTERNAL_API_BLOCKED_PI_PROVIDERS`) — silent default fallback is no longer
possible for sessions with a stored binding. Sessions created without a model
intentionally run the runtime default and are not re-bound.

## When a child asks a question

A child that stops to ask is otherwise a dead end, so this path matters.

```text
GET  $API_BASE/sessions/:id/approvals/pending
POST $API_BASE/sessions/:id/approvals/:requestId/respond
```

`/approvals/pending` reports live Claude SDK `AskUserQuestion` requests; runtimes
without a synchronous pending surface return an empty list. For a permission
request the body is `{"approved": true}`. For an SDK question it carries
structured answers keyed by the **exact question text**:

```json
{
  "approved": true,
  "answers": { "Which region?": "eu-west-1", "What size?": "small" },
  "annotations": { "Which region?": { "preview": "eu-west-1", "notes": "closest to users" } }
}
```

Multi-select answers are comma-separated. `cancelled: true` dismisses without
answering. The path identifier may be the question `requestId` **or** its
`toolCallId` — both resolve the same pending callback. A success returns
`resolved: true`; an unknown id returns `404 APPROVAL_REQUEST_NOT_FOUND`, and a
question that already timed out or disconnected returns `409 ASK_ALREADY_CLOSED`.
Nothing returns 2xx unless a live request was genuinely resolved.

Never fabricate an answer on the operator's behalf, and never treat an accepted
HTTP response as resolved work.

## Filters, native sessions, and identifier forms

**Server-side filters (contract 1.30.0)** — no need to download and filter the
whole registry any more:

```text
GET $API_BASE/sessions?runtime=pi,claude        # subset of pi,claude,opencode,antigravity,commandcode
GET $API_BASE/sessions?since=<iso>
GET $API_BASE/sessions?cwd=/path/to/project     # exact match
GET $API_BASE/sessions?limit=5                  # 1..1000, applied after sorting/filtering
```

Each entry also carries two additive fields (1.30.0): `archived` (web UI
archive state) and `source` (`browser` | `internal-api` | `native-discovered`
| `unknown`). `source` is how you separate real work from smoke sessions
created after 1.30.0; pre-1.30.0 entries are `unknown`.

**Direct-CLI sessions of the other runtimes are not in the registry.** If a
human or agent ran `claude`, `cmdc -p`, `opencode`, or `agy` directly, the only
trace is the runtime's native store. Query the bounded read-only scan instead
of hand-globbing (contract 1.30.0):

```text
GET $API_BASE/sessions/native?limit=10                 # all four runtimes, newest-first
GET $API_BASE/sessions/native?runtime=claude&since=<iso>
GET $API_BASE/sessions/native?before=<oldest-mtime-of-last-page>
```

The scan is newest-first with `limit` capped at 200 (default 20), so a
high-volume runtime silently truncates. Page past the cap with `before` — an
exclusive mtime upper bound (ISO 8601 or epoch ms, junk → `400`): pass the
oldest `mtime` of the current page to fetch the next-older page without
overlap. `truncated:true` in the response means older items remain; combine
`since` + `before` for a window.

Items return `nativePath`, `mtime`, size, best-effort `cwd`/`preview`, and
`knownInRegistry`/`registrySessionId`. `runtime=pi` is refused with an
explanatory 400 — native pi sessions are auto-discovered into the registry by
the SessionWatcher, so `GET /sessions?runtime=pi` already covers them. Read a
discovered session's content straight from `nativePath` (claude/cmdc JSONL are
line-delimited JSON; opencode items are small JSON; antigravity items are
SQLite conversation databases).

**Identifier forms are not interchangeable across routes.** A session carries
several: the Pi Web UI internal id, the registry `sessionPath`, and a
runtime-native id (Claude native id, OpenCode `ses_*`, Antigravity conversation
id). Control, diagnostics, notification, and watch routes want the **internal
id**; `/runs/:runId` wants a `runId`. Resolve first rather than guessing —
`GET /sessions/:id/evidence` accepts all supported forms and returns the
canonical `sessionId`, and `npm run debug:where -- <id|path|native-id>` in the
[Pi Web UI repository](https://github.com/valtterimelkko/pi-web-ui) is the offline
locator. Do not open with a global grep.
