---
name: webfetch-skill
description: "Fetch and analyze web content using a specialised extraction workflow that converts HTML to clean markdown, extracts main article content, handles images and links, and provides AI analysis. Use this when you need cleaner page extraction than a raw fetch, when comparing a small set of URLs, or when the user asks to fetch, extract, analyse, summarise, or compare web pages. Prefer native web_fetch for straightforward cooperative pages; if the target URL is blocked by anti-bot or JS-only rendering, escalate the blocked URL to camofox before considering residential-proxy."
license: Complete terms in LICENSE.txt
---

# Web Fetch

Fetch and analyze web content by calling a specialized sub-agent that uses the webfetch script.

Use this as a **clean single-page / few-page extraction tier**:
- prefer native `web_fetch` for quick cooperative pages
- prefer this skill when you want cleaner markdown extraction, comparison across a few URLs, or extraction from article-like pages
- if the page is challenge-blocked or JS-only, recover that URL with `camofox` before escalating to any paid proxy path

## Quick Start

To fetch and analyze web content, invoke the webfetch sub-agent:

**Fetch a single URL:**
> Fetch and summarize: https://example.com

**Fetch multiple URLs (max 5):**
> Fetch and compare: https://example.com and https://example2.com

**Analyze specific content:**
> What are the main points on: https://example.com/article

**Extract specific information:**
> Extract all email addresses from: https://example.com/contact

The sub-agent will:
1. Fetch the URL(s) using the webfetch script
2. Read the extracted markdown content
3. Provide AI analysis based on your prompt

## Escalation contract

Keep the order narrow and cheap:

1. Try native `web_fetch` or this script workflow first.
2. If the target page is blocked by Cloudflare, challenge pages, or blank JS rendering, retry that URL with `camofox`.
3. If `camofox` also fails and the blocked URL is genuinely important, ask before using `residential-proxy`.

Do **not** automatically turn a small fetch task into a proxy-backed workflow.

## Prerequisites

The webfetch script requires these Python packages:

```bash
pip install --break-system-packages trafilatura requests beautifulsoup4
```

**trafilatura** - Main content extraction and HTML→markdown conversion
**requests** - HTTP client for fetching URLs
**beautifulsoup4** - Link and image extraction

## How It Works

1. **Skill triggers** when you ask to fetch web content
2. **Sub-agent invoked** via Task tool
3. **Script executes** webfetch.py to fetch and extract content
4. **Sub-agent analyzes** the markdown output and provides intelligent response
5. **Results returned** with summaries, extractions, or answers

This approach avoids external APIs and local LLMs while providing intelligent analysis.

## Sub-Agent Instructions (READ CAREFULLY)

**CRITICAL: When you are the sub-agent for this skill, you MUST follow these instructions exactly:**

### TOOL RESTRICTIONS
- **DO NOT USE ANY MCP TOOLS** - Specifically: NO zai-web-reader, NO zai-vision tools, NO webfetch, NO webfetch_webReader
- **DO NOT USE the `webfetch` function** - Use the Python script instead
- **ONLY USE THESE TOOLS:** Bash tool (to run python3) and Read tool (to read markdown files)

### EXACT STEPS TO FOLLOW

When asked to fetch web content, follow this EXACT process:

**Step 1: Run the webfetch.py script**
```bash
python3 ./skills/webfetch-skill/scripts/webfetch.py --url "URL_HERE" --output ./tmp/webfetch-skill/FILENAME.md
```

For multiple URLs (max 5), run separately for each URL or use --url multiple times:
```bash
python3 ./skills/webfetch-skill/scripts/webfetch.py --url "URL1" --url "URL2" --url "URL3" --output ./tmp/webfetch-skill/output.md
```

**Step 2: Read the generated markdown file(s)**
```bash
Use the Read tool to read: ./tmp/webfetch-skill/FILENAME.md
```

**Step 3: Analyze the content**
- Read and understand the markdown content
- Provide analysis, summary, or extraction based on the user's request
- Answer any questions about the fetched content

**Step 4: Return results**
- Provide your analysis to the main agent
- Do NOT include tool execution details unless asked

