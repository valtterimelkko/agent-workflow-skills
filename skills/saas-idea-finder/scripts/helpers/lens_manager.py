#!/usr/bin/env python3
"""Lens manager for rotating daily perspectives on trend discovery."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any


class LensManager:
    """Manages the rotating lens system for daily trend perspectives."""

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize the lens manager.

        Args:
            config_path: Path to lenses.json config file. If None, uses default location.
        """
        if config_path is None:
            # Default path relative to this script
            skill_root = Path(__file__).parent.parent.parent
            config_path = skill_root / "config" / "lenses.json"

        self.config_path = Path(config_path)
        self.lenses = self._load_lenses()

    def _load_lenses(self) -> List[Dict[str, Any]]:
        """Load lens configurations from JSON file."""
        if not self.config_path.exists():
            raise FileNotFoundError(f"Lens config not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            config = json.load(f)

        return config.get('lenses', [])

    def get_active_lens(self, override: Optional[str] = None) -> Dict[str, Any]:
        """
        Get the active lens for today or a specified override.

        Args:
            override: Optional lens name to use instead of day-of-week rotation

        Returns:
            Dictionary containing lens configuration

        Raises:
            ValueError: If override lens name not found
        """
        if override:
            # Find lens by name
            for lens in self.lenses:
                if lens['name'].lower() == override.lower():
                    return lens
            raise ValueError(f"Lens '{override}' not found. Available: {self.get_lens_names()}")

        # Use day-of-week rotation
        today = datetime.now().weekday()  # 0=Monday, 6=Sunday
        for lens in self.lenses:
            if lens['day_of_week'] == today:
                return lens

        # Fallback to first lens if no match (shouldn't happen)
        return self.lenses[0]

    def get_lens_names(self) -> List[str]:
        """Get list of all lens names."""
        return [lens['name'] for lens in self.lenses]

    def get_lens_filters_for_github(self, lens_name: str) -> Dict[str, List[str]]:
        """
        Get GitHub-specific filters for a lens.

        Args:
            lens_name: Name of the lens

        Returns:
            Dictionary with 'languages' and 'topics' lists
        """
        lens = self._get_lens_by_name(lens_name)
        return lens.get('github_filters', {'languages': [], 'topics': []})

    def get_hn_algolia_keywords(self, lens_name: str) -> List[str]:
        """
        Get HN Algolia search keywords for a lens.

        Args:
            lens_name: Name of the lens

        Returns:
            List of search keywords
        """
        lens = self._get_lens_by_name(lens_name)
        return lens.get('hn_algolia_keywords', [])

    def get_devto_tags(self, lens_name: str) -> List[str]:
        """
        Get DEV.to tags for a lens.

        Args:
            lens_name: Name of the lens

        Returns:
            List of DEV.to tags
        """
        lens = self._get_lens_by_name(lens_name)
        return lens.get('devto_tags', [])

    def get_newsapi_keywords(self, lens_name: str) -> List[str]:
        """
        Get NewsAPI search keywords for a lens.

        Args:
            lens_name: Name of the lens

        Returns:
            List of search keywords
        """
        lens = self._get_lens_by_name(lens_name)
        return lens.get('newsapi_keywords', [])

    def get_newsapi_category(self, lens_name: str) -> Optional[str]:
        """
        Get NewsAPI category for a lens.

        Args:
            lens_name: Name of the lens

        Returns:
            News category string or None
        """
        lens = self._get_lens_by_name(lens_name)
        return lens.get('newsapi_category')

    def get_producthunt_topics(self, lens_name: str) -> List[str]:
        """
        Get Product Hunt topic slugs for a lens.

        Args:
            lens_name: Name of the lens

        Returns:
            List of Product Hunt topic slugs
        """
        lens = self._get_lens_by_name(lens_name)
        return lens.get('producthunt_topics', [])

    def get_arxiv_categories(self, lens_name: str) -> List[str]:
        """
        Get arXiv categories for a lens.

        Args:
            lens_name: Name of the lens

        Returns:
            List of arXiv category codes
        """
        lens = self._get_lens_by_name(lens_name)
        return lens.get('arxiv_categories', [])

    def get_stackexchange_tags(self, lens_name: str) -> List[str]:
        """
        Get Stack Exchange tags for a lens.

        Args:
            lens_name: Name of the lens

        Returns:
            List of Stack Exchange tags
        """
        lens = self._get_lens_by_name(lens_name)
        return lens.get('stackexchange_tags', [])

    def get_gdelt_themes(self, lens_name: str) -> List[str]:
        """
        Get GDELT themes/keywords for a lens.

        Args:
            lens_name: Name of the lens

        Returns:
            List of GDELT themes
        """
        lens = self._get_lens_by_name(lens_name)
        return lens.get('gdelt_themes', [])

    def get_serpapi_keywords(self, lens_name: str) -> List[str]:
        """
        Get SerpAPI validation keywords for a lens.

        Args:
            lens_name: Name of the lens

        Returns:
            List of SerpAPI search keywords
        """
        lens = self._get_lens_by_name(lens_name)
        return lens.get('serpapi_keywords', [])

    def get_youtube_queries(self, lens_name: str) -> List[str]:
        """
        Get YouTube search queries for a lens.

        Args:
            lens_name: Name of the lens

        Returns:
            List of YouTube search queries
        """
        lens = self._get_lens_by_name(lens_name)
        return lens.get('youtube_queries', [])

    def get_research_focus(self, lens_name: str) -> List[str]:
        """
        Get research focus areas for a lens (used in Stage 2).

        Args:
            lens_name: Name of the lens

        Returns:
            List of research focus areas
        """
        lens = self._get_lens_by_name(lens_name)
        return lens.get('research_focus', [])

    def get_saas_focus(self, lens_name: str) -> str:
        """
        Get SaaS focus description for a lens (used in Stage 3).

        Args:
            lens_name: Name of the lens

        Returns:
            SaaS focus description string
        """
        lens = self._get_lens_by_name(lens_name)
        return lens.get('saas_focus', '')

    def _get_lens_by_name(self, lens_name: str) -> Dict[str, Any]:
        """Get lens configuration by name."""
        for lens in self.lenses:
            if lens['name'].lower() == lens_name.lower():
                return lens
        raise ValueError(f"Lens '{lens_name}' not found")

    def rotate_lens(self) -> Dict[str, Any]:
        """
        Manually rotate to the next lens (for testing/manual override).

        Returns:
            The next lens configuration
        """
        current = self.get_active_lens()
        current_day = current['day_of_week']
        next_day = (current_day + 1) % 7

        for lens in self.lenses:
            if lens['day_of_week'] == next_day:
                return lens

        return self.lenses[0]