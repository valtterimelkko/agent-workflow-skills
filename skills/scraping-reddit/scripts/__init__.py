#!/usr/bin/env python3
"""
Reddit SaaS Opportunity Hunter - Scraping Reddit Skill

A production-quality Reddit scraping toolkit for discovering unaddressed user
frustrations and emerging market trends for software development.

Usage:
    from scripts import RedditScraper, OpportunityAnalyzer, RedditNavigator
    
    scraper = RedditScraper()
    navigator = RedditNavigator(scraper)
    analyzer = OpportunityAnalyzer()
    
    # Find relevant subreddits
    subreddits = await navigator.get_relevant_subreddits("marketing")
    
    # Get posts and analyze
    posts = await scraper.get_subreddit_posts("startups", limit=50)
    for post in posts:
        analysis = analyzer.analyze_post(post)
        if analysis["intent_signals"]:
            print(f"Opportunity found: {post.title}")
    
    await scraper.close()
"""

# Core scraper
from scripts.reddit_scraper import RedditScraper, CircuitBreaker, RedditOAuth2Manager

# Analysis
from scripts.analysis import OpportunityAnalyzer

# Navigation
from scripts.navigation import RedditNavigator

# Synthesis
from scripts.synthesis import TrendAnalyzer, CrossPollinationAnalyzer, IdeaSynthesizer

# Filters
from scripts.filters import (
    IntentFilter,
    NegativeSearchFilter,
    VelocityFilter,
    CompetitorFilter,
    FilterChain,
    filter_high_intent_posts,
    find_churn_signals,
    find_controversial_posts
)

# Utilities
from scripts.utils import (
    ScrapedPost,
    ScrapedComment,
    SubredditInfo,
    Contributor,
    WikiPage,
    VelocityMetrics,
    CompetitorMention,
    OpportunitySignal,
    TrendReport,
    CrossPollinationReport
)

# Credentials
from scripts.credentials import (
    load_reddit_proxy_url,
    load_reddit_oauth_credentials,
    check_proxy_configured,
    check_oauth_configured
)

__version__ = "1.0.0"
__all__ = [
    # Core
    "RedditScraper",
    "CircuitBreaker",
    "RedditOAuth2Manager",
    
    # Analysis
    "OpportunityAnalyzer",
    
    # Navigation
    "RedditNavigator",
    
    # Synthesis
    "TrendAnalyzer",
    "CrossPollinationAnalyzer",
    "IdeaSynthesizer",
    
    # Filters
    "IntentFilter",
    "NegativeSearchFilter",
    "VelocityFilter",
    "CompetitorFilter",
    "FilterChain",
    "filter_high_intent_posts",
    "find_churn_signals",
    "find_controversial_posts",
    
    # Utils
    "ScrapedPost",
    "ScrapedComment",
    "SubredditInfo",
    "Contributor",
    "WikiPage",
    "VelocityMetrics",
    "CompetitorMention",
    "OpportunitySignal",
    "TrendReport",
    "CrossPollinationReport",
    
    # Credentials
    "load_reddit_proxy_url",
    "load_reddit_oauth_credentials",
    "check_proxy_configured",
    "check_oauth_configured",
]