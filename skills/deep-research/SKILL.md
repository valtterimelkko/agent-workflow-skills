---
name: deep-research
description: "COMPREHENSIVE top-tier research for topics where breadth, source quality, and auditable methodology matter. Use when the user needs 40+ sources, publication-grade synthesis, due diligence, policy or market analysis, or any high-stakes research where missing key dimensions would materially weaken the answer. This skill is especially valuable when the prompt has multiple dimensions that must all be covered faithfully. NOT for quick or medium-depth briefs; prefer gpt-research or native web_search/web_fetch for those." 
---

# Deep Research Skill

A comprehensive workflow for conducting **broad, source-rich, auditable research** using iterative waves of subagents.

**Time**: ~6–10 minutes  
**Sources**: 40–100+  
**Best for**: academic rigor, due diligence, comparative analysis, high-stakes synthesis

The strength of this skill is **breadth with control**: it covers many dimensions without letting any single subagent become the whole research system.

---

## Core Operating Model

The main agent is the **research conductor**.

Subagents are used for:
- scouting source landscapes
- analysing curated source batches
- resolving contradictions
- checking synthesis quality

The main agent is responsible for:
- defining dimensions
- maintaining the research manifest
- maintaining the blocked-source registry
- curating which sources get promoted to deeper analysis
- deciding whether the research is sufficient
- consulting the user on fallback options when high-value blocked sources remain

### Core Principles

1. **Breadth is preserved at the workflow level, not overloaded into each subagent.**
2. **Subagents must return useful findings in their response text first.** File writes are secondary.
3. **Subagents must not silently switch to non-default fallback workflows** such as browser automation. If blocked, they must report and move on.
4. **Forward progress is preferred unless a critical gap is identified.**
5. **Blocked-source review happens at the end of the standard workflow**, before considering fallback workflows.
6. **Fallback workflows require explicit user consultation.**

---

## Research Tier Positioning

Use this skill as the **heaviest general-purpose research tier**:

1. **Native `web_search` / `web_fetch`** — one-off current facts, a single page, or a few URLs
2. **`gpt-research`** — quick / medium-depth synthesis across roughly 10-20 sources
3. **`deep-research` (this skill)** — 40+ sources, explicit methodology, high-stakes synthesis
4. **Specialised recency skills** such as `last30days` — when the main need is recent discourse across social/web platforms rather than broad general-web synthesis

If the user simply says “research this”, reserve this skill for tasks where the consequence of missing a dimension is materially important.

## When to Use This Skill vs Fast Research

### Use deep-research when:
- the user needs **40+ sources**
- the topic has **multiple dimensions that must all be covered**
- source quality and traceability matter
- the work is for publication, due diligence, or high-stakes decision-making
- the user explicitly wants a transparent, auditable methodology

### Use fast research instead when:
- the user wants a quick overview
- 10–20 sources are enough
- the topic is exploratory rather than high-stakes
- speed matters more than exhaustive coverage

---

## The Workflow

## Phase 0 — Preflight and Planning

### Goal
Validate that the normal research path is viable, then define the scope.

### Main agent actions
1. Analyse the user’s actual decision or question.
2. Break the topic into 4–8 research dimensions.
3. Identify the **key questions**, likely **source classes**, and any obvious **edge cases / blind spots**.
4. Draft **5–10 initial search queries or search angles** spanning the most important dimensions.
5. Run a **small preflight check** using the standard acquisition path to see whether search/fetch is broadly working.
6. Create a **Research Manifest** in your own notes / working state.

### Research Manifest (minimum fields)
Track at least:
- dimension name
- scout assigned
- scout result status
- analyst assigned
- analyst result status
- blocked-source count for the dimension
- whether the dimension is adequately covered

Do **not** turn the manifest into bureaucratic overhead. It is a lightweight control table.

---

## Phase 1 — Scout Wave (broad, lightweight)

### Goal
Cast a wide net cheaply and safely.

### Rule
**Scouts are discovery agents, not full analysts.** They should identify promising sources and report them compactly.

### Spawn
Launch 3–6 parallel scout agents, each covering a distinct dimension or source class.

Examples:
- official / regulatory
- academic / technical
- industry / practitioner
- news / current developments
- community / user sentiment
- regional / local angle

