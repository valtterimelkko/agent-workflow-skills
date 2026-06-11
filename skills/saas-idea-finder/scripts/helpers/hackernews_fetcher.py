#!/usr/bin/env python3
"""HackerNews API fetcher for trending stories."""

import requests
import time
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any


class HackerNewsFetcher:
    """Fetches trending stories from HackerNews API."""

    API_BASE = "https://hacker-news.firebaseio.com/v0"
    ALGOLIA_SEARCH = "http://hn.algolia.com/api/v1"

    def __init__(self, timeout: int = 30):
        """
        Initialize the HackerNews fetcher.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout

    @staticmethod
    def get_adaptive_min_score(since_days: int) -> int:
        """
        Calculate adaptive minimum score based on time window.
        Recent stories don't have high scores yet, so we lower the threshold.

        Args:
            since_days: Time window in days

        Returns:
            Recommended minimum score threshold
        """
        if since_days <= 7:
            return 50  # Recent stories, lower threshold
        elif since_days <= 14:
            return 100  # Two weeks, moderate threshold
        elif since_days <= 30:
            return 200  # One month, higher threshold
        else:
            return 300  # Older stories, highest threshold

    def get_top_stories(self, min_score: Optional[int] = None, since_days: int = 7, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Fetch top stories from HackerNews.

        Args:
            min_score: Minimum score (points) threshold. If None, uses adaptive scoring based on since_days.
            since_days: Only include stories from the last N days
            limit: Maximum number of stories to fetch

        Returns:
            List of story dictionaries
        """
        # Use adaptive scoring if min_score not provided
        if min_score is None:
            min_score = self.get_adaptive_min_score(since_days)

        try:
            # Get top story IDs
            response = requests.get(
                f"{self.API_BASE}/topstories.json",
                timeout=self.timeout
            )
            response.raise_for_status()
            story_ids = response.json()[:limit * 2]  # Fetch extra to filter

            stories = []
            cutoff_time = (datetime.now() - timedelta(days=since_days)).timestamp()

            for story_id in story_ids:
                if len(stories) >= limit:
                    break

                story = self._fetch_item(story_id)
                if story and story.get('type') == 'story':
                    # Filter by score and time
                    if story.get('score', 0) >= min_score and story.get('time', 0) >= cutoff_time:
                        stories.append({
                            'id': story.get('id'),
                            'title': story.get('title', ''),
                            'url': story.get('url', f"https://news.ycombinator.com/item?id={story.get('id')}"),
                            'score': story.get('score', 0),
                            'comments': story.get('descendants', 0),
                            'time': story.get('time', 0),
                            'by': story.get('by', 'unknown')
                        })

                # Be nice to the API
                time.sleep(0.05)

            return stories

        except Exception as e:
            print(f"Warning: HackerNews API error: {e}")
            return []

    def search_by_keywords(self, keywords: List[str], since_days: int = 7, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Search HackerNews using Algolia API with keywords.

        Args:
            keywords: List of keywords to search for
            since_days: Only include stories from the last N days
            limit: Maximum number of results

        Returns:
            List of story dictionaries
        """
        try:
            # Calculate timestamp for date filtering
            cutoff_timestamp = int((datetime.now() - timedelta(days=since_days)).timestamp())

            # Build query
            query = " OR ".join(keywords)

            response = requests.get(
                f"{self.ALGOLIA_SEARCH}/search",
                params={
                    'query': query,
                    'tags': 'story',
                    'numericFilters': f'created_at_i>{cutoff_timestamp}',
                    'hitsPerPage': limit
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            stories = []
            for hit in data.get('hits', []):
                stories.append({
                    'id': hit.get('objectID'),
                    'title': hit.get('title', ''),
                    'url': hit.get('url', f"https://news.ycombinator.com/item?id={hit.get('objectID')}"),
                    'score': hit.get('points', 0),
                    'comments': hit.get('num_comments', 0),
                    'time': hit.get('created_at_i', 0),
                    'by': hit.get('author', 'unknown')
                })

            return stories

        except Exception as e:
            print(f"Warning: HackerNews search error: {e}")
            return []

    def get_ask_hn_stories(self, since_days: int = 7, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Fetch recent "Ask HN" stories.

        Args:
            since_days: Only include stories from the last N days
            limit: Maximum number of stories

        Returns:
            List of Ask HN story dictionaries
        """
        try:
            cutoff_timestamp = int((datetime.now() - timedelta(days=since_days)).timestamp())

            response = requests.get(
                f"{self.ALGOLIA_SEARCH}/search",
                params={
                    'tags': 'ask_hn',
                    'numericFilters': f'created_at_i>{cutoff_timestamp}',
                    'hitsPerPage': limit
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            stories = []
            for hit in data.get('hits', []):
                stories.append({
                    'id': hit.get('objectID'),
                    'title': hit.get('title', ''),
                    'url': f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    'score': hit.get('points', 0),
                    'comments': hit.get('num_comments', 0),
                    'time': hit.get('created_at_i', 0),
                    'by': hit.get('author', 'unknown')
                })

            return stories

        except Exception as e:
            print(f"Warning: HackerNews Ask HN fetch error: {e}")
            return []

    def get_show_hn_stories(self, since_days: int = 7, limit: int = 25) -> List[Dict[str, Any]]:
        """
        Fetch recent "Show HN" stories (product launches).

        Args:
            since_days: Only include stories from the last N days
            limit: Maximum number of stories

        Returns:
            List of Show HN story dictionaries
        """
        try:
            cutoff_timestamp = int((datetime.now() - timedelta(days=since_days)).timestamp())

            response = requests.get(
                f"{self.ALGOLIA_SEARCH}/search",
                params={
                    'tags': 'show_hn',
                    'numericFilters': f'created_at_i>{cutoff_timestamp}',
                    'hitsPerPage': limit
                },
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            stories = []
            for hit in data.get('hits', []):
                stories.append({
                    'id': hit.get('objectID'),
                    'title': hit.get('title', ''),
                    'url': hit.get('url', f"https://news.ycombinator.com/item?id={hit.get('objectID')}"),
                    'score': hit.get('points', 0),
                    'comments': hit.get('num_comments', 0),
                    'time': hit.get('created_at_i', 0),
                    'by': hit.get('author', 'unknown')
                })

            return stories

        except Exception as e:
            print(f"Warning: HackerNews Show HN fetch error: {e}")
            return []

    def _fetch_item(self, item_id: int) -> Optional[Dict[str, Any]]:
        """Fetch a single item by ID."""
        try:
            response = requests.get(
                f"{self.API_BASE}/item/{item_id}.json",
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return None