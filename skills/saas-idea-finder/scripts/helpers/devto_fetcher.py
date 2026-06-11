#!/usr/bin/env python3
"""
DEV.to Forem API Fetcher

Fetches trending articles from DEV.to using the official Forem API.
Returns popularity-sorted posts from the developer community.

API Documentation: https://developers.forem.com/api/v0
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta


class DevToFetcher:
    """Fetch trending articles from DEV.to using Forem API."""

    BASE_URL = "https://dev.to/api"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'saas-idea-finder/1.0'
        })

    def get_trending_posts(
        self,
        days: int = 7,
        tag: Optional[str] = None,
        limit: int = 30
    ) -> List[Dict]:
        """
        Get trending posts from DEV.to.

        Args:
            days: Time period (7, 30, etc.)
            tag: Optional tag filter (e.g., 'python', 'javascript')
            limit: Max number of posts to return

        Returns:
            List of trending posts with metadata
        """
        try:
            # DEV.to API: 'top' parameter requires 'tag' parameter
            # Without tag, it returns featured articles by popularity
            params = {
                'per_page': min(limit, 1000)  # API max is 1000
            }

            if tag:
                # Map days to numbers (top param accepts numbers)
                if days <= 1:
                    top_param = '1'
                elif days <= 7:
                    top_param = '7'
                elif days <= 30:
                    top_param = '30'
                else:
                    top_param = '365'

                params['tag'] = tag
                params['top'] = top_param

            response = self.session.get(
                f"{self.BASE_URL}/articles",
                params=params,
                timeout=10
            )
            response.raise_for_status()

            articles = response.json()

            # Transform to standard format
            trending = []
            for article in articles[:limit]:
                trending.append({
                    'title': article.get('title', ''),
                    'url': article.get('url', ''),
                    'score': article.get('positive_reactions_count', 0),
                    'comments': article.get('comments_count', 0),
                    'published_at': article.get('published_at', ''),
                    'tags': article.get('tag_list', []),
                    'user': article.get('user', {}).get('username', ''),
                    'reading_time': article.get('reading_time_minutes', 0)
                })

            return trending

        except requests.exceptions.RequestException as e:
            print(f"Warning: DEV.to API error: {e}")
            return []

    def get_posts_by_tags(
        self,
        tags: List[str],
        days: int = 7,
        limit_per_tag: int = 10
    ) -> List[Dict]:
        """
        Get trending posts for multiple tags.

        Args:
            tags: List of tags to fetch (e.g., ['python', 'rust'])
            days: Time period
            limit_per_tag: Max posts per tag

        Returns:
            Combined list of trending posts from all tags
        """
        all_posts = []
        seen_urls = set()

        for tag in tags:
            posts = self.get_trending_posts(
                days=days,
                tag=tag,
                limit=limit_per_tag
            )

            # Deduplicate by URL
            for post in posts:
                if post['url'] not in seen_urls:
                    seen_urls.add(post['url'])
                    all_posts.append(post)

        # Sort by score (positive reactions)
        all_posts.sort(key=lambda x: x['score'], reverse=True)

        return all_posts

    @staticmethod
    def extract_topics(posts: List[Dict]) -> List[Dict]:
        """
        Extract trending topics from DEV.to posts.

        Args:
            posts: List of DEV.to posts

        Returns:
            List of trending topics with metadata
        """
        topics = []

        for post in posts:
            # Calculate trending score
            # DEV.to: reactions + (comments * 2) to weight engagement
            score = post['score'] + (post['comments'] * 2)

            topic = {
                'name': post['title'],
                'score': score,
                'source': 'devto',
                'url': post['url'],
                'tags': post['tags'],
                'engagement': {
                    'reactions': post['score'],
                    'comments': post['comments'],
                    'reading_time': post['reading_time']
                },
                'published_at': post['published_at']
            }

            topics.append(topic)

        return topics


if __name__ == '__main__':
    # Test the fetcher
    fetcher = DevToFetcher()

    print("Testing DEV.to fetcher...")
    print("\n1. Trending posts this week:")
    posts = fetcher.get_trending_posts(days=7, limit=5)
    for i, post in enumerate(posts, 1):
        print(f"  {i}. {post['title']}")
        print(f"     Score: {post['score']}, Comments: {post['comments']}")
        print(f"     Tags: {', '.join(post['tags'][:3])}")

    print("\n2. Trending by tags:")
    tagged_posts = fetcher.get_posts_by_tags(
        tags=['python', 'javascript', 'ai'],
        days=7,
        limit_per_tag=3
    )
    print(f"   Found {len(tagged_posts)} posts across tags")

    print("\n3. Extracted topics:")
    topics = DevToFetcher.extract_topics(posts)
    for topic in topics[:3]:
        print(f"   - {topic['name']}")
        print(f"     Score: {topic['score']}")