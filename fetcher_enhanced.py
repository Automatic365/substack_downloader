"""
Enhanced Substack Fetcher with logging, retries, caching, and concurrency
"""
import os
import pickle
import requests
import time
from typing import List, Optional
from pathlib import Path
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm

from config import (
    REQUEST_TIMEOUT, MAX_RETRIES, RETRY_BACKOFF_FACTOR,
    RETRY_STATUS_CODES, USER_AGENT, CONTENT_SELECTORS,
    API_LIMIT_PER_REQUEST, RATE_LIMIT_DELAY, ENABLE_CACHE,
    CACHE_DIR, MAX_CONCURRENT_FETCHES
)
from logger import setup_logger
from models import Post
from utils import get_cache_key

logger = setup_logger(__name__)


class SubstackFetcherEnhanced:
    """
    Enhanced fetcher with retry logic, caching, and concurrent downloads.
    """

    def __init__(self, url: str, cookie: Optional[str] = None, enable_cache: bool = ENABLE_CACHE):
        """
        Initialize fetcher with validation and retry session.

        Args:
            url: Substack newsletter URL
            cookie: Optional cookie for paywalled content
            enable_cache: Enable caching of fetched content

        Raises:
            ValueError: If URL is invalid
        """
        # Validate URL format
        if not url or not isinstance(url, str):
            raise ValueError("URL must be a non-empty string")

        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL format: {url}")

        # Security: Enforce HTTPS when using authentication
        if parsed.scheme == 'http':
            if cookie:
                raise ValueError(
                    "Security Error: Cannot use authentication cookie with HTTP URL. "
                    "Use HTTPS to protect your credentials."
                )
            logger.warning(
                f"⚠️  WARNING: Using HTTP instead of HTTPS for {url}. "
                "Connection is not encrypted!"
            )

        self.url = url.rstrip('/')
        self.api_url = f"{self.url}/api/v1/archive"
        self.enable_cache = enable_cache

        # Setup cache directory
        if self.enable_cache:
            self.cache_dir = Path(CACHE_DIR)
            self.cache_dir.mkdir(exist_ok=True)
            logger.info(f"Cache enabled at {self.cache_dir}")
        else:
            self.cache_dir = None

        # Setup headers
        self.headers = {
            'User-Agent': USER_AGENT,
            'Referer': 'https://substack.com/'
        }
        if cookie:
            # Ensure cookie is formatted as a key-value pair if only value is provided
            if "substack.sid=" not in cookie:
                self.headers['Cookie'] = f"substack.sid={cookie}"
            else:
                self.headers['Cookie'] = cookie
            logger.info("Cookie provided for authenticated requests")

        # Create session with retry logic
        self.session = self._create_retry_session()

        logger.info(f"Initialized fetcher for {self.url}")

    def _create_retry_session(self) -> requests.Session:
        """
        Create a requests session with automatic retry logic.

        Returns:
            Configured requests Session
        """
        session = requests.Session()

        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=RETRY_BACKOFF_FACTOR,
            status_forcelist=RETRY_STATUS_CODES,
            allowed_methods=["GET"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        logger.debug(f"Created session with {MAX_RETRIES} retries, backoff factor {RETRY_BACKOFF_FACTOR}")
        return session

    def get_newsletter_title(self) -> str:
        """
        Fetch the newsletter title from the main page.

        Returns:
            Newsletter title or default fallback
        """
        logger.info(f"Fetching newsletter title from {self.url}")

        try:
            response = self.session.get(
                self.url,
                headers=self.headers,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.title.string if soup.title else "Substack Archive"
            title = title.strip()

            logger.info(f"Newsletter title: {title}")
            return title

        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching title from {self.url}")
            return "Substack Archive"
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching title: {e}")
            return "Substack Archive"
        except (AttributeError, TypeError) as e:
            logger.error(f"Error parsing title: {e}")
            return "Substack Archive"

    def fetch_archive_metadata(self, limit: Optional[int] = None) -> List[Post]:
        """
        Fetch metadata for all posts using the Archive API.

        Args:
            limit: Optional limit on number of posts to fetch

        Returns:
            List of Post objects, sorted by date (oldest first)
        """
        logger.info(f"Fetching archive from: {self.api_url}")
        posts: List[Post] = []
        offset = 0

        # Progress bar
        pbar = tqdm(total=limit if limit else None, desc="Fetching metadata", unit="post")

        try:
            while True:
                params = {
                    'sort': 'new',
                    'search': '',
                    'offset': offset,
                    'limit': API_LIMIT_PER_REQUEST
                }

                try:
                    response = self.session.get(
                        self.api_url,
                        params=params,
                        headers=self.headers,
                        timeout=REQUEST_TIMEOUT
                    )
                    response.raise_for_status()
                    data = response.json()

                except requests.exceptions.Timeout:
                    logger.error(f"API timeout at offset {offset}")
                    break
                except requests.exceptions.HTTPError as e:
                    logger.error(f"API HTTP error: {e}")
                    break
                except (ValueError, requests.exceptions.JSONDecodeError) as e:
                    logger.error(f"API returned invalid JSON: {e}")
                    break
                except requests.exceptions.RequestException as e:
                    logger.error(f"API connection error: {e}")
                    break

                # Parse API response
                new_posts = self._parse_api_response(data)

                if not new_posts:
                    break

                # Convert to Post objects
                for item in new_posts:
                    post = Post.from_api_response(item)
                    if post:
                        posts.append(post)
                        pbar.update(1)

                        if limit and len(posts) >= limit:
                            posts = posts[:limit]
                            break

                if limit and len(posts) >= limit:
                    break

                offset += len(new_posts)

                # If we got fewer than requested, we're at the end
                if len(new_posts) < API_LIMIT_PER_REQUEST:
                    break

                # Be nice to the API
                time.sleep(RATE_LIMIT_DELAY)

        finally:
            pbar.close()

        # Sort by date: oldest first
        posts.sort(key=lambda x: x.pub_date)
        logger.info(f"Found {len(posts)} posts in archive")
        return posts

    def _parse_api_response(self, data: any) -> List[dict]:
        """
        Parse API response and extract posts list.

        Args:
            data: JSON response from API

        Returns:
            List of post dictionaries
        """
        if isinstance(data, list):
            return data
        elif isinstance(data, dict) and 'posts' in data:
            posts_list = data['posts']
            if not isinstance(posts_list, list):
                logger.warning(f"API 'posts' field is {type(posts_list)}, expected list")
                return []
            return posts_list
        else:
            logger.warning(f"Unexpected API response format: {type(data)}")
            return []

    def fetch_post_content(self, url: str) -> str:
        """
        Fetch the full HTML content of a single post.

        Args:
            url: Post URL

        Returns:
            HTML content string (empty on failure)
        """
        # Check cache first
        if self.enable_cache:
            cached = self._get_from_cache(url)
            if cached is not None:
                logger.debug(f"Using cached content for {url}")
                return cached

        try:
            response = self.session.get(
                url,
                headers=self.headers,
                timeout=REQUEST_TIMEOUT
            )
            response.raise_for_status()

            content = self._extract_content(response.content, url)

            # Cache the result
            if self.enable_cache and content:
                self._save_to_cache(url, content)

            return content

        except requests.exceptions.Timeout:
            logger.error(f"Timeout fetching content from {url}")
            return ""
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching content from {url}: {e}")
            return ""
        except MemoryError:
            logger.error(f"Content too large from {url}")
            return ""
        except Exception as e:
            logger.error(f"Unexpected error fetching content from {url}: {type(e).__name__}: {e}")
            return ""

    def _extract_content(self, html: bytes, url: str) -> str:
        """
        Extract content from HTML using multiple selectors.

        Args:
            html: HTML content bytes
            url: URL for logging

        Returns:
            Extracted HTML content string
        """
        soup = BeautifulSoup(html, 'html.parser')

        # Try multiple selectors
        for tag, class_name in CONTENT_SELECTORS:
            if class_name:
                content_div = soup.find(tag, class_=class_name)
            else:
                content_div = soup.find(tag)

            if content_div:
                logger.debug(f"Found content using selector: {tag}.{class_name or '*'}")
                return str(content_div)

        # Final fallback: use body
        body = soup.find('body')
        if body:
            logger.warning(f"Could not find expected content structure in {url}, using body")
            return str(body)

        logger.warning(f"No content found for {url}")
        return ""

    def fetch_all_content_concurrent(self, posts: List[Post], max_workers: int = MAX_CONCURRENT_FETCHES) -> List[Post]:
        """
        Fetch content for all posts concurrently.

        Args:
            posts: List of Post objects
            max_workers: Maximum concurrent requests

        Returns:
            List of Post objects with content filled in
        """
        logger.info(f"Fetching content for {len(posts)} posts with {max_workers} workers")

        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all fetch tasks
            future_to_post = {
                executor.submit(self.fetch_post_content, post.link): post
                for post in posts
            }

            # Process completed tasks with progress bar
            with tqdm(total=len(posts), desc="Fetching content", unit="post") as pbar:
                for future in as_completed(future_to_post):
                    post = future_to_post[future]
                    try:
                        post.content = future.result()
                        if not post.content:
                            logger.warning(f"No content retrieved for {post.link}")
                    except Exception as e:
                        logger.error(f"Failed to fetch {post.link}: {e}")
                        post.content = ""
                    finally:
                        pbar.update(1)
                        time.sleep(RATE_LIMIT_DELAY / max_workers)  # Distributed rate limiting

        return posts

    def _get_from_cache(self, url: str) -> Optional[str]:
        """Get content from cache if it exists."""
        if not self.cache_dir:
            return None

        cache_key = get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.pkl"

        if cache_file.exists():
            try:
                with cache_file.open('rb') as f:
                    return pickle.load(f)
            except Exception as e:
                logger.warning(f"Failed to load cache for {url}: {e}")
                return None

        return None

    def _save_to_cache(self, url: str, content: str) -> None:
        """Save content to cache."""
        if not self.cache_dir:
            return

        cache_key = get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.pkl"

        try:
            with cache_file.open('wb') as f:
                pickle.dump(content, f)
            logger.debug(f"Cached content for {url}")
        except Exception as e:
            logger.warning(f"Failed to cache {url}: {e}")

    def clear_cache(self) -> None:
        """Clear all cached content."""
        if not self.cache_dir:
            logger.info("Cache not enabled")
            return

        if self.cache_dir.exists():
            cache_files = list(self.cache_dir.glob("*.pkl"))
            for cache_file in cache_files:
                cache_file.unlink()
            logger.info(f"Cleared {len(cache_files)} cached files")
        else:
            logger.info("Cache directory does not exist")

    def verify_auth(self) -> bool:
        """
        Verifies if the current session is authenticated by checking the subscriptions endpoint.

        Returns:
            bool: True if authenticated, False otherwise
        """
        if 'Cookie' not in self.headers:
            return False

        # Use the subscriptions endpoint as it requires authentication
        auth_url = "https://substack.com/api/v1/subscriptions"
        
        try:
            response = self.session.get(
                auth_url,
                headers=self.headers,
                timeout=REQUEST_TIMEOUT
            )
            # If we get a 200 OK, the session is valid
            if response.status_code == 200:
                logger.info("Authentication verification successful")
                return True
            
            # 401 Unauthorized means invalid cookie
            logger.warning(f"Authentication verification failed with status {response.status_code}")
            return False
        except requests.exceptions.RequestException as e:
            logger.error(f"Error verifying authentication: {e}")
            return False
