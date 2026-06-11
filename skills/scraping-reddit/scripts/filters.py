#!/usr/bin/env python3
"""
Advanced Scraping & Filtering Capabilities.

Provides semantic filters to isolate signal from noise:
- Keyword pattern matching for high-intent phrases
- Sentiment & aggravation scoring
- Velocity tracking
- Competitor mention extraction
"""
import re
import time
from typing import List, Dict, Any, Optional, Callable, Tuple
from dataclasses import dataclass
from collections import defaultdict

from scripts.utils import ScrapedPost, VelocityMetrics, CompetitorMention


# =============================================================================
# SEMANTIC FILTER CLASSES
# =============================================================================

class SemanticFilter:
    """Base class for semantic filters."""
    
    def filter(self, posts: List[ScrapedPost]) -> List[ScrapedPost]:
        """Apply filter to posts."""
        raise NotImplementedError


class IntentFilter(SemanticFilter):
    """
    Filter posts by high-intent keyword patterns.
    
    Triggers on phrases like:
    - "Is there an app for..."
    - "I hate it when..."
    - "Why is [Competitor] so expensive?"
    - "How do I [Task] without [Tool]?"
    """
    
    DEFAULT_PATTERNS = [
        # App/tool requests
        (r"is there an?\s+(?:app|tool|software|platform)\s+(?:for|to)\s+", "app_request"),
        (r"looking for\s+(?:an?|some)\s+(?:app|tool|software)", "tool_seek"),
        (r"(?:need|want)\s+(?:an?|some)\s+(?:app|tool|software)\s+(?:for|to)", "tool_seek"),
        (r"(?:recommend|suggest)\s+(?:an?|some)\s+(?:app|tool|software)", "recommendation_seek"),
        
        # Problem expressions
        (r"i hate\s+(?:it when|that|how)\s+", "hate_expression"),
        (r"(?:frustrated|annoyed|irritated)\s+(?:with|by|that)\s+", "frustration"),
        (r"(?:tired of|sick of)\s+", "fatigue"),
        (r"(?:struggling|having trouble)\s+(?:with|to)\s+", "struggle"),
        
        # Alternative seeking
        (r"(?:alternative|replacement)\s+(?:to|for)\s+\w+", "alternative_seek"),
        (r"(?:switching|migrating)\s+(?:from|to|away from)\s+\w+", "migration"),
        (r"(?:quitting|leaving)\s+\w+", "churn"),
        (r"(?:stopped|not)\s+(?:using|paying)\s+\w+", "churn"),
        
        # Opportunity gaps
        (r"why (?:hasn't|has not|doesn't|does not)\s+(?:someone|anyone)\s+(?:built|created|made)", "opportunity_gap"),
        (r"someone should\s+(?:build|create|make)\s+", "suggestion"),
        (r"i wish\s+(?:someone|there was|i could)\s+", "wish"),
        
        # Manual process pain
        (r"(?:doing|managing)\s+.+?\s+(?:manually|by hand|in excel|in sheets)", "manual_process"),
        (r"(?:spending|wasting)\s+(?:hours|time)\s+", "time_waste"),
        (r"(?:spreadsheet|excel)\s+(?:hell|nightmare|mess)", "tool_limitation"),
        
        # Price sensitivity
        (r"why is\s+\w+\s+so\s+(?:expensive|pricey|costly)", "price_pain"),
        (r"(?:too expensive|overpriced|can't afford)", "price_pain"),
        (r"(?:cheaper|affordable|free)\s+(?:alternative|option)", "price_conscious"),
        
        # Willingness to pay
        (r"would\s+(?:definitely\s+)?pay\s+(?:for|money)", "payment_willingness"),
        (r"(?:i'd|i would)\s+pay\s+(?:for|if|to)", "payment_willingness"),
        (r"(?:worth|worthy of)\s+(?:the\s+)?(?:price|cost|money)", "value_acknowledgment"),
    ]
    
    def __init__(self, patterns: Optional[List[tuple]] = None, min_confidence: float = 0.5):
        self.patterns = patterns or self.DEFAULT_PATTERNS
        self.min_confidence = min_confidence
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), label)
            for pattern, label in self.patterns
        ]
    
    def filter(self, posts: List[ScrapedPost]) -> List[ScrapedPost]:
        """Filter posts by intent patterns."""
        filtered = []
        
        for post in posts:
            text = f"{post.title} {post.body}".lower()
            matches = []
            
            for pattern, label in self._compiled_patterns:
                if pattern.search(text):
                    matches.append(label)
            
            if matches:
                # Store matches in metadata
                post.metadata["intent_matches"] = matches
                post.metadata["intent_confidence"] = min(1.0, len(matches) * 0.2)
                filtered.append(post)
        
        return filtered
    
    def score_post(self, post: ScrapedPost) -> float:
        """Score a single post by intent strength (0-100)."""
        text = f"{post.title} {post.body}".lower()
        score = 0.0
        
        for pattern, label in self._compiled_patterns:
            if pattern.search(text):
                # Higher score for more specific patterns
                if label in ["payment_willingness", "opportunity_gap"]:
                    score += 25
                elif label in ["churn", "alternative_seek"]:
                    score += 20
                else:
                    score += 15
        
        return min(100, score)


