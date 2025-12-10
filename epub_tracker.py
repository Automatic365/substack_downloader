import json
import os
from datetime import datetime

class EpubTracker:
    """
    Tracks which posts have been included in an EPUB file.
    Stores metadata in a JSON file alongside the EPUB.
    """

    def __init__(self, epub_path):
        """
        Args:
            epub_path: Path to the EPUB file (e.g., "output/Newsletter.epub")
        """
        self.epub_path = epub_path
        # Create tracking file path by replacing .epub with .json
        self.tracker_path = epub_path.replace('.epub', '_tracker.json')

    def load(self):
        """
        Load tracker data from JSON file.

        Returns:
            dict with keys: 'title', 'author', 'url', 'post_links', 'last_updated'
        """
        if not os.path.exists(self.tracker_path):
            return {
                'title': '',
                'author': '',
                'url': '',
                'post_links': [],
                'last_updated': None
            }

        try:
            with open(self.tracker_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            print(f"Error loading tracker file: {e}")
            return {
                'title': '',
                'author': '',
                'url': '',
                'post_links': [],
                'last_updated': None
            }

    def save(self, title, author, url, post_links):
        """
        Save tracker data to JSON file.

        Args:
            title: Newsletter title
            author: Author name
            url: Newsletter URL
            post_links: List of post URLs that have been included
        """
        data = {
            'title': title,
            'author': author,
            'url': url,
            'post_links': post_links,
            'last_updated': datetime.now().isoformat()
        }

        try:
            with open(self.tracker_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            print(f"Tracker saved: {len(post_links)} posts tracked")
        except IOError as e:
            print(f"Error saving tracker file: {e}")

    def get_new_posts(self, all_posts):
        """
        Filter out posts that are already included in the EPUB.

        Args:
            all_posts: List of post dicts with 'link' key

        Returns:
            List of new posts not yet in the EPUB
        """
        tracker_data = self.load()
        existing_links = set(tracker_data['post_links'])

        new_posts = [
            post for post in all_posts
            if post['link'] not in existing_links
        ]

        print(f"Total posts: {len(all_posts)}, Already included: {len(existing_links)}, New: {len(new_posts)}")
        return new_posts

    def exists(self):
        """Check if this EPUB has been created before."""
        return os.path.exists(self.epub_path) and os.path.exists(self.tracker_path)
