#!/usr/bin/env python3
"""
Quick Baseline Test - 1 lens only, smaller limits for faster results.
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

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

from helpers.xpoz_fetcher import XpozFetcher


async def run_quick_test():
    """Run quick baseline test with 1 lens."""
    print("=" * 70)
    print("QUICK BASELINE TEST - E-commerce/Sellers Lens")
    print("=" * 70)
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("Limit: 10 per platform (for speed)")
    print()
    
    fetcher = XpozFetcher()
    
    print("[Connecting to Xpoz...]")
    connected = await fetcher.connect()
    if not connected:
        print("ERROR: Could not connect to Xpoz")
        return {"error": "Connection failed"}
    print("✓ Connected\n")
    
    try:
        print("Fetching data for 'ecommerce_sellers' lens...")
        print("(This may take 2-5 minutes due to Xpoz API async operations)")
        print()
        
        result = await fetcher.fetch_for_lens(
            lens_name="ecommerce_sellers",
            limit_per_platform=10
        )
        
        # Print results
        platforms = result.get("platforms", {})
        errors = result.get("errors", [])
        
        total_posts = sum(p.get("count", 0) for p in platforms.values())
        total_high = sum(p.get("high_opportunity_count", 0) for p in platforms.values())
        
        print("\n" + "=" * 70)
        print("RESULTS")
        print("=" * 70)
        
        print(f"\n📊 Platform Results:")
        for platform, data in platforms.items():
            count = data.get("count", 0)
            high = data.get("high_opportunity_count", 0)
            print(f"  {platform:12} {count:3} posts | {high:2} high-opportunity")
        
        print(f"\n📈 Summary: {total_posts} total posts, {total_high} high-opportunity")
        
        if errors:
            print(f"\n⚠️  Errors ({len(errors)}):")
            for err in errors:
                print(f"  - {err.get('platform')}: {err.get('error', 'Unknown')}")
        
        # Show sample posts
        print(f"\n📝 Sample High-Opportunity Posts:")
        for platform, data in platforms.items():
            posts = data.get("posts", [])
            high_opp_posts = [p for p in posts if p.get("is_high_opportunity")]
            if high_opp_posts:
                print(f"\n  {platform.upper()}:")
                for post in high_opp_posts[:2]:
                    title = post.get('title', '') or post.get('body', '')[:60]
                    print(f"    - {title[:70]}... (pain: {post.get('pain_score', 0):.2f})")
        
        # Aggregated topics
        topics = result.get("aggregated_topics", [])
        print(f"\n🔥 Aggregated Topics ({len(topics)}):")
        for i, topic in enumerate(topics[:5], 1):
            print(f"  {i}. {topic['topic'][:40]} "
                  f"(score: {topic['validation_score']:.1f}, "
                  f"platforms: {', '.join(topic.get('platforms', []))})")
        
        # Save results
        output_dir = Path.home() / ".saas-idea-finder" / "outputs" / "baseline_test"
        output_dir.mkdir(parents=True, exist_ok=True)
        output_file = output_dir / f"quick_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        with open(output_file, 'w') as f:
            json.dump(result, f, indent=2, default=str)
        
        print(f"\n✓ Results saved to: {output_file}")
        
        return result
        
    finally:
        await fetcher.close()


if __name__ == "__main__":
    result = asyncio.run(run_quick_test())
    sys.exit(0 if "error" not in result else 1)