#!/usr/bin/env python3
"""
Production-quality Reddit scraper using legacy .json endpoints.

Features:
- OAuth2 and unauthenticated access
- Circuit breaker pattern for resilience
- User-Agent rotation
- Rate limit handling with exponential backoff
- Shadowban detection
- Residential proxy support
- Comprehensive retry logic

Usage:
    scraper = RedditScraper()
    posts = await scraper.get_subreddit_posts("startups", limit=50)
    await scraper.close()
"""
import asyncio
import base64
import json
import random
import time
from typing import List, Dict, Any, Optional

# Try to use httpx for async, fall back to requests
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    import requests
    HAS_HTTPX = False

from scripts.utils import (
    ScrapedPost, ScrapedComment, SubredditInfo, Contributor, WikiPage,
    RateLimitInfo, OAuth2Token
)
from scripts.credentials import (
    load_reddit_proxy_url, load_reddit_oauth_credentials
)


class CircuitBreaker:
    """Simple circuit breaker pattern for Reddit API calls."""
    
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 600):
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


class RedditOAuth2Manager:
    """Manages OAuth2 authentication for Reddit API."""
    
    TOKEN_URL = "https://www.reddit.com/api/v1/access_token"
    
    def __init__(self, client_id: Optional[str] = None, client_secret: Optional[str] = None):
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: Optional[OAuth2Token] = None
    
    def is_configured(self) -> bool:
        """Check if OAuth2 credentials are configured."""
        return bool(self.client_id and self.client_secret)
    
    async def get_token(self) -> Optional[OAuth2Token]:
        """Get valid OAuth2 token, refreshing if necessary."""
        if not self.is_configured():
            return None
        
        if self._token and not self._token.is_expired():
            return self._token
        
        self._token = await self._fetch_token()
        return self._token
    
    async def _fetch_token(self) -> Optional[OAuth2Token]:
        """Fetch new OAuth2 token from Reddit."""
        if not HAS_HTTPX:
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
                        "User-Agent": "RedditScraper/1.0",
                    },
                    data={"grant_type": "client_credentials"},
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
                    "User-Agent": "RedditScraper/1.0",
                },
                data={"grant_type": "client_credentials"},
                timeout=30.0
            )
            
            if response.status_code != 200:
                print(f"OAuth2 token fetch failed: HTTP {response.status_code}")
                return None
            
            data = response.json()
            access_token = data.get('access_token')
            expires_in = data.get('expires_in', 3600)
            
            if not access_token:
                return None
            
            return OAuth2Token(
                access_token=access_token,
                expires_at=time.time() + expires_in,
                token_type=data.get('token_type', 'bearer')
            )
            
        except Exception as e:
            print(f"OAuth2 token fetch error: {e}")
            return None


