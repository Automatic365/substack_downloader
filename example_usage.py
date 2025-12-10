#!/usr/bin/env python3
"""
Example usage of the enhanced Substack downloader
Demonstrates all new features
"""
import os
from fetcher_enhanced import SubstackFetcherEnhanced
from logger import setup_logger
from utils import sanitize_filename, format_size

# Setup logging
logger = setup_logger(__name__)


def basic_usage():
    """Basic usage example"""
    print("\n=== Basic Usage ===\n")

    url = "https://platformer.news"

    # Create fetcher
    fetcher = SubstackFetcherEnhanced(url)

    # Get newsletter title
    title = fetcher.get_newsletter_title()
    print(f"Newsletter: {title}")

    # Fetch metadata for 5 posts
    posts = fetcher.fetch_archive_metadata(limit=5)
    print(f"Found {len(posts)} posts")

    # Fetch content for first post
    if posts:
        post = posts[0]
        content = fetcher.fetch_post_content(post.link)
        print(f"First post: {post.title}")
        print(f"Content length: {format_size(len(content))}")


def concurrent_usage():
    """Concurrent fetching example"""
    print("\n=== Concurrent Fetching ===\n")

    url = "https://platformer.news"
    fetcher = SubstackFetcherEnhanced(url)

    # Fetch metadata
    posts = fetcher.fetch_archive_metadata(limit=10)

    # Fetch all content concurrently (much faster!)
    posts = fetcher.fetch_all_content_concurrent(posts, max_workers=5)

    # Show results
    successful = sum(1 for p in posts if p.content)
    print(f"Successfully fetched content for {successful}/{len(posts)} posts")


def caching_usage():
    """Caching example"""
    print("\n=== Caching Example ===\n")

    url = "https://platformer.news"

    # Create fetcher with caching enabled
    fetcher = SubstackFetcherEnhanced(url, enable_cache=True)

    print("First run (no cache)...")
    posts = fetcher.fetch_archive_metadata(limit=3)
    fetcher.fetch_all_content_concurrent(posts)

    print("\nSecond run (with cache)...")
    fetcher2 = SubstackFetcherEnhanced(url, enable_cache=True)
    posts2 = fetcher2.fetch_archive_metadata(limit=3)
    fetcher2.fetch_all_content_concurrent(posts2)
    print("Much faster! Content loaded from cache.")

    # Clear cache when done
    fetcher.clear_cache()
    print("Cache cleared")


def environment_variables_usage():
    """Using environment variables"""
    print("\n=== Environment Variables ===\n")

    # Set some environment variables
    os.environ['SUBSTACK_LOG_LEVEL'] = 'DEBUG'
    os.environ['SUBSTACK_MAX_WORKERS'] = '3'
    os.environ['SUBSTACK_ENABLE_CACHE'] = 'true'

    print("Environment variables set:")
    print(f"  LOG_LEVEL: {os.getenv('SUBSTACK_LOG_LEVEL')}")
    print(f"  MAX_WORKERS: {os.getenv('SUBSTACK_MAX_WORKERS')}")
    print(f"  ENABLE_CACHE: {os.getenv('SUBSTACK_ENABLE_CACHE')}")

    # These will be automatically picked up by config.py
    url = "https://platformer.news"
    fetcher = SubstackFetcherEnhanced(url)

    print("\nFetcher configured with environment variables!")


def authenticated_usage():
    """Using authentication cookie"""
    print("\n=== Authenticated Access ===\n")

    url = "https://your-private-newsletter.substack.com"

    # Get cookie from environment variable (secure!)
    cookie = os.getenv('SUBSTACK_COOKIE')

    if cookie:
        fetcher = SubstackFetcherEnhanced(url, cookie=cookie)
        print("Fetcher configured with authentication cookie")
    else:
        print("Set SUBSTACK_COOKIE environment variable for paywalled content")


def post_model_usage():
    """Working with Post objects"""
    print("\n=== Post Model ===\n")

    url = "https://platformer.news"
    fetcher = SubstackFetcherEnhanced(url)

    posts = fetcher.fetch_archive_metadata(limit=1)

    if posts:
        post = posts[0]

        # Access typed fields
        print(f"Title: {post.title}")
        print(f"Link: {post.link}")
        print(f"Date: {post.pub_date.strftime('%Y-%m-%d')}")
        print(f"Description: {post.description[:100]}...")

        # Convert to dict
        data = post.to_dict()
        print(f"\nAs dict: {list(data.keys())}")


def utils_usage():
    """Using utility functions"""
    print("\n=== Utility Functions ===\n")

    # Sanitize filenames
    unsafe_name = "My Newsletter/Post <2024>"
    safe_name = sanitize_filename(unsafe_name)
    print(f"Unsafe: '{unsafe_name}'")
    print(f"Safe: '{safe_name}'")

    # Format sizes
    sizes = [512, 1024*10, 1024*1024*5]
    for size in sizes:
        print(f"{size} bytes = {format_size(size)}")


def complete_workflow():
    """Complete workflow example"""
    print("\n=== Complete Workflow ===\n")

    # 1. Setup
    url = "https://platformer.news"
    fetcher = SubstackFetcherEnhanced(url, enable_cache=True)

    # 2. Get title
    title = fetcher.get_newsletter_title()
    safe_title = sanitize_filename(title)
    print(f"Downloading: {title}")

    # 3. Fetch metadata
    logger.info(f"Fetching posts from {url}")
    posts = fetcher.fetch_archive_metadata(limit=20)
    print(f"Found {len(posts)} posts")

    # 4. Fetch content concurrently
    logger.info("Fetching content...")
    posts = fetcher.fetch_all_content_concurrent(posts, max_workers=5)

    # 5. Process posts
    successful = sum(1 for p in posts if p.content)
    total_size = sum(len(p.content) for p in posts if p.content)

    print(f"\nResults:")
    print(f"  Posts with content: {successful}/{len(posts)}")
    print(f"  Total content size: {format_size(total_size)}")
    print(f"  Output filename: {safe_title}.pdf")

    # 6. Cleanup
    fetcher.clear_cache()
    logger.info("Workflow complete")


if __name__ == '__main__':
    import sys

    examples = {
        'basic': basic_usage,
        'concurrent': concurrent_usage,
        'caching': caching_usage,
        'env': environment_variables_usage,
        'auth': authenticated_usage,
        'models': post_model_usage,
        'utils': utils_usage,
        'workflow': complete_workflow
    }

    if len(sys.argv) > 1 and sys.argv[1] in examples:
        examples[sys.argv[1]]()
    else:
        print("Substack Downloader - Usage Examples")
        print("\nAvailable examples:")
        for name, func in examples.items():
            doc = func.__doc__ or ""
            print(f"  {name:15} - {doc}")
        print(f"\nUsage: python {sys.argv[0]} <example>")
        print("Example: python example_usage.py concurrent")
