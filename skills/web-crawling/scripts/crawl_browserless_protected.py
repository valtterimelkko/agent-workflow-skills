#!/usr/bin/env python3
"""
Web crawler using Browserless.io BrowserQL API for persistently protected sites.
Handles Cloudflare, advanced bot detection, CAPTCHAs, and TLS fingerprinting.

Requires BROWSERLESSIO_API_KEY environment variable.

Features:
- Built-in stealth mode (bypasses TLS/JA3 fingerprinting)
- Human-like behavior (mouse movements, delays)
- Session persistence for multi-page crawling
- Automatic CAPTCHA/Turnstile handling
"""

import requests
import json
import os
import sys
import time
import random
from urllib.parse import urljoin, urlparse

# Configuration
BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
MAX_DEPTH = int(sys.argv[2]) if len(sys.argv) > 2 else 1
OUTPUT_FILE = sys.argv[3] if len(sys.argv) > 3 else "crawled-content.md"
SESSION_FILE = sys.argv[4] if len(sys.argv) > 4 else ".browserless_session.json"

API_KEY = os.environ.get('BROWSERLESSIO_API_KEY')
if not API_KEY:
    print("Error: BROWSERLESSIO_API_KEY environment variable not set")
    sys.exit(1)

BROWSERLESS_URL = f"https://production-sfo.browserless.io/browserql?token={API_KEY}"


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


def load_session():
    """Load previous session cookies if available."""
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return {}
    return {}


def save_session(cookies, local_storage=None):
    """Save session for reuse."""
    session = {}
    if cookies:
        session['cookies'] = cookies
    if local_storage:
        session['localStorage'] = local_storage
    
    try:
        with open(SESSION_FILE, 'w') as f:
            json.dump(session, f)
    except Exception as e:
        print(f"  Warning: Could not save session: {e}")


def crawl_page_browserql(url, session=None):
    """
    Crawl a single page using Browserless BrowserQL API.
    Uses stealth mode and human-like behavior for protected sites.
    """
    
    # GraphQL query with stealth and human-like options
    query = """
    query CrawlProtected($url: String!, $cookies: [CookieInput]) {
      goto(url: $url, options: { 
        stealth: true, 
        humanlike: true,
        timeout: 60000,
        cookies: $cookies
      }) {
        waitForTimeout(duration: 5000) {
          title
          text
          links
          url
          cookies {
            name
            value
            domain
            path
          }
        }
      }
    }
    """
    
    variables = {
        "url": url,
        "cookies": session.get('cookies', []) if session else []
    }
    
    try:
        response = requests.post(
            BROWSERLESS_URL,
            json={"query": query, "variables": variables},
            timeout=70
        )
        response.raise_for_status()
        
        result = response.json()
        
        if result.get('errors'):
            error_msg = result['errors'][0].get('message', 'Unknown error')
            return {
                'url': url,
                'text': f"BrowserQL Error: {error_msg}",
                'links': set(),
                'success': False,
                'title': '',
                'cookies': []
            }
        
        data = result.get('data', {}).get('goto', {}).get('waitForTimeout', {})
        
        if not data:
            return {
                'url': url,
                'text': "Error: No data returned from BrowserQL",
                'links': set(),
                'success': False,
                'title': '',
                'cookies': []
            }
        
        # Process links - convert to internal format
        raw_links = data.get('links', [])
        internal_links = set()
        for link in raw_links:
            if isinstance(link, str):
                full_url = normalize_url(link, url)
            elif isinstance(link, dict) and 'href' in link:
                full_url = normalize_url(link['href'], url)
            else:
                continue
                
            if is_internal(full_url) and is_valid_page(full_url):
                internal_links.add(full_url)
        
        return {
            'url': url,
            'text': data.get('text', ''),
            'links': internal_links,
            'success': True,
            'title': data.get('title', ''),
            'cookies': data.get('cookies', [])
        }
        
    except requests.exceptions.Timeout:
        return {
            'url': url,
            'text': "Error: Request timeout (70s)",
            'links': set(),
            'success': False,
            'title': '',
            'cookies': []
        }
    except Exception as e:
        return {
            'url': url,
            'text': f"Error: {str(e)}",
            'links': set(),
            'success': False,
            'title': '',
            'cookies': []
        }


