<!-- Loaded from SKILL.md stubs (orchestration loop §1–§9). Open when designing a fan-out or batch job, when reporting to the operator (spoken or written), or before writing an orchestration report. -->

# Orchestration patterns, voice, and reporting

## Patterns

**Best-of-N comparison** — one child per runtime/model candidate, same prompt,
monitor, collect each `/transcript`, then either rank them or synthesize the
strongest parts deliberately. Don't pick one blindly.

**Task decomposition** — give each child a distinct responsibility (planner,
implementer, critic, synthesizer) and route each according to the recorded route
for that kind of work. When the responsibilities are *dependent phases rather
than parallel roles*, that is a multi-wave programme — plan it with
`multi-phase.md` instead of a one-wave fan-out.

**Reviewer fan-out** — one draft, several parallel critiques (technical, clarity,
edge-case/risk), merged by the parent.

**Variation then synthesis** — several children produce variants; either
synthesize as the parent or `/transfer` the strongest into a final session.

**Batch processing** — many homogeneous items (scoring, classification,
extraction, judging) through **one durable worker**, or a very small fixed
number. Not one session per item. Dispatch detached, have the child write
**per-item atomic checkpoints to files** and return only a compact final summary,
then validate deterministically parent-side **from those files** — row counts,
schema conformance, manifest hashes, metric roll-up — rather than from the
response body. Retry only the items with no valid artefact; never blindly
re-dispatch work already checkpointed.

The two failure shapes here are worth naming, because they look like diligence.
**One session per item** multiplies session creation and cleanup, route
read-backs, large-output formatting risk, empty-response risk and spurious
blocker alerts, while buying no better judgement. **One large structured document
squeezed back through a single synchronous response** is the other half of the
same mistake. If your design turns N items into N sessions, change the design
rather than hardening it — the fan-out patterns above earn their session count by
using *different* models or *different* roles, which batch work does not.

## Speaking to the operator by voice

Voice is an interaction mode, not a runtime — same API, same rules. What changes
is the reporting: announce the dispatch compactly before acting (for example,
"starting two child sessions on the selected routes"), make the target, runtime,
model, session count, and likely side effects clear up front, then
report evidence rather than claiming success from an HTTP acknowledgement. Keep
spoken updates short and concrete, and say plainly when something is still
running and what you'll check next.

## Reporting an orchestration run

```markdown
# Orchestration Report
## Goal
## Route plan (runtime + provider + exact selector + level/effort + role, per child)
## Child sessions created (sessionId, runId, lease)
## Monitoring approach
## Results by child
## Synthesis / final output
## Decisions requiring input (numbered; options, recommendation, and why each matters — kept apart from what you decided autonomously)
## Caveats, failures, remaining uncertainty
## Usage summary
```
