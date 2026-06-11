#!/usr/bin/env python3
"""State manager for tracking analyzed topics and preventing duplicates."""

import json
import re
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any


class StateManager:
    """Manages state tracking for deduplication and topic history."""

    def __init__(self, state_dir: Optional[str] = None):
        """
        Initialize the state manager.

        Args:
            state_dir: Directory for state files. Defaults to ~/.saas-idea-finder/
        """
        if state_dir is None:
            state_dir = Path.home() / ".saas-idea-finder"
        else:
            state_dir = Path(state_dir).expanduser()

        self.state_dir = state_dir
        self.state_dir.mkdir(parents=True, exist_ok=True)

        self.analyzed_topics_file = self.state_dir / "analyzed_topics.json"
        self.lens_rotation_file = self.state_dir / "lens_rotation.json"

        # Create output directories
        self.outputs_dir = self.state_dir / "outputs"
        self.outputs_dir.mkdir(exist_ok=True)

    def _normalize_topic_name(self, topic_name: str) -> str:
        """
        Normalize topic name for consistent comparison.

        Args:
            topic_name: Raw topic name

        Returns:
            Normalized topic name (lowercase, alphanumeric + spaces)
        """
        # Convert to lowercase
        normalized = topic_name.lower()
        # Keep only alphanumeric and spaces
        normalized = re.sub(r'[^a-z0-9\s]', '', normalized)
        # Collapse multiple spaces
        normalized = re.sub(r'\s+', ' ', normalized)
        return normalized.strip()

    def is_topic_analyzed(self, topic_name: str, within_days: int = 30) -> bool:
        """
        Check if a topic has been analyzed recently.

        Args:
            topic_name: Topic name to check
            within_days: Consider topics analyzed within this many days

        Returns:
            True if topic was analyzed within the specified timeframe
        """
        normalized = self._normalize_topic_name(topic_name)
        analyzed_topics = self._load_analyzed_topics()

        cutoff_date = datetime.now() - timedelta(days=within_days)

        for topic in analyzed_topics.get('topics', []):
            if topic['normalized_name'] == normalized:
                last_analyzed = datetime.fromisoformat(topic['last_analyzed'])
                if last_analyzed > cutoff_date:
                    return True

        return False

    def mark_topic_analyzed(self, topic_name: str, metadata: Dict[str, Any]) -> None:
        """
        Mark a topic as analyzed with metadata.

        Args:
            topic_name: Topic name
            metadata: Additional metadata (lens, output_files, etc.)
        """
        normalized = self._normalize_topic_name(topic_name)
        analyzed_topics = self._load_analyzed_topics()

        now = datetime.now().isoformat()

        # Check if topic already exists
        existing_topic = None
        for topic in analyzed_topics.get('topics', []):
            if topic['normalized_name'] == normalized:
                existing_topic = topic
                break

        if existing_topic:
            # Update existing
            existing_topic['last_analyzed'] = now
            existing_topic['analyze_count'] += 1
            if metadata.get('lens'):
                if metadata['lens'] not in existing_topic.get('lenses_used', []):
                    existing_topic.setdefault('lenses_used', []).append(metadata['lens'])
            if metadata.get('output_files'):
                existing_topic['output_files'] = metadata['output_files']
        else:
            # Create new entry
            new_topic = {
                'name': topic_name,
                'normalized_name': normalized,
                'first_analyzed': now,
                'last_analyzed': now,
                'analyze_count': 1,
                'lenses_used': [metadata.get('lens')] if metadata.get('lens') else [],
                'output_files': metadata.get('output_files', {})
            }
            analyzed_topics.setdefault('topics', []).append(new_topic)

        self._save_analyzed_topics(analyzed_topics)

    def get_analyzed_topics(self, since_days: int = 30) -> List[Dict[str, Any]]:
        """
        Get list of topics analyzed within the specified timeframe.

        Args:
            since_days: Look back this many days

        Returns:
            List of topic dictionaries
        """
        analyzed_topics = self._load_analyzed_topics()
        cutoff_date = datetime.now() - timedelta(days=since_days)

        recent_topics = []
        for topic in analyzed_topics.get('topics', []):
            last_analyzed = datetime.fromisoformat(topic['last_analyzed'])
            if last_analyzed > cutoff_date:
                recent_topics.append(topic)

        return recent_topics

    def clear_old_topics(self, older_than_days: int = 90) -> int:
        """
        Remove topics older than specified days.

        Args:
            older_than_days: Remove topics analyzed more than this many days ago

        Returns:
            Number of topics removed
        """
        analyzed_topics = self._load_analyzed_topics()
        cutoff_date = datetime.now() - timedelta(days=older_than_days)

        original_count = len(analyzed_topics.get('topics', []))

        # Filter to keep only recent topics
        recent_topics = []
        for topic in analyzed_topics.get('topics', []):
            last_analyzed = datetime.fromisoformat(topic['last_analyzed'])
            if last_analyzed > cutoff_date:
                recent_topics.append(topic)

        analyzed_topics['topics'] = recent_topics
        self._save_analyzed_topics(analyzed_topics)

        return original_count - len(recent_topics)

    def get_output_dir_for_date(self, date: Optional[datetime] = None, stage: str = '') -> Path:
        """
        Get output directory for a specific date and stage.

        Args:
            date: Date for outputs (defaults to today)
            stage: Stage name ('discover', 'research', 'ideas', or empty for date folder)

        Returns:
            Path to output directory
        """
        if date is None:
            date = datetime.now()

        date_str = date.strftime('%Y-%m-%d')
        if stage:
            output_dir = self.outputs_dir / f"{date_str}_{stage}"
        else:
            output_dir = self.outputs_dir / date_str

        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _load_analyzed_topics(self) -> Dict[str, Any]:
        """Load analyzed topics from JSON file."""
        if not self.analyzed_topics_file.exists():
            return {'topics': []}

        try:
            with open(self.analyzed_topics_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {'topics': []}

    def _save_analyzed_topics(self, data: Dict[str, Any]) -> None:
        """Save analyzed topics to JSON file."""
        with open(self.analyzed_topics_file, 'w') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)