---
name: thematic-analysis
description: Code and interpret qualitative data from files to generate themes, identify patterns, and explore coverage gaps. Use when analyzing interview transcripts, survey responses, documents, or any text data to identify codes, develop themes, assess analytical coverage, and determine what areas have been effectively explored versus potentially avoided. Supports both reflexive thematic analysis (Braun & Clarke) and codebook approaches for research rigor. Optimized for chat-based collaborative workflows.
---

# Thematic Analysis Skill

Conduct rigorous thematic analysis on qualitative data from files. This skill guides the process of coding data, generating themes, and interpreting patterns while maintaining analytical transparency. Designed for conversational collaboration through chat.

## When to Use This Skill

- Analyzing interview transcripts or focus group data
- Coding survey open-ended responses
- Examining documents, articles, or text corpora
- Identifying patterns across multiple data sources
- Assessing what themes are well-covered vs. under-explored
- Developing codebooks for team-based analysis

---

## Chat-Based Collaborative Workflow

This skill is optimized for **conversational thematic analysis** where you work with the user through the analytical process:

```
┌─────────────────────────────────────────────────────────────────┐
│  PHASE 1: Familiarization    ─────► Agent performs              │
│  PHASE 2: Initial Coding     ─────► Agent performs              │
│                                                                 │
│  [PAUSE: Present codes to user, get feedback]                   │
│                                                                 │
│  PHASE 3: Searching Themes   ─────► Conversational (with user)  │
│  PHASE 4: Reviewing Themes   ─────► Conversational (with user)  │
│  PHASE 5: Defining Themes    ─────► Conversational (with user)  │
│                                                                 │
│  [PAUSE: Get user permission]                                   │
│                                                                 │
│  PHASE 6: Producing Report   ─────► Agent performs (autonomous) │
└─────────────────────────────────────────────────────────────────┘
```

### How the Workflow Works

1. **Agent Autonomous Phases (1-2):** The agent reads the data, develops familiarity, generates initial codes, and presents them with emoji coding prefixes
2. **Conversational Phases (3-5):** The agent and user discuss, refine, and develop themes together through dialogue
3. **Final Autonomous Phase (6):** After user grants permission, the agent produces the final report independently

---

## Quick Start

### Step 1: Receive Data Files

When the user provides data files (transcripts, documents, etc.), confirm receipt and begin the autonomous phases.

### Step 2: Execute Phases 1-2 Autonomously

Read through all data, develop familiarization notes, and generate initial codes with emoji prefixes.

### Step 3: Present Coded Data to User

Share the coded excerpts using the emoji coding system (see below). Ask for feedback before proceeding.

### Step 4: Guide Conversational Phases 3-5

Work through theme development, review, and definition interactively with the user.

### Step 5: Request Permission for Phase 6

Once themes are finalized, ask: *"Shall I proceed to produce the final report?"* Then generate autonomously.

---

## Emoji Coding System for Chat

Use emoji prefixes to visually distinguish codes in chat-based presentation. This makes patterns immediately visible. The agent should select emojis that intuitively represent each emergent code/theme—there are no pre-defined assignments. Let the data guide the choice.

### ⚠️ CRITICAL: All Examples Are Illustrative Only

**ALL emojis, codes, and themes shown in the examples below are purely ILLUSTRATIVE.** They are NOT templates to follow or default codes to use.

**DO NOT:**
- Use the example codes (e.g., EMAIL-OVERLOAD, EMOTIONAL-DISTRESS, WORK-BOUNDARIES) as your actual codes
- Assume themes about "work-life balance," "stress," or "adaptation" will be in the data
- Copy the example emojis (📧, 🌊, 🏠, 🔄, etc.) without considering what fits YOUR data
- Pre-categorize data into thematic buckets based on these examples

**DO:**
- Read the data with fresh eyes—no preconceptions about what themes will emerge
- Create codes and choose emojis based ONLY on what you actually find in the data
- Let the participants' words and concepts drive your coding entirely
- Develop themes organically from the patterns that arise in YOUR dataset

