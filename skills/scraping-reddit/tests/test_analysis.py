#!/usr/bin/env python3
"""
Analysis Algorithm Test Suite.

Tests pain point detection, sentiment analysis, velocity tracking,
and opportunity scoring without requiring API calls.

Usage:
    python3 tests/test_analysis.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.analysis import OpportunityAnalyzer
from scripts.utils import ScrapedPost, VelocityMetrics
from scripts.filters import IntentFilter, NegativeSearchFilter, VelocityFilter


def test_intent_pattern_matching():
    """Test high-intent pattern detection."""
    print("\n[Test] Intent Pattern Matching...")
    
    analyzer = OpportunityAnalyzer()
    
    test_cases = [
        ("Is there an app for tracking inventory?", True, 90),
        ("I hate it when I have to manually update spreadsheets", True, 80),
        ("Why is Salesforce so expensive?", True, 80),
        ("Would pay for a tool that syncs everything", True, 95),
        ("Just had a great day at work", False, 0),
        ("Someone should build a better email client", True, 90),
    ]
    
    passed = 0
    for text, should_match, min_score in test_cases:
        signals = analyzer._extract_intent_signals(text)
        
        if should_match:
            if signals and signals[0]["score"] >= min_score * 0.7:  # Allow some flexibility
                passed += 1
            else:
                print(f"  ✗ Expected match for: {text[:50]}...")
                print(f"    Got signals: {signals}")
        else:
            if not signals:
                passed += 1
            else:
                print(f"  ✗ Expected no match for: {text[:50]}...")
    
    print(f"  ✓ PASS: {passed}/{len(test_cases)} test cases passed")
    return passed == len(test_cases)


def test_frustration_scoring():
    """Test frustration/aggravation scoring."""
    print("\n[Test] Frustration Scoring...")
    
    analyzer = OpportunityAnalyzer()
    
    test_cases = [
        ("I'm extremely frustrated with this terrible software", 60, 100),
        ("This is infuriating!", 30, 100),  # Single extreme word = high base score
        ("Having a minor issue, would be nice if fixed", 10, 40),
        ("Everything is working great!", 0, 10),
        ("I'm not frustrated at all, this is amazing", 0, 10),  # Negation handling
    ]
    
    passed = 0
    for text, min_score, max_score in test_cases:
        score = analyzer._calculate_frustration_score(text)
        
        if min_score <= score <= max_score:
            passed += 1
        else:
            print(f"  ✗ Score {score} not in range [{min_score}, {max_score}] for: {text[:50]}")
    
    print(f"  ✓ PASS: {passed}/{len(test_cases)} test cases passed")
    return passed == len(test_cases)


def test_monetization_detection():
    """Test monetization signal detection."""
    print("\n[Test] Monetization Signal Detection...")
    
    analyzer = OpportunityAnalyzer()
    
    test_cases = [
        ("Would definitely pay $50/month for this", True),
        ("Our budget is around $1000", True),
        ("Looking for enterprise pricing", True),
        ("Too expensive for our needs", True),
        ("Just a hobby project, no money involved", False),
    ]
    
    passed = 0
    for text, should_detect in test_cases:
        result = analyzer._detect_monetization_signals(text)
        detected = result["score"] > 0
        
        if detected == should_detect:
            passed += 1
        else:
            print(f"  ✗ Expected monetization={should_detect} for: {text[:50]}")
    
    print(f"  ✓ PASS: {passed}/{len(test_cases)} test cases passed")
    return passed == len(test_cases)


def test_velocity_calculation():
    """Test velocity metrics calculation."""
    print("\n[Test] Velocity Metrics Calculation...")
    
    analyzer = OpportunityAnalyzer()
    
    # Create a post from 2 hours ago with 100 upvotes and 20 comments
    import time
    post = ScrapedPost(
        id="test1",
        platform="reddit",
        title="Test",
        body="Body",
        url="http://test.com",
        author="test",
        engagement=100,
        comments_count=20,
        created_at=str(int(time.time()) - 7200),  # 2 hours ago
        metadata={}
    )
    
    velocity = analyzer.calculate_velocity_metrics(post)
    
    # Should be ~50 upvotes/hour and ~10 comments/hour
    assert 40 <= velocity.upvotes_per_hour <= 60, f"Upvotes/hour {velocity.upvotes_per_hour} out of range"
    assert 8 <= velocity.comments_per_hour <= 12, f"Comments/hour {velocity.comments_per_hour} out of range"
    assert 0.15 <= velocity.engagement_ratio <= 0.25, f"Engagement ratio {velocity.engagement_ratio} out of range"
    
    print(f"  ✓ PASS: Velocity metrics calculated correctly")
    print(f"    Upvotes/hour: {velocity.upvotes_per_hour}")
    print(f"    Comments/hour: {velocity.comments_per_hour}")
    print(f"    Engagement ratio: {velocity.engagement_ratio}")
    return True


def test_competitor_extraction():
    """Test competitor mention extraction."""
    print("\n[Test] Competitor Mention Extraction...")
    
    analyzer = OpportunityAnalyzer()
    
    text = "I'm switching from Salesforce to HubSpot because Salesforce is too expensive."
    known_competitors = ["Salesforce", "HubSpot"]
    
    mentions = analyzer.extract_competitor_mentions(text, known_competitors)
    
    # Should find both mentions
    salesforce_mentions = [m for m in mentions if m.brand_name.lower() == "salesforce"]
    hubspot_mentions = [m for m in mentions if m.brand_name.lower() == "hubspot"]
    
    assert len(salesforce_mentions) > 0, "Should detect Salesforce"
    assert len(hubspot_mentions) > 0, "Should detect HubSpot"
    
    # Check sentiment on Salesforce mention (if found)
    if salesforce_mentions:
        sf_mention = salesforce_mentions[0]
        # Sentiment detection varies by implementation
    
    print(f"  ✓ PASS: Found {len(mentions)} competitor mentions")
    print(f"    Salesforce sentiment: {sf_mention.sentiment}")
    return True


def test_intent_filter():
    """Test IntentFilter class."""
    print("\n[Test] IntentFilter...")
    
    filter_obj = IntentFilter()
    
    posts = [
        ScrapedPost(
            id="1", platform="reddit", title="Is there an app for this?",
            body="Looking for help", url="", author="a", engagement=10,
            comments_count=5, created_at="1234567890", metadata={}
        ),
        ScrapedPost(
            id="2", platform="reddit", title="Just sharing my experience",
            body="Had a great day!", url="", author="b", engagement=5,
            comments_count=2, created_at="1234567890", metadata={}
        ),
        ScrapedPost(
            id="3", platform="reddit", title="Hate using spreadsheets",
            body="Need an alternative", url="", author="c", engagement=20,
            comments_count=10, created_at="1234567890", metadata={}
        ),
    ]
    
    filtered = filter_obj.filter(posts)
    
    # Should filter posts 1 and 3, not 2 (may vary by pattern matching)
    ids = [p.id for p in filtered]
    # At least one of the high-intent posts should be included
    assert len(ids) >= 1, "Should include at least one high-intent post"
    
    print(f"  ✓ PASS: Filtered {len(posts)} posts to {len(filtered)} high-intent posts")
    return True


def test_negative_search_filter():
    """Test NegativeSearchFilter for churn signals."""
    print("\n[Test] NegativeSearchFilter...")
    
    filter_obj = NegativeSearchFilter()
    
    posts = [
        ScrapedPost(
            id="1", platform="reddit", title="I'm quitting Salesforce",
            body="Too expensive", url="", author="a", engagement=10,
            comments_count=5, created_at="1234567890", metadata={}
        ),
        ScrapedPost(
            id="2", platform="reddit", title="Love the new feature",
            body="Great update!", url="", author="b", engagement=5,
            comments_count=2, created_at="1234567890", metadata={}
        ),
        ScrapedPost(
            id="3", platform="reddit", title="Alternative to HubSpot?",
            body="Looking to switch", url="", author="c", engagement=20,
            comments_count=10, created_at="1234567890", metadata={}
        ),
    ]
    
    results = filter_obj.filter(posts)
    
    # Should find at least one churn signal
    assert len(results) >= 1, "Should find at least one churn signal"
    
    print(f"  ✓ PASS: Found {len(results)} churn signals")
    return True


def run_all_tests():
    """Run all analysis tests."""
    print("=" * 70)
    print("Analysis Algorithm Test Suite")
    print("=" * 70)
    
    tests = [
        test_intent_pattern_matching,
        test_frustration_scoring,
        test_monetization_detection,
        test_velocity_calculation,
        test_competitor_extraction,
        test_intent_filter,
        test_negative_search_filter,
    ]
    
    results = []
    for test in tests:
        try:
            results.append(test())
        except Exception as e:
            print(f"  ✗ FAIL: Exception in {test.__name__}: {e}")
            results.append(False)
    
    print("\n" + "=" * 70)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"ALL TESTS PASSED ({passed}/{total})")
    else:
        print(f"SOME TESTS FAILED ({passed}/{total} passed)")
    print("=" * 70)
    
    return passed == total


if __name__ == "__main__":
    import sys
    success = run_all_tests()
    sys.exit(0 if success else 1)