### Scout task shape
Each scout should:
- identify **6–10 promising sources**
- give a **1-line relevance note** for each
- estimate credibility at a high level
- capture **publication date / recency** when visible
- suggest **follow-up queries** if coverage looks thin or skewed
- report blocked URLs if encountered
- avoid deep extraction
- avoid contradiction resolution unless extremely obvious

### Mandatory scout instructions
Use wording along these lines:

```text
Use your default acquisition path only.
Do NOT invoke browser automation, playwright, or other non-default fallback workflows.
Browser automation is NOT a bot-protection bypass strategy in this workflow.
If a source is blocked by Cloudflare, anti-bot protection, rate limits, login walls, paywalls, or fetch failures, record the exact URL, barrier type, source class, and failure reason, then continue.
Your primary deliverable is this response text. File writes are optional secondary artifacts.
At the end, explicitly report:
- created_files: [...]
- modified_files: [...]
- blocked_urls: [{url, barrier_type, reason, source_class}]
- unblocked_sources: [{title, url, publication_date_or_recency, relevance_note, credibility_estimate}]
- follow_up_queries: [...]
If no files were created, say so explicitly.
```

### Preferred scout output format

```markdown
## Scout Summary
Dimension: [name]
Status: adequate | thin | blocked-heavy

## Candidate Sources
1. [Title] — URL
   - Relevance: ...
   - Credibility: High/Medium/Low
   - Date/Recency: ...

## Follow-up Queries
- ...

## Blocked URLs
- URL — barrier type — reason

## Files
- created_files: [...]
- modified_files: [...]
```

### Main agent after scouts
1. Read all scout outputs.
2. Deduplicate sources.
3. Update the manifest.
4. Build a **Blocked Source Registry**.
5. Promote the strongest sources into curated analyst batches.

---

## Phase 2 — Analyst Wave (narrower, heavier)

### Goal
Do the deep reading and extraction on curated source batches.

### Rule
**Analysts receive curated URLs.** They should not wander broadly. However, if a curated batch is missing a necessary primary source, a key dissenting source, or another narrowly defined source needed to evaluate a material claim, the analyst may add **up to 1–2 tightly scoped supplementary sources** and must label them clearly as supplementary recovery sources.

### Batch size
Give each analyst **~4–7 URLs** or a similarly narrow, clearly bounded source batch.

### Analyst responsibilities
Each analyst should:
- extract key findings
- identify areas of consensus and disagreement
- note methodological caveats
- flag weak or suspicious sources
- apply a **compact source-verification checklist** to material sources: author/organisation, date/recency, source type, primary-vs-secondary, methodology present/absent when relevant, obvious bias/conflict flags, and whether the claim was cross-checked
- report blocked URLs if any curated sources fail
- propose **follow-up queries** if a material gap remains
- return structured markdown in response text first

### Mandatory analyst instructions
Use wording along these lines:

```text
Use your default acquisition path only.
Do NOT invoke browser automation, playwright, or other non-default fallback workflows.
Browser automation is NOT a bot-protection bypass strategy in this workflow.
If any curated URL is blocked or fails to load, report it exactly and continue with the remaining sources.
Do not broaden scope unless explicitly instructed, except for at most 1–2 tightly scoped supplementary recovery sources when needed for a material claim.
Your primary deliverable is this response text. File writes are optional secondary artifacts.
At the end, explicitly report:
- created_files: [...]
- modified_files: [...]
- blocked_urls: [{url, barrier_type, reason, source_class, estimated_importance}]
- supplementary_sources: [{title, url, why_needed}]
- follow_up_queries: [...]
```

### Preferred analyst output format

```markdown
## Analyst Findings
Batch: [name]
Coverage: strong | moderate | weak

## Key Findings
- ...

## Important Claims and Support
- Claim: ...
  - Sources: ...
  - Cross-check status: ...

## Source Verification Notes
- Source: ...
  - Author/Organisation: ...
  - Date/Recency: ...
  - Type: primary / secondary / commentary
  - Methodology present?: yes/no/not applicable
  - Bias/conflict notes: ...

## Caveats / Contradictions
- ...

## Supplementary Recovery Sources
- ...

## Follow-up Queries
- ...

## Blocked URLs
- URL — barrier type — reason — estimated importance

## Files
- created_files: [...]
- modified_files: [...]
```

