import pytest
import requests
import requests_mock
from datetime import datetime
from fetcher import SubstackFetcher


class TestSubstackFetcher:
    """Tests for SubstackFetcher class"""

    @pytest.fixture
    def fetcher(self):
        """Create a fetcher instance for testing"""
        return SubstackFetcher('https://example.substack.com')

    @pytest.fixture
    def fetcher_with_cookie(self):
        """Create a fetcher instance with cookie for testing"""
        return SubstackFetcher('https://example.substack.com', cookie='session=abc123')

    def test_init_strips_trailing_slash(self):
        """Test that trailing slash is removed from URL"""
        fetcher = SubstackFetcher('https://example.substack.com/')
        assert fetcher.url == 'https://example.substack.com'
        assert fetcher.api_url == 'https://example.substack.com/api/v1/archive'

    def test_init_with_cookie(self, fetcher_with_cookie):
        """Test that cookie is added to headers"""
        assert 'Cookie' in fetcher_with_cookie.headers
        assert fetcher_with_cookie.headers['Cookie'] == 'session=abc123'

    def test_init_without_cookie(self, fetcher):
        """Test that headers don't have Cookie when not provided"""
        assert 'Cookie' not in fetcher.headers
        assert 'User-Agent' in fetcher.headers

    def test_init_validates_empty_url(self):
        """Test that empty URL raises ValueError"""
        with pytest.raises(ValueError, match="URL must be a non-empty string"):
            SubstackFetcher('')

    def test_init_validates_none_url(self):
        """Test that None URL raises ValueError"""
        with pytest.raises(ValueError, match="URL must be a non-empty string"):
            SubstackFetcher(None)

    def test_init_validates_invalid_url_format(self):
        """Test that invalid URL format raises ValueError"""
        with pytest.raises(ValueError, match="Invalid URL format"):
            SubstackFetcher('not-a-valid-url')

    def test_init_validates_url_without_scheme(self):
        """Test that URL without scheme raises ValueError"""
        with pytest.raises(ValueError, match="Invalid URL format"):
            SubstackFetcher('example.com')


class TestGetNewsletterTitle:
    """Tests for get_newsletter_title method"""

    @pytest.fixture
    def fetcher(self):
        return SubstackFetcher('https://example.substack.com')

    def test_get_newsletter_title_success(self, fetcher):
        """Test successful title extraction"""
        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com',
                  text='<html><head><title>My Newsletter</title></head></html>')

            title = fetcher.get_newsletter_title()
            assert title == 'My Newsletter'

    def test_get_newsletter_title_with_whitespace(self, fetcher):
        """Test title extraction strips whitespace"""
        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com',
                  text='<html><head><title>  My Newsletter  </title></head></html>')

            title = fetcher.get_newsletter_title()
            assert title == 'My Newsletter'

    def test_get_newsletter_title_no_title_tag(self, fetcher):
        """Test fallback when no title tag exists"""
        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com',
                  text='<html><head></head></html>')

            title = fetcher.get_newsletter_title()
            assert title == 'Substack Archive'

    def test_get_newsletter_title_network_error(self, fetcher):
        """Test fallback on network error"""
        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com',
                  exc=requests.exceptions.ConnectionError)

            title = fetcher.get_newsletter_title()
            assert title == 'Substack Archive'

    def test_get_newsletter_title_404(self, fetcher):
        """Test fallback on 404 error"""
        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com', status_code=404)

            title = fetcher.get_newsletter_title()
            assert title == 'Substack Archive'


