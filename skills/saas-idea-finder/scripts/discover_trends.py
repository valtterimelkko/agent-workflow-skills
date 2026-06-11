#!/usr/bin/env python3
"""
Stage 1: Discover Trends

Aggregates trending topics from multiple sources (HackerNews, Reddit, GitHub, DEV.to, HN Algolia)
using the active lens to filter and score results.
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Any
from collections import Counter

# Robust path resolution for imports (works from any working directory)
SCRIPT_DIR = Path(__file__).parent.resolve()
SKILL_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(SCRIPT_DIR))  # For helpers
sys.path.insert(0, str(SKILL_ROOT))  # For skill modules

# Add shared directory to path for credentials and GitHub API
SHARED_DIR = Path(__file__).resolve().parents[3] / 'shared'
sys.path.insert(0, str(SHARED_DIR))
sys.path.insert(0, str(SHARED_DIR / 'github'))

from helpers.lens_manager import LensManager
from helpers.state_manager import StateManager
from helpers.hackernews_fetcher import HackerNewsFetcher
from helpers.devto_fetcher import DevToFetcher
from helpers.hn_algolia_fetcher import HNAlgoliaFetcher
from helpers.newsapi_fetcher import NewsAPIFetcher
from helpers.producthunt_fetcher import ProductHuntFetcher
from helpers.output_formatter import format_success_json, format_error_json
from helpers.topic_extractor import TopicExtractor

# New fetchers
from helpers.arxiv_fetcher import ArxivFetcher
from helpers.stackexchange_fetcher import StackExchangeFetcher
from helpers.gdelt_fetcher import GDELTFetcher
from helpers.serpapi_fetcher import SerpAPIFetcher
from helpers.youtube_fetcher import YouTubeFetcher

# Social media fetcher (TwitterAPI.io + Xpoz for Instagram)
try:
    from helpers.xpoz_fetcher import SocialMediaFetcherSync, fetch_from_social_media
    SOCIAL_MEDIA_AVAILABLE = True
except ImportError:
    SOCIAL_MEDIA_AVAILABLE = False

try:
    from github_api import make_github_request, GitHubAPIError
    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    print("Warning: GitHub API not available", file=sys.stderr)


def fetch_from_hackernews(lens: Dict[str, Any], since_days: int) -> List[Dict[str, Any]]:
    """Fetch trending topics from HackerNews."""
    try:
        fetcher = HackerNewsFetcher()

        # Get top stories (uses adaptive scoring based on time window)
        top_stories = fetcher.get_top_stories(min_score=None, since_days=since_days, limit=25)

        # Get Show HN (product launches)
        show_hn = fetcher.get_show_hn_stories(since_days=since_days, limit=15)

        # Get Ask HN (pain points)
        ask_hn = fetcher.get_ask_hn_stories(since_days=since_days, limit=15)

        # Combine and deduplicate
        all_stories = top_stories + show_hn + ask_hn
        seen_ids = set()
        unique_stories = []
        for story in all_stories:
            if story['id'] not in seen_ids:
                seen_ids.add(story['id'])
                unique_stories.append(story)

        return unique_stories

    except Exception as e:
        print(f"HackerNews fetch error: {e}", file=sys.stderr)
        return []


def fetch_from_github(lens: Dict[str, Any], since_days: int) -> List[Dict[str, Any]]:
    """Fetch trending repos from GitHub."""
    if not GITHUB_AVAILABLE:
        return []

    try:
        github_filters = lens.get('github_filters', {})
        languages = github_filters.get('languages', [])
        topics = github_filters.get('topics', [])

        # GitHub search API doesn't support OR for language qualifier
        # So we search each language separately and combine results
        all_repos = []
        seen_ids = set()

        # Search by each language (up to 3)
        for lang in languages[:3]:
            query = f'language:{lang} stars:>50'
            
            try:
                response = make_github_request(
                    '/search/repositories',
                    params={
                        'q': query,
                        'sort': 'stars',
                        'order': 'desc',
                        'per_page': 10
                    }
                )

                for repo in response.get('items', []):
                    repo_id = repo['id']
                    if repo_id not in seen_ids:
                        seen_ids.add(repo_id)
                        all_repos.append({
                            'id': repo_id,
                            'name': repo['full_name'],
                            'description': repo.get('description', ''),
                            'url': repo['html_url'],
                            'stars': repo['stargazers_count'],
                            'language': repo.get('language', 'Unknown'),
                            'topics': repo.get('topics', [])
                        })
            except GitHubAPIError:
                # Continue to next language if one fails
                continue

        # Also try topic-based search if we have topics
        if topics and len(all_repos) < 10:
            topic_query = ' OR '.join([f'topic:{topic}' for topic in topics[:2]])
            query = f'({topic_query}) stars:>100'
            
            try:
                response = make_github_request(
                    '/search/repositories',
                    params={
                        'q': query,
                        'sort': 'stars',
                        'order': 'desc',
                        'per_page': 10
                    }
                )

                for repo in response.get('items', []):
                    repo_id = repo['id']
                    if repo_id not in seen_ids:
                        seen_ids.add(repo_id)
                        all_repos.append({
                            'id': repo_id,
                            'name': repo['full_name'],
                            'description': repo.get('description', ''),
                            'url': repo['html_url'],
                            'stars': repo['stargazers_count'],
                            'language': repo.get('language', 'Unknown'),
                            'topics': repo.get('topics', [])
                        })
            except GitHubAPIError:
                pass

        # Sort by stars
        all_repos.sort(key=lambda x: x['stars'], reverse=True)
        return all_repos[:30]

    except Exception as e:
        print(f"GitHub fetch error: {e}", file=sys.stderr)
        return []


def fetch_from_devto(lens: Dict[str, Any], since_days: int) -> List[Dict[str, Any]]:
    """Fetch trending articles from DEV.to."""
    try:
        fetcher = DevToFetcher()
        lens_manager = LensManager()

        # Get DEV.to tags for this lens
        tags = lens_manager.get_devto_tags(lens['name'])

        if not tags:
            # Fallback to top posts without tags
            posts = fetcher.get_trending_posts(days=since_days, limit=20)
        else:
            # Get posts by lens-specific tags
            posts = fetcher.get_posts_by_tags(
                tags=tags,
                days=since_days,
                limit_per_tag=5
            )

        return posts

    except Exception as e:
        print(f"DEV.to fetch error: {e}", file=sys.stderr)
        return []


def fetch_from_hn_algolia(lens: Dict[str, Any], since_days: int) -> List[Dict[str, Any]]:
    """Fetch keyword-based trending from HN Algolia API."""
    try:
        fetcher = HNAlgoliaFetcher()
        lens_manager = LensManager()

        # Get HN Algolia keywords for this lens
        keywords = lens_manager.get_hn_algolia_keywords(lens['name'])

        if not keywords:
            return []

        # Search for trending stories matching keywords
        stories = fetcher.get_trending_by_lens(
            lens_keywords=keywords,
            days_back=since_days,
            limit=20
        )

        return stories

    except Exception as e:
        print(f"HN Algolia fetch error: {e}", file=sys.stderr)
        return []


def fetch_from_newsapi(lens: Dict[str, Any], since_days: int) -> List[Dict[str, Any]]:
    """Fetch trending news from NewsAPI."""
    try:
        fetcher = NewsAPIFetcher()
        lens_manager = LensManager()

        # Get NewsAPI configuration for this lens
        category = lens_manager.get_newsapi_category(lens['name'])
        keywords = lens_manager.get_newsapi_keywords(lens['name'])

        articles = []

        # Try category-based fetch first
        if category:
            articles = fetcher.get_top_headlines(
                category=category,
                page_size=15
            )

        # If no articles or no category, try keyword-based search
        if not articles and keywords:
            articles = fetcher.get_trending_by_keywords(
                keywords=keywords,
                days_back=since_days,
                limit_per_keyword=5
            )

        return articles

    except ValueError as e:
        # API key not configured
        print(f"NewsAPI not configured: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"NewsAPI fetch error: {e}", file=sys.stderr)
        return []


def fetch_from_producthunt(lens: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch trending products from Product Hunt."""
    try:
        fetcher = ProductHuntFetcher()
        lens_manager = LensManager()

        # Get Product Hunt topics for this lens
        topics = lens_manager.get_producthunt_topics(lens['name'])

        posts = []

        if topics:
            # Fetch posts for lens-specific topics
            posts = fetcher.get_posts_for_lens(
                lens_topics=topics,
                limit_per_topic=5
            )
        else:
            # Fallback to today's featured posts
            posts = fetcher.get_todays_posts(first=10)

        return posts

    except ValueError as e:
        # Token not configured
        print(f"Product Hunt not configured: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Product Hunt fetch error: {e}", file=sys.stderr)
        return []


