#!/usr/bin/env python3
"""
Reddit scraper for SaaS idea discovery - Self-hosted JSON API implementation.

This module now uses Reddit's public .json endpoints instead of Xpoz MCP.
The interface remains the same for backwards compatibility.

Usage:
    from platforms.reddit_scraper import RedditScraper
    scraper = RedditScraper()
    posts = await scraper.scrape_for_lens("ecommerce_sellers", limit=50)
"""
import sys
from pathlib import Path

# Import the new JSON-based implementation
from reddit_json_scraper import (
    RedditJSONScraper,
    RedditScraper as _RedditScraper,
    fetch_reddit_posts,
    RateLimitInfo
)

# Re-export for backwards compatibility
RedditScraper = _RedditScraper

# If this file is run directly, provide info
if __name__ == "__main__":
    print("Reddit Scraper - Self-hosted JSON API implementation")
    print("")
    print("This scraper uses Reddit's public .json endpoints.")
    print("No authentication required for read-only access.")
    print("")
    print("Usage:")
    print("  from platforms.reddit_scraper import RedditScraper")
    print("  scraper = RedditScraper()")
    print("  posts = await scraper.scrape_for_lens('ecommerce_sellers', limit=50)")
    print("")
    print("Available lens keys:")
    for key in RedditScraper.SUBREDDIT_CLUSTERS.keys():
        print(f"  - {key}")