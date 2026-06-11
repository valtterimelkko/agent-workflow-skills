#!/usr/bin/env python3
"""
Self-hosted Reddit scraper using Reddit's legacy .json endpoints.

Replaces Xpoz-based scraping with direct HTTP requests to Reddit's public JSON API.
Supports both unauthenticated and OAuth2 authenticated access.

Rate limits:
- Unauthenticated: ~10 requests per minute (be conservative: 1 req per 6 seconds)
- OAuth2 Authenticated: ~100 requests per minute

OAuth2 Setup (recommended for production):
1. Go to https://www.reddit.com/prefs/apps
2. Create a "script" type app
3. Note the client_id and client_secret
4. Set environment variables:
   export REDDIT_CLIENT_ID="your_client_id"
   export REDDIT_CLIENT_SECRET="your_client_secret"

Usage:
    scraper = RedditJSONScraper()
    posts = await scraper.scrape_for_lens("devtools_ai", limit=50)
"""
import asyncio
import base64
import json
import os
import random
import re
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'shared'))
from credentials import load_credential

# Try to use httpx for async, fall back to requests
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    import requests
    HAS_HTTPX = False

try:
    from .base_scraper import BaseScraper, ScrapedPost
except ImportError:
    from base_scraper import BaseScraper, ScrapedPost

# Add parent to path for consumer detection
sys.path.insert(0, str(Path(__file__).parent))
try:
    from consumer_scraper_enhanced import ConsumerProblemDetectionMixin
except ImportError:
    # Define dummy mixin if not available
    class ConsumerProblemDetectionMixin:
        def calculate_consumer_opportunity_score(self, post):
            """Dummy implementation - returns 0 score and empty details."""
            return 0, {}


@dataclass
class RateLimitInfo:
    """Track rate limit status from Reddit responses."""
    remaining: Optional[int] = None
    reset_timestamp: Optional[int] = None
    used: Optional[int] = None
    
    def should_slow_down(self) -> bool:
        """Check if we're approaching rate limit."""
        if self.remaining is not None and self.remaining < 5:
            return True
        return False
    
    def get_wait_time(self) -> float:
        """Calculate how long to wait before next request."""
        if self.reset_timestamp:
            now = int(time.time())
            wait = self.reset_timestamp - now + 1
            return max(wait, 6.0)  # Minimum 6 seconds for unauthenticated
        return 6.0  # Default conservative delay


@dataclass
class OAuth2Token:
    """OAuth2 token for Reddit API authentication."""
    access_token: str
    expires_at: float
    token_type: str = "bearer"
    
    def is_expired(self) -> bool:
        """Check if token has expired (with 60 second buffer)."""
        return time.time() >= (self.expires_at - 60)


