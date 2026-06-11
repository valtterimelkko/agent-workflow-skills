---
name: scraping-twitter
description: "Production-quality Twitter/X scraping skill for discovering SaaS opportunities. Navigate Twitter programmatically to identify unaddressed user frustrations, high-intent signals, and emerging market trends. Uses TwitterAPI.io for fast, cost-effective data extraction with simple API key authentication. Provides tactical navigation (user discovery, hashtag analysis), advanced filtering (intent patterns, sentiment scoring, velocity tracking), and idea synthesis (trend persistence, cross-pollination detection). Use when: (1) Researching SaaS opportunities on Twitter/X, (2) Analyzing competitor mentions and gaps, (3) Finding high-intent user pain points, (4) Tracking hashtag trends, (5) Discovering cross-niche opportunities."
---

# Skill: Twitter/X SaaS Opportunity Hunter

Production-quality Twitter/X scraping toolkit for discovering unaddressed user frustrations and emerging market trends for software development.

## Overview

This skill provides a comprehensive framework for Twitter-based SaaS opportunity discovery through three distinct layers:

1. **Navigation** - Where to look (user discovery, hashtag analysis, conversation exploration)
2. **Extraction** - What to pull (high-intent patterns, sentiment scoring, velocity tracking)
3. **Synthesis** - How to interpret (trend persistence, cross-pollination, opportunity scoring)