def crawl_page_function_api(url, session=None):
    """
    Fallback to Function API if BrowserQL fails.
    Includes advanced stealth configuration.
    """
    
    cookies_json = json.dumps(session.get('cookies', [])) if session else '[]'
    
    puppeteer_code = f'''
export default async function ({{ page, context }}) {{
  try {{
    // Restore session cookies
    const cookies = {cookies_json};
    if (cookies && cookies.length > 0) {{
      await page.setCookie(...cookies);
    }}
    
    // Stealth configuration
    await page.setViewport({{ 
      width: 1920, 
      height: 1080,
      deviceScaleFactor: 1
    }});
    
    await page.setUserAgent(
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    );
    
    // Inject stealth scripts
    await page.evaluateOnNewDocument(() => {{
      Object.defineProperty(navigator, 'webdriver', {{ get: () => undefined }});
      Object.defineProperty(navigator, 'plugins', {{ get: () => [1, 2, 3, 4, 5] }});
      Object.defineProperty(navigator, 'languages', {{ get: () => ['en-US', 'en'] }});
    }});
    
    // Navigate
    const response = await page.goto("{url}", {{ 
      waitUntil: "networkidle2", 
      timeout: 60000 
    }});
    
    // Wait with random delay for human-like behavior
    await new Promise(r => setTimeout(r, 5000 + Math.floor(Math.random() * 3000)));
    
    // Check for CAPTCHA
    const isCaptcha = await page.$('iframe[src*="captcha"], iframe[src*="turnstile"], .cf-turnstile, #cf-turnstile');
    
    if (isCaptcha) {{
      // Wait longer for CAPTCHA to be solved or pass automatically
      await new Promise(r => setTimeout(r, 15000));
    }}
    
    // Extract data
    const data = await page.evaluate(() => {{
      document.querySelectorAll('script, style, nav, footer, iframe').forEach(el => el.remove());
      
      const links = Array.from(document.querySelectorAll('a[href]'))
        .map(a => a.getAttribute('href'))
        .filter(h => h && !h.startsWith('#') && !h.startsWith('javascript:'));
      
      const main = document.querySelector('main') || 
                   document.querySelector('article') || 
                   document.body;
      
      return {{
        title: document.title,
        text: main ? main.innerText : document.body.innerText,
        links: links,
        url: window.location.href
      }};
    }});
    
    // Save cookies
    const newCookies = await page.cookies();
    
    return {{
      data: {{
        ...data,
        cookies: newCookies,
        hasCaptcha: !!isCaptcha
      }},
      type: "application/json"
    }};
  }} catch (error) {{
    return {{
      data: {{
        title: "",
        text: "Error: " + error.message,
        links: [],
        cookies: [],
        hasCaptcha: false
      }},
      type: "application/json"
    }};
  }}
}}
'''
    
    try:
        response = requests.post(
            f"https://production-sfo.browserless.io/function?token={API_KEY}",
            headers={'Content-Type': 'application/javascript'},
            data=puppeteer_code,
            timeout=70
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
            'success': 'Error:' not in data.get('text', ''),
            'title': data.get('title', ''),
            'cookies': data.get('cookies', [])
        }
        
    except Exception as e:
        return {
            'url': url,
            'text': f"Error: {str(e)}",
            'links': set(),
            'success': False,
            'title': '',
            'cookies': []
        }


def crawl_page(url, session=None, use_browserql=True):
    """Crawl a page using the best available method."""
    
    if use_browserql:
        result = crawl_page_browserql(url, session)
        if result['success']:
            return result
        print(f"  BrowserQL failed, trying Function API...")
    
    return crawl_page_function_api(url, session)


def main():
    print(f"Crawling with Browserless.io (Protected Mode): {BASE_URL}")
    print(f"Max depth: {MAX_DEPTH}")
    print(f"Output: {OUTPUT_FILE}")
    print(f"Session file: {SESSION_FILE}")
    print()
    
    # Load previous session
    session = load_session()
    if session:
        print(f"Loaded session with {len(session.get('cookies', []))} cookies")
    
    crawled = {}
    to_crawl = {normalize_url(BASE_URL)}
    depth_map = {normalize_url(BASE_URL): 0}
    
    pages_with_captcha = 0
    
    while to_crawl:
        url = to_crawl.pop()
        current_depth = depth_map[url]
        
        if url in crawled:
            continue
        
        print(f"[Depth {current_depth}] Crawling: {url}")
        
        # Try BrowserQL first, fall back to Function API
        page_data = crawl_page(url, session, use_browserql=True)
        crawled[url] = page_data
        
        # Save session cookies for next request
        if page_data.get('cookies'):
            save_session(page_data['cookies'])
            session = load_session()
        
        if page_data['success']:
            print(f"  ✓ Success: {page_data['title'][:60]}... ({len(page_data['links'])} links)")
            
            # Track CAPTCHA encounters
            if 'captcha' in page_data.get('text', '').lower() or page_data.get('hasCaptcha'):
                pages_with_captcha += 1
            
            # Add new links if we haven't reached max depth
            if current_depth < MAX_DEPTH:
                for link in page_data['links']:
                    if link not in crawled and link not in to_crawl:
                        to_crawl.add(link)
                        depth_map[link] = current_depth + 1
        else:
            print(f"  ✗ Failed: {page_data['text'][:100]}")
        
        # Random delay between requests to avoid rate limiting
        if to_crawl:
            delay = 2 + random.random() * 3  # 2-5 seconds
            time.sleep(delay)
    
    print(f"\n{'='*50}")
    print(f"Crawled {len(crawled)} pages")
    print(f"Pages with CAPTCHA: {pages_with_captcha}")
    print(f"Session saved to: {SESSION_FILE}")
    
    # Write to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# Crawled Content - {BASE_URL}\n\n")
        f.write(f"**Max Depth:** {MAX_DEPTH}\n")
        f.write(f"**Pages Crawled:** {len(crawled)}\n")
        f.write(f"**Method:** Browserless.io (Protected Mode)\n")
        f.write(f"**CAPTCHA Encounters:** {pages_with_captcha}\n")
        f.write(f"**Session File:** {SESSION_FILE}\n\n")
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
