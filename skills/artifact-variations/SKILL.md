---
name: artifact-variations
description: "Generate many design, copy, or layout variations as a single browsable HTML artifact so the user can pick favorites visually instead of describing what they want in words. Use when the user asks for design variations, multiple versions of a UI component, alternative layouts, copy variants, different takes on the same section, or anything phrased as 'give me options' / 'I want to see a few variations' / 'I'll know it when I see it'. Also use this pattern whenever a decision between options is easier to make by eye than by description — landing page heroes, settings screens, pricing cards, LinkedIn post drafts, icon styles, color directions. Do not use this skill for building the final production artifact itself — use it to explore, then hand the chosen variation to the implementation skill."
---

# Artifact Variations

Use this skill when the user needs to **pick a favorite from a set of options visually** rather than describe what they want in words.

The core idea: instead of iterating over a single design through many rounds of feedback, generate **N distinct variations in one HTML artifact**, let the user scroll through, pick the one (or few) they like, and then apply that choice to the real codebase. This collapses design exploration from many turns to one.

This is **Layer 1** of the interactive artifact pattern — a static, one-shot artifact used as a decision surface.

## When to use this skill

Use it when:

- the user asks for "variations", "options", "takes", "versions", or "a few different ways"
- the task involves picking a design direction and the user struggles to describe what they want
- the choice is subjective (layout, typography, color direction, copy tone, illustration style)
- iteration-by-description is slow and picking-by-eye would be fast
- the component, section, or output is visual enough that side-by-side viewing helps

Good examples:
- "give me 10 hero section variations for this landing page"
- "I'm not sure what the settings screen should look like — show me some options"
- "draft a few versions of this LinkedIn post so I can pick the tone"
- "what are some ways this pricing card could look"

Do not use this skill for:
- building the final artifact after the direction is already known → use the appropriate frontend/implementation skill directly
- generating a single polished component → use `frontend-design` or `ui-ux-pro-max`
- design discovery that needs a full `DESIGN.md` first → use `cli-design-studio`
- exploring reference sites → use `skill-ui` or `awesome-design-md`

## The workflow

### 1. Clarify scope and mode

Before generating, nail down:

- **What is the unit?** One component, one section, one full page, or just the copy
- **How many variations?** Default to 6–10. Go higher (15–25) when the user explicitly wants to explore widely, lower (3–5) when the decision space is small or the user has already narrowed down candidates
- **What stays constant?** Brand, theme, content structure, or nothing? The constants anchor the comparison
- **What should vary?** Layout, typography, color direction, density, tone, illustration style, or a mix
- **Wide or refinement round?** If this is a first pass, maximise diversity across the full option space. If the user has already picked rough favourites from a previous round, bias toward winners and prune the rest — don't serve 10 near-identical refinements when 3–4 focused ones would do

Ask only if unclear. If the user says "give me 10 variations of this hero" and the hero exists in the codebase, extract it and vary freely.

### 2. Plan the variation matrix before generating

This is the step that separates useful variation sets from noise. **Before writing any HTML**, sketch a lightweight matrix that assigns each variation a unique combination of axes. You don't need to show the user this matrix, but you must think through it.

The axes depend on the task, but for UI work they typically include:

| Axis | Examples |
|------|---------|
| Layout archetype | split, stacked, centered, sidebar, full-bleed, grid |
| Typography voice | editorial serif, compact sans, display mono, humanist |
| Density | spacious / airy, balanced, dense / data-heavy |
| CTA framing | outcome-led, demo-pull, low-friction, social-proof |
| Visual mood | clean minimal, warm illustrative, technical precision, bold contrast |

**The self-check:** no two variations should occupy the same combination of layout archetype + typographic voice. If you find you have duplicates, redesign one until it occupies a distinct slot. This is what makes the set actually useful for picking.

For copy-only variants (LinkedIn posts, email drafts, etc.) the axes shift to: tone register, opening hook type, structural framing, CTA posture, length, punctuation rhythm.

### 3. Pick the design direction

If the user already has a design system (existing codebase, brand, DESIGN.md), **stay within it** — the variations should all feel like they belong to the same product, just exploring different executions.

If there's no direction yet, make each variation visibly distinct (different layout archetypes, different typographic voices, different density) rather than small tweaks of the same thing. The point is to surface options that are actually different, not six versions of the same idea.

Consider routing to a companion skill for the design direction:

- `ui-ux-pro-max` — for structured design-system decisions (product-type reasoning, palettes, typography systems). Strong default when the user wants grounded, professional variations
- `frontend-design` — for distinctive, bold aesthetic execution. Use when variations should push against generic AI aesthetics
- `taste-design` — when the user wants more confident, curated stylistic point of view across all variations
- `awesome-design-md` / `skill-ui` — when variations should be grounded in real reference sites
- `cli-design-studio` — only if design ambiguity is blocking; otherwise proceed directly