---

## Phase 3 — Synthesis and Gap Resolution

### Goal
Turn analysed batches into a coherent answer.

### Main agent actions
1. Group findings into themes.
2. Identify what is already adequately covered.
3. Identify only the most important remaining gaps.
4. If substantive disagreement appears on a material claim, spawn a **targeted contradiction-resolution deep dive** before treating that claim as high-confidence.
5. Spawn other targeted deep-dive agents only where necessary.

### Use additional deep-dive agents for:
- contradiction resolution
- missing official / survey evidence
- missing primary / seminal / uniquely probative evidence
- regional gaps
- terminology or methodology clarification

### Do not spawn another broad scout wave unless:
- a major dimension is still under-covered, or
- the user explicitly asks for more breadth

---

## Phase 4 — QA and Sufficiency Check

### Goal
Decide whether the research is strong enough to stand on its own.

### Main agent checks
- Are all key dimensions covered?
- Are the strongest claims supported by credible sources?
- Are the blocked sources material to the conclusions?
- Is the evidence set broad enough to answer the original prompt faithfully?

### QA micro-checklist
Before finalising, explicitly check:
- Are any **material claims** unsupported, weakly supported, or supported only by low-credibility sources?
- Do the **citations actually support the claims** they are attached to?
- Were **substantive contradictions** either resolved through targeted follow-up or clearly carried forward as uncertainty/contestation?
- Are any high-confidence conclusions relying on evidence that should instead be framed as tentative?

### Prefer forward progress
Do not keep digging forever. Move toward report assembly unless a **critical gap** remains.

---

## Phase 5 — Blocked Source Review (end of normal workflow)

This happens **after** the standard workflow is complete, not mid-workflow.

### Goal
Assess whether blocked/failed sources materially weaken the result.

### Maintain a Blocked Source Registry
Track, at minimum:
- URL
- source class (official / major survey / academic / technical doc / practitioner / media / community / aggregator / other)
- dimension
- barrier type / failure reason
- evidentiary role (official, major survey, primary study, seminal paper, benchmark doc, canonical technical documentation, practitioner evidence, commentary, other)
- whether an equivalent unblocked source was found
- replaceability (high / medium / low)
- estimated importance

### Importance rubric
Class blocked sources as:
- **Critical** — sources whose absence materially weakens the conclusion because they are official, major-survey, primary, seminal, uniquely probative, or otherwise not adequately replaceable
- **Important** — strong sources that materially improve confidence or breadth, but are replaceable with some loss of fidelity
- **Peripheral** — useful but non-essential

### Default threshold for stronger fallback recommendations
Recommend stronger fallback options primarily when blocked sources include:
- **official sources**, and/or
- **major survey sources**
that are not adequately replaced by unblocked alternatives

Also consider stronger fallback recommendations when blocked sources are:
- **primary or seminal sources** central to a key claim
- **canonical technical documentation / benchmark pages** needed to verify an important claim
- **uniquely relevant regional or practitioner evidence** with no good unblocked substitute

### End-of-workflow blocked-source analysis
Report to the user:
- number of blocked URLs
- blocked-source count by source class
- which dimensions were affected
- whether the blocked sources are critical, important, or peripheral
- whether the current research is still sufficient without them
- which blocked sources are likely replaced well vs poorly replaced

Do **not** dump a giant raw URL list into the final user-facing summary unless asked.

---

## Fallback Workflows (only after standard workflow ends)

Fallback workflows are considered **only at the end** of the normal deep-research workflow.

## Fallback A — Camofox targeted recovery (free, local, preferred first)

Recommend **`camofox`** first when blocked sources remain important and the problem looks like a browser-style anti-bot / JS-rendering barrier, especially when:
- a **small number of high-value URLs** are blocked
- the blocked pages are public but hidden behind Cloudflare, challenge pages, blank JS rendering, or similar anti-bot friction
- recovering those pages would materially improve confidence in one or more important claims

### Camofox rules in this workflow
- Use it only for **targeted recovery of specific blocked URLs**, not as a silent background path for every scout or analyst
- The **main agent** should decide which blocked URLs are worth recovery after blocked-source analysis
- Recover the smallest useful set first: official pages, major surveys, canonical documentation, or other poorly replaceable sources
- If Camofox fails, keep the evidence gap visible and only then consider higher-friction fallbacks

