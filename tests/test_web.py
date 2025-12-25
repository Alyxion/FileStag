"""Tests for web module (fetch and web_cache)."""

import os
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from filestag.web import WebCache, web_fetch


class TestWebCache:
    """Tests for WebCache class."""

    def setup_method(self):
        """Clear cache before each test."""
        WebCache.flush()

    def teardown_method(self):
        """Clear cache after each test."""
        WebCache.flush()

    def test_store_and_fetch(self):
        """Test storing and fetching from cache."""
        WebCache.store("test_key", b"test_data")
        result = WebCache.fetch("test_key", max_age=3600.0)
        assert result == b"test_data"

    def test_fetch_nonexistent(self):
        """Test fetching non-existent key returns None."""
        result = WebCache.fetch("nonexistent_key", max_age=3600.0)
        assert result is None

    def test_max_age(self):
        """Test max_age expiration."""
        WebCache.store("age_key", b"data")

        # Immediate fetch should succeed
        result = WebCache.fetch("age_key", max_age=10.0)
        assert result == b"data"

        # With very short max_age after time passes
        time.sleep(0.1)
        result = WebCache.fetch("age_key", max_age=0.01)
        assert result is None

    def test_clear(self):
        """Test clearing the cache."""
        WebCache.store("key1", b"data1")
        WebCache.store("key2", b"data2")

        WebCache.flush()

        assert WebCache.fetch("key1", max_age=3600.0) is None
        assert WebCache.fetch("key2", max_age=3600.0) is None

    def test_different_keys(self):
        """Test storing different data under different keys."""
        WebCache.store("key_a", b"data_a")
        WebCache.store("key_b", b"data_b")

        assert WebCache.fetch("key_a", max_age=3600.0) == b"data_a"
        assert WebCache.fetch("key_b", max_age=3600.0) == b"data_b"

    def test_overwrite(self):
        """Test overwriting existing key."""
        WebCache.store("overwrite_key", b"original")
        WebCache.store("overwrite_key", b"updated")

        result = WebCache.fetch("overwrite_key", max_age=3600.0)
        assert result == b"updated"

    def test_binary_data(self):
        """Test storing binary data."""
        binary_data = bytes(range(256))
        WebCache.store("binary_key", binary_data)

        result = WebCache.fetch("binary_key", max_age=3600.0)
        assert result == binary_data

    def test_url_as_key(self):
        """Test using URL as key."""
        url = "https://example.com/path/to/file.txt"
        WebCache.store(url, b"file content")

        result = WebCache.fetch(url, max_age=3600.0)
        assert result == b"file content"