> The examples below show the *format* of how to present coded data. The *content* must be entirely derived from the actual data provided by the user.

### Code Prefix Format

```
[EMOJI] CODE_NAME: "Coded text excerpt from the data"
```

### Emoji Selection Guidelines

The agent should choose emojis based on the emergent content of each code:

- **Be intuitive:** Select emojis that naturally evoke the code's meaning (e.g., 🏠 for home-related codes, ⚡ for energy/stress, 🔄 for change/processes)
- **Be consistent:** Use the same emoji for the same code throughout the analysis
- **Stay simple:** Prefer clear, widely-understood emojis over obscure ones
- **Limit variety:** Aim for 6-10 distinct emojis across all codes for visual scannability
- **Avoid confusion:** Don't use similar emojis for different codes (e.g., 😊 and 🙂)

### Example Coded Excerpt

> **Participant P3:** "I just feel completely overwhelmed by the constant stream of messages. It's like I'm drowning and can't come up for air."
>
> **Agent Coding:**
> - 📧 EMAIL-OVERLOAD: "constant stream of messages"
> - 🌊 EMOTIONAL-DISTRESS: "I'm drowning and can't come up for air"
> - 😵 LOSS-OF-CONTROL: "completely overwhelmed"

### Code Key Presentation

Always present a code key at the start of coded data, showing the emoji chosen for each code:

```
📋 CODE KEY FOR THIS SESSION:
📧 EMAIL-OVERLOAD  |  🌊 EMOTIONAL-DISTRESS  |  😵 LOSS-OF-CONTROL
🏠 HOME-BOUNDARY   |  ⚡ ENERGY-DRAIN        |  🔄 ADAPTATION
```

> 🔴 **Remember:** These are EXAMPLE codes only. Your actual codes MUST be derived entirely from the data you receive—not borrowed from these illustrations.

---

## The Six Phases of Thematic Analysis

### Phase 1: Familiarization with Data (Agent Autonomous)

**Goal:** Develop deep, intimate knowledge of your dataset.

**Actions:**
1. Read through all data multiple times
2. Note tone, pauses, emotion where evident in transcripts
3. Write 2-3 sentence summaries per document
4. Create initial memos with observations, questions, and patterns
5. Document assumptions and biases before coding

**Key Questions:**
- What initial patterns do I notice?
- What surprises me?
- What is my relationship to this topic?
- What do I expect to find?

**Output:** Familiarization notes, initial memos, researcher positionality statement

**To User:** Present a brief summary: *"I've reviewed all [N] transcripts. Initial observations: [2-3 patterns]. Ready to proceed with coding."*

---

### Phase 2: Generating Initial Codes (Agent Autonomous)

**Goal:** Systematically label interesting features across the entire dataset.

**Coding Principles:**
- **Be systematic:** Code entire dataset, not just vivid examples
- **Stay close to data:** Use participants' own words (in vivo) when powerful
- **Start broad:** Aim for 50-80 initial codes (not 300+)
- **Maintain inclusivity:** Same segment can have multiple codes

**Types of Codes:**

| Type | Description | Example* |
|------|-------------|----------|
| **Descriptive** | Labels surface content | 📊 [e.g., DATA-TYPE] |
| **Interpretive** | Captures underlying meaning | 🌀 [e.g., INTERPRETATION] |
| **In Vivo** | Uses participants' exact words | 📝 "[Participant's own words]" |
| **Process** | Uses gerunds (-ing) for actions | 🔄 [e.g., DOING-ACTION] |

*Examples show format only—use codes derived from YOUR data, not these illustrations.

**Chat Presentation Format:**

Present coded excerpts to the user with:
1. A code key (emoji legend)
2. Representative coded excerpts (5-10 per code)
3. Code frequency summary
4. Invitation for user feedback

**Example Presentation:**

> 🔴 **The codes and emojis below are EXAMPLE ILLUSTRATIONS only.** Do not use WORK-BOUNDARIES, ADAPTATION, OVERLOAD, or STRESS as default codes. Generate your own codes and emojis based solely on the actual data.

