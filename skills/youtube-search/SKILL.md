---
name: youtube-search
description: Search YouTube videos by query or within specific channels. Supports date filtering, sort ordering, and duration filters to exclude YouTube Shorts. Returns LLM-optimized JSON with video details.
---

# Search YouTube Videos

Search for YouTube videos using the YouTube Data API v3. Find videos by query across all of YouTube or within specific channels.

## Prerequisites

**YouTube API Key** available in the environment or a shell startup file such as `~/.bashrc`:
```bash
export YOUTUBE_API_KEY="your-api-key-here"
```

Get one from [Google Cloud Console](https://console.cloud.google.com/): Create project → Enable YouTube Data API v3 → Create API Key.

**Daily quota**: 10,000 units (each search ≈ 100 units, channel resolution ≈ 1 unit, playlist fetch ≈ 1 unit).

## When to Use

- Search videos by topic or channel
- Filter by date, duration, sort order
- Get up to 50 results per query

## Quick Start

### Basic search:
```bash
python3 ./scripts/youtube_search.py --query "AI tutorials" --max-results 10
```

### Channel-specific (if you already have the channel ID):
```bash
python3 ./scripts/youtube_search.py --query "Python" --channel-id "UC123..." --max-results 20
```

## Parameters

| Parameter | Required | Default | Notes |
|-----------|----------|---------|-------|
| `--query` or `-q` | **Yes** | - | Search term |
| `--channel-id` or `-c` | No | - | If provided, search only in this channel |
| `--max-results` or `-m` | No | 10 | Max 50 (preserves quota and LLM context) |
| `--order` or `-o` | No | relevance | date, rating, relevance, viewCount |
| `--published-after` | No | - | ISO 8601 format (e.g., "2025-01-01T00:00:00Z") |
| `--published-before` | No | - | ISO 8601 format |
| `--video-duration` or `-d` | No | any | any, short (<4min), medium (4-20min), long (>20min) |

## Helper Scripts (API Quota Warning)

⚠️ **Each helper script uses API quota. Plan carefully before running multiple times.**

### 1. youtube_channel_id.py - Resolve @handle to Channel ID
**Cost**: 1 unit per resolution
```bash
python3 ./scripts/youtube_channel_id.py --handle "@MetalSole"
```

### 2. youtube_channel_videos.py - List Channel Videos
**Cost**: 1-2 units for channel lookup + 1 unit per ~50 videos fetched
```bash
# By handle
python3 ./scripts/youtube_channel_videos.py --handle "@MetalSole" --max-results 50

# By channel ID (saves quota - skips handle resolution)
python3 ./scripts/youtube_channel_videos.py --channel-id "UC123..." --max-results 50

# By playlist ID (cheapest - fastest method)
python3 ./scripts/youtube_channel_videos.py --playlist-id "UU123..." --max-results 50
```

### 3. youtube_channel_search.py - Search Within Channel
**Cost**: 1-2 units (channel lookup) + 100 units (search query)
```bash
python3 ./scripts/youtube_channel_search.py --channel-handle "@MetalSole" --query "AI"
```

## Quota Estimation

| Operation | Cost | Purpose |
|-----------|------|---------|
| Basic search with query | ~100 | Find videos by topic |
| Resolve handle (@MetalSole) | ~1 | Get channel ID from handle |
| Fetch 50 channel videos | ~1 | List all uploads from channel |
| Search within channel | ~100 | Find topic within specific channel |

**Example cost**: Searching 10 channels for videos = ~10 units. Then searching within each channel = ~1000 units total. Plan accordingly!

## Output Format

Returns JSON with video metadata:
```json
{
  "success": true,
  "videos": [
    {
      "title": "Video Title",
      "url": "https://www.youtube.com/watch?v=VIDEO_ID",
      "channel_title": "Channel Name",
      "published_at": "2025-01-15T10:00:00Z",
      "description": "..."
    }
  ]
}
```

## Examples

```bash
# Latest AI videos
python3 ./scripts/youtube_search.py --query "AI" --order "date" --max-results 10

# Longer-form content only (no shorts)
python3 ./scripts/youtube_search.py --query "tutorial" --video-duration "medium" --max-results 15

# Last 30 days
python3 ./scripts/youtube_search.py --query "news" --published-after "2025-11-23T00:00:00Z"
```

## Troubleshooting

| Problem | Solution |
|---------|----------|
| API key not found | Make available in your environment or shell startup file: `export YOUTUBE_API_KEY="key-here"` |
| 403 Forbidden | Key lacks permissions. Enable YouTube Data API v3 in Google Cloud Console |
| Quota exceeded | Used 10,000 units today. Create new Google Cloud project or wait 24hrs |
| No results | Try broader query, remove date filters |

## Tips for Efficient Quota Use

1. **Use channel_id, not handle** when possible (saves resolution cost)
2. **Use playlist_id** for channel videos (cheapest - ~1 unit instead of 100+)
3. **Batch operations**: Plan all queries before executing to avoid re-runs
4. **Cache results**: Save output to file to avoid re-querying same channels
5. **For bulk channel analysis**: Prefer `youtube_channel_videos.py` over `youtube_channel_search.py`

## When Quota Runs Out

If you exhaust today's quota:
- **Option 1**: Wait 24 hours for quota reset
- **Option 2**: Create new Google Cloud project with fresh quota
- **Option 3**: Request quota increase (takes 24-48 hours)
- **Option 4**: Switch to web-based channel browsing (manual, no quota cost)

## Security & Limitations

- API key = read-only access to public data
- Cannot access: private videos, watch history, subscriptions
- Max 50 results per query (for context window)
- View counts/likes not included
