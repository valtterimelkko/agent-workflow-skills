---
name: capture-dashboard
description: "Capture authenticated dashboards as screenshots and/or HTML using cookies, with safe same-origin crawling. Use when the goal is archival capture, documentation, or structured snapshotting of dashboard pages. Do not use for arbitrary interactive browsing, existing live-tab reuse, or DOM-debugging workflows; prefer agent-browser or chrome-cdp for those."
---

# Dashboard Capture

Capture authenticated web dashboards as screenshots and HTML files using cookie-based authentication with automatic crawling.

## Prerequisites

### 1. Install cookie-editor Chrome Extension

Install the cookie-editor extension to export cookies from your browser:
- Chrome Web Store: https://chrome.google.com/webstore/search/cookie-editor
- Search for "cookie-editor" or "EditThisCookie"

### 2. Install Dependencies

Required:
- Node.js v16 or higher
- puppeteer: `npm install -g puppeteer`

The capture script uses puppeteer's bundled Chromium browser.

## Quick Start

Basic single-page screenshot capture:

```bash
# 1. Export cookies from your authenticated session
# (Use cookie-editor extension, export as JSON, save as cookies.json)

# 2. Run capture
node scripts/capture.js \
  --cookies cookies.json \
  --url https://dashboard.example.com \
  --mode screenshots
```

## Workflow

### Step 1: Authenticate and Export Cookies

1. Open your browser and navigate to the dashboard
2. Sign in with your credentials
3. Click the cookie-editor extension icon
4. Click "Export" and select "JSON" format
5. Copy the JSON and save to a file (e.g., `cookies.json`)

**Important**: Cookies contain sensitive authentication tokens. Never commit cookie files to version control.

### Step 2: Create Configuration File

For advanced usage with crawling, create a config file:

```json
{
  "cookies": "./cookies.json",
  "landing_page": "https://dashboard.example.com",
  "output_dir": "./dashboard-capture",
  "mode": "both",
  "crawl": {
    "enabled": true,
    "max_depth": 2,
    "same_origin_only": true,
    "exclude_patterns": [
      "*logout*",
      "*signout*",
      "*delete*",
      "*remove*",
      "*destroy*"
    ]
  },
  "screenshot": {
    "full_page": true
  },
  "timeout": 30000
}
```

### Step 3: Run Capture Script

With config file:
```bash
node scripts/capture.js --config config.json
```

With command-line arguments:
```bash
node scripts/capture.js \
  --cookies cookies.json \
  --url https://dashboard.example.com \
  --mode both \
  --output ./output
```

The script will:
1. Load cookies and authenticate
2. Navigate to landing page
3. Capture screenshot/HTML based on mode
4. Extract links from the page
5. Crawl linked pages (if crawling enabled)
6. Save organized output with metadata

### Step 4: Review Output

Output structure:
```
output/
├── screenshots/           # PNG screenshots (full-page)
│   ├── dashboard_example_com.png
│   ├── dashboard_example_com_reports.png
│   └── dashboard_example_com_settings.png
├── html/                  # HTML files
│   ├── dashboard_example_com.html
│   ├── dashboard_example_com_reports.html
│   └── dashboard_example_com_settings.html
└── metadata.json          # Capture metadata and results
```

**metadata.json** contains:
```json
{
  "status": "success",
  "pages_captured": 3,
  "output_directory": "/path/to/output",
  "capture_time": "2026-02-05T12:34:56Z",
  "config": {
    "landing_page": "https://dashboard.example.com",
    "mode": "both",
    "max_depth": 2
  },
  "pages": [
    {
      "url": "https://dashboard.example.com",
      "depth": 0,
      "screenshot": {
        "filename": "dashboard_example_com.png",
        "path": "/path/to/output/screenshots/dashboard_example_com.png"
      },
      "html": {
        "filename": "dashboard_example_com.html",
        "path": "/path/to/output/html/dashboard_example_com.html"
      },
      "timestamp": "2026-02-05T12:34:56Z"
    }
  ]
}
```

## Configuration Reference

### Required Parameters

| Parameter | Description | Example |
|-----------|-------------|---------|
| `cookies` | Path to cookie JSON file | `"./cookies.json"` |
| `landing_page` | Starting URL for capture | `"https://dashboard.example.com"` |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `output_dir` | string | `"./output"` | Output directory path |
| `mode` | string | `"both"` | Capture mode: `"screenshots"`, `"html"`, or `"both"` |
| `timeout` | number | `30000` | Page load timeout in milliseconds |

