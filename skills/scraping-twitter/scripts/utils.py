#!/usr/bin/env python3
"""Utility classes and dataclasses for Twitter scraping."""
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class ScrapedTweet:
    """Standardized tweet structure."""
    id: str
    platform: str = "twitter"
    text: str = ""
    url: str = ""
    author_username: str = ""
    author_name: str = ""
    author_verified: bool = False
    author_followers: int = 0
    engagement: int = 0  # Like count
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


@dataclass
class ScrapedReply:
    """Standardized reply/comment structure."""
    id: str
    tweet_id: str
    parent_id: Optional[str]
    author_username: str = ""
    author_name: str = ""
    text: str = ""
    engagement: int = 0
    created_at: str = ""
    replies: List['ScrapedReply'] = field(default_factory=list)
    depth: int = 0
    
    # Analysis fields
    agreement_indicators: int = 0
    sentiment_score: float = 0.0


@dataclass
class TwitterUser:
    """Twitter user profile metadata."""
    id: str
    username: str
    name: str
    description: str = ""
    location: str = ""
    url: str = ""
    profile_image: str = ""
    cover_image: str = ""
    verified: bool = False
    verified_type: str = ""  # blue, business, government
    followers: int = 0
    following: int = 0
    tweet_count: int = 0
    listed_count: int = 0
    favourites_count: int = 0
    media_count: int = 0
    created_at: str = ""
    can_dm: bool = False
    pinned_tweet_ids: List[str] = field(default_factory=list)
    
    @property
    def influence_score(self) -> float:
        """Calculate influence score based on followers and engagement."""
        if self.followers == 0:
            return 0.0
        # Log scale for follower count to avoid extreme values
        import math
        follower_score = min(100, math.log10(self.followers + 1) * 10)
        # Penalty for low follower/following ratio (possible bot)
        if self.following > 0:
            ratio = self.followers / self.following
            if ratio < 0.1:
                follower_score *= 0.5
        return follower_score


@dataclass
class TrendingTopic:
    """Trending topic data."""
    name: str
    query: str
    tweet_volume: Optional[int] = None
    rank: int = 0
    location: str = ""
    woeid: int = 1  # 1 = worldwide


@dataclass
class TweetThread:
    """A thread of related tweets (conversation)."""
    root_tweet_id: str
    tweets: List[ScrapedTweet] = field(default_factory=list)
    replies: List[ScrapedReply] = field(default_factory=list)
    
    @property
    def total_engagement(self) -> int:
        """Sum of all engagement in the thread."""
        tweet_engagement = sum(t.total_engagement for t in self.tweets)
        reply_engagement = sum(r.engagement for r in self.replies)
        return tweet_engagement + reply_engagement
    
    @property
    def unique_authors(self) -> int:
        """Count of unique authors in the thread."""
        authors = set(t.author_username for t in self.tweets)
        authors.update(r.author_username for r in self.replies)
        return len(authors)


@dataclass
class RateLimitInfo:
    """Track rate limit status from API responses."""
    remaining: Optional[int] = None
    reset_timestamp: Optional[int] = None
    used: Optional[int] = None
    
    def should_slow_down(self) -> bool:
        """Check if we're approaching rate limit."""
        if self.remaining is not None and self.remaining < 5:
            return True
        return False
    
    def get_wait_time(self) -> float:
        """Calculate how long to wait before next request."""
        if self.reset_timestamp:
            now = int(time.time())
            wait = self.reset_timestamp - now + 1
            return max(wait, 5.0)  # Minimum 5 seconds for safety
        return 5.0


@dataclass
class VelocityMetrics:
    """Engagement velocity tracking for tweets."""
    likes_per_hour: float
    replies_per_hour: float
    retweets_per_hour: float
    engagement_ratio: float  # replies/likes
    acceleration: float
    viral_probability: float
    time_since_post: float  # hours


@dataclass
class CompetitorMention:
    """Competitor mention in tweet/reply."""
    brand_name: str
    mention_type: str  # direct, comparison, alternative, complaint, praise
    context: str
    sentiment: float  # -1 to 1
    intent: str  # switching, researching, complaining, praising


@dataclass
class OpportunitySignal:
    """Synthesized SaaS opportunity signal."""
    opportunity_score: float  # 0-100
    priority: str  # high, medium, low, monitor
    
    # Component scores
    intent_score: float
    frustration_score: float
    velocity_score: float
    trend_score: float
    monetization_score: float
    
    # Details
    problem_statement: str
    target_audience: str
    suggested_features: List[str]
    tech_stack_hints: List[str]
    competitor_gaps: List[str]
    recommended_action: str


@dataclass
class TrendReport:
    """Trend persistence analysis."""
    keyword: str
    is_persistent: bool
    mention_count_7d: int
    mention_count_30d: int
    growth_rate: float  # percentage
    consistency_score: float  # 0-1
    seasonality_detected: bool
    prediction: str  # growing, stable, declining


@dataclass
class HashtagAnalysis:
    """Analysis of hashtag usage and reach."""
    hashtag: str
    tweet_count: int
    unique_authors: int
    total_engagement: int
    top_tweets: List[ScrapedTweet]
    velocity: float  # tweets per hour
    related_hashtags: List[str]


@dataclass
class SearchPagination:
    """Pagination state for search queries."""
    has_next_page: bool
    next_cursor: Optional[str]
    last_min_id: Optional[str]
    query: str


def parse_tweet_date(date_str: str) -> float:
    """Parse Twitter date string to Unix timestamp."""
    from datetime import datetime
    try:
        # Twitter API format: "2025-01-15T10:30:00.000Z"
        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")
        return dt.timestamp()
    except (ValueError, TypeError):
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%SZ")
            return dt.timestamp()
        except (ValueError, TypeError):
            return time.time()


def format_tweet_url(username: str, tweet_id: str) -> str:
    """Generate Twitter URL for a tweet."""
    return f"https://twitter.com/{username}/status/{tweet_id}"


def extract_hashtags(text: str) -> List[str]:
    """Extract hashtags from tweet text."""
    import re
    hashtags = re.findall(r'#(\w+)', text)
    return [h.lower() for h in hashtags]


def extract_mentions(text: str) -> List[str]:
    """Extract @mentions from tweet text."""
    import re
    mentions = re.findall(r'@(\w+)', text)
    return [m.lower() for m in mentions]


def calculate_engagement_rate(tweet: ScrapedTweet) -> float:
    """Calculate engagement rate for a tweet."""
    if tweet.author_followers == 0:
        return 0.0
    total = tweet.total_engagement
    return (total / tweet.author_followers) * 100