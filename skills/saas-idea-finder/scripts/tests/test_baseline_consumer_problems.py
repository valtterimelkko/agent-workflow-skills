#!/usr/bin/env python3
"""
Baseline Test: Consumer Problem Detection Quality Analysis

Runs the current Xpoz implementation across 2-3 lenses to establish
baseline quality metrics for consumer problem detection.

This test analyzes:
1. Volume of high-opportunity posts per lens
2. Pain point detection accuracy
3. Cross-platform validation effectiveness
4. Consumer vs developer problem ratio
"""
import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List

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

# Now import other scrapers - they should find base_scraper in sys.modules

# Test configuration
TEST_LENSES = [
    "ecommerce_sellers",  # Consumer-focused (Tuesday)
    "small_business_ops", # Consumer-focused (Friday)
    "creator_economy",    # Consumer-focused (Wednesday)
]

LIMIT_PER_PLATFORM = 20  # Reasonable for testing


class BaselineTestRunner:
    """Runs baseline tests and analyzes results."""
    
    def __init__(self):
        self.results = {}
        self.analysis = {}
        
    async def run_test(self) -> Dict[str, Any]:
        """Run baseline test across configured lenses."""
        print("=" * 70)
        print("BASELINE TEST: Consumer Problem Detection Quality")
        print("=" * 70)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Test Lenses: {', '.join(TEST_LENSES)}")
        print(f"Limit per platform: {LIMIT_PER_PLATFORM}")
        print()
        
        try:
            from helpers.xpoz_fetcher import XpozFetcher
        except ImportError as e:
            print(f"ERROR: Could not import XpozFetcher: {e}")
            return {"error": str(e)}
        
        fetcher = XpozFetcher()
        
        # Test connection
        print("[Connecting to Xpoz...]")
        connected = await fetcher.connect()
        if not connected:
            print("ERROR: Could not connect to Xpoz")
            print("Note: Ensure ~/.xpoz/token.txt exists with valid token")
            return {"error": "Connection failed"}
        print("✓ Connected\n")
        
        all_results = {}
        
        try:
            for lens in TEST_LENSES:
                print(f"\n{'='*70}")
                print(f"Testing Lens: {lens}")
                print("=" * 70)
                
                result = await fetcher.fetch_for_lens(
                    lens_name=lens,
                    limit_per_platform=LIMIT_PER_PLATFORM
                )
                
                all_results[lens] = result
                self._print_lens_results(lens, result)
                
        finally:
            await fetcher.close()
        
        # Analyze results
        print(f"\n{'='*70}")
        print("ANALYSIS: Consumer Problem Detection Quality")
        print("=" * 70)
        
        analysis = self._analyze_results(all_results)
        self._print_analysis(analysis)
        
        # Save results
        output_dir = Path.home() / ".saas-idea-finder" / "outputs" / "baseline_test"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"baseline_test_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                "timestamp": datetime.now().isoformat(),
                "config": {
                    "lenses": TEST_LENSES,
                    "limit_per_platform": LIMIT_PER_PLATFORM
                },
                "results": all_results,
                "analysis": analysis
            }, f, indent=2, default=str)
        
        print(f"\n✓ Results saved to: {output_file}")
        
        return {
            "results": all_results,
            "analysis": analysis,
            "output_file": str(output_file)
        }
    
    def _print_lens_results(self, lens: str, result: Dict):
        """Print results for a single lens."""
        platforms = result.get("platforms", {})
        errors = result.get("errors", [])
        
        total_posts = sum(p.get("count", 0) for p in platforms.values())
        total_high_opportunity = sum(
            p.get("high_opportunity_count", 0) 
            for p in platforms.values()
        )
        
        print(f"\n📊 Platform Results:")
        for platform, data in platforms.items():
            count = data.get("count", 0)
            high_opp = data.get("high_opportunity_count", 0)
            ratio = (high_opp / count * 100) if count > 0 else 0
            print(f"  {platform:12} {count:3} posts | {high_opp:2} high-opp ({ratio:4.1f}%)")
        
        print(f"\n📈 Summary: {total_posts} total posts, {total_high_opportunity} high-opportunity")
        
        if errors:
            print(f"\n⚠️  Errors ({len(errors)}):")
            for err in errors:
                print(f"  - {err.get('platform')}: {err.get('error', 'Unknown')}")
        
        # Show top aggregated topics
        topics = result.get("aggregated_topics", [])
        if topics:
            print(f"\n🔥 Top Aggregated Topics:")
            for i, topic in enumerate(topics[:5], 1):
                platforms_str = ', '.join(topic.get('platforms', []))
                print(f"  {i}. {topic['topic'][:40]:40} "
                      f"(score: {topic['validation_score']:.1f}, "
                      f"platforms: {platforms_str})")
    
    def _analyze_results(self, all_results: Dict) -> Dict:
        """Analyze results across all lenses."""
        analysis = {
            "total_posts": 0,
            "total_high_opportunity": 0,
            "platform_breakdown": {},
            "lens_analysis": {},
            "consumer_problem_indicators": {
                "pain_point_mentions": 0,
                "question_mentions": 0,
                "wish_want_mentions": 0,
                "frustration_mentions": 0,
            },
            "quality_metrics": {
                "avg_posts_per_lens": 0,
                "high_opportunity_ratio": 0,
                "cross_platform_topics": 0,
            },
            "gaps_identified": []
        }
        
        for lens, result in all_results.items():
            platforms = result.get("platforms", {})
            topics = result.get("aggregated_topics", [])
            
            lens_total = sum(p.get("count", 0) for p in platforms.values())
            lens_high = sum(p.get("high_opportunity_count", 0) for p in platforms.values())
            
            analysis["total_posts"] += lens_total
            analysis["total_high_opportunity"] += lens_high
            
            # Platform breakdown
            for platform, data in platforms.items():
                if platform not in analysis["platform_breakdown"]:
                    analysis["platform_breakdown"][platform] = {
                        "total_posts": 0,
                        "high_opportunity": 0
                    }
                analysis["platform_breakdown"][platform]["total_posts"] += data.get("count", 0)
                analysis["platform_breakdown"][platform]["high_opportunity"] += data.get("high_opportunity_count", 0)
            
            # Lens-specific analysis
            analysis["lens_analysis"][lens] = {
                "total_posts": lens_total,
                "high_opportunity": lens_high,
                "high_opportunity_ratio": (lens_high / lens_total * 100) if lens_total > 0 else 0,
                "cross_platform_topics": sum(1 for t in topics if t.get("cross_platform_count", 0) >= 2),
                "top_topic": topics[0]["topic"] if topics else None
            }
            
            # Count cross-platform topics
            analysis["quality_metrics"]["cross_platform_topics"] += sum(
                1 for t in topics if t.get("cross_platform_count", 0) >= 2
            )
        
        # Calculate overall metrics
        num_lenses = len(all_results)
        if num_lenses > 0:
            analysis["quality_metrics"]["avg_posts_per_lens"] = analysis["total_posts"] / num_lenses
        
        if analysis["total_posts"] > 0:
            analysis["quality_metrics"]["high_opportunity_ratio"] = (
                analysis["total_high_opportunity"] / analysis["total_posts"] * 100
            )
        
        # Identify gaps
        self._identify_gaps(analysis, all_results)
        
        return analysis
    
    def _identify_gaps(self, analysis: Dict, all_results: Dict):
        """Identify gaps and improvement opportunities."""
        gaps = []
        
        # Check volume
        avg_posts = analysis["quality_metrics"]["avg_posts_per_lens"]
        if avg_posts < 30:
            gaps.append({
                "type": "low_volume",
                "severity": "medium",
                "description": f"Low post volume per lens ({avg_posts:.0f} avg). Consider increasing limit_per_platform or expanding query coverage."
            })
        
        # Check high-opportunity ratio
        opp_ratio = analysis["quality_metrics"]["high_opportunity_ratio"]
        if opp_ratio < 20:
            gaps.append({
                "type": "low_opportunity_ratio",
                "severity": "high",
                "description": f"Low high-opportunity ratio ({opp_ratio:.1f}%). Pain point detection may need refinement."
            })
        
        # Check cross-platform validation
        cross_plat = analysis["quality_metrics"]["cross_platform_topics"]
        if cross_plat < 3:
            gaps.append({
                "type": "low_cross_platform",
                "severity": "medium",
                "description": f"Few cross-platform topics ({cross_plat}). Topic aggregation may need tuning."
            })
        
        # Check platform coverage
        for lens, result in all_results.items():
            platforms = result.get("platforms", {})
            missing_platforms = []
            for expected in ["reddit", "twitter", "instagram"]:
                if expected not in platforms or platforms[expected].get("count", 0) == 0:
                    missing_platforms.append(expected)
            
            if missing_platforms:
                gaps.append({
                    "type": "missing_platform_data",
                    "severity": "medium",
                    "lens": lens,
                    "description": f"Lens '{lens}' missing data from: {', '.join(missing_platforms)}"
                })
        
        # Check for consumer-specific problem detection
        # This is a heuristic - we want to see if we're getting consumer problems
        consumer_keywords = ["wish", "frustrated", "tired", "annoying", "difficult", "expensive"]
        gaps.append({
            "type": "needs_content_analysis",
            "severity": "low",
            "description": "Content analysis needed to verify consumer vs developer problem detection ratio."
        })
        
        analysis["gaps_identified"] = gaps
    
    def _print_analysis(self, analysis: Dict):
        """Print analysis summary."""
        print(f"\n📊 OVERALL METRICS:")
        print(f"  Total posts collected: {analysis['total_posts']}")
        print(f"  Total high-opportunity: {analysis['total_high_opportunity']}")
        print(f"  Avg posts per lens: {analysis['quality_metrics']['avg_posts_per_lens']:.1f}")
        print(f"  High-opportunity ratio: {analysis['quality_metrics']['high_opportunity_ratio']:.1f}%")
        print(f"  Cross-platform topics: {analysis['quality_metrics']['cross_platform_topics']}")
        
        print(f"\n📈 PLATFORM BREAKDOWN:")
        for platform, data in analysis["platform_breakdown"].items():
            ratio = (data['high_opportunity'] / data['total_posts'] * 100) if data['total_posts'] > 0 else 0
            print(f"  {platform:12} {data['total_posts']:3} posts | {data['high_opportunity']:2} high-opp ({ratio:4.1f}%)")
        
        print(f"\n🔍 LENS-SPECIFIC ANALYSIS:")
        for lens, data in analysis["lens_analysis"].items():
            print(f"  {lens}:")
            print(f"    Posts: {data['total_posts']} | High-opp: {data['high_opportunity']} ({data['high_opportunity_ratio']:.1f}%)")
            print(f"    Cross-platform topics: {data['cross_platform_topics']}")
            if data['top_topic']:
                print(f"    Top topic: {data['top_topic'][:50]}")
        
        print(f"\n⚠️  GAPS IDENTIFIED ({len(analysis['gaps_identified'])}):")
        for gap in analysis["gaps_identified"]:
            severity_icon = "🔴" if gap["severity"] == "high" else "🟡" if gap["severity"] == "medium" else "🟢"
            print(f"  {severity_icon} [{gap['type']}] {gap['description']}")
        
        # Recommendations
        print(f"\n💡 RECOMMENDATIONS:")
        if any(g["type"] == "low_opportunity_ratio" for g in analysis["gaps_identified"]):
            print("  1. Refine pain point patterns for better consumer problem detection")
            print("  2. Consider adding sentiment analysis or emotion detection")
            print("  3. Add consumer-specific query terms (e.g., 'wasting money', 'too expensive')")
        
        if any(g["type"] == "missing_platform_data" for g in analysis["gaps_identified"]):
            print("  4. Review platform-specific queries for better coverage")
            print("  5. Consider adding platform-specific pain point patterns")
        
        if any(g["type"] == "low_volume" for g in analysis["gaps_identified"]):
            print("  6. Increase query breadth or result limits")


async def main():
    """Run baseline test."""
    runner = BaselineTestRunner()
    results = await runner.run_test()
    
    # Return exit code based on success
    if "error" in results:
        return 1
    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)