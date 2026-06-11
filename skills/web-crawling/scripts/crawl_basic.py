#!/usr/bin/env python3
"""
Basic web crawler using requests + BeautifulSoup.
For sites without heavy JavaScript or bot protection.
"""

import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import time
import sys

# Configuration
BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "https://example.com"
MAX_DEPTH = int(sys.argv[2]) if len(sys.argv) > 2 else 1
OUTPUT_FILE = sys.argv[3] if len(sys.argv) > 3 else "crawled-content.md"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
}


def normalize_url(url, base=BASE_URL):
    """Normalize URL for consistent comparison."""
    if not url.startswith('http'):
        url = urljoin(base, url)
    # Remove fragments and query params
    url = url.split('#')[0].split('?')[0]
    # Remove trailing slash
    url = url.rstrip('/')
    return url


def is_internal(url):
    """Check if URL belongs to the target domain."""
    parsed = urlparse(url)
    base_parsed = urlparse(BASE_URL)
    return parsed.netloc == base_parsed.netloc or parsed.netloc == ''


def is_valid_page(url):
    """Check if URL is a crawlable page (not media/file)."""
    excluded = ('.pdf', '.jpg', '.jpeg', '.png', '.gif', '.zip', '.doc', '.docx',
                '.mp3', '.mp4', '.avi', '.mov', '.css', '.js', '.svg', '.ico')
    return not url.lower().endswith(excluded)


def crawl_page(url):
    """Crawl a single page and return content + links."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=15, verify=True)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract links
        links = set()
        for anchor in soup.find_all('a', href=True):
            href = anchor['href']
            full_url = normalize_url(urljoin(url, href))
            if is_internal(full_url) and is_valid_page(full_url):
                links.add(full_url)
        
        # Extract text
        for script in soup(["script", "style", "nav", "footer", "iframe"]):
            script.decompose()
        
        text = soup.get_text(separator='\n', strip=True)
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        clean_text = '\n'.join(lines)
        
        return {
            'url': url,
            'text': clean_text,
            'links': links,
            'success': True,
            'status': response.status_code
        }
    except Exception as e:
        return {
            'url': url,
            'text': f"Error: {str(e)}",
            'links': set(),
            'success': False,
            'status': 0
        }


def main():
    print(f"Crawling: {BASE_URL}")
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
            print(f"  ✓ Success ({len(page_data['links'])} links)")
            
            # Add new links if we haven't reached max depth
            if current_depth < MAX_DEPTH:
                for link in page_data['links']:
                    if link not in crawled and link not in to_crawl:
                        to_crawl.add(link)
                        depth_map[link] = current_depth + 1
        else:
            print(f"  ✗ Failed: {page_data['text']}")
        
        # Be polite
        time.sleep(1)
    
    print(f"\nCrawled {len(crawled)} pages")
    
    # Write to file
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(f"# Crawled Content - {BASE_URL}\n\n")
        f.write(f"**Max Depth:** {MAX_DEPTH}\n")
        f.write(f"**Pages Crawled:** {len(crawled)}\n\n")
        f.write("---\n\n")
        
        for url in sorted(crawled.keys()):
            page = crawled[url]
            f.write(f"## {url}\n\n")
            f.write(f"**Depth:** {depth_map[url]}\n")
            f.write(f"**Status:** {'Success' if page['success'] else 'Failed'}\n\n")
            
            if page['links']:
                f.write(f"**Links ({len(page['links'])}):**\n")
                for link in sorted(page['links'])[:20]:  # Limit links shown
                    f.write(f"- {link}\n")
                f.write("\n")
            
            f.write("**Content:**\n\n```\n")
            f.write(page['text'])
            f.write("\n```\n\n---\n\n")
    
    print(f"Saved to: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
