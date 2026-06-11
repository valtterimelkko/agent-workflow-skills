#!/usr/bin/env python3
"""Utility classes and dataclasses for Reddit scraping."""
import time
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional


@dataclass
class ScrapedPost:
    """Standardized post structure."""
    id: str
    platform: str
    title: str
    body: str
    url: str
    author: str
    engagement: int  # Upvotes/score
    comments_count: int
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Computed fields
    pain_score: float = 0.0
    opportunity_score: float = 0.0
    is_high_opportunity: bool = False


@dataclass
class ScrapedComment:
    """Standardized comment structure."""
    id: str
    post_id: str
    parent_id: str
    author: str
    body: str
    score: int
    created_utc: float
    replies: List['ScrapedComment'] = field(default_factory=list)
    depth: int = 0
    
    # Analysis fields
    agreement_indicators: int = 0  # "I agree", "me too", etc.
    sentiment_score: float = 0.0


@dataclass
class SubredditInfo:
    """Subreddit metadata."""
    name: str
    display_name: str
    subscribers: int
    accounts_active: int
    description: str
    public_description: str
    created_utc: float
    over18: bool
    url: str
    icon_img: Optional[str] = None


@dataclass
class Contributor:
    """Top contributor information."""
    username: str
    post_count: int
    comment_count: int
    total_engagement: int
    avg_engagement_per_post: float
    top_subreddits: List[str] = field(default_factory=list)


@dataclass
class WikiPage:
    """Wiki page content."""
    page: str
    title: str
    content_md: str
    content_html: str
    revision_date: float


@dataclass
class RateLimitInfo:
    """Track rate limit status from Reddit responses."""
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
            return max(wait, 6.0)  # Minimum 6 seconds for unauthenticated
        return 6.0


@dataclass
class OAuth2Token:
    """OAuth2 token for Reddit API authentication."""
    access_token: str
    expires_at: float
    token_type: str = "bearer"
    
    def is_expired(self) -> bool:
        """Check if token has expired (with 60 second buffer)."""
        return time.time() >= (self.expires_at - 60)


@dataclass
class VelocityMetrics:
    """Engagement velocity tracking."""
    upvotes_per_hour: float
    comments_per_hour: float
    engagement_ratio: float  # comments/upvotes
    acceleration: float
    viral_probability: float
    time_since_post: float  # hours


@dataclass
class CompetitorMention:
    """Competitor mention in post/comment."""
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
    mention_count_30d: int
    mention_count_90d: int
    growth_rate: float  # percentage
    consistency_score: float  # 0-1
    seasonality_detected: bool
    prediction: str  # growing, stable, declining


@dataclass
class CrossPollinationReport:
    """Cross-community opportunity detection."""
    subreddit_a: str
    subreddit_b: str
    similarity_score: float
    shared_keywords: List[str]
    pain_points_a: List[str]
    pain_points_b: List[str]
    opportunity_type: str  # expansion, adaptation, new_market