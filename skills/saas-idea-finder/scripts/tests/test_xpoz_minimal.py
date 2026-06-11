#!/usr/bin/env python3
"""
Minimal Xpoz test - just connection and single platform test.
"""
import asyncio
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR / "xpoz"))
sys.path.insert(0, str(SCRIPT_DIR / "platforms"))

# Import platform scrapers with proper path handling
import importlib.util
spec = importlib.util.spec_from_file_location("base_scraper", SCRIPT_DIR / "platforms" / "base_scraper.py")
base_scraper = importlib.util.module_from_spec(spec)
sys.modules['base_scraper'] = base_scraper
spec.loader.exec_module(base_scraper)

from xpoz_client import XpozMCPClient


async def test_connection():
    """Test basic Xpoz connection."""
    print("Testing Xpoz Connection")
    print("=" * 50)
    
    client = XpozMCPClient()
    try:
        await client.connect()
        print("✓ Connected to Xpoz MCP")
        
        # Try a simple Reddit query with minimal results
        print("\nTesting Reddit query (subreddit:startups, limit:5)...")
        print("(This may take up to 60 seconds)")
        
        result = await client.call_tool(
            "getRedditPostsByKeywords",
            {"query": "subreddit:startups", "limit": 5}
        )
        
        content = result.get("content", [])
        print(f"✓ Got response with {len(content)} content items")
        
        # Parse and show sample
        if content:
            text = content[0].get("text", "") if isinstance(content[0], dict) else str(content[0])
            print(f"\nSample data (first 200 chars):")
            print(text[:200] + "...")
        
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        await client.close()


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    sys.exit(0 if success else 1)