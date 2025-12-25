"""Tests for async methods."""

import os
import time
from unittest.mock import patch, MagicMock, AsyncMock

import pytest

from filestag import FileStag, web_fetch_async
from filestag.web import WebCache


class TestWebFetchAsync:
    """Tests for web_fetch_async function."""

    def setup_method(self):
        """Clear cache before each test."""
        WebCache.flush()

    def teardown_method(self):
        """Clear cache after each test."""
        WebCache.flush()

    async def test_fetch_from_cache(self):
        """Test async fetching from cache when available."""
        url = "https://cached.example.com/file.txt"
        await WebCache.store_async(url, b"cached content")

        result = await web_fetch_async(url, max_cache_age=3600.0)
        assert result == b"cached content"

    @patch("httpx.AsyncClient")
    async def test_fetch_from_web(self, mock_client_class):
        """Test async fetching from web when not cached."""
        WebCache.flush()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"web content"
        mock_response.headers = {}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        url = "https://test.example.com/new_file.txt"
        result = await web_fetch_async(url)

        assert result == b"web content"

    @patch("httpx.AsyncClient")
    async def test_fetch_caches_result(self, mock_client_class):
        """Test that async fetched content is cached."""
        WebCache.flush()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"to be cached"
        mock_response.headers = {}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        url = "https://cache.example.com/cache_me.txt"
        await web_fetch_async(url, max_cache_age=3600.0)

        # Should now be in cache
        cached = await WebCache.fetch_async(url, max_age=3600.0)
        assert cached == b"to be cached"

    @patch("httpx.AsyncClient")
    async def test_fetch_error_returns_none(self, mock_client_class):
        """Test that HTTP errors return None."""
        WebCache.flush()

        mock_response = MagicMock()
        mock_response.status_code = 404

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        url = "https://error.example.com/not_found.txt"
        result = await web_fetch_async(url)

        assert result is None

    @patch("httpx.AsyncClient")
    async def test_fetch_exception_returns_none(self, mock_client_class):
        """Test that async exceptions return None."""
        import httpx

        WebCache.flush()

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(side_effect=httpx.RequestError("Network error"))
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        url = "https://exception.example.com/error.txt"
        result = await web_fetch_async(url)

        assert result is None


class TestWebCacheAsync:
    """Tests for async WebCache methods."""

    def setup_method(self):
        """Clear cache before each test."""
        WebCache.flush()

    def teardown_method(self):
        """Clear cache after each test."""
        WebCache.flush()

    async def test_store_and_fetch_async(self):
        """Test async storing and fetching from cache."""
        await WebCache.store_async("test_key", b"test_data")
        result = await WebCache.fetch_async("test_key", max_age=3600.0)
        assert result == b"test_data"

    async def test_fetch_async_nonexistent(self):
        """Test async fetching non-existent key returns None."""
        result = await WebCache.fetch_async("nonexistent_key", max_age=3600.0)
        assert result is None

    async def test_max_age_async(self):
        """Test async max_age expiration."""
        await WebCache.store_async("age_key", b"data")

        # Immediate fetch should succeed
        result = await WebCache.fetch_async("age_key", max_age=10.0)
        assert result == b"data"

        # With very short max_age after time passes
        time.sleep(0.1)
        result = await WebCache.fetch_async("age_key", max_age=0.01)
        assert result is None

    async def test_flush_async(self):
        """Test async cache flush."""
        await WebCache.store_async("key1", b"data1")
        await WebCache.store_async("key2", b"data2")

        await WebCache.flush_async()

        assert await WebCache.fetch_async("key1", max_age=3600.0) is None
        assert await WebCache.fetch_async("key2", max_age=3600.0) is None

    async def test_cleanup_async(self):
        """Test async cache cleanup."""
        await WebCache.store_async("cleanup_test", b"data")
        await WebCache.cleanup_async()

        # Data should still be there (not old enough to be cleaned)
        result = await WebCache.fetch_async("cleanup_test", max_age=3600.0)
        assert result == b"data"