### Crawl Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `crawl.enabled` | boolean | `true` | Enable automatic crawling |
| `crawl.max_depth` | number | `2` | Maximum crawl depth (0 = landing page only) |
| `crawl.same_origin_only` | boolean | `true` | Only follow same-origin links |
| `crawl.exclude_patterns` | array | `["*logout*", ...]` | URL patterns to exclude |

### Screenshot Configuration

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `screenshot.full_page` | boolean | `true` | Capture full scrollable page |
| `screenshot.format` | string | `"png"` | Screenshot format (png) |

## Command-Line Options

```bash
node scripts/capture.js [OPTIONS]

OPTIONS:
  --config FILE         Load configuration from JSON file
  --cookies FILE        Path to cookie JSON file
  --url URL             Landing page URL
  --mode MODE           Capture mode: screenshots, html, or both
  --output DIR          Output directory
  --max-depth N         Maximum crawl depth
  --no-crawl            Disable crawling
  --help, -h            Show help message
```

## Examples

### Example 1: Screenshot-Only Capture

Capture screenshots of a single dashboard page:

```bash
node scripts/capture.js \
  --cookies cookies.json \
  --url https://dashboard.example.com \
  --mode screenshots \
  --no-crawl
```

### Example 2: Full Dashboard Crawl

Capture both screenshots and HTML, crawling up to 2 levels deep:

```json
{
  "cookies": "./cookies.json",
  "landing_page": "https://dashboard.example.com",
  "mode": "both",
  "crawl": {
    "enabled": true,
    "max_depth": 2
  }
}
```

```bash
node scripts/capture.js --config config.json
```

### Example 3: HTML Documentation

Capture HTML only for documentation purposes:

```bash
node scripts/capture.js \
  --cookies cookies.json \
  --url https://dashboard.example.com \
  --mode html \
  --output ./docs/dashboard-html
```

### Example 4: Custom Exclude Patterns

Exclude additional URL patterns:

```json
{
  "cookies": "./cookies.json",
  "landing_page": "https://dashboard.example.com",
  "crawl": {
    "exclude_patterns": [
      "*logout*",
      "*delete*",
      "*edit*",
      "*admin*"
    ]
  }
}
```

## Troubleshooting

### Cookies Not Working / Authentication Failed

**Symptom**: Script reports "Authentication failed - redirected to login page"

**Solutions**:
1. Re-export cookies - they may have expired
2. Ensure you export cookies from the exact domain (not a subdomain)
3. Check that cookies include authentication tokens (look for session IDs)
4. Try exporting cookies immediately after logging in

See [references/troubleshooting.md](references/troubleshooting.md) for detailed cookie export instructions.

### Missing Dependencies

**Symptom**: `puppeteer not found` error

**Solution**:
```bash
npm install -g puppeteer
```

If that fails, try local installation:
```bash
npm install puppeteer
# Then use: node_modules/.bin/node scripts/capture.js
```

### Pages Not Loading / Timeout Errors

**Symptom**: Page navigation times out

**Solutions**:
1. Increase timeout in config: `"timeout": 60000` (60 seconds)
2. Check network connectivity
3. Verify the URL is accessible
4. Try disabling same-origin restriction temporarily for testing

### Links Not Being Followed

**Symptom**: Only landing page captured, no crawling

**Solutions**:
1. Check that `crawl.enabled` is `true`
2. Verify `max_depth` is greater than 0
3. Check that links are same-origin (if `same_origin_only: true`)
4. Review exclude patterns - they may be too broad

### For More Help

See detailed troubleshooting guide: [references/troubleshooting.md](references/troubleshooting.md)

## Notes

**Cookie Expiration**: Cookies expire based on server settings. If capture fails with authentication errors, re-export fresh cookies.

**Same-Origin Restriction**: By default, only links within the same domain are followed. This prevents accidentally crawling external sites.

**Depth Limit**: Maximum depth of 2 prevents excessive crawling. Depth 0 = landing page, Depth 1 = direct links, Depth 2 = links from depth 1 pages.

**Safety Filters**: Exclude patterns prevent the script from clicking logout, delete, or other dangerous actions. These patterns use wildcard matching (`*logout*` matches any URL containing "logout").

**File Naming**: URLs are converted to safe filenames by replacing non-alphanumeric characters with underscores. Long URLs are truncated to 200 characters.

**Graceful Degradation**: If a single page fails to capture, the script continues with other pages and reports partial success.