Powered by [TwitterAPI.io](https://twitterapi.io) - no Twitter developer account required, simple API key authentication, and cost-effective pricing at ~$0.15 per 1,000 tweets.

## Prerequisites

### Required Credentials

The skill uses the hierarchical credential loading strategy from `saas-idea-finder`:

1. **Environment variables** (highest priority)
2. **Optional vault/secret store** (for service users like openclaw)
3. **Shell startup file** such as `~/.bashrc` (fallback)

**Environment variables:**
```bash
export TWITTERAPI_KEY="your_twitterapi_key"
```

**Optional vault/secret store setup:**
```bash
vault kv put secret/skills-apis/twitterapi/api_key value="your_api_key"
```

### Getting a TwitterAPI.io Key

1. Go to https://twitterapi.io/
2. Sign up for an account (no credit card required for free tier)
3. Copy your API key from the dashboard
4. Add to environment or vault as shown above

### Rate Limits & Pricing

| User Type | Rate Limit | Cost |
|-----------|------------|------|
| Free Trial | 1 req / 5 seconds | $0.10 free credit |
| Paid | 20+ QPS | $0.15 per 1,000 tweets |
| Enterprise | 1000+ QPS | Custom pricing |

## Quick Start

### Basic Usage

```python
import asyncio
from scripts import TwitterScraper, OpportunityAnalyzer

async def main():
    # Initialize scraper (auto-loads credentials)
    scraper = TwitterScraper()
    
    # Search tweets
    tweets, pagination = await scraper.search_tweets("#buildinpublic", limit=50)
    
    # Analyze for opportunities
    analyzer = OpportunityAnalyzer()
    for tweet in tweets:
        analysis = analyzer.analyze_tweet(tweet)
        if analysis["intent_signals"]:
            print(f"💡 Opportunity: {tweet.text[:100]}...")
            print(f"   Problem: {analysis['problem_statement']}")
    
    await scraper.close()

asyncio.run(main())
```

### High-Level Synthesis

```python
from scripts import TwitterScraper, IdeaSynthesizer

async def main():
    scraper = TwitterScraper()
    synthesizer = IdeaSynthesizer(scraper)
    
    # Comprehensive analysis across hashtags
    report = await synthesizer.analyze_opportunity(
        hashtags=["buildinpublic", "indiehacker", "SaaS"],
        keywords=["automation", "AI", "workflow"],
        known_competitors=["Zapier", "Notion", "Airtable"],
        min_opportunity_score=60
    )
    
    print(f"Found {report['summary']['high_opportunity_count']} high-opportunity signals")
    print(f"Average score: {report['summary']['average_opportunity_score']}")
    
    for opp in report['opportunities'][:5]:
        signal = opp['opportunity']
        print(f"\n🎯 {signal['opportunity_score']}/100 - {signal['priority'].upper()}")
        print(f"   Problem: {signal['problem_statement'][:100]}...")
        print(f"   Action: {signal['recommended_action']}")
    
    await scraper.close()
```

## Tactical Navigation Functions

### Find Relevant Users

```python
from scripts import TwitterScraper, TwitterNavigator

scraper = TwitterScraper()
navigator = TwitterNavigator(scraper)

# Find influencers in your target niche
users = await navigator.find_relevant_users(
    niche_keyword="ecommerce",
    limit=10,
    min_followers=5000
)

for user in users:
    print(f"@{user['user'].username}: {user['user'].followers:,} followers")
    print(f"   Relevance: {user['relevance_score']:.1f}")
    print(f"   Influence: {user['influence_score']:.1f}")
```

### Analyze Hashtags

```python
# Discover relevant hashtags and their metrics
hashtags = await navigator.get_relevant_hashtags(
    niche_keyword="productivity",
    limit=10
)

for hashtag in hashtags:
    print(f"#{hashtag.hashtag}:")
    print(f"   Tweets: {hashtag.tweet_count}")
    print(f"   Unique authors: {hashtag.unique_authors}")
    print(f"   Velocity: {hashtag.velocity} tweets/hour")
    print(f"   Related: {', '.join(hashtag.related_hashtags[:5])}")
```

### Identify Top Contributors

```python
# Find "power users" who spark high-engagement conversations
contributors = await navigator.identify_top_contributors(
    hashtag="buildinpublic",
    limit=15,
    activity_lookback=100
)

for c in contributors[:5]:
    print(f"@{c['username']}: {c['tweet_count']} tweets")
    print(f"   Avg engagement: {c['avg_engagement_per_tweet']}")
    print(f"   Quality score: {c['quality_score']}")
```

### Explore Conversation Threads

```python
# Deep dive into a conversation thread
thread = await navigator.explore_conversation_thread(
    tweet_id="1234567890",
    max_depth=3
)

print(f"Thread tweets: {len(thread.tweets)}")
print(f"Total replies: {len(thread.replies)}")
print(f"Unique authors: {thread.unique_authors}")
print(f"Total engagement: {thread.total_engagement}")
```

## Advanced Filtering Capabilities

### Intent Pattern Matching

```python
from scripts.filters import IntentFilter, filter_high_intent_tweets

# Filter for high-intent phrases
intent_filter = IntentFilter()
filtered_tweets = intent_filter.filter(tweets)

# Or use the convenience function
high_intent = filter_high_intent_tweets(tweets, min_confidence=0.3)

for tweet in high_intent:
    matches = tweet.metadata.get("intent_matches", [])
    print(f"🎯 {tweet.text[:80]}...")
    print(f"   Signals: {', '.join(matches)}")
```

### The "Negative Search" (Churn Signals)

```python
from scripts.filters import NegativeSearchFilter, find_churn_signals

# Find people quitting products (ready-to-churn users)
churn_signals = find_churn_signals(
    tweets,
    target_products=["Salesforce", "HubSpot"]  # Optional: focus on specific products
)

for signal in churn_signals:
    print(f"⚠️  {signal['churn_type'].upper()}: {signal['tweet'].text[:80]}...")
    if signal['product']:
        print(f"   Product: {signal['product']}")
    print(f"   Context: {signal['context'][:150]}...")
```

### Velocity Tracking

```python
from scripts.filters import VelocityFilter, find_controversial_tweets

# Find tweets with high engagement velocity
velocity_filter = VelocityFilter(
    min_likes_per_hour=1.0,
    min_replies_per_hour=0.1,
    min_engagement_ratio=0.05
)
hot_tweets = velocity_filter.filter_by_velocity(tweets)

# High reply-to-like ratio = controversial/painful
controversial = find_controversial_tweets(tweets, min_ratio=0.3)

for tweet, ratio in controversial[:5]:
    print(f"🔥 {ratio:.2f} ratio: {tweet.text[:80]}...")
    print(f"   {tweet.reply_count} replies / {tweet.engagement} likes")
```

### Competitor Mention Extraction

```python
from scripts.filters import CompetitorFilter

# Track mentions of known competitors
competitor_filter = CompetitorFilter(
    known_competitors=["Salesforce", "HubSpot", "Zapier"]
)

mentions = competitor_filter.extract_mentions(tweets)
for brand, mentions_list in mentions.items():
    print(f"📊 {brand}: {len(mentions_list)} mentions")
    for m in mentions_list[:3]:
        print(f"   {m['mention_type']} - {m['intent']}")

# Find feature gaps
gaps = competitor_filter.find_competitor_gaps(tweets)
for gap in gaps[:5]:
    print(f"🕳️  Gap: {gap['gap_description']}")
    print(f"   Confidence: {gap['confidence']}")
```

### Hashtag Filtering

```python
from scripts.filters import HashtagFilter, filter_by_hashtags

# Filter tweets by specific hashtags
hashtag_filter = HashtagFilter(["buildinpublic", "indiehacker"])
filtered = hashtag_filter.filter(tweets)

# Or use the convenience function
filtered = filter_by_hashtags(tweets, ["saas", "b2b"])

# Analyze hashtag usage
analysis = hashtag_filter.analyze_hashtags(tweets)
for hashtag, stats in analysis.items():
    print(f"#{hashtag}: {stats['tweet_count']} tweets, "
          f"{stats['unique_authors']} authors, "
          f"avg {stats['avg_engagement']:.1f} engagement")
```

## Idea Synthesis

### Trend Persistence Check

```python
from scripts import TrendAnalyzer

trend_analyzer = TrendAnalyzer(scraper)

# Check if a problem is a "fad" or "chronic pain point"
report = await trend_analyzer.check_trend_persistence(
    keyword="inventory management",
    hashtags=["ecommerce", "shopify"],
    days=30
)

print(f"Keyword: {report.keyword}")
print(f"Is persistent: {report.is_persistent}")
print(f"7-day mentions: {report.mention_count_7d}")
print(f"30-day mentions: {report.mention_count_30d}")
print(f"Growth rate: {report.growth_rate:+.1f}%")
print(f"Prediction: {report.prediction}")
```

### Cross-Pollination Detection

```python
from scripts import CrossPollinationAnalyzer

cross_analyzer = CrossPollinationAnalyzer(scraper)

# Find similar problems across different niches
report = await cross_analyzer.find_cross_pollination(
    hashtag_a="EtsySeller",
    hashtag_b="AmazonFBA"
)

print(f"Similarity score: {report['similarity_score']:.2f}")
print(f"Opportunity type: {report['opportunity_type']}")
print(f"Shared keywords: {', '.join(report['shared_keywords'][:10])}")

# Pain points in both communities
for pain in report['pain_points_a'][:5]:
    print(f"  A: {pain}")
for pain in report['pain_points_b'][:5]:
    print(f"  B: {pain}")
```

### Comprehensive Opportunity Analysis

```python
from scripts import IdeaSynthesizer

synthesizer = IdeaSynthesizer(scraper)

# Full synthesis pipeline
report = await synthesizer.analyze_opportunity(
    hashtags=["buildinpublic", "indiehacker", "SaaS"],
    keywords=["automation", "AI", "workflow"],
    known_competitors=["Zapier", "Make", "n8n"],
    min_opportunity_score=65
)

summary = report['summary']
print(f"Priority distribution: {summary['priority_distribution']}")
print(f"Avg opportunity score: {summary['average_opportunity_score']}")
print(f"Avg frustration score: {summary['average_frustration_score']}")

print("\nTop suggested features:")
for feature, count in summary['top_suggested_features'][:5]:
    print(f"  • {feature} ({count} mentions)")

print(f"\nRecommendation: {summary['recommendation']}")
```

## Data Models

### ScrapedTweet

```python
@dataclass
class ScrapedTweet:
    id: str
    platform: str = "twitter"
    text: str = ""
    url: str = ""
    author_username: str = ""
    author_name: str = ""
    author_verified: bool = False
    author_followers: int = 0
    engagement: int = 0           # Like count
    reply_count: int = 0
    retweet_count: int = 0
    quote_count: int = 0
    view_count: Optional[int] = None
    created_at: str = ""
    language: str = "en"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Computed fields
    pain_score: float = 0.0
    opportunity_score: float = 0.0
    is_high_opportunity: bool = False
    
    @property
    def total_engagement(self) -> int:
        """Calculate total engagement across all metrics."""
        return self.engagement + self.reply_count + self.retweet_count + self.quote_count
```

### OpportunitySignal

```python
@dataclass
class OpportunitySignal:
    opportunity_score: float      # 0-100
    priority: str                 # high, medium, low, monitor
    intent_score: float
    frustration_score: float
    velocity_score: float
    trend_score: float
    monetization_score: float
    problem_statement: str
    target_audience: str
    suggested_features: List[str]
    tech_stack_hints: List[str]
    competitor_gaps: List[str]
    recommended_action: str
```

## Testing

### Run Tests

```bash
# All tests
python3 tests/run_tests.py

# Or directly
python3 tests/test_scraper.py
```

### Test Coverage

Tests validate:
- **Dataclass creation**: All models instantiate correctly
- **Analysis functions**: Intent detection, frustration scoring, monetization signals
- **Filter functions**: Intent filtering, churn detection
- **Credential loading**: Hierarchy works correctly

## Pro Tips

### The "Negative Search"

Don't just search for what people want. Search for "I'm quitting [Product]":

```python
# This finds ready-to-churn users and tells you what NOT to build
churn_signals = find_churn_signals(tweets, target_products=["CompetitorX"])

for signal in churn_signals:
    print(f"Why they're leaving: {signal['context']}")
    # Build the OPPOSITE of these complaints
```

### High Reply-to-Like Ratio

Tweets with high replies relative to likes often indicate:
- Controversial topics
- Deeply felt problems
- Active pain points

```python
controversial = find_controversial_tweets(tweets, min_ratio=0.3)
# These are goldmines for SaaS opportunities
```

### Cross-Hashtag Validation

If the same problem exists in #EtsySeller AND #AmazonFBA:
- It's likely a universal pain point
- Solution can potentially serve both markets
- Higher total addressable market

```python
report = await cross_analyzer.find_cross_pollination("EtsySeller", "AmazonFBA")
if report['similarity_score'] > 0.3:
    print("Cross-niche opportunity detected!")
```

### Advanced Search Operators

TwitterAPI.io supports Twitter's advanced search operators:

```python
# Search by user
tweets, _ = await scraper.search_tweets("from:elonmusk", limit=50)

# Search by mention
tweets, _ = await scraper.search_tweets("@twitter", limit=50)

# Search with minimum engagement
tweets, _ = await scraper.search_tweets("python min_retweets:10", limit=50)

# Exclude replies
tweets, _ = await scraper.search_tweets("saas -filter:replies", limit=50)

# Date range
tweets, _ = await scraper.search_tweets("startup since:2025-01-01", limit=50)

# Language filter
tweets, _ = await scraper.search_tweets("programming lang:en", limit=50)
```

## Error Handling

The scraper implements multiple resilience patterns:

- **Circuit Breaker**: Prevents cascading failures after 3 consecutive errors
- **Exponential Backoff**: 2^attempt seconds between retries
- **User-Agent Rotation**: 5 realistic browser UAs
- **Rate Limit Handling**: Automatic delay adjustment based on 429 responses

## Troubleshooting

### "No API key configured" Error

Set up your credentials:

```bash
# Environment variable
export TWITTERAPI_KEY="your_api_key"

# Or vault
vault kv put secret/skills-apis/twitterapi/api_key value="your_api_key"
```

### Rate Limiting (429 Errors)

The scraper automatically handles 429s with exponential backoff. To reduce frequency:
- Upgrade to paid TwitterAPI.io tier for higher QPS
- Increase delay between requests (modify `_min_delay` in scraper)

### Empty Results

If you get empty results:
- Check if the hashtag/keyword actually exists
- Try broader search terms
- Check your API key is valid and has credits

## Architecture

```
skills-global/scraping-twitter/
├── scripts/
│   ├── twitter_scraper.py   # Core scraper with TwitterAPI.io
│   ├── analysis.py          # Pain point & opportunity analysis
│   ├── navigation.py        # User/hashtag discovery
│   ├── synthesis.py         # Trend & cross-pollination analysis
│   ├── filters.py           # Semantic filtering
│   ├── credentials.py       # Credential loading (saas-idea-finder pattern)
│   └── utils.py             # Dataclasses & utilities
├── tests/
│   ├── test_scraper.py      # Scraper tests
│   └── run_tests.py         # Test runner
└── SKILL.md                 # This file
```

## References

- TwitterAPI.io documentation: https://twitterapi.io/
- Credential loading follows `saas-idea-finder` pattern
- Pricing: $0.15 per 1,000 tweets

## License

This skill follows the same patterns and robustness standards as `saas-idea-finder` and `scraping-reddit`.
