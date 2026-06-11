#!/usr/bin/env python3
"""
Monitor Xpoz API usage and estimate costs.

Free tier: 100,000 results/month
Pro tier: $20/month for 1M results
"""
import json
from pathlib import Path
from datetime import datetime, timedelta


class XpozUsageMonitor:
    """Track and estimate Xpoz API usage.
    
    IMPORTANT: Xpoz Free tier is 5,000 ONE-TIME credits (not monthly, not 100K).
    Once used, credits do not refresh. Upgrade required for more.
    
    Credit calculation: Credits = (Queries × 5) + (Results × 0.005)
    Example: 100 queries + 100K results = 1,000 credits
    """

    FREE_TIER_LIMIT = 5_000  # One-time credits, not monthly!
    PRO_TIER_COST = 20  # USD per month for 30K credits
    PRO_TIER_LIMIT = 30_000  # Monthly for Pro plan
    MAX_TIER_COST = 200  # USD per month for 600K credits
    MAX_TIER_LIMIT = 600_000  # Monthly for Max plan

    def __init__(self):
        self.usage_file = Path.home() / ".xpoz" / "usage.json"
        self.usage = self._load_usage()

    def _load_usage(self) -> dict:
        """Load usage data from file."""
        if self.usage_file.exists():
            return json.loads(self.usage_file.read_text())
        return {"daily": {}, "total_this_month": 0}

    def _save_usage(self):
        """Save usage data to file."""
        self.usage_file.parent.mkdir(exist_ok=True)
        self.usage_file.write_text(json.dumps(self.usage, indent=2))

    def log_request(self, results_count: int):
        """Log an API request."""
        today = datetime.now().strftime("%Y-%m-%d")
        month = datetime.now().strftime("%Y-%m")

        if "monthly" not in self.usage:
            self.usage["monthly"] = {}

        if month not in self.usage["monthly"]:
            self.usage["monthly"][month] = 0

        self.usage["daily"][today] = self.usage["daily"].get(today, 0) + results_count
        self.usage["monthly"][month] += results_count
        self._save_usage()

    def get_usage_report(self) -> dict:
        """Get usage statistics."""
        month = datetime.now().strftime("%Y-%m")
        monthly_usage = self.usage.get("monthly", {}).get(month, 0)

        return {
            "current_month": month,
            "usage_this_month": monthly_usage,
            "free_tier_limit": self.FREE_TIER_LIMIT,
            "usage_percent": round(monthly_usage / self.FREE_TIER_LIMIT * 100, 1),
            "remaining": max(0, self.FREE_TIER_LIMIT - monthly_usage),
            "needs_upgrade": monthly_usage > self.FREE_TIER_LIMIT * 0.9,
            "estimated_monthly_cost": self._estimate_cost(monthly_usage)
        }

    def _estimate_cost(self, usage: int) -> float:
        """Estimate monthly cost based on usage."""
        if usage <= self.FREE_TIER_LIMIT:
            return 0.0
        else:
            return self.PRO_TIER_COST

    def estimate_daily_usage(self) -> dict:
        """Estimate usage based on pipeline configuration.
        
        Uses Xpoz credit formula: Credits = (Queries × 5) + (Results × 0.005)
        """
        # Estimated usage per day
        lenses_per_day = 1  # 1 lens runs per day
        platforms_per_lens = 3  # Reddit, Twitter, Instagram (TikTok not available)
        queries_per_platform = 5  # Average queries per platform
        results_per_query = 30  # Average results per query
        
        # Calculate credits using Xpoz formula
        total_queries = lenses_per_day * platforms_per_lens * queries_per_platform
        total_results = total_queries * results_per_query
        daily_credits = (total_queries * 5) + (total_results * 0.005)
        
        monthly_estimate = daily_credits * 30

        return {
            "daily_estimate_credits": round(daily_credits, 2),
            "monthly_estimate_credits": round(monthly_estimate, 2),
            "queries_per_day": total_queries,
            "results_per_day": total_results,
            "within_free_tier": monthly_estimate <= self.FREE_TIER_LIMIT,
            "free_tier_percent": round(monthly_estimate / self.FREE_TIER_LIMIT * 100, 1),
            "free_tier_note": "FREE CREDITS ARE ONE-TIME ONLY AND DO NOT REFRESH"
        }

    def estimate_for_lens(self, lens_name: str, platforms: list = None) -> dict:
        """Estimate usage for a specific lens run."""
        if platforms is None:
            platforms = ["reddit", "twitter", "instagram"]
        
        queries_per_platform = {
            "reddit": 5,      # Subreddit searches
            "twitter": 3,     # Hashtag searches
            "instagram": 4,   # Hashtag searches
        }
        
        results_per_query = 30
        
        total_queries = sum(queries_per_platform.get(p, 5) for p in platforms)
        total_results = total_queries * results_per_query
        
        return {
            "lens": lens_name,
            "platforms": platforms,
            "estimated_queries": total_queries,
            "estimated_results": total_results,
            "percent_of_free_tier": round(total_results / self.FREE_TIER_LIMIT * 100, 2)
        }


def main():
    """Print usage report."""
    print("=" * 60)
    print("Xpoz API Usage Report")
    print("=" * 60)
    print("\n⚠️  IMPORTANT: Free tier = 5,000 ONE-TIME credits (not monthly!)")
    print("   Credits do NOT refresh. Once used, you must upgrade for more.")

    monitor = XpozUsageMonitor()

    # Current usage
    report = monitor.get_usage_report()
    print(f"\nCurrent Status:")
    print(f"  Credits Used: {report['usage_this_month']:,}")
    print(f"  Total Credits (Free): {report['free_tier_limit']:,}")
    print(f"  Remaining: {report['remaining']:,}")
    print(f"  Usage: {report['usage_percent']}%")

    if report['remaining'] < 1000:
        print("\n🔴 WARNING: Running low on credits!")
        print("   Consider upgrading to Pro ($20/month for 30K credits)")
    elif report['usage_percent'] > 50:
        print("\n🟡 Note: You've used over 50% of free credits")
    else:
        print("\n🟢 Good: You have plenty of credits remaining")

    # Estimate
    estimate = monitor.estimate_daily_usage()
    print(f"\n--- Estimated Usage (Daily Pipeline) ---")
    print(f"Formula: Credits = (Queries × 5) + (Results × 0.005)")
    print(f"Daily: ~{estimate['queries_per_day']} queries, ~{estimate['results_per_day']} results")
    print(f"Daily Credits: ~{estimate['daily_estimate_credits']}")
    print(f"Monthly Credits: ~{estimate['monthly_estimate_credits']}")
    print(f"Free Tier Usage: {estimate['free_tier_percent']}%")
    print(f"Note: {estimate['free_tier_note']}")

    if estimate['within_free_tier']:
        print("\n✅ Current configuration fits within free tier.")
    else:
        print("\n⚠️  WARNING: Estimated usage exceeds free tier!")
        print("   You'll need to upgrade before running this configuration.")

    # Upgrade recommendation
    print("\n--- Upgrade Options ---")
    print("Pro: $20/month for 30,000 credits/month")
    print("Max: $200/month for 600,000 credits/month")
    print("\nWith current usage (341 credits), you have ~4,659 free credits remaining.")
    print("That's enough for approximately 30-40 lens runs before upgrading.")

    print("\n" + "=" * 60)


if __name__ == "__main__":
    main()