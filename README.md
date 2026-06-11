# Agent Workflow Skills

A curated public collection of practical `SKILL.md` agent skills for AI-agent workflows.

Most of these skills happen to be used inside coding-agent harnesses, but they are not only for coding. Many of them are for research, media, document workflows, qualitative analysis, web capture, and agent-operational design more broadly.

## Project story

After Anthropic popularised the `SKILL.md` pattern, I started building my own private skills library to make real work faster and more reliable.

That work grew out of two overlapping contexts:

1. day-to-day work in **experiential education** inside a UK university environment
2. a parallel obsession with **AI coding agents**, agent runtimes, workflow automation, and prompt-operational design

Over time, the private library became much larger and more environment-specific than a public repo should be. This repository is the opposite of a dump: it is a **curated extraction** of the skills that feel broadly useful to other agent builders and are safe to publish without exposing personal, employer, or infrastructure-specific details.

## What this repo is

This repo contains a small set of opinionated skills for agent workflows such as:

- systematic debugging
- test-first implementation
- session continuity
- clarification and planning
- codebase documentation
- OpenAPI schema authoring
- agent-oriented web/data acquisition routing
- Claude Code operational patterns
- OpenCode plugin development
- visual variation generation

Each skill lives in its own folder and is designed to be readable, copyable, and adaptable.
Some of the bundled scripts expect you to provide your own API keys, proxy credentials, or local shell-environment setup; the public repo includes the skill logic, but you still need to supply your own credentials and environment wiring.

## What this repo is not

- not my full private skills library
- not a dump of employer-specific or personal workflow skills
- not a guarantee that every skill matches every harness exactly as-is
- not a credential-bearing automation bundle

## Selection rules for this public extraction

A skill qualified for this repo only if it was:

- broadly useful outside my own environment
- not tied to a university, employer, or private tenant
- not written in my own personal/public voice
- not dependent on sensitive local infrastructure
- worth publishing as an original workflow or operational pattern

## Included skills