```
📋 CODE KEY:
🏠 WORK-BOUNDARIES | 🔄 ADAPTATION | 📡 OVERLOAD | 😵 STRESS

═══════════════════════════════════════════════════════════════

🏠 WORK-BOUNDARIES (appears 12 times across 5 participants)

P2: "I had to learn to turn off notifications after 6pm." 📵 SETTING-LIMITS

P4: "My family knows if my door is closed, I'm working." 🚪 PHYSICAL-BOUNDARIES

═══════════════════════════════════════════════════════════════

🔄 ADAPTATION (appears 8 times across 4 participants)
...

═══════════════════════════════════════════════════════════════

📡 OVERLOAD (appears 15 times across 6 participants)
...

[Continue for all codes...]

───────────────────────────────────────────────────────────────
🤔 I've identified 8 codes across the dataset. 
   Do these capture what you're seeing? Any codes to merge, 
   split, or add before we move to theme development?
```

**Best Practices:**
- Over-code rather than under-code initially
- Review codes every 2-3 documents for consistency
- Write memos explaining why each code was created
- Balance granularity with pattern recognition

**Common Pitfall:** Creating too many tiny codes—group similar codes early

---

### Phase 3: Searching for Themes (Conversational)

**Goal:** Group codes into potential themes that tell a story — **work through this conversationally with the user.**

**Understanding Themes vs. Codes:**

| Codes | Themes |
|-------|--------|
| Building blocks (bricks) | Central organizing concepts (walls) |
| Micro-level, specific | Macro-level, interpretive |
| Many (50-80) | Few (4-8 main themes) |
| Describe | Interpret |

**Conversational Process:**

> 🔴 **The theme example below is ILLUSTRATIVE.** "Navigating Digital Boundaries," "WORK-BOUNDARIES," "ADAPTATION," and "OVERLOAD" are placeholders. Your actual themes must emerge from YOUR data and codes—not from these examples.

**Agent opens:**
```
Let's develop themes together. Looking at the codes, I see potential 
connections. Here's one grouping I'm considering:

┌────────────────────────────────────────────────────────┐
│  THEME CANDIDATE: "[Theme Name Derived from Your Data]" │
├────────────────────────────────────────────────────────┤
│  [EMOJI] CODE-1-FROM-YOUR-DATA                         │
│  [EMOJI] CODE-2-FROM-YOUR-DATA                         │
│  [EMOJI] CODE-3-FROM-YOUR-DATA                         │
├────────────────────────────────────────────────────────┤
│  Central Concept: [Interpretive concept based on the   │
│  patterns in your specific dataset]                    │
└────────────────────────────────────────────────────────┘

Does this grouping make sense to you? Do you see alternative 
ways to group these codes?
```

**Agent facilitates dialogue:**
- Present 1-2 candidate theme groupings at a time
- Ask for user input: *"What connections do you see?"*
- Discuss alternative groupings
- Refine based on user feedback

**What Makes a Good Theme:**
- Has a **central organizing concept** (not just a topic summary)
- Tells a clear story about a pattern
- Goes beyond description to offer insight
- Answers "So what?"
- Is backed by evidence across the dataset

**Theme Evolution Example***

| Weak (Topic Summary) | Strong (Interpretive Theme) |
|---------------------|----------------------------|
| "Technology problems" | "Navigating system fractures" |
| "Communication issues" | "Emotional disconnection in virtual encounters" |
| "Work stress" | "The invisible labor of digital presence" |

*These show the *pattern* of how to evolve themes (descriptive → interpretive). Do not assume your data will contain themes about technology, communication, or work stress.

**Output:** 4-8 candidate themes with central concepts, preliminary thematic map

**Transition to Phase 4:** *"We now have [N] candidate themes. Ready to review and refine them together?"*

---

### Phase 4: Reviewing Themes (Conversational)

**Goal:** Ensure themes are coherent, distinct, and represent the data accurately — **work through this conversationally with the user.**

**Two-Level Review:**

