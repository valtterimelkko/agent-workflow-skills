#!/usr/bin/env python3
"""
Twitter Navigation - Tactical discovery functions for finding relevant users,
hashtags, and conversations.

Provides:
- User discovery by keyword/search
- Hashtag discovery and analysis
- Thread/conversation navigation
- Top contributor identification
"""
import asyncio
from typing import List, Dict, Any, Optional, Tuple
from collections import defaultdict

from scripts.utils import (
    ScrapedTweet, ScrapedReply, TwitterUser, TrendingTopic,
    TweetThread, HashtagAnalysis
)


class TwitterNavigator:
    """Navigate Twitter to find relevant users, hashtags, and conversations."""
    
    def __init__(self, scraper):
        """
        Initialize navigator.
        
        Args:
            scraper: TwitterScraper instance
        """
        self.scraper = scraper
    
    async def find_relevant_users(
        self,
        niche_keyword: str,
        limit: int = 10,
        min_followers: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Find relevant Twitter users for a niche.
        
        Args:
            niche_keyword: Keyword to search for
            limit: Maximum users to return
            min_followers: Minimum follower count
            
        Returns:
            List of user info dicts with relevance scores
        """
        # Search for users
        users = await self.scraper.search_users(niche_keyword, limit=limit * 2)
        
        # Score and filter users
        scored_users = []
        for user in users:
            if user.followers < min_followers:
                continue
            
            # Calculate relevance score
            relevance_score = self._calculate_user_relevance(user, niche_keyword)
            
            scored_users.append({
                "user": user,
                "relevance_score": relevance_score,
                "follower_tier": self._get_follower_tier(user.followers),
                "influence_score": user.influence_score
            })
        
        # Sort by relevance score
        scored_users.sort(key=lambda x: x["relevance_score"], reverse=True)
        return scored_users[:limit]
    
    async def get_relevant_hashtags(
        self,
        niche_keyword: str,
        limit: int = 10,
        min_tweets: int = 10
    ) -> List[HashtagAnalysis]:
        """
        Find relevant hashtags for a niche.
        
        Args:
            niche_keyword: Keyword to search for
            limit: Maximum hashtags to return
            min_tweets: Minimum tweets for consideration
            
        Returns:
            List of HashtagAnalysis objects
        """
        # Search for tweets with the keyword
        tweets, _ = await self.scraper.search_tweets(niche_keyword, limit=200)
        
        # Extract and count hashtags
        hashtag_data = defaultdict(lambda: {
            "tweets": [],
            "authors": set(),
            "total_engagement": 0
        })
        
        for tweet in tweets:
            hashtags = tweet.metadata.get("hashtags", [])
            for hashtag in hashtags:
                hashtag_data[hashtag]["tweets"].append(tweet)
                hashtag_data[hashtag]["authors"].add(tweet.author_username)
                hashtag_data[hashtag]["total_engagement"] += tweet.total_engagement
        
        # Create analyses
        analyses = []
        for hashtag, data in hashtag_data.items():
            tweet_count = len(data["tweets"])
            if tweet_count < min_tweets:
                continue
            
            # Calculate velocity (tweets per day approximation)
            velocity = tweet_count / 7  # Assuming 7 day window
            
            # Find related hashtags
            related = defaultdict(int)
            for tweet in data["tweets"]:
                for h in tweet.metadata.get("hashtags", []):
                    if h != hashtag:
                        related[h] += 1
            
            related_hashtags = [
                h for h, count in sorted(related.items(), key=lambda x: x[1], reverse=True)
            ][:10]
            
            analyses.append(HashtagAnalysis(
                hashtag=hashtag,
                tweet_count=tweet_count,
                unique_authors=len(data["authors"]),
                total_engagement=data["total_engagement"],
                top_tweets=sorted(
                    data["tweets"],
                    key=lambda t: t.total_engagement,
                    reverse=True
                )[:5],
                velocity=round(velocity, 2),
                related_hashtags=related_hashtags
            ))
        
        # Sort by total engagement
        analyses.sort(key=lambda x: x.total_engagement, reverse=True)
        return analyses[:limit]
    
    async def identify_top_contributors(
        self,
        hashtag: str,
        limit: int = 15,
        activity_lookback: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Identify top contributors for a hashtag.
        
        Args:
            hashtag: Hashtag to analyze (without #)
            limit: Number of contributors to return
            activity_lookback: Number of tweets to analyze
            
        Returns:
            List of contributor info dicts
        """
        # Search for tweets with hashtag
        tweets, _ = await self.scraper.search_tweets(
            f"#{hashtag}",
            limit=activity_lookback
        )
        
        # Aggregate by author
        author_data = defaultdict(lambda: {
            "tweets": [],
            "total_engagement": 0,
            "replies_received": 0
        })
        
        for tweet in tweets:
            author = tweet.author_username
            author_data[author]["tweets"].append(tweet)
            author_data[author]["total_engagement"] += tweet.total_engagement
            author_data[author]["replies_received"] += tweet.reply_count
        
        # Calculate quality scores
        contributors = []
        for username, data in author_data.items():
            tweet_count = len(data["tweets"])
            if tweet_count < 2:  # Minimum activity threshold
                continue
            
            avg_engagement = data["total_engagement"] / tweet_count
            reply_ratio = data["replies_received"] / max(1, data["total_engagement"])
            
            # Quality score combines engagement and discussion generation
            quality_score = (avg_engagement * 0.6) + (reply_ratio * 100 * 0.4)
            
            # Get user details if available from tweets
            sample_tweet = data["tweets"][0]
            
            contributors.append({
                "username": username,
                "tweet_count": tweet_count,
                "total_engagement": data["total_engagement"],
                "avg_engagement_per_tweet": round(avg_engagement, 2),
                "replies_generated": data["replies_received"],
                "quality_score": round(quality_score, 2),
                "followers": sample_tweet.author_followers,
                "is_verified": sample_tweet.author_verified
            })
        
        # Sort by quality score
        contributors.sort(key=lambda x: x["quality_score"], reverse=True)
        return contributors[:limit]
    
    async def explore_conversation_thread(
        self,
        tweet_id: str,
        max_depth: int = 3
    ) -> Optional[TweetThread]:
        """
        Deep dive into a conversation thread.
        
        Args:
            tweet_id: Root tweet ID
            max_depth: Maximum reply depth to fetch
            
        Returns:
            TweetThread with full conversation
        """
        # Get the thread
        thread = await self.scraper.get_tweet_thread(tweet_id)
        
        if not thread:
            return None
        
        # The scraper already fetches replies, but we can go deeper if needed
        # For now, return what we have
        return thread
    
    async def find_conversations_by_keyword(
        self,
        keyword: str,
        min_replies: int = 5,
        limit: int = 10
    ) -> List[TweetThread]:
        """
        Find active conversations about a keyword.
        
        Args:
            keyword: Keyword to search for
            min_replies: Minimum replies to include
            limit: Maximum conversations to return
            
        Returns:
            List of TweetThread objects
        """
        # Search for tweets
        tweets, _ = await self.scraper.search_tweets(keyword, limit=100)
        
        # Filter for tweets with replies
        tweets_with_replies = [
            t for t in tweets
            if t.reply_count >= min_replies
        ]
        
        # Sort by reply count
        tweets_with_replies.sort(key=lambda t: t.reply_count, reverse=True)
        
        # Get threads for top tweets
        threads = []
        for tweet in tweets_with_replies[:limit]:
            thread = await self.scraper.get_tweet_thread(tweet.id)
            if thread:
                threads.append(thread)
        
        return threads
    
    async def scan_user_timeline_for_pain_points(
        self,
        username: str,
        limit: int = 50
    ) -> Dict[str, Any]:
        """
        Scan a user's timeline for pain point mentions.
        
        Args:
            username: Twitter username
            limit: Number of tweets to scan
            
        Returns:
            Analysis dict with pain points found
        """
        from scripts.analysis import OpportunityAnalyzer
        from scripts.filters import IntentFilter
        
        # Get user's tweets
        tweets, _ = await self.scraper.get_user_tweets(username, limit=limit)
        
        # Analyze for pain points
        analyzer = OpportunityAnalyzer()
        intent_filter = IntentFilter()
        
        pain_point_tweets = []
        for tweet in tweets:
            analysis = analyzer.analyze_tweet(tweet)
            
            # Check if it has intent signals
            if analysis["intent_signals"]:
                pain_point_tweets.append({
                    "tweet": tweet,
                    "analysis": analysis
                })
        
        # Also filter by intent patterns
        high_intent = intent_filter.filter(tweets)
        
        return {
            "username": username,
            "total_tweets_scanned": len(tweets),
            "pain_point_tweets": pain_point_tweets,
            "high_intent_tweets": high_intent,
            "pain_point_ratio": len(pain_point_tweets) / max(1, len(tweets))
        }
    
    async def discover_influencers_in_niche(
        self,
        niche_keyword: str,
        limit: int = 10,
        min_followers: int = 5000
    ) -> List[Dict[str, Any]]:
        """
        Discover influencers in a specific niche.
        
        Args:
            niche_keyword: Niche to search
            limit: Maximum influencers to return
            min_followers: Minimum follower count
            
        Returns:
            List of influencer info dicts
        """
        # Find relevant users
        users = await self.find_relevant_users(
            niche_keyword,
            limit=limit * 2,
            min_followers=min_followers
        )
        
        # Enhance with engagement analysis
        influencers = []
        for user_info in users:
            user = user_info["user"]
            
            # Get recent tweets for engagement analysis
            tweets, _ = await self.scraper.get_user_tweets(user.username, limit=20)
            
            if not tweets:
                continue
            
            # Calculate average engagement rate
            total_engagement = sum(t.total_engagement for t in tweets)
            avg_engagement = total_engagement / len(tweets)
            
            # Calculate engagement rate (engagement per follower)
            engagement_rate = (avg_engagement / max(1, user.followers)) * 100
            
            influencers.append({
                "username": user.username,
                "name": user.name,
                "followers": user.followers,
                "verified": user.verified,
                "description": user.description,
                "relevance_score": user_info["relevance_score"],
                "avg_engagement": round(avg_engagement, 2),
                "engagement_rate": round(engagement_rate, 3),
                "recent_tweet_count": len(tweets)
            })
        
        # Sort by combined influence (followers * engagement_rate)
        influencers.sort(
            key=lambda x: (x["followers"] * x["engagement_rate"]),
            reverse=True
        )
        
        return influencers[:limit]
    
    def _calculate_user_relevance(self, user: TwitterUser, keyword: str) -> float:
        """Calculate relevance score for a user based on keyword."""
        score = 0.0
        keyword_lower = keyword.lower()
        
        # Check description
        if user.description:
            desc_lower = user.description.lower()
            if keyword_lower in desc_lower:
                score += 50
            # Check for related terms
            related_terms = self._get_related_terms(keyword)
            for term in related_terms:
                if term in desc_lower:
                    score += 20
        
        # Check name/username
        if keyword_lower in user.name.lower():
            score += 30
        if keyword_lower in user.username.lower():
            score += 20
        
        # Factor in follower count (log scale)
        import math
        follower_score = min(30, math.log10(user.followers + 1) * 3)
        score += follower_score
        
        # Verified bonus
        if user.verified:
            score += 10
        
        return score
    
    def _get_related_terms(self, keyword: str) -> List[str]:
        """Get related terms for a keyword."""
        # Simple mapping - could be expanded
        term_map = {
            "saas": ["software", "startup", "b2b", "business"],
            "ai": ["artificial intelligence", "machine learning", "ml", "gpt"],
            "dev": ["developer", "development", "coding", "programming"],
            "marketing": ["growth", "seo", "content", "ads"],
            "ecommerce": ["shopify", "amazon", "retail", "selling"],
        }
        
        return term_map.get(keyword.lower(), [])
    
    def _get_follower_tier(self, followers: int) -> str:
        """Classify follower count into tier."""
        if followers >= 1000000:
            return "mega"
        elif followers >= 100000:
            return "macro"
        elif followers >= 10000:
            return "mid"
        elif followers >= 1000:
            return "micro"
        else:
            return "nano"


class ConversationExplorer:
    """Explore Twitter conversations and threads."""
    
    def __init__(self, scraper):
        self.scraper = scraper
    
    async def trace_conversation_path(
        self,
        tweet_id: str,
        direction: str = "down"  # 'down' for replies, 'up' for thread context
    ) -> Dict[str, Any]:
        """
        Trace a conversation path from a tweet.
        
        Args:
            tweet_id: Starting tweet ID
            direction: 'down' for replies, 'up' for parent thread
            
        Returns:
            Conversation path data
        """
        if direction == "down":
            replies, _ = await self.scraper.get_tweet_replies(tweet_id, limit=100)
            return {
                "root_tweet_id": tweet_id,
                "direction": "down",
                "replies": replies,
                "total_replies": len(replies)
            }
        else:
            thread = await self.scraper.get_tweet_thread(tweet_id)
            return {
                "root_tweet_id": tweet_id,
                "direction": "up",
                "thread": thread
            }
    
    async def find_high_engagement_threads(
        self,
        hashtag: str,
        min_total_engagement: int = 100,
        limit: int = 10
    ) -> List[TweetThread]:
        """
        Find threads with high overall engagement.
        
        Args:
            hashtag: Hashtag to search
            min_total_engagement: Minimum combined engagement
            limit: Maximum threads to return
            
        Returns:
            List of high-engagement TweetThreads
        """
        tweets, _ = await self.scraper.search_tweets(f"#{hashtag}", limit=100)
        
        high_engagement_threads = []
        
        for tweet in tweets:
            if tweet.total_engagement < min_total_engagement:
                continue
            
            thread = await self.scraper.get_tweet_thread(tweet.id)
            if thread and thread.total_engagement >= min_total_engagement:
                high_engagement_threads.append(thread)
        
        # Sort by total engagement
        high_engagement_threads.sort(key=lambda t: t.total_engagement, reverse=True)
        return high_engagement_threads[:limit]