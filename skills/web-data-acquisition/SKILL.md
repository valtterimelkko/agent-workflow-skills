---
name: web-data-acquisition
description: "Route web scraping, crawling, site-ingestion, URL discovery, structured extraction, and public-site capture tasks to the right local stack. Make sure to use this whenever the user wants to scrape a site, crawl docs, export markdown from many pages, map a website, capture a public website for later analysis, understand a website thoroughly, gather comprehensive information from a site, extract structured data from pages, or recover blocked public web content."
---

# Web Data Acquisition

Use this skill as the **first routing layer** for public web-data tasks.

It exists to stop the agent from improvising the stack every time. Choose the best local path first, then escalate only when the target is blocked.

This skill routes **acquisition**, not full research synthesis. For research tiering, think:
- native `web_search` / `web_fetch` for tiny tasks
- `gpt-research` for fast 10-20 source synthesis
- `deep-research` for heavy 40+ source auditable work

## Routing

### 1. Small public fetches
Use the agent's **native `web_fetch` / `web_search` tools first** for:
- one page or a handful of pages
- quick article or docs summarisation
- simple fact extraction from cooperative sites

Only reach for `webfetch-skill` if the native web tools are unavailable or there is a specific reason to use that script workflow.

### 2. Whole-site content crawl / markdown ingestion
Use **`crawl4ai`** for:
- documentation crawling
- exporting markdown from many pages
- AI/RAG-ready site ingestion
- deep crawl with page caps

### 3. Site mapping / URL discovery
Use **`katana`** for:
- enumerating routes before extraction
- discovering internal URLs, known files, and JS-linked endpoints
- understanding site surface before a deeper crawl

### 4. Structured extraction
Use **`scrapegraph-ai`** for:
- extracting structured JSON-like answers from one page or a small set of pages
- pricing/contact/product/company extraction
- cases where brittle selectors are not ideal

### 5. Anti-bot or JS-rendering problems
Use **`camofox`** as the free local fallback when the native path fails because of:
- Cloudflare or similar bot protection
- CAPTCHA / challenge pages
- blank pages / JS-required rendering
- anti-scraping blocks

### 6. Paid targeted recovery
Use **`residential-proxy`** only when:
- the native path failed
- `camofox` was actually tried and still failed, or the task is a narrow public HTTP endpoint recovery where a browser path is not sufficient
- the blocked URLs are genuinely high-value
- the user explicitly approved paid proxy usage

## Escalation contract

Always follow this order:

1. **Native best-fit tool**
2. **`camofox`** if blocked by JS / anti-bot / challenge flow
3. **`residential-proxy`** only with explicit permission and only for narrow recovery

Do **not** silently push a whole crawl through the residential proxy.

## Guardrails

- Keep the acquisition path as cheap and local as possible.
- Prefer discovery first, then extraction, rather than blind crawling.
- If only a few URLs matter, recover only those URLs.
- If the task is really browser interaction rather than data acquisition, prefer `agent-browser` / `browser-use` and only bring in `camofox` when anti-bot pressure is the actual blocker.

## Reporting

When you use this routing skill, report:

```markdown
## Web-data path used
- Primary route: native fetch | crawl4ai | katana | scrapegraph-ai
- Escalated to camofox: yes/no
- Escalated to residential proxy: yes/no
- Reason for escalation: ...
- URLs or scope: ...
- Artifacts created: ...
- Remaining blockers: ...
```