**Level 1 - Internal Coherence:**
- Do the coded segments within this theme belong together?
- Is there a clear shared concept?
- Is the theme too broad or too narrow?

**Level 2 - External Validity:**
- Do themes work together as a set?
- Are themes clearly distinct from each other?
- Do they capture the full dataset?
- Do they answer the research question?

**Conversational Review Format:**

> 🔴 **This is a FORMAT TEMPLATE only.** Replace "[THEME NAME]," "[CODE-1]," etc. with actual themes and codes from YOUR analysis.

```
Let's review each theme together. Starting with:

[EMOJI] THEME: "[Theme Name from Your Data]"

Codes included:
  - [CODE-1] (X instances)
  - [CODE-2] (Y instances)
  - [CODE-3] (Z instances)

Sample quotes:
  "[Actual quote from data]" (P#)
  "[Another quote from data]" (P#)

QUESTIONS FOR REVIEW:
□ Does "[Theme Name]" capture what unites these codes?
□ Are there quotes that DON'T fit this theme?
□ Is this theme distinct from the others we've discussed?

What's your sense — does this theme hold together? Anything 
you'd change?
```

**Patton's Dual Criteria:**

| Criterion | Question | Application |
|-----------|----------|-------------|
| **Internal Homogeneity** | Do data within the theme fit together? | Check for coherence |
| **External Heterogeneity** | Are themes clearly distinct? | Check for overlap |

**Refinement Actions (discuss with user):**

| Issue | Action | Example |
|-------|--------|---------|
| Theme too broad | Split | "Challenges" → "Technical barriers" + "Social barriers" |
| Themes overlap | Collapse | "Time pressure" + "Workload" → "Time demands" |
| Theme unclear | Redefine | "Stuff about work" → "Negotiating professional identity" |
| Insufficient data | Discard | Remove themes with only 1-2 quotes |
| Missing pattern | Return to coding | Add new codes for overlooked areas |

**Agent's role:**
- Present each theme with supporting evidence
- Ask targeted questions about coherence and distinctness
- Propose refinements based on user feedback
- Iterate until user is satisfied

**Transition to Phase 5:** *"Themes are feeling solid. Shall we finalize the definitions and names together?"*

---

### Phase 5: Defining and Naming Themes (Conversational)

**Goal:** Finalize themes by articulating their essence and creating evocative names — **work through this conversationally with the user.**

**For Each Theme, Develop Together:**

**Agent presents template, user contributes:**

> 🔴 **This is a TEMPLATE FORMAT only.** The theme "Navigating Digital Boundaries" and its definition are EXAMPLES showing the structure. Replace with themes derived from YOUR data.

```
Let's define Theme 1: "[Theme Name from Your Data]"

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

DEFINITION:
[Agent proposes based on YOUR data and our conversation] 
[Describe the central concept that unites the codes in this theme,
based on patterns found in the actual dataset]

[Ask user] Does this capture the essence? What would you add or change?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SCOPE:
- Includes: [develop together based on your data]
- Excludes: [develop together based on your data]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SUB-THEMES:
1. [Agent suggests based on patterns in YOUR data] [description]
2. [Agent suggests based on patterns in YOUR data] [description]

[Ask user] Do these sub-themes match your understanding? Others?

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

CONTRIBUTION TO RESEARCH QUESTION:
[develop together]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FINAL NAME OPTIONS:
A. "[Agent's suggestion based on your data]"
B. [User can propose alternatives]
C. "[Alternative evocative name based on your data]"

Which resonates most? Or shall we brainstorm others?
```

**Naming Guidelines***

| Weak Name | Strong Name | Why |
|-----------|-------------|-----|
| "Problems" | "Navigating systemic neglect" | Captures action + meaning |
| "Feelings" | "Emotional labor of care" | Specific + interpretive |
| "Technology" | "Digital disruption of intimacy" | Evocative + conceptual |

*These show the *pattern* of weak → strong naming. Do not assume themes about problems, feelings, or technology will be in the data.

**Output:** Finalized themes with definitions, scope, sub-themes, and evocative names

