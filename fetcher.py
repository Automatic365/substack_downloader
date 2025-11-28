import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup

class SubstackFetcher:
    def __init__(self, url, cookie=None):
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
            response = requests.get(self.url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            title = soup.title.string if soup.title else "Substack Archive"
            return title.strip()
        except Exception as e:
            print(f"Error fetching title: {e}")
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
                response = requests.get(self.api_url, params=params, headers=self.headers)
                if response.status_code != 200:
                    print(f"API Error: {response.status_code}")
                    break
                
                data = response.json()
            except Exception as e:
                print(f"Error fetching API: {e}")
                break

            # API returns a list of posts directly
            if isinstance(data, list):
                new_posts = data
            elif isinstance(data, dict) and 'posts' in data:
                new_posts = data['posts']
            else:
                new_posts = []

            if not new_posts:
                break
            
            for item in new_posts:
                title = item.get('title', 'No Title')
                canonical_url = item.get('canonical_url', '')
                post_date_str = item.get('post_date', '')
                description = item.get('description', '')
                
                # Parse date
                # Format: 2024-11-27T18:00:00.000Z
                try:
                    pub_date = datetime.fromisoformat(post_date_str.replace('Z', '+00:00'))
                except (ValueError, AttributeError):
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
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Substack content is usually in <div class="available-content"> or <div class="body markup">
            # We want the main content.
            content_div = soup.find('div', class_='available-content')
            if not content_div:
                content_div = soup.find('div', class_='body markup')
            
            if content_div:
                return str(content_div)
            else:
                return ""
        except Exception as e:
            print(f"Error fetching content for {url}: {e}")
            return ""

