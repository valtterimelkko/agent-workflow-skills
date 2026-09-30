---
name: long-horizon-waiting-strategies
description: "Strategies for surviving long waits and supervising dispatched child agents without over-watching: go idle safely with verified recovery, and build liveness-correct stuck-detectors — server-side watch-wake, bare-CLI watch extensions, model-free wake deadlines and independent process backstops, hand-back protocol (children are told to follow `orchestrated-child-worker`), liveness discriminator. Make sure to use this skill whenever waiting > few minutes — long-running child sessions, Internal API orchestration, builds/migrations/batch jobs/measurement windows, 'check back later' — or before polling, sleeping in-turn, holding a turn open, or re-checking child progress. Also for supervision design, child authority, heartbeats/stuck-detectors, child question protocol, wake not firing, dead-man/watchdog, going idle, micromanaging, or agent idle for hours. Covers Pi, Claude Code, Antigravity and Command Code mechanisms; supervision is harness-agnostic."
---

# Long-horizon waiting strategies

How to wait for hours without burning context, holding a turn open, or — the
failure that actually bites — **never waking up again**.

## What to read, in three tiers

**Tier 1 — Must read, every run that will idle.** These named sections, in
order, before you end any turn on a wait: *Harness applicability* (which wake
path applies to you), *The pre-idle checklist*, *The child contract* (every
dispatch mandates `orchestrated-child-worker`), *Choose the backstop for the failure you
are covering* and *The backstop ladder*.

**Tier 2 — Must read when the situation matches.** Conditional references —
mandatory within their situation, skippable outside it:

| Reference | Mandatory when… |
|---|---|
| `references/supervision-and-stuck-detectors.md` | you will dispatch or supervise a child, or build any stuck-detector — read **before** the dispatch, not after |
| `references/claude-code-watch-wake-and-background-watcher.md` | you are a Claude Code CLI parent — before that harness's first long wait |
| `references/antigravity-reactive-watcher-and-schedule.md` | you are an Antigravity CLI/IDE parent — before that harness's first long wait (covers `wait-watch.sh` and orchestrator invariants) |

**Tier 3 — Situational.** *Supervising a dispatched child* (near the end:
operator-confirmed capability, over-supervision, the liveness discriminator,
the hand-back protocol, goal cases) is required reading before you dispatch an
agent child and skippable when you are waiting on a build, a measurement
window, or a batch job with no child agent.

Skipping a Tier 1 or Tier 2 item is how idle windows end with nobody waking
up.

## The problem this solves

Any wait longer than a few minutes has three bad options and one good one:

- **Polling in-turn** (check, sleep, check again inside your own turn) burns
  context, blocks the session, and dies with the turn.
- **Holding the turn open** on a stream or a `wait` call dies with the
  connection.
- **Ending your turn with no wake mechanism** means the work finishes and
  nobody notices — you sit idle until a human asks "did it work?". This is the
  worst outcome and it happens silently.
- **The good option:** end your turn with a *verified wake path and backstop*, go fully
  idle, and reconcile when the wake arrives.

Use **primary + backstop**, with the delivery path and failure domain made
explicit. No in-process mechanism can guarantee recovery after the parent dies
or its event loop blocks; do not turn "armed" into an unconditional guarantee.

## Harness applicability — read this first

Every harness has a proven wake path. The names differ; the contract does not:
**register an observer on the child, arm one model-free backstop, end the turn,
reconcile on wake.** Read the matching reference **before that harness's first
long wait**.

- **Pi** (Pi Coding Agent CLI or a Pi SDK host with watch-wake and background-task
  extensions): `watch_wake_register`, `wake_deadline` and background shell tools are
  covered below. Background task completion is a follow-up message that triggers a
  turn; that delivery *is* the wake.