## Fallback B — NotebookLM (user-participatory broad recovery)

Recommend NotebookLM when blocked sources remain important and the recovery problem is broad rather than a short list of individual pages, especially when:
- the blocked material spans a **broad topic**
- several blocked URLs affect the same dimension or subtopic
- the user is comfortable doing a login step and wants a lower-barrier recovery path

NotebookLM is usually the next fallback when the blocked problem is broad or when multiple important blocked URLs can be recovered through a user-participatory notebook workflow.

### Two NotebookLM patterns

#### 1. Broad-topic recovery
Use NotebookLM to perform deep research on:
- the same topic, or
- a narrower blocked subtopic

This is appropriate when blocked coverage affects a broad slice of the research.

#### 2. Narrow-source recovery
If only a modest number of blocked URLs matter, recommend adding those URLs directly as notebook sources, then querying the notebook.

### Important NotebookLM notes
- Requires user login / session participation
- Treat NotebookLM as a **recommended fallback**, not an autonomous silent fallback
- It is best used as a **recovery and synthesis aid**, not as a perfect substitute for direct fetch
- For technical details and commands, **read the `notebooklm` skill**

## Fallback C — Residential Proxy (higher barrier; explicit permission only)

Recommend residential proxy only when:
- blocked sources are **high-value**, especially official or major-survey sources
- or the blocked sources are **critical primary / seminal / uniquely probative sources** that are poorly replaceable
- the gaps materially weaken the research
- the user explicitly authorizes the proxy path

### Residential proxy policy
- **Never use it without explicit user permission**
- Estimate **data volume bands**, not exact cost:
  - small batch
  - medium batch
  - large batch
- Explain why the blocked sources are important enough to justify it
- For technical details, **read the `residential-proxy` skill**

---

## Retry Policy

### Default bias
Prefer **balanced forward progress**:
- move on unless a critical gap is identified
- do not let one blocked source stall the whole workflow

### Recommended retry behavior
- **Blocked / anti-bot / rate-limit / login-wall / paywall failure**: do not retry with browser automation, Playwright, or other non-default acquisition tools; log the barrier type and continue
- **Formatting / malformed output failure**: 1 retry with simpler output requirements
- **Thin scout results**: 1 narrower retry if the dimension still matters
- **Repeated failure**: mark the dimension as thin or blocked-heavy and proceed

---

## Final Report Requirements

The final report should include all of the following:

1. **Blocked-source statistics**
2. **Blocked-source importance analysis**
3. **Confidence statement**
4. **Fallback recommendations** (if relevant)
5. **Methodology limitations stated up front**, not buried only in an appendix
6. **References section** for sources actually used in the report
7. **Source inventory appendix or machine-readable source list** covering the consulted evidence base

Major claims in the final report should be traceable to cited sources. Do not rely on uncited synthesis for material conclusions.

### Recommended methodology summary table
Include a concise methodology / limitations table in the final report, for example:

| Item | Status |
|------|--------|
| Dimensions covered | X / Y |
| Sources used | N |
| Blocked URLs | N |
| Critical blocked sources | N |
| Research confidence | High / Medium / Low |
| Fallback recommended | None / Camofox / NotebookLM / Residential proxy |

---

## Common Pitfalls to Avoid

1. **Overloading scouts** with deep extraction and formatting duties
2. **Losing findings because file writes failed**
3. **Silent browser/playwright fallback** that creates hidden artifacts without helping
4. **Treating all blocked URLs as equally important**
5. **Raw-appending research files into the final report** instead of synthesizing them cleanly
6. **Letting blocked-source analysis derail the standard workflow too early**
7. **Burying major methodology limitations in appendices only**
8. **Letting curated analysts become broad scouts again** instead of using only narrow recovery where truly needed
9. **Dropping source traceability** because the prose sounds confident

---

## Summary

This skill wins by keeping the **overall workflow broad** while making each subagent more focused and auditable.

Use broad scouting first, promote the best sources into deeper analysis, keep a clear blocked-source registry, and only consider fallback workflows after the normal research pass is complete.

**Default stance:** keep moving, surface blocked-source significance clearly, try targeted `camofox` recovery before paid proxy escalation, and involve the user before using higher-friction fallback paths.
