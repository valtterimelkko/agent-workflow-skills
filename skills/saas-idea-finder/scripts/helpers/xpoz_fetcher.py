#!/usr/bin/env python3
"""
Social media fetcher for saas-idea-finder.

Integrates with the existing discover_trends.py pipeline.
Uses TwitterAPI.io for Twitter/X and Xpoz MCP for Instagram.
Reddit is self-hosted via JSON API.
"""
import asyncio
import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

# Add paths
sys.path.insert(0, str(Path(__file__).parent.parent / "xpoz"))
sys.path.insert(0, str(Path(__file__).parent.parent / "platforms"))

# Import platform scrapers
try:
    from base_scraper import ScrapedPost
    from reddit_scraper import RedditScraper
    from twitter_scraper import TwitterScraper
    from instagram_scraper import InstagramScraper
except ImportError as e:
    print(f"Warning: Could not import platform scrapers: {e}", file=sys.stderr)
    # Define dummy classes for type hints
    class ScrapedPost:
        pass
    RedditScraper = None
    TwitterScraper = None
    InstagramScraper = None

# Import Xpoz client (only needed for Instagram now)
try:
    from xpoz_client import XpozMCPClient, XpozAPIError
    from xpoz_credentials import CredentialNotFoundError
    XPOZ_AVAILABLE = True
except ImportError as e:
    print(f"Warning: Could not import Xpoz client modules: {e}", file=sys.stderr)
    XpozMCPClient = None
    XpozAPIError = Exception
    CredentialNotFoundError = Exception
    XPOZ_AVAILABLE = False


