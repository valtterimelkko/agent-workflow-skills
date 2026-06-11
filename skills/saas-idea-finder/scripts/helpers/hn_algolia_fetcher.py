#!/usr/bin/env python3
"""
Hacker News Algolia Search API Fetcher

Uses HN Algolia API to search for trending discussions by keywords.
Extends the existing HN top stories with keyword-based discovery.

API Documentation: https://hn.algolia.com/api
"""

import requests
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import time


class HNAlgoliaFetcher:
    """Fetch keyword-based trending discussions from Hacker News."""

    BASE_URL = "https://hn.algolia.com/api/v1"

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'saas-idea-finder/1.0'
        })

    def search_stories(
        self,
        query: str,
        days_back: int = 7,
        min_points: int = 50,
        limit: int = 20
    ) -> List[Dict]:
        """
        Search HN stories by keyword.

        Args:
            query: Search query (e.g., "rust async", "AI agents")
            days_back: How many days back to search
            min_points: Minimum score threshold
            limit: Max results to return

        Returns:
            List of matching HN stories
        """
        try:
            # Calculate timestamp for filtering
            cutoff_time = int(
                (datetime.now() - timedelta(days=days_back)).timestamp()
            )

            params = {
                'query': query,
                'tags': 'story',  # Only stories, not comments
                'numericFilters': (
                    f'created_at_i>{cutoff_time},'
                    f'points>{min_points}'
                ),
                'hitsPerPage': limit
            }

            response = self.session.get(
                f"{self.BASE_URL}/search",
                params=params,
                timeout=10
            )
            response.raise_for_status()

            data = response.json()
            hits = data.get('hits', [])

            # Transform to standard format
            stories = []
            for hit in hits:
                stories.append({
                    'title': hit.get('title', ''),
                    'url': hit.get('url', ''),
                    'hn_url': (
                        f"https://news.ycombinator.com/item?"
                        f"id={hit.get('objectID', '')}"
                    ),
                    'score': hit.get('points', 0),
                    'comments': hit.get('num_comments', 0),
                    'author': hit.get('author', ''),
                    'created_at': hit.get('created_at', ''),
                    'created_at_i': hit.get('created_at_i', 0),
                    'story_id': hit.get('objectID', ''),
                    'query': query  # Track which query found this
                })

            return stories

        except requests.exceptions.RequestException as e:
            print(f"Warning: HN Algolia API error for '{query}': {e}")
            return []

    def search_multiple_keywords(
        self,
        keywords: List[str],
        days_back: int = 7,
        min_points: int = 50,
        limit_per_keyword: int = 10
    ) -> List[Dict]:
        """
        Search for multiple keywords and combine results.

        Args:
            keywords: List of search terms
            days_back: Days to look back
            min_points: Minimum score threshold
            limit_per_keyword: Max results per keyword

        Returns:
            Combined deduplicated list of stories
        """
        all_stories = []
        seen_ids = set()

        for keyword in keywords:
            # Small delay to be respectful to API
            time.sleep(0.1)

            stories = self.search_stories(
                query=keyword,
                days_back=days_back,
                min_points=min_points,
                limit=limit_per_keyword
            )

            # Deduplicate by story ID
            for story in stories:
                story_id = story['story_id']
                if story_id and story_id not in seen_ids:
                    seen_ids.add(story_id)
                    all_stories.append(story)

        # Sort by score (points)
        all_stories.sort(key=lambda x: x['score'], reverse=True)

        return all_stories

    def get_trending_by_lens(
        self,
        lens_keywords: List[str],
        days_back: int = 7,
        limit: int = 20
    ) -> List[Dict]:
        """
        Get trending stories relevant to a lens.

        Args:
            lens_keywords: Keywords from lens configuration
            days_back: Days to search
            limit: Total results to return

        Returns:
            Top trending stories matching lens keywords
        """
        # Use adaptive min_points based on time window
        # Recent: lower threshold, Older: higher threshold
        if days_back <= 7:
            min_points = 30
        elif days_back <= 14:
            min_points = 50
        else:
            min_points = 100

        stories = self.search_multiple_keywords(
            keywords=lens_keywords,
            days_back=days_back,
            min_points=min_points,
            limit_per_keyword=max(5, limit // len(lens_keywords))
        )

        return stories[:limit]

    @staticmethod
    def extract_topics(stories: List[Dict]) -> List[Dict]:
        """
        Extract trending topics from HN Algolia stories.

        Args:
            stories: List of HN stories from Algolia

        Returns:
            List of trending topics
        """
        topics = []

        for story in stories:
            # Score: points + (comments * 1.5) to weight discussion
            score = story['score'] + (story['comments'] * 1.5)

            topic = {
                'name': story['title'],
                'score': score,
                'source': 'hn_algolia',
                'url': story['url'] or story['hn_url'],
                'hn_url': story['hn_url'],
                'keywords': [story['query']],
                'engagement': {
                    'points': story['score'],
                    'comments': story['comments']
                },
                'author': story['author'],
                'created_at': story['created_at']
            }

            topics.append(topic)

        return topics


if __name__ == '__main__':
    # Test the fetcher
    fetcher = HNAlgoliaFetcher()

    print("Testing HN Algolia fetcher...")

    print("\n1. Search for 'rust async':")
    stories = fetcher.search_stories('rust async', days_back=7, limit=3)
    for i, story in enumerate(stories, 1):
        print(f"  {i}. {story['title']}")
        print(f"     Score: {story['score']}, "
              f"Comments: {story['comments']}")

    print("\n2. Multiple keywords:")
    multi_stories = fetcher.search_multiple_keywords(
        keywords=['AI agents', 'local-first', 'rust'],
        days_back=7,
        limit_per_keyword=2
    )
    print(f"   Found {len(multi_stories)} unique stories")
    for story in multi_stories[:3]:
        print(f"   - {story['title']} (query: {story['query']})")

    print("\n3. Lens-based search:")
    lens_stories = fetcher.get_trending_by_lens(
        lens_keywords=['python', 'javascript', 'devtools'],
        days_back=7,
        limit=5
    )
    print(f"   Found {len(lens_stories)} trending stories")

    print("\n4. Extracted topics:")
    topics = HNAlgoliaFetcher.extract_topics(stories)
    for topic in topics:
        print(f"   - {topic['name']}")
        print(f"     Score: {topic['score']}")