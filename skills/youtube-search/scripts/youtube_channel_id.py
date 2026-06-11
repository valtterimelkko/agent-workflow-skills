#!/usr/bin/env python3
"""
YouTube Channel ID Resolver

Resolves YouTube channel handles (@ChannelName) or URLs to channel IDs.
Uses the YouTube Data API v3 channels.list endpoint with forHandle parameter.

Usage:
    python3 youtube_channel_id.py --handle "@MetalSole"
    python3 youtube_channel_id.py --url "https://www.youtube.com/@MetalSole"
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
    """Extract channel handle from various YouTube URL formats."""
    # Pattern for @handle in URL
    match = re.search(r'youtube\.com/@([^/?&]+)', url)
    if match:
        return match.group(1)

    # Pattern for /c/customname
    match = re.search(r'youtube\.com/c/([^/?&]+)', url)
    if match:
        return match.group(1)

    # Pattern for /channel/UCxxxx (already a channel ID)
    match = re.search(r'youtube\.com/channel/(UC[^/?&]+)', url)
    if match:
        # Return None to indicate we already have the ID
        return None

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
    api_key: Optional[str] = None
) -> Dict[str, Any]:
    """
    Resolve a YouTube channel handle or URL to its channel ID.

    Args:
        handle: Channel handle (with or without @)
        url: YouTube channel URL
        api_key: Optional API key override

    Returns:
        Dictionary with channel information
    """
    api_key = get_api_key(api_key)

    # Determine handle from inputs
    channel_handle = None
    direct_channel_id = None

    if url:
        # Check if URL contains channel ID directly
        direct_channel_id = extract_channel_id_from_url(url)
        if not direct_channel_id:
            channel_handle = extract_handle_from_url(url)
            if not channel_handle:
                return {
                    "success": False,
                    "error": f"Could not extract handle from URL: {url}"
                }
    elif handle:
        # Remove @ if present
        channel_handle = handle.lstrip('@')
    else:
        return {
            "success": False,
            "error": "Either --handle or --url must be provided"
        }

    # If we already have a channel ID from the URL, verify and return it
    if direct_channel_id:
        return verify_channel_id(direct_channel_id, api_key)

    # Use forHandle to get channel info
    base_url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "snippet,contentDetails,statistics",
        "forHandle": channel_handle,
        "key": api_key
    }

    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        if "error" in data:
            return {
                "success": False,
                "error": data["error"].get("message", "Unknown API error")
            }

        items = data.get("items", [])
        if not items:
            return {
                "success": False,
                "error": f"No channel found for handle: @{channel_handle}"
            }

        channel = items[0]
        snippet = channel.get("snippet", {})
        content_details = channel.get("contentDetails", {})
        statistics = channel.get("statistics", {})

        return {
            "success": True,
            "channel_id": channel.get("id"),
            "handle": f"@{channel_handle}",
            "title": snippet.get("title", ""),
            "description": snippet.get("description", "")[:200] + "..." if len(snippet.get("description", "")) > 200 else snippet.get("description", ""),
            "custom_url": snippet.get("customUrl", ""),
            "uploads_playlist_id": content_details.get("relatedPlaylists", {}).get("uploads"),
            "subscriber_count": statistics.get("subscriberCount", "hidden"),
            "video_count": statistics.get("videoCount", "0"),
            "channel_url": f"https://www.youtube.com/channel/{channel.get('id')}"
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Request failed: {str(e)}"
        }


def verify_channel_id(channel_id: str, api_key: str) -> Dict[str, Any]:
    """Verify a channel ID and return channel info."""
    base_url = "https://www.googleapis.com/youtube/v3/channels"
    params = {
        "part": "snippet,contentDetails,statistics",
        "id": channel_id,
        "key": api_key
    }

    try:
        response = requests.get(base_url, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()

        items = data.get("items", [])
        if not items:
            return {
                "success": False,
                "error": f"No channel found for ID: {channel_id}"
            }

        channel = items[0]
        snippet = channel.get("snippet", {})
        content_details = channel.get("contentDetails", {})
        statistics = channel.get("statistics", {})

        return {
            "success": True,
            "channel_id": channel.get("id"),
            "title": snippet.get("title", ""),
            "description": snippet.get("description", "")[:200] + "..." if len(snippet.get("description", "")) > 200 else snippet.get("description", ""),
            "custom_url": snippet.get("customUrl", ""),
            "uploads_playlist_id": content_details.get("relatedPlaylists", {}).get("uploads"),
            "subscriber_count": statistics.get("subscriberCount", "hidden"),
            "video_count": statistics.get("videoCount", "0"),
            "channel_url": f"https://www.youtube.com/channel/{channel.get('id')}"
        }

    except requests.exceptions.RequestException as e:
        return {
            "success": False,
            "error": f"Request failed: {str(e)}"
        }


def main():
    parser = argparse.ArgumentParser(
        description="Resolve YouTube channel handle or URL to channel ID",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Resolve by handle
  %(prog)s --handle "@MetalSole"
  %(prog)s --handle "MetalSole"

  # Resolve by URL
  %(prog)s --url "https://www.youtube.com/@MetalSole"
  %(prog)s --url "https://www.youtube.com/c/MetalSole"
  %(prog)s --url "https://www.youtube.com/channel/UCxxxxxxx"
        """
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--handle", "-H", help="Channel handle (e.g., @MetalSole or MetalSole)")
    group.add_argument("--url", "-u", help="YouTube channel URL")

    parser.add_argument("--api-key", help="YouTube API key (overrides env var)")

    args = parser.parse_args()

    try:
        result = resolve_channel_id(
            handle=args.handle,
            url=args.url,
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