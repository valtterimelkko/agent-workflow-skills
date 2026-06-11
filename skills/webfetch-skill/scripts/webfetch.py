#!/usr/bin/env python3
"""
Webfetch CLI - Fetch and extract web content.

IMPORTANT: This script should be located at:
./skills/webfetch-skill/scripts/webfetch.py

This script is used by the webfetch-skill sub-agent to fetch web content.
The sub-agent MUST use this script via python3, NOT MCP tools.

Usage:
    python3 ./skills/webfetch-skill/scripts/webfetch.py --url "https://example.com"
    python3 ./skills/webfetch-skill/scripts/webfetch.py --url "https://example.com" --url "https://example2.com"
    python3 ./skills/webfetch-skill/scripts/webfetch.py --url "https://example.com" --no-cache
    python3 ./skills/webfetch-skill/scripts/webfetch.py --url "https://example.com" --output content.md
"""

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, urljoin

try:
    import trafilatura
    import requests
except ImportError as e:
    print(f"Error: Required library not installed: {e}")
    print("Install with: pip install --break-system-packages trafilatura requests beautifulsoup4")
    sys.exit(1)

# IMPORTANT: Sub-agent uses this folder to store cache and output files
CACHE_DIR = Path.home() / "webfetch-skill-temp-folder"
CACHE_TTL = 900  # 15 minutes in seconds
MAX_URLS = 5
DEFAULT_TIMEOUT = 10
DEFAULT_USER_AGENT = "Mozilla/5.0 (compatible; OpenCode-Webfetch/1.0)"


