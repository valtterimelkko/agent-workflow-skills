---
name: web-crawling
description: "Crawl websites to extract text content from multiple pages and internal links. Use when the user wants to scrape a website, gather content across a section, archive docs text, understand a site more thoroughly by following internal links, or follow internal links beyond a single page. Prefer this general skill for bounded crawl workflows, route to Crawl4AI or Katana when the task is specifically AI-ready ingestion or site mapping, and escalate blocked pages to camofox before any residential-proxy discussion."
---

# Web Crawling

Use this skill for **general multi-page crawling** when the user wants more than a one-page fetch but does not yet need a highly specialised workflow.

## First choose the right crawl path

### Prefer `crawl4ai` when:
- the user wants markdown from many pages
- the output is for AI/RAG ingestion
- documentation export is the main goal
- you want a bounded deep crawl with good markdown output

### Prefer `katana` when:
- the main need is URL discovery or site mapping
- you want to enumerate a site's surface before extraction
- you need JS-aware endpoint discovery

### Prefer `scrapegraph-ai` when:
- the main need is structured extraction rather than broad crawling
- you only need a small set of pages turned into JSON-like facts

### Use this `web-crawling` skill directly when:
- you need a bounded general crawl
- a simple recursive content pass is enough
- you are combining native fetches, small scripts, and selective link following

## Default operating pattern

1. Start from the seed URL.
2. Use the agent's **native web fetch / simple HTTP path first** for cooperative pages.
3. Extract internal links and keep scope bounded.
4. Save output to a file, not the chat transcript.
5. Increase depth only after the first pass looks good.

## Escalation contract

When the crawl path hits blocking or rendering problems:

1. **Try the native path first**
   - native `web_fetch`
   - requests/BeautifulSoup
   - or the chosen crawl tool directly

2. **Escalate to `camofox`** if the problem is:
   - Cloudflare / anti-bot challenge
   - blank or JS-only page content
   - CAPTCHA / verify-you-are-human flow
   - a browser-rendering dependency that breaks the crawl

3. **Escalate to `residential-proxy` only if all of these are true:**
   - `camofox` was actually tried and still failed, or the blocked target is a narrow public HTTP endpoint where a browser step is not sufficient
   - the blocked URLs are high-value
   - the user explicitly approves paid proxy use
   - the proxy scope stays narrow and targeted

Do **not** automatically turn a whole crawl into a proxy-backed crawl.

## Guardrails

- Respect robots.txt and site terms where relevant.
- Keep depth and page count bounded.
- Prefer discovery first, then extraction, instead of blind breadth.
- If only a few pages matter, recover only those pages.
- If the task grows into docs ingestion, switch to `crawl4ai`.
- If the task grows into route discovery, switch to `katana`.

## Output format

Save crawled content in a file with clear source markers, for example:

```markdown
# Website Crawl - example.com

**Seed URL:** https://example.com
**Depth:** 2
**Crawl Date:** YYYY-MM-DD

---

## Page: https://example.com/page1
**Depth:** 0

[content]

---

## Page: https://example.com/page2
**Depth:** 1

[content]
```

## Reporting

```markdown
## Web crawl result
- Seed URL: ...
- Depth / page cap: ...
- Primary method: native fetch | crawl4ai | katana | custom script
- Escalated to camofox: yes/no
- Escalated to residential proxy: yes/no
- Output file: ...
- Notes: ...
```


## Optional local integrations

This public extraction keeps optional Browserless reference material and example scripts for cases where a local or paid browser-automation escalation path is useful. Those extras are optional and require your own `BROWSERLESSIO_API_KEY` if you choose to use them. They are not required for the core skill.
