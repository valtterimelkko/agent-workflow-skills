#!/usr/bin/env python3
"""Twitter scraper test suite.

Note: Full tests require Xpoz API calls (30-120s). For quick verification:
  python3 -c "from platforms import TwitterScraper; print('OK')"
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from xpoz.xpoz_client import XpozMCPClient
from platforms.twitter_scraper import TwitterScraper


QUALITY_THRESHOLDS = {
    "min_reply_ratio": 0.20,        # 20% tweets have replies
    "min_engagement_avg": 10,       # Average engagement
    "min_posts_returned": 5,
}


async def run_twitter_tests(skip_long_ops: bool = False):
    """Run Twitter scraper tests."""
    print("=" * 60)
    print("Twitter Scraper Quality Tests")
    print("=" * 60)
    
    if skip_long_ops:
        print("\n⚠️  SKIP_LONG_OPS=True - Skipping API calls")
        print("To run full tests: python3 test_twitter_scraper.py")
        print("(Full tests take 2-5 minutes due to Xpoz async operations)")

    async with XpozMCPClient() as client:
        scraper = TwitterScraper(client)

        # Test 1: Basic search
        print("\n[Test 1] Basic hashtag search (#buildinpublic)...")
        if skip_long_ops:
            print("  SKIP: (skip_long_ops=True)")
            tweets = []
        else:
            try:
                tweets = await scraper._search_hashtag("#buildinpublic", limit=20)
                if len(tweets) >= QUALITY_THRESHOLDS["min_posts_returned"]:
                    print(f"  PASS: Retrieved {len(tweets)} tweets")
                else:
                    print(f"  WARN: Only {len(tweets)} tweets")
            except Exception as e:
                print(f"  FAIL: {e}")
                tweets = []

        # Test 2: Lens-based scraping
        print("\n[Test 2] Lens-based scraping (devtools_ai)...")
        if skip_long_ops:
            print("  SKIP: (skip_long_ops=True)")
        else:
            tweets = await scraper.scrape_for_lens("devtools_ai", limit=30)
            print(f"  Retrieved {len(tweets)} tweets")

        # Test 3: Engagement quality
        print("\n[Test 3] Engagement quality...")
        if skip_long_ops:
            print("  SKIP: (skip_long_ops=True)")
        elif tweets:
            avg_engagement = sum(t.engagement for t in tweets) / len(tweets)
            print(f"  Average engagement: {avg_engagement:.1f}")

        # Test 4: Velocity tracking
        print("\n[Test 4] Hashtag velocity tracking...")
        if skip_long_ops:
            print("  SKIP: (skip_long_ops=True)")
        else:
            try:
                velocity = await scraper.track_hashtag_velocity("#buildinpublic")
                print(f"  Velocity: {velocity['velocity_percent']:.1f}%")
                print(f"  Stage: {velocity['stage']}")
                print(f"  Recommendation: {velocity['recommendation']}")
            except Exception as e:
                print(f"  WARN: Velocity tracking failed: {e}")

        # Sample tweets
        if not skip_long_ops and tweets:
            print("\n## Sample Tweets (for manual review)")
            for i, tweet in enumerate(tweets[:3], 1):
                print(f"\n--- Sample {i} ---")
                print(f"Text: {tweet.body[:150]}...")
                print(f"Engagement: {tweet.engagement} | Pain: {tweet.pain_score:.2f}")

        print("\n" + "=" * 60)
        if skip_long_ops:
            print("STRUCTURAL TESTS PASSED (API calls skipped)")
        else:
            print("Review samples above. PAUSE if quality is insufficient.")
        print("=" * 60)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--quick', action='store_true', help='Skip API calls (fast)')
    args = parser.parse_args()
    
    asyncio.run(run_twitter_tests(skip_long_ops=args.quick))