- **Claude Code**: server-side `onFire` cannot reach a bare `claude` CLI, but a
  host-wide `watch-wake` mod can: `watch_wake_register` on the child plus
  `wake_deadline` as the model-free backstop, then end the turn; the wake starts a
  new turn in the idle session. Where the mod tools are absent
  (`--bare`, `--safe-mode`), a capped background Bash task that *exits* is the wake. A
  managed Claude session uses server `onFire` targeting `$PI_WEB_UI_SESSION_ID`, with a
  `deadline` condition as backstop. `claude -p` cannot wait (the mod refuses it): hand
  back instead. Differences from Pi: no harness background-shell tool (use
  `run_in_background` Bash for command-shaped waits), no goal engine or memory mod, and
  no subagent dead-man (none is needed).
  → `references/claude-code-watch-wake-and-background-watcher.md`
- **Antigravity**: as a **child** it is a first-class watch subject and, unlike a bare
  Claude CLI, a managed antigravity session is a valid `onFire` **target** (the server
  can prompt it, queue-while-busy since contract 1.37.0), so a supervised antigravity
  child wakes its managed parent without extra tooling. As a **parent** in the bare
  `agy` CLI or IDE, server-side `onFire` cannot reach the process and hooks are
  synchronous lifecycle interceptors, not turn injectors. Use the reactive background
  task (`run_command` with low `WaitMsBeforeAsync`; process exit delivers a
  high-priority wake) paired with the native model-free task-scheduling tool
  (`TimerCondition: <taskId>`, auto-cancels on completion). Obey zero-token waiting: do
  not poll the task manager in a loop; end the turn immediately and let the reactive
  system message wake you.
  → `references/antigravity-reactive-watcher-and-schedule.md`
- **Command Code**: its watch-wake mod parks the run in the built-in `sleep` tool and
  wakes via queued follow-up; it cannot start a fully idle run, so park, don't exit.

## The pre-idle checklist — run it before EVERY idle window

> **Harness scope.** The *questions* below are harness-agnostic; the tool names
> in the answers differ. **Pi** (CLI or SDK host with watch-wake): `watch_wake_register`,
> `wake_deadline`, a background shell. **Claude Code**: the `watch-wake` mod, with the same
> `watch_wake_register` + `wake_deadline` contract (fallback: an exiting background
> watcher); a managed Claude session uses server `onFire` plus the server `deadline`
> condition. **Antigravity**: the exiting background task (`wait-watch.sh` via
> `run_command`, low `WaitMsBeforeAsync`) plus the native scheduling tool. **Command
> Code**: its watch-wake mod. See *Harness applicability* above before importing any
> named tool.

Before you end your turn on any wait, answer all four out loud. If you cannot,
you are not going to wake up.

1. **Name the delivery.** For each outstanding wake, name the exact tool call
   that delivers it into *this* session (server `onFire` targeting a managed
   session, `watch_wake_register`, background-task completion). "A watch exists"
   is not an answer — *delivery* is.
2. **Bare-CLI check.** If you are a bare pi or Claude Code CLI and children were
   dispatched via the Internal API, use a working `watch_wake_register` in this
   session. If the loaded tool is unavailable/broken, record an explicit bounded
   in-harness relay or exiting background task whose exit wakes this parent
   instead. A server-side
   `onFire` alone **cannot reach you** — including one armed on
   your behalf by a repo script or curl command; that serves audit/durability,
   not your wake. Verify by reading the tool result back, not from memory.
3. **Exactly one appropriate live backstop exists for this window** (selection
   below). Record its id/deadline and check its returned state.
4. **Both mechanisms verified**, then end your turn. On wake, run the On-wake
   checklist further down this file.

> **Server-side watch exists ≠ wake guaranteed.** These are different claims:
> evaluation (the server records that the condition fired) and delivery (a turn
> starts in your session) are separable. The watch ledger can be perfectly
> healthy while your session sits silent forever. The observed failure shape:
> a parent audits its own server-side watch (status active, correct conditions)
> and reports it will auto-resume — but as a bare CLI parent it has no
> delivery path, and it stays idle until a human intervenes. The wake extension
> works once actually called; the failure was never asking "what delivers my
> wake?".

## The child contract — every dispatch mandates `orchestrated-child-worker`

