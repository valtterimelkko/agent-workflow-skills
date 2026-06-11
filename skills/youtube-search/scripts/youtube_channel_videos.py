#!/usr/bin/env python3
"""
YouTube Channel Videos Lister

Lists ALL videos from a YouTube channel using the uploads playlist.
This bypasses the search API limitations by directly accessing the channel's
uploads playlist via playlistItems.list endpoint.

Usage:
    python3 youtube_channel_videos.py --handle "@MetalSole"
    python3 youtube_channel_videos.py --url "https://www.youtube.com/@MetalSole"
    python3 youtube_channel_videos.py --channel-id "UC6-EGajbNF0DPD9AJ8oQC1A"
    python3 youtube_channel_videos.py --playlist-id "UU6-EGajbNF0DPD9AJ8oQC1A"
"""

import os
import sys
import json
import argparse
import requests
import re
from pathlib import Path
from typing import Optional, Dict, Any, List
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


def get_uploads_playlist_id(
    handle: Optional[str] = None,
    url: Optional[str] = None,
    channel_id: Optional[str] = None,
    api_key: str = None
) -> Dict[str, Any]:
    """Get the uploads playlist ID for a channel."""

    base_url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "snippet,contentDetails",
        "key": api_key
    }

    # Determine how to identify the channel
    if channel_id:
        params["id"] = channel_id
    elif url:
        # Try to extract channel ID directly from URL
        direct_id = extract_channel_id_from_url(url)
        if direct_id:
            params["id"] = direct_id
        else:
            extracted_handle = extract_handle_from_url(url)
            if extracted_handle:
                params["forHandle"] = extracted_handle
            else:
                return {"success": False, "error": f"Could not parse URL: {url}"}
    elif handle:
        params["forHandle"] = handle.lstrip('@')
    else:
        return {"success": False, "error": "No channel identifier provided"}

    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            return {"success": False, "error": data["error"].get("message", "API error")}

        items = data.get("items", [])
        if not items:
            return {"success": False, "error": "Channel not found"}

        channel = items[0]
        uploads_id = channel.get("contentDetails", {}).get("relatedPlaylists", {}).get("uploads")

        if not uploads_id:
            return {"success": False, "error": "Could not find uploads playlist"}

        return {
            "success": True,
            "channel_id": channel.get("id"),
            "channel_title": channel.get("snippet", {}).get("title", ""),
            "uploads_playlist_id": uploads_id
        }

    except requests.exceptions.RequestException as e:
        return {"success": False, "error": f"Request failed: {str(e)}"}


def list_playlist_videos(
    playlist_id: str,
    api_key: str,
    max_results: int = 50
) -> List[Dict[str, Any]]:
    """
    List all videos from a playlist using pagination.

    Args:
        playlist_id: YouTube playlist ID (uploads playlist starts with UU)
        api_key: YouTube API key
        max_results: Maximum videos to return (0 = all)

    Returns:
        List of video dictionaries
    """
    base_url = "https://www.googleapis.com/youtube/v3/playlistItems"
    videos = []
    next_page_token = None

    while True:
        params = {
            "part": "snippet,contentDetails",
            "playlistId": playlist_id,
            "maxResults": 50,  # API max per request
            "key": api_key
        }

        if next_page_token:
            params["pageToken"] = next_page_token

        try:
            response = requests.get(base_url, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()

            if "error" in data:
                break

            for item in data.get("items", []):
                snippet = item.get("snippet", {})
                content_details = item.get("contentDetails", {})
                video_id = content_details.get("videoId") or snippet.get("resourceId", {}).get("videoId")

                if not video_id:
                    continue

                video = {
                    "title": snippet.get("title", ""),
                    "video_id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "channel_title": snippet.get("channelTitle", ""),
                    "channel_id": snippet.get("channelId", ""),
                    "published_at": snippet.get("publishedAt", ""),
                    "description": snippet.get("description", "")[:300] if snippet.get("description") else "",
                    "thumbnail_url": snippet.get("thumbnails", {}).get("high", {}).get("url", ""),
                    "position": snippet.get("position", 0)
                }
                videos.append(video)

                # Check if we've hit the max
                if max_results > 0 and len(videos) >= max_results:
                    return videos

            # Check for next page
            next_page_token = data.get("nextPageToken")
            if not next_page_token:
                break

        except requests.exceptions.RequestException:
            break

    return videos


def get_channel_videos(
    handle: Optional[str] = None,
    url: Optional[str] = None,
    channel_id: Optional[str] = None,
    playlist_id: Optional[str] = None,
    max_results: int = 50,
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get all videos from a YouTube channel.

    Args:
        handle: Channel handle (e.g., @MetalSole)
        url: Channel URL
        channel_id: Channel ID (UCxxxx)
        playlist_id: Direct uploads playlist ID (UUxxxx)
        max_results: Maximum videos to return (0 = all, default 50)
        api_key: Optional API key override

    Returns:
        Dictionary with channel info and videos
    """
    api_key = get_api_key(api_key)

    # If playlist_id provided directly, use it
    if playlist_id:
        uploads_id = playlist_id
        channel_info = {"channel_title": "Unknown", "channel_id": "Unknown"}
    else:
        # Get uploads playlist ID from channel
        result = get_uploads_playlist_id(
            handle=handle,
            url=url,
            channel_id=channel_id,
            api_key=api_key
        )

        if not result.get("success"):
            return result

        uploads_id = result["uploads_playlist_id"]
        channel_info = {
            "channel_title": result["channel_title"],
            "channel_id": result["channel_id"]
        }

    # Get videos from uploads playlist
    videos = list_playlist_videos(uploads_id, api_key, max_results)

    return {
        "success": True,
        "channel_title": channel_info.get("channel_title", videos[0]["channel_title"] if videos else "Unknown"),
        "channel_id": channel_info.get("channel_id", videos[0]["channel_id"] if videos else "Unknown"),
        "uploads_playlist_id": uploads_id,
        "total_videos": len(videos),
        "videos": videos
    }


def main():
    parser = argparse.ArgumentParser(
        description="List all videos from a YouTube channel",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List videos by channel handle
  %(prog)s --handle "@MetalSole"
  %(prog)s --handle "@MetalSole" --max-results 20

  # List videos by channel URL
  %(prog)s --url "https://www.youtube.com/@MetalSole"

  # List videos by channel ID
  %(prog)s --channel-id "UC6-EGajbNF0DPD9AJ8oQC1A"

  # List videos by uploads playlist ID (faster, skips channel lookup)
  %(prog)s --playlist-id "UU6-EGajbNF0DPD9AJ8oQC1A"

  # Get all videos (no limit)
  %(prog)s --handle "@MetalSole" --max-results 0
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--handle", "-H", help="Channel handle (e.g., @MetalSole)")
    group.add_argument("--url", "-u", help="YouTube channel URL")
    group.add_argument("--channel-id", "-c", help="Channel ID (UCxxxx)")
    group.add_argument("--playlist-id", "-p", help="Uploads playlist ID (UUxxxx) - fastest option")

    parser.add_argument(
        "--max-results", "-m",
        type=int,
        default=50,
        help="Maximum videos to return (0 = all, default: 50)"
    )
    parser.add_argument("--api-key", help="YouTube API key (overrides env var)")

    args = parser.parse_args()

    try:
        result = get_channel_videos(
            handle=args.handle,
            url=args.url,
            channel_id=args.channel_id,
            playlist_id=args.playlist_id,
            max_results=args.max_results,
            api_key=args.api_key
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