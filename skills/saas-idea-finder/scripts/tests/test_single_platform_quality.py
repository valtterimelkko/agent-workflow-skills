#!/usr/bin/env python3
"""
Single Platform Quality Test

Tests ONE platform with ONE query to verify data quality without
hitting rate limits. This validates that Xpoz returns usable data.
"""
import asyncio
import sys
import json
import re
from pathlib import Path
from datetime import datetime

SCRIPT_DIR = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(SCRIPT_DIR))
sys.path.insert(0, str(SCRIPT_DIR / "xpoz"))

from xpoz_client import XpozMCPClient


async def test_reddit_quality():
    """Test Reddit data quality with a single query."""
    print("=" * 70)
    print("SINGLE PLATFORM QUALITY TEST - Reddit")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("\nTesting ONE query with 10 results to verify data quality")
    print("Query: 'expensive fees' in r/EtsySellers")
    print()
    
    client = None
    try:
        client = XpozMCPClient()
        await client.connect()
        print("✓ Connected to Xpoz\n")
        
        print("Executing query... (may take 30-60 seconds)")
        result = await client.call_tool(
            "getRedditPostsByKeywords",
            {"query": "expensive fees subreddit:EtsySellers", "limit": 10}
        )
        
        # Parse the result
        content = result.get("content", [])
        print(f"✓ Got response with {len(content)} content items\n")
        
        # Extract and analyze posts
        posts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                text = item.get("text", "")
                
                # Try to parse YAML-like format
                if "results[" in text and "{" in text:
                    # This is the Xpoz YAML-like format
                    print("📄 Sample raw response (first 500 chars):")
                    print(text[:500])
                    print("\n" + "=" * 70)
                    
                    # Parse posts from YAML format
                    posts = parse_yaml_posts(text)
                    print(f"✓ Parsed {len(posts)} posts from response\n")
                    
        if posts:
            print("📊 POST ANALYSIS:")
            print("=" * 70)
            
            for i, post in enumerate(posts[:5], 1):
                print(f"\nPost {i}:")
                print(f"  Title: {post.get('title', 'N/A')[:80]}")
                print(f"  Subreddit: {post.get('subreddit', 'N/A')}")
                print(f"  Author: {post.get('author', 'N/A')}")
                
                # Check for consumer pain points
                title = post.get('title', '').lower()
                has_pain = any(word in title for word in ['expensive', 'fee', 'cost', 'money', 'frustrated', 'hate', 'problem'])
                print(f"  Consumer Pain Signal: {'✓ YES' if has_pain else '✗ No'}")
            
            # Count pain signals
            pain_count = sum(1 for p in posts if any(word in p.get('title', '').lower() 
                             for word in ['expensive', 'fee', 'cost', 'frustrated', 'problem', 'hate']))
            
            print("\n" + "=" * 70)
            print(f"📈 QUALITY SUMMARY:")
            print(f"   Total posts: {len(posts)}")
            print(f"   Posts with consumer pain signals: {pain_count}")
            print(f"   Quality ratio: {(pain_count/len(posts)*100):.1f}%")
            
            if pain_count >= 2:
                print("\n✅ DATA QUALITY: GOOD")
                print("   Xpoz is returning relevant consumer problem data")
                print("   Integration is working as intended")
            else:
                print("\n⚠️  DATA QUALITY: NEEDS IMPROVEMENT")
                print("   Consider refining search queries")
            
            return True
        else:
            print("⚠️  Could not parse posts from response")
            return False
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        if client:
            await client.close()


def parse_yaml_posts(text: str) -> list:
    """Parse posts from Xpoz YAML-like format."""
    posts = []
    lines = text.strip().split('\n')
    
    in_data = False
    header_fields = []
    
    for line in lines:
        line = line.strip()
        
        # Look for results header
        if 'results[' in line and ']{' in line:
            match = re.search(r'\{([^}]+)\}', line)
            if match:
                header_fields = match.group(1).split(',')
            in_data = True
            continue
        
        # Parse data lines
        if in_data and line and not line.startswith(('success:', 'data:', 'status:', 'operationId:')):
            values = line.split(',')
            if len(values) >= len(header_fields):
                post = {}
                for i, field in enumerate(header_fields):
                    if i < len(values):
                        post[field] = values[i].strip().strip('"')
                posts.append(post)
    
    return posts


async def main():
    success = await test_reddit_quality()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))