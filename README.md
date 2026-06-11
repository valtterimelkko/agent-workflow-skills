# Agent Workflow Skills

A curated public collection of practical `SKILL.md`-style prompts for coding agents.

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
- `systematic-debugging`
- `test-driven-development`
- `handoff`
- `grill-me`

### Maintainer / documentation skills
- `code-documenter`
- `openapi-schema`
- `socialmedia-optimization`

### Agent operations and ecosystem skills
- `web-data-acquisition`
- `claude-p`
- `claude-channels`
- `opencode-plugin`
- `artifact-variations`

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
  web-data-acquisition/
  claude-p/
  claude-channels/
  opencode-plugin/
  artifact-variations/
```

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

This repo is being prepared as a fresh public extraction from a much larger private library. Before publishing, run one final secret/path audit over the extracted folders and then push to a new public GitHub repository.