**Transition to Phase 6:** *"Themes are now finalized. Shall I proceed to produce the final report? I'll generate it autonomously based on what we've developed together."*

---

### Phase 6: Producing the Report (Agent Autonomous)

**Goal:** Present findings with vivid examples and analytical narrative — **proceed autonomously after receiving user permission.**

**Trigger:** User says "yes," "proceed," "generate report," etc.

**Report Structure:**
1. **Introduction** - Research questions, why TA was chosen
2. **Methodology** - Data collection, analytical process, reflexivity statement
3. **Findings** - Each theme with definition, narrative, and quotes
4. **Discussion** - Interpretation, connections to literature
5. **Conclusion** - Summary, limitations, recommendations

**Using Quotes Effectively:**
- Include sufficient context for quotes to make sense
- Balance analytic narrative with raw data
- Show range—not just perfect examples
- Anonymize appropriately

**Agent delivers:**
- Complete report in markdown format
- Optional: Offer to save as a file
- Offer to make any adjustments based on user feedback

---

## Analyzing Coverage: What's Explored vs. Avoided

### Assessing Analytical Coverage

**Coverage Dimensions:**

| Dimension | Questions to Ask | Red Flags |
|-----------|------------------|-----------|
| **Depth** | Are themes richly developed with nuance? | Thin themes with few quotes |
| **Breadth** | Do themes capture the full dataset? | Important topics missing |
| **Balance** | Are all participants/themes represented? | Over-reliance on outliers |
| **Reflexivity** | Has researcher position been examined? | No discussion of bias |

### Identifying Potentially Avoided Areas

**Signs of Avoidance:**
1. **Silences in data:** Topics participants mentioned that weren't coded
2. **Disconfirming evidence:** Data that contradicts emerging themes
3. **Marginalized voices:** Certain participant groups underrepresented
4. **Convenient themes:** Patterns that confirm researcher expectations
5. **Vague themes:** "Miscellaneous" or "Other" categories

**Techniques to Surface Avoided Areas:**

1. **Negative Case Analysis:**
   - Actively look for data that disconfirms themes
   - Document and explain exceptions
   - Revise themes to account for variation

2. **Data Audit:**
   - Randomly sample 10% of uncoded data
   - Ask: What wasn't captured?
   - Add new codes/themes if needed

3. **Reflexive Questions (ask user during conversation):**
   - What hypotheses did you have before reading data?
   - Are we ignoring data that contradicts your beliefs?
   - What would stakeholders want to hear?
   - What topics feel uncomfortable to code?

4. **Gap Analysis Matrix:**

| Research Question | Themes Addressing | Gaps Identified |
|-------------------|-------------------|-----------------|
| RQ1: Experience of X | Theme A, Theme B | Missing: negative experiences |
| RQ2: Response to Y | Theme C | Missing: long-term effects |

---

## Quality Checklist

### 15-Point Quality Criteria (Braun & Clarke)

| # | Criterion | Check |
|---|-----------|-------|
| 1 | Data transcribed to appropriate level | ☐ |
| 2 | Each data item given equal attention | ☐ |
| 3 | Themes not from vivid examples only | ☐ |
| 4 | Themes capture something important about data | ☐ |
| 5 | Data within themes cohere meaningfully | ☐ |
| 6 | Clear distinction between themes | ☐ |
| 7 | Themes internally coherent and distinctive | ☐ |
| 8 | Analysis matches theoretical framework | ☐ |
| 9 | Data extracts relate to identified themes | ☐ |
| 10 | Data extracts sufficient to support claims | ☐ |
| 11 | Analysis makes sense relative to extracts | ☐ |
| 12 | Analysis goes beyond description | ☐ |
| 13 | Analysis is nuanced and sophisticated | ☐ |
| 14 | Analysis tells convincing story about data | ☐ |
| 15 | Analysis addresses research question | ☐ |

### Credibility Strategies

