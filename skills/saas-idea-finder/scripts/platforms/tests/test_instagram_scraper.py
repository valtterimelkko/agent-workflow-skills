#!/usr/bin/env python3
"""Instagram scraper test suite."""
import asyncio
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from xpoz.xpoz_client import XpozMCPClient
from platforms.instagram_scraper import InstagramScraper


QUALITY_THRESHOLDS = {
    "min_posts_returned": 3,
    "min_high_intent_ratio": 0.10,  # 10% high intent posts
}


async def run_instagram_tests(quick_mode: bool = False):
    """Run Instagram scraper tests."""
    print("=" * 60)
    print("Instagram Scraper Quality Tests")
    print("=" * 60)
    
    if quick_mode:
        print("\n[QUICK MODE] Skipping API calls, verifying code structure only")
        print("-" * 60)
        
        # Test 1: Verify scraper class structure
        print("\n[Test 1] Verifying InstagramScraper class structure...")
        try:
            # Check class has required methods
            assert hasattr(InstagramScraper, 'scrape_for_lens'), "Missing scrape_for_lens method"
            assert hasattr(InstagramScraper, '_search_hashtag'), "Missing _search_hashtag method"
            assert hasattr(InstagramScraper, '_analyze_engagement_quality'), "Missing _analyze_engagement_quality method"
            assert hasattr(InstagramScraper, '_detect_content_signals'), "Missing _detect_content_signals method"
            print("  PASS: All required methods present")
        except AssertionError as e:
            print(f"  FAIL: {e}")
            return False
        
        # Test 2: Verify hashtag clusters
        print("\n[Test 2] Verifying hashtag clusters...")
        try:
            clusters = InstagramScraper.HASHTAG_CLUSTERS
            assert len(clusters) >= 7, f"Expected 7+ lens clusters, got {len(clusters)}"
            for lens, hashtags in clusters.items():
                assert len(hashtags) >= 3, f"Lens '{lens}' has fewer than 3 hashtags"
            print(f"  PASS: {len(clusters)} lens clusters configured")
        except AssertionError as e:
            print(f"  FAIL: {e}")
            return False
        
        # Test 3: Verify engagement thresholds
        print("\n[Test 3] Verifying engagement thresholds...")
        try:
            thresholds = InstagramScraper.ENGAGEMENT_THRESHOLDS
            assert "save_rate_high" in thresholds, "Missing save_rate_high threshold"
            assert "share_rate_high" in thresholds, "Missing share_rate_high threshold"
            print("  PASS: Engagement thresholds configured")
        except AssertionError as e:
            print(f"  FAIL: {e}")
            return False
        
        # Test 4: Verify content signal patterns
        print("\n[Test 4] Verifying content signal patterns...")
        try:
            patterns = InstagramScraper.INSTAGRAM_PATTERNS
            assert "cta_patterns" in patterns, "Missing cta_patterns"
            assert "tutorial_patterns" in patterns, "Missing tutorial_patterns"
            assert "business_patterns" in patterns, "Missing business_patterns"
            print("  PASS: Content signal patterns configured")
        except AssertionError as e:
            print(f"  FAIL: {e}")
            return False
        
        # Test 5: Verify pain patterns
        print("\n[Test 5] Verifying pain patterns...")
        try:
            pain_patterns = InstagramScraper.INSTAGRAM_PAIN_PATTERNS
            assert len(pain_patterns) >= 5, f"Expected 5+ pain patterns, got {len(pain_patterns)}"
            print(f"  PASS: {len(pain_patterns)} pain patterns defined")
        except AssertionError as e:
            print(f"  FAIL: {e}")
            return False
        
        print("\n" + "=" * 60)
        print("All structure tests PASSED (Quick Mode)")
        print("=" * 60)
        return True
    
    # Full test mode with API calls
    async with XpozMCPClient() as client:
        scraper = InstagramScraper(client)

        # Test 1: Basic search
        print("\n[Test 1] Basic hashtag search (#smallbusiness)...")
        try:
            posts = await scraper._search_hashtag("smallbusiness", limit=15)
            if len(posts) >= QUALITY_THRESHOLDS["min_posts_returned"]:
                print(f"  PASS: Retrieved {len(posts)} posts")
            else:
                print(f"  WARN: Only {len(posts)} posts")
        except Exception as e:
            print(f"  FAIL: {e}")
            posts = []

        # Test 2: Engagement quality analysis
        print("\n[Test 2] Engagement quality analysis...")
        if posts:
            high_intent = [
                p for p in posts
                if p.metadata.get("engagement_quality", {}).get("is_high_intent")
            ]
            ratio = len(high_intent) / len(posts)
            print(f"  High intent ratio: {ratio:.1%}")
            if high_intent:
                sample = high_intent[0]
                eq = sample.metadata.get("engagement_quality", {})
                print(f"  Sample save rate: {eq.get('save_rate', 0):.2%}")
                print(f"  Sample quality tier: {eq.get('quality_tier', 'unknown')}")
        else:
            print("  SKIP: No posts to analyze")

        # Test 3: Content signal detection
        print("\n[Test 3] Content signal detection...")
        if posts:
            has_cta = [p for p in posts if p.metadata.get("content_signals", {}).get("cta_patterns")]
            has_tutorial = [p for p in posts if p.metadata.get("content_signals", {}).get("tutorial_patterns")]
            has_business = [p for p in posts if p.metadata.get("content_signals", {}).get("business_patterns")]
            print(f"  Posts with CTA: {len(has_cta)}")
            print(f"  Posts with tutorial: {len(has_tutorial)}")
            print(f"  Posts with business signals: {len(has_business)}")
        else:
            print("  SKIP: No posts to analyze")

        # Test 4: Lens-based scraping
        print("\n[Test 4] Lens-based scraping (ecommerce_sellers)...")
        try:
            posts = await scraper.scrape_for_lens("ecommerce_sellers", limit=20)
            print(f"  Retrieved {len(posts)} posts")
            
            # Check for high-opportunity posts
            high_opp = [p for p in posts if p.is_high_opportunity]
            print(f"  High opportunity posts: {len(high_opp)}")
        except Exception as e:
            print(f"  FAIL: {e}")
            posts = []

        # Sample posts
        print("\n## Sample Posts (for manual review)")
        for i, post in enumerate(posts[:3], 1):
            print(f"\n--- Sample {i} ---")
            caption = post.body[:150] if post.body else "(no caption)"
            print(f"Caption: {caption}...")
            print(f"Engagement: {post.engagement}")
            eq = post.metadata.get("engagement_quality", {})
            print(f"Quality Tier: {eq.get('quality_tier', 'unknown')}")
            print(f"High Intent: {eq.get('is_high_intent', False)}")
            signals = post.metadata.get("content_signals", {})
            print(f"Business Signals: {signals.get('business_patterns', False)}")

        # Quality guidance
        print("\n" + "=" * 60)
        print("## Quality Self-Assessment")
        print("1. Is engagement quality analysis useful?")
        print("2. Are content signals being detected correctly?")
        print("3. Are we finding small business content?")
        print("\nIf ANY answer is 'no' → PAUSE and propose improvements.")
        print("=" * 60)
        
        return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Test Instagram scraper")
    parser.add_argument("--quick", action="store_true", help="Skip API calls, verify structure only")
    args = parser.parse_args()
    
    success = asyncio.run(run_instagram_tests(quick_mode=args.quick))
    sys.exit(0 if success else 1)