class WebFetcher:
    def __init__(self, use_cache=True, timeout=DEFAULT_TIMEOUT):
        self.use_cache = use_cache
        self.timeout = timeout
        self.headers = {
            "User-Agent": DEFAULT_USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        }

    def _get_cache_path(self, url):
        """Generate cache file path for a URL."""
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return CACHE_DIR / f"{url_hash}.json"

    def _is_cache_valid(self, cache_path):
        """Check if cache file is still valid."""
        if not cache_path.exists():
            return False
        cache_age = time.time() - cache_path.stat().st_mtime
        return cache_age < CACHE_TTL

    def _get_cached_content(self, cache_path):
        """Retrieve content from cache."""
        try:
            with open(cache_path, "r") as f:
                cached = json.load(f)
                return cached.get("content"), cached.get("links"), cached.get("images")
        except (json.JSONDecodeError, KeyError):
            return None, None, None

    def _save_to_cache(self, cache_path, content, links=None, images=None):
        """Save content to cache."""
        cache_data = {
            "content": content,
            "links": links or [],
            "images": images or [],
        }
        with open(cache_path, "w") as f:
            json.dump(cache_data, f)

    def _normalize_url(self, url):
        """Normalize URL - upgrade HTTP to HTTPS."""
        url = url.strip()
        if url.startswith("http://"):
            url = url.replace("http://", "https://", 1)
        return url

    def _fetch_html(self, url):
        """Fetch HTML content from URL."""
        try:
            response = requests.get(
                url,
                headers=self.headers,
                timeout=self.timeout,
                allow_redirects=True,
                verify=False
            )
            response.raise_for_status()
            return response.text, response.url
        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to fetch {url}: {e}")

    def _extract_content_with_trafilatura(self, html, url):
        """Extract main content using trafilatura."""
        downloaded = trafilatura.fetch_url(url)

        if downloaded:
            content = trafilatura.extract(downloaded, include_comments=False, include_tables=True)
            if not content:
                content = trafilatura.extract(downloaded, output_format="markdown", include_links=True)
        else:
            content = trafilatura.extract(html, include_comments=False, include_tables=True)

        if not content:
            content = trafilatura.extract(html, output_format="markdown", include_links=True)

        return content if content else None

    def _extract_links(self, html, base_url):
        """Extract all links from HTML."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            links = []

            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"].strip()
                if href and not href.startswith(("#", "javascript:", "mailto:", "tel:")):
                    absolute_url = urljoin(base_url, href)
                    text = a_tag.get_text(strip=True) or "No text"
                    links.append({"text": text, "url": absolute_url})

            return links[:20]
        except Exception:
            return []

    def _extract_images(self, html, base_url):
        """Extract image information from HTML."""
        try:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html, "html.parser")
            images = []

            for img_tag in soup.find_all("img"):
                src = img_tag.get("src", "").strip()
                if src:
                    absolute_url = urljoin(base_url, src)
                    alt = img_tag.get("alt", "").strip() or "No alt text"
                    images.append({"alt": alt, "url": absolute_url})

            return images[:10]
        except Exception:
            return []

    def fetch(self, url):
        """Fetch and extract content from a URL."""
        url = self._normalize_url(url)
        cache_path = self._get_cache_path(url)

        if self.use_cache and self._is_cache_valid(cache_path):
            content, links, images = self._get_cached_content(cache_path)
            if content:
                return {
                    "url": url,
                    "content": content,
                    "links": links or [],
                    "images": images or [],
                    "cached": True,
                }

        try:
            html, final_url = self._fetch_html(url)
            content = self._extract_content_with_trafilatura(html, final_url)

            if not content:
                content = "No content could be extracted from this page."

            links = self._extract_links(html, final_url)
            images = self._extract_images(html, final_url)

            if self.use_cache:
                CACHE_DIR.mkdir(parents=True, exist_ok=True)
                self._save_to_cache(cache_path, content, links, images)

            return {
                "url": url,
                "content": content,
                "links": links,
                "images": images,
                "cached": False,
            }

        except Exception as e:
            return {
                "url": url,
                "error": str(e),
                "content": None,
                "links": [],
                "images": [],
                "cached": False,
            }

    def format_as_markdown(self, result):
        """Format fetch result as markdown."""
        if result.get("error"):
            return f"## Error: {result['url']}\n\n{result['error']}\n"

        md = []
        md.append(f"# {result['url']}")
        if result.get("cached"):
            md.append("_(from cache)_")
        md.append("")

        md.append("## Content\n")
        md.append(result["content"])
        md.append("")

        if result.get("images"):
            md.append("## Images\n")
            for img in result["images"]:
                md.append(f"- **{img['alt']}**: {img['url']}")
            md.append("")

        if result.get("links"):
            md.append("## Links\n")
            for link in result["links"]:
                md.append(f"- [{link['text']}]({link['url']})")
            md.append("")

        return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(
        description="Fetch and extract web content with trafilatura",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Fetch a single URL
  %(prog)s --url "https://example.com"

  # Fetch multiple URLs
  %(prog)s --url "https://example.com" --url "https://example2.com"

  # Disable cache
  %(prog)s --url "https://example.com" --no-cache

  # Save to file
  %(prog)s --url "https://example.com" --output content.md

  # Set timeout
  %(prog)s --url "https://example.com" --timeout 30
        """
    )

    parser.add_argument(
        "--url", "-u",
        action="append",
        required=True,
        help="URL to fetch (can be specified multiple times, max 5)"
    )

    parser.add_argument(
        "--cache", "-c",
        action="store_true",
        default=True,
        help="Enable caching (default: enabled, use --no-cache to disable)"
    )

    parser.add_argument(
        "--no-cache",
        action="store_false",
        dest="cache",
        help="Disable caching"
    )

    parser.add_argument(
        "--timeout", "-t",
        type=int,
        default=DEFAULT_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})"
    )

    parser.add_argument(
        "--output", "-o",
        help="Save output to file instead of stdout"
    )

    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Print detailed progress messages"
    )

    args = parser.parse_args()

    # Ensure cache directory exists
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if len(args.url) > MAX_URLS:
        print(f"Error: Maximum {MAX_URLS} URLs allowed", file=sys.stderr)
        sys.exit(1)

    fetcher = WebFetcher(use_cache=args.cache, timeout=args.timeout)
    results = []

    if args.verbose:
        print(f"[Webfetch] Fetching {len(args.url)} URL(s)...", file=sys.stderr)
        print(f"[Webfetch] Cache: {'enabled' if args.cache else 'disabled'}", file=sys.stderr)
        print(f"[Webfetch] Cache dir: {CACHE_DIR}", file=sys.stderr)

    for url in args.url:
        if args.verbose:
            print(f"[Webfetch] Fetching: {url}", file=sys.stderr)
        result = fetcher.fetch(url)
        if args.verbose:
            if result.get("error"):
                print(f"[Webfetch] ERROR: {result['error']}", file=sys.stderr)
            elif result.get("cached"):
                print(f"[Webfetch] Retrieved from cache", file=sys.stderr)
            else:
                print(f"[Webfetch] Fetched successfully ({len(result.get('content', ''))} chars)", file=sys.stderr)
        results.append(result)

    output_lines = []
    for i, result in enumerate(results, 1):
        if len(results) > 1:
            output_lines.append(f"\n{'=' * 80}\n")
        output_lines.append(fetcher.format_as_markdown(result))

    output = "\n".join(output_lines)

    if args.output:
        Path(args.output).parent.mkdir(parents=True, exist_ok=True)
        Path(args.output).write_text(output)
        print(f"Saved to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()