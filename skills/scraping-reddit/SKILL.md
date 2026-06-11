---
name: scraping-reddit
description: "Production-quality Reddit scraping skill for discovering SaaS opportunities. Navigate Reddit programmatically to identify unaddressed user frustrations, high-intent signals, and emerging market trends. Uses Reddit's legacy .json endpoints with OAuth2 support, circuit breaker patterns, and comprehensive error handling. Provides tactical navigation (subreddit discovery, wiki scanning, contributor analysis), advanced filtering (intent patterns, sentiment scoring, velocity tracking), and idea synthesis (trend persistence, cross-pollination detection). Use when: (1) Researching SaaS opportunities on Reddit, (2) Analyzing competitor mentions and gaps, (3) Finding high-intent user pain points, (4) Tracking trend persistence across communities, (5) Discovering cross-niche opportunities."
---

# Skill: Reddit SaaS Opportunity Hunter

Production-quality Reddit scraping toolkit for discovering unaddressed user frustrations and emerging market trends for software development.

## Overview

This skill provides a comprehensive framework for Reddit-based SaaS opportunity discovery through three distinct layers:

1. **Navigation** - Where to look (subreddit discovery, wiki scanning, contributor analysis)
2. **Extraction** - What to pull (high-intent patterns, sentiment scoring, velocity tracking)
3. **Synthesis** - How to interpret (trend persistence, cross-pollination, opportunity scoring)

## Prerequisites

### Required Credentials

The skill uses the same credential hierarchy as `saas-idea-finder`:

1. **Environment variables** (highest priority)
2. **Optional vault/secret store** (for service users like openclaw)
3. **Shell startup file** such as `~/.bashrc` (fallback)

**Environment variables:**
```bash
export REDDIT_PROXY_URL="http://user:pass@proxy:8080"  # Residential proxy (recommended)
export REDDIT_CLIENT_ID="your_reddit_app_id"           # OAuth2 (optional, for higher rate limits)
export REDDIT_CLIENT_SECRET="your_reddit_app_secret"   # OAuth2 (optional)
```

**Optional vault/secret store setup:**
```bash
vault kv put secret/skills-apis/reddit/proxy_url value="http://user:pass@proxy:8080"
vault kv put secret/skills-apis/reddit/client_id value="your_client_id"
vault kv put secret/skills-apis/reddit/client_secret value="your_client_secret"
```

### Rate Limits

- **Unauthenticated**: ~10 requests/minute (6 second delays)
- **OAuth2 Authenticated**: 100 requests/minute (0.6 second delays)
- **With Residential Proxy**: More reliable access, less blocking

## Quick Start

### Basic Usage

```python
import asyncio
from scripts import RedditScraper, OpportunityAnalyzer

async def main():
    # Initialize scraper (auto-loads credentials)
    scraper = RedditScraper()
    
    # Fetch posts from a subreddit
    posts = await scraper.get_subreddit_posts("startups", limit=50)
    
    # Analyze for opportunities
    analyzer = OpportunityAnalyzer()
    for post in posts:
        analysis = analyzer.analyze_post(post)
        if analysis["intent_signals"]:
            print(f"💡 Opportunity: {post.title}")
            print(f"   Problem: {analysis['problem_statement']}")
    
    await scraper.close()

asyncio.run(main())
```

### High-Level Synthesis

```python
from scripts import RedditScraper, IdeaSynthesizer

async def main():
    scraper = RedditScraper()
    synthesizer = IdeaSynthesizer(scraper)
    
    # Comprehensive analysis across multiple subreddits
    report = await synthesizer.analyze_opportunity(
        subreddits=["startups", "SaaS", "Entrepreneur"],
        known_competitors=["Salesforce", "HubSpot"],
        min_opportunity_score=60
    )
    
    print(f"Found {report['high_opportunity_count']} high-opportunity signals")
    print(f"Average score: {report['summary']['average_opportunity_score']}")
    
    for opp in report['opportunities'][:5]:
        signal = opp['opportunity']
        print(f"\n🎯 {signal['opportunity_score']}/100 - {signal['priority'].upper()}")
        print(f"   Problem: {signal['problem_statement'][:100]}...")
        print(f"   Action: {signal['recommended_action']}")
    
    await scraper.close()
```

## Tactical Navigation Functions

### Find Relevant Subreddits

```python
from scripts import RedditScraper, RedditNavigator

scraper = RedditScraper()
navigator = RedditNavigator(scraper)

# Find "watering holes" for your target audience
subreddits = await navigator.get_relevant_subreddits(
    niche_keyword="ecommerce",
    limit=10,
    min_subscribers=5000
)

for sub in subreddits:
    print(f"r/{sub['name']}: {sub['subscribers']:,} subscribers")
    print(f"   Relevance: {sub['relevance_score']:.1f}")
    print(f"   Activity: {sub['activity_ratio']:.3f}")
```

