#!/usr/bin/env python3
"""
Minimal Xpoz Pipeline Test - Tests with minimal API calls to verify functionality.

This test uses a SINGLE platform and SINGLE query to verify the pipeline works
without consuming too many credits or timing out.
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR / "xpoz"))

# Import Xpoz client
from xpoz_client import XpozMCPClient
from xpoz_credentials import CredentialNotFoundError


async def test_single_reddit_query():
    """Test with a single Reddit query - minimal credit usage."""
    print("=" * 70)
    print("MINIMAL XPOZ PIPELINE TEST")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("\nThis test uses 1 query to verify the pipeline works.")
    print("Estimated credit usage: ~5-10 credits")
    print()
    
    client = None
    try:
        # Connect
        print("[1/3] Connecting to Xpoz...")
        client = XpozMCPClient()
        
        # Increase timeout for this test
        client.TIMEOUT = aiohttp.ClientTimeout(total=120)  # 2 minutes
        client.MAX_POLL_TIME = 180  # 3 minutes max polling
        
        await client.connect()
        print("✓ Connected to Xpoz MCP\n")
        
        # Single query - minimal credit usage
        print("[2/3] Executing test query (r/startups, limit=5)...")
        print("    (This may take 30-120 seconds due to async processing)")
        
        start_time = datetime.now()
        
        result = await client.call_tool(
            "getRedditPostsByKeywords",
            {
                "query": "subreddit:startups SaaS",
                "limit": 5
            }
        )
        
        elapsed = (datetime.now() - start_time).total_seconds()
        print(f"✓ Query completed in {elapsed:.1f} seconds\n")
        
        # Parse results
        print("[3/3] Analyzing results...")
        content = result.get("content", [])
        
        if not content:
            print("⚠️  No content in response")
            return False
        
        print(f"✓ Got {len(content)} content items")
        
        # Extract sample data
        sample_text = ""
        if isinstance(content[0], dict) and "text" in content[0]:
            sample_text = content[0]["text"][:200]
        else:
            sample_text = str(content[0])[:200]
        
        print(f"\nSample response data:")
        print(f"  {sample_text}...")
        
        # Check if we got actual Reddit data
        has_data = "results[" in sample_text or "title" in sample_text.lower()
        
        if has_data:
            print("\n✅ SUCCESS: Pipeline is working correctly!")
            print("   - Connection established")
            print("   - Query executed successfully")
            print("   - Data received from Xpoz")
            return True
        else:
            print("\n⚠️  WARNING: Response received but may not contain expected data")
            return False
            
    except asyncio.TimeoutError:
        print("\n❌ TIMEOUT: Operation took too long")
        print("   This is normal for Xpoz API - operations can take 30-120 seconds")
        print("   Try increasing timeout or running during off-peak hours")
        return False
    except CredentialNotFoundError as e:
        print(f"\n❌ CREDENTIAL ERROR: {e}")
        print("   Ensure ~/.xpoz/token.txt exists with a valid token")
        return False
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if client:
            await client.close()


async def main():
    """Run minimal test."""
    import aiohttp
    
    success = await test_single_reddit_query()
    
    print("\n" + "=" * 70)
    if success:
        print("TEST PASSED - Pipeline is functional")
        print("\nYou can now run the full pipeline with confidence.")
        print("Note: Full pipeline will use ~77 credits per run.")
        print("With 4,659 remaining credits, you have ~60 runs available.")
    else:
        print("TEST ISSUES DETECTED")
        print("\nPossible causes:")
        print("  1. Xpoz API temporarily slow (retry in a few minutes)")
        print("  2. Network connectivity issues")
        print("  3. Token may need refresh (visit xpoz.ai)")
    print("=" * 70)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))