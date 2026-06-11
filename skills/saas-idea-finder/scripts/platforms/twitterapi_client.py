#!/usr/bin/env python3
"""
TwitterAPI.io client for SaaS idea discovery.

Direct REST API client for TwitterAPI.io - replaces Xpoz MCP for Twitter scraping.
Documentation: https://twitterapi.io/
"""
import os
import sys
import time
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'shared'))
from credentials import load_credential, CredentialNotFound


@dataclass
class TwitterAPITweet:
    """Standardized tweet structure from TwitterAPI.io."""
    id: str
    text: str
    author_username: str
    author_name: str
    author_id: str
    created_at: str
    like_count: int
    retweet_count: int
    reply_count: int
    quote_count: int
    view_count: int
    is_reply: bool
    url: str
    lang: str
    hashtags: List[str]
    mentions: List[str]
    entities: Dict[str, Any]
    
    @classmethod
    def from_api_response(cls, data: Dict[str, Any]) -> 'TwitterAPITweet':
        """Create TwitterAPITweet from API response dictionary."""
        author = data.get('author', {})
        entities = data.get('entities', {})
        
        # Extract hashtags
        hashtags = []
        for hashtag in entities.get('hashtags', []):
            if isinstance(hashtag, dict) and 'text' in hashtag:
                hashtags.append(hashtag['text'])
        
        # Extract mentions
        mentions = []
        for mention in entities.get('user_mentions', []):
            if isinstance(mention, dict) and 'screen_name' in mention:
                mentions.append(mention['screen_name'])
        
        # Build URL from author and tweet ID
        tweet_id = data.get('id', '')
        author_username = author.get('userName', '')
        url = data.get('url', '')
        if not url and tweet_id and author_username:
            url = f"https://twitter.com/{author_username}/status/{tweet_id}"
        
        return cls(
            id=tweet_id,
            text=data.get('text', ''),
            author_username=author_username,
            author_name=author.get('name', ''),
            author_id=author.get('id', ''),
            created_at=data.get('createdAt', ''),
            like_count=data.get('likeCount', 0) or 0,
            retweet_count=data.get('retweetCount', 0) or 0,
            reply_count=data.get('replyCount', 0) or 0,
            quote_count=data.get('quoteCount', 0) or 0,
            view_count=data.get('viewCount', 0) or 0,
            is_reply=data.get('isReply', False) or False,
            url=url,
            lang=data.get('lang', ''),
            hashtags=hashtags,
            mentions=mentions,
            entities=entities
        )


class TwitterAPIError(Exception):
    """Raised when TwitterAPI.io request fails."""
    pass


class TwitterAPIRateLimitError(TwitterAPIError):
    """Raised when rate limit is exceeded."""
    pass


class TwitterAPIAuthError(TwitterAPIError):
    """Raised when authentication fails."""
    pass


