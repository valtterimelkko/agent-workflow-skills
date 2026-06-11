#!/usr/bin/env python3
"""
Web crawler using Jina AI Reader API.
Converts any URL to clean markdown - FREE, no API key needed!

Features:
- JavaScript rendering handled automatically
- Clean markdown output
- Image captioning support
- Handles many SPA (Single Page Application) sites

Note: Jina Reader extracts content well but doesn't return links.
This script parses links from the source URL separately.

Usage:
    python crawl_jina.py <url> [max_depth] [output_file]
    
Example:
    python crawl_jina.py https://example.com 1 output.md
"""

import requests
import re
import sys
import time
import random
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

# Configuration
BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
MAX_DEPTH = int(sys.argv[2]) if len(sys.argv) > 2 else 1
OUTPUT_FILE = sys.argv[3] if len(sys.argv) > 3 else "crawled-content.md"

# Request headers for link extraction (not via Jina)
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
}

# Jina Reader API
JINA_BASE = "https://r.jina.ai"


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


def extract_links_from_html(url):
    """
    Extract internal links from a page using requests + BeautifulSoup.
    Used alongside Jina for content extraction.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        links = set()
        for anchor in soup.find_all('a', href=True):
            href = anchor['href']
            full_url = normalize_url(urljoin(url, href))
            if is_internal(full_url) and is_valid_page(full_url):
                links.add(full_url)
        
        return links
    except Exception:
        return set()


def extract_links_from_markdown(markdown):
    """Extract links from markdown content as fallback."""
    # Match [text](url) markdown links
    pattern = r'\[([^\]]+)\]\(([^)]+)\)'
    matches = re.findall(pattern, markdown)
    
    links = set()
    for _, href in matches:
        # Skip anchor-only links
        if href.startswith('#') or href.startswith('javascript:'):
            continue
        # Skip external links that aren't http/https
        if href.startswith('http'):
            full_url = normalize_url(href)
            if is_internal(full_url):
                links.add(full_url)
        else:
            # Relative URL
            links.add(normalize_url(href))
    
    return links


def crawl_page_jina(url, use_streaming=False, timeout=30):
    """
    Crawl a page using Jina AI Reader.
    Returns content and extracted links.
    """
    jina_url = f"{JINA_BASE}/{url}"
    
    headers = {
        "Accept": "application/json",
        "x-no-cache": "true"  # Fresh content
    }
    
    try:
        if use_streaming:
            # Use streaming mode for large/complex pages
            headers["Accept"] = "text/event-stream"
            
            response = requests.get(
                jina_url,
                headers=headers,
                stream=True,
                timeout=timeout + 10
            )
            response.raise_for_status()
            
            # Get final (most complete) chunk
            final_content = ""
            final_data = None
            
            for line in response.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith('data: '):
                        data_str = decoded[6:]
                        try:
                            import json
                            final_data = json.loads(data_str)
                        except json.JSONDecodeError:
                            final_content = data_str
            
            if final_data:
                return {
                    'url': url,
                    'title': final_data.get('title', ''),
                    'content': final_data.get('content', ''),
                    'links': set(),  # Would need separate extraction
                    'success': True
                }
            else:
                return {
                    'url': url,
                    'title': '',
                    'content': final_content,
                    'links': set(),
                    'success': bool(final_content)
                }
        else:
            # Standard JSON mode
            response = requests.get(
                jina_url,
                headers=headers,
                timeout=timeout
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Extract links from markdown content
            md_links = extract_links_from_markdown(data.get('content', ''))
            
            # Also try to get links from HTML
            html_links = extract_links_from_html(url)
            
            all_links = md_links.union(html_links)
            
            return {
                'url': url,
                'title': data.get('title', ''),
                'content': data.get('content', ''),
                'links': all_links,
                'success': True
            }
            
    except requests.exceptions.Timeout:
        return {
            'url': url,
            'title': '',
            'content': f"Error: Timeout ({timeout}s)",
            'links': set(),
            'success': False
        }
    except Exception as e:
        return {
            'url': url,
            'title': '',
            'content': f"Error: {str(e)}",
            'links': set(),
            'success': False
        }


def crawl_page_jina_with_wait(url, wait_selector=None, timeout=30):
    """
    Crawl a page with custom wait for dynamic content.
    Useful for SPAs and sites with delayed loading.
    """
    jina_url = f"{JINA_BASE}/{url}"
    
    headers = {
        "Accept": "application/json",
        "x-no-cache": "true",
        "x-timeout": str(timeout)
    }
    
    if wait_selector:
        headers["x-wait-for-selector"] = wait_selector
    
    try:
        response = requests.get(
            jina_url,
            headers=headers,
            timeout=timeout + 5
        )
        response.raise_for_status()
        
        data = response.json()
        
        # Get links from HTML
        html_links = extract_links_from_html(url)
        
        return {
            'url': url,
            'title': data.get('title', ''),
            'content': data.get('content', ''),
            'links': html_links,
            'success': True
        }
        
    except Exception as e:
        return {
            'url': url,
            'title': '',
            'content': f"Error: {str(e)}",
            'links': set(),
            'success': False
        }


def main():
    print(f"Crawling with Jina AI Reader: {BASE_URL}")
    print(f"Max depth: {MAX_DEPTH}")
    print(f"Output: {OUTPUT_FILE}")
    print()
    
    crawled = {}
    to_crawl = {normalize_url(BASE_URL)}
    depth_map = {normalize_url(BASE_URL): 0}
    
    retry_queue = []  # Pages that might need retry with different settings
    
    while to_crawl or retry_queue:
        # Process retry queue after main queue
        if not to_crawl and retry_queue:
            url, depth = retry_queue.pop(0)
            print(f"[Retry] Crawling: {url}")
            page_data = crawl_page_jina_with_wait(url, timeout=45)
        else:
            url = to_crawl.pop()
            depth = depth_map[url]
            
            if url in crawled:
                continue
            
            print(f"[Depth {depth}] Crawling: {url}")
            page_data = crawl_page_jina(url)
        
        crawled[url] = page_data
        
        if page_data['success']:
            content_len = len(page_data['content'])
            links_count = len(page_data['links'])
            print(f"  ✓ Success: {page_data['title'][:60]}... ({content_len} chars, {links_count} links)")
            
            # If content is very short, might be a loading issue - add to retry
            if content_len < 500 and depth == 0:
                print(f"  ⚠ Content very short, will retry with longer timeout")
                retry_queue.append((url, depth))
            
            # Add new links if we haven't reached max depth
            if depth < MAX_DEPTH:
                for link in page_data['links']:
                    if link not in crawled and link not in to_crawl:
                        to_crawl.add(link)
                        depth_map[link] = depth + 1
        else:
            print(f"  ✗ Failed: {page_data['content'][:100]}")
        
        # Polite delay with jitter
        if to_crawl or retry_queue:
            delay = 1 + random.random() * 2  # 1-3 seconds
            time.sleep(delay)
    
    print(f"\n{'='*50}")
    print(f"Crawled {len(crawled)} pages")
    
    # Write to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# Crawled Content - {BASE_URL}\n\n")
        f.write(f"**Max Depth:** {MAX_DEPTH}\n")
        f.write(f"**Pages Crawled:** {len(crawled)}\n")
        f.write(f"**Method:** Jina AI Reader\n")
        f.write(f"**Source:** https://jina.ai/reader\n\n")
        f.write("---\n\n")
        
        for url in sorted(crawled.keys()):
            page = crawled[url]
            f.write(f"## {page['title'] or url}\n\n")
            f.write(f"**URL:** {url}\n")
            f.write(f"**Depth:** {depth_map[url]}\n")
            f.write(f"**Status:** {'Success' if page['success'] else 'Failed'}\n\n")
            
            if page['links']:
                f.write(f"**Links ({len(page['links'])}):**\n")
                for link in sorted(page['links'])[:20]:
                    f.write(f"- {link}\n")
                f.write("\n")
            
            f.write("**Content:**\n\n")
            f.write(page['content'])
            f.write("\n\n---\n\n")
    
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
