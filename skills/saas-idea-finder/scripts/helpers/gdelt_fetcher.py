#!/usr/bin/env python3
"""GDELT (Global Database of Events, Language, and Tone) fetcher for global news trends."""

import requests
import time
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any


class GDELTFetcher:
    """
    Fetches global news trends from GDELT Analysis Service.
    
    GDELT monitors news media from around the world and provides
    access to trends, themes, and mentions data.
    
    Uses the free GDELT Analysis Service API (no API key required).
    """

    ANALYSIS_API = "https://api.gdeltproject.org/api/v2"

    # Common GDELT themes relevant to tech/business
    THEMES = {
        'TECHNOLOGY': 'Technology and Computing',
        'ARTIFICIAL_INTELLIGENCE': 'AI and Machine Learning',
        'CYBER_SECURITY': 'Cybersecurity',
        'DATA_PRIVACY': 'Data Privacy',
        'CLOUD_COMPUTING': 'Cloud Computing',
        'STARTUP': 'Startups and Entrepreneurship',
        'INNOVATION': 'Innovation',
        'ECON_INVESTMENT': 'Investment and Finance',
        'DIGITAL_ECONOMY': 'Digital Economy',
        'REMOTE_WORK': 'Remote Work',
        'BLOCKCHAIN': 'Blockchain and Cryptocurrency',
        'SUSTAINABILITY': 'Sustainability and Green Tech'
    }

    def __init__(self, timeout: int = 30):
        """
        Initialize the GDELT fetcher.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'saas-idea-finder/1.0'
        })

    def get_trending_topics(
        self,
        keywords: List[str],
        days: int = 7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch trending topics from GDELT based on keywords.

        Args:
            keywords: List of keywords to search for
            days: Time period to analyze
            limit: Maximum number of results to return

        Returns:
            List of trending topic dictionaries
        """
        try:
            # GDELT uses date format: YYYYMMDD
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            # Build query string (GDELT requires OR queries to be wrapped in parentheses)
            query = '(' + ' OR '.join([f'"{kw}"' for kw in keywords]) + ')'

            params = {
                'query': query,
                'mode': 'ArtList',  # Article list mode
                'format': 'json',
                'startdatetime': start_date.strftime('%Y%m%d%H%M%S'),
                'enddatetime': end_date.strftime('%Y%m%d%H%M%S'),
                'maxrecords': min(limit, 250),
                'sort': 'ToneAsc'  # Sort by sentiment tone
            }

            response = self.session.get(
                f"{self.ANALYSIS_API}/doc/doc",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            return self._parse_articles(data, keywords)

        except requests.exceptions.RequestException as e:
            print(f"Warning: GDELT API error: {e}")
            return []
        except Exception as e:
            print(f"Warning: GDELT parsing error: {e}")
            return []

    def get_mentions_by_theme(
        self,
        themes: List[str],
        days: int = 7,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch news mentions by GDELT theme categories.

        Args:
            themes: List of GDELT theme codes (e.g., ['TECHNOLOGY', 'CYBER_SECURITY'])
            days: Time period to analyze
            limit: Maximum number of results to return

        Returns:
            List of mention dictionaries with theme information
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            mentions = []

            for theme in themes[:2]:  # Limit to 2 themes to reduce API calls
                # Use GDELT's theme query syntax
                query = f'theme:"{theme}"'

                params = {
                    'query': query,
                    'mode': 'ArtList',
                    'format': 'json',
                    'startdatetime': start_date.strftime('%Y%m%d%H%M%S'),
                    'enddatetime': end_date.strftime('%Y%m%d%H%M%S'),
                    'maxrecords': min(limit, 25),  # Reduced limit
                    'sort': 'DateDesc'
                }

                try:
                    response = self.session.get(
                        f"{self.ANALYSIS_API}/doc/doc",
                        params=params,
                        timeout=self.timeout
                    )
                    response.raise_for_status()
                    
                    # Check content type
                    content_type = response.headers.get('content-type', '')
                    if 'json' not in content_type:
                        print(f"Warning: GDELT returned non-JSON response ({content_type})")
                        continue
                    
                    # Try to parse JSON
                    try:
                        data = response.json()
                    except json.JSONDecodeError as je:
                        print(f"Warning: GDELT JSON parse error: {je}")
                        continue

                    theme_mentions = self._parse_mentions(data, theme)
                    mentions.extend(theme_mentions)

                except requests.exceptions.RequestException as re:
                    print(f"Warning: GDELT request error for theme {theme}: {re}")
                    continue

                # Be nice to the API
                time.sleep(0.3)

            # Sort by mention count/tone and limit results
            mentions.sort(key=lambda x: x.get('mention_count', 0), reverse=True)
            return mentions[:limit]

        except Exception as e:
            print(f"Warning: GDELT fetch error: {e}")
            return []

    def _parse_articles(
        self,
        data: Dict,
        keywords: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Parse GDELT article list response.

        Args:
            data: GDELT API response data
            keywords: Original search keywords

        Returns:
            List of parsed article dictionaries
        """
        articles = []

        # GDELT returns articles in 'articles' key
        gdelt_articles = data.get('articles', []) if isinstance(data, dict) else []

        for item in gdelt_articles:
            article = {
                'id': item.get('url', ''),  # Use URL as ID
                'title': item.get('title', ''),
                'url': item.get('url', ''),
                'source': item.get('domain', 'Unknown'),
                'language': item.get('language', 'en'),
                'published_date': item.get('seendate', ''),
                'country_code': item.get('sourcecountry', ''),
                'tone': item.get('tone', 0),
                'keyword_matched': keywords[0] if keywords else '',
                'mention_count': 1  # Individual article
            }
            articles.append(article)

        return articles

    def _parse_mentions(
        self,
        data: Dict,
        theme: str
    ) -> List[Dict[str, Any]]:
        """
        Parse GDELT mentions response for themes.

        Args:
            data: GDELT API response data
            theme: Theme code

        Returns:
            List of parsed mention dictionaries
        """
        mentions = []

        gdelt_articles = data.get('articles', []) if isinstance(data, dict) else []

        for item in gdelt_articles:
            mention = {
                'id': f"{theme}_{item.get('seendate', '')}_{hash(item.get('url', ''))}",
                'theme': theme,
                'theme_description': self.THEMES.get(theme, theme),
                'title': item.get('title', ''),
                'url': item.get('url', ''),
                'source': item.get('domain', 'Unknown'),
                'country_code': item.get('sourcecountry', ''),
                'date': item.get('seendate', ''),
                'tone': item.get('tone', 0),
                'mention_count': 1
            }
            mentions.append(mention)

        return mentions

    def get_volume_trends(
        self,
        keywords: List[str],
        days: int = 7
    ) -> Dict[str, Any]:
        """
        Get volume/timeline trends for keywords (volume of coverage over time).

        Args:
            keywords: List of keywords to analyze
            days: Time period to analyze

        Returns:
            Dictionary with timeline data and volume statistics
        """
        try:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)

            query = '(' + ' OR '.join([f'"{kw}"' for kw in keywords]) + ')'

            params = {
                'query': query,
                'mode': 'timeline',
                'format': 'json',
                'startdatetime': start_date.strftime('%Y%m%d%H%M%S'),
                'enddatetime': end_date.strftime('%Y%m%d%H%M%S'),
                'timelinesmooth': '5'  # 5-point smoothing
            }

            response = self.session.get(
                f"{self.ANALYSIS_API}/doc/doc",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            # Parse timeline data
            timeline = data.get('timeline', []) if isinstance(data, dict) else []

            return {
                'keywords': keywords,
                'days_analyzed': days,
                'timeline': timeline,
                'total_mentions': sum(point.get('value', 0) for point in timeline),
                'peak_date': max(timeline, key=lambda x: x.get('value', 0)).get('date', '') if timeline else ''
            }

        except requests.exceptions.RequestException as e:
            print(f"Warning: GDELT API error: {e}")
            return {'keywords': keywords, 'timeline': [], 'total_mentions': 0}
        except Exception as e:
            print(f"Warning: GDELT parsing error: {e}")
            return {'keywords': keywords, 'timeline': [], 'total_mentions': 0}

    @staticmethod
    def extract_topics(mentions: List[Dict]) -> List[Dict[str, Any]]:
        """
        Extract trending topics from GDELT mentions.

        Args:
            mentions: List of GDELT mentions

        Returns:
            List of trending topics with metadata
        """
        topics = []

        for mention in mentions:
            # Score based on tone and source diversity
            tone = mention.get('tone', 0)
            score = 50 + abs(tone)  # Higher score for strong sentiment

            topic = {
                'name': mention.get('title', ''),
                'score': int(score),
                'source': 'gdelt',
                'url': mention.get('url', ''),
                'theme': mention.get('theme', ''),
                'country': mention.get('country_code', ''),
                'published_at': mention.get('date', ''),
                'sentiment': tone
            }

            topics.append(topic)

        return topics


if __name__ == '__main__':
    # Test the fetcher
    print("Testing GDELT fetcher...")

    fetcher = GDELTFetcher()

    print("\n1. Trending topics for AI/technology:")
    topics = fetcher.get_trending_topics(
        keywords=['artificial intelligence', 'technology', 'startup'],
        days=7,
        limit=5
    )
    for i, topic in enumerate(topics, 1):
        print(f"  {i}. {topic['title'][:80]}...")
        print(f"     Source: {topic['source']}, Country: {topic['country_code']}")
        print(f"     Tone: {topic.get('tone', 0):.2f}")

    print("\n2. Mentions by theme (TECHNOLOGY):")
    mentions = fetcher.get_mentions_by_theme(
        themes=['TECHNOLOGY', 'INNOVATION'],
        days=7,
        limit=5
    )
    for i, m in enumerate(mentions, 1):
        print(f"  {i}. [{m['theme']}] {m['title'][:70]}...")
        print(f"     Source: {m['source']}, Date: {m['date']}")

    print("\n3. Extracted topics:")
    extracted = GDELTFetcher.extract_topics(topics)
    for topic in extracted[:3]:
        print(f"   - {topic['name'][:70]}...")
        print(f"     Score: {topic['score']}, Sentiment: {topic['sentiment']:.2f}")

    print("\n✅ GDELT fetcher test complete!")
    print("Note: GDELT API is free but rate-limited. Results may vary based on global news coverage.")