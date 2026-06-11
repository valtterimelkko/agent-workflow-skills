#!/usr/bin/env python3
"""arXiv API fetcher for research papers and trending topics."""

import requests
import time
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any
from urllib.parse import quote


class ArxivFetcher:
    """Fetches research papers from arXiv API."""

    API_BASE = "http://export.arxiv.org/api/query"

    # Common arXiv categories
    CATEGORIES = {
        'cs': 'Computer Science',
        'cs.AI': 'Artificial Intelligence',
        'cs.CL': 'Computation and Language',
        'cs.CV': 'Computer Vision',
        'cs.LG': 'Machine Learning',
        'cs.SE': 'Software Engineering',
        'cs.DB': 'Databases',
        'cs.DC': 'Distributed Computing',
        'cs.CR': 'Cryptography and Security',
        'cs.HC': 'Human-Computer Interaction',
        'cs.IR': 'Information Retrieval',
        'cs.NE': 'Neural and Evolutionary Computing',
        'econ': 'Economics',
        'eess': 'Electrical Engineering and Systems Science',
        'math': 'Mathematics',
        'physics': 'Physics',
        'q-bio': 'Quantitative Biology',
        'q-fin': 'Quantitative Finance',
        'stat': 'Statistics'
    }

    def __init__(self, timeout: int = 30):
        """
        Initialize the arXiv fetcher.

        Args:
            timeout: Request timeout in seconds
        """
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'saas-idea-finder/1.0'
        })

    def search_by_keywords(
        self,
        keywords: List[str],
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search arXiv papers by keywords.

        Args:
            keywords: List of keywords to search for
            max_results: Maximum number of results to return

        Returns:
            List of paper dictionaries with metadata
        """
        try:
            # Build search query
            query = " OR ".join([f'all:{quote(kw)}' for kw in keywords])

            params = {
                'search_query': query,
                'start': 0,
                'max_results': min(max_results, 100),
                'sortBy': 'submittedDate',
                'sortOrder': 'descending'
            }

            response = self.session.get(
                self.API_BASE,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

            return self._parse_atom_feed(response.text)

        except requests.exceptions.RequestException as e:
            print(f"Warning: arXiv API error: {e}")
            return []
        except Exception as e:
            print(f"Warning: arXiv parsing error: {e}")
            return []

    def get_recent_by_category(
        self,
        category: str,
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Fetch recent papers from a specific arXiv category.

        Args:
            category: arXiv category code (e.g., 'cs.AI', 'cs.LG')
            max_results: Maximum number of results to return

        Returns:
            List of paper dictionaries with metadata
        """
        try:
            params = {
                'search_query': f'cat:{category}',
                'start': 0,
                'max_results': min(max_results, 100),
                'sortBy': 'submittedDate',
                'sortOrder': 'descending'
            }

            response = self.session.get(
                self.API_BASE,
                params=params,
                timeout=self.timeout
            )
            response.raise_for_status()

            return self._parse_atom_feed(response.text)

        except requests.exceptions.RequestException as e:
            print(f"Warning: arXiv API error: {e}")
            return []
        except Exception as e:
            print(f"Warning: arXiv parsing error: {e}")
            return []

    def _parse_atom_feed(self, xml_content: str) -> List[Dict[str, Any]]:
        """
        Parse arXiv Atom feed XML response.

        Args:
            xml_content: Raw XML content from API

        Returns:
            List of parsed paper dictionaries
        """
        papers = []

        try:
            # Register namespaces
            namespaces = {
                'atom': 'http://www.w3.org/2005/Atom',
                'arxiv': 'http://arxiv.org/schemas/atom'
            }

            root = ET.fromstring(xml_content)

            for entry in root.findall('atom:entry', namespaces):
                paper = {}

                # Basic fields
                paper['id'] = self._get_text(entry, 'atom:id', namespaces)
                paper['title'] = self._clean_text(
                    self._get_text(entry, 'atom:title', namespaces)
                )
                paper['summary'] = self._clean_text(
                    self._get_text(entry, 'atom:summary', namespaces)
                )
                paper['published'] = self._get_text(
                    entry, 'atom:published', namespaces
                )
                paper['updated'] = self._get_text(
                    entry, 'atom:updated', namespaces
                )

                # Extract arXiv ID and create URL
                arxiv_id = paper['id'].split('/abs/')[-1] if paper['id'] else ''
                paper['arxiv_id'] = arxiv_id
                paper['url'] = f"https://arxiv.org/abs/{arxiv_id}"
                paper['pdf_url'] = f"https://arxiv.org/pdf/{arxiv_id}.pdf"

                # Authors
                authors = []
                for author in entry.findall('atom:author', namespaces):
                    name = self._get_text(author, 'atom:name', namespaces)
                    if name:
                        authors.append(name)
                paper['authors'] = authors

                # Categories
                categories = []
                for category in entry.findall('atom:category', namespaces):
                    term = category.get('term', '')
                    if term:
                        categories.append(term)
                paper['categories'] = categories
                paper['primary_category'] = categories[0] if categories else ''

                # arXiv specific fields
                paper['comment'] = self._get_text(
                    entry, 'arxiv:comment', namespaces
                )
                paper['journal_ref'] = self._get_text(
                    entry, 'arxiv:journal_ref', namespaces
                )

                papers.append(paper)

            # Be nice to the API
            time.sleep(0.1)

        except ET.ParseError as e:
            print(f"Warning: XML parsing error: {e}")

        return papers

    def _get_text(
        self,
        element: ET.Element,
        path: str,
        namespaces: Dict[str, str]
    ) -> str:
        """Safely extract text from XML element."""
        elem = element.find(path, namespaces)
        return elem.text.strip() if elem is not None and elem.text else ''

    def _clean_text(self, text: str) -> str:
        """Clean up whitespace in text."""
        return ' '.join(text.split())

    @staticmethod
    def extract_topics(papers: List[Dict]) -> List[Dict[str, Any]]:
        """
        Extract trending topics from arXiv papers.

        Args:
            papers: List of arXiv papers

        Returns:
            List of trending topics with metadata
        """
        topics = []

        for paper in papers:
            # Score based on recency and category
            score = 50  # Base score

            # Boost score for AI/ML related papers
            ai_categories = ['cs.AI', 'cs.LG', 'cs.CL', 'cs.CV', 'cs.NE']
            if any(cat in paper.get('categories', []) for cat in ai_categories):
                score += 30

            topic = {
                'name': paper['title'],
                'score': score,
                'source': 'arxiv',
                'url': paper['url'],
                'description': paper.get('summary', '')[:200] + '...',
                'published_at': paper.get('published', ''),
                'categories': paper.get('categories', []),
                'authors': paper.get('authors', [])[:3]  # Top 3 authors
            }

            topics.append(topic)

        return topics


if __name__ == '__main__':
    # Test the fetcher
    print("Testing arXiv fetcher...")

    fetcher = ArxivFetcher()

    print("\n1. Search by keywords (AI/ML):")
    papers = fetcher.search_by_keywords(
        keywords=['artificial intelligence', 'machine learning'],
        max_results=3
    )
    for i, paper in enumerate(papers, 1):
        print(f"  {i}. {paper['title'][:80]}...")
        print(f"     Authors: {', '.join(paper['authors'][:2])}")
        print(f"     Categories: {', '.join(paper['categories'][:2])}")

    print("\n2. Recent papers in cs.AI:")
    ai_papers = fetcher.get_recent_by_category(
        category='cs.AI',
        max_results=3
    )
    for i, paper in enumerate(ai_papers, 1):
        print(f"  {i}. {paper['title'][:80]}...")
        print(f"     Published: {paper['published'][:10]}")

    print("\n3. Extracted topics:")
    topics = ArxivFetcher.extract_topics(papers)
    for topic in topics[:3]:
        print(f"   - {topic['name'][:70]}...")
        print(f"     Score: {topic['score']}")

    print("\n✅ arXiv fetcher test complete!")