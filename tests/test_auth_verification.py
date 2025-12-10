
import pytest
import requests
import requests_mock
from fetcher import SubstackFetcher
from fetcher_enhanced import SubstackFetcherEnhanced

class TestAuthVerification:
    """Tests for verify_auth method"""

    def test_verify_auth_success(self):
        """Test that verify_auth returns True on 200 OK"""
        fetcher = SubstackFetcher('https://example.substack.com', cookie='test_cookie')
        with requests_mock.Mocker() as m:
            m.get('https://substack.com/api/v1/subscriptions', status_code=200)
            assert fetcher.verify_auth() is True

    def test_verify_auth_failure_401(self):
        """Test that verify_auth returns False on 401 Unauthorized"""
        fetcher = SubstackFetcher('https://example.substack.com', cookie='test_cookie')
        with requests_mock.Mocker() as m:
            m.get('https://substack.com/api/v1/subscriptions', status_code=401)
            assert fetcher.verify_auth() is False

    def test_verify_auth_no_cookie(self):
        """Test that verify_auth returns False if no cookie is present"""
        fetcher = SubstackFetcher('https://example.substack.com')
        # Ensure cookie is not in headers
        assert 'Cookie' not in fetcher.headers
        assert fetcher.verify_auth() is False

    def test_verify_auth_network_error(self):
        """Test that verify_auth returns False on network error"""
        fetcher = SubstackFetcher('https://example.substack.com', cookie='test_cookie')
        with requests_mock.Mocker() as m:
            m.get('https://substack.com/api/v1/subscriptions', exc=requests.exceptions.ConnectionError)
            assert fetcher.verify_auth() is False

class TestAuthVerificationEnhanced:
    """Tests for verify_auth method in SubstackFetcherEnhanced"""

    def test_verify_auth_success(self):
        """Test that verify_auth returns True on 200 OK"""
        fetcher = SubstackFetcherEnhanced('https://example.substack.com', cookie='test_cookie')
        with requests_mock.Mocker() as m:
            m.get('https://substack.com/api/v1/subscriptions', status_code=200)
            assert fetcher.verify_auth() is True

    def test_verify_auth_failure_401(self):
        """Test that verify_auth returns False on 401 Unauthorized"""
        fetcher = SubstackFetcherEnhanced('https://example.substack.com', cookie='test_cookie')
        with requests_mock.Mocker() as m:
            m.get('https://substack.com/api/v1/subscriptions', status_code=401)
            assert fetcher.verify_auth() is False
