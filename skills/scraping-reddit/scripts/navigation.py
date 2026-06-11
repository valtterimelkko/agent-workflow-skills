#!/usr/bin/env python3
"""
Tactical Navigation Functions for Reddit SaaS Opportunity Discovery.

Provides capabilities for:
- Finding relevant subreddits for niche keywords
- Scanning community wikis for pain points
- Identifying top contributors
- Recursive comment threading analysis
"""
import re
from typing import List, Dict, Any, Optional, Tuple
from collections import Counter, defaultdict

from scripts.utils import SubredditInfo, Contributor, WikiPage, ScrapedComment
from scripts.reddit_scraper import RedditScraper


class RedditNavigator:
    """
    Navigation capabilities for Reddit SaaS opportunity discovery.
    
    Helps agents understand community structure and identify
    high-value discussion threads.
    """
    
    def __init__(self, scraper: RedditScraper):
        self.scraper = scraper
    
    async def get_relevant_subreddits(
        self,
        niche_keyword: str,
        limit: int = 15,
        min_subscribers: int = 1000
    ) -> List[Dict[str, Any]]:
        """
        Find relevant "watering holes" for a target niche.
        
        Args:
            niche_keyword: Keyword describing the niche (e.g., "marketing", "ecommerce")
            limit: Maximum number of subreddits to return
            min_subscribers: Minimum subscriber count to include
            
        Returns:
            List of subreddit information with relevance scoring
            
        Example:
            >>> navigator = RedditNavigator(scraper)
            >>> subs = await navigator.get_relevant_subreddits("marketing")
            >>> # Returns: r/marketing, r/ppc, r/growthhacking, etc.
        """
        # Search for subreddits matching the keyword
        subreddits = await self.scraper.search_subreddits(niche_keyword, limit=limit * 2)
        
        # Filter and score
        results = []
        for sub in subreddits:
            if sub.subscribers < min_subscribers:
                continue
            
            # Calculate relevance score
            relevance_score = self._calculate_relevance(sub, niche_keyword)
            
            # Calculate activity ratio (active / subscribers)
            activity_ratio = sub.accounts_active / max(1, sub.subscribers)
            
            results.append({
                "name": sub.name,
                "display_name": sub.display_name,
                "subscribers": sub.subscribers,
                "accounts_active": sub.accounts_active,
                "activity_ratio": round(activity_ratio, 4),
                "description": sub.public_description[:200] if sub.public_description else "",
                "relevance_score": relevance_score,
                "url": f"https://reddit.com/r/{sub.name}",
                "over18": sub.over18
            })
        
        # Sort by relevance score then subscribers
        results.sort(key=lambda x: (x["relevance_score"], x["subscribers"]), reverse=True)
        return results[:limit]
    
    def _calculate_relevance(self, sub: SubredditInfo, keyword: str) -> float:
        """Calculate relevance score for a subreddit to a keyword."""
        score = 0.0
        keyword_lower = keyword.lower()
        
        # Name match
        if keyword_lower in sub.name.lower():
            score += 50
        
        # Description match
        desc = (sub.public_description or "").lower()
        if keyword_lower in desc:
            score += 30
        
        # Title match
        title = (sub.display_name or "").lower()
        if keyword_lower in title:
            score += 20
        
        # Activity bonus
        if sub.accounts_active > 100:
            score += 10
        
        # Size bonus (logarithmic to avoid giant subs dominating)
        import math
        if sub.subscribers > 0:
            score += min(20, math.log10(sub.subscribers))
        
        return score
    
    async def scan_community_wiki(
        self,
        subreddit: str,
        target_sections: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Scan community wiki/FAQ for recurring pain points.
        
        Many subreddits have FAQs or Wikis listing "Commonly Asked Questions"
        - these are literally lists of recurring pain points.
        
        Args:
            subreddit: Subreddit name (without r/)
            target_sections: Specific wiki pages to scan (default: auto-detect)
            
        Returns:
            Analysis of wiki content with extracted pain points
            
        Example:
            >>> wiki_analysis = await navigator.scan_community_wiki("startups")
            >>> print(wiki_analysis["pain_points"])
        """
        # Get list of wiki pages
        wiki_pages = await self.scraper.get_wiki_pages(subreddit)
        
        if not wiki_pages:
            return {
                "subreddit": subreddit,
                "pages_found": 0,
                "pain_points": [],
                "common_questions": [],
                "error": "No wiki pages found"
            }
        
        # Determine which pages to scan
        pages_to_scan = target_sections or self._identify_relevant_pages(wiki_pages)
        
        # Scan each page
        all_pain_points = []
        all_questions = []
        scanned_pages = []
        
        for page_name in pages_to_scan[:5]:  # Limit to 5 pages
            wiki_page = await self.scraper.get_wiki_page(subreddit, page_name)
            if not wiki_page:
                continue
            
            scanned_pages.append({
                "page": page_name,
                "title": wiki_page.title,
                "revision_date": wiki_page.revision_date
            })
            
            # Extract pain points from content
            pain_points = self._extract_pain_points_from_wiki(wiki_page.content_md)
            all_pain_points.extend(pain_points)
            
            # Extract common questions
            questions = self._extract_questions_from_wiki(wiki_page.content_md)
            all_questions.extend(questions)
        
        # Deduplicate and rank
        unique_pain_points = self._deduplicate_strings(all_pain_points)
        unique_questions = self._deduplicate_strings(all_questions)
        
        return {
            "subreddit": subreddit,
            "pages_found": len(wiki_pages),
            "pages_scanned": len(scanned_pages),
            "scanned_pages": scanned_pages,
            "pain_points": unique_pain_points[:20],  # Top 20
            "common_questions": unique_questions[:20],
            "pain_point_count": len(unique_pain_points),
            "question_count": len(unique_questions)
        }
    
    def _identify_relevant_pages(self, wiki_pages: List[str]) -> List[str]:
        """Identify wiki pages likely to contain FAQ/pain point info."""
        priority_keywords = [
            "faq", "index", "guide", "help", "getting_started",
            "newbie", "beginner", "questions", "common", "rules"
        ]
        
        scored_pages = []
        for page in wiki_pages:
            score = 0
            page_lower = page.lower()
            for keyword in priority_keywords:
                if keyword in page_lower:
                    score += 10
            scored_pages.append((page, score))
        
        # Sort by score
        scored_pages.sort(key=lambda x: x[1], reverse=True)
        return [p[0] for p in scored_pages]
    
    def _extract_pain_points_from_wiki(self, content: str) -> List[str]:
        """Extract pain points from wiki markdown content."""
        pain_points = []
        
        # Look for bullet points that indicate problems
        bullet_pattern = r'^[\s]*[-*•][\s]+(.+?)$'
        bullets = re.findall(bullet_pattern, content, re.MULTILINE | re.IGNORECASE)
        
        problem_indicators = [
            "problem", "issue", "difficult", "hard", "struggle",
            "frustrated", "confused", "error", "fail", "trouble"
        ]
        
        for bullet in bullets:
            bullet_lower = bullet.lower()
            if any(indicator in bullet_lower for indicator in problem_indicators):
                pain_points.append(bullet.strip())
        
        # Look for FAQ-style Q&A
        faq_pattern = r'Q:\s*(.+?)(?:\nA:|$)'
        faqs = re.findall(faq_pattern, content, re.MULTILINE | re.IGNORECASE)
        pain_points.extend(faqs)
        
        return pain_points
    
    def _extract_questions_from_wiki(self, content: str) -> List[str]:
        """Extract questions from wiki content."""
        questions = []
        
        # Markdown headers that are questions
        header_pattern = r'^#+\s*(.+?\?)'
        headers = re.findall(header_pattern, content, re.MULTILINE)
        questions.extend(headers)
        
        # Numbered questions
        numbered_pattern = r'^\d+\.\s*(.+?\?)'
        numbered = re.findall(numbered_pattern, content, re.MULTILINE)
        questions.extend(numbered)
        
        return questions
    
    def _deduplicate_strings(self, strings: List[str], similarity_threshold: float = 0.7) -> List[str]:
        """Deduplicate similar strings."""
        if not strings:
            return []
        
        unique = []
        for s in strings:
            s_normalized = re.sub(r'[^\w]', '', s.lower())
            is_duplicate = False
            
            for existing in unique:
                existing_normalized = re.sub(r'[^\w]', '', existing.lower())
                
                # Simple similarity: common substring ratio
                if len(s_normalized) > 0 and len(existing_normalized) > 0:
                    similarity = self._string_similarity(s_normalized, existing_normalized)
                    if similarity > similarity_threshold:
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                unique.append(s)
        
        return unique
    
    def _string_similarity(self, s1: str, s2: str) -> float:
        """Calculate simple string similarity."""
        # Jaccard similarity of character bigrams
        def get_bigrams(s):
            return set(s[i:i+2] for i in range(len(s)-1))
        
        bigrams1 = get_bigrams(s1)
        bigrams2 = get_bigrams(s2)
        
        if not bigrams1 or not bigrams2:
            return 0.0
        
        intersection = len(bigrams1 & bigrams2)
        union = len(bigrams1 | bigrams2)
        
        return intersection / union if union > 0 else 0.0
    
    async def identify_top_contributors(
        self,
        subreddit: str,
        limit: int = 20,
        activity_lookback: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Find "power users" whose posts often spark high-engagement debates.
        
        Args:
            subreddit: Subreddit to analyze
            limit: Number of top contributors to return
            activity_lookback: Number of recent posts to analyze
            
        Returns:
            List of contributors with engagement metrics
            
        Example:
            >>> contributors = await navigator.identify_top_contributors("startups")
            >>> # Returns users who generate the most engagement
        """
        # Fetch recent posts
        posts = await self.scraper.get_subreddit_posts(
            subreddit, 
            limit=activity_lookback,
            sort="hot"
        )
        
        # Also fetch some new posts
        new_posts = await self.scraper.get_subreddit_posts(
            subreddit,
            limit=min(50, activity_lookback // 2),
            sort="new"
        )
        posts.extend(new_posts)
        
        # Aggregate by author
        author_stats = defaultdict(lambda: {
            "post_count": 0,
            "total_engagement": 0,
            "total_comments": 0,
            "avg_score": 0,
            "posts": []
        })
        
        for post in posts:
            if not post.author or post.author in ["[deleted]", "AutoModerator"]:
                continue
            
            author = post.author
            author_stats[author]["post_count"] += 1
            author_stats[author]["total_engagement"] += post.engagement
            author_stats[author]["total_comments"] += post.comments_count
            author_stats[author]["posts"].append({
                "title": post.title[:100],
                "score": post.engagement,
                "comments": post.comments_count
            })
        
        # Calculate averages and scores
        contributors = []
        for username, stats in author_stats.items():
            if stats["post_count"] < 2:  # Filter single-post users
                continue
            
            avg_engagement = stats["total_engagement"] / stats["post_count"]
            avg_comments = stats["total_comments"] / stats["post_count"]
            
            # Quality score: engagement per post + discussion generation
            quality_score = avg_engagement + (avg_comments * 2)
            
            contributors.append({
                "username": username,
                "post_count": stats["post_count"],
                "total_engagement": stats["total_engagement"],
                "avg_engagement_per_post": round(avg_engagement, 1),
                "avg_comments_per_post": round(avg_comments, 1),
                "quality_score": round(quality_score, 1),
                "top_posts": sorted(stats["posts"], key=lambda x: x["score"], reverse=True)[:3]
            })
        
        # Sort by quality score
        contributors.sort(key=lambda x: x["quality_score"], reverse=True)
        return contributors[:limit]
    
    async def recursive_comment_threading(
        self,
        subreddit: str,
        post_id: str,
        max_depth: int = 5
    ) -> Dict[str, Any]:
        """
        Fetch nested comments looking for "I agree" or "I wish this existed" chains.
        
        These chains indicate the scale of a pain point - more agreement = more demand.
        
        Args:
            subreddit: Subreddit containing the post
            post_id: Post ID to analyze
            max_depth: Maximum comment depth to traverse
            
        Returns:
            Analysis of comment thread with pain amplification metrics
            
        Example:
            >>> analysis = await navigator.recursive_comment_threading("startups", "abc123")
            >>> print(analysis["pain_amplification"])  # True if strong agreement detected
        """
        from scripts.analysis import OpportunityAnalyzer
        
        # Fetch post with comments
        post, comments = await self.scraper.get_post_with_comments(
            subreddit, 
            post_id,
            depth=max_depth
        )
        
        if not post:
            return {
                "post_id": post_id,
                "error": "Could not fetch post",
                "total_comments": 0,
                "agreement_chains": [],
                "pain_amplification": False
            }
        
        # Analyze comment thread
        analyzer = OpportunityAnalyzer()
        thread_analysis = analyzer.analyze_comment_thread(comments)
        
        # Find agreement chains
        agreement_chains = self._find_agreement_chains(comments)
        
        # Extract high-intent comments
        high_intent_comments = []
        
        def extract_intents(comments_list: List[ScrapedComment], depth: int = 0):
            for comment in comments_list:
                text = comment.body.lower()
                
                # Check for high-intent patterns
                intent_patterns = [
                    r"\bi wish\b",
                    r"\bsame here\b",
                    r"\bthis is exactly\b",
                    r"\bme too\b",
                    r"\bi have the same (?:problem|issue)\b",
                    r"\bfacing the same\b",
                ]
                
                for pattern in intent_patterns:
                    if re.search(pattern, text):
                        high_intent_comments.append({
                            "id": comment.id,
                            "author": comment.author,
                            "body": comment.body[:200],
                            "score": comment.score,
                            "depth": depth,
                            "replies_count": len(comment.replies)
                        })
                        break
                
                # Recurse into replies
                if comment.replies and depth < max_depth:
                    extract_intents(comment.replies, depth + 1)
        
        extract_intents(comments)
        
        # Determine pain amplification
        pain_amplification = (
            thread_analysis["agreement_ratio"] > 0.15 or
            len(agreement_chains) >= 2 or
            len(high_intent_comments) >= 3
        )
        
        return {
            "post_id": post_id,
            "post_title": post.title,
            "post_url": post.url,
            "total_comments": thread_analysis["total_comments"],
            "agreement_indicators": thread_analysis["agreement_indicators"],
            "agreement_ratio": thread_analysis["agreement_ratio"],
            "avg_sentiment": thread_analysis["avg_sentiment"],
            "pain_amplification": pain_amplification,
            "agreement_chains": agreement_chains[:5],
            "high_intent_comments": high_intent_comments[:10]
        }
    
    def _find_agreement_chains(self, comments: List[ScrapedComment]) -> List[Dict[str, Any]]:
        """Find chains of agreement in comment threads."""
        chains = []
        
        def traverse(comment_list: List[ScrapedComment], chain: List[Dict] = None):
            if chain is None:
                chain = []
            
            for comment in comment_list:
                text_lower = comment.body.lower()
                
                # Check for agreement indicator
                is_agreement = bool(re.search(
                    r"\b(i agree|me too|same here|exactly|this\s*^\s*so much)\b",
                    text_lower
                ))
                
                if is_agreement:
                    new_chain = chain + [{
                        "id": comment.id,
                        "author": comment.author,
                        "body": comment.body[:100],
                        "depth": len(chain)
                    }]
                    
                    # If chain is long enough, save it
                    if len(new_chain) >= 2:
                        chains.append({
                            "length": len(new_chain),
                            "participants": [c["author"] for c in new_chain],
                            "comments": new_chain
                        })
                    
                    # Continue chain in replies
                    if comment.replies:
                        traverse(comment.replies, new_chain)
                else:
                    # Reset chain
                    if comment.replies:
                        traverse(comment.replies, [])
        
        traverse(comments)
        
        # Sort by length
        chains.sort(key=lambda x: x["length"], reverse=True)
        return chains