class TestFileStagAsync:
    """Tests for async FileStag methods."""

    async def test_load_async(self, temp_dir):
        """Test async file loading."""
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "wb") as f:
            f.write(b"async test content")

        result = await FileStag.load_async(test_file)
        assert result == b"async test content"

    async def test_save_async(self, temp_dir):
        """Test async file saving."""
        test_file = os.path.join(temp_dir, "save_test.txt")

        result = await FileStag.save_async(test_file, b"saved content")
        assert result is True

        with open(test_file, "rb") as f:
            assert f.read() == b"saved content"

    async def test_delete_async(self, temp_dir):
        """Test async file deletion."""
        test_file = os.path.join(temp_dir, "delete_test.txt")
        with open(test_file, "wb") as f:
            f.write(b"to delete")

        result = await FileStag.delete_async(test_file)
        assert result is True
        assert not os.path.exists(test_file)

    async def test_delete_async_nonexistent(self, temp_dir):
        """Test async delete of non-existent file returns False."""
        test_file = os.path.join(temp_dir, "nonexistent.txt")
        result = await FileStag.delete_async(test_file)
        assert result is False

    async def test_load_text_async(self, temp_dir):
        """Test async text loading."""
        test_file = os.path.join(temp_dir, "text_test.txt")
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("async text content")

        result = await FileStag.load_text_async(test_file)
        assert result == "async text content"

    async def test_save_text_async(self, temp_dir):
        """Test async text saving."""
        test_file = os.path.join(temp_dir, "text_save.txt")

        result = await FileStag.save_text_async(test_file, "saved text")
        assert result is True

        with open(test_file, "r", encoding="utf-8") as f:
            assert f.read() == "saved text"

    async def test_load_json_async(self, temp_dir):
        """Test async JSON loading."""
        import json

        test_file = os.path.join(temp_dir, "test.json")
        data = {"key": "value", "number": 42}
        with open(test_file, "w", encoding="utf-8") as f:
            json.dump(data, f)

        result = await FileStag.load_json_async(test_file)
        assert result == data

    async def test_save_json_async(self, temp_dir):
        """Test async JSON saving."""
        import json

        test_file = os.path.join(temp_dir, "save.json")
        data = {"key": "value", "number": 42}

        result = await FileStag.save_json_async(test_file, data)
        assert result is True

        with open(test_file, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded == data

    async def test_copy_async(self, temp_dir):
        """Test async file copying."""
        source_file = os.path.join(temp_dir, "source.txt")
        target_file = os.path.join(temp_dir, "target.txt")

        with open(source_file, "wb") as f:
            f.write(b"copy this")

        result = await FileStag.copy_async(source_file, target_file)
        assert result is True

        with open(target_file, "rb") as f:
            assert f.read() == b"copy this"

    async def test_exists_async(self, temp_dir):
        """Test async file existence check."""
        test_file = os.path.join(temp_dir, "exists.txt")
        with open(test_file, "wb") as f:
            f.write(b"exists")

        assert await FileStag.exists_async(test_file) is True
        assert await FileStag.exists_async(os.path.join(temp_dir, "not_there.txt")) is False

    async def test_load_async_nonexistent(self, temp_dir):
        """Test async load returns None for non-existent file."""
        result = await FileStag.load_async(os.path.join(temp_dir, "nonexistent.txt"))
        assert result is None

    async def test_load_async_as_stream(self, temp_dir):
        """Test async load with as_stream=True."""
        from io import BytesIO

        test_file = os.path.join(temp_dir, "stream_test.txt")
        with open(test_file, "wb") as f:
            f.write(b"stream content")

        result = await FileStag.load_async(test_file, as_stream=True)
        assert isinstance(result, BytesIO)
        assert result.read() == b"stream content"

    async def test_copy_async_with_create_dir(self, temp_dir):
        """Test async copy with directory creation."""
        source_file = os.path.join(temp_dir, "copy_source.txt")
        target_file = os.path.join(temp_dir, "subdir", "copied.txt")

        with open(source_file, "wb") as f:
            f.write(b"copy to new dir")

        result = await FileStag.copy_async(source_file, target_file, create_dir=True)
        assert result is True

        with open(target_file, "rb") as f:
            assert f.read() == b"copy to new dir"

    async def test_copy_async_without_create_dir_fails(self, temp_dir):
        """Test async copy fails without directory creation."""
        source_file = os.path.join(temp_dir, "copy_source2.txt")
        target_file = os.path.join(temp_dir, "nonexistent_subdir", "copied.txt")

        with open(source_file, "wb") as f:
            f.write(b"copy to new dir")

        result = await FileStag.copy_async(source_file, target_file, create_dir=False)
        assert result is False

    async def test_load_async_bytes_passthrough(self):
        """Test async load passes through bytes directly."""
        data = b"direct bytes"
        result = await FileStag.load_async(data)
        assert result == data

    async def test_save_async_none_raises(self, temp_dir):
        """Test async save with None data raises."""
        test_file = os.path.join(temp_dir, "none_test.txt")
        with pytest.raises(ValueError):
            await FileStag.save_async(test_file, None)

    async def test_save_text_async_none_raises(self, temp_dir):
        """Test async save_text with None raises."""
        test_file = os.path.join(temp_dir, "none_text.txt")
        with pytest.raises(ValueError):
            await FileStag.save_text_async(test_file, None)

    async def test_save_json_async_none_raises(self, temp_dir):
        """Test async save_json with None raises."""
        test_file = os.path.join(temp_dir, "none_json.json")
        with pytest.raises(ValueError):
            await FileStag.save_json_async(test_file, None)

    async def test_load_text_async_with_crlf(self, temp_dir):
        """Test async load_text with CRLF conversion."""
        test_file = os.path.join(temp_dir, "crlf_test.txt")
        with open(test_file, "wb") as f:
            f.write(b"line1\r\nline2\r\n")

        # Convert to LF
        result = await FileStag.load_text_async(test_file, crlf=False)
        assert result == "line1\nline2\n"

        # Convert to CRLF
        with open(test_file, "wb") as f:
            f.write(b"line1\nline2\n")
        result = await FileStag.load_text_async(test_file, crlf=True)
        assert result == "line1\r\nline2\r\n"


class TestWebFetchAsyncAdvanced:
    """Advanced tests for web_fetch_async."""

    def setup_method(self):
        """Clear cache before each test."""
        WebCache.flush()

    def teardown_method(self):
        """Clear cache after each test."""
        WebCache.flush()

    @patch("httpx.AsyncClient")
    async def test_fetch_with_cache_bool(self, mock_client_class):
        """Test async fetch with cache=True uses default cache age."""
        WebCache.flush()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"cached content"
        mock_response.headers = {}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        url = "https://cache.example.com/bool_cache.txt"
        result = await web_fetch_async(url, cache=True)

        assert result == b"cached content"

    @patch("httpx.AsyncClient")
    async def test_fetch_with_response_details(self, mock_client_class):
        """Test async fetch populates response details."""
        WebCache.flush()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"content"
        mock_response.headers = {"Content-Type": "text/plain"}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        url = "https://details.example.com/file.txt"
        details = {}
        result = await web_fetch_async(url, out_response_details=details)

        assert result == b"content"
        assert details["statusCode"] == 200
        assert "headers" in details

    @patch("httpx.AsyncClient")
    async def test_fetch_with_filename_async(self, mock_client_class, temp_dir):
        """Test async fetch saves to filename."""
        WebCache.flush()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"file content"
        mock_response.headers = {}

        mock_client = AsyncMock()
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_client_class.return_value = mock_client

        url = "https://file.example.com/download.txt"
        filename = os.path.join(temp_dir, "downloaded.txt")
        result = await web_fetch_async(url, filename=filename)

        assert result == b"file content"
        assert os.path.exists(filename)
        with open(filename, "rb") as f:
            assert f.read() == b"file content"

    async def test_fetch_from_cache_with_response_details(self):
        """Test async fetch from cache populates fromCache in details."""
        url = "https://cached_details.example.com/file.txt"
        await WebCache.store_async(url, b"cached")

        details = {}
        result = await web_fetch_async(url, max_cache_age=3600.0, out_response_details=details)

        assert result == b"cached"
        assert details.get("fromCache") is True


class TestDiskCacheAsync:
    """Tests for async DiskCache methods."""

    async def test_set_and_get_async(self, temp_dir):
        """Test async storing and retrieving from disk cache."""
        from filestag.cache import DiskCache

        cache = DiskCache(version="1", cache_dir=temp_dir)
        await cache.set_async("test_key", {"data": "test_value"})
        result = await cache.get_async("test_key")
        assert result == {"data": "test_value"}

    async def test_get_async_nonexistent(self, temp_dir):
        """Test async get returns default for non-existent key."""
        from filestag.cache import DiskCache

        cache = DiskCache(version="1", cache_dir=temp_dir)
        result = await cache.get_async("nonexistent_key", default="default_value")
        assert result == "default_value"

    async def test_delete_async(self, temp_dir):
        """Test async deletion from disk cache."""
        from filestag.cache import DiskCache

        cache = DiskCache(version="1", cache_dir=temp_dir)
        await cache.set_async("delete_me", "value")

        # Verify it exists
        result = await cache.get_async("delete_me")
        assert result == "value"

        # Delete it
        deleted = await cache.delete_async("delete_me")
        assert deleted is True

        # Verify it's gone
        result = await cache.get_async("delete_me", default=None)
        assert result is None

    async def test_delete_async_nonexistent(self, temp_dir):
        """Test async delete of non-existent key returns False."""
        from filestag.cache import DiskCache

        cache = DiskCache(version="1", cache_dir=temp_dir)
        result = await cache.delete_async("nonexistent_key")
        assert result is False

    async def test_clear_async(self, temp_dir):
        """Test async cache clear."""
        from filestag.cache import DiskCache

        cache = DiskCache(version="1", cache_dir=temp_dir)
        await cache.set_async("key1", "value1")
        await cache.set_async("key2", "value2")

        await cache.clear_async()

        # Both keys should be gone
        assert await cache.get_async("key1", default=None) is None
        assert await cache.get_async("key2", default=None) is None

    async def test_version_mismatch_async(self, temp_dir):
        """Test async get returns default when version doesn't match."""
        from filestag.cache import DiskCache

        cache = DiskCache(version="1", cache_dir=temp_dir)
        await cache.set_async("versioned_key", "value", version="1")

        # Same version should work
        result = await cache.get_async("versioned_key", version="1")
        assert result == "value"

        # Different version should return default
        result = await cache.get_async("versioned_key", version="2", default="not_found")
        assert result == "not_found"

    async def test_key_with_version_syntax_async(self, temp_dir):
        """Test async get/set with key@version syntax."""
        from filestag.cache import DiskCache

        cache = DiskCache(version="1", cache_dir=temp_dir)
        await cache.set_async("mykey@2", "versioned_value")

        result = await cache.get_async("mykey@2")
        assert result == "versioned_value"

    async def test_complex_data_async(self, temp_dir):
        """Test async storing complex data types."""
        from filestag.cache import DiskCache

        cache = DiskCache(version="1", cache_dir=temp_dir)

        # Test with nested dict
        complex_data = {
            "string": "value",
            "number": 42,
            "float": 3.14,
            "list": [1, 2, 3],
            "nested": {"a": 1, "b": 2},
        }
        await cache.set_async("complex", complex_data)
        result = await cache.get_async("complex")
        assert result == complex_data


class TestFileSourceAsync:
    """Tests for async FileSource methods."""

    async def test_fetch_async(self, temp_dir):
        """Test async file fetching from source."""
        from filestag import FileSource

        # Create test file
        test_file = os.path.join(temp_dir, "test.txt")
        with open(test_file, "wb") as f:
            f.write(b"source content")

        source = FileSource.from_source(temp_dir)
        result = await source.fetch_async("test.txt")
        assert result == b"source content"

    async def test_fetch_async_nonexistent(self, temp_dir):
        """Test async fetch returns None for non-existent file."""
        from filestag import FileSource

        source = FileSource.from_source(temp_dir)
        result = await source.fetch_async("nonexistent.txt")
        assert result is None

    async def test_copy_async(self, temp_dir):
        """Test async file copying from source."""
        from filestag import FileSource

        # Create source dir and file
        source_dir = os.path.join(temp_dir, "source")
        os.makedirs(source_dir)
        test_file = os.path.join(source_dir, "copy_me.txt")
        with open(test_file, "wb") as f:
            f.write(b"copy this content")

        target_file = os.path.join(temp_dir, "copied.txt")

        source = FileSource.from_source(source_dir)
        result = await source.copy_async("copy_me.txt", target_file)
        assert result is True

        with open(target_file, "rb") as f:
            assert f.read() == b"copy this content"

    async def test_copy_async_skip_existing(self, temp_dir):
        """Test async copy skips existing files when overwrite=False."""
        from filestag import FileSource

        # Create source file
        source_dir = os.path.join(temp_dir, "source")
        os.makedirs(source_dir)
        test_file = os.path.join(source_dir, "file.txt")
        with open(test_file, "wb") as f:
            f.write(b"source content")

        # Create existing target
        target_file = os.path.join(temp_dir, "target.txt")
        with open(target_file, "wb") as f:
            f.write(b"existing content")

        skipped = []
        source = FileSource.from_source(source_dir)
        result = await source.copy_async(
            "file.txt", target_file, overwrite=False, on_skip=lambda f: skipped.append(f)
        )
        assert result is False
        assert len(skipped) == 1

        # Content should be unchanged
        with open(target_file, "rb") as f:
            assert f.read() == b"existing content"

    async def test_save_and_load_file_list_async(self, temp_dir):
        """Test async file list save and load."""
        from filestag import FileSource

        # Create source with files
        source_dir = os.path.join(temp_dir, "source")
        os.makedirs(source_dir)
        for i in range(3):
            with open(os.path.join(source_dir, f"file{i}.txt"), "wb") as f:
                f.write(f"content {i}".encode())

        source = FileSource.from_source(source_dir, fetch_file_list=True)
        assert len(source.file_list) == 3

        # Save file list
        list_file = os.path.join(temp_dir, "file_list.json")
        await source.save_file_list_async(list_file, version=1)
        assert os.path.exists(list_file)

        # Load into new source
        new_source = FileSource.from_source(source_dir, fetch_file_list=False)
        loaded = await new_source.load_file_list_async(list_file, version=1)
        assert loaded is True
        assert len(new_source.file_list) == 3

    async def test_load_file_list_async_version_mismatch(self, temp_dir):
        """Test async file list load fails on version mismatch."""
        from filestag import FileSource

        # Create source with files
        source_dir = os.path.join(temp_dir, "source")
        os.makedirs(source_dir)
        with open(os.path.join(source_dir, "file.txt"), "wb") as f:
            f.write(b"content")

        source = FileSource.from_source(source_dir, fetch_file_list=True)

        # Save with version 1
        list_file = os.path.join(temp_dir, "file_list.json")
        await source.save_file_list_async(list_file, version=1)

        # Try to load with version 2
        new_source = FileSource.from_source(source_dir, fetch_file_list=False)
        loaded = await new_source.load_file_list_async(list_file, version=2)
        assert loaded is False


class TestFileSinkAsync:
    """Tests for async FileSink methods."""

    async def test_store_async_disk(self, temp_dir):
        """Test async file storage to disk."""
        from filestag import FileSink

        sink = FileSink.with_target(temp_dir)
        result = await sink.store_async("test.txt", b"async stored content")
        assert result is True

        with open(os.path.join(temp_dir, "test.txt"), "rb") as f:
            assert f.read() == b"async stored content"

    async def test_store_async_zip(self):
        """Test async file storage to memory zip."""
        from filestag import FileSink

        sink = FileSink.with_target("zip://")
        await sink.store_async("file1.txt", b"content 1")
        await sink.store_async("file2.txt", b"content 2")
        sink.close()

        zip_data = sink.get_value()
        assert zip_data is not None
        assert len(zip_data) > 0

        # Verify contents using zipfile
        import zipfile
        import io

        with zipfile.ZipFile(io.BytesIO(zip_data)) as zf:
            assert zf.read("file1.txt") == b"content 1"
            assert zf.read("file2.txt") == b"content 2"

    async def test_store_async_overwrite_false(self, temp_dir):
        """Test async store with overwrite=False skips existing files."""
        from filestag import FileSink

        # Create existing file
        existing_file = os.path.join(temp_dir, "existing.txt")
        with open(existing_file, "wb") as f:
            f.write(b"original content")

        sink = FileSink.with_target(temp_dir)
        result = await sink.store_async("existing.txt", b"new content", overwrite=False)
        assert result is False

        # Content should be unchanged
        with open(existing_file, "rb") as f:
            assert f.read() == b"original content"

    async def test_store_async_with_subdirectory(self, temp_dir):
        """Test async store creates subdirectories."""
        from filestag import FileSink

        sink = FileSink.with_target(temp_dir)
        result = await sink.store_async("subdir/nested/file.txt", b"nested content")
        assert result is True

        target_file = os.path.join(temp_dir, "subdir", "nested", "file.txt")
        assert os.path.exists(target_file)
        with open(target_file, "rb") as f:
            assert f.read() == b"nested content"


class TestFileSourceAsyncAdvanced:
    """Advanced async tests for FileSource."""

    async def test_fetch_async_with_web_cache(self, temp_dir):
        """Test async fetch using web cache."""
        from filestag import FileSource
        from filestag.web import WebCache

        WebCache.flush()

        # Create test file
        test_file = os.path.join(temp_dir, "cached.txt")
        with open(test_file, "wb") as f:
            f.write(b"cached content")

        source = FileSource.from_source(temp_dir, max_web_cache_age=3600.0)

        # First fetch - should read from disk and store in cache
        result = await source.fetch_async("cached.txt")
        assert result == b"cached content"

        # Second fetch - should read from cache
        result = await source.fetch_async("cached.txt")
        assert result == b"cached content"

        WebCache.flush()

    async def test_copy_async_with_callbacks(self, temp_dir):
        """Test async copy with all callbacks."""
        from filestag import FileSource

        source_dir = os.path.join(temp_dir, "source")
        os.makedirs(source_dir)
        test_file = os.path.join(source_dir, "callback_test.txt")
        with open(test_file, "wb") as f:
            f.write(b"callback content")

        target_file = os.path.join(temp_dir, "callback_target.txt")

        fetch_calls = []
        fetch_done_calls = []
        stored_calls = []

        source = FileSource.from_source(source_dir)
        result = await source.copy_async(
            "callback_test.txt",
            target_file,
            on_fetch=lambda f: fetch_calls.append(f),
            on_fetch_done=lambda f, s: fetch_done_calls.append((f, s)),
            on_stored=lambda f, s: stored_calls.append((f, s)),
        )

        assert result is True
        assert fetch_calls == ["callback_test.txt"]
        assert len(fetch_done_calls) == 1
        assert fetch_done_calls[0][0] == "callback_test.txt"
        assert len(stored_calls) == 1

    async def test_copy_async_file_not_found(self, temp_dir):
        """Test async copy with non-existent source file."""
        from filestag import FileSource

        source = FileSource.from_source(temp_dir)
        errors = []
        result = await source.copy_async(
            "nonexistent.txt",
            os.path.join(temp_dir, "target.txt"),
            on_error=lambda f, e: errors.append((f, e)),
        )

        assert result is False
        assert len(errors) == 1
        assert errors[0][0] == "nonexistent.txt"

    async def test_load_file_list_async_invalid_json(self, temp_dir):
        """Test async load file list with invalid JSON."""
        from filestag import FileSource

        invalid_file = os.path.join(temp_dir, "invalid.json")
        with open(invalid_file, "w") as f:
            f.write("not valid json")

        source = FileSource.from_source(temp_dir, fetch_file_list=False)
        loaded = await source.load_file_list_async(invalid_file)
        assert loaded is False

    async def test_load_file_list_async_wrong_format(self, temp_dir):
        """Test async load file list with wrong format version."""
        import json
        from filestag import FileSource

        wrong_format_file = os.path.join(temp_dir, "wrong_format.json")
        with open(wrong_format_file, "w") as f:
            json.dump({"format_version": 2, "files": []}, f)

        source = FileSource.from_source(temp_dir, fetch_file_list=False)
        loaded = await source.load_file_list_async(wrong_format_file)
        assert loaded is False


class TestZipSourceAsync:
    """Tests for async operations with zip sources."""

    async def test_fetch_async_from_zip(self, temp_dir):
        """Test async fetch from zip file."""
        import zipfile
        from filestag import FileSource

        # Create a zip file
        zip_path = os.path.join(temp_dir, "test.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("file.txt", b"zip content")

        source = FileSource.from_source(zip_path)
        result = await source.fetch_async("file.txt")
        assert result == b"zip content"
        source.close()

    async def test_copy_async_from_zip(self, temp_dir):
        """Test async copy from zip file."""
        import zipfile
        from filestag import FileSource

        # Create a zip file
        zip_path = os.path.join(temp_dir, "test.zip")
        with zipfile.ZipFile(zip_path, "w") as zf:
            zf.writestr("copy_me.txt", b"copy from zip")

        target_file = os.path.join(temp_dir, "copied.txt")

        source = FileSource.from_source(zip_path)
        result = await source.copy_async("copy_me.txt", target_file)
        assert result is True

        with open(target_file, "rb") as f:
            assert f.read() == b"copy from zip"
        source.close()
