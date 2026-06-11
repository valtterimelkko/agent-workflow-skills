#!/usr/bin/env python3
"""
Production-quality Twitter/X scraper using TwitterAPI.io.

Features:
- Simple API key authentication (no OAuth required)
- Rate limit handling with exponential backoff
- Pagination support for large result sets
- Circuit breaker pattern for resilience
- Comprehensive retry logic

Usage:
    scraper = TwitterScraper()
    tweets = await scraper.search_tweets("python programming", limit=50)
    await scraper.close()
"""
import asyncio
import json
import random
import time
from typing import List, Dict, Any, Optional, Tuple

# Try to use httpx for async, fall back to requests
try:
    import httpx
    HAS_HTTPX = True
except ImportError:
    import requests
    HAS_HTTPX = False

from scripts.utils import (
    ScrapedTweet, ScrapedReply, TwitterUser, TrendingTopic,
    TweetThread, RateLimitInfo, SearchPagination,
    parse_tweet_date, format_tweet_url, extract_hashtags, extract_mentions
)
from scripts.credentials import load_twitterapi_key


class CircuitBreaker:
    """Simple circuit breaker pattern for API calls."""
    
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


class TwitterScraper:
    """
    Production-quality Twitter/X scraper using TwitterAPI.io.
    """
    
    BASE_URL = "https://api.twitterapi.io"
    
    # Rotate through multiple realistic browser User-Agents
    USER_AGENTS = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:121.0) Gecko/20100101 Firefox/121.0",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the scraper.
        
        Args:
            api_key: Optional API key (auto-loaded from credentials if not provided)
        """
        self._client = None
        self._session = None
        self._rate_limit = RateLimitInfo()
        self._last_request_time = 0
        self._ua_index = 0
        
        # Load API key from credential hierarchy
        self._api_key = api_key or load_twitterapi_key(required=True)
        
        # Circuit breaker for resilience
        self._circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=600)
        
        # Rate limiting - TwitterAPI.io supports 1000+ req/sec for paid users
        # But we use conservative delays for reliability
        self._min_delay = 0.5  # 0.5 seconds between requests (120 req/min)
        
        print("TwitterAPI.io scraper initialized")
    
    async def _get_client(self):
        """Get or create HTTP client."""
        if HAS_HTTPX:
            if self._client is None or self._client.is_closed:
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
            return self._session
    
    def _get_headers(self) -> Dict[str, str]:
        """Get request headers with API key."""
        return {
            "x-api-key": self._api_key,
            "User-Agent": self.USER_AGENTS[self._ua_index % len(self.USER_AGENTS)],
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
        jitter = random.uniform(0.1, 0.5)
        total_delay = max(0, delay - elapsed + jitter)
        
        if total_delay > 0:
            await asyncio.sleep(total_delay)
        
        self._last_request_time = time.time()
    
    async def _make_request(
        self, 
        endpoint: str, 
        params: Optional[Dict] = None,
        max_retries: int = 5
    ) -> Optional[Dict]:
        """
        Make HTTP request with retry logic and circuit breaker.
        
        Args:
            endpoint: API endpoint (e.g., '/twitter/tweet/advanced_search')
            params: Query parameters
            max_retries: Number of retry attempts
            
        Returns:
            Parsed JSON response or None on failure
        """
        if not self._circuit_breaker.can_execute():
            print(f"Circuit breaker OPEN - skipping request to avoid cascading failures")
            return None
        
        url = f"{self.BASE_URL}{endpoint}"
        
        for attempt in range(max_retries):
            await self._rate_limit_delay()
            
            try:
                if HAS_HTTPX:
                    client = await self._get_client()
                    response = await client.get(url, params=params)
                else:
                    loop = asyncio.get_event_loop()
                    response = await loop.run_in_executor(
                        None, 
                        lambda: self._session.get(url, params=params, timeout=30)
                    )
                
                # Update rate limit info from headers if available
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
                
                # Handle 401 - bad API key
                if response.status_code == 401:
                    print(f"HTTP 401 - Invalid API key")
                    self._circuit_breaker.record_failure()
                    return None
                
                # Handle 403 Forbidden
                if response.status_code == 403:
                    print(f"HTTP 403 for {endpoint}")
                    if attempt < max_retries - 1:
                        print(f"Rotating User-Agent and retrying...")
                        self._rotate_user_agent()
                    continue
                
                # Handle other errors
                if response.status_code != 200:
                    print(f"HTTP {response.status_code} for {endpoint}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(2 ** attempt)
                    continue
                
                # Parse JSON response
                try:
                    data = response.json()
                except json.JSONDecodeError as e:
                    print(f"JSON parse error: {e}")
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
    
    # =================================================================
    # PUBLIC API METHODS
    # =================================================================
    
    async def search_tweets(
        self,
        query: str,
        limit: int = 50,
        query_type: str = "Latest",
        since_id: Optional[str] = None,
        until_id: Optional[str] = None
    ) -> Tuple[List[ScrapedTweet], SearchPagination]:
        """
        Search tweets using advanced search.
        
        Args:
            query: Search query (supports Twitter advanced search operators)
            limit: Maximum tweets to fetch
            query_type: "Latest" or "Top"
            since_id: Fetch tweets newer than this ID
            until_id: Fetch tweets older than this ID
            
        Returns:
            Tuple of (tweets, pagination_info)
            
        Advanced Search Operators:
            - from:username - Tweets from specific user
            - to:username - Tweets sent to user
            - @username - Tweets mentioning user
            - #hashtag - Tweets with hashtag
            - "exact phrase" - Exact phrase match
            - min_retweets:100 - Minimum retweets
            - min_faves:500 - Minimum likes
            - since:YYYY-MM-DD - Start date
            - until:YYYY-MM-DD - End date
            - lang:en - Language filter
            - -filter:replies - Exclude replies
        """
        all_tweets = []
        cursor = None
        last_min_id = until_id
        pages = 0
        max_pages = (limit // 20) + 5  # Approximate pages needed
        
        while len(all_tweets) < limit and pages < max_pages:
            params = {
                "query": query,
                "queryType": query_type
            }
            
            if cursor:
                params["cursor"] = cursor
            elif last_min_id:
                # Use max_id technique for deep pagination
                params["query"] = f"{query} max_id:{last_min_id}"
            
            if since_id:
                params["query"] = f"{params['query']} since_id:{since_id}"
            
            data = await self._make_request("/twitter/tweet/advanced_search", params)
            
            if not data:
                break
            
            tweets = self._parse_tweet_list(data.get("tweets", []))
            all_tweets.extend(tweets)
            
            # Check for more pages
            has_next = data.get("has_next_page", False)
            cursor = data.get("next_cursor")
            
            if not has_next or not cursor:
                # Try max_id pagination
                if tweets:
                    last_min_id = min(t.id for t in tweets)
                    cursor = None
                else:
                    break
            
            pages += 1
            
            # Stop if we got no new tweets
            if not tweets:
                break
        
        pagination = SearchPagination(
            has_next_page=bool(cursor or last_min_id),
            next_cursor=cursor,
            last_min_id=last_min_id,
            query=query
        )
        
        return all_tweets[:limit], pagination
    
    async def get_user_by_username(self, username: str) -> Optional[TwitterUser]:
        """Get user profile by username."""
        params = {"userName": username}
        
        data = await self._make_request("/twitter/user/get_user_by_username", params)
        
        if not data or "data" not in data:
            return None
        
        return self._parse_user(data["data"])
    
    async def get_user_tweets(
        self,
        username: str,
        limit: int = 50
    ) -> Tuple[List[ScrapedTweet], SearchPagination]:
        """
        Get recent tweets from a user.
        
        Args:
            username: Twitter username (without @)
            limit: Maximum tweets to fetch
            
        Returns:
            Tuple of (tweets, pagination_info)
        """
        all_tweets = []
        cursor = None
        pages = 0
        max_pages = (limit // 20) + 5
        
        while len(all_tweets) < limit and pages < max_pages:
            params = {"userName": username}
            if cursor:
                params["cursor"] = cursor
            
            data = await self._make_request("/twitter/user/last_tweets", params)
            
            if not data:
                break
            
            tweets = self._parse_tweet_list(data.get("tweets", []))
            all_tweets.extend(tweets)
            
            has_next = data.get("has_next_page", False)
            cursor = data.get("next_cursor")
            
            if not has_next or not cursor:
                break
            
            pages += 1
        
        pagination = SearchPagination(
            has_next_page=bool(cursor),
            next_cursor=cursor,
            last_min_id=None,
            query=f"from:{username}"
        )
        
        return all_tweets[:limit], pagination
    
    async def get_tweet_replies(
        self,
        tweet_id: str,
        limit: int = 50
    ) -> Tuple[List[ScrapedReply], SearchPagination]:
        """
        Get replies to a tweet.
        
        Args:
            tweet_id: The tweet ID to get replies for
            limit: Maximum replies to fetch
            
        Returns:
            Tuple of (replies, pagination_info)
        """
        all_replies = []
        cursor = None
        pages = 0
        max_pages = (limit // 20) + 5
        
        while len(all_replies) < limit and pages < max_pages:
            params = {"tweetId": tweet_id}
            if cursor:
                params["cursor"] = cursor
            
            data = await self._make_request("/twitter/tweet/replies", params)
            
            if not data:
                break
            
            replies = self._parse_reply_list(data.get("replies", []), tweet_id)
            all_replies.extend(replies)
            
            has_next = data.get("has_next_page", False)
            cursor = data.get("next_cursor")
            
            if not has_next or not cursor:
                break
            
            pages += 1
        
        pagination = SearchPagination(
            has_next_page=bool(cursor),
            next_cursor=cursor,
            last_min_id=None,
            query=f"replies_to:{tweet_id}"
        )
        
        return all_replies[:limit], pagination
    
    async def get_tweet_thread(self, tweet_id: str) -> Optional[TweetThread]:
        """
        Get a tweet and its thread context.
        
        Args:
            tweet_id: The root tweet ID
            
        Returns:
            TweetThread object or None
        """
        # Get thread context
        params = {"tweetId": tweet_id}
        data = await self._make_request("/twitter/tweet/thread_context", params)
        
        if not data:
            return None
        
        thread_tweets = self._parse_tweet_list(data.get("tweets", []))
        
        # Get replies
        replies, _ = await self.get_tweet_replies(tweet_id, limit=100)
        
        return TweetThread(
            root_tweet_id=tweet_id,
            tweets=thread_tweets,
            replies=replies
        )
    
    async def search_users(
        self,
        query: str,
        limit: int = 20
    ) -> List[TwitterUser]:
        """
        Search for users by keyword.
        
        Args:
            query: Search query
            limit: Maximum users to fetch
            
        Returns:
            List of TwitterUser objects
        """
        params = {"query": query}
        
        data = await self._make_request("/twitter/user/search", params)
        
        if not data:
            return []
        
        users = data.get("users", [])[:limit]
        return [self._parse_user(u) for u in users]
    
    async def get_trending_topics(
        self,
        woeid: int = 1,  # 1 = Worldwide
        limit: int = 30
    ) -> List[TrendingTopic]:
        """
        Get trending topics by location.
        
        Args:
            woeid: Yahoo! Where On Earth ID (1 = worldwide)
            limit: Maximum trends to return
            
        Returns:
            List of TrendingTopic objects
        """
        params = {"woeid": woeid}
        
        data = await self._make_request("/twitter/trends", params)
        
        if not data or "trends" not in data:
            return []
        
        trends = []
        for i, trend in enumerate(data["trends"][:limit]):
            trends.append(TrendingTopic(
                name=trend.get("name", ""),
                query=trend.get("query", ""),
                tweet_volume=trend.get("tweet_volume"),
                rank=i + 1,
                woeid=woeid
            ))
        
        return trends
    
    async def get_user_mentions(
        self,
        username: str,
        limit: int = 50
    ) -> Tuple[List[ScrapedTweet], SearchPagination]:
        """
        Get mentions of a user.
        
        Args:
            username: Twitter username (without @)
            limit: Maximum mentions to fetch
            
        Returns:
            Tuple of (mentions, pagination_info)
        """
        all_mentions = []
        cursor = None
        pages = 0
        max_pages = (limit // 20) + 5
        
        while len(all_mentions) < limit and pages < max_pages:
            params = {"userName": username}
            if cursor:
                params["cursor"] = cursor
            
            data = await self._make_request("/twitter/user/mentions", params)
            
            if not data:
                break
            
            mentions = self._parse_tweet_list(data.get("mentions", []))
            all_mentions.extend(mentions)
            
            has_next = data.get("has_next_page", False)
            cursor = data.get("next_cursor")
            
            if not has_next or not cursor:
                break
            
            pages += 1
        
        pagination = SearchPagination(
            has_next_page=bool(cursor),
            next_cursor=cursor,
            last_min_id=None,
            query=f"@{username}"
        )
        
        return all_mentions[:limit], pagination
    
    async def close(self):
        """Close HTTP client."""
        if HAS_HTTPX and self._client:
            await self._client.aclose()
        elif self._session:
            self._session.close()
    
    # =================================================================
    # PRIVATE HELPER METHODS
    # =================================================================
    
    def _parse_tweet_list(self, tweets_data: List[Dict]) -> List[ScrapedTweet]:
        """Parse list of tweet JSON objects into ScrapedTweet objects."""
        tweets = []
        for data in tweets_data:
            tweet = self._parse_single_tweet(data)
            if tweet:
                tweets.append(tweet)
        return tweets
    
    def _parse_single_tweet(self, data: Dict) -> Optional[ScrapedTweet]:
        """Parse a single tweet JSON object into ScrapedTweet."""
        try:
            if not isinstance(data, dict):
                return None
            
            tweet_id = str(data.get("id", ""))
            if not tweet_id:
                return None
            
            # Extract author info
            author = data.get("author", {})
            author_username = author.get("userName", "")
            
            # Build URL
            if author_username:
                url = format_tweet_url(author_username, tweet_id)
            else:
                url = f"https://twitter.com/i/web/status/{tweet_id}"
            
            # Parse metadata
            metadata = {
                "is_reply": data.get("isReply", False),
                "in_reply_to_id": data.get("inReplyToId"),
                "conversation_id": data.get("conversationId"),
                "source": data.get("source", ""),
            }
            
            # Extract hashtags and mentions
            entities = data.get("entities", {})
            hashtags = entities.get("hashtags", [])
            mentions = entities.get("user_mentions", [])
            metadata["hashtags"] = [h.get("text", "").lower() for h in hashtags]
            metadata["mentions"] = [m.get("screen_name", "").lower() for m in mentions]
            
            return ScrapedTweet(
                id=tweet_id,
                text=data.get("text", ""),
                url=url,
                author_username=author_username,
                author_name=author.get("name", ""),
                author_verified=author.get("isBlueVerified", False),
                author_followers=author.get("followers", 0),
                engagement=data.get("likeCount", 0),
                reply_count=data.get("replyCount", 0),
                retweet_count=data.get("retweetCount", 0),
                quote_count=data.get("quoteCount", 0),
                view_count=data.get("viewCount"),
                created_at=data.get("createdAt", ""),
                language=data.get("lang", "en"),
                metadata=metadata
            )
            
        except Exception as e:
            print(f"Error parsing tweet: {e}")
            return None
    
    def _parse_reply_list(self, replies_data: List[Dict], tweet_id: str) -> List[ScrapedReply]:
        """Parse list of reply JSON objects into ScrapedReply objects."""
        replies = []
        for data in replies_data:
            reply = self._parse_single_reply(data, tweet_id)
            if reply:
                replies.append(reply)
        return replies
    
    def _parse_single_reply(self, data: Dict, tweet_id: str) -> Optional[ScrapedReply]:
        """Parse a single reply JSON object into ScrapedReply."""
        try:
            if not isinstance(data, dict):
                return None
            
            reply_id = str(data.get("id", ""))
            if not reply_id:
                return None
            
            author = data.get("author", {})
            
            return ScrapedReply(
                id=reply_id,
                tweet_id=tweet_id,
                parent_id=data.get("inReplyToId"),
                author_username=author.get("userName", ""),
                author_name=author.get("name", ""),
                text=data.get("text", ""),
                engagement=data.get("likeCount", 0),
                created_at=data.get("createdAt", "")
            )
            
        except Exception as e:
            print(f"Error parsing reply: {e}")
            return None
    
    def _parse_user(self, data: Dict) -> TwitterUser:
        """Parse user JSON object into TwitterUser."""
        return TwitterUser(
            id=str(data.get("id", "")),
            username=data.get("userName", ""),
            name=data.get("name", ""),
            description=data.get("description", ""),
            location=data.get("location", ""),
            url=data.get("url", ""),
            profile_image=data.get("profilePicture", ""),
            cover_image=data.get("coverPicture", ""),
            verified=data.get("isBlueVerified", False),
            verified_type=data.get("verifiedType", ""),
            followers=data.get("followers", 0),
            following=data.get("following", 0),
            tweet_count=data.get("statusesCount", 0),
            listed_count=data.get("listedCount", 0),
            favourites_count=data.get("favouritesCount", 0),
            media_count=data.get("mediaCount", 0),
            created_at=data.get("createdAt", ""),
            can_dm=data.get("canDm", False),
            pinned_tweet_ids=data.get("pinnedTweetIds", [])
        )