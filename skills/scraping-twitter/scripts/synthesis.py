#!/usr/bin/env python3
"""
Idea Synthesis for Twitter - Trend analysis and cross-pollination detection.

Provides:
- Trend persistence checking
- Cross-community opportunity detection
- Comprehensive opportunity analysis
"""
import asyncio
from typing import List, Dict, Any, Optional
from collections import defaultdict
from datetime import datetime, timedelta

from scripts.utils import (
    ScrapedTweet, TrendReport, OpportunitySignal
)


class TrendAnalyzer:
    """Analyze trend persistence and growth on Twitter."""
    
    def __init__(self, scraper):
        """
        Initialize trend analyzer.
        
        Args:
            scraper: TwitterScraper instance
        """
        self.scraper = scraper
    
    async def check_trend_persistence(
        self,
        keyword: str,
        hashtags: Optional[List[str]] = None,
        days: int = 30
    ) -> TrendReport:
        """
        Check if a keyword/hashtag trend is persistent or a fad.
        
        Args:
            keyword: Keyword to analyze
            hashtags: Additional hashtags to include in search
            days: Number of days to analyze
            
        Returns:
            TrendReport with persistence analysis
        """
        # Calculate date ranges
        now = datetime.utcnow()
        
        # Search for recent mentions (last 7 days approximation)
        recent_query = keyword
        if hashtags:
            recent_query += " OR " + " OR ".join(f"#{h}" for h in hashtags)
        
        recent_tweets, _ = await self.scraper.search_tweets(
            recent_query,
            limit=200
        )
        
        # Count mentions
        mention_count_7d = len(recent_tweets)
        
        # For older data, we'd need historical search or use date filters
        # Since TwitterAPI.io has limited historical, we estimate
        # In a real implementation, you might store data over time
        mention_count_30d = mention_count_7d * 3  # Rough estimate
        
        # Calculate growth rate
        if mention_count_30d > 0:
            growth_rate = ((mention_count_7d - (mention_count_30d / 4)) / 
                          max(1, mention_count_30d / 4)) * 100
        else:
            growth_rate = 0
        
        # Determine persistence
        is_persistent = mention_count_7d > 10 and growth_rate > -20
        
        # Determine prediction
        if growth_rate > 50:
            prediction = "growing"
        elif growth_rate < -30:
            prediction = "declining"
        else:
            prediction = "stable"
        
        # Calculate consistency (would need time-series data for real calc)
        consistency_score = 0.7 if is_persistent else 0.3
        
        return TrendReport(
            keyword=keyword,
            is_persistent=is_persistent,
            mention_count_7d=mention_count_7d,
            mention_count_30d=mention_count_30d,
            growth_rate=growth_rate,
            consistency_score=consistency_score,
            seasonality_detected=False,  # Would need historical data
            prediction=prediction
        )
    
    async def compare_hashtag_trends(
        self,
        hashtags: List[str],
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Compare trends across multiple hashtags.
        
        Args:
            hashtags: List of hashtags to compare
            limit: Tweets to fetch per hashtag
            
        Returns:
            Comparison report
        """
        results = {}
        
        for hashtag in hashtags:
            tweets, _ = await self.scraper.search_tweets(
                f"#{hashtag}",
                limit=limit
            )
            
            # Calculate metrics
            total_engagement = sum(t.total_engagement for t in tweets)
            unique_authors = len(set(t.author_username for t in tweets))
            avg_engagement = total_engagement / max(1, len(tweets))
            
            results[hashtag] = {
                "tweet_count": len(tweets),
                "total_engagement": total_engagement,
                "unique_authors": unique_authors,
                "avg_engagement": round(avg_engagement, 2),
                "trend_report": await self.check_trend_persistence(hashtag)
            }
        
        # Sort by total engagement
        sorted_results = dict(sorted(
            results.items(),
            key=lambda x: x[1]["total_engagement"],
            reverse=True
        ))
        
        return {
            "hashtag_comparison": sorted_results,
            "top_hashtag": list(sorted_results.keys())[0] if sorted_results else None,
            "total_tweets_analyzed": sum(r["tweet_count"] for r in results.values())
        }
    
    async def analyze_engagement_patterns(
        self,
        keyword: str,
        limit: int = 200
    ) -> Dict[str, Any]:
        """
        Analyze engagement patterns for a keyword.
        
        Args:
            keyword: Keyword to analyze
            limit: Number of tweets to analyze
            
        Returns:
            Engagement pattern analysis
        """
        tweets, _ = await self.scraper.search_tweets(keyword, limit=limit)
        
        if not tweets:
            return {"error": "No tweets found"}
        
        # Calculate engagement distribution
        engagements = [t.total_engagement for t in tweets]
        likes = [t.engagement for t in tweets]
        replies = [t.reply_count for t in tweets]
        retweets = [t.retweet_count for t in tweets]
        
        # Find high-engagement tweets
        avg_engagement = sum(engagements) / len(engagements)
        high_engagement = [t for t in tweets if t.total_engagement > avg_engagement * 2]
        
        # Analyze top performers
        top_tweets = sorted(tweets, key=lambda t: t.total_engagement, reverse=True)[:10]
        
        return {
            "keyword": keyword,
            "total_tweets": len(tweets),
            "avg_engagement": round(avg_engagement, 2),
            "median_engagement": sorted(engagements)[len(engagements)//2] if engagements else 0,
            "max_engagement": max(engagements) if engagements else 0,
            "engagement_breakdown": {
                "avg_likes": round(sum(likes) / len(likes), 2) if likes else 0,
                "avg_replies": round(sum(replies) / len(replies), 2) if replies else 0,
                "avg_retweets": round(sum(retweets) / len(retweets), 2) if retweets else 0,
            },
            "high_engagement_tweets": len(high_engagement),
            "top_performers": [
                {
                    "id": t.id,
                    "text": t.text[:100],
                    "author": t.author_username,
                    "engagement": t.total_engagement
                }
                for t in top_tweets
            ]
        }


class CrossPollinationAnalyzer:
    """Detect cross-community opportunities."""
    
    def __init__(self, scraper):
        """
        Initialize cross-pollination analyzer.
        
        Args:
            scraper: TwitterScraper instance
        """
        self.scraper = scraper
    
    async def find_cross_pollination(
        self,
        hashtag_a: str,
        hashtag_b: str,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Find similar problems/opportunities across two hashtag communities.
        
        Args:
            hashtag_a: First hashtag
            hashtag_b: Second hashtag
            limit: Tweets to fetch per hashtag
            
        Returns:
            Cross-pollination analysis
        """
        from scripts.analysis import OpportunityAnalyzer
        from scripts.filters import IntentFilter
        
        # Fetch tweets from both communities
        tweets_a, _ = await self.scraper.search_tweets(f"#{hashtag_a}", limit=limit)
        tweets_b, _ = await self.scraper.search_tweets(f"#{hashtag_b}", limit=limit)
        
        # Analyze for pain points
        analyzer = OpportunityAnalyzer()
        intent_filter = IntentFilter()
        
        high_intent_a = intent_filter.filter(tweets_a)
        high_intent_b = intent_filter.filter(tweets_b)
        
        # Extract common keywords
        words_a = self._extract_keywords([t.text for t in high_intent_a])
        words_b = self._extract_keywords([t.text for t in high_intent_b])
        
        shared_keywords = list(set(words_a.keys()) & set(words_b.keys()))
        
        # Calculate similarity score
        if words_a and words_b:
            common_words = sum(words_a.get(w, 0) for w in shared_keywords)
            total_words = sum(words_a.values()) + sum(words_b.values())
            similarity_score = (2 * common_words) / max(1, total_words)
        else:
            similarity_score = 0
        
        # Determine opportunity type
        if similarity_score > 0.3:
            opportunity_type = "expansion"
        elif similarity_score > 0.1:
            opportunity_type = "adaptation"
        else:
            opportunity_type = "new_market"
        
        return {
            "hashtag_a": hashtag_a,
            "hashtag_b": hashtag_b,
            "similarity_score": round(similarity_score, 3),
            "opportunity_type": opportunity_type,
            "shared_keywords": shared_keywords[:20],
            "pain_points_a": [t.text[:100] for t in high_intent_a[:5]],
            "pain_points_b": [t.text[:100] for t in high_intent_b[:5]],
            "tweet_count_a": len(tweets_a),
            "tweet_count_b": len(tweets_b),
            "high_intent_count_a": len(high_intent_a),
            "high_intent_count_b": len(high_intent_b)
        }
    
    def _extract_keywords(self, texts: List[str]) -> Dict[str, int]:
        """Extract and count keywords from texts."""
        import re
        
        word_counts = defaultdict(int)
        
        # Common stop words
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "shall",
            "can", "need", "dare", "ought", "used", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "as", "into",
            "through", "during", "before", "after", "above", "below",
            "between", "under", "and", "but", "or", "yet", "so", "if",
            "because", "although", "though", "while", "where", "when",
            "that", "which", "who", "whom", "whose", "what", "this",
            "these", "those", "i", "you", "he", "she", "it", "we", "they",
            "me", "him", "her", "us", "them", "my", "your", "his", "its",
            "our", "their", "mine", "yours", "hers", "ours", "theirs",
            "myself", "yourself", "himself", "herself", "itself", "ourselves",
            "yourselves", "themselves", "rt", "https", "http", "co"
        }
        
        for text in texts:
            # Clean and tokenize
            text = text.lower()
            words = re.findall(r'\b[a-z]{3,}\b', text)
            
            for word in words:
                if word not in stop_words:
                    word_counts[word] += 1
        
        return dict(word_counts)


