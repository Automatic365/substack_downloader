"""
Integration tests for Substack Downloader
These tests make real network calls - mark with @pytest.mark.integration
"""
import pytest
import os
from fetcher_enhanced import SubstackFetcherEnhanced
from models import Post


# Skip integration tests by default (run with: pytest -m integration)
pytestmark = pytest.mark.integration


class TestIntegration:
    """Integration tests against real Substack newsletters"""

    @pytest.fixture
    def public_newsletter_url(self):
        """A known public Substack newsletter for testing"""
        # Using a well-known public newsletter
        return os.getenv('TEST_SUBSTACK_URL', 'https://platformer.news')

    def test_fetch_newsletter_title_real(self, public_newsletter_url):
        """Test fetching title from a real newsletter"""
        fetcher = SubstackFetcherEnhanced(public_newsletter_url)
        title = fetcher.get_newsletter_title()

        assert title != ""
        assert title != "Substack Archive"  # Should get actual title
        assert isinstance(title, str)
        print(f"Fetched title: {title}")

    def test_fetch_archive_metadata_real(self, public_newsletter_url):
        """Test fetching metadata from a real newsletter"""
        fetcher = SubstackFetcherEnhanced(public_newsletter_url)
        posts = fetcher.fetch_archive_metadata(limit=5)

        assert len(posts) > 0
        assert len(posts) <= 5
        assert all(isinstance(p, Post) for p in posts)

        # Check post structure
        for post in posts:
            assert post.title
            assert post.link
            assert post.link.startswith('http')
            assert post.pub_date
            print(f"Post: {post.title[:50]}...")

    def test_fetch_post_content_real(self, public_newsletter_url):
        """Test fetching content from a real post"""
        fetcher = SubstackFetcherEnhanced(public_newsletter_url)

        # Get one post
        posts = fetcher.fetch_archive_metadata(limit=1)
        assert len(posts) == 1

        # Fetch its content
        content = fetcher.fetch_post_content(posts[0].link)

        assert content != ""
        assert len(content) > 100  # Should have substantial content
        assert '<' in content  # Should be HTML
        print(f"Fetched {len(content)} characters of content")

    def test_concurrent_fetch_real(self, public_newsletter_url):
        """Test concurrent fetching with real posts"""
        fetcher = SubstackFetcherEnhanced(public_newsletter_url)

        # Get a few posts
        posts = fetcher.fetch_archive_metadata(limit=3)
        assert len(posts) > 0

        # Fetch content concurrently
        posts_with_content = fetcher.fetch_all_content_concurrent(posts, max_workers=2)

        assert len(posts_with_content) == len(posts)

        # Check all have content
        successful = sum(1 for p in posts_with_content if p.content)
        print(f"Successfully fetched content for {successful}/{len(posts)} posts")
        assert successful > 0  # At least some should succeed

    def test_caching_works(self, public_newsletter_url):
        """Test that caching actually works"""
        import time

        # Create fetcher with caching enabled
        fetcher = SubstackFetcherEnhanced(public_newsletter_url, enable_cache=True)

        # Get one post
        posts = fetcher.fetch_archive_metadata(limit=1)
        assert len(posts) == 1

        url = posts[0].link

        # First fetch (uncached)
        start = time.time()
        content1 = fetcher.fetch_post_content(url)
        first_duration = time.time() - start

        assert content1 != ""

        # Second fetch (should be cached)
        start = time.time()
        content2 = fetcher.fetch_post_content(url)
        second_duration = time.time() - start

        assert content2 == content1
        assert second_duration < first_duration / 2  # Should be much faster
        print(f"First fetch: {first_duration:.2f}s, Cached fetch: {second_duration:.2f}s")

        # Cleanup
        fetcher.clear_cache()

    def test_invalid_url_raises(self):
        """Test that invalid URLs raise appropriate errors"""
        with pytest.raises(ValueError, match="Invalid URL format"):
            SubstackFetcherEnhanced("not-a-valid-url")

        with pytest.raises(ValueError, match="URL must be a non-empty string"):
            SubstackFetcherEnhanced("")

    def test_retry_on_timeout(self):
        """Test retry logic (using a URL that times out)"""
        # This test is tricky - we'd need a mock server or a very slow endpoint
        # For now, just verify the retry session is configured
        fetcher = SubstackFetcherEnhanced("https://example.substack.com")
        assert fetcher.session is not None
        assert fetcher.session.adapters is not None


class TestModels:
    """Test the Post model"""

    def test_post_from_valid_api_response(self):
        """Test creating Post from valid API data"""
        api_data = {
            'title': 'Test Post',
            'canonical_url': 'https://example.com/p/test',
            'post_date': '2024-11-27T18:00:00.000Z',
            'description': 'Test description'
        }

        post = Post.from_api_response(api_data)

        assert post is not None
        assert post.title == 'Test Post'
        assert post.link == 'https://example.com/p/test'
        assert post.description == 'Test description'
        assert post.pub_date.year == 2024

    def test_post_from_invalid_data(self):
        """Test creating Post from invalid data returns None"""
        # Missing URL
        post = Post.from_api_response({'title': 'Test'})
        assert post is None

        # Not a dict
        post = Post.from_api_response("not a dict")
        assert post is None

    def test_post_to_dict(self):
        """Test converting Post to dictionary"""
        post = Post(
            title="Test",
            link="https://example.com",
            pub_date=datetime(2024, 1, 1),
            description="Desc",
            content="Content"
        )

        data = post.to_dict()

        assert data['title'] == "Test"
        assert data['link'] == "https://example.com"
        assert data['description'] == "Desc"
        assert data['content'] == "Content"


class TestUtils:
    """Test utility functions"""

    def test_sanitize_filename(self):
        """Test filename sanitization"""
        from utils import sanitize_filename

        assert sanitize_filename("Hello/World") == "Hello_World"
        assert sanitize_filename("Test<>File") == "TestFile"
        assert sanitize_filename("Normal.File") == "Normal.File"
        assert sanitize_filename("") == "unnamed"
        assert sanitize_filename("   ") == "unnamed"

        # Test length limiting
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) <= 255

    def test_get_cache_key(self):
        """Test cache key generation"""
        from utils import get_cache_key

        key1 = get_cache_key("https://example.com/post1")
        key2 = get_cache_key("https://example.com/post2")
        key3 = get_cache_key("https://example.com/post1")

        assert len(key1) == 32  # MD5 hash length
        assert key1 != key2
        assert key1 == key3  # Same URL = same key

    def test_format_size(self):
        """Test size formatting"""
        from utils import format_size

        assert "1.0 KB" in format_size(1024)
        assert "1.0 MB" in format_size(1024 * 1024)
        assert "500.0 B" in format_size(500)