class NegativeSearchFilter(SemanticFilter):
    """
    The "Negative Search" - find people quitting products.
    
    Searches for:
    - "I'm quitting [Product]"
    - "Leaving [Product] for..."
    - "Switching away from [Product]"
    
    This provides:
    - List of ready-to-churn users
    - What not to build in your own app
    """
    
    CHURN_PATTERNS = [
        (r"(?:i'm|i am|we're|we are)\s+(?:quitting|leaving)\s+(\w+)", "quitting"),
        (r"(?:cancelled|canceled)\s+(?:my|our)\s+(?:subscription|account|plan)\s+(?:with|to)?\s*(\w*)", "cancelled"),
        (r"(?:switching|migrating|moving)\s+(?:away from|from)\s+(\w+)", "migration"),
        (r"(?:done with|fed up with|tired of)\s+(\w+)", "fatigue"),
        (r"(?:looking for|need)\s+(?:an?|some)\s+(?:alternative|replacement)\s+(?:to|for)\s+(\w+)", "alternative_seek"),
        (r"(?:not|stopped)\s+(?:using|paying for|recommending)\s+(\w+)", "stopped_using"),
        (r"(?:why i left|why we left|why i quit)\s+(\w*)", "post_mortem"),
        (r"(?:disappointed|frustrated)\s+(?:with|by)\s+(\w+)", "disappointment"),
    ]
    
    # Common false positives to filter out
    FALSE_POSITIVES = ["my", "the", "this", "that", "it", "we", "you", "they"]
    
    def __init__(self, target_products: Optional[List[str]] = None):
        self.target_products = [p.lower() for p in target_products] if target_products else None
        self._compiled_patterns = [
            (re.compile(pattern, re.IGNORECASE), label)
            for pattern, label in self.CHURN_PATTERNS
        ]
    
    def filter(self, posts: List[ScrapedPost]) -> List[Dict[str, Any]]:
        """
        Filter posts for churn/negative signals.
        
        Returns enriched results with extracted product names.
        """
        results = []
        
        for post in posts:
            text = f"{post.title} {post.body}".lower()
            
            for pattern, churn_type in self._compiled_patterns:
                matches = pattern.finditer(text)
                
                for match in matches:
                    # Extract product name if captured
                    product = match.group(1) if match.groups() else None
                    
                    # Filter false positives
                    if product and product.lower() in self.FALSE_POSITIVES:
                        continue
                    
                    # If targeting specific products, filter
                    if self.target_products:
                        if not product or product.lower() not in self.target_products:
                            continue
                    
                    results.append({
                        "post": post,
                        "churn_type": churn_type,
                        "product": product,
                        "matched_text": match.group(0),
                        "context": self._extract_context(text, match.start(), match.end())
                    })
        
        return results
    
    def _extract_context(self, text: str, start: int, end: int, window: int = 100) -> str:
        """Extract context around the match."""
        ctx_start = max(0, start - window)
        ctx_end = min(len(text), end + window)
        return text[ctx_start:ctx_end].strip()