| Strategy | Application |
|----------|-------------|
| **Prolonged engagement** | Spend sufficient time with data |
| **Peer debriefing** | Regular discussions with user |
| **Negative case analysis** | Actively seek disconfirming evidence |
| **Thick description** | Rich, contextualized reporting |
| **Audit trail** | Document all analytical decisions |
| **Reflexivity journal** | Track assumptions and positionality |

---

## Codebook Development (Team-Based Analysis)

For collaborative or structured approaches, see [references/codebook-guide.md](references/codebook-guide.md).

### Quick Codebook Structure

```
THEME: [Name]
├── Code 1: [Name]
│   ├── Definition
│   ├── Inclusion criteria
│   ├── Exclusion criteria
│   └── Examples (2-3)
├── Code 2: [Name]
│   └── ...
```

### Coding Reliability

When using codebook approaches:
- Train coders with practice sessions
- Calculate inter-rater reliability (Cohen's Kappa target: ≥0.60)
- Hold calibration meetings to discuss discrepancies
- Document all coding decisions

---

## Common Pitfalls to Avoid

| Pitfall | Solution |
|---------|----------|
| **Theme = Topic Summary** | Ensure themes have central organizing concept |
| **"Themes emerged"** | Use active language: "we identified/developed" |
| **Positivism Creep** | Maintain methodological coherence |
| **Frequency = Significance** | Consider meaning, not just frequency |
| **Insufficient Familiarization** | Read data multiple times before coding |
| **Theme Overload** | Aim for 4-8 main themes |
| **Ignoring Reflexivity** | Document researcher position throughout |
| **Agent Dominance** | Ensure user drives interpretive decisions |

---

## Tool Recommendations

| Use Case | Tool | Notes |
|----------|------|-------|
| Small projects (<20 interviews) | Spreadsheet + manual coding | Low learning curve |
| Free QDA software | Taguette, QualCoder | Good functionality |
| Commercial QDA | NVivo, MAXQDA, ATLAS.ti | Advanced features |
| Team collaboration | Dedoose | Real-time collaboration |
| AI assistance | Use for suggestions only | Human must lead analysis |

---

## Key References

- Braun, V. & Clarke, V. (2006). Using thematic analysis in psychology. *Qualitative Research in Psychology*, 3(2), 77-101.
- Braun, V. & Clarke, V. (2019). Reflecting on reflexive thematic analysis. *Qualitative Research in Sport, Exercise and Health*, 11(4), 589-597.
- Braun, V. & Clarke, V. (2022). *Thematic Analysis: A Practical Guide*. SAGE.
- DeCuir-Gunby, J.T. et al. (2011). Developing and using a codebook. *Field Methods*, 23(2), 136-155.
- Miles, M.B., Huberman, A.M. & Saldaña, J. (2014). *Qualitative Data Analysis: A Methods Sourcebook* (3rd ed.). SAGE.
- Nowell, L.S. et al. (2017). Thematic analysis: Striving to meet the trustworthiness criteria. *International Journal of Qualitative Methods*, 16(1).

---

## Workflow Summary

### For the Agent:

1. **Prepare (Phases 1-2):** Read data, note initial impressions, generate codes with emoji prefixes — **autonomous**
2. **Present:** Share coded data, code key, and summary with user
3. **Theme (Phase 3):** Group codes into candidate themes — **conversational with user**
4. **Review (Phase 4):** Test themes against data, refine structure — **conversational with user**
5. **Define (Phase 5):** Articulate theme essence, create evocative names — **conversational with user**
6. **Request Permission:** Ask user before proceeding to final report
7. **Report (Phase 6):** Write analytical narrative with supporting evidence — **autonomous after permission**
8. **Audit:** Check coverage, identify gaps, ensure rigor

### For the User:

1. **Provide data files** (transcripts, documents)
2. **Review codes** presented by agent, give feedback
3. **Collaborate** on theme development (Phases 3-5) through conversation
4. **Grant permission** for final report generation
5. **Review and refine** the final report as needed

---

Remember: Thematic analysis is **iterative, not linear**. Expect to cycle back through phases as your understanding deepens. The conversational workflow ensures user insight guides the interpretive work at the crucial theme development stages.