### Core workflow patterns
- `systematic-debugging` — root-cause-first debugging discipline for bugs, test failures, and unexpected behaviour
- `test-driven-development` — test-first implementation workflow for features and bugfixes
- `handoff` — structured session handoff skill for continuity across agent sessions
- `grill-me` — clarification and stress-testing skill for plans, projects, workflows, and designs *(adapted/curated from Matt Pocock's `grill-me` skill in `mattpocock/skills`)*

### Maintainer / documentation skills
- `code-documenter` — comprehensive project documentation generation for APIs, apps, CLIs, and libraries
- `openapi-schema` — creation and repair of OpenAPI 3.1 schemas for API integrations and GPT-style actions, built from public documentation and implementation research
- `socialmedia-optimization` — implementation and validation of Open Graph and social preview metadata
- `context7-search` — search for the correct Context7 library ID before documentation lookup; useful when agents need the exact library handle before fetching docs
- `context7-docs` — fetch current library/framework documentation from Context7, a service that helps agents retrieve up-to-date library syntax and usage examples beyond training-cutoff knowledge

### Research and analysis skills
- `deep-research` — broad, auditable multi-source research workflow for high-stakes topics, built by me and inspired in part by Google Gemini Deep Research while aiming for stronger controllability and, in some cases, better output quality
- `thematic-analysis` — collaborative coding and theme development for qualitative text data; especially useful for interview transcripts, reflective writing, and other qualitative datasets
- `academic-writing` — British academic writing best-practice guide for higher-education prose
- `video-deep-understanding` — grounded video understanding workflow that combines transcript evidence with targeted visual/frame evidence when you need an agent to understand what is happening in a video, not just what is being said

### Agent operations and ecosystem skills
- `web-data-acquisition` — routing layer for choosing the right scraping, crawling, or extraction approach
- `web-crawling` — bounded multi-page crawl workflow with optional local Browserless examples
- `webfetch-skill` — cleaner single-page/few-page extraction workflow using a bundled fetch script
- `claude-p` — operational guidance for programmatic non-interactive / print-mode Claude Code CLI usage (`claude -p`), based on public documentation and observed scripting patterns
- `claude-channels` — guidance for building channel plugins that push events into live Claude Code sessions, based on public documentation for the channels interface
- `opencode-plugin` — development and troubleshooting guide for OpenCode plugins, based on public OpenCode plugin documentation and ecosystem research
- `artifact-variations` — generate multiple visual/copy/layout variations as a browsable selection artifact
- `pi-extension` — build and debug Pi extensions with current extension APIs and patterns, based on public Pi Coding Agent documentation and examples

### Document workflow skills
- `docx-draft` — round-trip Word-to-markdown drafting while preserving document structure for rebuild
- `pptx-draft` — round-trip PowerPoint-to-markdown drafting while preserving presentation structure for rebuild
- `audio-transcription-workflow` — convert local audio files into cleaned markdown transcripts with layered fallbacks

### Media, web, and asset skills
- `youtube-search` — search YouTube videos with filtering for channels, dates, sort order, and duration
- `youtube-caption` — fetch YouTube captions/transcripts and metadata with optional proxy support
- `text-to-speech` — local CPU-based text-to-speech generation using [Supertonic](https://github.com/supertone-inc/supertonic)
- `transcribe-audio` — simple local Whisper-service transcription for English audio files
- `video-use` — conversation-driven transcript-led video editing workflow
- `web-asset-generator` — generate favicons, app icons, and social preview assets
- `web-create-assets` — create net-new branded UI assets that match an existing design system
- `agy-p` — programmatic non-interactive Antigravity CLI integration guide
- `amazon-uk-scraper` — Amazon UK product/spec scraping with optional anti-bot routing
- `scraping-reddit` — Reddit opportunity/pain-point scraping with optional proxy and OAuth setup
- `scraping-twitter` — Twitter/X opportunity/pain-point scraping via TwitterAPI.io
- `saas-idea-finder` — multi-source SaaS idea discovery pipeline with optional API integrations
- `capture-dashboard` — screenshot/HTML capture for authenticated dashboards using exported cookies

## Structure

```text
skills/
  systematic-debugging/
  test-driven-development/
  handoff/
  grill-me/
  code-documenter/
  openapi-schema/
  socialmedia-optimization/
  context7-search/
  context7-docs/
  deep-research/
  web-data-acquisition/
  web-crawling/
  webfetch-skill/
  claude-p/
  claude-channels/
  opencode-plugin/
  artifact-variations/
  pi-extension/
  docx-draft/
  pptx-draft/
  audio-transcription-workflow/
  youtube-search/
  youtube-caption/
  text-to-speech/
  transcribe-audio/
  thematic-analysis/
  video-deep-understanding/
  video-use/
  web-asset-generator/
  web-create-assets/
  academic-writing/
  agy-p/
  amazon-uk-scraper/
  scraping-reddit/
  scraping-twitter/
  saas-idea-finder/
  capture-dashboard/
shared/
```

## Setup notes by skill

Some skills are pure workflow/documentation skills. Others include scripts that require you to supply your own credentials, browser cookies, proxy access, or local services.

### Mostly self-contained / local-first
- `systematic-debugging`, `test-driven-development`, `handoff`, `grill-me`, `code-documenter`, `openapi-schema`, `socialmedia-optimization`, `academic-writing`, `thematic-analysis`, `artifact-variations` — mostly documentation/prompt workflow, little or no external setup.
- `text-to-speech` — requires local Python dependencies and the Supertonic model download; see [supertone-inc/supertonic](https://github.com/supertone-inc/supertonic).
- `transcribe-audio` — requires a local Whisper ASR service at `http://localhost:9000` or an equivalent setup.

### Requires your own API keys or service credentials
- `context7-search`, `context7-docs` — `CONTEXT7_API_KEY`
- `youtube-search` — `YOUTUBE_API_KEY`
- `youtube-caption` — optional `YOUTUBE_PROXY_URL` (or legacy `REDDIT_PROXY_URL`) when proxy support is needed
- `audio-transcription-workflow` — optional `OPENAI_API_KEY`, `OPENROUTER_API_KEY`, optional `AUDIO_TRANSCRIPTION_LEGACY_ENV`
- `web-create-assets` — `RUNWARE_API_KEY`
- `video-deep-understanding` — optional `OPENAI_API_KEY`, optional `VIDEO_PROXY_URL` (or legacy `REDDIT_PROXY_URL`)
- `scraping-twitter` — `TWITTERAPI_KEY`
- `scraping-reddit` — optional `REDDIT_PROXY_URL`, optional Reddit OAuth credentials
- `saas-idea-finder` — several optional integrations such as `OPENROUTER_API_KEY`, `TWITTERAPI_KEY`, `YOUTUBE_API_KEY`, `SERPAPI_KEY`, `STACK_KEY`, `PRODUCTHUNT_TOKEN`, Reddit proxy/OAuth, and related sources

### Requires local browser/session/cookie setup
- `capture-dashboard` — exported browser cookies for the target authenticated dashboard
- `amazon-uk-scraper` — optional anti-bot routing/proxy setup if you need UK-specific pricing/delivery accuracy

### Requires local tool/runtime setup
- `pi-extension` — Pi Coding Agent installation and docs/examples for your installed version
- `claude-p`, `claude-channels` — Claude Code CLI installation and local auth state
- `opencode-plugin` — OpenCode installation and plugin runtime
- `agy-p` — Antigravity CLI installation and local auth state
- `video-use` — ffmpeg plus the repo's editing helpers and any optional animation/video tooling you choose to use
- `web-crawling`, `webfetch-skill`, `web-data-acquisition`, `deep-research` — optional anti-bot or browser-recovery additions such as Camoufox, Browserless, or residential proxies can improve resilience, but are not universally required.

In general: **the public repo ships the skill logic, examples, and helper scripts, but you must supply your own credentials, services, and environment wiring.**

## How I use some of these skills in practice

### `artifact-variations`
This is one of my favourite ways to work with visual ambiguity. Instead of trying to describe the perfect output in one go, I ask the agent to generate multiple variations at once — for example three hero sections, three landing page directions, three presentation covers, or three image/layout options. Comparing options visually is usually much easier than writing ever more precise instructions blindly.

In practice I often combine it with a fast publishing/deployment step — sometimes with tools like here.now — so I can view the variations in a browser, compare what I like and dislike, and then ask for a refined second round or a hybrid of the strongest options.

### `docx-draft` and `pptx-draft`
These two are especially valuable in real professional workflows because they separate **content editing** from **layout preservation**.

The core idea is:
1. start from a real Word or PowerPoint file that already has the right formatting, branding, logos, colours, masters, and layout rules
2. convert it into structured markdown that preserves enough structure to rebuild accurately
3. let the agent edit the content inside that structured representation
4. convert it back while keeping the original document formatting/layout intact

That makes these skills unusually practical for corporate templates, institutionally formatted documents, branded decks, and any workflow where normal AI document generation would otherwise damage layout quality.

### `video-deep-understanding`
This is not just a transcript workflow. It is for cases where you need an agent to understand a video **visually as well as verbally** — for example a product demo, a UI walkthrough, a recorded presentation, or a screen capture where the important evidence is partly on screen rather than in speech.

It can be token-heavy, but it is the best fit when the task is "understand what is happening in this video in detail", not merely "transcribe what was said".

### `amazon-uk-scraper`
I often use this as part of pre-purchase research. It helps an agent compare product variants, check whether a specific item is actually easy to buy from Amazon UK, verify delivery/Prime availability, and cross-check specs before ordering.

That makes it useful both for straightforward buying decisions and for narrowing down exactly which version of a product I mean when multiple near-identical listings exist.

### `capture-dashboard`
I use this when I want to capture the essence of an existing dashboard — including authenticated ones — so I can study it, benchmark it, or reuse the best ideas when designing my own dashboard/UI.

It is helpful both for documentation/archival capture and for design analysis of real products that already solve similar interface problems well.

### `saas-idea-finder`
This is a multi-source opportunity-discovery workflow rather than a single search prompt. The goal is to help an agent gather signals from multiple platforms, look for recurring pain points, and turn them into structured SaaS or micro-SaaS opportunities.

Depending on how much setup you provide, it can combine optional connectors such as:
- Reddit signals
- X/Twitter signals
- YouTube search
- web search / SERP data
- Stack Exchange signals
- Product Hunt data
- LLM synthesis via OpenRouter

The point is not just to list ideas, but to create a more grounded pipeline for spotting repeated frustrations, workflow gaps, and commercially interesting patterns across sources.

### `thematic-analysis`
This skill sits much closer to qualitative research practice than to generic summarisation. It is designed for coding transcripts, grouping patterns, iterating themes, and checking what parts of the dataset are being foregrounded or neglected.

It is especially useful for interview transcripts, reflective journals, open-text survey responses, and other qualitative datasets where the task is to build an interpretive account rather than just produce a summary.

## Attribution and provenance notes

This public extraction is primarily a curated subset of my broader private skills library, but not every included skill has the same origin story.

- `grill-me` is included as a curated/adapted skill and should credit the original public source: **Matt Pocock's `grill-me` skill** from [`mattpocock/skills`](https://github.com/mattpocock/skills).
- `openapi-schema`, `claude-p`, `claude-channels`, `opencode-plugin`, and `pi-extension` are based on public documentation and implementation research rather than on private source material.
- `deep-research` is an original skill built by me, influenced in part by the product direction of Gemini Deep Research but implemented as my own agent workflow.
- `text-to-speech` should credit **Supertonic** by Supertone as the underlying local TTS engine: [GitHub](https://github.com/supertone-inc/supertonic).
- `thematic-analysis` is strongly informed by the thematic analysis tradition associated with **Virginia Braun** and **Victoria Clarke**, especially their 2006 paper *Using thematic analysis in psychology* and later book-length guidance such as *Thematic Analysis: A Practical Guide*.

Useful upstream/public references for some included skills:
- **Pi Coding Agent** — website: [pi.dev](https://pi.dev/) · GitHub: [earendil-works/pi](https://github.com/earendil-works/pi)
- **OpenCode** — website: [opencode.ai](https://opencode.ai/) · GitHub: [opencode-ai/opencode](https://github.com/opencode-ai/opencode)
- **Camofox / Camoufox** — useful optional anti-bot companion for research and crawling workflows: GitHub: [daijro/camoufox](https://github.com/daijro/camoufox)

Where future provenance notes matter, this README should continue to distinguish between original skills, adapted skills, and curated inclusions.

## Notes on sanitisation

This public extraction intentionally removes or generalises:

- personal names and institution names
- local private filesystem assumptions where possible
- sensitive infrastructure references
- any skill that felt too tied to private tenants, grading systems, or personal workflow data

Some skills still reference ecosystem-specific conventions such as Claude Code paths or harness concepts. Those references are included only where they are part of the useful operational knowledge, and should be adapted to your own environment.

For bot-protected web research or crawling workflows, a practical setup can combine the included skills with optional anti-bot fallbacks such as **Camofox / Camoufox** and, where justified, a residential proxy. Those are not required for the core skills, but they can improve resilience against challenge pages and bot protection.

## How to use

There is no single required runtime. These skills are written in a portable style so you can:

- copy a skill into your own agent setup
- adapt the wording to your harness
- treat the repo as a pattern library for building your own skills

## Status

This repository is a fresh public extraction from a much larger private skills library. Only the skills that felt broadly useful and low-risk to share have been included here.
