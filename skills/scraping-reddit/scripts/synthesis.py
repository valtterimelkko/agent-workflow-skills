#!/usr/bin/env python3
"""
Idea Synthesis Logic for Reddit SaaS Opportunity Discovery.

Provides capabilities for:
- Trend persistence checking
- Monetization proxy detection
- Tech stack inference
- Cross-pollination detection
"""
import re
import time
from typing import List, Dict, Any, Optional, Set, Tuple
from collections import Counter, defaultdict
from dataclasses import asdict

from scripts.utils import TrendReport, CrossPollinationReport, OpportunitySignal
from scripts.reddit_scraper import RedditScraper
from scripts.analysis import OpportunityAnalyzer


class TrendAnalyzer:
    """Analyzes trend persistence and predicts future trajectory."""
    
    def __init__(self, scraper: RedditScraper):
        self.scraper = scraper
        self.analyzer = OpportunityAnalyzer()
    
    async def check_trend_persistence(
        self,
        keyword: str,
        subreddits: List[str],
        days: int = 90
    ) -> TrendReport:
        """
        Check if a problem is a "fad" or a "chronic pain point".
        
        Args:
            keyword: Keyword to search for
            subreddits: List of subreddits to monitor
            days: Number of days to look back
            
        Returns:
            TrendReport with persistence analysis
            
        Example:
            >>> report = await analyzer.check_trend_persistence(
            ...     "inventory management",
            ...     ["smallbusiness", "Etsy", "ecommerce"],
            ...     days=90
            ... )
            >>> print(report.is_persistent)  # True if chronic pain point
        """
        # Collect mentions across different time windows
        mentions_30d = await self._count_mentions_in_window(keyword, subreddits, 30)
        mentions_60d = await self._count_mentions_in_window(keyword, subreddits, 60)
        mentions_90d = await self._count_mentions_in_window(keyword, subreddits, 90)
        
        # Calculate metrics
        count_30d = len(mentions_30d)
        count_90d = len(mentions_90d)
        
        # Growth rate (30d vs previous 60d)
        prev_60d_count = len(mentions_60d) - count_30d
        growth_rate = ((count_30d - prev_60d_count) / max(1, prev_60d_count)) * 100
        
        # Consistency check (mentions distributed across time)
        consistency_score = self._calculate_consistency(mentions_90d, days)
        
        # Determine persistence
        is_persistent = (
            count_90d >= 10 and  # Minimum threshold
            consistency_score > 0.3 and  # Not all bunched together
            growth_rate > -50  # Not declining rapidly
        )
        
        # Detect seasonality (would need more historical data for accuracy)
        seasonality_detected = False  # Placeholder
        
        # Predict future trend
        if growth_rate > 20:
            prediction = "growing"
        elif growth_rate < -20:
            prediction = "declining"
        else:
            prediction = "stable"
        
        return TrendReport(
            keyword=keyword,
            is_persistent=is_persistent,
            mention_count_30d=count_30d,
            mention_count_90d=count_90d,
            growth_rate=round(growth_rate, 1),
            consistency_score=round(consistency_score, 3),
            seasonality_detected=seasonality_detected,
            prediction=prediction
        )
    
    async def _count_mentions_in_window(
        self,
        keyword: str,
        subreddits: List[str],
        days: int
    ) -> List[Dict[str, Any]]:
        """Count mentions of a keyword in recent posts."""
        mentions = []
        keyword_lower = keyword.lower()
        cutoff_time = time.time() - (days * 86400)
        
        for subreddit in subreddits[:3]:  # Limit to avoid rate limits
            try:
                # Fetch top posts from the time window
                time_filter = "month" if days <= 30 else "year"
                posts = await self.scraper.get_subreddit_posts(
                    subreddit,
                    limit=50,
                    sort="top",
                    time_filter=time_filter
                )
                
                for post in posts:
                    try:
                        post_time = float(post.created_at)
                        if post_time < cutoff_time:
                            continue
                    except (ValueError, TypeError):
                        continue
                    
                    # Check for keyword in title/body
                    text = f"{post.title} {post.body}".lower()
                    if keyword_lower in text:
                        mentions.append({
                            "post_id": post.id,
                            "subreddit": subreddit,
                            "title": post.title,
                            "created_utc": post.created_at,
                            "engagement": post.engagement
                        })
            
            except Exception as e:
                print(f"Error fetching from r/{subreddit}: {e}")
                continue
        
        return mentions
    
    def _calculate_consistency(
        self,
        mentions: List[Dict[str, Any]],
        total_days: int
    ) -> float:
        """
        Calculate consistency score - how evenly distributed mentions are.
        
        Returns 0-1 where 1 = perfectly distributed, 0 = all bunched together.
        """
        if not mentions:
            return 0.0
        
        if len(mentions) < 5:
            return 0.5  # Not enough data
        
        # Group by week
        weeks = defaultdict(int)
        for mention in mentions:
            try:
                timestamp = float(mention.get("created_utc", 0))
                week_num = int((time.time() - timestamp) / 604800)  # Weeks ago
                weeks[week_num] += 1
            except (ValueError, TypeError):
                continue
        
        if not weeks:
            return 0.0
        
        # Calculate coefficient of variation
        counts = list(weeks.values())
        mean = sum(counts) / len(counts)
        variance = sum((c - mean) ** 2 for c in counts) / len(counts)
        std_dev = variance ** 0.5
        
        cv = std_dev / mean if mean > 0 else 0
        
        # Convert to consistency score (inverse of CV, normalized)
        consistency = max(0, 1 - (cv / 2))  # CV of 2 = 0 consistency
        
        return consistency


