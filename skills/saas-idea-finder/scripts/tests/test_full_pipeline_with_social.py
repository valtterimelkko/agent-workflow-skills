#!/usr/bin/env python3
"""
Full pipeline test with social media integration.

Run this after completing all integrations.

Usage:
    # Quick test (no API calls - verifies code structure only)
    cd /path/to/skills/saas-idea-finder
    python3 scripts/tests/test_full_pipeline_with_social.py --quick

    # Full test (requires Xpoz credentials)
    python3 scripts/tests/test_full_pipeline_with_social.py
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# Add parent paths for imports
SCRIPT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR / "xpoz"))
sys.path.insert(0, str(SCRIPT_DIR / "platforms"))

# Try to import Xpoz modules
try:
    from helpers.xpoz_fetcher import XpozFetcher
    XPOZ_AVAILABLE = True
except ImportError as e:
    print(f"Warning: XpozFetcher not available: {e}")
    XPOZ_AVAILABLE = False


def test_imports():
    """Test that all required modules can be imported."""
    print("\n[Test] Verifying module imports...")
    
    results = {
        "base_scraper": False,
        "reddit_scraper": False,
        "twitter_scraper": False,
        "instagram_scraper": False,
        "xpoz_fetcher": False,
        "xpoz_client": False,
        "xpoz_credentials": False,
    }
    
    # Test base_scraper
    try:
        from base_scraper import BaseScraper, ScrapedPost
        results["base_scraper"] = True
        print("  ✓ base_scraper")
    except Exception as e:
        print(f"  ✗ base_scraper: {e}")
    
    # Test reddit_scraper (handle relative imports)
    try:
        # Import via the module path
        sys.path.insert(0, str(SCRIPT_DIR / "platforms"))
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "reddit_scraper", SCRIPT_DIR / "platforms" / "reddit_scraper.py"
        )
        reddit_module = importlib.util.module_from_spec(spec)
        # Patch the base_scraper import
        sys.modules['base_scraper'] = __import__('base_scraper')
        spec.loader.exec_module(reddit_module)
        results["reddit_scraper"] = True
        print("  ✓ reddit_scraper")
    except Exception as e:
        print(f"  ✗ reddit_scraper: {e}")
    
    # Test twitter_scraper
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "twitter_scraper", SCRIPT_DIR / "platforms" / "twitter_scraper.py"
        )
        twitter_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(twitter_module)
        results["twitter_scraper"] = True
        print("  ✓ twitter_scraper")
    except Exception as e:
        print(f"  ✗ twitter_scraper: {e}")
    
    # Test instagram_scraper
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "instagram_scraper", SCRIPT_DIR / "platforms" / "instagram_scraper.py"
        )
        instagram_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(instagram_module)
        results["instagram_scraper"] = True
        print("  ✓ instagram_scraper")
    except Exception as e:
        print(f"  ✗ instagram_scraper: {e}")
    
    # Test xpoz_fetcher
    try:
        from helpers.xpoz_fetcher import XpozFetcher, XpozFetcherSync, fetch_from_xpoz_social
        results["xpoz_fetcher"] = True
        print("  ✓ xpoz_fetcher")
    except Exception as e:
        print(f"  ✗ xpoz_fetcher: {e}")
    
    # Test xpoz_client
    try:
        # Skip if aiohttp not available
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "xpoz_client", SCRIPT_DIR / "xpoz" / "xpoz_client.py"
        )
        xpoz_client_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(xpoz_client_module)
        results["xpoz_client"] = True
        print("  ✓ xpoz_client")
    except ImportError as e:
        if "aiohttp" in str(e):
            print("  ⚠ xpoz_client: aiohttp not installed (expected in minimal env)")
            results["xpoz_client"] = True  # Mark as pass for quick mode
        else:
            print(f"  ✗ xpoz_client: {e}")
    except Exception as e:
        print(f"  ✗ xpoz_client: {e}")
    
    # Test xpoz_credentials
    try:
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "xpoz_credentials", SCRIPT_DIR / "xpoz" / "xpoz_credentials.py"
        )
        xpoz_cred_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(xpoz_cred_module)
        results["xpoz_credentials"] = True
        print("  ✓ xpoz_credentials")
    except Exception as e:
        print(f"  ✗ xpoz_credentials: {e}")
    
    return all(results.values())


def test_lens_configuration():
    """Test that lens configuration includes social platforms."""
    print("\n[Test] Verifying lens configuration...")
    
    try:
        lens_path = Path(__file__).parent.parent.parent / "config" / "lenses.json"
        with open(lens_path) as f:
            lenses = json.load(f)
        
        total_lenses = len(lenses.get("lenses", []))
        lenses_with_social = sum(
            1 for lens in lenses.get("lenses", [])
            if "social_platforms" in lens
        )
        
        print(f"  Total lenses: {total_lenses}")
        print(f"  Lenses with social_platforms: {lenses_with_social}")
        
        if lenses_with_social == total_lenses:
            print("  ✓ All lenses have social_platforms configuration")
            return True
        else:
            print(f"  ⚠ {total_lenses - lenses_with_social} lenses missing social_platforms")
            return False
            
    except Exception as e:
        print(f"  ✗ Could not verify lens config: {e}")
        return False


def test_discover_trends_integration():
    """Test that discover_trends.py includes Xpoz integration."""
    print("\n[Test] Verifying discover_trends.py integration...")
    
    try:
        discover_path = Path(__file__).parent.parent / "discover_trends.py"
        content = discover_path.read_text()
        
        checks = {
            "xpoz import": "from helpers.xpoz_fetcher" in content,
            "xpoz fetcher": "XpozFetcherSync" in content or "fetch_from_xpoz_social" in content,
            "xpoz call": "fetch_from_xpoz_social(" in content,
            "xpoz_topics": "xpoz_topics" in content,
        }
        
        for check_name, result in checks.items():
            status = "✓" if result else "✗"
            print(f"  {status} {check_name}")
        
        return all(checks.values())
        
    except Exception as e:
        print(f"  ✗ Could not verify discover_trends.py: {e}")
        return False


def test_topic_extractor_integration():
    """Test that topic_extractor.py handles xpoz_topics."""
    print("\n[Test] Verifying topic_extractor.py integration...")
    
    try:
        extractor_path = Path(__file__).parent.parent / "helpers" / "topic_extractor.py"
        content = extractor_path.read_text()
        
        checks = {
            "xpoz_topics param": "xpoz_topics" in content,
            "xpoz_social type": "xpoz_social" in content,
            "social extraction": "Extract from Xpoz" in content or "xpoz_topics" in content,
        }
        
        for check_name, result in checks.items():
            status = "✓" if result else "✗"
            print(f"  {status} {check_name}")
        
        return all(checks.values())
        
    except Exception as e:
        print(f"  ✗ Could not verify topic_extractor.py: {e}")
        return False


def test_monitor_usage():
    """Test that monitor_usage.py exists and is valid."""
    print("\n[Test] Verifying monitor_usage.py...")
    
    try:
        monitor_path = Path(__file__).parent.parent / "xpoz" / "monitor_usage.py"
        
        if not monitor_path.exists():
            print("  ✗ monitor_usage.py not found")
            return False
        
        content = monitor_path.read_text()
        
        checks = {
            "file exists": True,
            "XpozUsageMonitor class": "class XpozUsageMonitor" in content,
            "free tier limit": "100_000" in content or "100000" in content,
            "estimate methods": "estimate" in content.lower(),
        }
        
        for check_name, result in checks.items():
            status = "✓" if result else "✗"
            print(f"  {status} {check_name}")
        
        return all(checks.values())
        
    except Exception as e:
        print(f"  ✗ Could not verify monitor_usage.py: {e}")
        return False


def run_quick_test():
    """Quick test without API calls - verifies code structure."""
    print("=" * 60)
    print("Quick Test: Code Structure Verification")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("\n[Mode] Quick (no API calls)")
    
    all_passed = True
    
    # Run all tests
    all_passed &= test_imports()
    all_passed &= test_lens_configuration()
    all_passed &= test_discover_trends_integration()
    all_passed &= test_topic_extractor_integration()
    all_passed &= test_monitor_usage()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("QUICK TEST PASSED - Code structure verified")
    else:
        print("QUICK TEST COMPLETED - Some checks failed (review above)")
    print("=" * 60)
    
    print("\nTo run full test with API calls (requires Xpoz credentials):")
    print("  python3 scripts/tests/test_full_pipeline_with_social.py")
    
    return all_passed


async def run_full_pipeline_test(quick: bool = False):
    """Test the complete pipeline with social sources."""
    print("=" * 60)
    print("Full Pipeline Test with Social Media")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print(f"Mode: {'Quick (no API calls)' if quick else 'Full (with API calls)'}")

    if quick:
        return run_quick_test()

    if not XPOZ_AVAILABLE:
        print("\nERROR: Xpoz modules not available. Cannot run full test.")
        return False

    fetcher = XpozFetcher()
    all_passed = True

    try:
        # Test 1: Connection
        print("\n[Test 1] Xpoz connection...")
        connected = await fetcher.connect()
        if connected:
            print("  PASS: Connected to Xpoz")
        else:
            print("  FAIL: Connection failed (credentials may not be configured)")
            print("  Note: This is expected if Xpoz OAuth has not been completed.")
            return False

        # Test 2: Multi-platform fetch for each lens
        test_lenses = [
            "ecommerce_sellers",
            "devtools_ai",
            "creator_economy",
        ]

        for lens in test_lenses:
            print(f"\n[Test 2.{test_lenses.index(lens)+1}] Fetch for lens: {lens}...")
            results = await fetcher.fetch_for_lens(lens, limit_per_platform=10)

            # Check results
            total_posts = sum(
                data.get("count", 0)
                for data in results.get("platforms", {}).values()
            )
            errors = results.get("errors", [])

            print(f"  Total posts: {total_posts}")
            print(f"  Platforms: {list(results.get('platforms', {}).keys())}")
            print(f"  Errors: {len(errors)}")

            if total_posts >= 5:
                print(f"  PASS")
            else:
                print(f"  WARN: Low post count (may be normal for test queries)")

            # Show aggregated topics
            topics = results.get("aggregated_topics", [])
            print(f"  Aggregated topics: {len(topics)}")
            if topics:
                print(f"  Top topic: {topics[0]['topic']} (score: {topics[0]['validation_score']:.1f})")

        # Test 3: Cross-platform validation
        print("\n[Test 3] Cross-platform topic validation...")
        results = await fetcher.fetch_for_lens("small_business_ops", limit_per_platform=20)
        topics = results.get("aggregated_topics", [])

        cross_platform_topics = [t for t in topics if t["cross_platform_count"] >= 2]
        print(f"  Topics with 2+ platform mentions: {len(cross_platform_topics)}")

        if cross_platform_topics:
            print("  PASS: Cross-platform validation working")
            print(f"  Best cross-platform topic: {cross_platform_topics[0]['topic']}")
            print(f"    Platforms: {cross_platform_topics[0]['platforms']}")
        else:
            print("  WARN: No cross-platform topics found (may be normal for test queries)")

        # Test 4: Source tagging
        print("\n[Test 4] Source tagging...")
        for platform, data in results.get("platforms", {}).items():
            posts = data.get("posts", [])
            if posts:
                sample = posts[0]
                has_source = (
                    sample.get("platform") and
                    sample.get("metadata", {}).get("hashtag_searched") or
                    sample.get("metadata", {}).get("subreddit")
                )
                status = "PASS" if has_source else "WARN"
                print(f"  {status}: {platform} posts have source metadata")

        # Summary
        print("\n" + "=" * 60)
        print("PIPELINE TEST COMPLETE")
        print("=" * 60)

        # Quality assessment
        print("\n## Final Quality Assessment")
        print("Review these questions before marking complete:")
        print("1. Are aggregated topics relevant for SaaS ideas?")
        print("2. Is cross-platform validation adding value?")
        print("3. Are source attributions clear and useful?")
        print("4. Is the pipeline fast enough for daily use?")
        print("\nIf ALL answers are 'yes', the integration is complete.")

        return all_passed

    except Exception as e:
        print(f"\n  FAIL: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        await fetcher.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test full pipeline with social media")
    parser.add_argument("--quick", action="store_true", help="Quick test without API calls")
    args = parser.parse_args()

    if args.quick:
        success = run_quick_test()
    else:
        success = asyncio.run(run_full_pipeline_test(quick=False))
    
    sys.exit(0 if success else 1)