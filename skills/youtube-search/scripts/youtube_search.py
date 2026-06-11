#!/usr/bin/env python3
"""
YouTube Search Helper Script
Searches YouTube videos using the YouTube Data API v3 with API key authentication.
"""

import os
import sys
import json
import argparse
import requests
import re
from datetime import datetime
from typing import Optional, List, Dict, Any
from pathlib import Path
SHARED_DIR = Path(__file__).resolve().parents[3] / 'shared'
sys.path.insert(0, str(SHARED_DIR))
from credentials import load_credential


class YouTubeSearchError(Exception):
    """Custom exception for YouTube search errors"""
    pass



class YouTubeSearcher:
    """Handle YouTube API searches"""
    
    BASE_URL = "https://www.googleapis.com/youtube/v3/search"
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize YouTube searcher
        
        Args:
            api_key: YouTube API key. If None, reads from YOUTUBE_API_KEY 
                     environment variable or a shell startup file such as ~/.bashrc
        """
        # Try in order: 1) provided arg, 2) env var, 3) ~/.bashrc
        self.api_key = (
            api_key or 
            os.getenv("YOUTUBE_API_KEY") or 
            load_credential('YOUTUBE_API_KEY', required=False)
        )
        
        if not self.api_key:
            raise YouTubeSearchError(
                "YouTube API key not found. Set YOUTUBE_API_KEY in your environment or shell startup file: "
                "export YOUTUBE_API_KEY='your-key-here'"
            )
    
    def search(
        self,
        query: str,
        channel_id: Optional[str] = None,
        max_results: int = 10,
        order: str = "relevance",
        published_after: Optional[str] = None,
        published_before: Optional[str] = None,
        video_duration: str = "any"
    ) -> Dict[str, Any]:
        """
        Search YouTube videos
        
        Args:
            query: Search query string
            channel_id: Optional channel ID to search within
            max_results: Maximum number of results (1-50)
            order: Sort order (date, rating, relevance, viewCount)
            published_after: ISO 8601 date string (e.g., "2025-01-01T00:00:00Z")
            published_before: ISO 8601 date string
            video_duration: Video duration filter (any, short, medium, long)
                - short: < 4 minutes
                - medium: 4-20 minutes  
                - long: > 20 minutes
        
        Returns:
            Dictionary with search results
        """
        # Validate max_results
        if max_results < 1 or max_results > 50:
            raise YouTubeSearchError("max_results must be between 1 and 50")
        
        # Validate order
        valid_orders = ["date", "rating", "relevance", "viewCount", "title"]
        if order not in valid_orders:
            raise YouTubeSearchError(
                f"Invalid order '{order}'. Must be one of: {', '.join(valid_orders)}"
            )
        
        # Validate video_duration
        valid_durations = ["any", "short", "medium", "long"]
        if video_duration not in valid_durations:
            raise YouTubeSearchError(
                f"Invalid video_duration '{video_duration}'. "
                f"Must be one of: {', '.join(valid_durations)}"
            )
        
        # Build request parameters
        params = {
            "part": "snippet",
            "q": query,
            "type": "video",  # Only search for videos
            "maxResults": max_results,
            "order": order,
            "key": self.api_key
        }
        
        # Add optional parameters
        if channel_id:
            params["channelId"] = channel_id
        
        if published_after:
            params["publishedAfter"] = published_after
        
        if published_before:
            params["publishedBefore"] = published_before
        
        if video_duration != "any":
            params["videoDuration"] = video_duration
        
        try:
            # Make API request
            response = requests.get(self.BASE_URL, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            # Check for API errors
            if "error" in data:
                error_msg = data["error"].get("message", "Unknown error")
                raise YouTubeSearchError(f"YouTube API error: {error_msg}")
            
            # Format results
            return self._format_results(data, query, channel_id)
            
        except requests.exceptions.RequestException as e:
            raise YouTubeSearchError(f"Request failed: {str(e)}")
        except json.JSONDecodeError as e:
            raise YouTubeSearchError(f"Invalid JSON response: {str(e)}")
    
    def _format_results(
        self,
        data: Dict[str, Any],
        query: str,
        channel_id: Optional[str]
    ) -> Dict[str, Any]:
        """Format API response into clean result structure"""
        
        items = data.get("items", [])
        page_info = data.get("pageInfo", {})
        
        videos = []
        for item in items:
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId")
            
            if not video_id:
                continue
            
            video = {
                "title": snippet.get("title", ""),
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "channel_title": snippet.get("channelTitle", ""),
                "channel_id": snippet.get("channelId", ""),
                "published_at": snippet.get("publishedAt", ""),
                "description": snippet.get("description", ""),
                "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", "")
            }
            videos.append(video)
        
        result = {
            "success": True,
            "query": query,
            "total_results": page_info.get("totalResults", 0),
            "returned_results": len(videos),
            "videos": videos
        }
        
        if channel_id:
            result["channel_id"] = channel_id
        
        return result


def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(
        description="Search YouTube videos using YouTube Data API v3",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search videos in a specific channel
  %(prog)s --query "machine learning" --channel-id "UC_x5XG1OV2P6uZZ5FSM9Ttw"
  
  # General search with date filter
  %(prog)s --query "python tutorial" --published-after "2025-01-01T00:00:00Z" --max-results 20
  
  # Exclude YouTube Shorts (videos under 4 minutes)
  %(prog)s --query "documentary" --video-duration "medium" --order "viewCount"
  
  # Search by date, excluding short videos
  %(prog)s --query "tech news" --order "date" --video-duration "medium"
        """
    )
    
    parser.add_argument(
        "--query", "-q",
        required=True,
        help="Search query string"
    )
    
    parser.add_argument(
        "--channel-id", "-c",
        help="Channel ID to search within (e.g., 'UC_x5XG1OV2P6uZZ5FSM9Ttw')"
    )
    
    parser.add_argument(
        "--max-results", "-m",
        type=int,
        default=10,
        help="Maximum number of results (1-50, default: 10)"
    )
    
    parser.add_argument(
        "--order", "-o",
        choices=["date", "rating", "relevance", "viewCount", "title"],
        default="relevance",
        help="Sort order (default: relevance)"
    )
    
    parser.add_argument(
        "--published-after",
        help="Return videos published after this date (ISO 8601 format: 2025-01-01T00:00:00Z)"
    )
    
    parser.add_argument(
        "--published-before",
        help="Return videos published before this date (ISO 8601 format: 2025-12-31T23:59:59Z)"
    )
    
    parser.add_argument(
        "--video-duration", "-d",
        choices=["any", "short", "medium", "long"],
        default="any",
        help="Video duration: any, short (<4min), medium (4-20min), long (>20min). "
             "Use 'medium' or 'long' to exclude YouTube Shorts (default: any)"
    )
    
    parser.add_argument(
        "--api-key",
        help="YouTube API key (overrides YOUTUBE_API_KEY env var)"
    )
    
    args = parser.parse_args()
    
    try:
        searcher = YouTubeSearcher(api_key=args.api_key)
        
        results = searcher.search(
            query=args.query,
            channel_id=args.channel_id,
            max_results=args.max_results,
            order=args.order,
            published_after=args.published_after,
            published_before=args.published_before,
            video_duration=args.video_duration
        )
        
        # Output JSON
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return 0
        
    except YouTubeSearchError as e:
        error_result = {
            "success": False,
            "error": str(e)
        }
        print(json.dumps(error_result, indent=2), file=sys.stderr)
        return 1
    except Exception as e:
        error_result = {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }
        print(json.dumps(error_result, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())