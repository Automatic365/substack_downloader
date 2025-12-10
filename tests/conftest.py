"""
Pytest configuration and shared fixtures for Substack Downloader tests
"""
import pytest
import os


@pytest.fixture
def fixtures_dir():
    """Return path to fixtures directory"""
    return os.path.join(os.path.dirname(__file__), 'fixtures')


@pytest.fixture
def sample_api_response(fixtures_dir):
    """Load sample API response JSON"""
    import json
    path = os.path.join(fixtures_dir, 'sample_api_response.json')
    with open(path, 'r') as f:
        return json.load(f)


@pytest.fixture
def sample_post_html(fixtures_dir):
    """Load sample post HTML content"""
    path = os.path.join(fixtures_dir, 'sample_post_content.html')
    with open(path, 'r') as f:
        return f.read()
