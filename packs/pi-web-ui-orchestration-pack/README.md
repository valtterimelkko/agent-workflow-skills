# Pi Web UI orchestration pack

> **Part of a set of four public repositories that work together:** [Pi Web UI](https://github.com/valtterimelkko/pi-web-ui) (server and Internal API) · [`pi-orch`](https://github.com/valtterimelkko/pi-orch) (thin parent client) · **this pack** (the discipline) · the [`watch-wake` companions](../../companions/watch-wake/README.md) (the wake mechanism). How they fit and the install order: [orchestration fixture set guide](https://github.com/valtterimelkko/pi-web-ui/blob/master/docs/ORCHESTRATION-FIXTURE-SET.md).

Four agent skills for running multi-agent orchestration through **Pi Web UI**'s
local Internal API — dispatching child sessions across runtimes, supervising
them without polling, demanding evidence before acceptance, and keeping
credentials out of everything you publish.

## Who this is for

- You run **[Pi Web UI](https://github.com/valtterimelkko/pi-web-ui)** on the
  same machine as your agent (its Internal API is a local Unix socket, so
  child sessions land in the same registry the browser shows).
- You want a parent agent to split work across models and runtimes, walk away
  while children run, and come back to verified results rather than a wall of
  polling.
- You use any harness that can read a `SKILL.md`: Pi Coding Agent, Claude Code,
  OpenCode, Antigravity, Command Code, or something of your own.

## What you need

- **Pi Web UI** running locally, with its Internal API socket and token
  reachable. Defaults: `$HOME/.pi-web-ui/internal-api.sock` and
  `$HOME/.pi-web-ui/internal-api-token`; both are overridable by environment
  variable (`PI_WEB_UI_SOCKET`, `PI_WEB_UI_TOKEN_PATH`).
- At least one runtime configured in Pi Web UI (Pi, Claude Code, OpenCode,
  Antigravity, or the gated Command Code path).
- **Optional but recommended: [`pi-orch`](https://github.com/valtterimelkko/pi-orch)**
  — a thin parent client for the common loop (`spawn`, `prompt`, `wait`,
  `result`, `verify`, `cleanup`, `status`, plus `goal` and `watch`). It removes
  hand-written curl and `sleep` loops; the raw Internal API is fully documented
  if you prefer it. The orchestration skill's `references/pi-orch.md` covers the
  verbs, goal budgets, owner ids, waiting patterns, route caps and exit codes.
- **For a bare CLI parent (Claude Code or Pi you started yourself): the [`watch-wake` companions](../../companions/watch-wake/README.md).** They are what lets the parent end its turn after dispatching and be woken when a child finishes; the waiting skill assumes them (and describes the plain fallback when they are absent).
- No cloud account, no orchestration server, and no extra infrastructure.

## The four skills

| Skill | Role |
|---|---|
| [`pi-web-ui-internal-api-orchestration`](../../skills/pi-web-ui-internal-api-orchestration/SKILL.md) | **The parent's loop.** Discovery (`/capabilities`, `/capacity`, `/models`), session creation and retention, dispatch modes, goals, watch-wake, evidence, adoption, cleanup, and the child directive every dispatch must carry. This is the main skill; start here. |
| [`long-horizon-waiting-strategies`](../../skills/long-horizon-waiting-strategies/SKILL.md) | **Going idle safely.** The pre-idle checklist, wake mechanisms per harness, model-free backstops, the liveness discriminator, and how to supervise a child without over-watching. Read it before your first long wait. |
| [`agent-os-child`](../../skills/agent-os-child/SKILL.md) | **The child's discipline.** Every dispatched child is told to load this: owned paths, strict TDD, clean commits, command receipts with exit statuses, the hand-back protocol, reviewer rules, and never self-sign-off. |
| [`secret-scanning`](../../skills/secret-scanning/SKILL.md) | **Before publishing.** Scan repositories and artefacts for credentials with gitleaks, redact findings, and keep credentials outside the repo tree. |

### How they fit together

- The **parent** loads `pi-web-ui-internal-api-orchestration` for the loop and
  `long-horizon-waiting-strategies` before any idle window.
- Every dispatch prompt **mandates `agent-os-child`** — no harness
  injects it automatically, so a brief that omits it produces drift.
- When the work produces repos, evidence bundles or published artefacts,
  **`secret-scanning`** is the check before anything leaves the machine.
- The waiting skill and the parent skill cross-reference each other: the parent
  skill owns the API surface, the waiting skill owns the idle safety on top.

## Install

The skills are plain folders containing a `SKILL.md` (some have
`references/`). Copy the ones you need into your harness's skills directory:

```bash
git clone https://github.com/valtterimelkko/agent-workflow-skills
cp -r agent-workflow-skills/skills/pi-web-ui-internal-api-orchestration <your-skills-dir>/
cp -r agent-workflow-skills/skills/long-horizon-waiting-strategies      <your-skills-dir>/
cp -r agent-workflow-skills/skills/agent-os-child            <your-skills-dir>/
cp -r agent-workflow-skills/skills/secret-scanning                      <your-skills-dir>/
```

- **Pi Coding Agent:** skills live under `~/.pi/agent/skills/`.
- **Claude Code:** skills live under `~/.claude/skills/` (or a project skills
  directory).
- **Other harnesses:** any directory your agent can read; point it at the
  `SKILL.md` or adapt the wording. The skills are deliberately harness-neutral.

## First run

1. Confirm the API is present:
   ```bash
   ls -l "$HOME/.pi-web-ui/internal-api.sock" "$HOME/.pi-web-ui/internal-api-token"
   ```
2. Ask the server what it can do (never trust a remembered model list):
   ```bash
   TOKEN="$(cat "$HOME/.pi-web-ui/internal-api-token")"
   curl --silent --show-error --unix-socket "$HOME/.pi-web-ui/internal-api.sock" \
     -H "Authorization: Bearer $TOKEN" http://localhost/api/v1/capabilities
   ```
3. Read `pi-web-ui-internal-api-orchestration` §1–§6, then dispatch a small
   child and watch it end. The parent skill's §3 holds the brief template and
   the mandatory child directive.

## What is not included

- **Host-specific tooling.** The pack documents the method, not the author's
  machine: there is no board/coordinator server, no notification relay, no
  scheduler, no model routing table and no provider credentials. The optional
  watch-wake extension and mod are published separately as code in
  [`companions/watch-wake`](../../companions/watch-wake/README.md). Where a step
  benefits from other tooling (a background-shell tool, a notification path),
  the skill states the plain fallback.
- **Pi Web UI itself and `pi-orch`.** Both are separate repositories (linked
  below), not vendored here.
- **Live validation.** Proving a change to Pi Web UI works belongs to Pi Web
  UI's own repository and its live-validation docs; this pack is for *using*
  the API, not testing it.

## Links

- **Pi Web UI** — https://github.com/valtterimelkko/pi-web-ui
  (Internal API docs: [`docs/INTERNAL-API.md`](https://github.com/valtterimelkko/pi-web-ui/blob/master/docs/INTERNAL-API.md),
  [`docs/INTERNAL-API-ORCHESTRATION.md`](https://github.com/valtterimelkko/pi-web-ui/blob/master/docs/INTERNAL-API-ORCHESTRATION.md),
  [`docs/INTERNAL-API-CONTRACT.md`](https://github.com/valtterimelkko/pi-web-ui/blob/master/docs/INTERNAL-API-CONTRACT.md))
- **pi-orch** — https://github.com/valtterimelkko/pi-orch

## Provenance

These four skills are adapted from the author's private skills library for
public use:

- `pi-web-ui-internal-api-orchestration` and `long-horizon-waiting-strategies`
  keep their canonical names; host-specific routing, subscriptions, private
  repositories and incident details have been removed or generalised.
- `agent-os-child` keeps the name of the author's private skill (so `pi-orch`
  and the Pi Web UI docs refer to one name everywhere), with the
  coordination-layer mechanics removed. "Agent OS" is the author's private
  layer and is not needed; its directive wording about a "board" can be
  ignored. See the [what-to-ignore table](https://github.com/valtterimelkko/pi-web-ui/blob/master/docs/ORCHESTRATION-FIXTURE-SET.md#adopting-outside-the-authors-setup-what-to-ignore).
- `secret-scanning` is the canonical secret-scanning skill, with host paths
  generalised.