Your wake depends on the child ending its turn: a child that polls, sleeps or waits
for your reply holds the turn open, and the watch that would wake you never trips.
The `orchestrated-child-worker` skill is where the child learns to hand back by ending its
turn, to commit cleanly, to report commands with exit statuses, and never to
self-sign-off.

- **It is not injected for you.** Sessions created through the Internal API get the
  identity packet and scope warnings from the harness, not this
  skill. **Every dispatch brief must tell the child to load and follow
  `orchestrated-child-worker`**, also for a reviewer (its section on reviewers), a follow-up
  prompt to a fresh session, and a child you adopted.
- The brief also carries the child's own session id, the
  coordination directory outside the work tree, and the ordered hand-back files with
  the completion marker last (hand-back protocol below).
- Wording, the reviewer variant and the dispatch template are in
  `pi-web-ui-internal-api-orchestration` (§3 and §3c).

## Choose the backstop for the failure you are covering

Where the tool is actually loaded (**Pi**, or **Claude Code with the `watch-wake` mod**),
prefer the model-free `wake_deadline` over any model child that merely sleeps:

```json
{ "action":"arm", "delay_seconds":1500,
  "message":"Reconcile every owned child and watch health; expiry is not completion",
  "wait_label":"implementation-wave" }
```

Read the returned id, deadline, status and `durable` flag. `status` is read-only;
`cancel` requires the exact current id, so an old window cannot cancel its
replacement. Arm replaces the single local window. It has no model/API/process
calls while waiting, but processing its wake is an ordinary model turn.

The deadline has finite retries, visible persistence/restore errors, same-owner
restart recovery and no inherited fork authority. Channel acceptance is not
processing; a crash before accepted-state persistence may replay the wake. It
never resumes a goal or decides whether a child succeeded.

**Server-side variant.** A watch condition `{"type":"deadline","afterSeconds":N}` on the
same watch is a model-free timer inside the server: it survives restarts (overdue at
boot fires `reconciled:true`) and works with `onFire`, so it is the backstop for a
**managed** parent (no local tool needed) and an independent second clock for any
watcher (`pi-web-ui-internal-api-orchestration/references/walk-away.md`).

**Do not assume deployment.** If `wake_deadline` is absent, the loaded extension
is old, or the failure under investigation is the host/extension itself, use the next
rung of the ladder below. Source on disk does not upgrade a running process. Never
hot-reload a supervising parent (or redeploy a mod under one) just to obtain the
timer mid-window.

**`wake_deadline` has one slot per session.** Arming it replaces whatever it held — including
a long-range scheduled check (e.g. a 12-hour production-verification deadline) or the
current wave's backstop. When a scheduled check and per-window backstops coexist, give the
slot to one of them and use rung 2 (a capped background sleep) for the other; record which
is which in your checkpoint.

A deadline can also carry **a scheduled task, not just a backstop**: when a change can only
be judged on later traffic, arm it with a message that *is* the verification recipe (what to
compare, where, against which baseline).

Use one backstop per actual waiting window. Cancel only that window's owned
handle when settled; ignore delayed cancellation/old-window notifications rather
than starting another reconciliation loop. After a genuine wake, re-arm only
when dependent work remains.

## The backstop ladder: cheapest rung that fits (rungs 1–2 are model-free; rung 3 is not)

**Standing rule:** a timed, **model-free** backstop is the default for *every*
child-waiting window, not an optional extra. Arm one per window, verify it, re-arm for the
next window.

| Rung | Mechanism | Cost while waiting | Use when |
|---|---|---|---|
| **1** | `wake_deadline` (Pi, Claude mod), or the server `deadline` watch condition (managed parent), or the native scheduling tool with `TimerCondition` (Antigravity) | no model/API/process calls | The tool is loaded and healthy. |
| **2** | a bounded background shell sleep with a self-cancelling backstop (Pi `bg_run` with `backstop_s`; Claude Code capped `run_in_background` Bash sleep) | a plain process, no tokens | Rung 1 absent or suspect; also the natural form for command-shaped waits. |
| **3** | Independent-process "dead-man" **subagent** (Pi only, last resort) | one model child launch + report | Only when rungs 1 and 2 are absent, unloaded, or themselves under suspicion. |

