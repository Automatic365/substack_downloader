import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse

class SubstackFetcher:
    def __init__(self, url, cookie=None):
        # Validate URL format
        if not url or not isinstance(url, str):
            raise ValueError("URL must be a non-empty string")

        parsed = urlparse(url)
        if not parsed.scheme or not parsed.netloc:
            raise ValueError(f"Invalid URL format: {url}")

        # Security: Warn about HTTP, block with authentication
        if parsed.scheme == 'http':
            if cookie:
                raise ValueError(
                    "Security Error: Cannot use authentication cookie with HTTP URL. "
                    "Use HTTPS to protect your credentials."
                )
            print(f"⚠️  WARNING: Using HTTP instead of HTTPS. Connection not encrypted!")

        self.url = url.rstrip('/')
        self.api_url = f"{self.url}/api/v1/archive"
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        }
        if cookie:
            self.headers['Cookie'] = cookie

    def get_newsletter_title(self):
        """
        Fetches the newsletter title from the main page.
        """
        try:
            response = requests.get(self.url, headers=self.headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.title.string if soup.title else "Substack Archive"
            return title.strip()
        except requests.exceptions.Timeout:
            print(f"Timeout fetching title from {self.url}")
            return "Substack Archive"
        except requests.exceptions.RequestException as e:
            print(f"Error fetching title: {e}")
            return "Substack Archive"
        except (AttributeError, TypeError) as e:
            print(f"Error parsing title: {e}")
            return "Substack Archive"

    def fetch_archive_metadata(self, limit=None):
        """
        Fetches metadata for all posts using the Archive API.
        Returns a list of dicts: {title, url, pub_date, description}
        """
        print(f"Fetching archive from: {self.api_url}")
        posts = []
        offset = 0
        limit_per_request = 12
        
        while True:
            params = {
                'sort': 'new',
                'search': '',
                'offset': offset,
                'limit': limit_per_request
            }
            try:
                response = requests.get(self.api_url, params=params, headers=self.headers, timeout=30)
                response.raise_for_status()
                data = response.json()
            except requests.exceptions.Timeout:
                print(f"API timeout at offset {offset}")
                break
            except requests.exceptions.HTTPError as e:
                print(f"API HTTP error: {e}")
                break
            except (ValueError, requests.exceptions.JSONDecodeError) as e:
                print(f"API returned invalid JSON: {e}")
                break
            except requests.exceptions.RequestException as e:
                print(f"API connection error: {e}")
                break

            # API returns a list of posts directly or dict with 'posts' key
            if isinstance(data, list):
                new_posts = data
            elif isinstance(data, dict) and 'posts' in data:
                posts_list = data['posts']
                if not isinstance(posts_list, list):
                    print(f"Warning: API 'posts' field is {type(posts_list)}, expected list")
                    new_posts = []
                else:
                    new_posts = posts_list
            else:
                print(f"Warning: Unexpected API response format: {type(data)}")
                new_posts = []

            if not new_posts:
                break

            for item in new_posts:
                # Validate item is a dict
                if not isinstance(item, dict):
                    print(f"Warning: Post item is not a dict: {type(item)}, skipping")
                    continue

                title = item.get('title', 'No Title')
                canonical_url = item.get('canonical_url', '')
                post_date_str = item.get('post_date', '')
                description = item.get('description', '')

                # Validate that we have a URL
                if not canonical_url or not isinstance(canonical_url, str):
                    print(f"Warning: Skipping post '{title}': no valid URL")
                    continue
                
                # Parse date
                # Format: 2024-11-27T18:00:00.000Z
                try:
                    pub_date = datetime.fromisoformat(post_date_str.replace('Z', '+00:00'))
                except ValueError:
                    print(f"Warning: Invalid date format '{post_date_str}' for post '{title}', using current time")
                    pub_date = datetime.now()
                except (AttributeError, TypeError):
                    print(f"Warning: post_date is not a string: {type(post_date_str)}, using current time")
                    pub_date = datetime.now()

                posts.append({
                    'title': title,
                    'link': canonical_url,
                    'pub_date': pub_date,
                    'description': description
                })
                
                if limit and len(posts) >= limit:
                    return posts[:limit]

            offset += len(new_posts)
            # If we got fewer than requested, we are at the end
            if len(new_posts) < limit_per_request:
                break
            
            time.sleep(1) # Be nice to the API

        # Sort by date: Oldest first
        posts.sort(key=lambda x: x['pub_date'])
        print(f"Found {len(posts)} posts in archive.")
        return posts

    def fetch_post_content(self, url):
        """
        Fetches the full HTML content of a single post.
        """
        try:
            response = requests.get(url, headers=self.headers, timeout=30)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')

            # Try multiple content selectors with fallbacks
            selectors = [
                ('div', 'available-content'),
                ('div', 'body markup'),
                ('article', None),
                ('div', 'post-content'),
                ('main', None)
            ]

            for tag, class_name in selectors:
                if class_name:
                    content_div = soup.find(tag, class_=class_name)
                else:
                    content_div = soup.find(tag)

                if content_div:
                    return str(content_div)

            # Final fallback: try to extract body
            body = soup.find('body')
            if body:
                print(f"Warning: Could not find expected content structure in {url}, using body")
                return str(body)

            print(f"Warning: No content found for {url}")
            return ""
        except requests.exceptions.Timeout:
            print(f"Timeout fetching content from {url}")
            return ""
        except requests.exceptions.RequestException as e:
            print(f"Error fetching content from {url}: {e}")
            return ""
        except MemoryError:
            print(f"Content too large from {url}")
            return ""
        except Exception as e:
            print(f"Unexpected error fetching content from {url}: {type(e).__name__}: {e}")
            return ""


    def verify_auth(self):
        """
        Verifies if the current session is authenticated by checking the subscriptions endpoint.
        Returns:
            bool: True if authenticated, False otherwise
        """
        if 'Cookie' not in self.headers:
            return False

        # Use the subscriptions endpoint as it requires authentication
        auth_url = f"https://substack.com/api/v1/subscriptions"
        
        try:
            response = requests.get(auth_url, headers=self.headers, timeout=10)
            # If we get a 200 OK, the session is valid
            if response.status_code == 200:
                return True
            # 401 Unauthorized means invalid cookie
            return False
        except requests.exceptions.RequestException as e:
            print(f"Error verifying authentication: {e}")
            return False
