#!/usr/bin/env python3
"""Stack Exchange API fetcher for unanswered questions and pain points."""

import sys
import time
import requests
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any


class StackExchangeFetcher:
    """Fetches unanswered questions and pain points from Stack Exchange API."""

    API_BASE = "https://api.stackexchange.com/2.3"

    # Popular Stack Exchange sites
    SITES = {
        'stackoverflow': 'Stack Overflow',
        'superuser': 'Super User',
        'serverfault': 'Server Fault',
        'askubuntu': 'Ask Ubuntu',
        'softwareengineering': 'Software Engineering',
        'webapps': 'Web Applications',
        'unix': 'Unix & Linux',
        'apple': 'Ask Different',
        'android': 'Android Enthusiasts',
        'security': 'Information Security',
        'crypto': 'Cryptography',
        'datascience': 'Data Science',
        'ai': 'Artificial Intelligence',
        'devops': 'DevOps'
    }

    def __init__(self, api_key: Optional[str] = None, timeout: int = 30):
        """
        Initialize the Stack Exchange fetcher.

        Args:
            api_key: Stack Exchange API key. If None, loads from credential system.
            timeout: Request timeout in seconds
        """
        self.timeout = timeout

        if api_key:
            self.api_key = api_key
        else:
            # Lazy import to avoid circular dependency issues
            try:
                import os
                sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'shared'))
                from credentials import load_credential, CredentialNotFound
                self.api_key = load_credential(
                    'STACK_KEY',
                    required=False
                )
            except Exception:
                self.api_key = None

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'saas-idea-finder/1.0',
            'Accept-Encoding': 'gzip'
        })

    def get_unanswered_questions(
        self,
        tags: List[str],
        days: int = 7,
        limit: int = 10,
        site: str = 'stackoverflow'
    ) -> List[Dict[str, Any]]:
        """
        Fetch unanswered questions from Stack Exchange.

        Args:
            tags: List of tags to filter by (e.g., ['python', 'javascript'])
            days: Only include questions from the last N days
            limit: Maximum number of questions to return
            site: Stack Exchange site to query

        Returns:
            List of question dictionaries
        """
        try:
            questions = []
            seen_ids = set()

            # Calculate date range
            from_date = int((datetime.now() - timedelta(days=days)).timestamp())

            # Query each tag separately (OR logic) since semicolon uses AND
            for tag in tags[:3]:  # Limit to first 3 tags to avoid rate limits
                params = {
                    'order': 'desc',
                    'sort': 'creation',
                    'tagged': tag,
                    'site': site,
                    'pagesize': min(limit // len(tags) + 1, 10),
                    'fromdate': from_date,
                    'filter': 'withbody'  # Include question body
                }

                if self.api_key:
                    params['key'] = self.api_key

                response = self.session.get(
                    f"{self.API_BASE}/questions/unanswered",
                    params=params,
                    timeout=self.timeout
                )
                response.raise_for_status()
                data = response.json()

                if data.get('error_id'):
                    print(f"Warning: Stack Exchange API error: {data.get('error_message')}")
                    continue

                for item in data.get('items', []):
                    q_id = item.get('question_id')
                    if q_id not in seen_ids:
                        seen_ids.add(q_id)
                        questions.append(self._format_question(item))

                # Be nice to the API
                time.sleep(0.1)

                if len(questions) >= limit:
                    break

            return questions[:limit]

        except requests.exceptions.RequestException as e:
            print(f"Warning: Stack Exchange API error: {e}")
            return []
        except Exception as e:
            print(f"Warning: Stack Exchange unexpected error: {e}")
            return []

    def search_pain_points(
        self,
        keywords: List[str],
        days: int = 7,
        limit: int = 10,
        site: str = 'stackoverflow'
    ) -> List[Dict[str, Any]]:
        """
        Search for potential pain points (questions with low answers or high views).

        Args:
            keywords: List of keywords to search for
            days: Only include questions from the last N days
            limit: Maximum number of questions to return
            site: Stack Exchange site to query

        Returns:
            List of question dictionaries representing pain points
        """
        try:
            # Calculate date range
            from_date = int((datetime.now() - timedelta(days=days)).timestamp())

            # Build search query
            intitle = ' OR '.join(keywords)

            params = {
                'order': 'desc',
                'sort': 'votes',
                'intitle': intitle,
                'site': site,
                'pagesize': min(limit, 100),
                'fromdate': from_date,
                'filter': 'withbody'
            }

            if self.api_key:
                params['key'] = self.api_key

            response = self.session.get(
                f"{self.API_BASE}/search",
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()

            if data.get('error_id'):
                print(f"Warning: Stack Exchange API error: {data.get('error_message')}")
                return []

            questions = []
            for item in data.get('items', []):
                # Filter for pain points: unanswered or low answer count
                answer_count = item.get('answer_count', 0)
                view_count = item.get('view_count', 0)

                # Consider it a pain point if:
                # - No answers, or
                # - Many views but few answers (indicates difficulty)
                if answer_count == 0 or (view_count > 100 and answer_count < 2):
                    questions.append(self._format_question(item))

            # Be nice to the API
            time.sleep(0.1)

            return questions

        except requests.exceptions.RequestException as e:
            print(f"Warning: Stack Exchange API error: {e}")
            return []
        except Exception as e:
            print(f"Warning: Stack Exchange unexpected error: {e}")
            return []

    def _format_question(self, item: Dict) -> Dict[str, Any]:
        """
        Format a Stack Exchange question item to standard format.

        Args:
            item: Raw question item from API

        Returns:
            Formatted question dictionary
        """
        # Truncate body for readability
        body = item.get('body', '')
        if body:
            # Remove HTML tags for plain text summary
            import re
            body_text = re.sub(r'<[^>]+>', '', body)
            body_truncated = body_text[:300] + '...' if len(body_text) > 300 else body_text
        else:
            body_truncated = ''

        # Convert timestamp to ISO format
        creation_date = item.get('creation_date', 0)
        created_iso = datetime.fromtimestamp(creation_date).isoformat() if creation_date else ''

        return {
            'id': item.get('question_id'),
            'title': item.get('title', ''),
            'body': body_truncated,
            'url': item.get('link', ''),
            'score': item.get('score', 0),
            'answer_count': item.get('answer_count', 0),
            'view_count': item.get('view_count', 0),
            'tags': item.get('tags', []),
            'created_date': created_iso,
            'is_answered': item.get('is_answered', False),
            'owner': item.get('owner', {}).get('display_name', 'Unknown')
        }

    @staticmethod
    def extract_topics(questions: List[Dict]) -> List[Dict[str, Any]]:
        """
        Extract trending topics/pain points from Stack Exchange questions.

        Args:
            questions: List of Stack Exchange questions

        Returns:
            List of trending topics with metadata
        """
        topics = []

        for question in questions:
            # Score based on engagement and unanswered status
            score = question['score']

            # Boost score for unanswered questions (potential pain points)
            if question['answer_count'] == 0:
                score += 50
            elif question['answer_count'] < 2:
                score += 25

            # Boost for high views (indicates widespread interest)
            if question.get('view_count', 0) > 1000:
                score += 30

            topic = {
                'name': question['title'],
                'score': score,
                'source': 'stackexchange',
                'url': question['url'],
                'tags': question['tags'],
                'engagement': {
                    'score': question['score'],
                    'views': question.get('view_count', 0),
                    'answers': question['answer_count'],
                    'is_answered': question['is_answered']
                },
                'created_at': question['created_date']
            }

            topics.append(topic)

        return topics


if __name__ == '__main__':
    # Test the fetcher
    print("Testing Stack Exchange fetcher...")

    try:
        fetcher = StackExchangeFetcher()

        print("\n1. Unanswered questions (python, javascript):")
        questions = fetcher.get_unanswered_questions(
            tags=['python', 'javascript'],
            days=7,
            limit=3
        )
        for i, q in enumerate(questions, 1):
            print(f"  {i}. {q['title'][:80]}...")
            print(f"     Score: {q['score']}, Answers: {q['answer_count']}, Views: {q['view_count']}")
            print(f"     Tags: {', '.join(q['tags'][:3])}")

        print("\n2. Search pain points:")
        pain_points = fetcher.search_pain_points(
            keywords=['error', 'bug', 'issue'],
            days=7,
            limit=3
        )
        for i, q in enumerate(pain_points, 1):
            print(f"  {i}. {q['title'][:80]}...")
            print(f"     Unanswered: {not q['is_answered']}, Views: {q['view_count']}")

        print("\n3. Extracted topics:")
        topics = StackExchangeFetcher.extract_topics(questions)
        for topic in topics[:3]:
            print(f"   - {topic['name'][:70]}...")
            print(f"     Score: {topic['score']}, Pain Point: {topic['engagement']['answers'] == 0}")

        print("\n✅ Stack Exchange fetcher test complete!")

    except Exception as e:
        print(f"\n⚠️  Error: {e}")
        print("Note: Stack Exchange API has quota limits. Some features may be limited without an API key.")