class TwitterAPIClient:
    """
    Client for TwitterAPI.io REST API.
    
    Provides methods to search tweets, get user info, and retrieve tweet details.
    Handles authentication, pagination, and rate limiting.
    
    Authentication:
        - Uses X-API-Key header
        - Loads credential from: env var TWITTERAPI_KEY → a shell startup file such as ~/.bashrc
    
    Usage:
        client = TwitterAPIClient()
        tweets = client.search_tweets("#buildinpublic", limit=50)
    """
    
    BASE_URL = "https://api.twitterapi.io"
    DEFAULT_TIMEOUT = 30
    MAX_RETRIES = 3
    RETRY_DELAY = 1  # seconds
    RATE_LIMIT_DELAY = 60  # seconds to wait on rate limit
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize TwitterAPI.io client.
        
        Args:
            api_key: Optional API key. If not provided, loads from credential chain.
        
        Raises:
            CredentialNotFound: If API key cannot be loaded.
        """
        if api_key:
            self._api_key = api_key
        else:
            self._api_key = self._load_api_key()
        
        self._session = requests.Session()
        self._session.headers.update({
            'X-API-Key': self._api_key,
            'Accept': 'application/json'
        })
    
    def _load_api_key(self) -> str:
        """Load API key using credential hierarchy."""
        try:
            key = load_credential('TWITTERAPI_KEY', required=True)
            if key:
                return key
        except Exception as e:
            print(f"Warning: Error loading credential: {e}", file=sys.stderr)
        
        raise CredentialNotFound(
            "TWITTERAPI_KEY not found. Set it in environment or a shell startup file such as ~/.bashrc"
        )
    
    def _make_request(
        self, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None,
        retry_count: int = 0
    ) -> Dict[str, Any]:
        """
        Make HTTP request to TwitterAPI.io.
        
        Args:
            endpoint: API endpoint path (e.g., '/twitter/tweet/advanced_search')
            params: Query parameters
            retry_count: Current retry attempt
        
        Returns:
            JSON response as dictionary
        
        Raises:
            TwitterAPIAuthError: On authentication failure
            TwitterAPIRateLimitError: On rate limit
            TwitterAPIError: On other API errors
        """
        url = f"{self.BASE_URL}{endpoint}"
        
        try:
            response = self._session.get(
                url,
                params=params,
                timeout=self.DEFAULT_TIMEOUT
            )
            
            # Handle specific HTTP errors
            if response.status_code == 401:
                raise TwitterAPIAuthError("Invalid API key or unauthorized")
            elif response.status_code == 429:
                raise TwitterAPIRateLimitError("Rate limit exceeded")
            elif response.status_code >= 500:
                # Server error, retry if possible
                if retry_count < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY * (retry_count + 1))
                    return self._make_request(endpoint, params, retry_count + 1)
                raise TwitterAPIError(f"Server error {response.status_code}: {response.text}")
            elif response.status_code != 200:
                raise TwitterAPIError(f"HTTP {response.status_code}: {response.text}")
            
            return response.json()
            
        except TwitterAPIRateLimitError:
            # Don't retry rate limits immediately - propagate up
            raise
            
        except requests.exceptions.Timeout:
            if retry_count < self.MAX_RETRIES:
                time.sleep(self.RETRY_DELAY * (retry_count + 1))
                return self._make_request(endpoint, params, retry_count + 1)
            raise TwitterAPIError("Request timed out after retries")
            
        except requests.exceptions.RequestException as e:
            if retry_count < self.MAX_RETRIES:
                time.sleep(self.RETRY_DELAY * (retry_count + 1))
                return self._make_request(endpoint, params, retry_count + 1)
            raise TwitterAPIError(f"Request failed: {e}")
    
    def search_tweets(
        self,
        query: str,
        query_type: str = "Latest",
        limit: int = 50,
        cursor: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Search tweets using TwitterAPI.io advanced search.
        
        Args:
            query: Search query (supports Twitter advanced search operators)
                   Examples: "#buildinpublic", "AI dev tools", "from:elonmusk"
            query_type: "Latest" or "Top"
            limit: Maximum tweets to return (default 50, max ~20 per API call)
            cursor: Pagination cursor for next page
        
        Returns:
            Dictionary with:
                - tweets: List of TwitterAPITweet objects
                - has_next_page: Boolean indicating more results available
                - next_cursor: Cursor string for next page (if available)
        
        Raises:
            TwitterAPIError: On API error
        
        Example:
            >>> client = TwitterAPIClient()
            >>> result = client.search_tweets("#buildinpublic", limit=20)
            >>> for tweet in result['tweets']:
            ...     print(f"@{tweet.author_username}: {tweet.text[:100]}")
        """
        params = {
            'query': query,
            'queryType': query_type
        }
        
        if cursor:
            params['cursor'] = cursor
        
        data = self._make_request('/twitter/tweet/advanced_search', params)
        
        # Parse tweets from response
        tweets = []
        for tweet_data in data.get('tweets', []):
            try:
                tweet = TwitterAPITweet.from_api_response(tweet_data)
                tweets.append(tweet)
            except Exception as e:
                print(f"Warning: Failed to parse tweet: {e}", file=sys.stderr)
                continue
        
        return {
            'tweets': tweets,
            'has_next_page': data.get('has_next_page', False),
            'next_cursor': data.get('next_cursor', '')
        }
    
    def search_tweets_paginated(
        self,
        query: str,
        query_type: str = "Latest",
        limit: int = 50
    ) -> List[TwitterAPITweet]:
        """
        Search tweets with automatic pagination to get more results.
        
        Args:
            query: Search query
            query_type: "Latest" or "Top"
            limit: Maximum tweets to return
        
        Returns:
            List of TwitterAPITweet objects
        
        Note:
            API returns ~20 tweets per page. This method makes multiple calls
            to reach the desired limit.
        """
        all_tweets = []
        cursor = None
        max_pages = (limit // 20) + 2  # Approximate pages needed
        
        for _ in range(max_pages):
            remaining = limit - len(all_tweets)
            if remaining <= 0:
                break
            
            result = self.search_tweets(
                query=query,
                query_type=query_type,
                limit=min(remaining, 20),
                cursor=cursor
            )
            
            tweets = result.get('tweets', [])
            all_tweets.extend(tweets)
            
            if not result.get('has_next_page') or not result.get('next_cursor'):
                break
            
            cursor = result.get('next_cursor')
            
            # Small delay to be respectful to the API
            if len(all_tweets) < limit:
                time.sleep(0.1)
        
        return all_tweets[:limit]
    
    def get_tweet_by_id(self, tweet_id: str) -> Optional[TwitterAPITweet]:
        """
        Get tweet details by ID.
        
        Args:
            tweet_id: Tweet ID
        
        Returns:
            TwitterAPITweet object or None if not found
        """
        params = {'tweet_ids': tweet_id}
        data = self._make_request('/twitter/tweets', params)
        
        tweets = data.get('tweets', [])
        if tweets:
            return TwitterAPITweet.from_api_response(tweets[0])
        return None
    
    def get_user_info(self, username: Optional[str] = None, user_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get user profile information.
        
        Args:
            username: Twitter screen name (without @)
            user_id: Twitter user ID
        
        Returns:
            User data dictionary
        
        Raises:
            ValueError: If neither username nor user_id provided
        """
        if not username and not user_id:
            raise ValueError("Either username or user_id must be provided")
        
        params = {}
        if username:
            params['userName'] = username
        if user_id:
            params['userId'] = user_id
        
        return self._make_request('/twitter/user/info', params)
    
    def get_user_last_tweets(
        self,
        username: Optional[str] = None,
        user_id: Optional[str] = None,
        include_replies: bool = False,
        limit: int = 20
    ) -> List[TwitterAPITweet]:
        """
        Get user's recent tweets.
        
        Args:
            username: Twitter screen name
            user_id: Twitter user ID
            include_replies: Whether to include reply tweets
            limit: Maximum tweets to return
        
        Returns:
            List of TwitterAPITweet objects
        """
        if not username and not user_id:
            raise ValueError("Either username or user_id must be provided")
        
        params = {'includeReplies': str(include_replies).lower()}
        if username:
            params['userName'] = username
        if user_id:
            params['userId'] = user_id
        
        all_tweets = []
        cursor = None
        
        while len(all_tweets) < limit:
            if cursor:
                params['cursor'] = cursor
            
            data = self._make_request('/twitter/user/last_tweets', params)
            tweets_data = data.get('tweets', [])
            
            if not tweets_data:
                break
            
            for tweet_data in tweets_data:
                try:
                    tweet = TwitterAPITweet.from_api_response(tweet_data)
                    all_tweets.append(tweet)
                except Exception as e:
                    print(f"Warning: Failed to parse tweet: {e}", file=sys.stderr)
                    continue
            
            # Check for more pages
            if len(tweets_data) < 20:
                break
            
            # Get next cursor from last tweet
            if tweets_data:
                # API returns cursor in pagination info usually
                # This is a simplified approach
                break
        
        return all_tweets[:limit]
    
    def close(self):
        """Close the HTTP session."""
        self._session.close()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()


# Convenience functions for simple use cases

def search_tweets(query: str, limit: int = 50, api_key: Optional[str] = None) -> List[TwitterAPITweet]:
    """
    Simple function to search tweets without managing client lifecycle.
    
    Args:
        query: Search query
        limit: Maximum tweets to return
        api_key: Optional API key (loads from env or a shell startup file such as ~/.bashrc if not provided)
    
    Returns:
        List of TwitterAPITweet objects
    """
    with TwitterAPIClient(api_key) as client:
        return client.search_tweets_paginated(query, limit=limit)


def search_hashtag(hashtag: str, limit: int = 50, api_key: Optional[str] = None) -> List[TwitterAPITweet]:
    """
    Search tweets by hashtag.
    
    Args:
        hashtag: Hashtag with or without # prefix
        limit: Maximum tweets to return
        api_key: Optional API key
    
    Returns:
        List of TwitterAPITweet objects
    """
    # Ensure hashtag has # prefix
    if not hashtag.startswith('#'):
        hashtag = f'#{hashtag}'
    
    return search_tweets(hashtag, limit=limit, api_key=api_key)


if __name__ == '__main__':
    # Simple test
    print("TwitterAPI.io Client - Test Mode")
    print("=" * 50)
    
    try:
        client = TwitterAPIClient()
        print("✓ Client initialized successfully")
        
        # Test hashtag search
        print("\nSearching for #buildinpublic (limit: 5)...")
        result = client.search_tweets("#buildinpublic", limit=5)
        
        tweets = result.get('tweets', [])
        print(f"✓ Found {len(tweets)} tweets")
        
        for i, tweet in enumerate(tweets[:3], 1):
            print(f"\n{i}. @{tweet.author_username} ({tweet.like_count} likes)")
            print(f"   {tweet.text[:100]}...")
        
        client.close()
        print("\n✓ Test completed successfully")
        
    except CredentialNotFound as e:
        print(f"✗ Credential error: {e}")
        sys.exit(1)
    except TwitterAPIError as e:
        print(f"✗ API error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)