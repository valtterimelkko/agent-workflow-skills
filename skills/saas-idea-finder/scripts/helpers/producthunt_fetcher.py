#!/usr/bin/env python3
"""Product Hunt GraphQL API fetcher for trending products."""

import sys
import json
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime


class ProductHuntFetcher:
    """Fetches trending products from Product Hunt GraphQL API."""

    API_URL = "https://api.producthunt.com/v2/api/graphql"

    def __init__(self, token: Optional[str] = None):
        """
        Initialize the Product Hunt fetcher.

        Args:
            token: Product Hunt developer token. If None, loads from credential system.
        """
        if token:
            self.token = token
        else:
            # Lazy import to avoid circular dependency issues
            try:
                import os
                sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'shared'))
                from credentials import load_credential, CredentialNotFound
                self.token = load_credential(
                    'PRODUCTHUNT_TOKEN',
                    required=True
                )
            except Exception as e:
                raise ValueError(f"PRODUCTHUNT_TOKEN not found: {e}")

        self.headers = {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.token}',
            'Host': 'api.producthunt.com'
        }

    def _make_request(self, query: str, variables: Optional[Dict] = None) -> Optional[Dict]:
        """
        Make a GraphQL request to Product Hunt API.

        Args:
            query: GraphQL query string
            variables: Optional query variables

        Returns:
            JSON response data or None if error
        """
        try:
            payload = {'query': query}
            if variables:
                payload['variables'] = variables

            response = requests.post(
                self.API_URL,
                headers=self.headers,
                data=json.dumps(payload),
                timeout=15
            )

            if response.status_code == 429:
                # Rate limit hit
                print("Warning: Product Hunt API rate limit reached", file=sys.stderr)
                return None

            if response.status_code == 401:
                print("Warning: Product Hunt API authentication failed", file=sys.stderr)
                return None

            response.raise_for_status()
            data = response.json()

            if 'errors' in data:
                error_msg = data['errors'][0].get('message', 'Unknown GraphQL error')
                print(f"Warning: Product Hunt GraphQL error: {error_msg}", file=sys.stderr)
                return None

            return data.get('data')

        except requests.exceptions.RequestException as e:
            print(f"Warning: Product Hunt API request error: {e}", file=sys.stderr)
            return None
        except json.JSONDecodeError as e:
            print(f"Warning: Product Hunt API JSON decode error: {e}", file=sys.stderr)
            return None
        except Exception as e:
            print(f"Warning: Product Hunt API unexpected error: {e}", file=sys.stderr)
            return None

    def get_todays_posts(self, first: int = 20) -> List[Dict[str, Any]]:
        """
        Fetch today's featured posts from Product Hunt.

        Args:
            first: Number of posts to fetch (max ~20 per query for complexity)

        Returns:
            List of post dictionaries
        """
        query = """
        query getPosts($first: Int) {
            posts(first: $first) {
                edges {
                    node {
                        id
                        name
                        tagline
                        description
                        url
                        votesCount
                        commentsCount
                        createdAt
                        topics {
                            edges {
                                node {
                                    name
                                }
                            }
                        }
                        user {
                            name
                            username
                        }
                    }
                }
            }
        }
        """

        variables = {'first': first}
        data = self._make_request(query, variables)

        if not data or 'posts' not in data:
            return []

        # Transform to standard format
        results = []
        edges = data['posts'].get('edges', [])

        for edge in edges:
            node = edge.get('node', {})
            if not node:
                continue

            # Extract topics
            topics = []
            topic_edges = node.get('topics', {}).get('edges', [])
            for topic_edge in topic_edges:
                topic_node = topic_edge.get('node', {})
                if topic_node and topic_node.get('name'):
                    topics.append(topic_node['name'])

            results.append({
                'id': node.get('id', ''),
                'name': node.get('name', ''),
                'tagline': node.get('tagline', ''),
                'description': node.get('description', ''),
                'url': node.get('url', ''),
                'votes_count': node.get('votesCount', 0),
                'comments_count': node.get('commentsCount', 0),
                'created_at': node.get('createdAt', ''),
                'topics': topics,
                'maker': node.get('user', {}).get('name', 'Unknown')
            })

        return results

    def get_posts_by_topic(self, topic_slug: str, first: int = 10) -> List[Dict[str, Any]]:
        """
        Fetch posts filtered by a specific topic.

        Args:
            topic_slug: Topic slug (e.g., 'artificial-intelligence', 'developer-tools')
            first: Number of posts to fetch

        Returns:
            List of post dictionaries
        """
        query = """
        query getPostsByTopic($topicSlug: String!, $first: Int) {
            posts(first: $first, topic: $topicSlug) {
                edges {
                    node {
                        id
                        name
                        tagline
                        description
                        url
                        votesCount
                        commentsCount
                        createdAt
                        topics {
                            edges {
                                node {
                                    name
                                }
                            }
                        }
                        user {
                            name
                            username
                        }
                    }
                }
            }
        }
        """

        variables = {
            'topicSlug': topic_slug,
            'first': first
        }
        data = self._make_request(query, variables)

        if not data or 'posts' not in data:
            return []

        # Transform to standard format
        results = []
        edges = data['posts'].get('edges', [])

        for edge in edges:
            node = edge.get('node', {})
            if not node:
                continue

            # Extract topics
            topics = []
            topic_edges = node.get('topics', {}).get('edges', [])
            for topic_edge in topic_edges:
                topic_node = topic_edge.get('node', {})
                if topic_node and topic_node.get('name'):
                    topics.append(topic_node['name'])

            results.append({
                'id': node.get('id', ''),
                'name': node.get('name', ''),
                'tagline': node.get('tagline', ''),
                'description': node.get('description', ''),
                'url': node.get('url', ''),
                'votes_count': node.get('votesCount', 0),
                'comments_count': node.get('commentsCount', 0),
                'created_at': node.get('createdAt', ''),
                'topics': topics,
                'maker': node.get('user', {}).get('name', 'Unknown'),
                'matched_topic': topic_slug
            })

        return results

    def get_posts_for_lens(self, lens_topics: List[str], limit_per_topic: int = 5) -> List[Dict[str, Any]]:
        """
        Get posts for multiple lens-related topics.

        Args:
            lens_topics: List of topic slugs relevant to the lens
            limit_per_topic: Max posts per topic

        Returns:
            Combined deduplicated list of posts
        """
        all_posts = []
        seen_ids = set()

        for topic in lens_topics:
            # Small delay to respect rate limits
            import time
            time.sleep(0.5)

            posts = self.get_posts_by_topic(topic, first=limit_per_topic)

            # Deduplicate by ID
            for post in posts:
                post_id = post.get('id')
                if post_id and post_id not in seen_ids:
                    seen_ids.add(post_id)
                    all_posts.append(post)

        # Sort by votes (popularity)
        all_posts.sort(key=lambda x: x.get('votes_count', 0), reverse=True)

        return all_posts

    @staticmethod
    def extract_topics(posts: List[Dict]) -> List[Dict[str, Any]]:
        """
        Extract trending topics from Product Hunt posts.

        Args:
            posts: List of Product Hunt posts

        Returns:
            List of trending topics with metadata
        """
        topics = []

        for post in posts:
            # Calculate score based on engagement
            # Votes have higher weight than comments
            votes = post.get('votes_count', 0)
            comments = post.get('comments_count', 0)
            score = votes + (comments * 2)

            # Get all topic tags
            topic_tags = post.get('topics', [])

            topic = {
                'name': f"{post['name']}: {post['tagline']}",
                'score': score,
                'source': 'producthunt',
                'url': post.get('url', ''),
                'description': post.get('description', ''),
                'topics': topic_tags,
                'votes': votes,
                'comments': comments,
                'created_at': post.get('created_at', ''),
                'maker': post.get('maker', 'Unknown'),
                'keywords': topic_tags
            }

            topics.append(topic)

        return topics


if __name__ == '__main__':
    # Test the fetcher
    print("Testing Product Hunt fetcher...")

    try:
        fetcher = ProductHuntFetcher()

        print("\n1. Today's featured posts:")
        posts = fetcher.get_todays_posts(first=3)
        for i, post in enumerate(posts, 1):
            print(f"  {i}. {post['name']}: {post['tagline']}")
            print(f"     Votes: {post['votes_count']}, Comments: {post['comments_count']}")

        print("\n2. Posts by topic 'developer-tools':")
        topic_posts = fetcher.get_posts_by_topic('developer-tools', first=3)
        for i, post in enumerate(topic_posts, 1):
            print(f"  {i}. {post['name']}")

        print("\n3. Extracted topics:")
        topics = ProductHuntFetcher.extract_topics(posts[:3])
        for topic in topics:
            print(f"   - {topic['name'][:60]}...")
            print(f"     Score: {topic['score']}")

        print("\n✅ Product Hunt fetcher test complete!")

    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("Make sure PRODUCTHUNT_TOKEN is set in your environment or a shell startup file such as ~/.bashrc")