class TestFetchArchiveMetadata:
    """Tests for fetch_archive_metadata method"""

    @pytest.fixture
    def fetcher(self):
        return SubstackFetcher('https://example.substack.com')

    @pytest.fixture
    def sample_post(self):
        """Sample post data"""
        return {
            'title': 'Test Post',
            'canonical_url': 'https://example.substack.com/p/test-post',
            'post_date': '2024-11-27T18:00:00.000Z',
            'description': 'Test description'
        }

    def test_fetch_single_page(self, fetcher, sample_post):
        """Test fetching a single page of posts"""
        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com/api/v1/archive',
                  json=[sample_post])

            posts = fetcher.fetch_archive_metadata()

            assert len(posts) == 1
            assert posts[0]['title'] == 'Test Post'
            assert posts[0]['link'] == 'https://example.substack.com/p/test-post'
            assert posts[0]['description'] == 'Test description'
            assert isinstance(posts[0]['pub_date'], datetime)

    def test_fetch_with_limit(self, fetcher, sample_post):
        """Test fetching with a limit"""
        posts_data = [sample_post.copy() for _ in range(20)]
        for i, post in enumerate(posts_data):
            post['title'] = f'Test Post {i}'

        with requests_mock.Mocker() as m:
            # First request returns 12 posts
            m.get('https://example.substack.com/api/v1/archive',
                  json=posts_data[:12])

            posts = fetcher.fetch_archive_metadata(limit=5)

            assert len(posts) == 5

    def test_fetch_pagination(self, fetcher, sample_post):
        """Test pagination works correctly"""
        with requests_mock.Mocker() as m:
            # First page: 12 posts
            first_page = [sample_post.copy() for _ in range(12)]
            for i, post in enumerate(first_page):
                post['title'] = f'Post {i}'
                post['post_date'] = f'2024-11-{27-i:02d}T18:00:00.000Z'

            # Second page: 5 posts (less than limit_per_request)
            second_page = [sample_post.copy() for _ in range(5)]
            for i, post in enumerate(second_page):
                post['title'] = f'Post {12+i}'
                post['post_date'] = f'2024-11-{15-i:02d}T18:00:00.000Z'

            def callback(request, context):
                offset = int(request.qs.get('offset', [0])[0])
                if offset == 0:
                    return first_page
                elif offset == 12:
                    return second_page
                return []

            m.get('https://example.substack.com/api/v1/archive', json=callback)

            posts = fetcher.fetch_archive_metadata()

            assert len(posts) == 17

    def test_fetch_dict_response_format(self, fetcher, sample_post):
        """Test handling dict response with 'posts' key"""
        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com/api/v1/archive',
                  json={'posts': [sample_post]})

            posts = fetcher.fetch_archive_metadata()

            assert len(posts) == 1
            assert posts[0]['title'] == 'Test Post'

    def test_fetch_empty_response(self, fetcher):
        """Test handling empty response"""
        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com/api/v1/archive', json=[])

            posts = fetcher.fetch_archive_metadata()

            assert len(posts) == 0

    def test_fetch_malformed_json(self, fetcher):
        """Test handling malformed JSON response"""
        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com/api/v1/archive',
                  text='not json')

            posts = fetcher.fetch_archive_metadata()

            assert len(posts) == 0

    def test_fetch_404_error(self, fetcher):
        """Test handling 404 error"""
        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com/api/v1/archive',
                  status_code=404)

            posts = fetcher.fetch_archive_metadata()

            assert len(posts) == 0

    def test_fetch_network_error(self, fetcher):
        """Test handling network error"""
        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com/api/v1/archive',
                  exc=requests.exceptions.ConnectionError)

            posts = fetcher.fetch_archive_metadata()

            assert len(posts) == 0

    def test_date_parsing_valid(self, fetcher):
        """Test date parsing with valid ISO format"""
        post = {
            'title': 'Test',
            'canonical_url': 'https://example.com/p/test',
            'post_date': '2024-11-27T18:00:00.000Z',
            'description': 'Test'
        }

        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com/api/v1/archive', json=[post])

            posts = fetcher.fetch_archive_metadata()

            assert posts[0]['pub_date'].year == 2024
            assert posts[0]['pub_date'].month == 11
            assert posts[0]['pub_date'].day == 27

    def test_date_parsing_invalid(self, fetcher):
        """Test date parsing with invalid date falls back to current time"""
        post = {
            'title': 'Test',
            'canonical_url': 'https://example.com/p/test',
            'post_date': 'invalid-date',
            'description': 'Test'
        }

        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com/api/v1/archive', json=[post])

            posts = fetcher.fetch_archive_metadata()

            # Should fallback to datetime.now()
            assert isinstance(posts[0]['pub_date'], datetime)
            assert posts[0]['pub_date'].year == datetime.now().year

    def test_missing_fields_use_defaults(self, fetcher):
        """Test that missing fields use default values"""
        post = {
            'canonical_url': 'https://example.com/p/test'
        }

        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com/api/v1/archive', json=[post])

            posts = fetcher.fetch_archive_metadata()

            assert posts[0]['title'] == 'No Title'
            assert posts[0]['description'] == ''
            assert isinstance(posts[0]['pub_date'], datetime)

    def test_posts_sorted_by_date_oldest_first(self, fetcher, sample_post):
        """Test that posts are sorted oldest first"""
        posts_data = [
            {**sample_post, 'title': 'Newest', 'post_date': '2024-11-27T18:00:00.000Z'},
            {**sample_post, 'title': 'Middle', 'post_date': '2024-11-26T18:00:00.000Z'},
            {**sample_post, 'title': 'Oldest', 'post_date': '2024-11-25T18:00:00.000Z'},
        ]

        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com/api/v1/archive', json=posts_data)

            posts = fetcher.fetch_archive_metadata()

            assert posts[0]['title'] == 'Oldest'
            assert posts[1]['title'] == 'Middle'
            assert posts[2]['title'] == 'Newest'