class IdeaSynthesizer:
    """Synthesize comprehensive opportunity reports from Twitter data."""
    
    def __init__(self, scraper):
        """
        Initialize idea synthesizer.
        
        Args:
            scraper: TwitterScraper instance
        """
        self.scraper = scraper
        self.trend_analyzer = TrendAnalyzer(scraper)
        self.cross_analyzer = CrossPollinationAnalyzer(scraper)
    
    async def analyze_opportunity(
        self,
        hashtags: List[str],
        keywords: Optional[List[str]] = None,
        known_competitors: Optional[List[str]] = None,
        min_opportunity_score: float = 50,
        limit: int = 100
    ) -> Dict[str, Any]:
        """
        Full synthesis pipeline for opportunity analysis.
        
        Args:
            hashtags: Hashtags to analyze
            keywords: Additional keywords to search
            known_competitors: List of known competitors to track
            min_opportunity_score: Minimum score to include
            limit: Tweets to fetch per source
            
        Returns:
            Comprehensive opportunity report
        """
        from scripts.analysis import OpportunityAnalyzer
        from scripts.filters import (
            IntentFilter, VelocityFilter, CompetitorFilter
        )
        
        # Collect all tweets
        all_tweets = []
        
        for hashtag in hashtags:
            tweets, _ = await self.scraper.search_tweets(f"#{hashtag}", limit=limit)
            all_tweets.extend(tweets)
        
        if keywords:
            for keyword in keywords:
                tweets, _ = await self.scraper.search_tweets(keyword, limit=limit)
                all_tweets.extend(tweets)
        
        # Remove duplicates
        seen_ids = set()
        unique_tweets = []
        for tweet in all_tweets:
            if tweet.id not in seen_ids:
                seen_ids.add(tweet.id)
                unique_tweets.append(tweet)
        
        all_tweets = unique_tweets
        
        # Run analysis pipeline
        analyzer = OpportunityAnalyzer()
        intent_filter = IntentFilter()
        velocity_filter = VelocityFilter()
        
        # Filter for high-intent tweets
        high_intent_tweets = intent_filter.filter(all_tweets)
        
        # Calculate velocity for all tweets
        velocity_results = []
        for tweet in all_tweets:
            velocity = analyzer.calculate_velocity_metrics(tweet)
            velocity_results.append((tweet, velocity))
        
        # Analyze for opportunities
        opportunities = []
        for tweet in high_intent_tweets:
            analysis = analyzer.analyze_tweet(tweet)
            velocity = analyzer.calculate_velocity_metrics(tweet)
            
            # Check for competitor mentions
            competitor_mentions = []
            if known_competitors:
                competitor_mentions = analyzer.extract_competitor_mentions(
                    tweet.text, known_competitors
                )
            
            # Synthesize opportunity
            opportunity = analyzer.synthesize_opportunity(
                tweet, analysis, velocity, competitor_mentions
            )
            
            if opportunity.opportunity_score >= min_opportunity_score:
                opportunities.append({
                    "tweet": tweet,
                    "opportunity": opportunity,
                    "analysis": analysis
                })
        
        # Sort by opportunity score
        opportunities.sort(
            key=lambda x: x["opportunity"].opportunity_score,
            reverse=True
        )
        
        # Calculate summary statistics
        total_tweets = len(all_tweets)
        high_intent_count = len(high_intent_tweets)
        
        if opportunities:
            avg_opportunity_score = sum(
                o["opportunity"].opportunity_score for o in opportunities
            ) / len(opportunities)
            avg_frustration_score = sum(
                o["opportunity"].frustration_score for o in opportunities
            ) / len(opportunities)
        else:
            avg_opportunity_score = 0
            avg_frustration_score = 0
        
        # Priority distribution
        priority_counts = defaultdict(int)
        for opp in opportunities:
            priority_counts[opp["opportunity"].priority] += 1
        
        # Top suggested features
        all_features = []
        for opp in opportunities:
            all_features.extend(opp["opportunity"].suggested_features)
        
        feature_counts = defaultdict(int)
        for feature in all_features:
            feature_counts[feature] += 1
        
        top_features = sorted(
            feature_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:10]
        
        # Competitor gaps
        competitor_gaps = []
        if known_competitors:
            comp_filter = CompetitorFilter(known_competitors)
            competitor_gaps = comp_filter.find_competitor_gaps(all_tweets)
        
        # Trend analysis
        trend_reports = []
        for hashtag in hashtags[:3]:  # Limit to first 3 for performance
            report = await self.trend_analyzer.check_trend_persistence(hashtag)
            trend_reports.append(report)
        
        # Generate recommendation
        if priority_counts.get("high", 0) > 3:
            recommendation = "Strong opportunity signals detected. Prioritize validation."
        elif avg_opportunity_score > 60:
            recommendation = "Good opportunity landscape. Continue monitoring and research."
        else:
            recommendation = "Limited signals. Consider expanding search or different angles."
        
        return {
            "summary": {
                "total_tweets_analyzed": total_tweets,
                "unique_tweets": len(seen_ids),
                "high_intent_count": high_intent_count,
                "opportunities_found": len(opportunities),
                "high_opportunity_count": priority_counts.get("high", 0),
                "average_opportunity_score": round(avg_opportunity_score, 1),
                "average_frustration_score": round(avg_frustration_score, 1),
                "priority_distribution": dict(priority_counts),
                "top_suggested_features": top_features,
                "competitor_gaps_found": len(competitor_gaps),
                "recommendation": recommendation
            },
            "opportunities": opportunities[:20],  # Top 20
            "trend_analysis": trend_reports,
            "competitor_gaps": competitor_gaps[:10],
            "hashtags_analyzed": hashtags,
            "keywords_analyzed": keywords or []
        }