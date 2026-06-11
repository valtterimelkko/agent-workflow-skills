#!/usr/bin/env python3
"""SerpAPI fetcher for Google search trends and SaaS idea validation."""

import sys
import time
import requests
from pathlib import Path
from typing import List, Dict, Optional, Any


class SerpAPIFetcher:
    """
    Fetches Google search trends and validates SaaS ideas via SerpAPI.
    
    SerpAPI provides access to Google Search, Google Trends, and other
    Google services in a structured format.
    """

    BASE_URL = "https://serpapi.com/search"

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the SerpAPI fetcher.

        Args:
            api_key: SerpAPI key. If None, loads from credential system.
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
                    'SERPAPI_KEY',
                    required=False
                )
            except Exception:
                self.api_key = None

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'saas-idea-finder/1.0'
        })

    def get_trending_searches(
        self,
        keywords: List[str],
        geo: str = "US",
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch Google Trends data for keywords.

        Args:
            keywords: List of keywords to analyze
            geo: Geographic location (country code, e.g., 'US', 'GB')
            limit: Maximum number of results to return

        Returns:
            List of trending search data with interest scores
        """
        try:
            trends = []

            # Get trending searches for the region first
            params = {
                'engine': 'google_trends_trending_now',
                'geo': geo,
                'api_key': self.api_key
            }

            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=30
            )

            if response.status_code == 429:
                print("Warning: SerpAPI rate limit reached")
                return []

            response.raise_for_status()
            data = response.json()

            # Parse trending searches
            trending_searches = data.get('trending_searches', [])

            for item in trending_searches[:limit]:
                query = item.get('query', '')

                # Check if query matches any of our keywords
                if any(kw.lower() in query.lower() for kw in keywords):
                    trend = {
                        'id': f"trend_{hash(query)}",
                        'query': query,
                        'trend_score': item.get('search_volume', 0),
                        'related_queries': item.get('related_queries', []),
                        'url': f"https://trends.google.com/trends/explore?geo={geo}&q={query}",
                        'geo': geo,
                        'timestamp': item.get('timestamp', '')
                    }
                    trends.append(trend)

            # If no keyword matches, get interest over time for first keyword
            if not trends and keywords:
                interest_data = self._get_interest_over_time(keywords[0], geo)
                if interest_data:
                    trends.append(interest_data)

            # Be nice to the API
            time.sleep(0.2)

            return trends

        except requests.exceptions.RequestException as e:
            print(f"Warning: SerpAPI error: {e}")
            return []
        except Exception as e:
            print(f"Warning: SerpAPI unexpected error: {e}")
            return []

    def _get_interest_over_time(
        self,
        keyword: str,
        geo: str = "US"
    ) -> Optional[Dict[str, Any]]:
        """
        Get interest over time data for a keyword.

        Args:
            keyword: Search term
            geo: Geographic location

        Returns:
            Interest data dictionary or None
        """
        try:
            params = {
                'engine': 'google_trends',
                'q': keyword,
                'geo': geo,
                'data_type': 'TIMESERIES',
                'api_key': self.api_key
            }

            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            # Extract interest data
            interest_over_time = data.get('interest_over_time', {})
            timeline_data = interest_over_time.get('timeline_data', [])

            if timeline_data:
                # Calculate average interest
                values = [
                    point.get('values', [{}])[0].get('value', 0)
                    for point in timeline_data
                ]
                avg_interest = sum(values) / len(values) if values else 0

                return {
                    'id': f"interest_{hash(keyword)}",
                    'query': keyword,
                    'trend_score': int(avg_interest),
                    'related_queries': [],
                    'url': f"https://trends.google.com/trends/explore?geo={geo}&q={keyword}",
                    'geo': geo,
                    'timeline': timeline_data[:10]  # Last 10 periods
                }

            return None

        except Exception:
            return None

    def search_validation(
        self,
        query: str,
        location: str = "United States"
    ) -> Dict[str, Any]:
        """
        Validate a SaaS idea by analyzing Google search results.

        Args:
            query: The SaaS idea/concept to validate (e.g., "AI writing assistant")
            location: Search location

        Returns:
            Validation data including search volume, competition, and insights
        """
        try:
            params = {
                'engine': 'google',
                'q': query,
                'location': location,
                'num': 20,
                'api_key': self.api_key
            }

            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=30
            )

            if response.status_code == 429:
                return {'error': 'Rate limit reached', 'query': query}

            response.raise_for_status()
            data = response.json()

            # Analyze search results
            organic_results = data.get('organic_results', [])
            ads = data.get('ads', [])
            related_questions = data.get('related_questions', [])
            related_searches = data.get('related_searches', [])

            # Calculate competition level
            competition = self._calculate_competition(organic_results, ads)

            # Extract insights
            insights = {
                'search_volume_indicator': self._estimate_search_volume(
                    len(organic_results), len(ads), len(related_searches)
                ),
                'competition_level': competition,
                'existing_solutions': self._extract_competitors(organic_results),
                'user_pain_points': self._extract_pain_points(related_questions),
                'related_keywords': [s.get('query', '') for s in related_searches[:5]]
            }

            return {
                'id': f"validation_{hash(query)}",
                'query': query,
                'trend_score': self._calculate_opportunity_score(insights),
                'related_queries': insights['related_keywords'],
                'url': f"https://www.google.com/search?q={query.replace(' ', '+')}",
                'validation': insights,
                'result_count': len(organic_results),
                'ad_count': len(ads)
            }

        except requests.exceptions.RequestException as e:
            print(f"Warning: SerpAPI validation error: {e}")
            return {'query': query, 'error': str(e), 'trend_score': 0}
        except Exception as e:
            print(f"Warning: SerpAPI unexpected error: {e}")
            return {'query': query, 'error': str(e), 'trend_score': 0}

    def _calculate_competition(
        self,
        organic_results: List[Dict],
        ads: List[Dict]
    ) -> str:
        """Calculate competition level based on results."""
        score = 0

        # Check for big players
        big_players = ['microsoft', 'google', 'amazon', 'salesforce', 'oracle', 'adobe']
        domains = [r.get('domain', '').lower() for r in organic_results[:10]]

        for player in big_players:
            if any(player in d for d in domains):
                score += 2

        # Ads indicate high commercial intent
        score += len(ads) * 1.5

        if score >= 8:
            return 'High'
        elif score >= 4:
            return 'Medium'
        else:
            return 'Low'

    def _estimate_search_volume(
        self,
        organic_count: int,
        ads_count: int,
        related_count: int
    ) -> str:
        """Estimate search volume category."""
        score = organic_count + (ads_count * 2) + related_count

        if score > 30:
            return 'High'
        elif score > 15:
            return 'Medium'
        else:
            return 'Low'

    def _extract_competitors(self, organic_results: List[Dict]) -> List[Dict]:
        """Extract competitor information from search results."""
        competitors = []

        for result in organic_results[:5]:
            competitor = {
                'title': result.get('title', ''),
                'domain': result.get('domain', ''),
                'url': result.get('link', ''),
                'snippet': result.get('snippet', '')
            }
            competitors.append(competitor)

        return competitors

    def _extract_pain_points(self, related_questions: List[Dict]) -> List[str]:
        """Extract potential pain points from related questions."""
        pain_indicators = [
            'how to', 'why is', 'what is', 'problem', 'issue',
            'error', 'fix', 'solution', 'alternative', 'best'
        ]

        pain_points = []

        for question in related_questions:
            q = question.get('question', '').lower()
            if any(indicator in q for indicator in pain_indicators):
                pain_points.append(question.get('question', ''))

        return pain_points[:5]

    def _calculate_opportunity_score(self, insights: Dict) -> int:
        """Calculate an opportunity score for the SaaS idea."""
        score = 50  # Base score

        # Adjust based on competition
        competition = insights.get('competition_level', 'Medium')
        if competition == 'Low':
            score += 30
        elif competition == 'Medium':
            score += 10
        else:
            score -= 10

        # Adjust based on search volume
        volume = insights.get('search_volume_indicator', 'Medium')
        if volume == 'High':
            score += 20
        elif volume == 'Medium':
            score += 10

        # Bonus for identified pain points
        pain_points = insights.get('user_pain_points', [])
        score += min(len(pain_points) * 5, 20)

        return max(0, min(100, score))  # Clamp between 0-100

    @staticmethod
    def extract_topics(validations: List[Dict]) -> List[Dict[str, Any]]:
        """
        Extract trending topics from SerpAPI validation results.

        Args:
            validations: List of validation dictionaries

        Returns:
            List of trending topics with metadata
        """
        topics = []

        for validation in validations:
            if 'error' in validation:
                continue

            score = validation.get('trend_score', 50)
            insights = validation.get('validation', {})

            topic = {
                'name': validation['query'],
                'score': score,
                'source': 'serpapi',
                'url': validation['url'],
                'competition': insights.get('competition_level', 'Unknown'),
                'search_volume': insights.get('search_volume_indicator', 'Unknown'),
                'related_keywords': validation.get('related_queries', [])
            }

            topics.append(topic)

        return topics


if __name__ == '__main__':
    # Test the fetcher
    print("Testing SerpAPI fetcher...")

    try:
        fetcher = SerpAPIFetcher()

        print("\n1. Trending searches for AI/tech:")
        trends = fetcher.get_trending_searches(
            keywords=['AI', 'software', 'automation'],
            geo='US',
            limit=5
        )
        for i, trend in enumerate(trends, 1):
            print(f"  {i}. {trend['query']}")
            print(f"     Trend Score: {trend['trend_score']}")
            if trend['related_queries']:
                print(f"     Related: {', '.join(trend['related_queries'][:3])}")

        print("\n2. Search validation for SaaS idea:")
        validation = fetcher.search_validation(
            query="AI writing assistant for developers",
            location="United States"
        )
        print(f"   Query: {validation['query']}")
        print(f"   Opportunity Score: {validation['trend_score']}/100")
        if 'validation' in validation:
            v = validation['validation']
            print(f"   Competition: {v['competition_level']}")
            print(f"   Search Volume: {v['search_volume_indicator']}")
            print(f"   Top Competitors: {len(v['existing_solutions'])}")

        print("\n3. Extracted topics:")
        topics = SerpAPIFetcher.extract_topics([validation])
        for topic in topics:
            print(f"   - {topic['name']}")
            print(f"     Score: {topic['score']}, Competition: {topic['competition']}")

        print("\n✅ SerpAPI fetcher test complete!")

    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("Make sure SERPAPI_KEY is set in your environment or a shell startup file such as ~/.bashrc")