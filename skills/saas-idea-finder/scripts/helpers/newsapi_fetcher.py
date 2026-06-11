#!/usr/bin/env python3
"""NewsAPI fetcher for trending news topics."""

import sys
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


class NewsAPIFetcher:
    """Fetches trending topics from NewsAPI."""

    BASE_URL = "https://newsapi.org/v2"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the NewsAPI fetcher.

        Args:
            api_key: NewsAPI key. If None, loads from credential system.
        """
        if api_key:
            self.api_key = api_key
        else:
            # Lazy import to avoid circular dependency issues
            try:
                import os
                sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'shared'))
                from credentials import load_credential, CredentialNotFound
                self.api_key = load_credential(
                    'NEWSAPI_KEY',
                    required=True
                )
            except Exception as e:
                raise ValueError(f"NEWSAPI_KEY not found: {e}")

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'saas-idea-finder/1.0'
        })

    def get_top_headlines(
        self,
        category: Optional[str] = None,
        country: str = 'us',
        q: Optional[str] = None,
        page_size: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Fetch top headlines from NewsAPI.

        Args:
            category: News category (business, technology, etc.)
            country: Country code (default: 'us')
            q: Search query/keywords
            page_size: Number of results to return

        Returns:
            List of article dictionaries
        """
        try:
            params = {
                'apiKey': self.api_key,
                'pageSize': min(page_size, 100),  # API max is 100
                'country': country
            }

            if category:
                params['category'] = category
            if q:
                params['q'] = q

            response = self.session.get(
                f"{self.BASE_URL}/top-headlines",
                params=params,
                timeout=10
            )

            if response.status_code == 429:
                # Rate limit hit
                print("Warning: NewsAPI rate limit reached", file=sys.stderr)
                return []

            if response.status_code == 401:
                print("Warning: NewsAPI authentication failed", file=sys.stderr)
                return []

            response.raise_for_status()
            data = response.json()

            if data.get('status') != 'ok':
                print(f"Warning: NewsAPI error: {data.get('message', 'Unknown error')}", file=sys.stderr)
                return []

            articles = data.get('articles', [])

            # Transform to standard format
            results = []
            for article in articles:
                results.append({
                    'title': article.get('title', ''),
                    'url': article.get('url', ''),
                    'description': article.get('description', ''),
                    'published_at': article.get('publishedAt', ''),
                    'source': article.get('source', {}).get('name', 'Unknown'),
                    'author': article.get('author', ''),
                    'content': article.get('content', '')
                })

            return results

        except requests.exceptions.RequestException as e:
            print(f"Warning: NewsAPI request error: {e}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"Warning: NewsAPI unexpected error: {e}", file=sys.stderr)
            return []

    def search_everything(
        self,
        q: str,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        language: str = 'en',
        sort_by: str = 'relevancy',
        page_size: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search all articles with NewsAPI /everything endpoint.

        Args:
            q: Search query/keywords (required)
            from_date: Start date (YYYY-MM-DD)
            to_date: End date (YYYY-MM-DD)
            language: Language code (default: 'en')
            sort_by: Sort order (relevancy, popularity, publishedAt)
            page_size: Number of results to return

        Returns:
            List of article dictionaries
        """
        try:
            params = {
                'apiKey': self.api_key,
                'q': q,
                'language': language,
                'sortBy': sort_by,
                'pageSize': min(page_size, 100)
            }

            if from_date:
                params['from'] = from_date
            if to_date:
                params['to'] = to_date

            response = self.session.get(
                f"{self.BASE_URL}/everything",
                params=params,
                timeout=10
            )

            if response.status_code == 429:
                print("Warning: NewsAPI rate limit reached", file=sys.stderr)
                return []

            if response.status_code == 401:
                print("Warning: NewsAPI authentication failed", file=sys.stderr)
                return []

            response.raise_for_status()
            data = response.json()

            if data.get('status') != 'ok':
                print(f"Warning: NewsAPI error: {data.get('message', 'Unknown error')}", file=sys.stderr)
                return []

            articles = data.get('articles', [])

            # Transform to standard format
            results = []
            for article in articles:
                results.append({
                    'title': article.get('title', ''),
                    'url': article.get('url', ''),
                    'description': article.get('description', ''),
                    'published_at': article.get('publishedAt', ''),
                    'source': article.get('source', {}).get('name', 'Unknown'),
                    'author': article.get('author', ''),
                    'content': article.get('content', '')
                })

            return results

        except requests.exceptions.RequestException as e:
            print(f"Warning: NewsAPI request error: {e}", file=sys.stderr)
            return []
        except Exception as e:
            print(f"Warning: NewsAPI unexpected error: {e}", file=sys.stderr)
            return []

    def get_trending_by_keywords(
        self,
        keywords: List[str],
        days_back: int = 7,
        limit_per_keyword: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get trending articles for multiple keywords.

        Args:
            keywords: List of search terms
            days_back: How many days back to search
            limit_per_keyword: Max results per keyword

        Returns:
            Combined deduplicated list of articles
        """
        all_articles = []
        seen_urls = set()

        # Calculate date range
        to_date = datetime.now().strftime('%Y-%m-%d')
        from_date = (datetime.now() - timedelta(days=days_back)).strftime('%Y-%m-%d')

        for keyword in keywords:
            # Small delay to be respectful to API
            import time
            time.sleep(0.2)

            articles = self.search_everything(
                q=keyword,
                from_date=from_date,
                to_date=to_date,
                sort_by='popularity',
                page_size=limit_per_keyword
            )

            # Deduplicate by URL
            for article in articles:
                if article['url'] and article['url'] not in seen_urls:
                    seen_urls.add(article['url'])
                    article['query'] = keyword  # Track which keyword found this
                    all_articles.append(article)

        # Sort by published date (newest first)
        all_articles.sort(
            key=lambda x: x.get('published_at', ''),
            reverse=True
        )

        return all_articles

    @staticmethod
    def extract_topics(articles: List[Dict]) -> List[Dict[str, Any]]:
        """
        Extract trending topics from NewsAPI articles.

        Args:
            articles: List of NewsAPI articles

        Returns:
            List of trending topics with metadata
        """
        topics = []

        for article in articles:
            # Score based on source popularity (simplified)
            score = 50  # Base score

            topic = {
                'name': article['title'],
                'score': score,
                'source': 'newsapi',
                'url': article['url'],
                'description': article.get('description', ''),
                'published_at': article.get('published_at', ''),
                'source_name': article.get('source', 'Unknown'),
                'keywords': [article.get('query', '')] if article.get('query') else []
            }

            topics.append(topic)

        return topics


if __name__ == '__main__':
    # Test the fetcher
    print("Testing NewsAPI fetcher...")

    try:
        fetcher = NewsAPIFetcher()

        print("\n1. Top technology headlines:")
        articles = fetcher.get_top_headlines(category='technology', page_size=3)
        for i, article in enumerate(articles, 1):
            print(f"  {i}. {article['title']}")
            print(f"     Source: {article['source']}")

        print("\n2. Search for 'artificial intelligence':")
        search_articles = fetcher.search_everything(
            q='artificial intelligence',
            page_size=3
        )
        for i, article in enumerate(search_articles, 1):
            print(f"  {i}. {article['title']}")

        print("\n3. Trending by keywords:")
        trending = fetcher.get_trending_by_keywords(
            keywords=['startup', 'SaaS', 'AI'],
            days_back=7,
            limit_per_keyword=2
        )
        print(f"   Found {len(trending)} unique articles")

        print("\n✅ NewsAPI fetcher test complete!")

    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("Make sure NEWSAPI_KEY is set in your environment or a shell startup file such as ~/.bashrc")