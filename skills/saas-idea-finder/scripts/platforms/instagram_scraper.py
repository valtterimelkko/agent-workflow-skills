#!/usr/bin/env python3
"""Instagram scraper for SaaS idea discovery via Xpoz MCP.

Focus: Hashtag monitoring, engagement quality analysis, comment analysis.
Uses actual Xpoz API: getInstagramPostsByKeywords
"""
import re
import json
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from .base_scraper import BaseScraper, ScrapedPost
except ImportError:
    from base_scraper import BaseScraper, ScrapedPost

sys.path.insert(0, str(Path(__file__).parent))
try:
    from consumer_scraper_enhanced import ConsumerProblemDetectionMixin
except ImportError:
    class ConsumerProblemDetectionMixin:
        pass


class InstagramScraper(BaseScraper, ConsumerProblemDetectionMixin):
    """Scrape Instagram for business trends and opportunities.
    
    Enhanced with consumer-specific problem detection.
    """

    # Hashtag clusters by lens type
    HASHTAG_CLUSTERS = {
        "devtools_ai": [
            "codelife", "developer", "programming", "aitools"
        ],
        "ecommerce_sellers": [
            "etsyshop", "shopify", "onlineshop", "smallbusinessowner",
            "handmadebusiness", "expensive", "businessstruggles", "entrepreneurlife"
        ],
        "creator_economy": [
            "contentcreator", "influencerlife", "ugccommunity",
            "creatorlife", "influencer", "contentcreatorstruggles", "burnout", "creatorlife"
        ],
        "infra_automation": [
            "automation", "nocode", "workflow", "productivity"
        ],
        "small_business_ops": [
            "smallbusiness", "shopsmall", "supportsmallbusiness",
            "handmade", "shoplocal", "businessowner", "smallbusinessstruggles", "busylife", "hustleculture"
        ],
        "digital_marketing": [
            "digitalmarketing", "socialmediamarketing", "marketingtips",
            "seo", "contentmarketing"
        ],
        "data_analytics": [
            "datavisualization", "analytics", "dashboard", "excel"
        ]
    }

    # Engagement quality thresholds
    ENGAGEMENT_THRESHOLDS = {
        "save_rate_high": 0.03,      # Saves / likes > 3% = high intent
        "share_rate_high": 0.01,     # Shares / likes > 1% = viral potential
        "comment_question_rate": 0.05,  # Questions / comments > 5%
    }

    # Instagram-specific pain patterns
    INSTAGRAM_PAIN_PATTERNS = [
        r"struggling with",
        r"need help with",
        r"anyone know how to",
        r"wish there was",
        r"tired of doing this manually",
        r"wasting so much time",
        r"does anyone else",
        r"how do you",
    ]

    # Instagram-specific patterns
    INSTAGRAM_PATTERNS = {
        "cta_patterns": [
            r"link in bio",
            r"shop now",
            r"dm me",
            r"swipe up",
        ],
        "tutorial_patterns": [
            r"how to",
            r"tutorial",
            r"step by step",
            r"guide",
        ],
        "business_patterns": [
            r"small business",
            r"side hustle",
            r"passive income",
            r"work from home",
        ]
    }

    def __init__(self, xpoz_client):
        super().__init__(xpoz_client)
        # Extend pain patterns with Instagram-specific ones
        self.PAIN_PATTERNS = self.PAIN_PATTERNS + self.INSTAGRAM_PAIN_PATTERNS

    async def scrape_for_lens(
        self,
        lens_key: str,
        limit: int = 50
    ) -> List[ScrapedPost]:
        """
        Scrape Instagram based on lens configuration.

        Args:
            lens_key: Lens identifier
            limit: Maximum posts to return

        Returns:
            List of processed Instagram posts
        """
        hashtags = self.HASHTAG_CLUSTERS.get(lens_key, [])
        if not hashtags:
            print(f"Warning: No Instagram hashtags for lens '{lens_key}'")
            return []

        all_posts = []

        for hashtag in hashtags[:4]:
            try:
                posts = await self._search_hashtag(hashtag, limit // len(hashtags))
                all_posts.extend(posts)
            except Exception as e:
                print(f"Warning: Instagram search failed for #{hashtag}: {e}")

        # Calculate scores and analyze engagement
        for post in all_posts:
            post.pain_score = self.calculate_pain_score(post.body)
            
            # Enhanced consumer opportunity scoring
            consumer_score, consumer_details = self.calculate_consumer_opportunity_score(post)
            base_opp_score = self.calculate_opportunity_score(post)
            post.opportunity_score = max(base_opp_score, consumer_score * 0.8)
            post.metadata['consumer_analysis'] = consumer_details
            
            post.metadata["engagement_quality"] = self._analyze_engagement_quality(post)
            post.metadata["content_signals"] = self._detect_content_signals(post.body)
            
            has_consumer_signals = consumer_details.get('signals_detected', 0) > 0
            post.is_high_opportunity = (
                post.metadata.get("engagement_quality", {}).get("is_high_intent", False) or
                post.pain_score >= 0.3 or
                (has_consumer_signals and consumer_score >= 40)
            )

        # Deduplicate and sort
        unique_posts = self.deduplicate_posts(all_posts)
        return sorted(unique_posts, key=lambda x: x.opportunity_score, reverse=True)

    async def _search_hashtag(
        self,
        hashtag: str,
        limit: int
    ) -> List[ScrapedPost]:
        """Search Instagram by hashtag via Xpoz MCP."""
        try:
            result = await self.xpoz.call_tool(
                "getInstagramPostsByKeywords",  # Actual tool name from Xpoz
                {
                    "query": f"#{hashtag}",  # Use query parameter with #
                    "limit": limit
                }
            )

            return self._process_instagram_results(result, hashtag)

        except Exception as e:
            print(f"Warning: Xpoz Instagram search failed for #{hashtag}: {e}")
            return []

    def _process_instagram_results(
        self,
        result: Dict[str, Any],
        hashtag: str
    ) -> List[ScrapedPost]:
        """Process raw Xpoz Instagram results."""
        posts = []

        # Handle different response formats from Xpoz
        content = result.get("content", [])
        
        if not content:
            return posts

        # Xpoz returns content as a list of text items
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                
                # Try JSON first
                try:
                    data = json.loads(text)
                    if isinstance(data, dict) and "data" in data:
                        instagram_data = data["data"]
                        if isinstance(instagram_data, list):
                            for post_data in instagram_data:
                                if isinstance(post_data, dict):
                                    posts.append(self._create_scraped_post(post_data, hashtag))
                        continue
                except json.JSONDecodeError:
                    pass
                
                # Try YAML-like format (Xpoz native format)
                yaml_posts = self._parse_xpoz_yaml_format(text, hashtag)
                posts.extend(yaml_posts)

        return posts

    def _parse_xpoz_yaml_format(self, text: str, hashtag: str) -> List[ScrapedPost]:
        """Parse Xpoz YAML-like data format for Instagram."""
        posts = []
        lines = text.strip().split('\n')
        
        header_fields = []
        in_data = False
        
        for line in lines:
            line = line.strip()
            
            # Look for results header: results[100]{id,caption,authorUsername...}
            if 'results[' in line and ']{' in line:
                match = re.search(r'\{([^}]+)\}', line)
                if match:
                    header_fields = match.group(1).split(',')
                in_data = True
                continue
            
            # Parse data lines (skip headers and metadata)
            if in_data and line and not line.startswith(('success:', 'data:', 'status:', 'operationId:')):
                # Handle CSV-like format with quoted values
                values = self._parse_csv_line(line)
                
                if len(values) >= 3 and header_fields:
                    # Map values to fields based on header
                    post_data = {}
                    for i, field in enumerate(header_fields):
                        if i < len(values):
                            post_data[field] = values[i]
                    
                    posts.append(self._create_scraped_post_from_yaml(post_data, hashtag))
        
        return posts

    def _parse_csv_line(self, line: str) -> List[str]:
        """Parse a CSV line handling quoted values."""
        values = []
        current = ""
        in_quotes = False
        
        for char in line:
            if char == '"':
                in_quotes = not in_quotes
            elif char == ',' and not in_quotes:
                values.append(current.strip())
                current = ""
            else:
                current += char
        values.append(current.strip())
        
        return values

    def _create_scraped_post_from_yaml(self, data: Dict[str, str], hashtag: str) -> ScrapedPost:
        """Create a ScrapedPost from YAML-format Instagram data."""
        # Map field names (handle variations in field naming)
        caption = data.get('caption', '').strip('"').replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        post_id = data.get('id', '')
        author = data.get('authorUsername', data.get('author', data.get('username', '')))
        created_at = data.get('createdAt', '').strip('"')
        
        # Get engagement metrics if available
        likes = int(data.get('likes', 0)) if 'likes' in data else 0
        comments = int(data.get('comments', 0)) if 'comments' in data else 0
        saves = int(data.get('saves', 0)) if 'saves' in data else 0
        
        return ScrapedPost(
            id=post_id,
            platform="instagram",
            title="",  # Instagram doesn't have titles
            body=caption,
            url=f"https://instagram.com/p/{post_id}" if post_id else "",
            author=author,
            engagement=likes,
            comments_count=comments,
            created_at=created_at,
            metadata={
                "hashtag_searched": hashtag,
                "likes": likes,
                "saves": saves,
                "source": "xpoz_yaml"
            }
        )

    def _create_scraped_post(self, item: Dict[str, Any], hashtag: str) -> ScrapedPost:
        """Create a ScrapedPost from JSON-format Instagram data."""
        # Get engagement metrics
        likes = item.get("likes", item.get("like_count", 0))
        comments = item.get("comments", item.get("comment_count", 0))
        saves = item.get("saves", item.get("save_count", 0))
        
        # Get post ID
        post_id = str(item.get("id", item.get("shortcode", "")))
        
        # Build URL
        url = item.get("url", "")
        if not url and post_id:
            url = f"https://instagram.com/p/{post_id}"
        
        return ScrapedPost(
            id=post_id,
            platform="instagram",
            title="",
            body=item.get("caption", item.get("text", "")),
            url=url,
            author=item.get("author", item.get("username", item.get("user", {}).get("username", ""))),
            engagement=likes,
            comments_count=comments,
            created_at=str(item.get("created_at", item.get("timestamp", ""))),
            metadata={
                "hashtag_searched": hashtag,
                "likes": likes,
                "saves": saves,
                "is_reel": item.get("is_reel", item.get("media_type") == "VIDEO"),
                "is_carousel": item.get("is_carousel", False),
                "source": "xpoz_json"
            }
        )

    def _analyze_engagement_quality(self, post: ScrapedPost) -> Dict[str, Any]:
        """Analyze engagement quality beyond simple counts."""
        likes = post.metadata.get("likes", post.engagement) or 1
        saves = post.metadata.get("saves", 0)
        shares = post.metadata.get("shares", 0)
        comments = post.comments_count

        save_rate = saves / likes if likes > 0 else 0
        share_rate = shares / likes if likes > 0 else 0

        return {
            "save_rate": round(save_rate, 4),
            "share_rate": round(share_rate, 4),
            "comments_per_like": round(comments / likes, 4) if likes > 0 else 0,
            "is_high_intent": save_rate >= self.ENGAGEMENT_THRESHOLDS["save_rate_high"],
            "is_viral_potential": share_rate >= self.ENGAGEMENT_THRESHOLDS["share_rate_high"],
            "quality_tier": self._get_quality_tier(save_rate, share_rate)
        }

    def _get_quality_tier(self, save_rate: float, share_rate: float) -> str:
        """Classify engagement quality tier."""
        if save_rate >= 0.05 and share_rate >= 0.02:
            return "exceptional"
        elif save_rate >= 0.03 or share_rate >= 0.01:
            return "high"
        elif save_rate >= 0.01:
            return "moderate"
        else:
            return "low"

    def _detect_content_signals(self, caption: str) -> Dict[str, bool]:
        """Detect business-relevant content signals."""
        if not caption:
            return {}

        caption_lower = caption.lower()
        signals = {}

        for signal_type, patterns in self.INSTAGRAM_PATTERNS.items():
            signals[signal_type] = any(
                re.search(p, caption_lower)
                for p in patterns
            )

        return signals

    async def find_small_business_profiles(
        self,
        hashtags: List[str],
        min_followers: int = 1000,
        max_followers: int = 100000
    ) -> List[Dict[str, Any]]:
        """
        Find small business profiles in a niche.

        Small businesses (1K-100K followers) often have high pain points.
        """
        # This would require profile search capability from Xpoz
        # Placeholder implementation
        return [{
            "note": "Profile discovery requires additional Xpoz capabilities",
            "workaround": "Analyze post authors manually"
        }]