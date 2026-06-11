# Agent Workflow Skills

A curated public collection of practical `SKILL.md` agent skills for coding-agent workflows.

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
- `openapi-schema` — creation and repair of OpenAPI 3.1 schemas for API integrations and GPT-style actions
- `socialmedia-optimization` — implementation and validation of Open Graph and social preview metadata
- `context7-search` — search for the correct Context7 library ID before documentation lookup
- `context7-docs` — fetch current library/framework documentation from Context7
- `deep-research` — broad, auditable multi-source research workflow for high-stakes topics

### Agent operations and ecosystem skills
- `web-data-acquisition` — routing layer for choosing the right scraping, crawling, or extraction approach
- `web-crawling` — bounded multi-page crawl workflow with optional local Browserless examples
- `webfetch-skill` — cleaner single-page/few-page extraction workflow using a bundled fetch script
- `claude-p` — operational guidance for programmatic multi-turn Claude Code CLI usage
- `claude-channels` — guidance for building channel plugins that push events into live Claude Code sessions
- `opencode-plugin` — development and troubleshooting guide for OpenCode plugins
- `artifact-variations` — generate multiple visual/copy/layout variations as a browsable selection artifact
- `pi-extension` — build and debug Pi extensions with current extension APIs and patterns

### Document workflow skills
- `docx-draft` — round-trip Word-to-markdown drafting while preserving document structure for rebuild
- `pptx-draft` — round-trip PowerPoint-to-markdown drafting while preserving presentation structure for rebuild
- `audio-transcription-workflow` — convert local audio files into cleaned markdown transcripts with layered fallbacks

### Documentation lookup and media skills
- `youtube-search` — search YouTube videos with filtering for channels, dates, sort order, and duration
- `youtube-caption` — fetch YouTube captions/transcripts and metadata with optional proxy support

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
shared/
```

## Attribution notes

This public extraction is primarily a curated subset of my broader private skills library, but not every included skill originated entirely from scratch here.

- `grill-me` is included as a curated/adapted skill and should credit the original public source: **Matt Pocock's `grill-me` skill** from [`mattpocock/skills`](https://github.com/mattpocock/skills).

Where future provenance notes matter, this README should continue to distinguish between original skills, adapted skills, and curated inclusions.

## Notes on sanitisation

This public extraction intentionally removes or generalises:

- personal names and institution names
- local private filesystem assumptions where possible
- sensitive infrastructure references
- any skill that felt too tied to private tenants, grading systems, or personal workflow data

Some skills still reference ecosystem-specific conventions such as Claude Code paths or harness concepts. Those references are included only where they are part of the useful operational knowledge, and should be adapted to your own environment.

## How to use

There is no single required runtime. These skills are written in a portable style so you can:

- copy a skill into your own agent setup
- adapt the wording to your harness
- treat the repo as a pattern library for building your own skills

## Status

This repository is a fresh public extraction from a much larger private skills library. Only the skills that felt broadly useful and low-risk to share have been included here.
