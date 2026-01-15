"""
Utilities for compiler package.
"""
from typing import Iterable, List


def sanitize_text(text: str) -> str:
    """
    Replace characters not supported by Latin-1 encoding.
    """
    replacements = {
        '\u2018': "'", '\u2019': "'",  # Smart quotes
        '\u201c': '"', '\u201d': '"',  # Smart double quotes
        '\u2013': '-', '\u2014': '-',  # Dashes
        '\u2026': '...',               # Ellipsis
        '\u00a0': ' ',                 # Non-breaking space
    }
    for char, replacement in replacements.items():
        text = text.replace(char, replacement)

    return text.encode('latin-1', 'replace').decode('latin-1')


def normalize_post(post):
    if hasattr(post, "to_dict"):
        return post.to_dict()
    if isinstance(post, dict):
        return post
    raise TypeError(f"Unsupported post type: {type(post)}")


def normalize_posts(posts: Iterable) -> List[dict]:
    return [normalize_post(post) for post in posts]
