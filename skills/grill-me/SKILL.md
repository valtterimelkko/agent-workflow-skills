---
name: grill-me
description: "Interview the user relentlessly about a plan, project, workflow, or design until you reach shared understanding. Make sure to use this whenever the user wants to be grilled, stress-test an idea, clarify a new project, surface missing context, or think through decisions before execution."
---

Interview me relentlessly about every important aspect of this plan until we reach a shared understanding.

Walk down each branch of the decision tree, resolving dependencies one by one. For each question, provide your recommended answer, but stay open to correction.

Ask questions one at a time.

If a question can be answered by exploring the codebase, existing docs, available memory, or context already present in the session, explore that first instead of asking me to repeat it.

When relevant, begin by identifying what kind of project this is and what context already exists. Distinguish between:
- what is already decided
- what is assumed but unverified
- what is still open

Do not depend on any specific file path or agent harness. Use whatever context is available in the current environment. If important context is missing, ask me to provide it.

As the discussion progresses, periodically checkpoint the emerging understanding in a lightweight way. Keep track of:
- key decisions made
- important constraints
- assumptions
- unresolved questions
- items that need external verification

Keep the process lean. Do not turn this into a giant framework or a long lecture. The goal is to uncover the missing context that will make downstream execution much stronger.

Stop when the important branches have been covered and there is a solid, practical shared understanding. Finish with a concise synthesis of:
- the project or plan
- the key decisions
- the main open questions or risks
- the most sensible next step