class CrossPollinationAnalyzer:
    """Detects opportunities by finding similar problems across communities."""
    
    def __init__(self, scraper: RedditScraper):
        self.scraper = scraper
        self.analyzer = OpportunityAnalyzer()
    
    async def find_cross_pollination(
        self,
        subreddit_a: str,
        subreddit_b: str,
        keywords: Optional[List[str]] = None,
        sample_size: int = 30
    ) -> CrossPollinationReport:
        """
        Find a pain point in Subreddit A and check if Subreddit B has a similar problem.
        
        This helps identify cross-niche opportunities or market expansion potential.
        
        Args:
            subreddit_a: First subreddit to analyze
            subreddit_b: Second subreddit to analyze
            keywords: Specific keywords to search for (optional)
            sample_size: Number of posts to sample from each
            
        Returns:
            CrossPollinationReport with shared opportunities
            
        Example:
            >>> report = await analyzer.find_cross_pollination(
            ...     "EtsySellers", "AmazonFBA"
            ... )
            >>> # Might find both groups struggle with inventory management
        """
        # Fetch posts from both subreddits
        posts_a = await self.scraper.get_subreddit_posts(
            subreddit_a, limit=sample_size, sort="hot"
        )
        posts_a.extend(await self.scraper.get_subreddit_posts(
            subreddit_a, limit=sample_size // 2, sort="top", time_filter="week"
        ))
        
        posts_b = await self.scraper.get_subreddit_posts(
            subreddit_b, limit=sample_size, sort="hot"
        )
        posts_b.extend(await self.scraper.get_subreddit_posts(
            subreddit_b, limit=sample_size // 2, sort="top", time_filter="week"
        ))
        
        # Extract keywords from both communities
        if not keywords:
            keywords_a = self._extract_keywords(posts_a)
            keywords_b = self._extract_keywords(posts_b)
        else:
            keywords_a = set(k.lower() for k in keywords)
            keywords_b = keywords_a
        
        # Find shared keywords
        shared_keywords = keywords_a & keywords_b
        
        # Calculate Jaccard similarity
        similarity_score = self._jaccard_similarity(keywords_a, keywords_b)
        
        # Extract pain points from both
        pain_points_a = self._extract_pain_points(posts_a)
        pain_points_b = self._extract_pain_points(posts_b)
        
        # Find shared pain themes
        shared_themes = self._find_shared_themes(pain_points_a, pain_points_b)
        
        # Determine opportunity type
        if similarity_score > 0.5:
            opportunity_type = "expansion"
        elif shared_themes:
            opportunity_type = "adaptation"
        else:
            opportunity_type = "new_market"
        
        return CrossPollinationReport(
            subreddit_a=subreddit_a,
            subreddit_b=subreddit_b,
            similarity_score=round(similarity_score, 3),
            shared_keywords=list(shared_keywords)[:20],
            pain_points_a=pain_points_a[:10],
            pain_points_b=pain_points_b[:10],
            opportunity_type=opportunity_type
        )
    
    def _extract_keywords(self, posts: List[Any], top_n: int = 50) -> Set[str]:
        """Extract significant keywords from posts."""
        all_text = " ".join([f"{p.title} {p.body}" for p in posts])
        
        # Simple tokenization
        words = re.findall(r'\b[a-z]{4,}\b', all_text.lower())
        
        # Filter common stop words
        stop_words = {
            "this", "that", "with", "from", "they", "have", "been",
            "were", "said", "each", "which", "their", "time", "would",
            "there", "could", "other", "after", "first", "never",
            "these", "think", "where", "being", "every", "great",
            "might", "shall", "still", "those", "while", "what",
            "when", "your", "know", "just", "like", "over", "also",
            "back", "only", "come", "make", "well", "work", "want",
            "more", "here", "look", "down", "most", "long", "last",
            "find", "give", "does", "made", "part", "such", "take",
            "than", "them", "very", "even", "into", "year", "some",
            "come", "could", "state", "good", "much", "need", "help"
        }
        
        filtered = [w for w in words if w not in stop_words]
        
        # Get most common
        counter = Counter(filtered)
        return set(word for word, _ in counter.most_common(top_n))
    
    def _extract_pain_points(self, posts: List[Any]) -> List[str]:
        """Extract pain point descriptions from posts."""
        pain_indicators = [
            "problem", "issue", "difficult", "frustrated", "struggling",
            "annoying", "pain", "hard to", "wish", "hate", "terrible"
        ]
        
        pain_points = []
        for post in posts:
            text = f"{post.title} {post.body}".lower()
            
            if any(indicator in text for indicator in pain_indicators):
                # Extract sentences with pain indicators
                sentences = re.split(r'[.!?]+', text)
                for sentence in sentences:
                    if any(indicator in sentence for indicator in pain_indicators):
                        clean = sentence.strip()[:150]
                        if len(clean) > 20:
                            pain_points.append(clean)
        
        # Deduplicate
        seen = set()
        unique = []
        for pp in pain_points:
            key = re.sub(r'[^\w]', '', pp.lower())[:30]
            if key not in seen:
                seen.add(key)
                unique.append(pp)
        
        return unique[:20]
    
    def _find_shared_themes(
        self,
        pain_points_a: List[str],
        pain_points_b: List[str]
    ) -> List[str]:
        """Find shared themes between two sets of pain points."""
        # Extract key nouns from pain points
        def extract_nouns(texts: List[str]) -> Counter:
            nouns = []
            for text in texts:
                # Simple noun extraction (capitalized words or words after "the")
                matches = re.findall(r'\b(?:the|a|an)\s+(\w+)', text.lower())
                nouns.extend(matches)
            return Counter(nouns)
        
        nouns_a = extract_nouns(pain_points_a)
        nouns_b = extract_nouns(pain_points_b)
        
        # Find common nouns
        common = set(nouns_a.keys()) & set(nouns_b.keys())
        
        return list(common)[:10]
    
    def _jaccard_similarity(self, set_a: Set[str], set_b: Set[str]) -> float:
        """Calculate Jaccard similarity between two sets."""
        if not set_a or not set_b:
            return 0.0
        
        intersection = len(set_a & set_b)
        union = len(set_a | set_b)
        
        return intersection / union if union > 0 else 0.0