### Scan Community Wiki for Pain Points

```python
# Extract FAQs and common questions (literally lists of pain points)
wiki_analysis = await navigator.scan_community_wiki("startups")

print(f"Found {wiki_analysis['pain_point_count']} pain points:")
for pain in wiki_analysis['pain_points'][:10]:
    print(f"  • {pain}")

print(f"\nCommon questions:")
for q in wiki_analysis['common_questions'][:10]:
    print(f"  • {q}")
```

### Identify Top Contributors

```python
# Find "power users" who spark high-engagement debates
contributors = await navigator.identify_top_contributors(
    subreddit="startups",
    limit=15,
    activity_lookback=100
)

for c in contributors[:5]:
    print(f"u/{c['username']}: {c['post_count']} posts")
    print(f"   Avg engagement: {c['avg_engagement_per_post']}")
    print(f"   Quality score: {c['quality_score']}")
```

### Recursive Comment Threading

```python
# Fetch nested comments looking for "I agree" chains
thread_analysis = await navigator.recursive_comment_threading(
    subreddit="startups",
    post_id="abc123",
    max_depth=5
)

print(f"Total comments: {thread_analysis['total_comments']}")
print(f"Agreement ratio: {thread_analysis['agreement_ratio']:.1%}")
print(f"Pain amplification: {thread_analysis['pain_amplification']}")

# High-intent comments indicate strong demand
for comment in thread_analysis['high_intent_comments'][:5]:
    print(f"  💬 {comment['body'][:100]}...")
```

## Advanced Filtering Capabilities

### Intent Pattern Matching

```python
from scripts.filters import IntentFilter, filter_high_intent_posts

# Filter for high-intent phrases
intent_filter = IntentFilter()
filtered_posts = intent_filter.filter(posts)

# Or use the convenience function
high_intent = filter_high_intent_posts(posts, min_confidence=0.3)

for post in high_intent:
    matches = post.metadata.get("intent_matches", [])
    print(f"🎯 {post.title}")
    print(f"   Signals: {', '.join(matches)}")
```

### The "Negative Search" (Churn Signals)

```python
from scripts.filters import NegativeSearchFilter, find_churn_signals

# Find people quitting products (ready-to-churn users)
churn_signals = find_churn_signals(
    posts,
    target_products=["Salesforce", "HubSpot"]  # Optional: focus on specific products
)

for signal in churn_signals:
    print(f"⚠️  {signal['churn_type'].upper()}: {signal['post'].title}")
    if signal['product']:
        print(f"   Product: {signal['product']}")
    print(f"   Context: {signal['context'][:150]}...")
```

### Velocity Tracking

```python
from scripts.filters import VelocityFilter, find_controversial_posts

# Find posts with high engagement velocity
velocity_filter = VelocityFilter(
    min_upvotes_per_hour=1.0,
    min_engagement_ratio=0.1
)
hot_posts = velocity_filter.filter_by_velocity(posts)

# High comment-to-upvote ratio = controversial/painful
controversial = find_controversial_posts(posts, min_ratio=0.3)

for post, ratio in controversial[:5]:
    print(f"🔥 {ratio:.2f} ratio: {post.title}")
    print(f"   {post.comments_count} comments / {post.engagement} upvotes")
```

### Competitor Mention Extraction

```python
from scripts.filters import CompetitorFilter

# Track mentions of known competitors
competitor_filter = CompetitorFilter(
    known_competitors=["Salesforce", "HubSpot", "Zapier"]
)

mentions = competitor_filter.extract_mentions(posts)
for brand, mentions_list in mentions.items():
    print(f"📊 {brand}: {len(mentions_list)} mentions")
    for m in mentions_list[:3]:
        print(f"   {m['mention_type']} - {m['intent']}")

# Find feature gaps
gaps = competitor_filter.find_competitor_gaps(posts)
for gap in gaps[:5]:
    print(f"🕳️  Gap: {gap['gap_description']}")
    print(f"   Confidence: {gap['confidence']}")
```

## Idea Synthesis

### Trend Persistence Check

```python
from scripts import TrendAnalyzer

trend_analyzer = TrendAnalyzer(scraper)

# Check if a problem is a "fad" or "chronic pain point"
report = await trend_analyzer.check_trend_persistence(
    keyword="inventory management",
    subreddits=["smallbusiness", "Etsy", "AmazonFBA"],
    days=90
)

print(f"Keyword: {report.keyword}")
print(f"Is persistent: {report.is_persistent}")
print(f"30-day mentions: {report.mention_count_30d}")
print(f"90-day mentions: {report.mention_count_90d}")
print(f"Growth rate: {report.growth_rate:+.1f}%")
print(f"Prediction: {report.prediction}")
```

### Cross-Pollination Detection

