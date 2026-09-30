<!-- Read before selecting a runtime or model for a child. -->

# Choose and record your route

A dispatch route is a complete, reproducible tuple:

```text
runtime + provider + exact selector + advertised thinking/effort level + role
```

Treat the route as live configuration, not as a remembered model list. The
server's current catalogue, the provider's remaining quota, and the task's role
are the authority at dispatch time.

## Discover the live selector

Immediately before a real dispatch:

```text
GET $API_BASE/models?runtime=<runtime>
```

1. Filter the response to the runtime and capability you need.
2. Select the exact `selector` string returned by `/models`; copy it rather than
   constructing a `provider/model` value yourself.
3. Confirm that the entry advertises the requested thinking level or effort
   level. Thinking and effort are separate axes; do not map one onto the other.
4. Record the selected runtime, provider, selector, level, and role before
   creating the session.

Zero matches, multiple matches, a stale selector, or a missing required level is
a refusal. Do not silently choose a similar entry from another provider or
runtime.

## Check admission and provider headroom separately

`GET $API_BASE/capacity` answers whether the local server can admit a new turn.
It does not answer whether a provider has quota remaining. Before dispatching,
check the provider's remaining quota in its own dashboard or CLI, including any
shared pool or reset window, and record the check with the route.

A metered provider requires an explicit authorisation record for the work. The
presence of a metered entry in `/models`, a low price, or a convenient fallback
is not authorisation. Never hide a provider change or an exhausted-quota
fallback in an otherwise successful run.

## Bind and assert the route

Prefer binding the model in the session-create request. The create response's
model echo is not proof that the runtime applied the binding. Before spending a
long run, read:

```text
GET /sessions/:id/info
```

The effective model must be provider-qualified and must match the recorded
selector. For a profile-backed route, verify the profile and backend fields as
well. A mismatch is a failed preflight: do not prompt the session; clean it up
or start a correctly bound one.

After dispatch, read the run receipt:

```text
GET /runs/:runId
```

Assert `receipt.servedModel` against the intended provider-qualified model and
inspect `receipt.modelRebound`. If the runtime reports a fallback, a rebound, or
an unresolvable binding, record it as such; never report the requested route as
the served route. A model-comparison result is incomplete until the receipt has
been checked.

## Set reasoning explicitly

Request a thinking level only after reading the selected entry's advertised
`thinkingLevels`. If the entry exposes `off`, `minimal`, `low`, `medium`, `high`,
`xhigh`, or `max`, request the exact level the task requires and record the
choice. Do not silently downgrade when the requested level is unavailable.

For runtimes with a separate effort axis, read the advertised `effort` values
and request one of those instead. Store both fields distinctly when both are
present.

## Compare backends honestly

For a backend or provider comparison, use **one fresh session per profile** (or
per backend binding). Send the same prompt and constraints to each session and
collect the run receipt and transcript separately. Do not switch a session's
backend after a comparison run or compare a session whose binding was not
verified. Keep the route tuple with each result.

## Use an independent reviewer

A reviewer is a role, not a fixed model. Create a fresh, read-only reviewer
session after the implementer hands back, in the same working context if
needed, but use a **different model family** from the implementer. Choose the
highest reasoning level that the live reviewer route advertises, verify the
served model, and keep the reviewer's route and evidence separate from the
implementation result.

A reviewer does not acquire the implementer's authority and cannot sign off its
own work. If a review route is unavailable, record the gap or choose another
live route explicitly; do not silently use the implementer's session or family.

## Route record

Keep a compact record with the dispatch and receipt:

```markdown
- role: <implementer | reviewer | synthesiser | ...>
- runtime: <runtime>
- provider: <provider>
- selector: <exact selector copied from /models>
- thinkingLevel: <advertised level, or n/a>
- effort: <advertised effort, or n/a>
- quota check: <provider dashboard/CLI and time checked>
- sessionId: <internal session id>
- runId: <dispatch run id>
- servedModel: <provider-qualified receipt value>
- modelRebound: <true | false>
- fallback: <none, or the recorded fallback>
```

The route record is part of the evidence. If any field is unknown, stop short of
claiming a verified comparison or completion.

For the endpoint and receipt contracts, use the public
[Internal API documentation](https://github.com/valtterimelkko/pi-web-ui/blob/master/docs/INTERNAL-API.md).
For live end-to-end checks, use the repository's
[Live Validation documentation](https://github.com/valtterimelkko/pi-web-ui/blob/master/docs/LIVE-VALIDATION.md).
