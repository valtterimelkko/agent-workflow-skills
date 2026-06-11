# Jina AI Reader Reference

Jina AI Reader is a **free** service that converts any URL to LLM-friendly markdown. It uses Puppeteer and headless Chrome to render JavaScript and extract clean content.

## Quick Start

Simply prepend `https://r.jina.ai/` to any URL:

```
https://r.jina.ai/https://example.com
```

**No API key required for basic usage!**

## API Endpoint

**Base URL:** `https://r.jina.ai/`

**Method:** GET (simple) or POST (for hash-based routing)

## Basic Usage

### Simple GET Request

```python
import requests

url = "https://example.com"
response = requests.get(f"https://r.jina.ai/{url}", timeout=30)

print(response.text)  # Clean markdown content
```

### JSON Response

```python
import requests

url = "https://example.com"
response = requests.get(
    f"https://r.jina.ai/{url}",
    headers={"Accept": "application/json"},
    timeout=30
)

data = response.json()
# Returns:
# {
#   "url": "https://example.com",
#   "title": "Page Title",
#   "content": "Markdown content...",
#   "timestamp": "2024-01-15T10:30:00Z"  # if available
# }
```

### POST for Hash-Based Routing (SPAs)

For Single Page Applications with hash-based routing (e.g., `/#/route`):

```bash
curl -X POST 'https://r.jina.ai/' \
  -d 'url=https://example.com/#/route'
```

```python
import requests

response = requests.post(
    'https://r.jina.ai/',
    data={'url': 'https://example.com/#/route'},
    timeout=30
)
```

## Request Headers

Control Reader behavior using headers:

| Header | Description | Example |
|--------|-------------|---------|
| `Accept` | Response format | `application/json`, `text/event-stream` |
| `x-timeout` | Max wait time (seconds) | `30` |
| `x-target-selector` | Extract specific element | `article`, `.content` |
| `x-wait-for-selector` | Wait for element before extract | `#loaded`, `.ready` |
| `x-respond-with` | Output format | `markdown`, `html`, `text`, `screenshot` |
| `x-no-cache` | Bypass cache | `true` |
| `x-cache-tolerance` | Accept cached content if newer than (seconds) | `3600` |
| `x-with-generated-alt` | Caption images | `true` |
| `x-set-cookie` | Forward cookies | `session=abc123` |
| `x-proxy-url` | Use proxy | `http://proxy:8080` |
| `x-forwarded-for` | Set origin IP | `1.2.3.4` |

### Target Specific Elements

```python
import requests

headers = {
    "x-target-selector": "article",  # Only extract <article> element
    "x-wait-for-selector": ".content-loaded"  # Wait for this element
}

response = requests.get(
    "https://r.jina.ai/https://example.com",
    headers=headers,
    timeout=30
)
```

### Wait for Dynamic Content

```python
import requests

# Wait up to 30 seconds for content to load
headers = {
    "x-timeout": "30",
    "x-wait-for-selector": ".dynamic-content"
}

response = requests.get(
    "https://r.jina.ai/https://spa-example.com",
    headers=headers,
    timeout=35
)
```

### Get Screenshot Instead of Text

```python
import requests

headers = {
    "x-respond-with": "screenshot"
}

response = requests.get(
    "https://r.jina.ai/https://example.com",
    headers=headers,
    timeout=30
)

# Returns URL to screenshot image
screenshot_url = response.text
```

### Custom Output Formats

```python
import requests

# HTML instead of markdown
response = requests.get(
    "https://r.jina.ai/https://example.com",
    headers={"x-respond-with": "html"},
    timeout=30
)
html = response.text

# Plain text only
response = requests.get(
    "https://r.jina.ai/https://example.com",
    headers={"x-respond-with": "text"},
    timeout=30
)
text = response.text
```

### Image Captioning

Enable automatic image captioning with VLM (Vision Language Model):

```python
import requests

headers = {
    "x-with-generated-alt": "true"
}

response = requests.get(
    "https://r.jina.ai/https://example.com",
    headers=headers,
    timeout=60  # Captioning takes longer
)

# Images will have alt text like:
# ![Image 1: A photo of a mountain landscape](https://example.com/img.jpg)
```

### Authenticated Content

Forward cookies for authenticated pages:

```python
import requests

headers = {
    "x-set-cookie": "session=abc123; auth_token=xyz789"
}

response = requests.get(
    "https://r.jina.ai/https://private.example.com",
    headers=headers,
    timeout=30
)
```

## Streaming Mode

For large pages or when standard mode returns incomplete content:

```python
import requests

headers = {
    "Accept": "text/event-stream",
    "x-no-cache": "true"
}

response = requests.get(
    "https://r.jina.ai/https://large-example.com",
    headers=headers,
    stream=True,
    timeout=60
)

# Each chunk contains progressively more complete content
full_content = ""
for line in response.iter_lines():
    if line:
        chunk = line.decode('utf-8')
        if chunk.startswith('data: '):
            full_content = chunk[6:]  # Last chunk is most complete

print(full_content)
```

**Note:** Unlike LLM streaming, each chunk in Reader streaming contains the full content up to that point, with later chunks being more complete.

## Web Search (s.jina.ai)

Search the web and get top 5 results with full content:

```python
import requests
from urllib.parse import quote

query = "latest AI developments"
encoded_query = quote(query)

response = requests.get(
    f"https://s.jina.ai/{encoded_query}",
    headers={"Accept": "application/json"},
    timeout=30
)

results = response.json()
# Returns list of 5 items:
# [
#   {
#     "title": "...",
#     "content": "...",
#     "url": "..."
#   },
#   ...
# ]
```