### SCRIPT LOCATION
- Full path: `./skills/webfetch-skill/scripts/webfetch.py`
- This script uses trafilatura for HTML→markdown conversion
- Cache is stored in: `./tmp/webfetch-skill/`

### ERROR HANDLING
- If the script fails, run it again with --no-cache flag
- If timeout occurs, add --timeout 30 or --timeout 60
- Report errors to the user with the exact error message

### TEMPLATE PROMPT FOR MAIN AGENT
When invoking this sub-agent, use a prompt like:
```
Fetch and analyze content from these URLs using the webfetch script:
- https://example.com/page1
- https://example.com/page2

DO NOT use MCP tools. Use ONLY the python3 script at ./skills/webfetch-skill/scripts/webfetch.py.
Save output to ./tmp/webfetch-skill/ and read the files.
```

## Using the Script Directly

You can also run the webfetch script directly without the sub-agent:

```bash
# Basic fetch
python3 scripts/webfetch.py --url "https://example.com"

# Multiple URLs
python3 scripts/webfetch.py --url "https://example.com" --url "https://example2.com"

# Disable cache
python3 scripts/webfetch.py --url "https://example.com" --no-cache

# Set timeout
python3 scripts/webfetch.py --url "https://example.com" --timeout 30

# Save to file
python3 scripts/webfetch.py --url "https://example.com" --output content.md
```

## Script Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--url`, `-u` | Yes | - | URL to fetch (can be specified multiple times, max 5) |
| `--cache`, `-c` | No | true | Enable/disable 15-minute cache |
| `--no-cache` | No | - | Disable caching (alias for --cache=false) |
| `--timeout`, `-t` | No | 10 | Request timeout in seconds |
| `--output`, `-o` | No | - | Save output to file instead of stdout |

## Features

### Main Content Extraction

Trafilatura automatically identifies the main article body and removes boilerplate (navigation, ads, footers).

### Image Handling

Extracts up to 10 images with:
- Alt text (when available)
- Absolute URLs
- Markdown format: `![alt text](url)`

### Link Summary

Extracts up to 20 links with:
- Link text
- Absolute URLs
- Markdown format: `[text](url)`

### Caching

15-minute file-based cache in `./tmp/webfetch-skill/`:
- Cache key based on URL hash
- Automatic cache invalidation
- Improves performance for repeated requests

### URL Handling

- **HTTP→HTTPS**: Automatically upgrades HTTP URLs
- **Redirects**: Follows redirects automatically
- **User-Agent**: Uses realistic browser headers

## Output Format

When running the script directly, output is in markdown:

```markdown
# https://example.com
_(from cache)_

## Content

Main content extracted from the page...

## Images
- **Image Alt**: https://example.com/image.jpg

## Links
- [Link Text](https://example.com/page)
```

When using the sub-agent, you get AI analysis instead of raw content.

## Limitations

**Cannot access:**
- Authenticated/private URLs (Google Docs, Confluence, Jira, etc.)
- Sites requiring JavaScript rendering
- Sites with CAPTCHAs
- Rate-limited or blocked sites

**Potential issues:**
- Sites with anti-scraping measures
- Paywalled content
- Dynamic content loaded after page load
- Very large pages (may truncate)

## Error Handling

The script handles common errors gracefully:

- **404 Not Found**: Returns error message
- **500 Server Error**: Returns error message
- **Timeout**: Returns timeout error
- **Connection Error**: Returns connection error
- **Invalid URL**: Returns invalid URL error

Errors are included in markdown output so sub-agent can inform you.

## Best Practices

**For optimal results:**

1. **Use sub-agent** for intelligent analysis instead of reading raw content
2. **Provide specific prompts** rather than generic "fetch" requests
3. **Enable cache** (default) for performance on repeated requests
4. **Use --no-cache** when you need fresh content
5. **Set longer timeout** for slow-loading sites (e.g., `--timeout 30`)
6. **Limit URLs** when fetching multiple sites (max 5 enforced)

**Example effective prompts:**
- "Summarize the key takeaways from: https://example.com/article"
- "Extract all pricing information from: https://example.com/pricing"
- "What are the main sections in: https://example.com/docs"
- "Compare the content of these two pages: [url1] [url2]"

## Resources

This skill includes:

**scripts/webfetch.py** - Main fetch script with content extraction
