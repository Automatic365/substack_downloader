"""
Data models for Substack Downloader
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from logger import setup_logger

logger = setup_logger(__name__)


@dataclass
class Post:
    """
    Represents a Substack post with validated fields.
    """
    title: str
    link: str
    pub_date: datetime
    description: str
    content: str = ""

    @classmethod
    def from_api_response(cls, item: dict) -> Optional['Post']:
        """
        Create a Post from API response data with validation.

        Args:
            item: Dictionary from Substack API

        Returns:
            Post instance if valid, None otherwise
        """
        if not isinstance(item, dict):
            logger.warning(f"Post item is not a dict: {type(item)}, skipping")
            return None

        # Extract and validate required fields
        title = item.get('title', 'No Title')
        canonical_url = item.get('canonical_url', '')

        # Validate URL
        if not canonical_url or not isinstance(canonical_url, str):
            logger.warning(f"Skipping post '{title}': no valid URL")
            return None

        # Get optional fields
        description = item.get('description', '')
        post_date_str = item.get('post_date', '')

        # Parse date
        pub_date = cls._parse_date(post_date_str, title)

        return cls(
            title=title,
            link=canonical_url,
            pub_date=pub_date,
            description=description
        )

    @staticmethod
    def _parse_date(date_str: str, title: str) -> datetime:
        """
        Parse date string with fallback to current time.

        Args:
            date_str: ISO format date string from API
            title: Post title for logging

        Returns:
            Parsed datetime or current time
        """
        try:
            return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        except ValueError:
            logger.warning(f"Invalid date format '{date_str}' for post '{title}', using current time")
            return datetime.now()
        except (AttributeError, TypeError):
            logger.warning(f"Post date is not a string: {type(date_str)}, using current time")
            return datetime.now()

    def to_dict(self) -> dict:
        """Convert Post to dictionary format."""
        return {
            'title': self.title,
            'link': self.link,
            'pub_date': self.pub_date,
            'description': self.description,
            'content': self.content
        }

    def __repr__(self) -> str:
        return f"Post(title='{self.title[:50]}...', link='{self.link}')"
