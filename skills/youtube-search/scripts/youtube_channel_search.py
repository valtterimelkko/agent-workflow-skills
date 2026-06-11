#!/usr/bin/env python3
"""
YouTube Channel Search Helper

Searches for videos within a specific YouTube channel, accepting @handles or URLs.
This combines the channel ID resolver with the main search script.

Usage:
    python3 youtube_channel_search.py --channel-url "https://www.youtube.com/@ChannelName" --query "search terms"
    python3 youtube_channel_search.py --channel-handle "@ChannelName" --query "search terms"
    python3 youtube_channel_search.py --channel-id "UCxxxxx" --query "search terms"
"""

import os
import sys
import json
import argparse
import requests
import re
from pathlib import Path
from typing import Optional, Dict, Any
SHARED_DIR = Path(__file__).resolve().parents[3] / 'shared'
sys.path.insert(0, str(SHARED_DIR))
from credentials import load_credential


def get_api_key(provided_key: Optional[str] = None) -> str:
    """Get API key from provided arg, env var, or ~/.bashrc"""
    api_key = provided_key or os.getenv("YOUTUBE_API_KEY") or load_credential('YOUTUBE_API_KEY', required=False)

    if not api_key:
        raise ValueError(
            "YouTube API key not found. Set YOUTUBE_API_KEY in your environment or shell startup file: "
            "export YOUTUBE_API_KEY='your-key-here'"
        )
    return api_key


def extract_handle_from_url(url: str) -> Optional[str]:
    """Extract channel handle from YouTube URL."""
    match = re.search(r'youtube\.com/@([^/?&]+)', url)
    if match:
        return match.group(1)

    match = re.search(r'youtube\.com/c/([^/?&]+)', url)
    if match:
        return match.group(1)

    return None


def extract_channel_id_from_url(url: str) -> Optional[str]:
    """Extract channel ID directly if URL contains it."""
    match = re.search(r'youtube\.com/channel/(UC[^/?&]+)', url)
    if match:
        return match.group(1)
    return None


def resolve_channel_id(
    handle: Optional[str] = None,
    url: Optional[str] = None,
    channel_id: Optional[str] = None,
    api_key: str = None
) -> Dict[str, Any]:
    """Resolve channel handle/URL to channel ID using forHandle API."""

    # If channel_id provided directly, use it
    if channel_id:
        return {"success": True, "channel_id": channel_id}

    # Try to extract from URL
    if url:
        direct_id = extract_channel_id_from_url(url)
        if direct_id:
            return {"success": True, "channel_id": direct_id}

        handle = extract_handle_from_url(url)
        if not handle:
            return {"success": False, "error": f"Could not parse URL: {url}"}

    if not handle:
        return {"success": False, "error": "No channel identifier provided"}

    # Use forHandle API to get channel ID
    base_url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "id",
        "forHandle": handle.lstrip('@'),
        "key": api_key
    }

    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            return {"success": False, "error": data["error"].get("message", "API error")}

        items = data.get("items", [])
        if not items:
            return {"success": False, "error": f"Channel not found: @{handle.lstrip('@')}"}

        return {"success": True, "channel_id": items[0].get("id")}

    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Request failed: {str(e)}"}


def search_channel_videos(
    query: str,
    channel_id: str,
    api_key: str,
    max_results: int = 50,
    order: str = "date"
) -> Dict[str, Any]:
    """Search for videos within a specific channel."""

    base_url = "https://www.googleapis.com/youtube/v3/search"
    params = {
        "part": "snippet",
        "q": query,
        "type": "video",
        "channelId": channel_id,
        "maxResults": min(max_results, 50),
        "order": order,
        "key": api_key
    }

    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            return {"success": False, "error": data["error"].get("message", "API error")}

        videos = []
        for item in data.get("items", []):
            snippet = item.get("snippet", {})
            video_id = item.get("id", {}).get("videoId")

            if not video_id:
                continue

            videos.append({
                "title": snippet.get("title", ""),
                "video_id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "channel_title": snippet.get("channelTitle", ""),
                "channel_id": snippet.get("channelId", ""),
                "published_at": snippet.get("publishedAt", ""),
                "description": snippet.get("description", ""),
                "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", "")
            })

        return {
            "success": True,
            "query": query,
            "channel_id": channel_id,
            "total_results": data.get("pageInfo", {}).get("totalResults", 0),
            "returned_results": len(videos),
            "videos": videos
        }

    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Request failed: {str(e)}"}


def main():
    parser = argparse.ArgumentParser(
        description="Search for videos within a specific YouTube channel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Search by channel URL
  %(prog)s --channel-url "https://www.youtube.com/@MetalSole" --query "Claude"

  # Search by channel handle
  %(prog)s --channel-handle "@MetalSole" --query "AI coding"

  # Search by channel ID
  %(prog)s --channel-id "UC6-EGajbNF0DPD9AJ8oQC1A" --query "prompt engineering"
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--channel-url", help="YouTube channel URL")
    group.add_argument("--channel-handle", help="Channel handle (e.g., @MetalSole)")
    group.add_argument("--channel-id", help="Channel ID (UCxxxx)")

    parser.add_argument("--query", "-q", required=True, help="Search query")
    parser.add_argument("--max-results", "-m", type=int, default=50, help="Max results (1-50)")
    parser.add_argument("--order", "-o", choices=["date", "relevance", "viewCount", "rating"],
                       default="date", help="Sort order")
    parser.add_argument("--api-key", help="YouTube API key (overrides env var)")

    args = parser.parse_args()

    try:
        api_key = get_api_key(args.api_key)

        # Resolve channel ID
        resolve_result = resolve_channel_id(
            handle=args.channel_handle,
            url=args.channel_url,
            channel_id=args.channel_id,
            api_key=api_key
        )

        if not resolve_result.get("success"):
            print(json.dumps(resolve_result, indent=2))
            return 1

        channel_id = resolve_result["channel_id"]

        # Search within channel
        result = search_channel_videos(
            query=args.query,
            channel_id=channel_id,
            api_key=api_key,
            max_results=args.max_results,
            order=args.order
        )

        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0 if result.get("success") else 1

    except Exception as e:
        error_result = {
            "success": False,
            "error": f"Unexpected error: {str(e)}"
        }
        print(json.dumps(error_result, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())