### 4. Generate the variations HTML artifact

Create a **single HTML file** that displays all variations in a scrollable, browsable layout.

**Required structure of the artifact:**

1. **Header** — one line stating what stays constant across all variations (content, brand, product story, etc.) so the user knows what they are comparing
2. **Variation cards** — one per variation, each containing:
   - A short **ID** (`V1`, `V2`, … or `H1`–`H8`, `P1`–`P6`, etc.) — this lets the user reference picks without prose ("V3 layout + V7 typography")
   - A descriptive **angle name** ("editorial / heavy serif", "compact dashboard", not just "Option 3")
   - A one-line **"what changed"** note beneath the label (e.g. "Split layout · Display mono · Dense · Demo CTA")
   - The **rendered variation** itself
3. **Selection footer** — a lightweight "pick your favourites" section at the bottom with short IDs, so the user can quickly note "V2, maybe V5 for copy" without scrolling back up

Consistent rendering rules:
- consistent width/viewport so comparisons are fair
- for UI components, render them against a neutral page background so the component is what catches attention
- for copy, LinkedIn posts, or message drafts, mimic the destination surface (LinkedIn card, tweet card, email preview) so the user sees it in context
- include the full content inline — no external dependencies that require a server

Keep it simple: one HTML file, self-contained CSS, no build step. The artifact is disposable — it exists to help the user pick, not to ship.

### 5. Run the self-check before saving

Before writing the final file, verify:

- No two variations share the same layout archetype AND typographic voice
- All variations preserve the stated constants (same copy facts, same brand colours if specified)
- Labels are by angle, not just number
- The artifact has the header, per-variation "what changed" notes, and a selection footer
- Count is in the agreed range

If any check fails, fix it. This is cheap to do before the user sees it, expensive to fix after.

### 6. Make it viewable

Give the user a way to actually look at the artifact:

- saving locally and opening in a browser is fine for quick local loops
- **for sharing or viewing from another device, use `here-now`** to publish the HTML as a live URL. This is especially useful when the user is on mobile, showing the options to a colleague, or wants to compare on different screens

### 7. Let the user pick

After presenting the artifact:

- invite the user to reference variations by short ID ("V3", "V5's layout + V2's tone")
- follow up with the real implementation: apply the chosen direction to the actual codebase
- if no variation lands, generate a second round biased toward what worked and away from what didn't — this is a **refinement round**, so use fewer variations (3–5) focused tightly on the promising directions

### 8. Apply the winner

This is where the artifact-variations skill hands off. Once the user has picked, route to the right implementation skill:

- `frontend-design` or `ui-ux-pro-max` → for web components and pages
- the relevant project codebase directly → if the user wants the real component updated
- `post-linkedin` / `valtteris-linkedinx-voice` → for copy variations that end up in LinkedIn posts

The variations artifact itself is disposable — it did its job once the choice was made. You do not need to preserve it unless the user asks.

## What makes variations useful

Good variation sets are:

- **actually different** — if variations 1 through 10 all look like minor tweaks, the user can't make a real decision. The matrix check in step 2 is the practical guard against this
- **evenly fair** — same content, same viewport, same lighting. The user should pick based on design, not because one happened to get nicer copy
- **labeled by ID + angle** — `V3 · editorial / heavy serif` is more useful than "Variation 3". Short IDs are essential for mix-and-match picks
- **annotated with what changed** — "what changed" notes remove ambiguity when users want to remix across variations
- **anchored to reality** — respect the brand and product. Wild variations in a specific product context are noise, not options

Bad variation sets:

- six cards that differ only in gradient direction (fails the matrix check)
- variations that break the design system without saying so
- 20 variations when 6 would have been enough (decision fatigue)
- variations of the whole page when only the hero was the question
- missing short IDs — forces the user to write "the third one with the blue thing" instead of "V3"

## A note on how agents use this

Coding agents using this skill already know how to write HTML. The skill's value is in the **pattern and process**:

1. **Plan first** — build the variation matrix before writing a line of HTML. This is the step most agents skip, and it's what causes near-identical outputs.
2. Explore through parallel options, not sequential iteration
3. Make decisions visual, not verbal
4. Embed decision infrastructure in the artifact (IDs, "what changed" notes, selection footer)
5. Keep the exploration artifact separate from the real codebase
6. Hand off after choice, don't polish the exploration artifact

Do not over-engineer the variations artifact. It is scaffolding, not a deliverable. But do put the structural pieces in place — header, IDs, "what changed", footer — because that is what makes the artifact a genuine decision tool rather than just a gallery.
