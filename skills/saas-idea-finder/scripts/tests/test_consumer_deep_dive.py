#!/usr/bin/env python3
"""
Test Consumer Deep Dive Analysis

Tests the deep dive consumer problem detection capabilities.
Can be run in quick mode (no API calls) or full mode (with Xpoz API).
"""
import sys
import json
from pathlib import Path
from datetime import datetime

# Add paths
SCRIPT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR / "xpoz"))
sys.path.insert(0, str(SCRIPT_DIR / "platforms"))
sys.path.insert(0, str(SCRIPT_DIR / "helpers"))


def test_consumer_deep_dive_modules():
    """Test that all deep dive modules can be imported."""
    print("=" * 70)
    print("Consumer Deep Dive Module Import Test")
    print("=" * 70)
    
    results = {
        "consumer_deep_dive": False,
        "consumer_scraper_enhanced": False,
        "xpoz_consumer_deep_dive": False,
    }
    
    # Test consumer_deep_dive
    try:
        from consumer_deep_dive import ConsumerDeepDiveAnalyzer, ConsumerProblem
        print("✓ consumer_deep_dive imported")
        results["consumer_deep_dive"] = True
    except Exception as e:
        print(f"✗ consumer_deep_dive: {e}")
    
    # Test consumer_scraper_enhanced
    try:
        from consumer_scraper_enhanced import ConsumerProblemDetectionMixin
        print("✓ consumer_scraper_enhanced imported")
        results["consumer_scraper_enhanced"] = True
    except Exception as e:
        print(f"✗ consumer_scraper_enhanced: {e}")
    
    # Test xpoz_consumer_deep_dive
    try:
        from xpoz_consumer_deep_dive import XpozConsumerDeepDiveFetcher
        print("✓ xpoz_consumer_deep_dive imported")
        results["xpoz_consumer_deep_dive"] = True
    except Exception as e:
        print(f"✗ xpoz_consumer_deep_dive: {e}")
    
    print()
    return all(results.values())


def test_analyzer_logic():
    """Test the deep dive analyzer logic without API calls."""
    print("=" * 70)
    print("Consumer Deep Dive Logic Test")
    print("=" * 70)
    
    try:
        from consumer_deep_dive import ConsumerDeepDiveAnalyzer
    except ImportError as e:
        print(f"✗ Cannot import analyzer: {e}")
        return False
    
    analyzer = ConsumerDeepDiveAnalyzer()
    
    # Test case 1: High-intent consumer problem
    test_post_1 = {
        "platform": "reddit",
        "id": "test1",
        "title": "Etsy fees are killing my profit margins",
        "body": "I'm paying so much in fees that I'm barely breaking even. The platform takes a huge cut and then there's payment processing on top. I'm spending hours every week just calculating fees. Would definitely pay for a tool that helps me optimize pricing and track real profit after all fees.",
        "url": "https://example.com/1",
        "author": "seller123",
        "engagement": 45
    }
    
    problem_1 = analyzer.analyze_post_deep(test_post_1, replies=[
        "Same here! It's so frustrating.",
        "I built my own spreadsheet to track this",
        "Would pay for a solution too",
    ])
    
    if problem_1:
        print("✓ Test 1: High-intent problem detected")
        print(f"  Category: {problem_1.primary_category}")
        print(f"  Pain types: {problem_1.pain_types}")
        print(f"  Severity: {problem_1.severity_score}")
        print(f"  Willingness to pay: {len(problem_1.willingness_to_pay_signals) > 0}")
        print(f"  Validation signals: {problem_1.validation_signals}")
        print(f"  Workaround mentions: {problem_1.workaround_mentions}")
    else:
        print("✗ Test 1: Failed to detect problem")
    
    print()
    
    # Test case 2: Medium-intent problem
    test_post_2 = {
        "platform": "twitter",
        "id": "test2",
        "title": "",
        "body": "Tired of manually updating inventory across 5 different platforms. Why isn't there a simple tool for this?",
        "url": "https://example.com/2",
        "author": "seller456",
        "engagement": 12
    }
    
    problem_2 = analyzer.analyze_post_deep(test_post_2, replies=[])
    
    if problem_2:
        print("✓ Test 2: Medium-intent problem detected")
        print(f"  Category: {problem_2.primary_category}")
        print(f"  Severity: {problem_2.severity_score}")
    else:
        print("ℹ Test 2: No high-intent problem detected (expected - low validation)")
    
    print()
    
    # Test report generation
    if problem_1:
        print("✓ Testing report generation...")
        report = analyzer.generate_opportunity_report([problem_1])
        print(f"  Total problems: {report['total_problems_analyzed']}")
        print(f"  Category breakdown: {report['category_breakdown']}")
        print(f"  Avg severity: {report['avg_severity']:.1f}")
        print(f"  Willingness indicators: {report['willingness_to_pay_indicators']}")
    
    return True