def fetch_from_arxiv(lens: Dict[str, Any], since_days: int) -> List[Dict[str, Any]]:
    """Fetch research trends from arXiv."""
    try:
        fetcher = ArxivFetcher()
        lens_manager = LensManager()

        # Get arXiv categories for this lens
        categories = lens_manager.get_arxiv_categories(lens['name'])

        papers = []

        if categories:
            # Fetch papers by category
            papers = fetcher.get_recent_by_category(
                category=categories[0],
                max_results=10
            )

        return papers

    except ValueError as e:
        print(f"arXiv not configured: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"arXiv fetch error: {e}", file=sys.stderr)
        return []


def fetch_from_stackexchange(lens: Dict[str, Any], since_days: int) -> List[Dict[str, Any]]:
    """Fetch unanswered questions from Stack Exchange."""
    try:
        fetcher = StackExchangeFetcher()
        lens_manager = LensManager()

        # Get Stack Exchange tags for this lens
        tags = lens_manager.get_stackexchange_tags(lens['name'])

        questions = []

        if tags:
            # Fetch unanswered questions by tags
            questions = fetcher.get_unanswered_questions(
                tags=tags,
                days=since_days,
                limit=10
            )

        return questions

    except ValueError as e:
        print(f"Stack Exchange not configured: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"Stack Exchange fetch error: {e}", file=sys.stderr)
        return []


def fetch_from_gdelt(lens: Dict[str, Any], since_days: int) -> List[Dict[str, Any]]:
    """Fetch global news trends from GDELT."""
    try:
        fetcher = GDELTFetcher()
        lens_manager = LensManager()

        # Get GDELT themes for this lens
        themes = lens_manager.get_gdelt_themes(lens['name'])

        events = []

        if themes:
            # Fetch mentions by themes
            events = fetcher.get_mentions_by_theme(
                themes=themes,
                days=since_days,
                limit=10
            )

        return events

    except ValueError as e:
        print(f"GDELT not configured: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"GDELT fetch error: {e}", file=sys.stderr)
        return []


def fetch_from_serpapi(lens: Dict[str, Any], since_days: int) -> List[Dict[str, Any]]:
    """Fetch search trends from SerpAPI."""
    try:
        fetcher = SerpAPIFetcher()
        lens_manager = LensManager()

        # Get SerpAPI search keywords for this lens
        keywords = lens_manager.get_serpapi_keywords(lens['name'])

        trends = []

        if keywords:
            # Fetch trending searches (limit to first keyword to save quota)
            trends = fetcher.get_trending_searches(
                keywords=[keywords[0]],
                limit=5
            )

        return trends

    except ValueError as e:
        print(f"SerpAPI not configured: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"SerpAPI fetch error: {e}", file=sys.stderr)
        return []


def fetch_from_youtube(lens: Dict[str, Any], since_days: int) -> List[Dict[str, Any]]:
    """Fetch trending tech videos from YouTube with caption enrichment.
    
    Fetches top 10 videos and enriches top 5 with captions for pain point extraction.
    Timing: ~2-3s for search + ~5-10s for caption fetching = ~8-12s total.
    """
    try:
        fetcher = YouTubeFetcher()
        lens_manager = LensManager()

        # Get YouTube search queries for this lens
        queries = lens_manager.get_youtube_queries(lens['name'])

        videos = []

        if queries:
            # Search videos by first query (limit to save quota)
            videos = fetcher.search_tech_videos(
                query=queries[0],
                max_results=10
            )
            
            # Enrich top videos with captions for pain point extraction
            if videos:
                videos = fetcher.enrich_videos_with_captions(videos, max_videos=5)

        return videos

    except ValueError as e:
        print(f"YouTube not configured: {e}", file=sys.stderr)
        return []
    except Exception as e:
        print(f"YouTube fetch error: {e}", file=sys.stderr)
        return []


def fetch_from_social_media(lens: Dict[str, Any], limit: int = 30) -> List[Dict[str, Any]]:
    """Fetch trending topics from social media (TwitterAPI.io + Xpoz)."""
    if not SOCIAL_MEDIA_AVAILABLE:
        return []

    try:
        fetcher = SocialMediaFetcherSync()
        return fetcher.fetch_social_trends(lens, limit)
    except Exception as e:
        print(f"Social media fetch error: {e}", file=sys.stderr)
        return []


# Backward compatibility alias
fetch_from_xpoz_social = fetch_from_social_media


def extract_topics_from_sources(
    hn_stories: List[Dict],
    github_repos: List[Dict],
    devto_posts: List[Dict],
    hn_algolia_stories: List[Dict],
    newsapi_articles: List[Dict],
    producthunt_posts: List[Dict],
    arxiv_papers: List[Dict],
    stackexchange_questions: List[Dict],
    gdelt_events: List[Dict],
    serpapi_trends: List[Dict],
    youtube_videos: List[Dict],
    xpoz_topics: List[Dict] = None
) -> List[Dict[str, Any]]:
    """
    Extract and aggregate topics from all sources using enhanced topic extraction.
    
    Uses TopicExtractor for:
    - Smart deduplication
    - Better scoring
    - SaaS opportunity filtering
    """
    extractor = TopicExtractor()
    
    # Use the enhanced topic extraction
    topics = extractor.extract_topics_from_sources(
        hn_stories,
        github_repos,
        devto_posts,
        hn_algolia_stories,
        newsapi_articles,
        producthunt_posts,
        arxiv_papers,
        stackexchange_questions,
        gdelt_events,
        serpapi_trends,
        youtube_videos
    )
    
    # Merge Xpoz/social topics if available
    if xpoz_topics:
        # Convert xpoz topics to Topic objects
        from helpers.topic_extractor import Topic
        for xt in xpoz_topics:
            social_topic = Topic(
                name=xt.get('name', ''),
                sources=[{'type': xt.get('source', 'social_media'), 'url': xt.get('url', '')}],
                urls=[xt.get('url', '')] if xt.get('url') else [],
                engagement=xt.get('engagement', 0),
                score=xt.get('score', 0),
                is_social=True
            )
            topics.append(social_topic)
    
    # Deduplicate topics
    topics = extractor.deduplicate_topics(topics, threshold=0.7)
    
    # Filter to likely SaaS opportunities
    opportunities, filtered = extractor.filter_saas_opportunities(
        topics, 
        require_multi_source=True
    )
    
    # Log filtered topics for debugging
    if filtered:
        print(f"\n📊 Filtered out {len(filtered)} non-SaaS topics:")
        for topic, reason in filtered[:5]:  # Show first 5
            print(f"   - '{topic.name[:50]}...' ({reason})")
        if len(filtered) > 5:
            print(f"   ... and {len(filtered) - 5} more")
    
    # Convert back to dictionary format
    return extractor.format_for_output(opportunities)


def main():
    parser = argparse.ArgumentParser(
        description='Discover trending topics from multiple sources',
        epilog="""
TIMING EXPECTATIONS:
- Total runtime: ~30-60 seconds
- HackerNews/Dev.to/HN Algolia: ~2-3s each
- GitHub/NewsAPI/ProductHunt/arXiv/StackExchange: ~2-3s each  
- GDELT/SerpAPI: ~2-3s each (may timeout)
- YouTube: ~2-3s
- Reddit: ~18-25s (4 subreddits, sequential with rate limits)
- Twitter/X: ~15-25s (8 queries, parallel with 15s timeout)

If execution exceeds 90 seconds, check network connectivity or API status.
        """
    )
    parser.add_argument('--lens', help='Override lens (default: day-of-week rotation)')
    parser.add_argument('--force', action='store_true', help='Ignore deduplication')
    parser.add_argument('--output', help='Output file path')
    parser.add_argument('--limit', type=int, default=10, help='Max topics to return')
    parser.add_argument('--since', type=int, default=7, help='Look back N days')

    args = parser.parse_args()

    try:
        import time
        start_time = time.time()
        
        # Initialize managers
        lens_manager = LensManager()
        state_manager = StateManager()

        # Get active lens
        lens = lens_manager.get_active_lens(override=args.lens)
        lens_name = lens['name']

        print(f"🔍 Discovering trends with lens: {lens_name}")
        print(f"📅 Looking back: {args.since} days")
        print(f"⏱️  Expected runtime: ~30-60 seconds")

        # Fetch from all sources
        sources_used = []
        sources_failed = []

        print("\n🌐 Fetching from HackerNews...")
        hn_stories = fetch_from_hackernews(lens, args.since)
        if hn_stories:
            sources_used.append('hackernews')
            print(f"   ✓ Found {len(hn_stories)} stories")
        else:
            sources_failed.append('hackernews')

        print("🌐 Fetching from GitHub...")
        github_repos = fetch_from_github(lens, args.since)
        if github_repos:
            sources_used.append('github')
            print(f"   ✓ Found {len(github_repos)} repos")
        else:
            sources_failed.append('github')

        print("🌐 Fetching from DEV.to...")
        devto_posts = fetch_from_devto(lens, args.since)
        if devto_posts:
            sources_used.append('devto')
            print(f"   ✓ Found {len(devto_posts)} posts")
        else:
            sources_failed.append('devto')

        print("🌐 Fetching from HN Algolia...")
        hn_algolia_stories = fetch_from_hn_algolia(lens, args.since)
        if hn_algolia_stories:
            sources_used.append('hn_algolia')
            print(f"   ✓ Found {len(hn_algolia_stories)} stories")
        else:
            sources_failed.append('hn_algolia')

        print("🌐 Fetching from NewsAPI...")
        newsapi_articles = fetch_from_newsapi(lens, args.since)
        if newsapi_articles:
            sources_used.append('newsapi')
            print(f"   ✓ Found {len(newsapi_articles)} articles")
        else:
            sources_failed.append('newsapi')

        print("🌐 Fetching from Product Hunt...")
        producthunt_posts = fetch_from_producthunt(lens)
        if producthunt_posts:
            sources_used.append('producthunt')
            print(f"   ✓ Found {len(producthunt_posts)} posts")
        else:
            sources_failed.append('producthunt')

        print("🌐 Fetching from arXiv...")
        arxiv_papers = fetch_from_arxiv(lens, args.since)
        if arxiv_papers:
            sources_used.append('arxiv')
            print(f"   ✓ Found {len(arxiv_papers)} papers")
        else:
            sources_failed.append('arxiv')

        print("🌐 Fetching from Stack Exchange...")
        stackexchange_questions = fetch_from_stackexchange(lens, args.since)
        if stackexchange_questions:
            sources_used.append('stackexchange')
            print(f"   ✓ Found {len(stackexchange_questions)} questions")
        else:
            sources_failed.append('stackexchange')

        print("🌐 Fetching from GDELT...")
        # GDELT temporarily disabled due to timeout issues
        # gdelt_events = fetch_from_gdelt(lens, args.since)
        gdelt_events = []
        sources_failed.append('gdelt (timeout)')
        print("   ⚠️ GDELT skipped (timeout protection)")

        print("🌐 Fetching from SerpAPI...")
        serpapi_trends = fetch_from_serpapi(lens, args.since)
        if serpapi_trends:
            sources_used.append('serpapi')
            print(f"   ✓ Found {len(serpapi_trends)} trends")
        else:
            sources_failed.append('serpapi')

        print("🌐 Fetching from YouTube...")
        youtube_videos = fetch_from_youtube(lens, args.since)
        if youtube_videos:
            sources_used.append('youtube')
            print(f"   ✓ Found {len(youtube_videos)} videos")
        else:
            sources_failed.append('youtube')

        # Fetch from social media (TwitterAPI.io + Xpoz for Instagram)
        print("🌐 Fetching from Social Media (Reddit, Twitter/X via TwitterAPI.io, Instagram via Xpoz)...")
        social_topics = fetch_from_social_media(lens, limit=30)
        if social_topics:
            sources_used.append('social_media')
            print(f"   ✓ Found {len(social_topics)} social trends")
        else:
            sources_failed.append('social_media')

        # Check if we got at least one source
        if not sources_used:
            error = format_error_json(
                'all_sources_failed',
                'Could not fetch data from any source'
            )
            print(json.dumps(error, indent=2))
            sys.exit(1)

        # Extract and aggregate topics
        print("\n📊 Aggregating topics...")
        topics = extract_topics_from_sources(
            hn_stories,
            github_repos,
            devto_posts,
            hn_algolia_stories,
            newsapi_articles,
            producthunt_posts,
            arxiv_papers,
            stackexchange_questions,
            gdelt_events,
            serpapi_trends,
            youtube_videos,
            social_topics
        )

        # Check deduplication
        if not args.force:
            for topic in topics:
                topic['already_analyzed'] = state_manager.is_topic_analyzed(topic['name'])
        else:
            for topic in topics:
                topic['already_analyzed'] = False

        # Limit results
        topics = topics[:args.limit]

        # Prepare output
        result = {
            'lens': lens_name,
            'date': datetime.now().strftime('%Y-%m-%d'),
            'lookback_days': args.since,
            'sources_used': sources_used,
            'sources_failed': sources_failed,
            'topics': topics
        }

        # Save to file
        if args.output:
            output_path = Path(args.output).expanduser()
        else:
            output_dir = state_manager.get_output_dir_for_date(stage='discover')
            output_path = output_dir / 'trends.json'

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(format_success_json(result), f, indent=2, ensure_ascii=False)

        elapsed = time.time() - start_time
        print(f"\n✅ Discovery complete!")
        print(f"   - Topics found: {len(topics)}")
        print(f"   - Sources used: {', '.join(sources_used)}")
        print(f"   - Duration: {elapsed:.1f}s")
        print(f"   - Output: {output_path}")

        # Print to stdout for piping
        print(json.dumps(format_success_json(result), indent=2))

        sys.exit(0)

    except Exception as e:
        error = format_error_json('discovery_error', str(e))
        print(json.dumps(error, indent=2), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()