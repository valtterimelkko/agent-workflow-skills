#!/usr/bin/env python3
"""
Enhanced Topic Extractor for SaaS Idea Finder

Provides intelligent topic extraction, deduplication, and SaaS-opportunity filtering.
"""

import re
from typing import List, Dict, Any, Set, Tuple
from collections import defaultdict
from dataclasses import dataclass, field


@dataclass
class Topic:
    """Represents a discovered topic with metadata."""
    name: str
    canonical_name: str = ""  # Normalized for deduplication
    score: float = 0.0
    sources: List[Dict[str, Any]] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    urls: List[str] = field(default_factory=list)  # URLs associated with the topic
    engagement: float = 0.0  # Engagement metrics (e.g., likes, shares, comments)
    is_social: bool = False  # Whether this topic originated from social media
    
    @property
    def source_count(self) -> int:
        return len(self.sources)
    
    @property
    def why_trending(self) -> str:
        source_types = set(s['type'] for s in self.sources)
        if len(source_types) > 1:
            return f"Trending across {len(source_types)} sources: {', '.join(sorted(source_types))}"
        elif self.sources:
            return f"High engagement on {self.sources[0]['type']}"
        return "Trending topic"


class TopicExtractor:
    """
    Extracts and processes topics from multiple sources with:
    - Smart deduplication
    - SaaS opportunity filtering
    - Cross-source validation
    """
    
    # Non-commercial keywords to filter out (open source projects, educational resources, etc.)
    NON_SAAS_KEYWORDS = {
        'free', 'open source', 'opensource', 'tutorial', 'course', 'curriculum',
        'learn', 'learning', 'education', 'educational', 'study', 'guide',
        'awesome-list', 'awesome list', 'list of', 'collection of',
        'cheatsheet', 'cheat sheet', 'reference', 'documentation',
        'book', 'books', 'ebook', 'reading', 'curated',
        'roadmap', 'career path', 'interview questions',
        'sample', 'example', 'demo', 'showcase',
        'github', 'repository', 'repo list'
    }
    
    # Keywords that indicate strong SaaS potential
    SAAS_POSITIVE_KEYWORDS = {
        'tool', 'tools', 'platform', 'service', 'saas', 'software',
        'automation', 'workflow', 'management', 'analytics', 'dashboard',
        'integration', 'api', 'sdk', 'solution', 'product',
        'monitoring', 'testing', 'deployment', 'hosting', 'cloud',
        'security', 'backup', 'sync', 'collaboration', 'team',
        'business', 'enterprise', 'startup', 'marketing', 'sales',
        'customer', 'support', 'crm', 'erp', 'billing', 'payment'
    }
    
    def __init__(self):
        self.stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'as', 'is', 'was', 'are', 'be', 'been',
            'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
            'should', 'may', 'might', 'can', 'new', 'best', 'top', 'how', 'what',
            'why', 'when', 'where', 'who', 'this', 'that', 'these', 'those'
        }
    
    def normalize_topic_name(self, name: str) -> str:
        """
        Normalize a topic name for deduplication.
        
        Args:
            name: Raw topic name
            
        Returns:
            Normalized canonical name
        """
        # Lowercase
        normalized = name.lower()
        
        # Remove punctuation and extra spaces
        normalized = re.sub(r'[^\w\s]', ' ', normalized)
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        
        # Remove common suffixes/prefixes
        normalized = re.sub(r'^(the|a|an)\s+', '', normalized)
        normalized = re.sub(r'\s+(tool|tools|app|platform|service)$', '', normalized)
        
        # Sort words for consistent comparison
        words = sorted(normalized.split())
        return ' '.join(words)
    
    def calculate_similarity(self, name1: str, name2: str) -> float:
        """
        Calculate similarity between two topic names.
        
        Args:
            name1: First topic name
            name2: Second topic name
            
        Returns:
            Similarity score (0-1)
        """
        # Normalize both
        norm1 = self.normalize_topic_name(name1)
        norm2 = self.normalize_topic_name(name2)
        
        # Exact match
        if norm1 == norm2:
            return 1.0
        
        # Word overlap
        words1 = set(norm1.split())
        words2 = set(norm2.split())
        
        if not words1 or not words2:
            return 0.0
        
        # Jaccard similarity
        intersection = words1 & words2
        union = words1 | words2
        
        return len(intersection) / len(union)
    
    def is_likely_saas_opportunity(self, topic: Topic) -> Tuple[bool, str]:
        """
        Determine if a topic is likely to be a viable SaaS opportunity.
        
        Args:
            topic: Topic to evaluate
            
        Returns:
            Tuple of (is_opportunity, reason)
        """
        name_lower = topic.name.lower()
        
        # Check for non-commercial indicators
        for keyword in self.NON_SAAS_KEYWORDS:
            if keyword in name_lower:
                return False, f"Contains non-commercial keyword: '{keyword}'"
        
        # Check for GitHub repos that are just lists/resources
        for source in topic.sources:
            if source.get('type') == 'github':
                desc = source.get('description', '').lower()
                if any(kw in desc for kw in ['list of', 'collection', 'curated', 'awesome', 'free']):
                    return False, "GitHub repo appears to be a resource list, not a product"
                
                # Check if repo has high stars but no monetization indicators
                stars = source.get('stars', 0)
                if stars > 100000:  # Very popular repos are often foundational open source
                    has_saas_indicators = any(kw in name_lower + desc for kw in self.SAAS_POSITIVE_KEYWORDS)
                    if not has_saas_indicators:
                        return False, "High-star repo without SaaS indicators - likely foundational open source"
        
        # Check for SaaS positive indicators
        saas_score = 0
        for keyword in self.SAAS_POSITIVE_KEYWORDS:
            if keyword in name_lower:
                saas_score += 1
        
        # Must have at least one SaaS indicator OR multiple sources
        if saas_score >= 1 or topic.source_count >= 2:
            return True, "Shows SaaS potential"
        
        return False, "No clear SaaS indicators and limited cross-source validation"
    
    def deduplicate_topics(self, topics: List[Topic], threshold: float = 0.7) -> List[Topic]:
        """
        Deduplicate topics based on name similarity.
        
        Args:
            topics: List of topics
            threshold: Similarity threshold for merging (0-1)
            
        Returns:
            Deduplicated list
        """
        if not topics:
            return []
        
        # Sort by score (highest first) to keep highest-scoring version
        sorted_topics = sorted(topics, key=lambda t: t.score, reverse=True)
        
        deduplicated = []
        
        for topic in sorted_topics:
            is_duplicate = False
            
            for existing in deduplicated:
                similarity = self.calculate_similarity(topic.name, existing.name)
                
                if similarity >= threshold:
                    # Merge with existing
                    existing.sources.extend(topic.sources)
                    existing.score = max(existing.score, topic.score)
                    existing.keywords = list(set(existing.keywords + topic.keywords))
                    is_duplicate = True
                    break
            
            if not is_duplicate:
                deduplicated.append(topic)
        
        return deduplicated
    
    def extract_keywords(self, text: str) -> List[str]:
        """
        Extract meaningful keywords from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            List of keywords
        """
        # Simple keyword extraction
        words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
        keywords = [w for w in words if w not in self.stop_words]
        
        # Return top keywords by frequency
        freq = defaultdict(int)
        for kw in keywords:
            freq[kw] += 1
        
        sorted_kws = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [kw for kw, _ in sorted_kws[:10]]
    
    def process_raw_topics(self, raw_topics: List[Dict[str, Any]]) -> List[Topic]:
        """
        Process raw topics from discover_trends into structured Topics.
        
        Args:
            raw_topics: Raw topic dictionaries from discover_trends
            
        Returns:
            List of processed Topic objects
        """
        topics = []
        
        for raw in raw_topics:
            topic = Topic(
                name=raw['name'],
                canonical_name=self.normalize_topic_name(raw['name']),
                score=raw.get('score', 0),
                sources=raw.get('sources', []),
                keywords=raw.get('keywords', [])
            )
            topics.append(topic)
        
        return topics
    
    def filter_saas_opportunities(
        self, 
        topics: List[Topic], 
        require_multi_source: bool = True
    ) -> Tuple[List[Topic], List[Tuple[Topic, str]]]:
        """
        Filter topics to likely SaaS opportunities.
        
        Args:
            topics: List of topics
            require_multi_source: Whether to require multiple sources
            
        Returns:
            Tuple of (opportunities, filtered_out_with_reasons)
        """
        opportunities = []
        filtered = []
        
        for topic in topics:
            is_opportunity, reason = self.is_likely_saas_opportunity(topic)
            
            if not is_opportunity:
                filtered.append((topic, reason))
                continue
            
            if require_multi_source and topic.source_count < 2:
                # Still allow single-source if it has strong SaaS indicators
                name_lower = topic.name.lower()
                saas_score = sum(1 for kw in self.SAAS_POSITIVE_KEYWORDS if kw in name_lower)
                if saas_score < 2:
                    filtered.append((topic, "Single source without strong SaaS indicators"))
                    continue
            
            opportunities.append(topic)
        
        return opportunities, filtered
    
    def extract_topics_from_sources(
        self,
        hn_stories: List[Dict],
        github_repos: List[Dict],
        devto_posts: List[Dict],
        hn_algolia_stories: List[Dict],
        newsapi_articles: List[Dict],
        producthunt_posts: List[Dict],
        arxiv_papers: List[Dict],
        stackexchange_questions: List[Dict],
        gdelt_events: List[Dict],
        serpapi_trends: List[Dict],
        youtube_videos: List[Dict],
        xpoz_topics: List[Dict] = None
    ) -> List[Topic]:
        """
        Enhanced topic extraction from all sources with better scoring.
        
        Returns:
            List of Topic objects
        """
        topic_sources = {}  # canonical_name -> Topic
        
        def add_or_update_topic(name: str, source: Dict, base_score: float):
            """Helper to add or update a topic."""
            canonical = self.normalize_topic_name(name)
            
            if canonical not in topic_sources:
                keywords = self.extract_keywords(name)
                topic_sources[canonical] = Topic(
                    name=name,  # Keep original name
                    canonical_name=canonical,
                    score=0,
                    sources=[],
                    keywords=keywords
                )
            
            topic = topic_sources[canonical]
            topic.sources.append(source)
            topic.score = max(topic.score, base_score)  # Keep highest score
        
        # Extract from HackerNews
        for story in hn_stories:
            score = story.get('score', 0) / 10  # Scale down
            comments = story.get('comments', 0)
            engagement = score + (comments / 5)  # Weight comments less
            
            add_or_update_topic(
                story['title'],
                {
                    'type': 'hackernews',
                    'title': story['title'],
                    'url': story['url'],
                    'score': story.get('score', 0),
                    'comments': comments
                },
                engagement
            )
        
        # Extract from GitHub
        for repo in github_repos:
            # Use repo name without owner for cleaner topics
            name = repo['name'].split('/')[-1].replace('-', ' ').replace('_', ' ')
            stars = repo.get('stars', 0)
            
            # Score by stars but cap to avoid giant repos dominating
            if stars < 1000:
                score = stars / 50
            elif stars < 10000:
                score = 20 + (stars - 1000) / 500
            else:
                score = 40 + min((stars - 10000) / 5000, 20)  # Cap at 60
            
            add_or_update_topic(
                name,
                {
                    'type': 'github',
                    'repo': repo['name'],
                    'description': repo.get('description', ''),
                    'url': repo['url'],
                    'stars': stars,
                    'language': repo.get('language', 'Unknown')
                },
                score
            )
        
        # Extract from DEV.to
        for post in devto_posts:
            reactions = post.get('score', 0)
            comments = post.get('comments', 0)
            score = reactions + (comments * 2)
            
            add_or_update_topic(
                post['title'],
                {
                    'type': 'devto',
                    'title': post['title'],
                    'url': post['url'],
                    'reactions': reactions,
                    'comments': comments,
                    'tags': post.get('tags', [])
                },
                score
            )
        
        # Extract from HN Algolia
        for story in hn_algolia_stories:
            score = story.get('score', 0) / 10
            
            add_or_update_topic(
                story['title'],
                {
                    'type': 'hn_algolia',
                    'title': story['title'],
                    'url': story.get('url') or story.get('hn_url'),
                    'hn_url': story.get('hn_url'),
                    'score': story.get('score', 0),
                    'comments': story.get('comments', 0),
                    'query': story.get('query', '')
                },
                score
            )
        
        # Extract from NewsAPI
        for article in newsapi_articles:
            # Base score for news coverage
            add_or_update_topic(
                article['title'],
                {
                    'type': 'newsapi',
                    'title': article['title'],
                    'url': article['url'],
                    'description': article.get('description', ''),
                    'source': article.get('source_name', 'Unknown'),
                    'published_at': article.get('published_at', ''),
                    'query': article.get('query', '')
                },
                25  # Base news score
            )
        
        # Extract from Product Hunt
        for post in producthunt_posts:
            votes = post.get('votes_count', 0)
            comments = post.get('comments_count', 0)
            score = (votes / 20) + (comments / 5)
            
            # Use product name + tagline for context
            name = f"{post['name']}"
            if post.get('tagline'):
                name = f"{post['name']}: {post['tagline']}"
            
            add_or_update_topic(
                name,
                {
                    'type': 'producthunt',
                    'name': post['name'],
                    'tagline': post.get('tagline', ''),
                    'url': post['url'],
                    'votes': votes,
                    'comments': comments,
                    'topics': post.get('topics', []),
                    'maker': post.get('maker', 'Unknown')
                },
                score
            )
        
        # Extract from arXiv
        for paper in arxiv_papers:
            add_or_update_topic(
                paper['title'],
                {
                    'type': 'arxiv',
                    'title': paper['title'],
                    'url': paper['url'],
                    'abstract': paper.get('abstract', ''),
                    'authors': paper.get('authors', []),
                    'published': paper.get('published', ''),
                    'categories': paper.get('categories', []),
                    'query': paper.get('query', '')
                },
                30  # Base academic score
            )
        
        # Extract from Stack Exchange
        for question in stackexchange_questions:
            views = question.get('views', 0)
            score_val = question.get('score', 0)
            score = (views / 100) + score_val
            
            add_or_update_topic(
                question['title'],
                {
                    'type': 'stackexchange',
                    'title': question['title'],
                    'url': question['url'],
                    'score': score_val,
                    'views': views,
                    'tags': question.get('tags', []),
                    'site': question.get('site', 'stackoverflow'),
                    'query': question.get('query', '')
                },
                score
            )
        
        # Extract from GDELT
        for event in gdelt_events:
            add_or_update_topic(
                event['title'],
                {
                    'type': 'gdelt',
                    'title': event['title'],
                    'url': event['url'],
                    'source': event.get('source', 'Unknown'),
                    'published': event.get('published', ''),
                    'themes': event.get('themes', []),
                    'tone': event.get('tone', 0),
                    'query': event.get('query', '')
                },
                35  # Base news importance score
            )
        
        # Extract from SerpAPI
        for trend in serpapi_trends:
            add_or_update_topic(
                trend['title'],
                {
                    'type': 'serpapi',
                    'title': trend['title'],
                    'url': trend['url'],
                    'source': trend.get('source', 'Unknown'),
                    'snippet': trend.get('snippet', ''),
                    'date': trend.get('date', ''),
                    'query': trend.get('query', '')
                },
                25  # Base search trend score
            )
        
        # Extract from YouTube
        for video in youtube_videos:
            views = video.get('views', 0)
            likes = video.get('likes', 0)
            score = (views / 1000) + (likes / 100)
            
            # Boost score if video has pain points from captions
            pain_points = video.get('pain_points', [])
            if pain_points:
                max_severity = max([p.get('severity_score', 50) for p in pain_points])
                score *= (1 + (max_severity / 200))  # 1.0 to 1.5x boost
            
            source_data = {
                'type': 'youtube',
                'title': video['title'],
                'url': video['url'],
                'channel': video.get('channel', 'Unknown'),
                'views': views,
                'likes': likes,
                'published': video.get('published', ''),
                'query': video.get('query', '')
            }
            
            # Include pain points in source data if available
            if pain_points:
                source_data['pain_points'] = pain_points[:3]
                source_data['has_captions'] = True
            
            add_or_update_topic(
                video['title'],
                source_data,
                score
            )
        
        # Extract from Xpoz Social Media (Reddit, Twitter, Instagram)
        if xpoz_topics:
            for topic in xpoz_topics:
                name = topic.get('name', '')
                if not name:
                    continue
                
                # Score based on validation and engagement
                base_score = topic.get('score', 0)
                engagement = topic.get('engagement', 0)
                pain_score = topic.get('pain_score', 0)
                cross_platform = topic.get('cross_platform', 1)
                
                # Calculate final score with cross-platform bonus
                score = base_score + (engagement / 100) + (pain_score * 10) + (cross_platform * 5)
                
                add_or_update_topic(
                    name,
                    {
                        'type': 'xpoz_social',
                        'name': name,
                        'url': topic.get('url', ''),
                        'source': topic.get('source', 'xpoz'),
                        'engagement': engagement,
                        'pain_score': pain_score,
                        'cross_platform': cross_platform,
                        'is_social': True
                    },
                    score
                )
        
        # Convert to list
        topics = list(topic_sources.values())
        
        # Sort by score
        topics.sort(key=lambda x: x.score, reverse=True)
        
        return topics
    
    def format_for_output(self, topics: List[Topic]) -> List[Dict[str, Any]]:
        """Convert Topic objects back to dictionary format for JSON output."""
        return [
            {
                'name': t.name,
                'score': round(t.score, 2),
                'sources': t.sources,
                'source_count': t.source_count,
                'keywords': t.keywords,
                'why_trending': t.why_trending
            }
            for t in topics
        ]


if __name__ == '__main__':
    # Test the extractor
    extractor = TopicExtractor()
    
    # Test deduplication
    test_topics = [
        Topic(name="Local-first Software", canonical_name="", score=100, sources=[{'type': 'hn'}]),
        Topic(name="Software: Local First", canonical_name="", score=80, sources=[{'type': 'github'}]),
        Topic(name="AI Code Generation", canonical_name="", score=90, sources=[{'type': 'devto'}]),
    ]
    
    deduplicated = extractor.deduplicate_topics(test_topics)
    print(f"Deduplicated {len(test_topics)} topics to {len(deduplicated)}")
    for t in deduplicated:
        print(f"  - {t.name} (sources: {t.source_count})")