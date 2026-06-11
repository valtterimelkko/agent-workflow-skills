# ~/.bashrc Fallback Pattern

## Problem Solved

Some agent harnesses do not automatically source your shell startup file. This means variables stored there may need an explicit fallback reader in bundled scripts.

## Solution Implemented

The `youtube_search.py` script now includes a `read_api_key_from_bashrc()` function that:

1. **Reads `~/.bashrc` directly** - No need to source it
2. **Parses the API key** - Uses regex to extract the value
3. **Falls back automatically** - Only used if env var isn't set

### Code Pattern

```python
def read_api_key_from_bashrc() -> Optional[str]:
    """
    Read YOUTUBE_API_KEY from ~/.bashrc as a fallback.
    This is needed because Claude Code doesn't run in an interactive shell.
    """
    bashrc_path = Path.home() / ".bashrc"
    if not bashrc_path.exists():
        return None
    
    try:
        with open(bashrc_path, 'r') as f:
            content = f.read()
            # Look for export YOUTUBE_API_KEY="..." or similar
            patterns = [
                r'export\s+YOUTUBE_API_KEY=["\']([^"\']+)["\']',
                r'export\s+YOUTUBE_API_KEY=([^\s]+)',
                r'YOUTUBE_API_KEY=["\']([^"\']+)["\']',
                r'YOUTUBE_API_KEY=([^\s]+)'
            ]
            
            for pattern in patterns:
                match = re.search(pattern, content)
                if match:
                    return match.group(1)
    except Exception:
        pass
    
    return None
```

### Usage in Script

```python
# Try in order: 1) provided arg, 2) env var, 3) ~/.bashrc
self.api_key = (
    api_key or 
    os.getenv("YOUTUBE_API_KEY") or 
    read_api_key_from_bashrc()
)
```

## Benefits

✅ **Works immediately** - No need to run `source ~/.bashrc`  
✅ **User-friendly** - Just add key to `~/.bashrc` and go  
✅ **Robust** - Handles various formats (with/without quotes, with/without export)  
✅ **Backward compatible** - Still works with env vars if set  
✅ **Safe** - Gracefully handles missing or malformed files

## Tested Formats

The regex patterns handle all these formats:

```bash
export YOUTUBE_API_KEY="key-here"
export YOUTUBE_API_KEY='key-here'
export YOUTUBE_API_KEY=key-here
YOUTUBE_API_KEY="key-here"
YOUTUBE_API_KEY='key-here'
YOUTUBE_API_KEY=key-here
```

## Reusable for Other Skills

This pattern can be applied to **any MCP skill** that needs API keys:

- Context7 skills
- GitHub skills  
- n8n skills
- Custom API integrations

Just adapt the function for your specific environment variable name!

## Testing Confirmation

```bash
# Test 1: General search
$ python3 youtube_search.py --query "test" --max-results 1
✅ Success - API key read from ~/.bashrc

# Test 2: Channel-specific search
$ python3 youtube_search.py --query "python" --channel-id "UC8butISFwT-Wl7EV0hUK0BQ" --max-results 3
✅ Success - Found 2,488 results, returned 3

# Test 3: Without sourcing
$ env | grep YOUTUBE_API_KEY
(empty - env var not set)
$ python3 youtube_search.py --query "test" --max-results 1
✅ Success - Fallback to ~/.bashrc worked!
```

## Line Count

After adding this feature:
- `youtube_search.py`: ~310 lines (added ~30 lines for fallback)
- `SKILL.md`: 350 lines (still under 500 limit ✓)

## Next Steps

Consider applying this pattern to:
1. Context7 skills (`CONTEXT7_API_KEY`)
2. Any other skills using API keys stored in `~/.bashrc`
3. Document as a standard pattern for future skill development