class RedditOAuth2Manager:
    """
    Manages OAuth2 authentication for Reddit API.
    
    Uses application-only OAuth2 flow (client credentials).
    This does not require a user to log in - it's for read-only access.
    
    Setup:
        1. Create app at https://www.reddit.com/prefs/apps
        2. Select "script" type
        3. Set environment variables:
           REDDIT_CLIENT_ID=your_client_id
           REDDIT_CLIENT_SECRET=your_client_secret
    """
    
    TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
    
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        """
        Initialize OAuth2 manager.
        
        Args:
            client_id: Reddit app client ID (or from REDDIT_CLIENT_ID env var)
            client_secret: Reddit app client secret (or from REDDIT_CLIENT_SECRET env var)
        """
        self.client_id = client_id or load_credential('REDDIT_CLIENT_ID', required=False)
        self.client_secret = client_secret or load_credential('REDDIT_CLIENT_SECRET', required=False)
        self._token: Optional[OAuth2Token] = None
    
    def is_configured(self) -> bool:
        """Check if OAuth2 credentials are configured."""
        return bool(self.client_id and self.client_secret)
    
    async def get_token(self) -> Optional[OAuth2Token]:
        """
        Get valid OAuth2 token, refreshing if necessary.
        
        Returns:
            OAuth2Token if configured, None otherwise
        """
        if not self.is_configured():
            return None
        
        # Return existing valid token
        if self._token and not self._token.is_expired():
            return self._token
        
        # Fetch new token
        self._token = await self._fetch_token()
        return self._token
    
    async def _fetch_token(self) -> Optional[OAuth2Token]:
        """Fetch new OAuth2 token from Reddit."""
        if not HAS_HTTPX:
            # Fall back to synchronous requests
            return await asyncio.get_event_loop().run_in_executor(
                None, self._fetch_token_sync
            )
        
        try:
            auth_str = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.TOKEN_URL,
                    headers={
                        "Authorization": f"Basic {auth_str}",
                        "User-Agent": "RedditJSONScraper/1.0",
                    },
                    data={
                        "grant_type": "client_credentials",
                    },
                    timeout=30.0
                )
                
                if response.status_code != 200:
                    print(f"OAuth2 token fetch failed: HTTP {response.status_code}")
                    return None
                
                data = response.json()
                access_token = data.get('access_token')
                expires_in = data.get('expires_in', 3600)
                
                if not access_token:
                    print("OAuth2 token fetch failed: no access_token in response")
                    return None
                
                return OAuth2Token(
                    access_token=access_token,
                    expires_at=time.time() + expires_in,
                    token_type=data.get('token_type', 'bearer')
                )
                
        except Exception as e:
            print(f"OAuth2 token fetch error: {e}")
            return None
    
    def _fetch_token_sync(self) -> Optional[OAuth2Token]:
        """Synchronous version of token fetch for fallback."""
        try:
            auth_str = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()
            
            response = requests.post(
                self.TOKEN_URL,
                headers={
                    "Authorization": f"Basic {auth_str}",
                    "User-Agent": "RedditJSONScraper/1.0",
                },
                data={
                    "grant_type": "client_credentials",
                },
                timeout=30.0
            )
            
            if response.status_code != 200:
                print(f"OAuth2 token fetch failed: HTTP {response.status_code}")
                return None
            
            data = response.json()
            access_token = data.get('access_token')
            expires_in = data.get('expires_in', 3600)
            
            if not access_token:
                print("OAuth2 token fetch failed: no access_token in response")
                return None
            
            return OAuth2Token(
                access_token=access_token,
                expires_at=time.time() + expires_in,
                token_type=data.get('token_type', 'bearer')
            )
            
        except Exception as e:
            print(f"OAuth2 token fetch error: {e}")
            return None


class CircuitBreaker:
    """Simple circuit breaker pattern for Reddit API calls."""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 300):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again (half-open)
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = 'closed'  # closed, open, half-open
    
    def can_execute(self) -> bool:
        """Check if request can be executed."""
        if self.state == 'closed':
            return True
        elif self.state == 'open':
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = 'half-open'
                return True
            return False
        else:  # half-open
            return True
    
    def record_success(self):
        """Record successful request."""
        self.failures = 0
        self.state = 'closed'
    
    def record_failure(self):
        """Record failed request."""
        self.failures += 1
        self.last_failure_time = time.time()
        if self.failures >= self.failure_threshold:
            self.state = 'open'


