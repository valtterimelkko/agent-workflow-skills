#!/usr/bin/env python3
"""Base scraper class with common functionality."""
import re
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field


@dataclass
class ScrapedPost:
    """Standardized post structure across platforms."""
    id: str
    platform: str
    title: str
    body: str
    url: str
    author: str
    engagement: int  # Platform-specific (upvotes, likes, etc.)
    comments_count: int
    created_at: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Computed fields
    pain_score: float = 0.0
    opportunity_score: float = 0.0
    is_high_opportunity: bool = False


class BaseScraper(ABC):
    """Base class for all platform scrapers."""

    # Common pain point patterns (override in subclasses for platform-specific)
    PAIN_PATTERNS = [
        r"wish there was (an?|some) (app|tool|software|platform)",
        r"(frustrated|annoyed|hate) (with|that|when) (using|trying)",
        r"(hours|time) (every|each|spent|wasting) (week|day|manual|spreadsheet)",
        r"(would|i'd) pay (for|money|if|someone)",
        r"why (isn't|hasn't|doesn't) (someone|anyone) (built|created|made)",
        r"someone should (build|create|make)",
        r"(built|using) (a|an) (spreadsheet|excel|google sheets) (to|for)",
        r"(struggling|hard time) (with|to) (find|get|manage)",
        r"any (tool|app|software) (that|which|to)",
        r"(tired of|sick of) (manually|having to)",
    ]

    def __init__(self, xpoz_client):
        self.xpoz = xpoz_client

    @abstractmethod
    async def scrape_for_lens(self, lens_key: str, limit: int = 50) -> List[ScrapedPost]:
        """Scrape posts based on lens configuration."""
        pass

    def calculate_pain_score(self, text: str) -> float:
        """Calculate pain point score based on pattern matching."""
        if not text:
            return 0.0

        text_lower = text.lower()
        matches = sum(
            1 for pattern in self.PAIN_PATTERNS
            if re.search(pattern, text_lower, re.IGNORECASE)
        )

        # Normalize to 0-1 scale
        return min(matches / 3, 1.0)

    def calculate_opportunity_score(self, post: ScrapedPost) -> float:
        """Calculate overall opportunity score."""
        pain_weight = 0.4
        engagement_weight = 0.3
        recency_weight = 0.2
        specificity_weight = 0.1

        # Pain score (already 0-1)
        pain = post.pain_score

        # Engagement (normalize based on platform)
        engagement = min(post.engagement / 100, 1.0)

        # Specificity (longer, more detailed posts are better)
        text_length = len(post.body or "")
        specificity = min(text_length / 500, 1.0)

        # Combine
        score = (
            pain * pain_weight +
            engagement * engagement_weight +
            specificity * specificity_weight
        )

        return round(score * 100, 1)

    def deduplicate_posts(self, posts: List[ScrapedPost]) -> List[ScrapedPost]:
        """Remove duplicate posts based on title similarity."""
        seen = set()
        unique = []

        for post in posts:
            # Create a normalized key from title or body
            key_source = post.title if post.title else post.body
            key = re.sub(r'[^a-z0-9]', '', key_source.lower())[:50]
            if key not in seen:
                seen.add(key)
                unique.append(post)

        return unique