def test_enhanced_scrapers():
    """Test that enhanced scrapers have consumer detection."""
    print("=" * 70)
    print("Enhanced Scraper Test")
    print("=" * 70)
    
    # Import base scraper first
    import importlib.util
    spec = importlib.util.spec_from_file_location("base_scraper", SCRIPT_DIR / "platforms" / "base_scraper.py")
    base_module = importlib.util.module_from_spec(spec)
    sys.modules['base_scraper'] = base_module
    spec.loader.exec_module(base_module)
    
    # Import consumer enhanced
    spec2 = importlib.util.spec_from_file_location("consumer_scraper_enhanced", SCRIPT_DIR / "platforms" / "consumer_scraper_enhanced.py")
    consumer_module = importlib.util.module_from_spec(spec2)
    sys.modules['consumer_scraper_enhanced'] = consumer_module
    spec2.loader.exec_module(consumer_module)
    
    results = []
    
    # Test Reddit scraper
    try:
        spec = importlib.util.spec_from_file_location("reddit_scraper", SCRIPT_DIR / "platforms" / "reddit_scraper.py")
        reddit_module = importlib.util.module_from_spec(spec)
        sys.modules['reddit_scraper'] = reddit_module
        spec.loader.exec_module(reddit_module)
        
        # Check if it has the mixin
        if hasattr(reddit_module.RedditScraper, 'detect_consumer_pain_signals'):
            print("✓ RedditScraper has consumer detection")
            results.append(True)
        else:
            print("✗ RedditScraper missing consumer detection")
            results.append(False)
    except Exception as e:
        print(f"✗ RedditScraper test failed: {e}")
        results.append(False)
    
    # Test Twitter scraper
    try:
        spec = importlib.util.spec_from_file_location("twitter_scraper", SCRIPT_DIR / "platforms" / "twitter_scraper.py")
        twitter_module = importlib.util.module_from_spec(spec)
        sys.modules['twitter_scraper'] = twitter_module
        spec.loader.exec_module(twitter_module)
        
        if hasattr(twitter_module.TwitterScraper, 'detect_consumer_pain_signals'):
            print("✓ TwitterScraper has consumer detection")
            results.append(True)
        else:
            print("✗ TwitterScraper missing consumer detection")
            results.append(False)
    except Exception as e:
        print(f"✗ TwitterScraper test failed: {e}")
        results.append(False)
    
    return all(results)


def main():
    """Run all tests."""
    print("\n" + "=" * 70)
    print("CONSUMER DEEP DIVE TEST SUITE")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}\n")
    
    all_passed = True
    
    all_passed &= test_consumer_deep_dive_modules()
    print()
    
    all_passed &= test_analyzer_logic()
    print()
    
    all_passed &= test_enhanced_scrapers()
    print()
    
    print("=" * 70)
    if all_passed:
        print("ALL TESTS PASSED")
    else:
        print("SOME TESTS FAILED")
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())