#!/usr/bin/env python3
"""
Twitter/X SaaS Opportunity Hunter - Scraping Twitter Skill

A production-quality Twitter/X scraping toolkit for discovering unaddressed user
frustrations and emerging market trends for software development.

Uses TwitterAPI.io for fast, cost-effective data extraction.

Usage:
    from scripts import TwitterScraper, OpportunityAnalyzer, TwitterNavigator
    
    scraper = TwitterScraper()
    navigator = TwitterNavigator(scraper)
    analyzer = OpportunityAnalyzer()
    
    # Find relevant users
    users = await navigator.find_relevant_users("marketing")
    
    # Search tweets and analyze
    tweets, _ = await scraper.search_tweets("#buildinpublic", limit=50)
    for tweet in tweets:
        analysis = analyzer.analyze_tweet(tweet)
        if analysis["intent_signals"]:
            print(f"Opportunity found: {tweet.text[:100]}...")
    
    await scraper.close()
"""

# Core scraper
from scripts.twitter_scraper import TwitterScraper, CircuitBreaker

# Analysis
from scripts.analysis import OpportunityAnalyzer

# Navigation
from scripts.navigation import TwitterNavigator, ConversationExplorer

# Synthesis
from scripts.synthesis import TrendAnalyzer, CrossPollinationAnalyzer, IdeaSynthesizer

# Filters
from scripts.filters import (
    IntentFilter,
    NegativeSearchFilter,
    VelocityFilter,
    CompetitorFilter,
    HashtagFilter,
    FilterChain,
    filter_high_intent_tweets,
    find_churn_signals,
    find_controversial_tweets,
    filter_by_hashtags
)

# Utilities
from scripts.utils import (
    ScrapedTweet,
    ScrapedReply,
    TwitterUser,
    TrendingTopic,
    TweetThread,
    VelocityMetrics,
    CompetitorMention,
    OpportunitySignal,
    TrendReport,
    HashtagAnalysis,
    SearchPagination,
    parse_tweet_date,
    format_tweet_url,
    extract_hashtags,
    extract_mentions,
    calculate_engagement_rate
)

# Credentials
from scripts.credentials import (
    load_twitterapi_key,
    check_credentials_configured,
    get_credential_sources,
    TwitterAPICredentialNotFound
)

__version__ = "1.0.0"
__all__ = [
    # Core
    "TwitterScraper",
    "CircuitBreaker",
    
    # Analysis
    "OpportunityAnalyzer",
    
    # Navigation
    "TwitterNavigator",
    "ConversationExplorer",
    
    # Synthesis
    "TrendAnalyzer",
    "CrossPollinationAnalyzer",
    "IdeaSynthesizer",
    
    # Filters
    "IntentFilter",
    "NegativeSearchFilter",
    "VelocityFilter",
    "CompetitorFilter",
    "HashtagFilter",
    "FilterChain",
    "filter_high_intent_tweets",
    "find_churn_signals",
    "find_controversial_tweets",
    "filter_by_hashtags",
    
    # Utils
    "ScrapedTweet",
    "ScrapedReply",
    "TwitterUser",
    "TrendingTopic",
    "TweetThread",
    "VelocityMetrics",
    "CompetitorMention",
    "OpportunitySignal",
    "TrendReport",
    "HashtagAnalysis",
    "SearchPagination",
    "parse_tweet_date",
    "format_tweet_url",
    "extract_hashtags",
    "extract_mentions",
    "calculate_engagement_rate",
    
    # Credentials
    "load_twitterapi_key",
    "check_credentials_configured",
    "get_credential_sources",
    "TwitterAPICredentialNotFound",
]