**No rung resurrects a dead parent.** Every fallback needs a live parent delivery
channel; process-death recovery needs an external supervisor or a manual checkpoint
resume. A backstop bounds a missed wake; it does not promise delivery.

Rung 2 on Pi:

```text
bg_run: { command: "sleep 1500", label: "wait-window", backstop_s: 1800 }
```

`backstop_s` self-cancels when the task settles, so a lost completion wake still
surfaces. For the Claude Code loop template, see the Claude reference.

### Rung 3: the dead-man subagent (Pi, last resort)

A background subagent whose **entire job** is to sleep for a fixed period and report a
sentinel. It bounds a failed primary watch while the parent delivery channel stays
healthy. Use it only when the host's own timer or background-task tooling is the thing
under suspicion.

- Launch with `run_in_background: true`, a cheap worker agent (its route must be
  approved) and a prompt like: *"Pure dead-man timer. Do NOT inspect files or run any
  tool other than sleeping. Sleep in chunks of up to 600 s (bash `sleep 600`, repeated)
  until roughly <N> minutes have passed, then report exactly: `DEAD-MAN TIMER FIRED
  after ~<N> minutes`. Nothing else."*
- **Sleep budget strictly below the task ceiling.** Background subagent
  `timeout_seconds` typically caps at **3600**; 6×600 s equals the ceiling and ends
  `timed_out` instead of printing the sentinel. Keep real headroom (about 55 min of sleep
  against 3600 s, or 420 s against a 900 s ceiling for short re-arms). A timeout still
  wakes you, but that is luck of the harness: emit the sentinel on purpose. Past ~55 min,
  chain re-arms: reconcile on each fire, then arm the next.
- **Never implement a timer as an Internal API child session** (a full model session
  whose brief is "sleep N minutes", with a local `watch_wake_register` pointed at it).
  Observed: a bare-CLI parent did this, burned a real model run on an LLM-shaped timer,
  added a session to reconcile, pointed its only local watch at the timer instead of the
  work child, and still had no working primary wake. This anti-pattern applies on any
  harness.
- Neither the dead-man nor `wake_deadline` is a semantic completion oracle.

### Re-arm for every waiting window

The one documented incident was not a mechanism failure. An agent judged the backstop
"optional" for one window, the primary wake chain failed silently that same window (a
suppressed retry plus a wake that never surfaced), and it sat idle for about 3.5 hours
until the human noticed. The checkpoint: every actual waiting window has a verified,
appropriate, normally model-free backstop.

## The wake mechanisms

Pick per situation; combine when the wait matters.

### 1. Server-side `onFire` watch: the primary for a managed parent

When you dispatched children through the Pi Web UI Internal API and you are a
**managed session** the server can prompt (any runtime), register a watch on the
child with an `onFire` action targeting you. Watch the child, wake the parent.

Payload, fan-in rules, budgets, cooldowns, the two delivery traps and the evidence
ladder are owned by **`pi-web-ui-internal-api-orchestration`**
(`references/walk-away.md`); do not re-derive them here. This skill's job is the
discipline around it: *what to do so that a failed onFire chain cannot strand you*.

### 2. `watch-wake` (Pi extension, Claude Code mod): when you are a bare CLI