class TestFetchPostContent:
    """Tests for fetch_post_content method"""

    @pytest.fixture
    def fetcher(self):
        return SubstackFetcher('https://example.substack.com')

    def test_fetch_content_available_content_div(self, fetcher):
        """Test fetching content from available-content div"""
        html = '''
        <html>
            <div class="available-content">
                <h1>Post Title</h1>
                <p>Post content here</p>
            </div>
        </html>
        '''

        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com/p/test', text=html)

            content = fetcher.fetch_post_content('https://example.substack.com/p/test')

            assert 'Post Title' in content
            assert 'Post content here' in content
            assert 'available-content' in content

    def test_fetch_content_body_markup_div(self, fetcher):
        """Test fetching content from body markup div as fallback"""
        html = '''
        <html>
            <div class="body markup">
                <h1>Post Title</h1>
                <p>Post content here</p>
            </div>
        </html>
        '''

        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com/p/test', text=html)

            content = fetcher.fetch_post_content('https://example.substack.com/p/test')

            assert 'Post Title' in content
            assert 'Post content here' in content

    def test_fetch_content_no_content_div(self, fetcher):
        """Test falls back to body when no content div found"""
        html = '<html><body><p>No content div</p></body></html>'

        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com/p/test', text=html)

            content = fetcher.fetch_post_content('https://example.substack.com/p/test')

            # Should fallback to body element
            assert '<body>' in content
            assert 'No content div' in content

    def test_fetch_content_completely_empty(self, fetcher):
        """Test returns empty string when HTML has no body"""
        html = '<html></html>'

        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com/p/test', text=html)

            content = fetcher.fetch_post_content('https://example.substack.com/p/test')

            assert content == ''

    def test_fetch_content_network_error(self, fetcher):
        """Test returns empty string on network error"""
        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com/p/test',
                  exc=requests.exceptions.ConnectionError)

            content = fetcher.fetch_post_content('https://example.substack.com/p/test')

            assert content == ''

    def test_fetch_content_404(self, fetcher):
        """Test returns empty string on 404"""
        with requests_mock.Mocker() as m:
            m.get('https://example.substack.com/p/test', status_code=404)

            content = fetcher.fetch_post_content('https://example.substack.com/p/test')

            assert content == ''
