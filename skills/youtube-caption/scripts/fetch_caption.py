#!/usr/bin/env python3
"""Fetch YouTube video captions and metadata.

Uses youtube-transcript-api for captions (with residential proxy support)
and urllib with residential proxy for metadata (bypasses YouTube bot detection).

Proxy credentials are auto-loaded from environment or a shell startup file (YOUTUBE_PROXY_URL, or legacy REDDIT_PROXY_URL).
"""

import argparse
import json
import re
import sys
import os
import urllib.request
import urllib.parse
from typing import Optional, Dict, Any, Tuple

import sys
from pathlib import Path
SHARED_DIR = Path(__file__).resolve().parents[3] / 'shared'
sys.path.insert(0, str(SHARED_DIR))
from credentials import load_credential

# Try importing youtube-transcript-api
try:
    from youtube_transcript_api import YouTubeTranscriptApi
    from youtube_transcript_api._errors import TranscriptsDisabled, NoTranscriptFound, VideoUnavailable
    TRANSCRIPT_API_AVAILABLE = True
except ImportError:
    TRANSCRIPT_API_AVAILABLE = False


def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from various URL formats."""
    patterns = [
        r'(?:youtube\.com/watch\?v=|youtu\.be/|youtube\.com/embed/|youtube\.com/v/|youtube\.com/shorts/)([a-zA-Z0-9_-]{11})',
        r'^([a-zA-Z0-9_-]{11})$',  # Just the video ID
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None


def create_proxy_opener(proxy_url: Optional[str] = None) -> urllib.request.OpenerDirector:
    """Create urllib opener with optional proxy support.
    
    Args:
        proxy_url: Proxy URL (if None, loads from environment or a shell startup file)
        
    Returns:
        Configured urllib opener
    """
    if proxy_url is None:
        proxy_url = load_credential('YOUTUBE_PROXY_URL', required=False) or load_credential('REDDIT_PROXY_URL', required=False)
    
    if proxy_url:
        proxy_handler = urllib.request.ProxyHandler({
            'http': proxy_url,
            'https': proxy_url
        })
        opener = urllib.request.build_opener(proxy_handler)
    else:
        opener = urllib.request.build_opener()
    
    return opener


def fetch_captions_with_proxy(video_id: str, language: str = 'en', proxy_url: Optional[str] = None) -> Tuple[Optional[str], Optional[Dict]]:
    """Fetch captions using youtube-transcript-api with residential proxy.
    
    Args:
        video_id: YouTube video ID
        language: Language code (default: en)
        proxy_url: Optional proxy URL (loads from environment or a shell startup file if not provided)
        
    Returns:
        Tuple of (transcript_text, metadata_dict) or (None, None)
    """
    if not TRANSCRIPT_API_AVAILABLE:
        print("Error: youtube-transcript-api not installed. Run: pip install youtube-transcript-api", file=sys.stderr)
        return None, None
    
    # Load proxy from credential hierarchy if not provided
    if proxy_url is None:
        proxy_url = load_credential('YOUTUBE_PROXY_URL', required=False) or load_credential('REDDIT_PROXY_URL', required=False)
    
    try:
        # Initialize API with proxy if available
        if proxy_url:
            from youtube_transcript_api.proxies import GenericProxyConfig
            proxy_config = GenericProxyConfig(proxy_url)
            api = YouTubeTranscriptApi(proxy_config=proxy_config)
        else:
            api = YouTubeTranscriptApi()
        
        # Fetch transcript
        transcript = api.fetch(video_id, languages=[language])
        
        if not transcript:
            return None, None
        
        # Convert to list and combine text
        transcript_list = list(transcript)
        full_text = " ".join([segment.text for segment in transcript_list])
        
        # Get metadata
        word_count = len(full_text.split())
        duration = transcript_list[-1].start if transcript_list else 0
        
        # Check if it's auto-generated
        is_generated = any(
            'auto-generated' in str(segment).lower() or 
            'asr' in str(segment).lower()
            for segment in transcript_list[:5]
        )
        
        metadata = {
            'language': language,
            'word_count': word_count,
            'duration_seconds': int(duration),
            'segments': len(transcript_list),
            'is_generated': is_generated,
            'source': 'youtube_captions'
        }
        
        return full_text, metadata
        
    except TranscriptsDisabled:
        return None, {'error': 'Transcripts disabled for this video'}
    except NoTranscriptFound:
        return None, {'error': f'No transcript found for language: {language}'}
    except VideoUnavailable:
        return None, {'error': 'Video unavailable (private or deleted)'}
    except Exception as e:
        return None, {'error': str(e)}


def fetch_metadata_with_proxy(video_id: str, proxy_url: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch video metadata using urllib with residential proxy.
    
    Uses web scraping via residential proxy to bypass YouTube bot detection.
    
    Args:
        video_id: YouTube video ID
        proxy_url: Optional proxy URL (loads from environment or a shell startup file if not provided)
        
    Returns:
        Dictionary with metadata or None if failed
    """
    url = f"https://www.youtube.com/watch?v={video_id}"
    
    # Load proxy from credential hierarchy if not provided
    if proxy_url is None:
        proxy_url = load_credential('YOUTUBE_PROXY_URL', required=False) or load_credential('REDDIT_PROXY_URL', required=False)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    }
    
    try:
        # Create opener with proxy
        opener = create_proxy_opener(proxy_url)
        
        req = urllib.request.Request(url, headers=headers)
        
        with opener.open(req, timeout=30) as response:
            html = response.read().decode('utf-8')
        
        # Extract ytInitialPlayerResponse
        match = re.search(r'ytInitialPlayerResponse\s*=\s*({.+?});', html)
        if not match:
            return None
        
        data = json.loads(match.group(1))
        video_details = data.get('videoDetails', {})
        
        title = video_details.get('title', '')
        description = video_details.get('shortDescription', '')
        channel = video_details.get('author', '')
        channel_id = video_details.get('channelId', '')
        view_count = video_details.get('viewCount', '')
        
        # Get published date from microformat
        microformat = data.get('microformat', {}).get('playerMicroformatRenderer', {})
        published = microformat.get('publishDate', '')
        duration_seconds = microformat.get('lengthSeconds', 0)
        
        # Convert duration to HH:MM:SS format
        if duration_seconds:
            hours = int(duration_seconds) // 3600
            minutes = (int(duration_seconds) % 3600) // 60
            seconds = int(duration_seconds) % 60
            if hours > 0:
                duration_str = f"{hours}:{minutes:02d}:{seconds:02d}"
            else:
                duration_str = f"{minutes}:{seconds:02d}"
        else:
            duration_str = ''
        
        # Extract thumbnail
        thumbnails = video_details.get('thumbnail', {}).get('thumbnails', [])
        thumbnail = thumbnails[-1].get('url', '') if thumbnails else ''
        
        # Extract links from description
        urls = re.findall(r'https?://[^\s\)\]\>]+', description)
        
        return {
            'title': title,
            'description': description,
            'channel': channel,
            'channel_id': channel_id,
            'published_at': published,
            'duration': duration_str,
            'duration_seconds': int(duration_seconds) if duration_seconds else 0,
            'view_count': int(view_count) if view_count else 0,
            'thumbnail': thumbnail,
            'links_in_description': urls
        }
        
    except Exception as e:
        print(f"Warning: Metadata fetch failed: {e}", file=sys.stderr)
        return None