When the waiting agent is a **bare `pi` or `claude` CLI** the server cannot prompt,
`onFire` cannot reach you directly. Two shapes (see your harness's watch-wake docs):

- Point `watch_wake_register` at the child directly (pure-observer watch, polls the
  durable ledger, steers a busy host or starts an idle host via follow-up).
- Or the **relay pattern**: arm the server's `onFire` on the child targeting a cheap
  disposable managed session, then `watch_wake_register` on the relay. Needed when the
  children already carry pinned watches you must not clobber: registering your own
  watch on a session **replaces** the existing one and wipes its ledger.

### 3. Background completion: the in-harness wake

On Pi, a background subagent launch with `run_in_background: true` ends with its
completion or timeout delivered as a follow-up user message that triggers a turn. On
Claude Code, a background Bash task's exit does the same. **For command-shaped waits use
the shell, not a model child:** on Pi, a background-shell tool runs test suites, builds
and pure sleeps as a plain process with **no model child at all**, returns a task id
instantly and wakes you with the exit code and output tail. Pair a self-cancelling
backstop with must-not-miss completions. Reach for a background *subagent* only when the
waiter itself needs model reasoning mid-wait.

**`pi-orch wait` is a command-shaped wait.** It blocks in the server's watch long poll,
never polls and never sleeps. Run it as a background task (a background shell on Pi, a
background Bash task on Claude Code) with a result file and a `--deadline` sized to the
window. Its exit code tells you the outcome (`0` settled, `3` deadline: re-wait, `6`
never started, `16` bad target, `17` goal cleared). Do not hold your own turn open in a
foreground `pi-orch wait` for more than about ten minutes: one child blocked its turn for
35 minutes that way. For multi-hour windows, keep the watch-wake primary and the
backstop; the client does not replace them.

## Combining primary wake and an appropriate backstop

**Write each wake message for a parent that has just been compacted.** It should say
where state lives and what to do: "Read `<ops dir>/STATE-interim.md`, then reconcile ALL
lanes (b0-1, b1-1, b1-2) against receipts and coordination dirs", plus any known benign
pattern ("empty final text and activity after the end = compaction pause; do not
re-prompt"). "Child fired — reconcile it" is not enough after a compaction.

The patterns compose, and the composition is the recommended default for
waits that matter:

| Situation | Strategy |
|---|---|
| Internal API orchestration (Pi CLI/SDK) | Local `watch_wake_register` **+ model-free backstop: `wake_deadline`, or a background sleep with `backstop_s`** (dead-man subagent only as rung 3) |
| Internal API orchestration (Claude Code CLI) | `watch-wake` mod: `watch_wake_register` **+ `wake_deadline` backstop**, then end the turn (fallback: exiting background watcher + capped loop) |
| Internal API orchestration (Antigravity CLI/IDE) | Exiting background watcher (`wait-watch.sh` via `run_command`) **+ native schedule backstop (`TimerCondition`)** |
| Internal API orchestration (Managed session, any runtime) | Server-side `onFire` watch **+ a `deadline` condition on the same watch** |
| Reviewer or multi-turn child | `agent_end` watch with `"once": false`, `max_wakes` about 10 (compaction ends spend wakes), **+ deadline backstop**; see *Wake budgets and compaction* |
| Short wait completed in the current turn | No artificial idle window or timer child needed |
| Long wait without Internal API | Local deadline / schedule or independent process completion/backstop, chosen for the host and failure domain |

Why the backstop earns its keep: primary wake chains have real, observed
failure modes — `maxWakeups` budget burned by a busy parent, `cooldownSeconds`
suppressing a second firing, a relay wake that never surfaces in the CLI, a
server restart reloading watches `detached`. None of these are exotic; all of
them can strand a healthy parent. A verified backstop bounds that missed-watch
window; it does not promise recovery from parent death or an unavailable delivery
channel.

## On-wake checklist

0. **Read the clock** (`date -u`) before anything else. After an idle you do not know how
   long you slept; never stamp a checkpoint or judge a timeout from an assumed time.
1. Identify what fired: sentinel (timer expired) vs primary wake (something
   changed). Both mean "go look", not "work is done".
2. Reconcile every outstanding work item against durable evidence (receipts,
   checkpoint files, watch `wakeAttempts[]`) — not from the wake message text. A
   coalesced "N wakes arrived together" is one reconcile-all wake. A wake **held while
   you were busy** may describe an event you already handled: compare the run receipt's
   times with your checkpoint, and if nothing is new, go idle again.
3. If everything is terminal: proceed (collect, synthesise, report).
4. If dependent work is still running: preserve or re-arm the appropriate
   backstop for that window, repair only an owned broken primary, and go idle.
   If useful independent work exists, do that rather than polling for progress.
5. If the wait blew past expectation with no progress evidence: escalate to
   the operator instead of re-arming indefinitely.

### Wake budgets and compaction

Observed on long-running children (and reviewers, which run long):

- **An empty first end is not a failure.** An aborted turn with no text at about 75 %
  context is an `auto-compact-75` abort; the session **resumes by itself**. Read the run
  receipt (`outputEvidence`) and the deliverable file, wait for the resumed `agent_end`,
  and do **not** re-prompt. While it compacts, `busy` reads `false`: a prompt then
  returns `202` and later fails with a `RUNTIME_ERROR` receipt ("Cannot submit a prompt
  while compaction is in progress").
- **Each compaction's `agent_end` spends a wake.** For multi-turn, goal and reviewer
  children register `"once": false` with `max_wakes` about 10, so the real completion
  still finds budget. The server default `once: true` fires only once.
- **Refresh a budget before it runs out, not after.** Log wakes used per watch in your
  checkpoint (e.g. "ww_1 5/10"). Re-register near the cap (about 7/10) only when the
  child is idle and no wake is held, after checking its receipt; record the new id.
- **Never re-register with `replace` on a live child** to "refresh" it: a held wake is
  dropped and the ledger is wiped. After a stale notice, check the child's receipt
  first; a new watch cannot see an `agent_end` that already happened
  (`fireIfSettled:true` on re-registration covers that case).
- **A reviewer's end of turn is the wake.** It hands back by ending its turn (verdict in
  `reviews/<lane>-review.md`); the watch is `agent_end` plus a deadline, never the verdict
  file alone.

## Supervising a dispatched child — decide this before you dispatch

Waiting on a *process* and waiting on an *agent* are different problems. A
process cannot be over-supervised; an agent can, and usually is. **Everything in
this section is harness-agnostic** — the available signals differ between
runtimes, the shapes do not. Adapt them; they are patterns, not recipes.

### Ask the operator how capable the child is. Do not infer it.

You are a poor judge of which models are capable, and not through any failure of
reasoning: model names, versions and tiers move faster than training data, the
names carry marketing rather than capability signal, and your impression of a
model is often formed from material that predates it. A confident guess here is
still a guess.

So ask, in one short question, *before* you design the supervision: **is this
child capable enough to run autonomously, or do you want checkpoints?** The
operator knows their own fleet and their own bill. The answer changes the design
completely:

- **Operator confirms a highly capable child** → autonomous wake policy. Wake on
  gates and failures only, give the child broad decision authority, and expect
  it to use judgement instead of asking.
- **Unconfirmed, or a known-weak child** → tighter checkpoints are legitimate:
  smaller work units, more hand-back points, more independent verification of its
  claims.

Record which answer you were given. An already approved route/strategy can
supply this decision; do not ask again for each wave. It justifies the chosen
supervision level and stops the same question being re-litigated.

### Over-supervision is the common failure — not under-supervision

The instinct to keep checking feels like diligence. It is usually the opposite,
for a reason that is easy to miss: **the parent's context is the scarce resource,
and polling spends it permanently.** A parent kept for architecture, adjudication
or cross-cutting decisions has one window. A parent that spends that window
narrating its child's progress arrives at the decision it was kept for with
nothing left — and the delegation has bought nothing.

Three rules follow:

- **Wake on gates, not on progress.** "It finished phase 2" is not a wake.
  "It needs a decision", "it is stuck", "it is done" are.
- **Never poll in your own turn**, and never re-check something you have already
  armed a watcher for. Calling a status endpoint twice in one turn means the
  watcher is doing the wrong job — fix the watcher, do not supplement it by hand.
- **Read a heartbeat; do not generate one.** Have the child maintain a status
  artefact that you read *on wake*, rather than interrogating the child for it.

### The liveness discriminator — never trust a signal the child writes by choice

This is the part that generalises furthest, and it is worth stating as a rule:

> **An artefact the child writes by choice cannot measure whether the child is
> alive.**

It measures only whether the child is *choosing to report*, and that goes stale
for two opposite reasons you cannot tell apart from the artefact alone: the child
is legitimately idle waiting for something, or the child is dead. Both look
identical. Build a stuck-detector on it and it will fire on healthy work and stay
silent through real hangs — the exact inversion of what you wanted.

Use a signal published **independently of the child's cooperation**, and pair it
with a second signal saying whether the thing it is waiting for is still going.
Three states then separate cleanly:

| State | Independent liveness | Its outstanding work | Verdict |
|---|---|---|---|
| Working | moving | any | healthy — stay asleep |
| Legitimate wait | frozen | still running | healthy — stay asleep |
| **Dead wait** | **frozen** | **all terminal** | **wake me** |

The middle row is what naive detectors get wrong. The bottom row is the failure
genuinely worth catching: the child went idle expecting a wake that never came,
and will sit there until a human notices.

Two more discriminations the table implies:

- **A child waiting on its own background task looks like a silent end.** A Pi child
  that launched a background job and ended its turn to await that job's completion wake is
  on a legitimate path, not handing back. Check for its running background job before
  treating the end as a hand-back or a stall. `orchestrated-child-worker` now tells children not to
  do this, and to start any early stop with `NOT FINISHED:`; treat such a message as
  progress, not a hand-back. (22% of audited child sessions ended a turn this way.)
- **Pre-commit the stall response before you idle.** Write into your checkpoint what you
  will do and when: "if no further turn by 21:25 while its soak has finished, prompt it
  to finish (`follow_up`)"; "if the reviewer compacts again without its file, replace it
  with two reviewers on split scope". A decision made before the wake is not bent by the
  wake's framing.

The independent-signal selection table, the Internal API evidence calls, and
the two practical rules (consecutive observations; verify your own parsing)
are in `references/supervision-and-stuck-detectors.md` — read it before you
build any detector.

### Before building any of this, check whether the platform already evaluates it

A hand-rolled liveness heuristic should be your **last** resort, not your first.
Most orchestration platforms already evaluate conditions like "this child's turn
ended" correctly, durably, and with an audit trail — and their evaluation is
better than yours because it sits inside the runtime rather than inferring from
outside it.

The trap is reading "I cannot receive a push wake" as "this system is closed to
me". Those are different claims. Delivery and evaluation are separable: even
when nothing can push a wake into your process, you can usually **register an
observer and read it yourself**, then supply only the delivery your harness
needs — which for Claude Code is the `watch-wake` mod, or the exiting
background watcher where mods are unavailable (`references/claude-code-watch-wake-and-background-watcher.md`).

Concretely, on the Pi Web UI Internal API: a bare Claude CLI cannot be an
`onFire` target, but it can `POST /sessions/:id/watch` with **no** `onFire` (a
pure observer) and poll `GET /sessions/:id/watch`. That yields the server's own
`agent_end` evaluation and its durable ledger, with no heuristic in the path.

This is not hypothetical tidiness: orchestrators have read "bare Claude CLI has
no path", concluded the watch system was unavailable, and written several
incorrect stuck-detectors reconstructing liveness from `lastActivity`, run
status and a status file — while the observer watch existed the whole time.
Ask "what does the platform already know?" before writing a detector.

### The hand-back protocol — impose it, on any repo, any harness

A watcher cannot see a condition inside the child's head — only observable
state. So **convert the child's questions into observable state in the
dispatch brief**. Pick a coordination directory **outside** the work tree and
outside anything measured, hash-pinned or committed; the child writes an
**ordered** file there — `01-questions.md`, `02-batch-ready.md`, `NN-blocked.md`,
`NN-complete.md` — whenever it needs you, **and then ends its turn** (never
waits, polls, or holds the turn open). **A new file appearing is the wake**;
ordered names make re-arming trivial. Keep a separate status/heartbeat
artefact that is explicitly *not* a wake trigger — read it on wake as context,
never as liveness — and answer in a matching file the child reads when
resumed. Tell the child all of this explicitly: a child that has not been told
will hold its turn open waiting for you or end it silently, and both strand
the run.

**Mandate the child skill** (*the child contract*, above): the brief tells the
child to follow `orchestrated-child-worker`, which makes it announce its task and owned
paths in the coordination directory at boot, leave a closing note, and end its turn to
hand back.

**But do not make the hand-back file your completion signal.** It is an
artefact the child writes *by choice* — the exact category the liveness rule
above tells you never to trust. That is fine for **gates** (a child that does
not ask has nothing you need to answer), wrong for **completion**, where the
missing file is the whole event. Watch completion on a signal the child cannot
withhold: a commit landing, the run going terminal, the platform's own
end-of-turn condition. The full protocol, the measured failure shape and the
observed incident behind this rule are in
`references/supervision-and-stuck-detectors.md`.

### Calibrate what the child may ask about

Over-supervision has a mirror image: a child that asks about everything. Set the
bar in the dispatch brief, and set it by **size of question**, not frequency.
Keep it genuinely low for:

- a contradiction or impossibility in its instructions;
- an authority or scope boundary it cannot cross;
- anything irreversible, or that touches the operator's real data;
- a premise that turns out to be false — including a stop rule firing.

Everything below that line is the child's to decide, record and move on with. A
round trip on an implementation detail costs both sides more than it buys, and a
capable child — per the first rule in this section — does not need permission for
engineering judgement.

### Adopted children are supervision targets too

A child linked into the tree **after the fact** (Internal API adoption, contract 1.40.0 —
`pi-web-ui-internal-api-orchestration` §8 and `references/adoption.md`) is supervised like
any other child: watch the child, wake the parent, backstop the window. Adoption's own
gate still applies first: if the session was used in a CLI tool, the operator must confirm
they have exited it before you adopt or dispatch into it.

### Goal-driven children and goal-carrying parents

A child dispatched with a **goal** is a different supervision target: watch
terminal `goal_end` plus a state-filtered question/pause, **not** per-run
`agent_end` churn — a start receipt is not completion, and an unfiltered
one-shot watcher can be consumed too early by an old goal's clear event.
A **goal-carrying Pi parent** must park cleanly before idling: `goal` pause
with reason `"supervising <child>"` — never via the question exit
(a needs-user-input marker), which sets `pendingQuestion` so the wake itself
auto-resumes the goal — and resume only when fully settled. Budgets are real
outcomes (exhausted auto-continue or turn budget ends as
`goal_end {failed, budget}` — re-plan, don't poll through).

Two goal-child edges observed in practice (detail in
`pi-web-ui-internal-api-orchestration/references/goals.md`):

- **A `failed` goal_end can be premature.** The Pi goal engine failed a goal
  ("run ended in under 15000ms") while the child kept working, and its later
  completion produced no second `goal_end`. On such a wake, read `busy`, commits and
  the hand-back file. Let the window's backstop catch a quiet finish.
- **A deploy is a goal-child event.** A child cut off by a restart
  fires its goal watch with `interruptedByRestart` (contract ≥ 1.52.0). On older
  servers it dies silently, so pause goal children before such a restart. Either
  way, resume or re-dispatch after reconciling.

The full design consequences, per-runtime pause semantics and the observed
failure shapes are in `references/supervision-and-stuck-detectors.md`
(goal cases).

## Related

- **`pi-web-ui-internal-api-orchestration`** — owns the Internal API side:
  watch/onFire mechanics, fan-in, retention, evidence. Read it before your
  first detached dispatch; use this skill for the idle-safety discipline on
  top.
- **`orchestrated-child-worker`** — the skill every dispatched child is told to follow.
- **`secret-scanning`** — scan artefacts and repositories for credentials before
  publishing them.
- Your harness's watch-wake extension/mod docs — the bare-CLI wake primitives
  (`watch_wake_register/list/cancel`, `wake_deadline`), baselining, lifecycle edges.
- Your harness's background-task docs — background task launch, wake delivery,
  `task_list/output/stop`, the timeout ceiling.
- Origin: the pre-idle checklist and mandatory re-arm rule come from a live
  post-mortem (an un-backstopped 3.5 h stall).
- Origin: the supervision section comes from live incidents where orchestrators used
  status files the child wrote by choice as liveness proxies, causing false positives
  while children were actively running tool calls. Independent platform signals prevent
  this.

The reference tiers and their mandatory/situational split are described in
**What to read, in three tiers** at the top of this file.
