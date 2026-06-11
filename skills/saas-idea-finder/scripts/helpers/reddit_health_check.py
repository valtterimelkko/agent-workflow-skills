#!/usr/bin/env python3
"""
Health check for Reddit scraper.
Run this before daily pipeline to verify Reddit is accessible.
"""
import asyncio
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "platforms"))

from reddit_json_scraper import RedditJSONScraper


async def health_check():
    """Quick health check - should complete in < 30 seconds."""
    print("Reddit Scraper Health Check")
    print("=" * 50)
    
    proxy = os.environ.get('REDDIT_PROXY_URL')
    if proxy:
        print(f"✓ Proxy configured: {proxy.split('@')[-1]}")
    else:
        print("⚠ No proxy configured - may fail in cloud environment")
    
    scraper = RedditJSONScraper()
    
    try:
        # Quick test - single subreddit, 2 posts
        posts = await asyncio.wait_for(
            scraper._fetch_subreddit_posts('programming', limit=2),
            timeout=20
        )
        
        if posts:
            print(f"✓ Reddit accessible - retrieved {len(posts)} posts")
            print(f"✓ Sample: {posts[0].title[:50]}...")
            return True
        else:
            print("✗ No posts retrieved")
            return False
            
    except asyncio.TimeoutError:
        print("✗ Timeout - Reddit or proxy is slow/unresponsive")
        return False
    except Exception as e:
        print(f"✗ Error: {e}")
        return False
    finally:
        await scraper.close()


if __name__ == "__main__":
    success = asyncio.run(health_check())
    sys.exit(0 if success else 1)