def main():
    parser = argparse.ArgumentParser(
        description='Fetch YouTube video captions and metadata',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --url "https://www.youtube.com/watch?v=VIDEO_ID"
  %(prog)s --url "https://youtu.be/VIDEO_ID" --metadata-only
  %(prog)s --url "URL" --language es -o output.json
        """
    )
    
    parser.add_argument('--url', '-u', required=True, help='YouTube video URL')
    parser.add_argument('--metadata-only', action='store_true', help='Fetch only metadata (uses proxy)')
    parser.add_argument('--captions-only', action='store_true', help='Fetch only captions (uses proxy)')
    parser.add_argument('--language', '-l', default='en', help='Language code for captions (default: en)')
    parser.add_argument('--output', '-o', help='Save output to JSON file')
    
    args = parser.parse_args()
    
    # Extract video ID
    video_id = extract_video_id(args.url)
    if not video_id:
        print(json.dumps({
            'success': False,
            'error': 'Could not extract video ID from URL',
            'url': args.url
        }, indent=2))
        sys.exit(1)
    
    # Initialize result
    result = {
        'success': True,
        'video_id': video_id,
        'url': f'https://www.youtube.com/watch?v={video_id}'
    }
    
    # Fetch captions if requested (and not metadata-only)
    if not args.metadata_only:
        caption_text, caption_meta = fetch_captions_with_proxy(video_id, args.language)
        
        if caption_text:
            result['captions'] = {
                'text': caption_text,
                **caption_meta
            }
        else:
            result['captions'] = {
                'error': caption_meta.get('error', 'Unknown error') if caption_meta else 'Failed to fetch captions'
            }
    
    # Fetch metadata if requested (and not captions-only)
    if not args.captions_only:
        metadata = fetch_metadata_with_proxy(video_id)
        
        if metadata:
            result['metadata'] = metadata
        else:
            result['metadata'] = {'error': 'Failed to fetch metadata'}
    
    # Output result
    output_json = json.dumps(result, indent=2, ensure_ascii=False)
    
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            f.write(output_json)
        print(f"Output saved to: {args.output}")
    else:
        print(output_json)


if __name__ == '__main__':
    main()
