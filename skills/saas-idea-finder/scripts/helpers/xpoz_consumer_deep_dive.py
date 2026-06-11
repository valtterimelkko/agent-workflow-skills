#!/usr/bin/env python3
"""
Xpoz Consumer Deep Dive Fetcher

Specialized fetcher for deep consumer problem analysis.
Focuses on high-intent consumer problems with SaaS opportunity potential.
"""
import asyncio
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

sys.path.insert(0, str(Path(__file__).parent.parent / "xpoz"))
sys.path.insert(0, str(Path(__file__).parent.parent / "platforms"))

try:
    from xpoz_client import XpozMCPClient, XpozAPIError
    from xpoz_credentials import CredentialNotFoundError
except ImportError as e:
    print(f"Warning: Could not import Xpoz client: {e}", file=sys.stderr)
    XpozMCPClient = None
    XpozAPIError = Exception
    CredentialNotFoundError = Exception

try:
    from consumer_deep_dive import ConsumerDeepDiveAnalyzer, ConsumerProblem
except ImportError as e:
    print(f"Warning: Could not import ConsumerDeepDiveAnalyzer: {e}", file=sys.stderr)
    ConsumerDeepDiveAnalyzer = None
    ConsumerProblem = None


class XpozConsumerDeepDiveFetcher:
    """
    Specialized fetcher for consumer pain point deep dives.
    
    Focuses on lenses with high consumer problem density:
    - ecommerce_sellers
    - small_business_ops
    - creator_economy
    """
    
    # Consumer-focused lens configurations
    CONSUMER_LENS_CONFIG = {
        "ecommerce_sellers": {
            "description": "E-commerce sellers and resellers",
            "reddit_subreddits": ["Etsy", "EtsySellers", "AmazonFBA", "Flipping", "Depop", "Poshmark"],
            "twitter_hashtags": ["#etsyshop", "#reseller", "#ecommerce", "#smallbusiness", "#sidehustle"],
            "instagram_hashtags": ["etsyshop", "smallbusinessowner", "resellerlife", "ecommerce"],
            "consumer_focused_queries": [
                "expensive fees",
                "platform fees too high",
                "losing money",
                "inventory management",
                "shipping problems",
            ]
        },
        "small_business_ops": {
            "description": "Small business operations",
            "reddit_subreddits": ["smallbusiness", "Entrepreneur", "freelance", "realtors"],
            "twitter_hashtags": ["#smallbusiness", "#freelance", "#entrepreneur", "#solopreneur"],
            "instagram_hashtags": ["smallbusiness", "businessowner", "entrepreneurlife"],
            "consumer_focused_queries": [
                "wasting time on",
                "too expensive for small business",
                "can't afford",
                "manual process",
                "need better solution",
            ]
        },
        "creator_economy": {
            "description": "Content creators and influencers",
            "reddit_subreddits": ["YouTubers", "ContentCreation", "NewTubers", "TikTokCreators"],
            "twitter_hashtags": ["#creatorlife", "#contentcreator", "#ugc", "#influencer"],
            "instagram_hashtags": ["contentcreator", "influencerlife", "creatorlife"],
            "consumer_focused_queries": [
                "burnout",
                "too much work",
                "not getting paid",
                "platform taking cut",
                "need tool for",
            ]
        }
    }
    
    def __init__(self):
        self._client = None
        self._is_connected = False
        self._analyzer = None
        if ConsumerDeepDiveAnalyzer is not None:
            self._analyzer = ConsumerDeepDiveAnalyzer()
    
    async def connect(self) -> bool:
        """Initialize Xpoz connection."""
        if XpozMCPClient is None:
            print("XpozMCPClient not available", file=sys.stderr)
            return False
        
        try:
            self._client = XpozMCPClient()
            await self._client.connect()
            self._is_connected = True
            return True
        except Exception as e:
            print(f"Connection error: {e}", file=sys.stderr)
            return False
    
    async def close(self):
        """Close connection."""
        if self._client:
            await self._client.close()
        self._is_connected = False
    
    async def deep_dive_consumer_problems(
        self,
        lens: str,
        max_results_per_platform: int = 15
    ) -> Dict[str, Any]:
        """
        Perform deep dive analysis on consumer problems for a specific lens.
        
        Args:
            lens: Lens key (ecommerce_sellers, small_business_ops, creator_economy)
            max_results_per_platform: Max posts to fetch per platform
            
        Returns:
            Dictionary with deep dive analysis results
        """
        if not self._is_connected:
            raise RuntimeError("Not connected. Call connect() first.")
        
        if self._analyzer is None:
            return {"error": "ConsumerDeepDiveAnalyzer not available"}
        
        config = self.CONSUMER_LENS_CONFIG.get(lens)
        if not config:
            return {"error": f"Unknown lens: {lens}"}
        
        print(f"\n{'='*70}")
        print(f"Consumer Deep Dive: {lens}")
        print(f"Description: {config['description']}")
        print(f"{'='*70}")
        
        all_problems = []
        platform_results = {}
        
        # Fetch from Reddit with consumer-focused queries
        reddit_problems = await self._fetch_reddit_consumer_problems(
            config['reddit_subreddits'],
            config['consumer_focused_queries'],
            max_results_per_platform
        )
        all_problems.extend(reddit_problems)
        platform_results['reddit'] = len(reddit_problems)
        print(f"✓ Reddit: {len(reddit_problems)} consumer problems identified")
        
        # Fetch from Twitter
        twitter_problems = await self._fetch_twitter_consumer_problems(
            config['twitter_hashtags'],
            config['consumer_focused_queries'],
            max_results_per_platform
        )
        all_problems.extend(twitter_problems)
        platform_results['twitter'] = len(twitter_problems)
        print(f"✓ Twitter: {len(twitter_problems)} consumer problems identified")
        
        # Fetch from Instagram
        instagram_problems = await self._fetch_instagram_consumer_problems(
            config['instagram_hashtags'],
            max_results_per_platform
        )
        all_problems.extend(instagram_problems)
        platform_results['instagram'] = len(instagram_problems)
        print(f"✓ Instagram: {len(instagram_problems)} consumer problems identified")
        
        # Generate comprehensive report
        report = self._analyzer.generate_opportunity_report(all_problems)
        
        return {
            "lens": lens,
            "timestamp": datetime.now().isoformat(),
            "platform_breakdown": platform_results,
            "total_problems": len(all_problems),
            "analysis": report,
            "problems": [
                {
                    "id": p.problem_id,
                    "title": p.title,
                    "category": p.primary_category,
                    "pain_types": p.pain_types,
                    "severity": p.severity_score,
                    "platform": p.platform,
                    "url": p.source_url,
                    "validation_signals": p.validation_signals,
                    "workaround_mentions": p.workaround_mentions,
                    "willingness_to_pay": len(p.willingness_to_pay_signals) > 0,
                }
                for p in sorted(all_problems, key=lambda x: x.severity_score, reverse=True)
            ]
        }
    
    async def _fetch_reddit_consumer_problems(
        self,
        subreddits: List[str],
        queries: List[str],
        limit: int
    ) -> List[Any]:
        """Fetch consumer problems from Reddit."""
        problems = []
        
        for subreddit in subreddits[:3]:  # Limit for API efficiency
            for query in queries[:2]:  # Top 2 consumer queries
                try:
                    result = await self._client.call_tool(
                        "getRedditPostsByKeywords",
                        {"query": f"{query} subreddit:{subreddit}", "limit": limit}
                    )
                    
                    posts = self._parse_reddit_results(result)
                    for post in posts:
                        problem = self._analyzer.analyze_post_deep(post)
                        if problem:
                            problems.append(problem)
                            
                except Exception as e:
                    print(f"Warning: Reddit fetch failed for r/{subreddit}: {e}")
                    continue
        
        return problems
    
    async def _fetch_twitter_consumer_problems(
        self,
        hashtags: List[str],
        queries: List[str],
        limit: int
    ) -> List[Any]:
        """Fetch consumer problems from Twitter."""
        problems = []
        
        # Search by hashtags
        for hashtag in hashtags[:3]:
            try:
                result = await self._client.call_tool(
                    "getTwitterPostsByKeywords",
                    {"query": hashtag, "limit": limit}
                )
                
                posts = self._parse_twitter_results(result)
                for post in posts:
                    problem = self._analyzer.analyze_post_deep(post)
                    if problem:
                        problems.append(problem)
                        
            except Exception as e:
                print(f"Warning: Twitter fetch failed for {hashtag}: {e}")
                continue
        
        # Search by pain point queries
        for query in queries[:2]:
            try:
                result = await self._client.call_tool(
                    "getTwitterPostsByKeywords",
                    {"query": query, "limit": limit}
                )
                
                posts = self._parse_twitter_results(result)
                for post in posts:
                    problem = self._analyzer.analyze_post_deep(post)
                    if problem:
                        problems.append(problem)
                        
            except Exception as e:
                print(f"Warning: Twitter query failed for '{query}': {e}")
                continue
        
        return problems
    
    async def _fetch_instagram_consumer_problems(
        self,
        hashtags: List[str],
        limit: int
    ) -> List[Any]:
        """Fetch consumer problems from Instagram."""
        problems = []
        
        for hashtag in hashtags[:4]:
            try:
                result = await self._client.call_tool(
                    "getInstagramPostsByKeywords",
                    {"query": f"#{hashtag}", "limit": limit}
                )
                
                posts = self._parse_instagram_results(result)
                for post in posts:
                    problem = self._analyzer.analyze_post_deep(post)
                    if problem:
                        problems.append(problem)
                        
            except Exception as e:
                print(f"Warning: Instagram fetch failed for #{hashtag}: {e}")
                continue
        
        return problems
    
    def _parse_reddit_results(self, result: Dict) -> List[Dict]:
        """Parse Reddit results into standardized format."""
        posts = []
        content = result.get("content", [])
        
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                # Simple parsing - would need full YAML parsing in production
                if "title" in text.lower():
                    posts.append({
                        "platform": "reddit",
                        "title": text[:200],
                        "body": text,
                        "id": "unknown",
                        "url": "",
                        "author": "",
                        "engagement": 0
                    })
        
        return posts
    
    def _parse_twitter_results(self, result: Dict) -> List[Dict]:
        """Parse Twitter results into standardized format."""
        posts = []
        content = result.get("content", [])
        
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                posts.append({
                    "platform": "twitter",
                    "title": "",
                    "body": text,
                    "id": "unknown",
                    "url": "",
                    "author": "",
                    "engagement": 0
                })
        
        return posts
    
    def _parse_instagram_results(self, result: Dict) -> List[Dict]:
        """Parse Instagram results into standardized format."""
        posts = []
        content = result.get("content", [])
        
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                posts.append({
                    "platform": "instagram",
                    "title": "",
                    "body": text,
                    "id": "unknown",
                    "url": "",
                    "author": "",
                    "engagement": 0
                })
        
        return posts


# Synchronous wrapper
class XpozConsumerDeepDiveSync:
    """Synchronous wrapper for deep dive fetcher."""
    
    def __init__(self):
        self._async_fetcher = XpozConsumerDeepDiveFetcher()
    
    def analyze_lens(self, lens: str, max_results: int = 15) -> Dict[str, Any]:
        """Analyze consumer problems for a lens synchronously."""
        try:
            return asyncio.run(self._analyze_async(lens, max_results))
        except Exception as e:
            print(f"Deep dive error: {e}", file=sys.stderr)
            return {"error": str(e)}
    
    async def _analyze_async(self, lens: str, max_results: int) -> Dict[str, Any]:
        """Async implementation."""
        try:
            connected = await self._async_fetcher.connect()
            if not connected:
                return {"error": "Could not connect to Xpoz"}
            
            return await self._async_fetcher.deep_dive_consumer_problems(lens, max_results)
        finally:
            await self._async_fetcher.close()


# Convenience function
def analyze_consumer_problems(lens: str, max_results: int = 15) -> Dict[str, Any]:
    """Analyze consumer problems for a specific lens."""
    fetcher = XpozConsumerDeepDiveSync()
    return fetcher.analyze_lens(lens, max_results)