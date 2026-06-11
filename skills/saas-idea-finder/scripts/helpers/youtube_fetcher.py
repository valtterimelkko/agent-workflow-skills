#!/usr/bin/env python3
"""YouTube Data API fetcher for trending tech content and video insights.

Includes native caption fetching for pain point extraction from video content.
"""

import sys
import time
import re
import requests
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple

# YouTube transcript API for native captions
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
    TRANSCRIPT_API_AVAILABLE = True
except ImportError:
    TRANSCRIPT_API_AVAILABLE = False


class YouTubeFetcher:
    """
    Fetches trending tech content and video data from YouTube Data API v3.
    
    Useful for identifying trending topics, popular tutorials, and tech
    content that indicates market interest.
    """

    API_BASE = "https://www.googleapis.com/youtube/v3"

    # Popular tech topic IDs (YouTube topic IDs)
    TOPICS = {
        'tech': '/m/07c1v',  # Technology
        'science': '/m/01k8wb',  # Science
        'business': '/m/09s1f',  # Business
        'education': '/m/01h6rj',  # Education
    }

    # Region codes
    REGIONS = ['US', 'GB', 'CA', 'AU', 'DE', 'FR', 'JP', 'IN', 'BR']

    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the YouTube fetcher.

        Args:
            api_key: YouTube Data API key. If None, loads from credential system.
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
                    'YOUTUBE_API_KEY',
                    required=False
                )
            except Exception as e:
                raise ValueError(f"YOUTUBE_API_KEY not found: {e}")

        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'saas-idea-finder/1.0'
        })

    def search_tech_videos(
        self,
        query: str,
        max_results: int = 10,
        order: str = 'relevance'
    ) -> List[Dict[str, Any]]:
        """
        Search for tech-related videos on YouTube.

        Args:
            query: Search query (e.g., "Python tutorial", "AI startup")
            max_results: Maximum number of results to return
            order: Sort order ('relevance', 'date', 'rating', 'viewCount')

        Returns:
            List of video dictionaries with metadata
        """
        try:
            params = {
                'part': 'snippet',
                'q': query,
                'type': 'video',
                'maxResults': min(max_results, 50),  # API max is 50
                'order': order,
                'key': self.api_key
            }

            response = self.session.get(
                f"{self.API_BASE}/search",
                params=params,
                timeout=30
            )

            if response.status_code == 403:
                error_data = response.json()
                error_reason = error_data.get('error', {}).get('errors', [{}])[0].get('reason', '')
                if error_reason == 'quotaExceeded':
                    print("Warning: YouTube API quota exceeded")
                else:
                    print(f"Warning: YouTube API access denied: {error_reason}")
                return []

            if response.status_code == 400:
                print("Warning: YouTube API bad request - check query parameters")
                return []

            response.raise_for_status()
            data = response.json()

            videos = []
            video_ids = [item['id']['videoId'] for item in data.get('items', [])]

            # Fetch detailed statistics for each video
            if video_ids:
                stats = self._get_video_statistics(video_ids)

                for item in data.get('items', []):
                    video_id = item['id']['videoId']
                    video_data = self._format_video(item, stats.get(video_id, {}))
                    videos.append(video_data)

            # Be nice to the API
            time.sleep(0.1)

            return videos

        except requests.exceptions.RequestException as e:
            print(f"Warning: YouTube API error: {e}")
            return []
        except Exception as e:
            print(f"Warning: YouTube unexpected error: {e}")
            return []

    def get_popular_videos_by_topic(
        self,
        topic: str,
        region: str = "US",
        max_results: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get popular videos by topic/category in a specific region.

        Args:
            topic: Topic keyword or category
            region: Region code (e.g., 'US', 'GB', 'CA')
            max_results: Maximum number of results to return

        Returns:
            List of popular video dictionaries
        """
        try:
            # Search for videos with the topic
            params = {
                'part': 'snippet,statistics',
                'chart': 'mostPopular',
                'regionCode': region,
                'videoCategoryId': '28',  # Science & Technology
                'maxResults': min(max_results, 50),
                'key': self.api_key
            }

            # Add topic filter if it's a known topic ID
            if topic in self.TOPICS:
                params['topicId'] = self.TOPICS[topic]
            else:
                # Use search instead for custom topics
                return self.search_tech_videos(
                    query=topic,
                    max_results=max_results,
                    order='viewCount'
                )

            response = self.session.get(
                f"{self.API_BASE}/videos",
                params=params,
                timeout=30
            )

            if response.status_code == 403:
                print("Warning: YouTube API quota exceeded or access denied")
                return []

            response.raise_for_status()
            data = response.json()

            videos = []
            for item in data.get('items', []):
                video_data = self._format_video(
                    item,
                    item.get('statistics', {}),
                    is_full_item=True
                )
                videos.append(video_data)

            # Be nice to the API
            time.sleep(0.1)

            return videos

        except requests.exceptions.RequestException as e:
            print(f"Warning: YouTube API error: {e}")
            return []
        except Exception as e:
            print(f"Warning: YouTube unexpected error: {e}")
            return []

    def _get_video_statistics(
        self,
        video_ids: List[str]
    ) -> Dict[str, Dict]:
        """
        Fetch statistics for a list of video IDs.

        Args:
            video_ids: List of YouTube video IDs

        Returns:
            Dictionary mapping video ID to statistics
        """
        try:
            # API allows up to 50 IDs per request
            id_string = ','.join(video_ids[:50])

            params = {
                'part': 'statistics,contentDetails',
                'id': id_string,
                'key': self.api_key
            }

            response = self.session.get(
                f"{self.API_BASE}/videos",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            data = response.json()

            stats = {}
            for item in data.get('items', []):
                video_id = item['id']
                stats[video_id] = item.get('statistics', {})

            return stats

        except Exception:
            return {}

    def _format_video(
        self,
        item: Dict,
        stats: Dict,
        is_full_item: bool = False
    ) -> Dict[str, Any]:
        """
        Format a YouTube video item to standard format.

        Args:
            item: Video item from API
            stats: Video statistics
            is_full_item: Whether this is from /videos endpoint (not /search)

        Returns:
            Formatted video dictionary
        """
        if is_full_item:
            snippet = item.get('snippet', {})
            video_id = item.get('id', '')
        else:
            snippet = item.get('snippet', {})
            video_id = item.get('id', {}).get('videoId', '')

        # Parse statistics
        view_count = int(stats.get('viewCount', 0)) if stats.get('viewCount') else 0
        like_count = int(stats.get('likeCount', 0)) if stats.get('likeCount') else 0
        comment_count = int(stats.get('commentCount', 0)) if stats.get('commentCount') else 0

        # Parse publish date
        published_at = snippet.get('publishedAt', '')

        return {
            'id': video_id,
            'title': snippet.get('title', ''),
            'description': snippet.get('description', '')[:300],
            'url': f"https://www.youtube.com/watch?v={video_id}",
            'thumbnail': snippet.get('thumbnails', {}).get('high', {}).get('url', ''),
            'view_count': view_count,
            'like_count': like_count,
            'comment_count': comment_count,
            'published_at': published_at,
            'channel_id': snippet.get('channelId', ''),
            'channel_title': snippet.get('channelTitle', ''),
            'tags': snippet.get('tags', []),
            'category_id': snippet.get('categoryId', ''),
            'live_broadcast': snippet.get('liveBroadcastContent', 'none')
        }

    def get_trending_searches(
        self,
        query: str,
        region: str = "US"
    ) -> List[Dict[str, Any]]:
        """
        Get search suggestions (auto-complete) for a query.
        This can indicate trending searches.

        Args:
            query: Base search query
            region: Region code

        Returns:
            List of search suggestions
        """
        # Note: YouTube Data API doesn't have a direct trending searches endpoint
        # We use search with different related queries to simulate this
        try:
            suggestions = []

            # Get related videos and extract tags/titles as "suggestions"
            related = self.search_tech_videos(
                query=query,
                max_results=10,
                order='date'
            )

            seen_terms = set()
            for video in related:
                # Extract meaningful terms from title
                title = video.get('title', '').lower()
                words = title.split()

                for word in words:
                    word = word.strip('.,!?;:')
                    if len(word) > 3 and word not in seen_terms:
                        seen_terms.add(word)
                        suggestions.append({
                            'term': word,
                            'source_video': video.get('title', '')[:60],
                            'url': video.get('url', '')
                        })

            return suggestions[:10]

        except Exception:
            return []

    @staticmethod
    def extract_topics(videos: List[Dict]) -> List[Dict[str, Any]]:
        """
        Extract trending topics from YouTube videos.
        
        Enhanced to include pain points from captions when available.

        Args:
            videos: List of YouTube videos (optionally enriched with captions)

        Returns:
            List of trending topics with metadata and pain points
        """
        topics = []

        for video in videos:
            # Calculate engagement score
            views = video.get('view_count', 0)
            likes = video.get('like_count', 0)
            comments = video.get('comment_count', 0)

            # Engagement rate approximation
            engagement_rate = (likes + comments * 2) / max(views, 1) * 1000

            # Base score on views with engagement boost
            score = min(views / 1000, 100)  # Cap at 100 for views
            score += engagement_rate * 10  # Add engagement bonus
            
            # Boost score if video has pain points from captions
            pain_points = video.get('pain_points', [])
            if pain_points:
                # Boost by up to 50% based on pain severity
                max_severity = max([p['severity_score'] for p in pain_points])
                score *= (1 + (max_severity / 200))  # 1.0 to 1.5x boost
            
            topic = {
                'name': video['title'],
                'score': int(score),
                'source': 'youtube',
                'url': video['url'],
                'description': video.get('description', '')[:150] + '...',
                'channel': video.get('channel_title', ''),
                'published_at': video.get('published_at', ''),
                'engagement': {
                    'views': views,
                    'likes': likes,
                    'comments': comments,
                    'engagement_rate': round(engagement_rate, 2)
                },
                'tags': video.get('tags', [])[:5],
                'pain_points': pain_points[:3],  # Include top 3 pain points
                'has_captions': 'captions' in video
            }

            topics.append(topic)

        return topics

    def _get_proxy_config(self):
        """Load proxy configuration from Reddit credentials for YouTube transcript API."""
        try:
            from helpers.reddit_credentials import load_reddit_proxy_url
            proxy_url = load_reddit_proxy_url(required=False)
            
            if proxy_url and TRANSCRIPT_API_AVAILABLE:
                from youtube_transcript_api.proxies import GenericProxyConfig
                return GenericProxyConfig(proxy_url)
        except Exception:
            pass
        return None

    def fetch_captions(self, video_id: str, video_title: str = "") -> Tuple[Optional[str], Optional[Dict]]:
        """
        Fetch native captions/transcript for a YouTube video.
        
        Uses youtube-transcript-api to get auto-generated or manual captions.
        Falls back gracefully if captions are disabled or unavailable.
        Uses proxy from Reddit credentials if available (to work around IP blocks).
        
        Args:
            video_id: YouTube video ID (e.g., 'dQw4w9WgXcQ')
            video_title: Optional title for logging
            
        Returns:
            Tuple of (transcript_text, metadata_dict) or (None, None) if unavailable
            
        Timing: ~1-3 seconds per video (API call + processing)
        """
        if not TRANSCRIPT_API_AVAILABLE:
            return None, None
        
        try:
            # Initialize API with proxy if available
            proxy_config = self._get_proxy_config()
            if proxy_config:
                api = YouTubeTranscriptApi(proxy_config=proxy_config)
            else:
                api = YouTubeTranscriptApi()
            
            # Fetch transcript (auto-generated or manual)
            transcript = api.fetch(video_id)
            
            if not transcript:
                return None, None
            
            # Convert to list and combine all text segments
            transcript_list = list(transcript)
            full_text = " ".join([segment.text for segment in transcript_list])
            
            # Calculate basic stats
            word_count = len(full_text.split())
            duration = transcript_list[-1].start if transcript_list else 0
            
            metadata = {
                'word_count': word_count,
                'duration_seconds': int(duration),
                'segments': len(transcript_list),
                'source': 'youtube_captions'
            }
            
            return full_text, metadata
            
        except TranscriptsDisabled:
            print(f"    Captions disabled for: {video_title[:50]}...")
            return None, None
        except NoTranscriptFound:
            print(f"    No transcript found for: {video_title[:50]}...")
            return None, None
        except VideoUnavailable:
            print(f"    Video unavailable: {video_title[:50]}...")
            return None, None
        except Exception as e:
            # Silently fail for other errors (don't break pipeline)
            return None, None

    def extract_pain_points_from_captions(self, caption_text: str) -> List[Dict[str, Any]]:
        """
        Extract pain points and user frustrations from caption text.
        
        Looks for specific patterns indicating problems, wishes, or complaints.
        
        Args:
            caption_text: Full transcript text
            
        Returns:
            List of pain point dicts with quote, pattern type, and context
        """
        if not caption_text or len(caption_text) < 50:
            return []
        
        pain_points = []
        text_lower = caption_text.lower()
        
        # Pain point patterns with capturing groups
        patterns = [
            # Explicit complaints
            (r"(?:i |we )?(?:wish|wish there was|wish there were) ([^\.]{10,100})", "wish_statement"),
            (r"(?:i |we )?(?:hate|really hate|hate how) ([^\.]{10,100})", "hate_statement"),
            (r"(?:i |we )?(?:can't stand|can't stand how) ([^\.]{10,100})", "frustration"),
            (r"(?:i |we )?(?:wish someone would|wish someone could) ([^\.]{10,100})", "wish_for_solution"),
            (r"(?:i |we )?(?:wish there was a tool|wish there was an app) ([^\.]{10,100})", "tool_wish"),
            (r"(?:i |we )?(?:wish there was a way|wish there was a better way) ([^\.]{10,100})", "method_wish"),
            
            # Problem statements
            (r"(?:the )?(?:problem|issue|biggest issue|main problem) (?:is|with) ([^\.]{10,150})", "problem_statement"),
            (r"(?:i |we )?(?:always|constantly|keep) (?:struggle with|struggling with) ([^\.]{10,150})", "struggle"),
            (r"(?:i |we )?(?:spent|waste|wasted) (?:so much |hours |days )?time ([^\.]{10,150})", "time_waste"),
            (r"(?:i |we )?(?:wish|need|want) (?:a |an )?(?:better |easier |simpler )?way to ([^\.]{10,150})", "better_way"),
            (r"(?:this|it) (?:is|would be) (?:so much |way |a lot )?better if ([^\.]{10,150})", "improvement_suggestion"),
            (r"(?:i |we )?(?:can't|cannot|unable to) (?:figure out|get|make) ([^\.]{10,150})", "cant_figure"),
            
            # Missing features
            (r"(?:i |we )?(?:wish|need|want) (?:it|this|they) (?:had|supported|allowed) ([^\.]{10,150})", "missing_feature"),
            (r"(?:it|this|there) (?:needs|should have|is missing) ([^\.]{10,150})", "missing_feature"),
            (r"(?:the )?(?:only|main) (?:thing|feature|problem) (?:i |we )?(?:wish|need|want) (?:is |was )?([^\.]{10,150})", "main_wish"),
            
            # Workarounds indicate pain
            (r"(?:i |we )?(?:have to|had to|end up|usually) (?:manually|by hand|one by one) ([^\.]{10,150})", "manual_work"),
            (r"(?:i |we )?(?:have|need) (?:a |an )?workaround ([^\.]{10,150})", "workaround"),
            (r"(?:i |we )?(?:use|using) ([^\.]{5,50}) (?:as a |for )?workaround", "workaround_tool"),
        ]
        
        for pattern, pattern_type in patterns:
            matches = re.finditer(pattern, text_lower, re.IGNORECASE)
            for match in matches:
                # Get the captured group and surrounding context
                captured = match.group(1).strip()
                if len(captured) < 10:  # Skip very short matches
                    continue
                
                # Find position in original text for context
                start_pos = max(0, match.start() - 50)
                end_pos = min(len(caption_text), match.end() + 50)
                context = caption_text[start_pos:end_pos].strip()
                
                # Clean up the captured text
                captured = re.sub(r'\s+', ' ', captured)
                context = re.sub(r'\s+', ' ', context)
                
                pain_points.append({
                    'quote': captured[:200],  # Limit length
                    'pattern_type': pattern_type,
                    'context': context[:300],
                    'severity_score': self._calculate_pain_severity(pattern_type, captured)
                })
        
        # Sort by severity and remove duplicates (similar quotes)
        pain_points.sort(key=lambda x: x['severity_score'], reverse=True)
        
        # Deduplicate similar pain points
        unique_pains = []
        seen_quotes = set()
        for pain in pain_points:
            # Create a simplified key for deduplication
            key = pain['quote'][:30].lower()
            if key not in seen_quotes:
                seen_quotes.add(key)
                unique_pains.append(pain)
        
        return unique_pains[:5]  # Return top 5 pain points

    def _calculate_pain_severity(self, pattern_type: str, quote: str) -> int:
        """Calculate a severity score for a pain point based on type and content."""
        base_scores = {
            'hate_statement': 90,
            'frustration': 85,
            'time_waste': 80,
            'manual_work': 75,
            'problem_statement': 70,
            'struggle': 70,
            'cant_figure': 65,
            'workaround': 65,
            'wish_for_solution': 60,
            'tool_wish': 60,
            'missing_feature': 55,
            'wish_statement': 50,
            'better_way': 50,
            'method_wish': 45,
            'main_wish': 45,
            'improvement_suggestion': 40,
            'workaround_tool': 40,
        }
        
        score = base_scores.get(pattern_type, 50)
        
        # Boost score for specific keywords indicating urgency
        urgency_words = ['always', 'constantly', 'every day', 'every time', 'waste', 'hours', 'terrible', 'awful']
        for word in urgency_words:
            if word in quote.lower():
                score += 5
                break
        
        return min(score, 100)

    def enrich_videos_with_captions(self, videos: List[Dict], max_videos: int = 5) -> List[Dict]:
        """
        Enrich video data with captions and extracted pain points.
        
        Only processes top N videos by view count to manage API calls and time.
        
        Args:
            videos: List of video dictionaries
            max_videos: Maximum number of videos to fetch captions for (default 5)
            
        Returns:
            List of videos with added 'captions' and 'pain_points' fields
            
        Timing: ~1-3s per video with captions, ~0.5s per video without
        Expected total: ~5-15s for 5 videos
        """
        if not TRANSCRIPT_API_AVAILABLE:
            return videos
        
        # Sort by views and take top N
        sorted_videos = sorted(videos, key=lambda v: v.get('view_count', 0), reverse=True)
        videos_to_process = sorted_videos[:max_videos]
        
        print(f"  Fetching captions for top {len(videos_to_process)} videos...")
        
        enriched_count = 0
        pain_points_found = 0
        
        for video in videos_to_process:
            video_id = video.get('id')
            if not video_id:
                continue
            
            # Fetch captions
            caption_text, metadata = self.fetch_captions(video_id, video.get('title', ''))
            
            if caption_text:
                video['captions'] = {
                    'text': caption_text[:2000],  # Store first 2000 chars
                    'metadata': metadata
                }
                
                # Extract pain points
                pain_points = self.extract_pain_points_from_captions(caption_text)
                if pain_points:
                    video['pain_points'] = pain_points
                    pain_points_found += len(pain_points)
                    
                    # Boost video score if it has high-severity pain points
                    max_severity = max([p['severity_score'] for p in pain_points])
                    video['pain_score'] = max_severity / 100.0
                
                enriched_count += 1
        
        print(f"    ✓ Captions fetched: {enriched_count}/{len(videos_to_process)}")
        if pain_points_found > 0:
            print(f"    ✓ Pain points extracted: {pain_points_found}")
        
        return videos


if __name__ == '__main__':
    # Test the fetcher
    print("Testing YouTube fetcher...")

    try:
        fetcher = YouTubeFetcher()

        print("\n1. Search tech videos (AI tutorial):")
        videos = fetcher.search_tech_videos(
            query="AI tutorial for beginners",
            max_results=3,
            order='relevance'
        )
        for i, video in enumerate(videos, 1):
            print(f"  {i}. {video['title'][:80]}...")
            print(f"     Channel: {video['channel_title']}")
            print(f"     Views: {video['view_count']:,}, Likes: {video['like_count']:,}")

        print("\n2. Popular tech videos (US):")
        popular = fetcher.get_popular_videos_by_topic(
            topic='technology',
            region='US',
            max_results=3
        )
        for i, video in enumerate(popular, 1):
            print(f"  {i}. {video['title'][:80]}...")
            print(f"     Views: {video['view_count']:,}")

        print("\n3. Enriching videos with captions (top 3)...")
        enriched_videos = fetcher.enrich_videos_with_captions(videos, max_videos=3)
        
        print("\n4. Extracted topics with caption analysis:")
        topics = YouTubeFetcher.extract_topics(enriched_videos)
        for topic in topics[:3]:
            print(f"   - {topic['name'][:70]}...")
            print(f"     Score: {topic['score']}")
            print(f"     Engagement: {topic['engagement']['views']:,} views")
            if topic.get('has_captions'):
                print(f"     Captions: ✓")
            if topic.get('pain_points'):
                print(f"     Pain points found: {len(topic['pain_points'])}")
                for pain in topic['pain_points'][:2]:
                    print(f"       • [{pain['pattern_type']}] {pain['quote'][:60]}...")

        print("\n✅ YouTube fetcher test complete!")

    except ValueError as e:
        print(f"\n❌ Error: {e}")
        print("Make sure YOUTUBE_API_KEY is set in your environment or a shell startup file such as ~/.bashrc")