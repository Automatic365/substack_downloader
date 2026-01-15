import pickle
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Callable, Iterable, List, Optional
from urllib.parse import urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from config import (
    API_LIMIT_PER_REQUEST,
    CACHE_DIR,
    CONTENT_SELECTORS,
    ENABLE_CACHE,
    MAX_CONCURRENT_FETCHES,
    MAX_RETRIES,
    RATE_LIMIT_DELAY,
    REQUEST_TIMEOUT,
    RETRY_BACKOFF_FACTOR,
    RETRY_STATUS_CODES,
    USER_AGENT,
)
from logger import setup_logger
from models import Post
from utils import get_cache_key

logger = setup_logger(__name__)


ProgressCallback = Optional[Callable[[int, Optional[int], Optional[Post]], None]]


class SubstackFetcher:
    def __init__(
        self,
        url: str,
        cookie: Optional[str] = None,
        enable_cache: bool = ENABLE_CACHE,
        enable_retries: bool = True,
        max_concurrent: int = MAX_CONCURRENT_FETCHES,
    ):
        if not url or not isinstance(url, str):
            raise ValueError("URL must be a non-empty string")

        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL format: {url}")

        if parsed.scheme == 'http':
            if cookie:
                raise ValueError(
                    "Security Error: Cannot use authentication cookie with HTTP URL. "
                    "Use HTTPS to protect your credentials."
                )
            logger.warning(
                "Using HTTP instead of HTTPS for %s. Connection is not encrypted.",
                url,
            )

        self.url = url.rstrip('/')
        self.api_url = f"{self.url}/api/v1/archive"
        self.enable_cache = enable_cache
        self.max_concurrent = max_concurrent

        if self.enable_cache:
            self.cache_dir = Path(CACHE_DIR)
            self.cache_dir.mkdir(exist_ok=True)
            logger.info("Cache enabled at %s", self.cache_dir)
        else:
            self.cache_dir = None

        self.headers = {
            'User-Agent': USER_AGENT,
            'Referer': 'https://substack.com/',
        }
        if cookie:
            if "substack.sid=" not in cookie:
                self.headers['Cookie'] = f"substack.sid={cookie}"
            else:
                self.headers['Cookie'] = cookie
            logger.info("Cookie provided for authenticated requests")

        self.session = self._create_session(enable_retries)
        logger.info("Initialized fetcher for %s", self.url)

    def _create_session(self, enable_retries: bool) -> requests.Session:
        session = requests.Session()
        if not enable_retries:
            return session

        retry_strategy = Retry(
            total=MAX_RETRIES,
            backoff_factor=RETRY_BACKOFF_FACTOR,
            status_forcelist=RETRY_STATUS_CODES,
            allowed_methods=["GET"],
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        logger.debug(
            "Created session with %s retries, backoff factor %s",
            MAX_RETRIES,
            RETRY_BACKOFF_FACTOR,
        )
        return session

    def get_newsletter_title(self) -> str:
        try:
            response = self.session.get(
                self.url,
                headers=self.headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.title.string if soup.title else "Substack Archive"
            return title.strip()
        except requests.exceptions.Timeout:
            logger.error("Timeout fetching title from %s", self.url)
            return "Substack Archive"
        except requests.exceptions.RequestException as exc:
            logger.error("Error fetching title: %s", exc)
            return "Substack Archive"
        except (AttributeError, TypeError) as exc:
            logger.error("Error parsing title: %s", exc)
            return "Substack Archive"

    def get_newsletter_author(self) -> str:
        try:
            response = self.session.get(
                self.url,
                headers=self.headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            author_meta = soup.find('meta', attrs={'name': 'author'})
            if author_meta and author_meta.get('content'):
                return author_meta['content'].strip()

            publisher_meta = soup.find('meta', attrs={'property': 'article:publisher'})
            if publisher_meta and publisher_meta.get('content'):
                return publisher_meta['content'].strip()

            author_link = soup.find('a', class_=lambda x: x and 'author' in str(x).lower())
            if author_link:
                return author_link.get_text().strip()

            parsed = urlparse(self.url)
            subdomain = parsed.netloc.split('.')[0]
            if subdomain and subdomain != 'www':
                return ' '.join(word.capitalize() for word in subdomain.split('-'))

            return "Unknown Author"
        except requests.exceptions.Timeout:
            logger.error("Timeout fetching author from %s", self.url)
            return "Unknown Author"
        except requests.exceptions.RequestException as exc:
            logger.error("Error fetching author: %s", exc)
            return "Unknown Author"
        except Exception as exc:
            logger.error("Error parsing author: %s", exc)
            return "Unknown Author"

    def fetch_archive_metadata(
        self,
        limit: Optional[int] = None,
        progress_callback: ProgressCallback = None,
    ) -> List[Post]:
        logger.info("Fetching archive from: %s", self.api_url)
        posts: List[Post] = []
        offset = 0

        while True:
            params = {
                'sort': 'new',
                'search': '',
                'offset': offset,
                'limit': API_LIMIT_PER_REQUEST,
            }
            try:
                response = self.session.get(
                    self.api_url,
                    params=params,
                    headers=self.headers,
                    timeout=REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.Timeout:
                logger.error("API timeout at offset %s", offset)
                break
            except requests.exceptions.HTTPError as exc:
                logger.error("API HTTP error: %s", exc)
                break
            except (ValueError, requests.exceptions.JSONDecodeError) as exc:
                logger.error("API returned invalid JSON: %s", exc)
                break
            except requests.exceptions.RequestException as exc:
                logger.error("API connection error: %s", exc)
                break

            new_posts = self._parse_api_response(data)
            if not new_posts:
                break

            for item in new_posts:
                post = Post.from_api_response(item)
                if not post:
                    continue

                posts.append(post)
                if progress_callback:
                    progress_callback(len(posts), limit, post)

                if limit and len(posts) >= limit:
                    return posts[:limit]

            offset += len(new_posts)
            if len(new_posts) < API_LIMIT_PER_REQUEST:
                break

            time.sleep(RATE_LIMIT_DELAY)

        posts.sort(key=lambda x: x.pub_date)
        logger.info("Found %s posts in archive.", len(posts))
        return posts

    def _parse_api_response(self, data: any) -> List[dict]:
        if isinstance(data, list):
            return data
        if isinstance(data, dict) and 'posts' in data:
            posts_list = data['posts']
            if not isinstance(posts_list, list):
                logger.warning("API 'posts' field is %s, expected list", type(posts_list))
                return []
            return posts_list

        logger.warning("Unexpected API response format: %s", type(data))
        return []

    def fetch_post_content(self, url: str) -> str:
        if self.enable_cache:
            cached = self._get_from_cache(url)
            if cached is not None:
                logger.debug("Using cached content for %s", url)
                return cached

        try:
            response = self.session.get(
                url,
                headers=self.headers,
                timeout=REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            content = self._extract_content(response.content, url)

            if self.enable_cache and content:
                self._save_to_cache(url, content)

            return content
        except requests.exceptions.Timeout:
            logger.error("Timeout fetching content from %s", url)
            return ""
        except requests.exceptions.RequestException as exc:
            logger.error("Error fetching content from %s: %s", url, exc)
            return ""
        except MemoryError:
            logger.error("Content too large from %s", url)
            return ""
        except Exception as exc:
            logger.error("Unexpected error fetching content from %s: %s", url, exc)
            return ""

    def _extract_content(self, html: bytes, url: str) -> str:
        soup = BeautifulSoup(html, 'html.parser')

        for tag, class_name in CONTENT_SELECTORS:
            if class_name:
                content_div = soup.find(tag, class_=class_name)
            else:
                content_div = soup.find(tag)

            if content_div:
                return str(content_div)

        body = soup.find('body')
        if body:
            logger.warning("Could not find expected content structure in %s, using body", url)
            return str(body)

        logger.warning("No content found for %s", url)
        return ""

    def fetch_all_content_concurrent(
        self,
        posts: Iterable[Post],
        max_workers: Optional[int] = None,
        progress_callback: ProgressCallback = None,
    ) -> List[Post]:
        post_list = list(posts)
        total = len(post_list)
        if total == 0:
            return post_list

        workers = max_workers or self.max_concurrent
        logger.info("Fetching content for %s posts with %s workers", total, workers)

        completed = 0
        with ThreadPoolExecutor(max_workers=workers) as executor:
            future_to_post = {
                executor.submit(self.fetch_post_content, post.link): post
                for post in post_list
            }

            for future in as_completed(future_to_post):
                post = future_to_post[future]
                try:
                    post.content = future.result()
                    if not post.content:
                        logger.warning("No content retrieved for %s", post.link)
                except Exception as exc:
                    logger.error("Failed to fetch %s: %s", post.link, exc)
                    post.content = ""
                finally:
                    completed += 1
                    if progress_callback:
                        progress_callback(completed, total, post)
                    time.sleep(RATE_LIMIT_DELAY / max(workers, 1))

        return post_list

    def _get_from_cache(self, url: str) -> Optional[str]:
        if not self.cache_dir:
            return None

        cache_key = get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.pkl"

        if cache_file.exists():
            try:
                with cache_file.open('rb') as f:
                    return pickle.load(f)
            except Exception as exc:
                logger.warning("Failed to load cache for %s: %s", url, exc)
                return None

        return None

    def _save_to_cache(self, url: str, content: str) -> None:
        if not self.cache_dir:
            return

        cache_key = get_cache_key(url)
        cache_file = self.cache_dir / f"{cache_key}.pkl"

        try:
            with cache_file.open('wb') as f:
                pickle.dump(content, f)
            logger.debug("Cached content for %s", url)
        except Exception as exc:
            logger.warning("Failed to cache %s: %s", url, exc)

    def clear_cache(self) -> None:
        if not self.cache_dir:
            logger.info("Cache not enabled")
            return

        if self.cache_dir.exists():
            cache_files = list(self.cache_dir.glob("*.pkl"))
            for cache_file in cache_files:
                cache_file.unlink()
            logger.info("Cleared %s cached files", len(cache_files))
        else:
            logger.info("Cache directory does not exist")

    def verify_auth(self) -> bool:
        if 'Cookie' not in self.headers:
            return False

        auth_url = "https://substack.com/api/v1/subscriptions"

        try:
            response = self.session.get(
                auth_url,
                headers=self.headers,
                timeout=REQUEST_TIMEOUT,
            )
            if response.status_code == 200:
                logger.info("Authentication verification successful")
                return True

            logger.warning(
                "Authentication verification failed with status %s",
                response.status_code,
            )
            return False
        except requests.exceptions.RequestException as exc:
            logger.error("Error verifying authentication: %s", exc)
            return False
