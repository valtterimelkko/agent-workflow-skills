#!/usr/bin/env python3
"""
Web crawler using Browserless.io cloud browser service.
For sites with JavaScript rendering or bot protection.

Requires BROWSERLESSIO_API_KEY environment variable.
"""

import requests
import json
import os
import sys
from urllib.parse import urljoin, urlparse

# Configuration
BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
MAX_DEPTH = int(sys.argv[2]) if len(sys.argv) > 2 else 1
OUTPUT_FILE = sys.argv[3] if len(sys.argv) > 3 else "crawled-content.md"

API_KEY = os.environ.get('BROWSERLESSIO_API_KEY')
if not API_KEY:
    print("Error: BROWSERLESSIO_API_KEY environment variable not set")
    sys.exit(1)

BROWSERLESS_URL = f"https://production-sfo.browserless.io/function?token={API_KEY}"


def normalize_url(url, base=BASE_URL):
    """Normalize URL for consistent comparison."""
    if not url.startswith('http'):
        url = urljoin(base, url)
    url = url.split('#')[0].split('?')[0].rstrip('/')
    return url


def is_internal(url):
    """Check if URL belongs to the target domain."""
    parsed = urlparse(url)
    base_parsed = urlparse(BASE_URL)
    return parsed.netloc == base_parsed.netloc or parsed.netloc == ''


def is_valid_page(url):
    """Check if URL is a crawlable page."""
    excluded = ('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.zip', '.doc', '.docx',
                '.mp3', '.mp4', '.avi', '.mov', '.css', '.js', '.svg', '.ico')
    return not url.lower().endswith(excluded)


def crawl_page(url):
    """Crawl a single page using Browserless.io"""
    
    puppeteer_code = f'''
export default async function ({{ page }}) {{
  try {{
    // Navigate to page
    const response = await page.goto("{url}", {{ 
      waitUntil: "networkidle2", 
      timeout: 30000 
    }});
    
    // Wait for content to settle
    await new Promise(r => setTimeout(r, 3000));
    
    // Extract data
    const data = await page.evaluate(() => {{
      // Remove script/style elements
      document.querySelectorAll('script, style, nav, footer, iframe').forEach(el => el.remove());
      
      // Get links
      const links = Array.from(document.querySelectorAll('a[href]'))
        .map(a => a.getAttribute('href'))
        .filter(h => h && !h.startsWith('#') && !h.startsWith('javascript:'));
      
      // Get text
      const main = document.querySelector('main') || 
                   document.querySelector('article') || 
                   document.body;
      
      return {{
        title: document.title,
        text: main ? main.innerText : document.body.innerText,
        links: links,
        status: 'success'
      }};
    }});
    
    return {{
      data: data,
      type: "application/json"
    }};
  }} catch (error) {{
    return {{
      data: {{
        title: "",
        text: "Error: " + error.message,
        links: [],
        status: "error: " + error.message
      }},
      type: "application/json"
    }};
  }}
}}
'''
    
    try:
        response = requests.post(
            BROWSERLESS_URL,
            headers={'Content-Type': 'application/javascript'},
            data=puppeteer_code,
            timeout=55  # 60 second limit on free tier
        )
        response.raise_for_status()
        
        result = response.json()
        data = result.get('data', {})
        
        # Process links
        internal_links = set()
        for link in data.get('links', []):
            full_url = normalize_url(link, url)
            if is_internal(full_url) and is_valid_page(full_url):
                internal_links.add(full_url)
        
        return {
            'url': url,
            'text': data.get('text', ''),
            'links': internal_links,
            'success': 'error' not in data.get('status', ''),
            'title': data.get('title', '')
        }
    except Exception as e:
        return {
            'url': url,
            'text': f"Error: {str(e)}",
            'links': set(),
            'success': False,
            'title': ''
        }


def main():
    print(f"Crawling with Browserless.io: {BASE_URL}")
    print(f"Max depth: {MAX_DEPTH}")
    print(f"Output: {OUTPUT_FILE}")
    print()
    
    crawled = {}
    to_crawl = {normalize_url(BASE_URL)}
    depth_map = {normalize_url(BASE_URL): 0}
    
    while to_crawl:
        url = to_crawl.pop()
        current_depth = depth_map[url]
        
        if url in crawled:
            continue
        
        print(f"[Depth {current_depth}] Crawling: {url}")
        
        page_data = crawl_page(url)
        crawled[url] = page_data
        
        if page_data['success']:
            print(f"  ✓ Success: {page_data['title'][:50]}... ({len(page_data['links'])} links)")
            
            # Add new links if we haven't reached max depth
            if current_depth < MAX_DEPTH:
                for link in page_data['links']:
                    if link not in crawled and link not in to_crawl:
                        to_crawl.add(link)
                        depth_map[link] = current_depth + 1
        else:
            print(f"  ✗ Failed: {page_data['text'][:100]}")
    
    print(f"\nCrawled {len(crawled)} pages")
    
    # Write to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# Crawled Content - {BASE_URL}\n\n")
        f.write(f"**Max Depth:** {MAX_DEPTH}\n")
        f.write(f"**Pages Crawled:** {len(crawled)}\n")
        f.write(f"**Method:** Browserless.io\n\n")
        f.write("---\n\n")
        
        for url in sorted(crawled.keys()):
            page = crawled[url]
            f.write(f"## {url}\n\n")
            f.write(f"**Depth:** {depth_map[url]}\n")
            f.write(f"**Status:** {'Success' if page['success'] else 'Failed'}\n")
            if page['title']:
                f.write(f"**Title:** {page['title']}\n")
            f.write("\n")
            
            if page['links']:
                f.write(f"**Links ({len(page['links'])}):**\n")
                for link in sorted(page['links'])[:20]:
                    f.write(f"- {link}\n")
                f.write("\n")
            
            f.write("**Content:**\n\n```\n")
            f.write(page['text'])
            f.write("\n```\n\n---\n\n")
    
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
