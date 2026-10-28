<!-- Read before selecting a runtime or model for a child. -->

# Choose and record your route

A dispatch route is a complete, reproducible tuple:

```text
runtime + provider + exact selector + advertised thinking/effort level + role
```

Treat the route as live configuration, never as a remembered model list. The server's
current catalogue, the provider's remaining quota and the task's role are the authority at
dispatch time. Nothing in this file overrides them.

## Discover the live selector

Immediately before a real dispatch:

```text
GET $API_BASE/models?runtime=<runtime>
```

1. Filter the response to the runtime and capability you need.
2. Select the exact `selector` string returned by `/models`; copy it rather than
   constructing a `provider/model` value yourself.
3. Confirm that the entry advertises the requested thinking level or effort level.
   Thinking and effort are separate axes; do not map one onto the other.
4. Record the selected runtime, provider, selector, level and role before creating the
   session.

Zero matches, multiple matches, a stale selector, or a missing required level is a
refusal. Do not silently choose a similar entry from another provider or runtime.

## Choose by work class

Classify the work first, then choose within the class from measured headroom. The classes
are stable; the models in them are not.

| Class | What belongs here | What to choose |
|---|---|---|
| **Class 1 — default children** | routine, bounded work: small coding tasks, docs, analysis, data extraction, most reviews, most research. Expect this to cover roughly nine in ten children | a cheap, high-quota model from a generous subscription pool; keep a second, faster Class 1 route as the standing fall-back |
| **Class 2 — more demanding work** | planned implementation, demanding analysis, web and visual work, writing where quality is load-bearing | a stronger mid-tier model, capability first and headroom second |
| **Class 3 — the most demanding work** | planning and design, complex implementation, heavy reasoning, high-stakes judgement | the most capable model available, and only when that capability is load-bearing; otherwise stay in Class 2 |

Two rules sit above the classes:

1. **Check headroom before any dispatch.** Read `/capacity`, the provider's own dashboard
   or CLI, and the live `/models` list every time. The class ordering never overrides
   measured headroom.
2. **Same-family parents drain the shared pool faster.** If your own model shares a
   family or pool with a candidate child route, your turns and the child draw on the same
   allowance, so it empties faster than the read alone suggests. Weigh your own burn rate
   and prefer a different-family route when headroom is thin.

**Illustrative examples only.** Model names below are examples of the shape of each class,
not recommendations, and not a list to trust: selectors, availability, thinking levels and
pricing change, so read `/models` and `/capacity` live.

| Class | Illustrative route |
|---|---|
| Class 1 | a cheap fast model such as DeepSeek V4.1 Flash or GLM 5.3 Flash, on a subscription provider |
| Class 2 | a mid-tier model such as Claude Sonnet 5.5 or Gemini 3.8 Flash |
| Class 3 | the strongest available frontier model, such as Claude Opus 5.5 |

## Check admission and provider headroom separately

`GET $API_BASE/capacity` answers whether the local server can admit a new turn. It does not
answer whether a provider has quota remaining. Before dispatching, check the provider's
remaining quota in its own dashboard or CLI — a zero-model-token, read-only look, including
any shared pool, reset window or peak multiplier — and record the check with the route.

## Respect per-route concurrency caps

One provider route can only serve so many children at once: a route stops returning
completions somewhere around five to eight concurrent children, and a profile-capped
backend (`/capacity` → `claudeProfiles` or its equivalent) refuses new turns at its own
limit. `pi-orch` caps live children per selector (built-in defaults, `PI_ORCH_ROUTE_LIMITS`,
`--route-limit`) and refuses over the cap with exit `25` before creating anything; use
`--wait-for-slot` or spread a large wave across several routes rather than queueing it on
one. A server-side `429 PROFILE_CAPACITY_EXHAUSTED` is the same fact arriving later.

## Metered providers need explicit authorisation

Pay-as-you-go (metered, per-token) providers are never used unless the operator directly
authorises that provider for that work. This concerns the **provider**, not the model: the
same model served by a subscription provider is an ordinary route.

- Appearing in `/models` is not authorisation. A cheap-looking or "similar" metered entry
  is still off limits.
- Authorisation must be direct and specific: the operator names the provider or route for
  the task at hand. A general "pick the cheapest" or "use your judgement" instruction never
  covers metered spend.
- Read the account balance before spending, and treat a balance as information, never as
  permission.
- When the only way to satisfy a request is a metered route, stop and ask rather than
  substituting it or falling back to it silently.
- Record the authorisation (who, when, which provider) with the dispatch.

## Bind and assert the route

Prefer binding the model in the session-create request. The create response's model echo is
not proof that the runtime applied the binding. Before spending a long run, read:

```text
GET /sessions/:id/info
```

The effective model must be provider-qualified and must match the recorded selector. For a
profile-backed route, verify the profile and backend fields as well. A mismatch is a failed
preflight: do not prompt the session; clean it up or start a correctly bound one.

After dispatch, read the run receipt:

```text
GET /runs/:runId
```

Assert `receipt.servedModel` against the intended provider-qualified model and inspect
`receipt.modelRebound`. If the runtime reports a fallback, a rebound or an unresolvable
binding, record it as such; never report the requested route as the served route. A
model-comparison result is incomplete until the receipt has been checked.

## Set reasoning explicitly

Request a thinking level only after reading the selected entry's advertised
`thinkingLevels`. If the entry exposes `off`, `minimal`, `low`, `medium`, `high`, `xhigh`
or `max`, request the exact level the task requires and record the choice. Do not silently
downgrade when the requested level is unavailable.

For runtimes with a separate effort axis, read the advertised effort values and request one
of those instead. Store both fields distinctly when both are present.

## Hard exclusions

No silent substitution, ever:

- a disabled runtime (`enabled:false`) or a provider barred by
  `features.piProviderPolicy.blockedProviders`;
- a metered provider without the operator's authorisation for this task;
- a model you constructed yourself instead of copying a live selector;
- a Claude profile used for a non-Claude model, or any backend that fails
  `403 CLAUDE_BACKEND_NOT_ALLOWED`;
- a route you cannot verify on the receipt.

## Use an independent reviewer

A reviewer is a role, not a fixed model. Create a fresh, read-only reviewer session after
the implementer hands back, in the same working context if needed, but on a **different
model family** from the implementer — a same-family reviewer shares the implementer's blind
spots. Choose the highest reasoning level the live reviewer route advertises, verify the
served model, and keep the reviewer's route and evidence separate from the implementation
result. Never a metered route without authorisation.

A reviewer does not acquire the implementer's authority and cannot sign off its own work. If
a review route is unavailable, record the gap or choose another live route explicitly; do
not silently use the implementer's session or family.

## Compare backends honestly

For a backend or provider comparison, use **one fresh session per profile** (or per backend
binding). Send the same prompt and constraints to each session and collect the run receipt
and transcript separately. Do not switch a session's backend after a comparison run or
compare a session whose binding was not verified. Keep the route tuple with each result.

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

The route record is part of the evidence. If any field is unknown, stop short of claiming a
verified comparison or completion.

For the endpoint and receipt contracts, use the public
[Internal API documentation](https://github.com/valtterimelkko/pi-web-ui/blob/master/docs/INTERNAL-API.md).
For live end-to-end checks, use the repository's
[Live Validation documentation](https://github.com/valtterimelkko/pi-web-ui/blob/master/docs/LIVE-VALIDATION.md).
