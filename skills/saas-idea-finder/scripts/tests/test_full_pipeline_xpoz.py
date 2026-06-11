#!/usr/bin/env python3
"""
FULL PIPELINE TEST - Xpoz Integration

This test runs a complete pipeline with Xpoz integration using proper
timeouts for async operations. Tests 2 consumer-focused lenses to
verify quality of consumer problem detection.

Estimated runtime: 5-10 minutes
Estimated credit usage: ~150-200 credits
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


class FullPipelineTest:
    """Runs full pipeline test with comprehensive output."""
    
    def __init__(self):
        self.results = {}
        self.start_time = None
        
    async def run_test(self):
        """Run the full pipeline test."""
        self.start_time = datetime.now()
        
        print("=" * 80)
        print("FULL PIPELINE TEST - Xpoz Social Media Integration")
        print("=" * 80)
        print(f"Start Time: {self.start_time.isoformat()}")
        print(f"\nEstimated Runtime: 5-10 minutes")
        print(f"Estimated Credit Usage: ~150-200 credits")
        print(f"Your Current Balance: ~4,659 credits")
        print(f"\nTesting 2 consumer-focused lenses:")
        print("  1. ecommerce_sellers (Tuesday lens - high consumer problem density)")
        print("  2. small_business_ops (Friday lens - small business pain points)")
        print("\n" + "=" * 80)
        
        fetcher = XpozFetcher()
        
        # Test connection
        print("\n[PHASE 1/4] Connecting to Xpoz MCP...")
        connected = await fetcher.connect()
        if not connected:
            print("❌ FAILED: Could not connect to Xpoz")
            return False
        print("✓ Connected successfully")
        
        all_results = {}
        
        try:
            # Test Lens 1: ecommerce_sellers
            print("\n" + "=" * 80)
            print("[PHASE 2/4] Testing Lens: ecommerce_sellers")
            print("=" * 80)
            print("Platforms: Reddit, Twitter, Instagram")
            print("Limit per platform: 15 posts")
            print("This tests consumer problem detection for e-commerce sellers...")
            print()
            
            lens1_start = datetime.now()
            result1 = await fetcher.fetch_for_lens(
                lens_name="ecommerce_sellers",
                limit_per_platform=15
            )
            lens1_duration = (datetime.now() - lens1_start).total_seconds()
            
            all_results['ecommerce_sellers'] = result1
            self._print_lens_results("ecommerce_sellers", result1, lens1_duration)
            
            # Test Lens 2: small_business_ops
            print("\n" + "=" * 80)
            print("[PHASE 3/4] Testing Lens: small_business_ops")
            print("=" * 80)
            print("Platforms: Reddit, Twitter, Instagram")
            print("Limit per platform: 15 posts")
            print("This tests consumer problem detection for small business operations...")
            print()
            
            lens2_start = datetime.now()
            result2 = await fetcher.fetch_for_lens(
                lens_name="small_business_ops",
                limit_per_platform=15
            )
            lens2_duration = (datetime.now() - lens2_start).total_seconds()
            
            all_results['small_business_ops'] = result2
            self._print_lens_results("small_business_ops", result2, lens2_duration)
            
        finally:
            await fetcher.close()
        
        # Analysis
        print("\n" + "=" * 80)
        print("[PHASE 4/4] COMPREHENSIVE ANALYSIS")
        print("=" * 80)
        
        analysis = self._analyze_results(all_results)
        self._print_analysis(analysis)
        
        # Save results
        output_dir = Path.home() / ".saas-idea-finder" / "outputs" / "full_pipeline_test"
        output_dir.mkdir(parents=True, exist_ok=True)
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"full_pipeline_test_{timestamp}.json"
        
        with open(output_file, 'w') as f:
            json.dump({
                "test_type": "full_pipeline_xpoz",
                "timestamp": datetime.now().isoformat(),
                "duration_seconds": (datetime.now() - self.start_time).total_seconds(),
                "config": {
                    "lenses_tested": ["ecommerce_sellers", "small_business_ops"],
                    "limit_per_platform": 15,
                    "platforms": ["reddit", "twitter", "instagram"]
                },
                "results": all_results,
                "analysis": analysis
            }, f, indent=2, default=str)
        
        print(f"\n✓ Full results saved to: {output_file}")
        
        return analysis
    
    def _print_lens_results(self, lens: str, result: dict, duration: float):
        """Print results for a single lens."""
        platforms = result.get("platforms", {})
        errors = result.get("errors", [])
        topics = result.get("aggregated_topics", [])
        
        total_posts = sum(p.get("count", 0) for p in platforms.values())
        total_high_opp = sum(p.get("high_opportunity_count", 0) for p in platforms.values())
        consumer_problems = sum(1 for t in topics if t.get("is_consumer_problem"))
        
        print(f"\n📊 Results for '{lens}' (completed in {duration:.1f}s):")
        print(f"\n   Platform Breakdown:")
        for platform, data in platforms.items():
            count = data.get("count", 0)
            high = data.get("high_opportunity_count", 0)
            ratio = (high / count * 100) if count > 0 else 0
            print(f"     {platform:12} {count:3} posts | {high:2} high-opp ({ratio:4.1f}%)")
        
        print(f"\n   Summary:")
        print(f"     Total posts: {total_posts}")
        print(f"     High-opportunity: {total_high_opp}")
        print(f"     Aggregated topics: {len(topics)}")
        print(f"     Consumer problems: {consumer_problems}")
        
        if errors:
            print(f"\n   ⚠️  Errors ({len(errors)}):")
            for err in errors:
                print(f"       - {err.get('platform')}: {err.get('error', 'Unknown')}")
        
        # Show top topics
        if topics:
            print(f"\n   🔥 Top Topics:")
            for i, topic in enumerate(topics[:5], 1):
                consumer_flag = " [CONSUMER]" if topic.get("is_consumer_problem") else ""
                print(f"     {i}. {topic['topic'][:45]:45} "
                      f"(score: {topic['validation_score']:.1f}){consumer_flag}")
        
        # Show sample consumer problems if any
        consumer_topics = [t for t in topics if t.get("is_consumer_problem")]
        if consumer_topics:
            print(f"\n   💡 Consumer Problem Insights:")
            for topic in consumer_topics[:3]:
                cat = topic.get('consumer_category', 'general')
                print(f"     - {cat.upper()}: {topic['topic'][:50]}")
    
    def _analyze_results(self, all_results: dict) -> dict:
        """Analyze results across all lenses."""
        analysis = {
            "total_posts": 0,
            "total_high_opportunity": 0,
            "total_consumer_problems": 0,
            "platform_performance": {},
            "consumer_problem_categories": {},
            "pain_point_quality": {},
            "cross_platform_validation": 0,
            "value_assessment": {}
        }
        
        for lens, result in all_results.items():
            platforms = result.get("platforms", {})
            topics = result.get("aggregated_topics", [])
            
            # Count totals
            lens_posts = sum(p.get("count", 0) for p in platforms.values())
            lens_high = sum(p.get("high_opportunity_count", 0) for p in platforms.values())
            
            analysis["total_posts"] += lens_posts
            analysis["total_high_opportunity"] += lens_high
            
            # Platform performance
            for platform, data in platforms.items():
                if platform not in analysis["platform_performance"]:
                    analysis["platform_performance"][platform] = {
                        "total_posts": 0, "high_opportunity": 0
                    }
                analysis["platform_performance"][platform]["total_posts"] += data.get("count", 0)
                analysis["platform_performance"][platform]["high_opportunity"] += data.get("high_opportunity_count", 0)
            
            # Consumer problem analysis
            for topic in topics:
                if topic.get("is_consumer_problem"):
                    analysis["total_consumer_problems"] += 1
                    cat = topic.get("consumer_category", "general")
                    analysis["consumer_problem_categories"][cat] = \
                        analysis["consumer_problem_categories"].get(cat, 0) + 1
                
                # Cross-platform validation
                if topic.get("cross_platform_count", 0) >= 2:
                    analysis["cross_platform_validation"] += 1
        
        # Calculate quality metrics
        if analysis["total_posts"] > 0:
            analysis["pain_point_quality"]["high_opportunity_ratio"] = \
                (analysis["total_high_opportunity"] / analysis["total_posts"]) * 100
        
        # Value assessment
        analysis["value_assessment"] = self._assess_value(analysis)
        
        return analysis
    
    def _assess_value(self, analysis: dict) -> dict:
        """Assess the value of Xpoz integration."""
        assessment = {
            "consumer_problem_detection": "UNKNOWN",
            "cross_platform_insights": "UNKNOWN",
            "saas_opportunity_potential": "UNKNOWN",
            "recommendation": ""
        }
        
        # Consumer problem detection quality
        consumer_ratio = analysis["total_consumer_problems"] / max(analysis["total_posts"] / 50, 1)
        if consumer_ratio >= 0.3:
            assessment["consumer_problem_detection"] = "EXCELLENT"
        elif consumer_ratio >= 0.15:
            assessment["consumer_problem_detection"] = "GOOD"
        else:
            assessment["consumer_problem_detection"] = "NEEDS_IMPROVEMENT"
        
        # Cross-platform validation
        if analysis["cross_platform_validation"] >= 5:
            assessment["cross_platform_insights"] = "STRONG"
        elif analysis["cross_platform_validation"] >= 2:
            assessment["cross_platform_insights"] = "MODERATE"
        else:
            assessment["cross_platform_insights"] = "WEAK"
        
        # Overall SaaS opportunity potential
        high_opp_ratio = analysis["pain_point_quality"].get("high_opportunity_ratio", 0)
        if high_opp_ratio >= 30 and assessment["consumer_problem_detection"] in ["EXCELLENT", "GOOD"]:
            assessment["saas_opportunity_potential"] = "HIGH"
            assessment["recommendation"] = "Xpoz integration provides significant value - WORTH PAYING FOR"
        elif high_opp_ratio >= 20:
            assessment["saas_opportunity_potential"] = "MODERATE"
            assessment["recommendation"] = "Xpoz adds value but may need refinement - CONSIDER PRO TIER"
        else:
            assessment["saas_opportunity_potential"] = "LOW"
            assessment["recommendation"] = "Current configuration needs optimization before paying"
        
        return assessment
    
    def _print_analysis(self, analysis: dict):
        """Print comprehensive analysis."""
        print(f"\n📈 OVERALL METRICS:")
        print(f"   Total posts collected: {analysis['total_posts']}")
        print(f"   Total high-opportunity: {analysis['total_high_opportunity']}")
        print(f"   Consumer problems identified: {analysis['total_consumer_problems']}")
        print(f"   Cross-platform topics: {analysis['cross_platform_validation']}")
        
        print(f"\n📊 PLATFORM PERFORMANCE:")
        for platform, data in analysis["platform_performance"].items():
            ratio = (data['high_opportunity'] / data['total_posts'] * 100) if data['total_posts'] > 0 else 0
            print(f"   {platform:12} {data['total_posts']:3} posts | {data['high_opportunity']:2} high-opp ({ratio:4.1f}%)")
        
        print(f"\n🎯 CONSUMER PROBLEM BREAKDOWN:")
        for category, count in sorted(analysis["consumer_problem_categories"].items(), key=lambda x: x[1], reverse=True):
            print(f"   {category}: {count} problems")
        
        print(f"\n✨ VALUE ASSESSMENT:")
        va = analysis["value_assessment"]
        print(f"   Consumer Problem Detection: {va['consumer_problem_detection']}")
        print(f"   Cross-Platform Insights: {va['cross_platform_insights']}")
        print(f"   SaaS Opportunity Potential: {va['saas_opportunity_potential']}")
        
        print(f"\n💰 RECOMMENDATION:")
        print(f"   {va['recommendation']}")
        
        # Credit usage estimate
        print(f"\n💳 CREDIT USAGE ESTIMATE:")
        estimated_credits = 150  # Rough estimate for 2 lenses
        print(f"   This test used approximately: ~{estimated_credits} credits")
        print(f"   Remaining balance: ~{4659 - estimated_credits} credits")
        print(f"   Remaining lens runs at this rate: ~{(4659 - estimated_credits) // 75}")


async def main():
    """Run the full pipeline test."""
    test = FullPipelineTest()
    analysis = await test.run_test()
    
    if analysis and analysis.get("value_assessment", {}).get("saas_opportunity_potential") in ["HIGH", "MODERATE"]:
        print("\n" + "=" * 80)
        print("✅ TEST SUCCESSFUL - Xpoz integration provides value")
        print("=" * 80)
        return 0
    elif analysis:
        print("\n" + "=" * 80)
        print("⚠️  TEST COMPLETED - Review recommendations above")
        print("=" * 80)
        return 0
    else:
        print("\n" + "=" * 80)
        print("❌ TEST FAILED - Check errors above")
        print("=" * 80)
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))