class RedditScraper:
    """
    Production-quality Reddit scraper with comprehensive error handling.
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
    
    def __init__(self, use_oauth2: bool = True, proxy: Optional[str] = None):
        """
        Initialize the scraper.
        
        Args:
            use_oauth2: Whether to use OAuth2 if credentials available
            proxy: Optional proxy URL (auto-loaded if not provided)
        """
        self._client = None
        self._session = None
        self._rate_limit = RateLimitInfo()
        self._last_request_time = 0
        self._ua_index = 0
        
        # Load proxy from credential hierarchy
        self._proxy = proxy or load_reddit_proxy_url(required=False)
        
        # OAuth2 setup
        client_id, client_secret = load_reddit_oauth_credentials() if use_oauth2 else (None, None)
        self._oauth = RedditOAuth2Manager(client_id, client_secret)
        self._oauth_token: Optional[OAuth2Token] = None
        
        # Circuit breaker for resilience
        self._circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=600)
        
        # Adjust rate limits based on OAuth availability
        if self._oauth.is_configured():
            self._min_delay = 0.6  # 100 requests per minute
            print("Reddit OAuth2 credentials found - using authenticated access (100 req/min)")
        else:
            self._min_delay = 6.0  # 10 requests per minute
            print("Reddit OAuth2 not configured - using unauthenticated access (10 req/min)")
        
        if self._proxy:
            proxy_display = self._proxy.split('@')[-1] if '@' in self._proxy else self._proxy
            print(f"Using proxy: {proxy_display}")
        else:
            print("WARNING: No proxy configured. Reddit may block cloud/datacenter IPs.")
    
    async def _get_client(self):
        """Get or create HTTP client."""
        if HAS_HTTPX:
            if self._client is None or self._client.is_closed:
                if self._proxy:
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
            if self._session is None:
                self._session = requests.Session()
                self._session.headers.update(self._get_headers())
                if self._proxy:
                    self._session.proxies = {"http": self._proxy, "https": self._proxy}
            return self._session
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with rotated User-Agent."""
        ua = self.USER_AGENTS[self._ua_index % len(self.USER_AGENTS)]
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
        now = time.time()
        elapsed = now - self._last_request_time
        
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
        if not self._circuit_breaker.can_execute():
            print(f"Circuit breaker OPEN - skipping request to avoid cascading failures")
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
                    print(f"Rate limited (429). Waiting {wait_time:.1f}s...")
                    await asyncio.sleep(wait_time)
                    if attempt < max_retries - 1:
                        self._rotate_user_agent()
                    continue
                
                # Handle 403 Forbidden - rotate User-Agent and retry
                if response.status_code == 403:
                    print(f"HTTP 403 for {url}")
                    if attempt < max_retries - 1:
                        print(f"Rotating User-Agent and retrying...")
                        self._rotate_user_agent()
                        if HAS_HTTPX and self._client:
                            await self._client.aclose()
                            self._client = None
                        elif self._session:
                            self._session = None
                    continue
                
                # Handle 404 - don't retry
                if response.status_code == 404:
                    print(f"HTTP 404 for {url}")
                    return None
                
                # Handle other errors
                if response.status_code != 200:
                    print(f"HTTP {response.status_code} for {url}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    continue
                
                # Parse JSON response
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    print(f"JSON parse error: {e}")
                    if hasattr(response, 'text') and '<html' in response.text[:100].lower():
                        print("Possible shadowban - received HTML instead of JSON")
                        self._rotate_user_agent()
                    continue
                
                # Check for shadowban indicator
                if self._is_shadowban_response(data):
                    print("Possible shadowban - empty data array")
                    self._rotate_user_agent()
                    if attempt < max_retries - 1:
                        continue
                
                # Success - record and return
                self._circuit_breaker.record_success()
                return data
                
            except Exception as e:
                print(f"Request error (attempt {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
        
        # All retries exhausted - record failure
        self._circuit_breaker.record_failure()
        return None
    
    def _update_rate_limit_info(self, headers: Dict[str, str]):
        """Update rate limit tracking from response headers."""
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
        
        if isinstance(children, list) and len(children) == 0:
            if listing_data.get('after') is None and listing_data.get('before') is None:
                return True
        
        return False
    
    # =================================================================
    # PUBLIC API METHODS
    # =================================================================
    
    async def get_subreddit_posts(
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
        """
        url = f"{self.BASE_URL}/r/{subreddit}/{sort}.json"
        params = [f"limit={min(limit, 100)}"]
        
        if time_filter and sort == "top":
            params.append(f"t={time_filter}")
        
        if params:
            url += "?" + "&".join(params)
        
        data = await self._make_request(url)
        if not data:
            return []
        
        posts = self._parse_listing(data, subreddit)
        
        # Pagination if needed
        if len(posts) < limit:
            after = data.get('data', {}).get('after')
            if after:
                more_posts = await self._fetch_paginated(subreddit, after, limit - len(posts), sort, time_filter)
                posts.extend(more_posts)
        
        return posts[:limit]
    
    async def get_post_with_comments(
        self,
        subreddit: str,
        post_id: str,
        depth: int = 5
    ) -> tuple[Optional[ScrapedPost], List[ScrapedComment]]:
        """
        Fetch a post and its comments.
        
        Args:
            subreddit: Subreddit name
            post_id: Post ID
            depth: Maximum comment depth to fetch
            
        Returns:
            Tuple of (post, comments)
        """
        url = f"{self.BASE_URL}/r/{subreddit}/comments/{post_id}.json?depth={depth}"
        
        data = await self._make_request(url)
        if not data or not isinstance(data, list) or len(data) < 2:
            return None, []
        
        # First element is the post listing
        post_listing = data[0]
        posts = self._parse_listing(post_listing, subreddit)
        post = posts[0] if posts else None
        
        # Second element is comments
        comment_listing = data[1]
        comments = self._parse_comments(comment_listing, post_id)
        
        return post, comments
    
    async def search_subreddits(self, query: str, limit: int = 10) -> List[SubredditInfo]:
        """Search for subreddits by keyword."""
        url = f"{self.BASE_URL}/subreddits/search.json?q={query}&limit={limit}"
        
        data = await self._make_request(url)
        if not data:
            return []
        
        subreddits = []
        children = data.get('data', {}).get('children', [])
        
        for child in children:
            if child.get('kind') == 't5':
                d = child['data']
                subreddits.append(SubredditInfo(
                    name=d.get('display_name', ''),
                    display_name=d.get('display_name', ''),
                    subscribers=d.get('subscribers', 0),
                    accounts_active=d.get('accounts_active', 0),
                    description=d.get('description', ''),
                    public_description=d.get('public_description', ''),
                    created_utc=d.get('created_utc', 0),
                    over18=d.get('over18', False),
                    url=d.get('url', ''),
                    icon_img=d.get('icon_img')
                ))
        
        return subreddits
    
    async def get_subreddit_info(self, subreddit: str) -> Optional[SubredditInfo]:
        """Get metadata about a subreddit."""
        url = f"{self.BASE_URL}/r/{subreddit}/about.json"
        
        data = await self._make_request(url)
        if not data or data.get('kind') != 't5':
            return None
        
        d = data['data']
        return SubredditInfo(
            name=d.get('display_name', ''),
            display_name=d.get('display_name', ''),
            subscribers=d.get('subscribers', 0),
            accounts_active=d.get('accounts_active', 0),
            description=d.get('description', ''),
            public_description=d.get('public_description', ''),
            created_utc=d.get('created_utc', 0),
            over18=d.get('over18', False),
            url=d.get('url', ''),
            icon_img=d.get('icon_img')
        )
    
    async def get_wiki_pages(self, subreddit: str) -> List[str]:
        """Get list of wiki pages for a subreddit."""
        url = f"{self.BASE_URL}/r/{subreddit}/wiki.json"
        
        data = await self._make_request(url)
        if not data:
            return []
        
        pages = []
        children = data.get('data', {}).get('children', [])
        for child in children:
            if child.get('kind') == 'wikipage':
                pages.append(child['data'].get('page', ''))
        
        return pages
    
    async def get_wiki_page(self, subreddit: str, page: str) -> Optional[WikiPage]:
        """Get content of a specific wiki page."""
        url = f"{self.BASE_URL}/r/{subreddit}/wiki/{page}.json"
        
        data = await self._make_request(url)
        if not data or data.get('kind') != 'wikipage':
            return None
        
        d = data['data']
        return WikiPage(
            page=page,
            title=d.get('title', page),
            content_md=d.get('content_md', ''),
            content_html=d.get('content_html', ''),
            revision_date=d.get('revision_date', 0)
        )
    
    async def get_user_activity(
        self,
        username: str,
        limit: int = 50,
        activity_type: str = "overview"
    ) -> List[Dict[str, Any]]:
        """
        Get user activity (posts/comments).
        
        Args:
            username: Reddit username (without u/)
            limit: Number of items to fetch
            activity_type: 'overview', 'submitted', or 'comments'
        """
        url = f"{self.BASE_URL}/user/{username}/{activity_type}.json?limit={limit}"
        
        data = await self._make_request(url)
        if not data:
            return []
        
        items = []
        children = data.get('data', {}).get('children', [])
        
        for child in children:
            kind = child.get('kind')
            d = child.get('data', {})
            
            if kind == 't3':  # Post
                items.append({
                    'type': 'post',
                    'id': d.get('id'),
                    'title': d.get('title'),
                    'subreddit': d.get('subreddit'),
                    'score': d.get('score'),
                    'created_utc': d.get('created_utc')
                })
            elif kind == 't1':  # Comment
                items.append({
                    'type': 'comment',
                    'id': d.get('id'),
                    'body': d.get('body'),
                    'subreddit': d.get('subreddit'),
                    'score': d.get('score'),
                    'created_utc': d.get('created_utc')
                })
        
        return items
    
    async def close(self):
        """Close HTTP client."""
        if HAS_HTTPX and self._client:
            await self._client.aclose()
        elif self._session:
            self._session.close()
    
    # =================================================================
    # PRIVATE HELPER METHODS
    # =================================================================
    
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
            post_id = str(data.get('id', ''))
            if not post_id:
                return None
            
            title = data.get('title', '')
            body = data.get('selftext', '')
            author = data.get('author', '')
            
            score = data.get('score', 0) or 0
            num_comments = data.get('num_comments', 0) or 0
            
            permalink = data.get('permalink', '')
            url = data.get('url', '')
            
            if permalink:
                reddit_url = f"https://www.reddit.com{permalink}"
            elif url:
                reddit_url = url
            else:
                reddit_url = f"https://www.reddit.com/r/{subreddit}/comments/{post_id}"
            
            created_utc = data.get('created_utc', '')
            created_str = str(int(created_utc)) if created_utc else str(int(time.time()))
            
            metadata = {
                "subreddit": data.get('subreddit', subreddit),
                "flair": data.get('link_flair_text', ''),
                "is_self": data.get('is_self', True),
                "over_18": data.get('over_18', False),
                "upvote_ratio": data.get('upvote_ratio', 0),
            }
            
            return ScrapedPost(
                id=post_id,
                platform="reddit",
                title=title,
                body=body[:2000],
                url=reddit_url,
                author=author,
                engagement=score,
                comments_count=num_comments,
                created_at=created_str,
                metadata=metadata
            )
            
        except Exception as e:
            print(f"Error creating ScrapedPost: {e}")
            return None
    
    def _parse_comments(self, data: Dict, post_id: str, depth: int = 0) -> List[ScrapedComment]:
        """Recursively parse comment tree."""
        comments = []
        
        if not isinstance(data, dict):
            return comments
        
        children = data.get('data', {}).get('children', [])
        
        for child in children:
            kind = child.get('kind')
            
            if kind == 't1':  # Comment
                d = child.get('data', {})
                comment = ScrapedComment(
                    id=d.get('id', ''),
                    post_id=post_id,
                    parent_id=d.get('parent_id', ''),
                    author=d.get('author', ''),
                    body=d.get('body', ''),
                    score=d.get('score', 0),
                    created_utc=d.get('created_utc', 0),
                    depth=depth
                )
                
                # Parse nested replies
                replies = d.get('replies')
                if replies and isinstance(replies, dict):
                    comment.replies = self._parse_comments(replies, post_id, depth + 1)
                
                comments.append(comment)
            
            elif kind == 'more':
                # Truncated comments - skip for now
                pass
        
        return comments