class RedditJSONScraper(BaseScraper, ConsumerProblemDetectionMixin):
    """
    Self-hosted Reddit scraper using public .json endpoints.
    
    Features:
    - Direct HTTP requests to Reddit's JSON API
    - User-Agent rotation to avoid blocking
    - Rate limit handling with exponential backoff
    - Shadowban detection
    - Client-side keyword filtering
    - Async/await support
    - Circuit breaker pattern for resilience
    """

    BASE_URL = "https://www.reddit.com"
    
    # Rotate through multiple realistic browser User-Agents
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36 Edg/120.0.0.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Safari/605.1.15",
    ]
    
    # Subreddit clusters by lens type (same as original)
    SUBREDDIT_CLUSTERS = {
        "devtools_ai": [
            "webdev", "programming", "MachineLearning", "LocalLLaMA",
            "vscode", "commandline", "ExperiencedDevs"
        ],
        "ecommerce_sellers": [
            "Flipping", "Etsy", "Ebay", "Depop", "Poshmark",
            "AmazonFBA", "Mercari", "EtsySellers"
        ],
        "creator_economy": [
            "ContentCreation", "YouTubers", "TikTokCreators",
            "podcasting", "NewTubers", "PartneredYoutube"
        ],
        "infra_automation": [
            "devops", "sysadmin", "kubernetes", "nocode",
            "selfhosted", "homelab", "docker"
        ],
        "small_business_ops": [
            "smallbusiness", "Entrepreneur", "freelance",
            "realtors", "Plumbing", "Electricians", "Landlord"
        ],
        "digital_marketing": [
            "marketing", "PPC", "SEO", "SocialMediaMarketing",
            "advertising", "content_marketing", "growthhacking"
        ],
        "data_analytics": [
            "dataengineering", "businessintelligence", "analytics",
            "excel", "datascience", "businessanalysis"
        ]
    }

    # Reddit-specific pain patterns (same as original)
    REDDIT_PAIN_PATTERNS = [
        r"(oversold|sold out).*(platform|item|on)",
        r"(manually|by hand).*(update|sync).*(inventory|listing)",
        r"(5|six|multiple|different).*(platform|app|site)",
        r"spreadsheet.*(track|manage).*(inventory|sales)",
        r"wish.*(app|tool).*(sync|update).*(all|every)",
        r"(pricing|repricing).*(takes|manual|hours)",
        r"anyone (know|use|recommend).*(tool|app|software)",
        r"how do (you|I|we).*(manage|handle|track)",
    ]

    def __init__(self, client=None, use_oauth2: bool = True, proxy: Optional[str] = None):
        """
        Initialize the scraper.
        
        Args:
            client: Optional HTTP client (httpx.AsyncClient or requests.Session).
                   If not provided, a new client will be created.
            use_oauth2: Whether to use OAuth2 if credentials are available.
                       OAuth2 provides higher rate limits (100/min vs 10/min).
            proxy: Optional proxy URL (e.g., "http://user:pass@proxy:8080").
                  If not provided, loads from credential hierarchy:
                  1. REDDIT_PROXY_URL env var
                  2. a shell startup file such as ~/.bashrc
                  3. a shell startup file such as ~/.bashrc export REDDIT_PROXY_URL
        """
        super().__init__(client)
        # Extend pain patterns with Reddit-specific ones
        self.PAIN_PATTERNS = self.PAIN_PATTERNS + self.REDDIT_PAIN_PATTERNS
        
        self._client = None
        self._session = None
        self._rate_limit = RateLimitInfo()
        self._last_request_time = 0
        self._ua_index = 0
        
        # Load proxy from credential hierarchy
        self._proxy = proxy or load_credential('REDDIT_PROXY_URL', required=False)
        
        # OAuth2 setup
        self._oauth = RedditOAuth2Manager() if use_oauth2 else None
        self._oauth_token: Optional[OAuth2Token] = None
        
        # Circuit breaker for resilience
        self._circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=600)
        
        # Adjust rate limits based on OAuth availability
        if self._oauth and self._oauth.is_configured():
            self._min_delay = 0.6  # 100 requests per minute with OAuth2
            print("  Reddit OAuth2 credentials found - using authenticated access (100 req/min)")
        else:
            self._min_delay = 6.0  # 10 requests per minute unauthenticated
            print("  Reddit OAuth2 not configured - using unauthenticated access (10 req/min)")
        
        if self._proxy:
            print(f"  Using proxy: {self._proxy.split('@')[-1] if '@' in self._proxy else self._proxy}")
        else:
            print("  WARNING: No proxy configured. Reddit may block cloud/datacenter IPs.")
        
    async def _get_client(self):
        """Get or create HTTP client."""
        if HAS_HTTPX:
            if self._client is None or self._client.is_closed:
                # httpx uses 'proxy' (singular) with different format
                if self._proxy:
                    # Parse proxy URL for httpx format
                    # httpx expects: "http://user:pass@host:port"
                    self._client = httpx.AsyncClient(
                        headers=self._get_headers(),
                        timeout=30.0,
                        follow_redirects=True,
                        proxy=self._proxy
                    )
                else:
                    self._client = httpx.AsyncClient(
                        headers=self._get_headers(),
                        timeout=30.0,
                        follow_redirects=True
                    )
            return self._client
        else:
            # Synchronous fallback
            if self._session is None:
                self._session = requests.Session()
                self._session.headers.update(self._get_headers())
                if self._proxy:
                    self._session.proxies = {
                        "http": self._proxy,
                        "https": self._proxy
                    }
            return self._session
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with rotated User-Agent."""
        ua = self.USER_AGENTS[self._ua_index % len(self.USER_AGENTS)]
        # Minimal headers to avoid blocking - simpler is better for Reddit
        return {
            "User-Agent": ua,
            "Accept": "application/json",
        }
    
    def _rotate_user_agent(self):
        """Rotate to next User-Agent."""
        self._ua_index += 1
        headers = self._get_headers()
        
        if HAS_HTTPX and self._client:
            self._client.headers.update(headers)
        elif self._session:
            self._session.headers.update(headers)
    
    async def _rate_limit_delay(self):
        """Enforce rate limiting between requests."""
        # Calculate time since last request
        now = time.time()
        elapsed = now - self._last_request_time
        
        # Determine delay needed
        delay = self._min_delay
        if self._rate_limit.should_slow_down():
            delay = self._rate_limit.get_wait_time()
        
        # Add jitter to prevent synchronized patterns
        jitter = random.uniform(0.5, 2.0)
        total_delay = max(0, delay - elapsed + jitter)
        
        if total_delay > 0:
            await asyncio.sleep(total_delay)
        
        self._last_request_time = time.time()
    
    async def _make_request(self, url: str, max_retries: int = 5) -> Optional[Dict]:
        """
        Make HTTP request with retry logic and circuit breaker.
        
        Args:
            url: Full URL to fetch
            max_retries: Number of retry attempts
            
        Returns:
            Parsed JSON response or None on failure
        """
        # Check circuit breaker
        if not self._circuit_breaker.can_execute():
            print(f"  Circuit breaker OPEN - skipping request to avoid cascading failures")
            return None
        
        original_url = url
        
        # Get OAuth2 token if available
        if self._oauth and not self._oauth_token:
            self._oauth_token = await self._oauth.get_token()
        
        for attempt in range(max_retries):
            await self._rate_limit_delay()
            
            # Try old.reddit.com on 403 errors after first attempt
            if attempt > 0 and 'www.reddit.com' in url:
                url = original_url.replace('www.reddit.com', 'old.reddit.com')
            
            try:
                # Build headers with OAuth2 if available
                headers = self._get_headers()
                if self._oauth_token and not self._oauth_token.is_expired():
                    headers["Authorization"] = f"Bearer {self._oauth_token.access_token}"
                
                if HAS_HTTPX:
                    client = await self._get_client()
                    response = await client.get(url, headers=headers)
                else:
                    # Synchronous fallback
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None, 
                        lambda: self._session.get(url, headers=headers, timeout=30)
                    )
                
                # Update rate limit info from headers
                if hasattr(response, 'headers'):
                    self._update_rate_limit_info(response.headers)
                
                # Handle 429 rate limit
                if response.status_code == 429:
                    wait_time = (2 ** attempt) + random.uniform(1, 3)
                    print(f"  Rate limited (429). Waiting {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                    
                    # Rotate User-Agent on rate limit
                    if attempt < max_retries - 1:
                        self._rotate_user_agent()
                    continue
                
                # Handle 403 Forbidden - rotate User-Agent and retry
                if response.status_code == 403:
                    print(f"  HTTP 403 for {url}")
                    if attempt < max_retries - 1:
                        print(f"    Rotating User-Agent and retrying...")
                        self._rotate_user_agent()
                        # Recreate client with new headers
                        if HAS_HTTPX and self._client:
                            await self._client.aclose()
                            self._client = None
                        elif self._session:
                            self._session = None
                    continue
                
                # Handle 404 - don't retry
                if response.status_code == 404:
                    print(f"  HTTP 404 for {url}")
                    return None
                
                # Handle other errors
                if response.status_code != 200:
                    print(f"  HTTP {response.status_code} for {url}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    continue
                
                # Parse JSON response
                try:
                    if HAS_HTTPX:
                        data = response.json()
                    else:
                        data = response.json()
                except json.JSONDecodeError as e:
                    print(f"  JSON parse error: {e}")
                    # Check for shadowban (HTML response)
                    if hasattr(response, 'text') and '<html' in response.text[:100].lower():
                        print("  Possible shadowban - received HTML instead of JSON")
                        self._rotate_user_agent()
                    continue
                
                # Check for shadowban indicator (empty data with 200)
                if self._is_shadowban_response(data):
                    print("  Possible shadowban - empty data array")
                    self._rotate_user_agent()
                    if attempt < max_retries - 1:
                        continue
                
                # Success - record and return
                self._circuit_breaker.record_success()
                return data
                
            except Exception as e:
                print(f"  Request error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        # All retries exhausted - record failure
        self._circuit_breaker.record_failure()
        return None
    
    def _update_rate_limit_info(self, headers: Dict[str, str]):
        """Update rate limit tracking from response headers."""
        # Reddit rate limit headers
        remaining = headers.get('x-ratelimit-remaining')
        reset = headers.get('x-ratelimit-reset')
        used = headers.get('x-ratelimit-used')
        
        if remaining is not None:
            try:
                self._rate_limit.remaining = int(float(remaining))
            except ValueError:
                pass
        
        if reset is not None:
            try:
                self._rate_limit.reset_timestamp = int(reset)
            except ValueError:
                pass
        
        if used is not None:
            try:
                self._rate_limit.used = int(float(used))
            except ValueError:
                pass
    
    def _is_shadowban_response(self, data: Any) -> bool:
        """Detect shadowban by checking for empty data with 200 response."""
        if not isinstance(data, dict):
            return False
        
        listing_data = data.get('data', {})
        children = listing_data.get('children', [])
        
        # Empty children array with valid structure suggests shadowban
        if isinstance(children, list) and len(children) == 0:
            # But also check if this is just the end of pagination
            if listing_data.get('after') is None and listing_data.get('before') is None:
                return True
        
        return False
    
    async def _fetch_subreddit_posts(
        self, 
        subreddit: str, 
        limit: int = 50,
        sort: str = "hot",
        time_filter: Optional[str] = None
    ) -> List[ScrapedPost]:
        """
        Fetch posts from a subreddit.
        
        Args:
            subreddit: Subreddit name (without r/)
            limit: Maximum posts to fetch (max 100 per request)
            sort: Sort method (hot, new, top, rising)
            time_filter: Time filter for top (hour, day, week, month, year, all)
            
        Returns:
            List of ScrapedPost objects
        """
        # Build URL
        url = f"{self.BASE_URL}/r/{subreddit}/{sort}.json"
        params = [f"limit={min(limit, 100)}"]
        
        if time_filter and sort == "top":
            params.append(f"t={time_filter}")
        
        if params:
            url += "?" + "&".join(params)
        
        # Make request
        data = await self._make_request(url)
        
        if not data:
            return []
        
        # Parse posts
        posts = self._parse_listing(data, subreddit)
        
        # If we need more posts and there's pagination, fetch more
        if len(posts) < limit:
            after = data.get('data', {}).get('after')
            if after:
                more_posts = await self._fetch_paginated(subreddit, after, limit - len(posts), sort, time_filter)
                posts.extend(more_posts)
        
        return posts[:limit]
    
    async def _fetch_paginated(
        self,
        subreddit: str,
        after: str,
        limit: int,
        sort: str = "hot",
        time_filter: Optional[str] = None
    ) -> List[ScrapedPost]:
        """Fetch additional posts using pagination cursor."""
        url = f"{self.BASE_URL}/r/{subreddit}/{sort}.json"
        params = [f"limit={min(limit, 100)}", f"after={after}"]
        
        if time_filter and sort == "top":
            params.append(f"t={time_filter}")
        
        url += "?" + "&".join(params)
        
        data = await self._make_request(url)
        
        if not data:
            return []
        
        return self._parse_listing(data, subreddit)
    
    def _parse_listing(self, data: Dict, subreddit: str) -> List[ScrapedPost]:
        """Parse Reddit listing JSON into ScrapedPost objects."""
        posts = []
        
        if not isinstance(data, dict):
            return posts
        
        listing_data = data.get('data', {})
        children = listing_data.get('children', [])
        
        for child in children:
            if not isinstance(child, dict):
                continue
            
            post_data = child.get('data', {})
            if not post_data:
                continue
            
            post = self._create_scraped_post(post_data, subreddit)
            if post:
                posts.append(post)
        
        return posts
    
    def _create_scraped_post(self, data: Dict[str, Any], subreddit: str) -> Optional[ScrapedPost]:
        """Create a ScrapedPost from Reddit post data."""
        try:
            # Extract fields with fallbacks
            post_id = str(data.get('id', ''))
            if not post_id:
                return None
            
            title = data.get('title', '')
            body = data.get('selftext', '')
            author = data.get('author', '')
            
            # Engagement metrics
            score = data.get('score', 0) or 0
            num_comments = data.get('num_comments', 0) or 0
            
            # URLs
            permalink = data.get('permalink', '')
            url = data.get('url', '')
            
            # Build Reddit URL if we have permalink
            if permalink:
                reddit_url = f"https://www.reddit.com{permalink}"
            elif url:
                reddit_url = url
            else:
                reddit_url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}"
            
            # Timestamp
            created_utc = data.get('created_utc', '')
            if created_utc:
                created_str = str(int(created_utc))
            else:
                created_str = str(int(time.time()))
            
            # Metadata
            metadata = {
                "subreddit": data.get('subreddit', subreddit),
                "flair": data.get('link_flair_text', ''),
                "is_self": data.get('is_self', True),
                "over_18": data.get('over_18', False),
                "upvote_ratio": data.get('upvote_ratio', 0),
                "source": "reddit_json_api"
            }
            
            return ScrapedPost(
                id=post_id,
                platform="reddit",
                title=title,
                body=body[:2000],  # Limit body length
                url=reddit_url,
                author=author,
                engagement=score,
                comments_count=num_comments,
                created_at=created_str,
                metadata=metadata
            )
            
        except Exception as e:
            print(f"  Error creating ScrapedPost: {e}")
            return None
    
    async def scrape_for_lens(
        self,
        lens_key: str,
        limit: int = 50
    ) -> List[ScrapedPost]:
        """
        Scrape Reddit based on lens configuration.
        
        TIMING EXPECTATIONS (4 subreddits, sequential with rate limiting):
        - Per subreddit: ~4-5s (includes 6s rate limit delay)
        - 4 subreddits: ~16-20s total
        - Scoring & deduplication: 1-2s
        - Total: ~18-25s for full lens scrape
        
        Note: Reddit rate limits unauthenticated requests to ~10/min,
        so subreddits are fetched sequentially, not in parallel.
        
        Args:
            lens_key: Lens identifier (e.g., "ecommerce_sellers")
            limit: Maximum posts per subreddit
            
        Returns:
            List of processed posts sorted by opportunity score
        """
        subreddits = self.SUBREDDIT_CLUSTERS.get(lens_key, [])
        if not subreddits:
            print(f"Warning: No subreddits configured for lens '{lens_key}'")
            return []
        
        all_posts = []
        
        # Limit subreddits to reduce fetch time (prioritize first 4)
        subreddits_to_fetch = subreddits[:4]
        
        for subreddit in subreddits_to_fetch:
            try:
                # Fetch from subreddit (hot only to save time)
                posts = await self._fetch_subreddit_posts(subreddit, limit, sort="hot")
                all_posts.extend(posts)
                
            except Exception as e:
                print(f"Warning: Reddit fetch failed for r/{subreddit}: {e}")
        
        # Calculate scores
        for post in all_posts:
            text = f"{post.title} {post.body}"
            post.pain_score = self.calculate_pain_score(text)
            
            # Enhanced consumer opportunity scoring
            consumer_score, consumer_details = self.calculate_consumer_opportunity_score(post)
            
            # Blend base and consumer scores
            base_opp_score = self.calculate_opportunity_score(post)
            post.opportunity_score = max(base_opp_score, consumer_score * 0.8)
            
            # Store consumer details in metadata
            post.metadata['consumer_analysis'] = consumer_details
            
            # High-opportunity criteria
            has_consumer_signals = consumer_details.get('signals_detected', 0) > 0
            post.is_high_opportunity = (
                (post.pain_score >= 0.3 and post.engagement >= 5) or
                (has_consumer_signals and consumer_score >= 40)
            )
        
        # Deduplicate and sort
        unique_posts = self.deduplicate_posts(all_posts)
        return sorted(unique_posts, key=lambda x: x.opportunity_score, reverse=True)
    
    async def search_pain_points(
        self,
        subreddits: List[str],
        limit: int = 30
    ) -> List[ScrapedPost]:
        """
        Search for pain point posts across subreddits.
        
        Since Reddit's search.json requires OAuth for programmatic access,
        we fetch posts and filter client-side for pain keywords.
        """
        pain_keywords = [
            "frustrated", "annoying", "wish there was", "tired of",
            "problem", "issue", "struggling", "difficult", "pain",
            "manual", "spreadsheet", "automation", "tool needed"
        ]
        
        all_posts = []
        
        for subreddit in subreddits:
            try:
                # Fetch more posts than needed since we'll filter
                posts = await self._fetch_subreddit_posts(subreddit, limit * 3, sort="hot")
                posts.extend(await self._fetch_subreddit_posts(subreddit, limit, sort="new"))
                
                # Filter for pain keywords client-side
                filtered = []
                for post in posts:
                    text = f"{post.title} {post.body}".lower()
                    if any(kw in text for kw in pain_keywords):
                        filtered.append(post)
                
                all_posts.extend(filtered)
                
            except Exception as e:
                print(f"Warning: Pain point search failed for r/{subreddit}: {e}")
        
        # Score and sort
        for post in all_posts:
            text = f"{post.title} {post.body}"
            post.pain_score = self.calculate_pain_score(text)
            post.opportunity_score = self.calculate_opportunity_score(post)
        
        return sorted(
            self.deduplicate_posts(all_posts),
            key=lambda x: x.pain_score,
            reverse=True
        )[:limit]
    
    async def close(self):
        """Close HTTP client."""
        if HAS_HTTPX and self._client:
            await self._client.aclose()
        elif self._session:
            self._session.close()


# Convenience function for direct usage
async def fetch_reddit_posts(lens_key: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Fetch Reddit posts for a lens and return as dictionaries."""
    scraper = RedditJSONScraper()
    try:
        posts = await scraper.scrape_for_lens(lens_key, limit)
        return [
            {
                "id": p.id,
                "platform": p.platform,
                "title": p.title,
                "body": p.body[:500] if p.body else "",
                "url": p.url,
                "author": p.author,
                "engagement": p.engagement,
                "comments_count": p.comments_count,
                "pain_score": round(p.pain_score, 3),
                "opportunity_score": round(p.opportunity_score, 1),
                "is_high_opportunity": p.is_high_opportunity,
                "metadata": p.metadata
            }
            for p in posts
        ]
    finally:
        await scraper.close()


# Backwards compatibility: Create a class that matches the old Xpoz-based interface
class RedditScraper(RedditJSONScraper):
    """
    Backwards-compatible RedditScraper.
    
    This is an alias for RedditJSONScraper to maintain compatibility
    with existing code that imports RedditScraper.
    """
    pass