class VelocityFilter:
    """
    Velocity Tracking - compare "Upvotes per Hour" vs "Comments per Hour".
    
    High comment-to-upvote ratios usually indicate:
    - Controversial topics
    - Deeply felt problems
    - Active discussion/pain points
    """
    
    def __init__(
        self,
        min_upvotes_per_hour: float = 0.5,
        min_comments_per_hour: float = 0.1,
        min_engagement_ratio: float = 0.05
    ):
        self.min_upvotes_per_hour = min_upvotes_per_hour
        self.min_comments_per_hour = min_comments_per_hour
        self.min_engagement_ratio = min_engagement_ratio
    
    def filter_by_velocity(
        self,
        posts: List[ScrapedPost],
        min_viral_probability: float = 0.0
    ) -> List[Tuple[ScrapedPost, VelocityMetrics]]:
        """
        Filter posts by engagement velocity.
        
        Returns posts with their velocity metrics.
        """
        from scripts.analysis import OpportunityAnalyzer
        
        analyzer = OpportunityAnalyzer()
        results = []
        
        for post in posts:
            velocity = analyzer.calculate_velocity_metrics(post)
            
            # Apply filters
            if velocity.upvotes_per_hour < self.min_upvotes_per_hour:
                continue
            if velocity.comments_per_hour < self.min_comments_per_hour:
                continue
            if velocity.engagement_ratio < self.min_engagement_ratio:
                continue
            if velocity.viral_probability < min_viral_probability:
                continue
            
            # Store velocity in metadata
            post.metadata["velocity"] = {
                "upvotes_per_hour": velocity.upvotes_per_hour,
                "comments_per_hour": velocity.comments_per_hour,
                "engagement_ratio": velocity.engagement_ratio,
                "viral_probability": velocity.viral_probability
            }
            
            results.append((post, velocity))
        
        # Sort by viral probability
        results.sort(key=lambda x: x[1].viral_probability, reverse=True)
        return results
    
    def find_controversial_posts(
        self,
        posts: List[ScrapedPost],
        min_ratio: float = 0.3
    ) -> List[Tuple[ScrapedPost, float]]:
        """
        Find posts with high comment-to-upvote ratio (controversial/painful).
        
        Args:
            posts: List of posts to analyze
            min_ratio: Minimum comments/upvotes ratio (0.3 = 30 comments per 100 upvotes)
        """
        controversial = []
        
        for post in posts:
            if post.engagement <= 0:
                continue
            
            ratio = post.comments_count / post.engagement
            
            if ratio >= min_ratio:
                controversial.append((post, ratio))
        
        # Sort by ratio descending
        controversial.sort(key=lambda x: x[1], reverse=True)
        return controversial


