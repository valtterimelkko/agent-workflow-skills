---
name: youtube-caption
description: Fetch YouTube video captions/transcripts and metadata. Use when you need to download video transcripts, extract captions from YouTube URLs, get video descriptions and metadata, or process YouTube video text content. Supports residential proxy for reliable caption and metadata fetching (credentials can be auto-loaded from environment or a shell startup file).
---

# YouTube Caption Fetcher

Download captions/transcripts and metadata from any YouTube video using the `youtube-transcript-api` library with optional residential proxy support.

## Prerequisites

**Required Python package:**
```bash
pip install youtube-transcript-api
```

**Residential Proxy Credentials** (auto-loaded from environment or a shell startup file):
```bash
# Reddit proxy for YouTube caption and metadata fetching
export YOUTUBE_PROXY_URL="http://username:password@host:port"
# legacy fallback also supported:
export REDDIT_PROXY_URL="http://username:password@host:port"
```

The skill automatically fetches these credentials from the environment or a shell startup file when caption or metadata fetching requires proxy support.

## Quick Start

### Fetch captions and metadata:
```bash
python3 ./scripts/fetch_caption.py --url "https://www.youtube.com/watch?v=VIDEO_ID"
```

### Fetch only metadata (uses proxy):
```bash
python3 ./scripts/fetch_caption.py --url "https://youtu.be/VIDEO_ID" --metadata-only
```

### Fetch captions only (uses proxy):
```bash
python3 ./scripts/fetch_caption.py --url "https://www.youtube.com/watch?v=VIDEO_ID" --captions-only
```

## Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--url` or `-u` | **Yes** | - | YouTube video URL (supports various formats) |
| `--metadata-only` | No | false | Fetch only video metadata (uses proxy) |
| `--captions-only` | No | false | Fetch only captions (uses proxy) |
| `--language` or `-l` | No | en | Language code for captions (e.g., en, es, fr) |
| `--output` or `-o` | No | - | Save output to JSON file |

## Output Format

Returns JSON with both captions and metadata:

```json
{
  "success": true,
  "video_id": "dQw4w9WgXcQ",
  "url": "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
  "metadata": {
    "title": "Video Title",
    "description": "Full video description...",
    "channel": "Channel Name",
    "channel_id": "UC...",
    "published_at": "2025-01-15T10:00:00Z",
    "duration": "10:30",
    "duration_seconds": 630,
    "view_count": 1000000,
    "thumbnail": "https://i.ytimg.com/vi/...",
    "links_in_description": [
      "https://example.com/link1",
      "https://example.com/link2"
    ]
  },
  "captions": {
    "text": "Full transcript text...",
    "language": "en",
    "is_generated": true,
    "word_count": 1500,
    "duration_seconds": 630
  }
}
```

## How It Works

1. **Caption fetching**: Uses `youtube-transcript-api` with residential proxy (to avoid IP blocks)
2. **Metadata fetching**: Uses `urllib` with residential proxy (to bypass YouTube bot detection)
3. **Proxy credentials**: Automatically loaded from the environment or a shell startup file (`YOUTUBE_PROXY_URL`, or legacy `REDDIT_PROXY_URL`)

## Error Handling

| Error | Cause | Solution |
|-------|-------|----------|
| `TranscriptsDisabled` | Video has captions disabled | Try another video |
| `NoTranscriptFound` | No captions in requested language | Try `--language` with different code |
| `VideoUnavailable` | Video is private/deleted | Check video URL |
| `ProxyError` | Proxy connection failed | Check proxy credentials in your environment or shell startup file |

## Usage Examples

### Get full video data:
```bash
python3 ./scripts/fetch_caption.py --url "https://www.youtube.com/watch?v=VIDEO_ID" -o output.json
```

### Get captions in Spanish:
```bash
python3 ./scripts/fetch_caption.py --url "https://youtu.be/VIDEO_ID" --language es
```

### Extract just the transcript text:
```bash
python3 ./scripts/fetch_caption.py --url "URL" --captions-only | jq -r '.captions.text'
```

### Get metadata with links from description:
```bash
python3 ./scripts/fetch_caption.py --url "URL" --metadata-only | jq '.metadata.links_in_description'
```

## Notes

- **Proxy is used for both caption AND metadata fetching** to bypass YouTube bot detection
- Supports auto-generated and manual captions
- Falls back gracefully if captions are unavailable
- Metadata includes `links_in_description` array extracted from the video description