### Site-Specific Search

```python
import requests
from urllib.parse import quote

query = "API documentation"

# Search only on specific sites
response = requests.get(
    f"https://s.jina.ai/{quote(query)}?site=docs.example.com&site=api.example.com",
    timeout=30
)
```

## Python Integration Examples

### Basic Crawler with Jina Reader

```python
import requests
from urllib.parse import urljoin, urlparse
import time

def crawl_with_jina(start_url, max_depth=1):
    """Simple crawler using Jina AI Reader."""
    
    crawled = {}
    to_crawl = {start_url}
    depth_map = {start_url: 0}
    
    while to_crawl:
        url = to_crawl.pop()
        current_depth = depth_map[url]
        
        if url in crawled or current_depth > max_depth:
            continue
        
        try:
            response = requests.get(
                f"https://r.jina.ai/{url}",
                headers={"Accept": "application/json"},
                timeout=30
            )
            data = response.json()
            
            crawled[url] = {
                'title': data.get('title', ''),
                'content': data.get('content', ''),
                'depth': current_depth
            }
            
            print(f"✓ Crawled: {data.get('title', url)}")
            
            # Note: Jina Reader doesn't return links
            # You'd need to parse content or use other methods for link extraction
            
        except Exception as e:
            print(f"✗ Failed {url}: {e}")
        
        time.sleep(1)  # Be polite
    
    return crawled
```

### With Error Handling and Retries

```python
import requests
import time

def fetch_with_jina(url, retries=3, timeout=30):
    """Fetch URL with retry logic."""
    
    headers = {
        "Accept": "application/json",
        "x-no-cache": "true"  # Fresh content
    }
    
    for attempt in range(retries):
        try:
            response = requests.get(
                f"https://r.jina.ai/{url}",
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Check if content was actually extracted
            if not data.get('content') or len(data['content']) < 100:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                    continue
            
            return data
            
        except requests.exceptions.Timeout:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
                continue
            raise
    
    return None
```

### SPA with Dynamic Content

```python
import requests

def crawl_spa(url, wait_selector=None, timeout=30):
    """Crawl Single Page Application with dynamic content."""
    
    headers = {
        "Accept": "application/json",
        "x-timeout": str(timeout)
    }
    
    if wait_selector:
        headers["x-wait-for-selector"] = wait_selector
    
    response = requests.get(
        f"https://r.jina.ai/{url}",
        headers=headers,
        timeout=timeout + 5
    )
    
    return response.json()

# Usage
result = crawl_spa(
    "https://react-app.example.com",
    wait_selector=".content-loaded",
    timeout=30
)
```

## Handling Common Challenges

### JavaScript-Rendered Content

Jina Reader handles JavaScript automatically using Puppeteer. For sites with delayed loading:

```python
import requests

headers = {
    "x-timeout": "30",  # Wait up to 30 seconds
    "x-wait-for-selector": ".loaded"  # Wait for specific element
}

response = requests.get(
    "https://r.jina.ai/https://js-heavy-site.com",
    headers=headers,
    timeout=35
)
```

### Bot Detection

Jina Reader uses cloud infrastructure which may bypass basic bot detection. If blocked:

1. Try with `x-no-cache: true` for fresh session
2. Use `x-proxy-url` header with rotating proxies
3. Escalate to Browserless.io for advanced stealth

### Rate Limiting

Free tier has rate limits. To avoid hitting them:

```python
import time
import random

# Add delays between requests
time.sleep(1 + random.random() * 2)

# Or use exponential backoff on failures
```

### Incomplete Content

If content appears truncated:

```python
import requests

# Use streaming mode for large pages
headers = {
    "Accept": "text/event-stream",
    "x-no-cache": "true"
}

response = requests.get(
    "https://r.jina.ai/https://large-article.com",
    headers=headers,
    stream=True,
    timeout=60
)

# Read final chunk for most complete content
final_content = ""
for line in response.iter_lines():
    if line:
        decoded = line.decode('utf-8')
        if decoded.startswith('data: '):
            final_content = decoded[6:]
```

## Rate Limits and Pricing

| Tier | Rate Limit | Cost |
|------|------------|------|
| Free (no API key) | Limited | Free |
| Free (with API key) | Higher limits | Free |
| Paid | Higher limits | Check jina.ai/pricing |

Get API key at: https://jina.ai/api-dashboard

## Limitations

1. **No link extraction** - Returns content only, not page links
2. **No CAPTCHA solving** - May fail on sites with active CAPTCHA
3. **Rate limits** - Free tier has limits
4. **No session persistence** - Each request is independent
5. **Limited control** - Less flexible than Browserless.io

## When to Use Jina Reader vs Browserless.io

### Use Jina Reader when:
- Need quick, free content extraction
- Site has JavaScript but light/no protection
- Want clean markdown without setup
- Simple one-off extractions
- Budget constraints

### Use Browserless.io when:
- Site has advanced protection (Cloudflare, reCAPTCHA)
- Need session persistence across pages
- Require proxy rotation
- Need CAPTCHA solving
- Require full browser control

## Resources

- GitHub: https://github.com/jina-ai/reader
- Documentation: https://jina.ai/reader
- API Dashboard: https://jina.ai/api-dashboard
- Interactive Playground: https://jina.ai/reader#apiform
