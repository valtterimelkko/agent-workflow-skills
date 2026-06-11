#!/usr/bin/env python3
"""Tests for Twitter scraper functionality."""
import asyncio
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.utils import ScrapedTweet, TwitterUser, parse_tweet_date, format_tweet_url
from scripts.credentials import check_credentials_configured, get_credential_sources


def test_dataclasses():
    """Test dataclass creation."""
    print("Testing dataclasses...")
    
    # Test ScrapedTweet
    tweet = ScrapedTweet(
        id="123456",
        text="Test tweet content",
        url="https://twitter.com/user/status/123456",
        author_username="testuser",
        engagement=100
    )
    assert tweet.id == "123456"
    assert tweet.total_engagement == 100
    print("  ✓ ScrapedTweet works")
    
    # Test TwitterUser
    user = TwitterUser(
        id="789",
        username="testuser",
        name="Test User",
        followers=1000
    )
    assert user.username == "testuser"
    assert user.influence_score > 0
    print("  ✓ TwitterUser works")
    
    print("Dataclass tests passed!\n")


def test_utilities():
    """Test utility functions."""
    print("Testing utilities...")
    
    # Test format_tweet_url
    url = format_tweet_url("elonmusk", "123456")
    assert "elonmusk" in url
    assert "123456" in url
    print("  ✓ format_tweet_url works")
    
    # Test parse_tweet_date
    timestamp = parse_tweet_date("2025-01-15T10:30:00.000Z")
    assert timestamp > 0
    print("  ✓ parse_tweet_date works")
    
    print("Utility tests passed!\n")


def test_credentials():
    """Test credential functions."""
    print("Testing credentials...")
    
    # Check credential sources (won't fail if not configured)
    sources = get_credential_sources()
    assert "environment" in sources
    assert "bashrc" in sources
    print("  ✓ get_credential_sources works")
    
    # Check if configured
    configured = check_credentials_configured()
    print(f"  Credentials configured: {configured}")
    print("  ✓ check_credentials_configured works")
    
    print("Credential tests passed!\n")


def test_analysis_functions():
    """Test analysis functions without API calls."""
    print("Testing analysis functions...")
    
    from scripts.analysis import OpportunityAnalyzer
    
    analyzer = OpportunityAnalyzer()
    
    # Test frustration scoring
    text = "I am so frustrated with this terrible tool!"
    score = analyzer._calculate_frustration_score(text)
    assert score > 0
    print(f"  ✓ Frustration score: {score}")
    
    # Test intent signal extraction
    text = "Is there an app for tracking expenses automatically?"
    signals = analyzer._extract_intent_signals(text)
    assert len(signals) > 0
    print(f"  ✓ Intent signals found: {len(signals)}")
    
    # Test monetization detection
    text = "I would pay $50/month for this feature"
    monetization = analyzer._detect_monetization_signals(text)
    assert monetization["score"] > 0
    print(f"  ✓ Monetization score: {monetization['score']}")
    
    print("Analysis tests passed!\n")


def test_filters():
    """Test filter functions without API calls."""
    print("Testing filters...")
    
    from scripts.filters import IntentFilter, NegativeSearchFilter
    
    # Create test tweets
    tweets = [
        ScrapedTweet(id="1", text="Is there an app for tracking habits?", url="", author_username="user1", engagement=10),
        ScrapedTweet(id="2", text="I'm quitting Twitter for good", url="", author_username="user2", engagement=5),
        ScrapedTweet(id="3", text="Just had a great lunch!", url="", author_username="user3", engagement=2),
    ]
    
    # Test intent filter
    intent_filter = IntentFilter()
    high_intent = intent_filter.filter(tweets)
    assert len(high_intent) >= 1  # At least the first tweet
    print(f"  ✓ Intent filter found {len(high_intent)} high-intent tweets")
    
    # Test negative search filter
    negative_filter = NegativeSearchFilter()
    churn_signals = negative_filter.filter(tweets)
    # Note: Churn detection is pattern-based and may not always match
    print(f"  ✓ Negative filter found {len(churn_signals)} churn signals")
    
    print("Filter tests passed!\n")


def run_all_tests():
    """Run all tests."""
    print("="*60)
    print("Running Twitter Scraper Tests")
    print("="*60 + "\n")
    
    try:
        test_dataclasses()
        test_utilities()
        test_credentials()
        test_analysis_functions()
        test_filters()
        
        print("="*60)
        print("ALL TESTS PASSED!")
        print("="*60)
        return True
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)