class CompetitorFilter:
    """
    Competitor Mention Extractor.
    
    Automatically identifies and groups mentions of existing SaaS products
    to find gaps in their features.
    """
    
    def __init__(self, known_competitors: List[str]):
        self.known_competitors = [c.lower() for c in known_competitors]
    
    def extract_mentions(self, posts: List[ScrapedPost]) -> Dict[str, List[Dict[str, Any]]]:
        """
        Extract competitor mentions from posts.
        
        Returns dict mapping competitor name to list of mentions.
        """
        from scripts.analysis import OpportunityAnalyzer
        
        analyzer = OpportunityAnalyzer()
        mentions_by_competitor = defaultdict(list)
        
        for post in posts:
            text = f"{post.title} {post.body}"
            
            mentions = analyzer.extract_competitor_mentions(text, self.known_competitors)
            
            for mention in mentions:
                mentions_by_competitor[mention.brand_name].append({
                    "post_id": post.id,
                    "post_title": post.title,
                    "mention_type": mention.mention_type,
                    "context": mention.context,
                    "sentiment": mention.sentiment,
                    "intent": mention.intent
                })
        
        return dict(mentions_by_competitor)
    
    def find_competitor_gaps(
        self,
        posts: List[ScrapedPost]
    ) -> List[Dict[str, Any]]:
        """
        Find feature gaps mentioned in competitor context.
        
        Returns list of potential gaps with supporting evidence.
        """
        gaps = []
        
        # Patterns indicating missing features
        gap_patterns = [
            r"(?:wish|hope)\s+(?:it|they)\s+(?:had|would add|could add)\s+(.+?)(?:\.|$)",
            r"(?:missing|needs?|lacks?)\s+(?:a\s+)?(.+?)(?:\.|$)",
            r"(?:would be great|it would be nice)\s+(?:to have|if)\s+(.+?)(?:\.|$)",
            r"(?:only|biggest)\s+(?:complaint|issue|problem)\s+(?:is|with)\s+(.+?)(?:\.|$)",
        ]
        
        for post in posts:
            text = f"{post.title} {post.body}".lower()
            
            # Check if any competitor is mentioned
            has_competitor = any(
                comp in text for comp in self.known_competitors
            )
            
            if not has_competitor:
                continue
            
            # Look for gap patterns
            for pattern in gap_patterns:
                matches = re.finditer(pattern, text, re.IGNORECASE)
                for match in matches:
                    gap_description = match.group(1).strip() if match.groups() else match.group(0)
                    
                    if len(gap_description) > 10:
                        gaps.append({
                            "gap_description": gap_description[:200],
                            "post_id": post.id,
                            "post_title": post.title,
                            "full_context": text[:300],
                            "confidence": "high" if "wish" in text or "missing" in text else "medium"
                        })
        
        # Deduplicate
        seen = set()
        unique_gaps = []
        for gap in gaps:
            key = re.sub(r'[^\w]', '', gap["gap_description"].lower())[:40]
            if key not in seen:
                seen.add(key)
                unique_gaps.append(gap)
        
        return unique_gaps[:20]  # Top 20


# =============================================================================
# FILTER COMPOSITION
# =============================================================================

class FilterChain:
    """Chain multiple filters together."""
    
    def __init__(self, filters: Optional[List[Callable]] = None):
        self.filters = filters or []
    
    def add(self, filter_fn: Callable):
        """Add a filter to the chain."""
        self.filters.append(filter_fn)
    
    def apply(self, posts: List[ScrapedPost]) -> List[ScrapedPost]:
        """Apply all filters in sequence."""
        result = posts
        for filter_fn in self.filters:
            if isinstance(filter_fn, SemanticFilter):
                result = filter_fn.filter(result)
            else:
                result = filter_fn(result)
        return result


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def filter_high_intent_posts(
    posts: List[ScrapedPost],
    min_confidence: float = 0.3
) -> List[ScrapedPost]:
    """
    Convenience function to filter posts for high-intent signals.
    
    Args:
        posts: List of posts to filter
        min_confidence: Minimum intent confidence score
        
    Returns:
        Filtered list of high-intent posts
    """
    filter_obj = IntentFilter(min_confidence=min_confidence)
    return filter_obj.filter(posts)


def find_churn_signals(
    posts: List[ScrapedPost],
    target_products: Optional[List[str]] = None
) -> List[Dict[str, Any]]:
    """
    Convenience function to find churn/negative signals.
    
    Args:
        posts: List of posts to analyze
        target_products: Optional list of specific products to track
        
    Returns:
        List of posts with churn signals and extracted context
    """
    filter_obj = NegativeSearchFilter(target_products=target_products)
    return filter_obj.filter(posts)


def find_controversial_posts(
    posts: List[ScrapedPost],
    min_ratio: float = 0.3
) -> List[Tuple[ScrapedPost, float]]:
    """
    Find posts with high discussion relative to upvotes.
    
    Args:
        posts: List of posts to analyze
        min_ratio: Minimum comments/upvotes ratio
        
    Returns:
        List of (post, ratio) tuples sorted by ratio
    """
    filter_obj = VelocityFilter()
    return filter_obj.find_controversial_posts(posts, min_ratio)