class SocialMediaFetcher:
    """
    Unified social media fetcher.
    
    Uses:
    - Reddit: Self-hosted JSON API (always available)
    - Twitter/X: TwitterAPI.io direct REST API
    - Instagram: Xpoz MCP (optional, if credentials available)
    """

    def __init__(self):
        self._xpoz_client = None
        self._scrapers = {}
        self._is_connected = False

    async def connect(self) -> bool:
        """
        Initialize platform scrapers.

        Returns:
            True if at least one scraper is available
        """
        try:
            self._scrapers = {}
            
            # Reddit scraper - self-hosted, no Xpoz client needed
            if RedditScraper is not None:
                self._scrapers['reddit'] = RedditScraper()
                print("  Reddit scraper initialized (self-hosted JSON API)")
            else:
                print("Warning: RedditScraper not available", file=sys.stderr)
            
            # Twitter scraper - uses TwitterAPI.io, no Xpoz needed
            if TwitterScraper is not None:
                try:
                    self._scrapers['twitter'] = TwitterScraper()
                    print("  Twitter scraper initialized (TwitterAPI.io)")
                except Exception as e:
                    print(f"  Twitter scraper failed: {e}")
            else:
                print("Warning: TwitterScraper not available", file=sys.stderr)
            
            # Instagram scraper - still uses Xpoz if available
            # NOTE: Instagram is disabled by default due to Xpoz credit constraints
            # Set ENABLE_INSTAGRAM=1 to enable
            if InstagramScraper is not None and XPOZ_AVAILABLE and os.environ.get('ENABLE_INSTAGRAM') == '1':
                try:
                    self._xpoz_client = XpozMCPClient()
                    # 10 second timeout for Xpoz connection
                    await asyncio.wait_for(self._xpoz_client.connect(), timeout=10)
                    self._scrapers['instagram'] = InstagramScraper(self._xpoz_client)
                    print("  Instagram scraper initialized (Xpoz MCP)")
                except asyncio.TimeoutError:
                    print("  Instagram: Connection timeout, disabling")
                except (CredentialNotFoundError, XpozAPIError) as e:
                    print(f"  Xpoz not available for Instagram: {e}")
                    print("  Instagram scraping disabled")
            else:
                print("  Instagram scraping disabled (set ENABLE_INSTAGRAM=1 to enable)")

            if not self._scrapers:
                print("ERROR: No platform scrapers available", file=sys.stderr)
                return False

            self._is_connected = True
            return True

        except Exception as e:
            print(f"Social media initialization error: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return False

    async def close(self):
        """Close all connections."""
        # Close self-hosted scrapers (handle both sync and async close)
        for name, scraper in self._scrapers.items():
            if hasattr(scraper, 'close'):
                try:
                    close_result = scraper.close()
                    if asyncio.iscoroutine(close_result):
                        await close_result
                except Exception:
                    pass
        
        # Close Xpoz connection (for Instagram)
        if self._xpoz_client:
            await self._xpoz_client.close()
        
        self._is_connected = False

    async def fetch_for_lens(
        self,
        lens_name: str,
        platforms: Optional[List[str]] = None,
        limit_per_platform: int = 15
    ) -> Dict[str, Any]:
        """
        Fetch social trends for a given lens.

        Args:
            lens_name: Lens identifier (e.g., "ecommerce_sellers")
            platforms: Specific platforms to query (default: all)
            limit_per_platform: Max posts per platform (default 15 for speed)

        Returns:
            Dictionary with results by platform and aggregated topics
        """
        if not self._is_connected:
            raise RuntimeError("Not connected. Call connect() first.")

        # Map lens names to internal keys
        lens_key = self._normalize_lens_name(lens_name)

        # Determine platforms to query
        if platforms is None:
            platforms = list(self._scrapers.keys())

        results = {
            "lens": lens_name,
            "lens_key": lens_key,
            "timestamp": datetime.now().isoformat(),
            "platforms": {},
            "aggregated_topics": [],
            "errors": []
        }

        # Fetch from all platforms concurrently with individual timeouts
        async def fetch_platform(platform_name: str) -> tuple:
            """Fetch from a single platform with timeout."""
            scraper = self._scrapers[platform_name]
            try:
                # 90 second timeout per platform to prevent hanging
                posts = await asyncio.wait_for(
                    scraper.scrape_for_lens(lens_key, limit_per_platform),
                    timeout=90
                )
                return (platform_name, {
                    "posts": [self._post_to_dict(p) for p in posts],
                    "count": len(posts),
                    "high_opportunity_count": sum(1 for p in posts if p.is_high_opportunity)
                }, None)
            except asyncio.TimeoutError:
                return (platform_name, None, f"Timeout after 90s")
            except Exception as e:
                return (platform_name, None, str(e))

        # Run all platform fetches concurrently
        tasks = [fetch_platform(name) for name in platforms if name in self._scrapers]
        platform_results = await asyncio.gather(*tasks, return_exceptions=True)

        # Process results
        for result in platform_results:
            if isinstance(result, Exception):
                results["errors"].append({"platform": "unknown", "error": str(result)})
                continue
            
            platform_name, data, error = result
            if error:
                results["errors"].append({"platform": platform_name, "error": error})
                print(f"  ⚠️  {platform_name}: {error}", file=sys.stderr)
            elif data:
                results["platforms"][platform_name] = data
                print(f"  ✓ {platform_name}: {data['count']} posts ({data['high_opportunity_count']} high-opp)")

        # Aggregate topics across platforms
        results["aggregated_topics"] = self._aggregate_topics(results["platforms"])

        return results

    def _normalize_lens_name(self, lens_name: str) -> str:
        """Convert lens name to internal key format."""
        # Map common lens names to internal keys
        lens_mapping = {
            "developer tools monday": "devtools_ai",
            "devtools & ai": "devtools_ai",
            "e-commerce & sellers": "ecommerce_sellers",
            "business saas tuesday": "ecommerce_sellers",
            "ai/ml wednesday": "devtools_ai",
            "creator economy": "creator_economy",
            "infra & automation": "infra_automation",
            "infrastructure & devops": "infra_automation",
            "small business ops": "small_business_ops",
            "small business operations": "small_business_ops",
            "digital marketing": "digital_marketing",
            "data & analytics": "data_analytics",
            "productivity & automation": "infra_automation",
            "design & frontend": "devtools_ai",
        }

        normalized = lens_name.lower().strip()
        return lens_mapping.get(normalized, normalized.replace(" ", "_").replace("&", "and"))

    def _post_to_dict(self, post: ScrapedPost) -> Dict[str, Any]:
        """Convert ScrapedPost to dictionary for JSON serialization."""
        return {
            "id": post.id,
            "platform": post.platform,
            "title": post.title,
            "body": post.body[:500] if post.body else "",
            "url": post.url,
            "author": post.author,
            "engagement": post.engagement,
            "comments_count": post.comments_count,
            "pain_score": round(post.pain_score, 3),
            "opportunity_score": round(post.opportunity_score, 1),
            "is_high_opportunity": post.is_high_opportunity,
            "metadata": post.metadata
        }

    def _aggregate_topics(
        self,
        platforms_data: Dict[str, Dict]
    ) -> List[Dict[str, Any]]:
        """
        Aggregate and deduplicate topics across platforms.
        
        Enhanced with consumer problem detection and categorization.

        Returns topics sorted by cross-platform validation score.
        """
        # Extract all high-opportunity posts
        all_posts = []
        for platform, data in platforms_data.items():
            for post in data.get("posts", []):
                if post.get("is_high_opportunity"):
                    all_posts.append(post)

        if not all_posts:
            return []

        # Group by similar topics AND consumer problem categories
        topics = {}
        consumer_problem_topics = {}
        
        for post in all_posts:
            text = f"{post.get('title', '')} {post.get('body', '')}".lower()
            
            # Get consumer analysis from metadata
            consumer_analysis = post.get("metadata", {}).get("consumer_analysis", {})
            categories = consumer_analysis.get("categories", [])
            
            # Extract key phrases
            keywords = self._extract_keywords(text)
            
            # Also track consumer problem categories
            for category in categories:
                if category not in consumer_problem_topics:
                    consumer_problem_topics[category] = {
                        "keyword": f"{category}_problems",
                        "category": category,
                        "platforms": set(),
                        "posts": [],
                        "total_engagement": 0,
                        "avg_pain_score": 0,
                        "consumer_signals": 0,
                        "is_consumer_problem": True
                    }
                consumer_problem_topics[category]["platforms"].add(post["platform"])
                consumer_problem_topics[category]["posts"].append(post)
                consumer_problem_topics[category]["total_engagement"] += post.get("engagement", 0)
                consumer_problem_topics[category]["consumer_signals"] += consumer_analysis.get('signals_detected', 0)

            for keyword in keywords:
                if keyword not in topics:
                    topics[keyword] = {
                        "keyword": keyword,
                        "platforms": set(),
                        "posts": [],
                        "total_engagement": 0,
                        "avg_pain_score": 0,
                        "is_consumer_problem": False
                    }

                topics[keyword]["platforms"].add(post["platform"])
                topics[keyword]["posts"].append(post)
                topics[keyword]["total_engagement"] += post.get("engagement", 0)

        # Calculate scores and sort - merge regular and consumer problem topics
        aggregated = []
        
        # Process regular topics
        for keyword, data in topics.items():
            if len(data["posts"]) >= 2:  # At least 2 mentions
                avg_pain = sum(p.get("pain_score", 0) for p in data["posts"]) / len(data["posts"])
                cross_platform_bonus = len(data["platforms"]) * 10

                aggregated.append({
                    "topic": keyword,
                    "mention_count": len(data["posts"]),
                    "platforms": list(data["platforms"]),
                    "cross_platform_count": len(data["platforms"]),
                    "total_engagement": data["total_engagement"],
                    "avg_pain_score": round(avg_pain, 2),
                    "validation_score": len(data["posts"]) * 5 + cross_platform_bonus + data["total_engagement"] / 100,
                    "sample_posts": data["posts"][:3],
                    "is_consumer_problem": False
                })
        
        # Process consumer problem topics (weighted higher)
        for category, data in consumer_problem_topics.items():
            if len(data["posts"]) >= 1:  # Lower threshold for consumer problems
                avg_pain = sum(p.get("pain_score", 0) for p in data["posts"]) / len(data["posts"])
                cross_platform_bonus = len(data["platforms"]) * 15  # Higher bonus
                consumer_bonus = min(data["consumer_signals"] * 2, 30)  # Bonus for signals

                aggregated.append({
                    "topic": f"{category}_consumer_pain",
                    "category": category,
                    "mention_count": len(data["posts"]),
                    "platforms": list(data["platforms"]),
                    "cross_platform_count": len(data["platforms"]),
                    "total_engagement": data["total_engagement"],
                    "avg_pain_score": round(avg_pain, 2),
                    "consumer_signals": data["consumer_signals"],
                    # Weighted scoring for consumer problems
                    "validation_score": len(data["posts"]) * 8 + cross_platform_bonus + consumer_bonus + data["total_engagement"] / 50,
                    "sample_posts": data["posts"][:3],
                    "is_consumer_problem": True
                })

        return sorted(aggregated, key=lambda x: x["validation_score"], reverse=True)[:25]

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract potential topic keywords from text."""
        import re

        # Remove common words
        stopwords = {
            'the', 'a', 'an', 'is', 'it', 'to', 'for', 'and', 'or', 'but',
            'in', 'on', 'at', 'of', 'with', 'this', 'that', 'my', 'i', 'you',
            'we', 'they', 'have', 'has', 'had', 'be', 'been', 'being', 'do',
            'does', 'did', 'will', 'would', 'could', 'should', 'can', 'just',
            'so', 'if', 'when', 'how', 'what', 'why', 'who', 'which', 'where'
        }

        # Extract words
        words = re.findall(r'\b[a-z]{4,15}\b', text.lower())

        # Filter and return unique keywords
        keywords = []
        seen = set()
        for word in words:
            if word not in stopwords and word not in seen:
                seen.add(word)
                keywords.append(word)

        return keywords[:5]  # Top 5 keywords per post


# Synchronous wrapper for integration with existing discover_trends.py
class SocialMediaFetcherSync:
    """Synchronous wrapper for SocialMediaFetcher with timeout and graceful failure."""

    def __init__(self, timeout_seconds: int = 120):
        """
        Initialize with configurable timeout.
        
        Args:
            timeout_seconds: Maximum time to wait for operations (default 2 minutes)
        """
        self._async_fetcher = SocialMediaFetcher()
        self.timeout_seconds = timeout_seconds

    def fetch_social_trends(
        self,
        lens: Dict[str, Any],
        limit: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Fetch social trends synchronously with timeout protection.

        This method will:
        1. Attempt to fetch from social media platforms
        2. Return empty list if unavailable, rate limited, or times out
        3. Log the specific failure reason for debugging
        
        This ensures the main pipeline continues even if social fetch fails.

        Compatible with existing discover_trends.py pattern.

        Returns list of topics in the format expected by discover_trends.py.
        """
        import signal
        
        def timeout_handler(signum, frame):
            raise TimeoutError(f"Social media operation exceeded {self.timeout_seconds} seconds")
        
        # Set up timeout handler (Unix only)
        use_signal_timeout = hasattr(signal, 'SIGALRM')
        
        try:
            if use_signal_timeout:
                signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(self.timeout_seconds)
            
            return asyncio.run(self._fetch_async_with_timeout(lens, limit))
            
        except TimeoutError as e:
            print(f"⚠️  Social media timeout: {e}", file=sys.stderr)
            print("   Pipeline continuing without social data...", file=sys.stderr)
            return []
        except Exception as e:
            error_msg = str(e).lower()
            if "rate limit" in error_msg:
                print(f"⚠️  Social media rate limited: {e}", file=sys.stderr)
                print("   Pipeline continuing...", file=sys.stderr)
            elif "credential" in error_msg or "api key" in error_msg:
                print(f"⚠️  Social media authentication failed: {e}", file=sys.stderr)
                print("   Check TWITTERAPI_KEY or Xpoz credentials", file=sys.stderr)
            else:
                print(f"⚠️  Social media fetch error: {e}", file=sys.stderr)
                print("   Pipeline continuing without social data...", file=sys.stderr)
            return []
        finally:
            if use_signal_timeout:
                signal.alarm(0)  # Cancel timeout

    async def _fetch_async_with_timeout(
        self,
        lens: Dict[str, Any],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Async implementation with individual call timeout protection."""
        try:
            # Use asyncio.wait_for for timeout protection
            connected = await asyncio.wait_for(
                self._async_fetcher.connect(),
                timeout=30  # 30 seconds max for connection
            )
            if not connected:
                print("   Social Media: Could not connect (credentials may be missing)", file=sys.stderr)
                return []

            lens_name = lens.get('name', 'unknown')
            
            # Fetch with overall timeout
            results = await asyncio.wait_for(
                self._async_fetcher.fetch_for_lens(lens_name, limit_per_platform=limit),
                timeout=self.timeout_seconds - 30  # Reserve time for connection
            )

            # Convert to topic format expected by discover_trends.py
            topics = []
            for agg in results.get("aggregated_topics", []):
                topic = {
                    "name": agg["topic"],
                    "source": f"social_media ({', '.join(agg['platforms'])})",
                    "score": agg["validation_score"],
                    "url": agg["sample_posts"][0].get("url", "") if agg["sample_posts"] else "",
                    "engagement": agg["total_engagement"],
                    "pain_score": agg["avg_pain_score"],
                    "cross_platform": agg["cross_platform_count"],
                    "is_social": True,
                    "is_consumer_problem": agg.get("is_consumer_problem", False),
                }
                
                # Add consumer-specific metadata
                if agg.get("is_consumer_problem"):
                    topic["consumer_category"] = agg.get("category")
                    topic["consumer_signals"] = agg.get("consumer_signals", 0)
                    topic["consumer_problem_summary"] = f"{agg.get('category', 'General')} consumer pain: {agg['mention_count']} mentions"
                
                topics.append(topic)

            return topics

        finally:
            await self._async_fetcher.close()


# Backward compatibility aliases
XpozFetcher = SocialMediaFetcher
XpozFetcherSync = SocialMediaFetcherSync


# Convenience function for direct usage
def fetch_from_social_media(lens: Dict[str, Any], limit: int = 30) -> List[Dict[str, Any]]:
    """Fetch trending topics from social media platforms."""
    try:
        fetcher = SocialMediaFetcherSync()
        return fetcher.fetch_social_trends(lens, limit)
    except Exception as e:
        print(f"Social media fetch error: {e}", file=sys.stderr)
        return []


# Legacy alias for backward compatibility
fetch_from_xpoz_social = fetch_from_social_media