```python
from scripts import CrossPollinationAnalyzer

cross_analyzer = CrossPollinationAnalyzer(scraper)

# Find similar problems across different niches
report = await cross_analyzer.find_cross_pollination(
    subreddit_a="EtsySellers",
    subreddit_b="AmazonFBA"
)

print(f"Similarity score: {report.similarity_score:.2f}")
print(f"Opportunity type: {report.opportunity_type}")
print(f"Shared keywords: {', '.join(report.shared_keywords[:10])}")

# Pain points in both communities
for pain in report.pain_points_a[:5]:
    print(f"  A: {pain}")
for pain in report.pain_points_b[:5]:
    print(f"  B: {pain}")
```

### Comprehensive Opportunity Analysis

```python
from scripts import IdeaSynthesizer

synthesizer = IdeaSynthesizer(scraper)

# Full synthesis pipeline
report = await synthesizer.analyze_opportunity(
    subreddits=["startups", "SaaS", "Entrepreneur", "marketing"],
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

### ScrapedPost

```python
@dataclass
class ScrapedPost:
    id: str
    platform: str
    title: str
    body: str
    url: str
    author: str
    engagement: int           # Upvotes/score
    comments_count: int
    created_at: str
    metadata: Dict[str, Any]  # subreddit, flair, upvote_ratio, etc.
    
    # Computed fields
    pain_score: float = 0.0
    opportunity_score: float = 0.0
    is_high_opportunity: bool = False
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

# Skip API calls (structural tests only)
python3 tests/run_tests.py --quick

# Analysis tests only
python3 tests/run_tests.py --analysis

# Scraper tests only
python3 tests/run_tests.py --scraper
```

### Quality Thresholds

Tests validate:
- **Intent detection**: >90% accuracy on test cases
- **Frustration scoring**: Within expected ranges
- **Data quality**: >15% pain point detection rate
- **API reliability**: <10% failure rate

## Pro Tips

### The "Negative Search"

Don't just search for what people want. Search for "I'm quitting [Product]":

```python
# This finds ready-to-churn users and tells you what NOT to build
churn_signals = find_churn_signals(posts, target_products=["CompetitorX"])

for signal in churn_signals:
    print(f"Why they're leaving: {signal['context']}")
    # Build the OPPOSITE of these complaints
```

### High Comment-to-Upvote Ratio

Posts with high comments relative to upvotes often indicate:
- Controversial topics
- Deeply felt problems
- Active pain points

```python
controversial = find_controversial_posts(posts, min_ratio=0.3)
# These are goldmines for SaaS opportunities
```

### Cross-Niche Validation

If the same problem exists in r/EtsySellers AND r/AmazonFBA:
- It's likely a universal pain point
- Solution can potentially serve both markets
- Higher total addressable market

```python
report = await cross_analyzer.find_cross_pollination("EtsySellers", "AmazonFBA")
if report.similarity_score > 0.3:
    print("Cross-niche opportunity detected!")
```

## Error Handling

The scraper implements multiple resilience patterns:

- **Circuit Breaker**: Prevents cascading failures after 3 consecutive errors
- **Exponential Backoff**: 2^attempt seconds between retries
- **User-Agent Rotation**: 7 realistic browser UAs
- **Proxy Support**: Automatic via credential hierarchy
- **Shadowban Detection**: Detects and works around blocks
- **Old Reddit Fallback**: Falls back to old.reddit.com on 403s

## Troubleshooting

### "No proxy configured" Warning

Reddit may block cloud/datacenter IPs. Set up a residential proxy:

```bash
export REDDIT_PROXY_URL="http://user:pass@residential.proxy:8080"
```

### Rate Limiting (429 Errors)

The scraper automatically handles 429s with exponential backoff. To reduce frequency:
- Use OAuth2 credentials (100 req/min vs 10 req/min)
- Use a residential proxy
- Increase `min_delay` in scraper initialization

### Empty Results

If you get empty results:
- Check if OAuth2 is configured (some endpoints require auth)
- Try different subreddits (some block API access)
- Check the subreddit actually exists and is public

## Architecture

```
skills-global/scraping-reddit/
├── scripts/
│   ├── reddit_scraper.py    # Core scraper with robustness patterns
│   ├── analysis.py          # Pain point & opportunity analysis
│   ├── navigation.py        # Subreddit/wiki discovery
│   ├── synthesis.py         # Trend & cross-pollination analysis
│   ├── filters.py           # Semantic filtering
│   ├── credentials.py       # Credential loading
│   └── utils.py             # Dataclasses & utilities
├── tests/
│   ├── test_scraper.py      # Scraper tests
│   ├── test_analysis.py     # Algorithm tests
│   └── run_tests.py         # Test runner
└── SKILL.md                 # This file
```

## References

- Reddit JSON API endpoints documented in `REFERENCES.md`
- Credential loading follows `saas-idea-finder` pattern
- Rate limits: 10 req/min (unauth), 100 req/min (OAuth)

## License

This skill follows the same patterns and robustness standards as `saas-idea-finder`.