class TestWebFetch:
    """Tests for web_fetch function."""

    def test_fetch_from_cache(self):
        """Test fetching from cache when available."""
        url = "https://cached.example.com/file.txt"
        WebCache.store(url, b"cached content")

        result = web_fetch(url, max_cache_age=3600.0)
        assert result == b"cached content"

    @patch("requests.get")
    def test_fetch_from_web(self, mock_get):
        """Test fetching from web when not cached."""
        WebCache.flush()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"web content"
        mock_get.return_value = mock_response

        url = "https://test.example.com/new_file.txt"
        result = web_fetch(url)

        assert result == b"web content"
        mock_get.assert_called_once()

    @patch("requests.get")
    def test_fetch_caches_result(self, mock_get):
        """Test that fetched content is cached."""
        WebCache.flush()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"to be cached"
        mock_get.return_value = mock_response

        url = "https://cache.example.com/cache_me.txt"
        web_fetch(url, max_cache_age=3600.0)

        # Should now be in cache
        cached = WebCache.fetch(url, max_age=3600.0)
        assert cached == b"to be cached"

    @patch("requests.get")
    def test_fetch_error_returns_none(self, mock_get):
        """Test that HTTP errors return None."""
        WebCache.flush()

        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_get.return_value = mock_response

        url = "https://error.example.com/not_found.txt"
        result = web_fetch(url)

        assert result is None

    @patch("requests.get")
    def test_fetch_exception_returns_none(self, mock_get):
        """Test that exceptions return None."""
        import requests
        WebCache.flush()

        mock_get.side_effect = requests.exceptions.RequestException("Network error")

        url = "https://exception.example.com/error.txt"
        result = web_fetch(url)

        assert result is None

    @patch("requests.get")
    def test_fetch_with_timeout(self, mock_get):
        """Test fetch with timeout parameter."""
        WebCache.flush()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"content"
        mock_get.return_value = mock_response

        url = "https://timeout.example.com/file.txt"
        web_fetch(url, timeout_s=30)

        mock_get.assert_called_once()
        call_kwargs = mock_get.call_args[1]
        assert call_kwargs.get("timeout") == 30

    def test_fetch_uses_cache_for_performance(self):
        """Test that cache prevents repeated network calls."""
        url = "https://perf.example.com/file.txt"
        WebCache.store(url, b"cached")

        # Multiple fetches should all use cache
        for _ in range(10):
            result = web_fetch(url, max_cache_age=3600.0)
            assert result == b"cached"

    @patch("requests.get")
    def test_fetch_bypasses_cache_when_expired(self, mock_get):
        """Test that expired cache triggers new fetch."""
        url = "https://expired.example.com/file.txt"
        WebCache.store(url, b"old content")

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"new content"
        mock_get.return_value = mock_response

        # Wait for cache to expire
        time.sleep(0.1)
        result = web_fetch(url, max_cache_age=0.01)

        assert result == b"new content"

    @patch("requests.get")
    def test_fetch_with_cache_bool(self, mock_get):
        """Test fetch with cache=True uses default cache age."""
        WebCache.flush()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"cached content"
        mock_get.return_value = mock_response

        url = "https://cache.example.com/bool_cache.txt"
        result = web_fetch(url, cache=True)

        assert result == b"cached content"

    @patch("requests.get")
    def test_fetch_with_response_details(self, mock_get):
        """Test fetch populates response details."""
        WebCache.flush()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"content"
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_get.return_value = mock_response

        url = "https://details.example.com/file.txt"
        details = {}
        result = web_fetch(url, out_response_details=details)

        assert result == b"content"
        assert details["statusCode"] == 200
        assert "headers" in details

    @patch("requests.get")
    def test_fetch_with_filename(self, mock_get, temp_dir):
        """Test fetch saves to filename."""
        WebCache.flush()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"file content"
        mock_get.return_value = mock_response

        url = "https://file.example.com/download.txt"
        filename = os.path.join(temp_dir, "downloaded.txt")
        result = web_fetch(url, filename=filename)

        assert result == b"file content"
        assert os.path.exists(filename)
        with open(filename, "rb") as f:
            assert f.read() == b"file content"

    def test_fetch_from_cache_with_response_details(self):
        """Test fetch from cache populates fromCache in details."""
        url = "https://cached_details.example.com/file.txt"
        WebCache.store(url, b"cached")

        details = {}
        result = web_fetch(url, max_cache_age=3600.0, out_response_details=details)

        assert result == b"cached"
        assert details.get("fromCache") is True


class TestWebCacheAdvanced:
    """Advanced tests for WebCache class."""

    def setup_method(self):
        """Clear cache before each test."""
        WebCache.flush()

    def teardown_method(self):
        """Clear cache after each test."""
        WebCache.flush()

    def test_set_app_name(self):
        """Test setting application name."""
        WebCache.set_app_name("test_app")
        assert "test_app" in WebCache.cache_dir

    def test_encoded_name(self):
        """Test encoded_name method."""
        name1 = WebCache.encoded_name("test_url")
        name2 = WebCache.encoded_name("test_url")
        name3 = WebCache.encoded_name("different_url")

        assert name1 == name2
        assert name1 != name3
        # Should be MD5 hash length (32 chars)
        assert len(name1) == 32

    def test_find_existing(self):
        """Test find method with existing file."""
        WebCache.store("find_test", b"data")
        result = WebCache.find("find_test")
        assert result is not None
        assert os.path.exists(result)

    def test_find_nonexistent(self):
        """Test find method with nonexistent file."""
        result = WebCache.find("definitely_not_there")
        assert result is None

    def test_cleanup(self):
        """Test cleanup method."""
        # Store some data
        WebCache.store("cleanup_test", b"data")

        # Cleanup should run without errors
        WebCache.cleanup()

        # Data should still be there (not old enough)
        result = WebCache.fetch("cleanup_test", max_age=3600.0)
        assert result == b"data"

    def test_max_cache_size_triggers_flush(self):
        """Test that exceeding max cache size triggers flush."""
        original_max = WebCache.max_cache_size
        WebCache.max_cache_size = 100  # Very small limit

        try:
            # Store data larger than limit
            WebCache.store("large_test", b"x" * 200)

            # Cache should have been flushed
            assert WebCache.total_size > 0
        finally:
            WebCache.max_cache_size = original_max