class IdeaSynthesizer:
    """
    High-level synthesizer that combines all analysis into actionable insights.
    
    This is the main entry point for the "Idea Synthesis" capability layer.
    """
    
    def __init__(self, scraper: RedditScraper):
        self.scraper = scraper
        self.analyzer = OpportunityAnalyzer()
        self.trend_analyzer = TrendAnalyzer(scraper)
        self.cross_analyzer = CrossPollinationAnalyzer(scraper)
    
    async def analyze_opportunity(
        self,
        subreddits: List[str],
        keywords: Optional[List[str]] = None,
        known_competitors: Optional[List[str]] = None,
        min_opportunity_score: float = 50.0
    ) -> Dict[str, Any]:
        """
        Comprehensive opportunity analysis across multiple subreddits.
        
        This is the main synthesis function that combines all capabilities.
        
        Args:
            subreddits: List of subreddits to analyze
            keywords: Optional keywords to focus on
            known_competitors: Optional list of competitor names to track
            min_opportunity_score: Minimum score to include in results
            
        Returns:
            Comprehensive opportunity report
        """
        all_signals = []
        all_posts = []
        
        # Collect posts from all subreddits
        for subreddit in subreddits:
            try:
                posts = await self.scraper.get_subreddit_posts(subreddit, limit=50)
                all_posts.extend(posts)
            except Exception as e:
                print(f"Error fetching from r/{subreddit}: {e}")
                continue
        
        # Analyze each post
        for post in all_posts:
            try:
                # Basic analysis
                analysis = self.analyzer.analyze_post(post)
                
                # Skip if no intent signals
                if not analysis.get("intent_signals"):
                    continue
                
                # Velocity analysis
                velocity = self.analyzer.calculate_velocity_metrics(post)
                
                # Competitor analysis
                text = f"{post.title} {post.body}"
                competitor_mentions = self.analyzer.extract_competitor_mentions(
                    text, known_competitors
                )
                
                # Synthesize opportunity
                signal = self.analyzer.synthesize_opportunity(
                    post, analysis, velocity, competitor_mentions
                )
                
                if signal.opportunity_score >= min_opportunity_score:
                    all_signals.append({
                        "signal": signal,
                        "post": post,
                        "analysis": analysis
                    })
            
            except Exception as e:
                print(f"Error analyzing post {post.id}: {e}")
                continue
        
        # Sort by opportunity score
        all_signals.sort(key=lambda x: x["signal"].opportunity_score, reverse=True)
        
        # Aggregate insights
        insights = self._aggregate_insights(all_signals)
        
        return {
            "opportunities": [
                {
                    "opportunity": asdict(s["signal"]),
                    "post": {
                        "id": s["post"].id,
                        "title": s["post"].title,
                        "url": s["post"].url,
                        "subreddit": s["post"].metadata.get("subreddit"),
                        "engagement": s["post"].engagement,
                        "comments": s["post"].comments_count
                    }
                }
                for s in all_signals[:20]  # Top 20
            ],
            "summary": insights,
            "total_analyzed": len(all_posts),
            "high_opportunity_count": len(all_signals)
        }
    
    def _aggregate_insights(
        self,
        signals: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """Aggregate insights from multiple opportunity signals."""
        if not signals:
            return {"error": "No opportunities found"}
        
        # Count by priority
        priorities = Counter(s["signal"].priority for s in signals)
        
        # Aggregate suggested features
        all_features = []
        for s in signals:
            all_features.extend(s["signal"].suggested_features)
        top_features = Counter(all_features).most_common(10)
        
        # Aggregate tech stack hints
        all_tech = []
        for s in signals:
            all_tech.extend(s["signal"].tech_stack_hints)
        top_tech = Counter(all_tech).most_common(5)
        
        # Calculate average scores
        avg_opportunity = sum(s["signal"].opportunity_score for s in signals) / len(signals)
        avg_frustration = sum(s["signal"].frustration_score for s in signals) / len(signals)
        avg_monetization = sum(s["signal"].monetization_score for s in signals) / len(signals)
        
        # Most common problem themes
        problem_keywords = []
        for s in signals:
            problem = s["signal"].problem_statement.lower()
            words = re.findall(r'\b\w{5,}\b', problem)
            problem_keywords.extend(words)
        
        common_themes = Counter(problem_keywords).most_common(10)
        
        return {
            "priority_distribution": dict(priorities),
            "average_opportunity_score": round(avg_opportunity, 1),
            "average_frustration_score": round(avg_frustration, 1),
            "average_monetization_score": round(avg_monetization, 1),
            "top_suggested_features": top_features,
            "top_tech_stack_hints": top_tech,
            "common_problem_themes": common_themes,
            "recommendation": self._generate_recommendation(priorities, avg_opportunity)
        }
    
    def _generate_recommendation(
        self,
        priorities: Counter,
        avg_score: float
    ) -> str:
        """Generate overall recommendation based on analysis."""
        high_count = priorities.get("high", 0)
        medium_count = priorities.get("medium", 0)
        
        if high_count >= 3 and avg_score >= 70:
            return "Strong opportunity signals detected. Recommend immediate validation and MVP development."
        elif high_count >= 1 or (medium_count >= 3 and avg_score >= 60):
            return "Promising signals found. Recommend deeper research and user interviews."
        elif avg_score >= 50:
            return "Some signals present. Recommend continued monitoring and trend analysis."
        else:
            return "Weak signals currently. Recommend exploring different keywords or communities."