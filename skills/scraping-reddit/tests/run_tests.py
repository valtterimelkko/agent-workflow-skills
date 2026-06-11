#!/usr/bin/env python3
"""
Main Test Runner for Reddit Scraper Test Suite.

Runs all tests and generates a comprehensive report.

Usage:
    python3 tests/run_tests.py              # Run all tests
    python3 tests/run_tests.py --quick      # Skip API calls
    python3 tests/run_tests.py --analysis   # Analysis tests only
    python3 tests/run_tests.py --scraper    # Scraper tests only
"""
import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))


def run_analysis_tests():
    """Run analysis algorithm tests."""
    print("\n" + "=" * 70)
    print("RUNNING ANALYSIS TESTS")
    print("=" * 70)
    
    from tests.test_analysis import run_all_tests
    return run_all_tests()


def run_scraper_tests(skip_api=False):
    """Run scraper tests."""
    print("\n" + "=" * 70)
    print("RUNNING SCRAPER TESTS")
    print("=" * 70)
    
    from tests.test_scraper import run_scraper_tests
    return asyncio.run(run_scraper_tests(skip_api_calls=skip_api))


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Run Reddit scraper test suite")
    parser.add_argument('--quick', action='store_true',
                       help='Skip API calls (structural tests only)')
    parser.add_argument('--analysis', action='store_true',
                       help='Run only analysis tests')
    parser.add_argument('--scraper', action='store_true',
                       help='Run only scraper tests')
    args = parser.parse_args()
    
    results = {}
    
    # Determine which tests to run
    run_analysis = not args.scraper or args.analysis
    run_scraper = not args.analysis or args.scraper
    
    if run_analysis:
        results['analysis'] = run_analysis_tests()
    
    if run_scraper:
        results['scraper'] = run_scraper_tests(skip_api=args.quick)
    
    # Final summary
    print("\n" + "=" * 70)
    print("FINAL TEST SUMMARY")
    print("=" * 70)
    
    for test_suite, passed in results.items():
        status = "✓ PASSED" if passed else "✗ FAILED"
        print(f"  {test_suite.upper()}: {status}")
    
    all_passed = all(results.values())
    
    print("\n" + "=" * 70)
    if all_passed:
        print("ALL TEST SUITES PASSED ✓")
    else:
        print("SOME TEST SUITES FAILED ✗")
    print("=" * 70)
    
    return 0 if all_passed else 1


if __name__ == "__main__":
    sys.exit(main())