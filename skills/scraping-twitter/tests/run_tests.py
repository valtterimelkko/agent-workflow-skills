#!/usr/bin/env python3
"""Test runner for Twitter scraping skill."""
import sys
import os

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    """Run all tests."""
    print("Twitter Scraping Skill - Test Runner")
    print("="*60)
    
    # Import and run tests directly
    import test_scraper
    
    success = test_scraper.run_all_tests()
    
    if success:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1


if __name__ == "__main__":
    sys.exit(main())