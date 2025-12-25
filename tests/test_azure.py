"""
Tests for Azure Blob Storage functionality.

These tests require Azure credentials to be set in environment variables:
- AZ_TEST_SOURCE_ACCOUNT_NAME: Azure storage account name
- AZ_TEST_SOURCE_KEY: Azure storage account key

The tests will be skipped if credentials are not available.
"""

from __future__ import annotations

import hashlib
import os
import time

import pytest

# Check if Azure credentials are configured
AZURE_ACCOUNT_NAME = os.environ.get("AZ_TEST_SOURCE_ACCOUNT_NAME", "")
AZURE_ACCOUNT_KEY = os.environ.get("AZ_TEST_SOURCE_KEY", "")
AZURE_CONFIGURED = bool(AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY)

# Connection string template using environment variable substitution
CONNECTION_STRING = (
    "azure://DefaultEndpointsProtocol=https;"
    "AccountName={{env.AZ_TEST_SOURCE_ACCOUNT_NAME}};"
    "AccountKey={{env.AZ_TEST_SOURCE_KEY}};"
    "EndpointSuffix=core.windows.net"
)

# Test container name
TEST_CONTAINER = "filestag-test"


def get_connection_string(container: str = TEST_CONTAINER, path: str = "") -> str:
    """Build a connection string for the test container."""
    result = f"{CONNECTION_STRING}/{container}"
    if path:
        result = f"{result}/{path}"
    return result


@pytest.fixture(scope="module")
def azure_test_sink():
    """Create a test sink and ensure the container exists."""
    if not AZURE_CONFIGURED:
        pytest.skip("Azure credentials not configured")

    from filestag import FileSink

    sink = FileSink.with_target(get_connection_string())
    yield sink


@pytest.fixture(scope="module")
def azure_test_source():
    """Create a test source for reading from the container."""
    if not AZURE_CONFIGURED:
        pytest.skip("Azure credentials not configured")

    from filestag import FileSource

    source = FileSource.from_source(get_connection_string(), fetch_file_list=True)
    yield source
    source.close()


class TestAzureBlobPath:
    """Tests for AzureBlobPath parsing."""

    def test_connection_string_parsing(self):
        """Test parsing a connection string."""
        from filestag.azure.blob_path import AzureBlobPath
        from filestag.protocols import AZURE_PROTOCOL_HEADER

        conn_string = (
            "DefaultEndpointsProtocol=https;"
            "AccountName=testaccount;"
            "AccountKey=testkey123;"
            "EndpointSuffix=core.windows.net"
        )
        full_url = f"{AZURE_PROTOCOL_HEADER}{conn_string}"
        elements = AzureBlobPath.split_azure_url(full_url, insert_key=False)
        assert elements[0] == conn_string
        assert elements[1] == ""
        assert elements[2] == ""

    def test_connection_string_with_container(self):
        """Test parsing connection string with container name."""
        from filestag.azure.blob_path import AzureBlobPath
        from filestag.protocols import AZURE_PROTOCOL_HEADER

        conn_string = (
            "DefaultEndpointsProtocol=https;"
            "AccountName=testaccount;"
            "AccountKey=testkey123;"
            "EndpointSuffix=core.windows.net"
        )
        container = "mycontainer"
        full_url = f"{AZURE_PROTOCOL_HEADER}{conn_string}/{container}"
        elements = AzureBlobPath.split_azure_url(full_url, insert_key=False)
        assert elements[0] == conn_string
        assert elements[1] == container
        assert elements[2] == ""

    def test_connection_string_with_path(self):
        """Test parsing connection string with container and path."""
        from filestag.azure.blob_path import AzureBlobPath
        from filestag.protocols import AZURE_PROTOCOL_HEADER

        conn_string = (
            "DefaultEndpointsProtocol=https;"
            "AccountName=testaccount;"
            "AccountKey=testkey123;"
            "EndpointSuffix=core.windows.net"
        )
        container = "mycontainer"
        prefix = "subfolder/data"
        full_url = f"{AZURE_PROTOCOL_HEADER}{conn_string}/{container}/{prefix}"
        elements = AzureBlobPath.split_azure_url(full_url, insert_key=False)
        assert elements[0] == conn_string
        assert elements[1] == container
        assert elements[2] == prefix

    def test_from_string(self):
        """Test creating AzureBlobPath from string."""
        from filestag.azure.blob_path import AzureBlobPath

        conn_string = (
            "DefaultEndpointsProtocol=https;"
            "AccountName=testaccount;"
            "AccountKey=testkey123;"
            "EndpointSuffix=core.windows.net"
        )
        path = AzureBlobPath.from_string(conn_string)
        assert path.account_name == "testaccount"
        assert path.account_key == "testkey123"
        assert path.default_endpoints_protocol == "https"
        assert path.endpoint_suffix == "core.windows.net"

    def test_get_connection_string(self):
        """Test generating connection string from path."""
        from filestag.azure.blob_path import AzureBlobPath

        path = AzureBlobPath(
            default_endpoints_protocol="https",
            account_name="testaccount",
            account_key="testkey123",
            endpoint_suffix="core.windows.net",
            container_name="mycontainer",
        )
        conn = path.get_connection_string()
        assert "AccountName=testaccount" in conn
        assert "AccountKey=testkey123" in conn
        assert "DefaultEndpointsProtocol=https" in conn

    def test_sas_url_detection(self):
        """Test that SAS URLs are detected correctly."""
        from filestag.azure.blob_path import AzureBlobPath

        sas_url = "https://account.blob.core.windows.net/container?sp=r&st=2024-01-01&se=2024-12-31&spr=https&sig=abc123"
        path = AzureBlobPath.from_string(sas_url)
        assert path.is_sas()
        assert path.sas_url == sas_url


@pytest.mark.skipif(not AZURE_CONFIGURED, reason="Azure credentials not configured")
class TestAzureStorageFileSource:
    """Tests for AzureStorageFileSource (requires credentials)."""

    def test_source_creation(self, azure_test_sink):
        """Test creating an Azure file source.

        Uses azure_test_sink fixture to ensure container exists first.
        """
        from filestag import FileSource

        source = FileSource.from_source(
            get_connection_string(), fetch_file_list=True
        )
        assert source is not None
        source.close()

    def test_upload_and_list(self, azure_test_sink):
        """Test uploading a file and listing it."""
        from filestag import FileSource

        # Upload a test file
        test_name = f"test_file_{int(time.time())}.txt"
        test_data = b"Hello from FileStag test!"
        azure_test_sink.store(test_name, test_data)

        # Wait a moment for consistency
        time.sleep(1)

        # List and verify
        source = FileSource.from_source(
            get_connection_string(), fetch_file_list=True
        )
        file_names = [f.filename for f in source.file_list]
        assert test_name in file_names
        source.close()

    def test_fetch_file(self, azure_test_sink):
        """Test fetching a file from Azure."""
        from filestag import FileSource

        # Upload a test file
        test_name = f"fetch_test_{int(time.time())}.txt"
        test_data = b"Fetch test data content"
        azure_test_sink.store(test_name, test_data)

        time.sleep(1)

        # Fetch and verify
        source = FileSource.from_source(
            get_connection_string(), fetch_file_list=True
        )
        fetched = source.fetch(test_name)
        assert fetched == test_data
        source.close()

    def test_file_exists(self, azure_test_sink):
        """Test checking if a file exists."""
        from filestag import FileSource

        # Upload a test file
        test_name = f"exists_test_{int(time.time())}.txt"
        azure_test_sink.store(test_name, b"exists test")

        time.sleep(1)

        source = FileSource.from_source(
            get_connection_string(), fetch_file_list=True
        )
        assert source.exists(test_name)
        assert not source.exists("nonexistent_file_xyz.txt")
        source.close()

    def test_fetch_nonexistent(self):
        """Test fetching a non-existent file returns None."""
        from filestag import FileSource

        source = FileSource.from_source(
            get_connection_string(), fetch_file_list=True
        )
        result = source.fetch("this_file_does_not_exist_12345.txt")
        assert result is None
        source.close()

    def test_iteration(self, azure_test_sink):
        """Test iterating through files."""
        from filestag import FileSource

        # Upload some test files
        prefix = f"iter_test_{int(time.time())}"
        for i in range(3):
            azure_test_sink.store(f"{prefix}_{i}.txt", f"content {i}".encode())

        time.sleep(1)

        source = FileSource.from_source(
            get_connection_string(),
            search_mask=f"{prefix}_*.txt",
            fetch_file_list=True
        )
        count = 0
        for element in source:
            count += 1
            assert element.data is not None
        assert count == 3
        source.close()

    def test_search_path(self, azure_test_sink):
        """Test using a search path prefix."""
        from filestag import FileSource

        # Upload files with a prefix
        prefix = f"subdir_{int(time.time())}"
        for i in range(2):
            azure_test_sink.store(f"{prefix}/file_{i}.txt", f"sub content {i}".encode())

        time.sleep(1)

        source = FileSource.from_source(
            get_connection_string(path=prefix),
            fetch_file_list=True
        )
        assert len(source.file_list) >= 2
        source.close()


@pytest.mark.skipif(not AZURE_CONFIGURED, reason="Azure credentials not configured")
class TestAzureStorageFileSink:
    """Tests for AzureStorageFileSink (requires credentials)."""

    def test_sink_creation(self):
        """Test creating an Azure file sink."""
        from filestag import FileSink

        sink = FileSink.with_target(get_connection_string())
        assert sink is not None

    def test_store_and_retrieve(self):
        """Test storing and retrieving a file."""
        from filestag import FileSink, FileSource

        sink = FileSink.with_target(get_connection_string())

        test_name = f"sink_test_{int(time.time())}.bin"
        test_data = b"Binary test data \x00\x01\x02\x03"

        result = sink.store(test_name, test_data)
        assert result is True

        time.sleep(1)

        source = FileSource.from_source(
            get_connection_string(), fetch_file_list=True
        )
        fetched = source.fetch(test_name)
        assert fetched == test_data
        source.close()

    def test_overwrite_behavior(self):
        """Test overwrite parameter."""
        from filestag import FileSink

        sink = FileSink.with_target(get_connection_string())

        test_name = f"overwrite_test_{int(time.time())}.txt"

        # First store
        sink.store(test_name, b"original")
        time.sleep(0.5)

        # Overwrite should succeed
        result = sink.store(test_name, b"updated", overwrite=True)
        assert result is True

        # No overwrite should fail (file exists)
        result = sink.store(test_name, b"blocked", overwrite=False)
        assert result is False


@pytest.mark.skipif(not AZURE_CONFIGURED, reason="Azure credentials not configured")
class TestAzureSasUrls:
    """Tests for SAS URL creation and usage."""

    def test_create_sas_url(self, azure_test_sink):
        """Test creating a SAS URL for a blob."""
        from filestag import FileSource, web_fetch

        # Upload a test file
        test_name = f"sas_test_{int(time.time())}.txt"
        test_data = b"SAS URL test content"
        azure_test_sink.store(test_name, test_data)

        time.sleep(1)

        # Create SAS URL
        source = FileSource.from_source(
            get_connection_string(), fetch_file_list=True
        )
        sas_url = source.create_sas_url(test_name, end_time_days=1.0)
        assert sas_url.startswith("https://")
        assert "sig=" in sas_url

        # Verify we can fetch via SAS URL
        fetched = web_fetch(sas_url, max_cache_age=0)
        assert fetched == test_data
        source.close()

    def test_get_absolute_returns_sas(self, azure_test_sink):
        """Test that get_absolute returns a SAS URL."""
        from filestag import FileSource

        test_name = f"abs_test_{int(time.time())}.txt"
        azure_test_sink.store(test_name, b"absolute test")

        time.sleep(1)

        source = FileSource.from_source(
            get_connection_string(), fetch_file_list=True
        )
        abs_url = source.get_absolute(test_name)
        assert abs_url is not None
        assert "sig=" in abs_url
        source.close()


@pytest.mark.skipif(not AZURE_CONFIGURED, reason="Azure credentials not configured")
class TestAzureAsync:
    """Tests for async Azure operations."""

    async def test_fetch_async(self, azure_test_sink):
        """Test async file fetching from Azure."""
        from filestag import FileSource

        # Upload a test file
        test_name = f"async_test_{int(time.time())}.txt"
        test_data = b"Async fetch test data"
        azure_test_sink.store(test_name, test_data)

        import asyncio
        await asyncio.sleep(1)

        source = FileSource.from_source(
            get_connection_string(), fetch_file_list=True
        )
        fetched = await source.fetch_async(test_name)
        assert fetched == test_data
        source.close()

    async def test_copy_async(self, azure_test_sink, temp_dir):
        """Test async file copying from Azure."""
        import os
        from filestag import FileSource

        # Upload a test file
        test_name = f"copy_async_{int(time.time())}.txt"
        test_data = b"Async copy test data"
        azure_test_sink.store(test_name, test_data)

        import asyncio
        await asyncio.sleep(1)

        target_file = os.path.join(temp_dir, "copied.txt")

        source = FileSource.from_source(
            get_connection_string(), fetch_file_list=True
        )
        result = await source.copy_async(test_name, target_file)
        assert result is True

        with open(target_file, "rb") as f:
            assert f.read() == test_data
        source.close()


@pytest.mark.skipif(not AZURE_CONFIGURED, reason="Azure credentials not configured")
class TestAzureCacheValidation:
    """Tests for Azure file list cache validation with automatic invalidation."""

    def test_cache_validation_detects_new_files(self, temp_dir):
        """
        Test that validate_cache=True detects when new files are added.

        This test:
        1. Creates initial files in Azure
        2. Creates a cached file list
        3. Verifies cache is used on second load
        4. Adds a new file to Azure
        5. Verifies cache is invalidated with validate_cache=True
        6. Cleans up all test files
        """
        from filestag import FileSource, FileSink

        # Use a unique prefix for this test to avoid conflicts
        test_prefix = f"cache_test_{int(time.time())}"
        test_path = get_connection_string(path=test_prefix)
        cache_file = os.path.join(temp_dir, "azure_cache.json")

        # Create a sink for uploading test files
        sink = FileSink.with_target(get_connection_string())

        try:
            # Step 1: Upload initial test files
            initial_files = [f"{test_prefix}/file1.txt", f"{test_prefix}/file2.txt"]
            for filename in initial_files:
                sink.store(filename, f"content of {filename}".encode())

            time.sleep(1)  # Allow Azure to propagate

            # Step 2: Create initial cached file list
            source1 = FileSource.from_source(
                test_path,
                file_list_name=cache_file,
                fetch_file_list=True,
            )
            initial_count = len(source1.file_list)
            assert initial_count == 2, f"Expected 2 files, got {initial_count}"
            source1.close()

            # Verify cache file was created
            assert os.path.exists(cache_file), "Cache file should exist"

            # Step 3: Load from cache (should be fast, no Azure call for file list)
            source2 = FileSource.from_source(
                test_path,
                file_list_name=cache_file,
                fetch_file_list=True,
                validate_cache=False,  # Don't validate, just use cache
            )
            assert len(source2.file_list) == 2, "Should load 2 files from cache"
            source2.close()

            # Step 4: Add a new file to Azure
            new_file = f"{test_prefix}/file3_new.txt"
            sink.store(new_file, b"new file content")
            time.sleep(1)  # Allow Azure to propagate

            # Step 5a: Without validation, cache is stale (still shows 2 files)
            source3 = FileSource.from_source(
                test_path,
                file_list_name=cache_file,
                fetch_file_list=True,
                validate_cache=False,
            )
            assert len(source3.file_list) == 2, "Without validation, cache shows old count"
            source3.close()

            # Step 5b: With validation, cache should be invalidated and refreshed
            source4 = FileSource.from_source(
                test_path,
                file_list_name=cache_file,
                fetch_file_list=True,
                validate_cache=True,  # Enable validation!
            )
            assert len(source4.file_list) == 3, f"With validation, should detect new file. Got {len(source4.file_list)}"
            source4.close()

            # Step 6: Verify cache was updated
            source5 = FileSource.from_source(
                test_path,
                file_list_name=cache_file,
                fetch_file_list=True,
                validate_cache=False,
            )
            assert len(source5.file_list) == 3, "Updated cache should have 3 files"
            source5.close()

        finally:
            # Cleanup: Delete all test files from Azure
            cleanup_source = FileSource.from_source(
                get_connection_string(),
                search_path=test_prefix,
                fetch_file_list=True,
            )
            for entry in cleanup_source.file_list:
                try:
                    # Delete using the container client
                    from filestag.azure.source import AzureStorageFileSource
                    if isinstance(cleanup_source, AzureStorageFileSource):
                        blob_client = cleanup_source.container_client.get_blob_client(
                            cleanup_source.search_path + entry.filename
                        )
                        blob_client.delete_blob()
                except Exception:
                    pass  # Best effort cleanup
            cleanup_source.close()

    def test_cache_validation_detects_deleted_files(self, temp_dir):
        """Test that validate_cache=True detects when files are deleted."""
        from filestag import FileSource, FileSink

        test_prefix = f"cache_del_test_{int(time.time())}"
        test_path = get_connection_string(path=test_prefix)
        cache_file = os.path.join(temp_dir, "azure_cache_del.json")

        sink = FileSink.with_target(get_connection_string())

        try:
            # Upload initial files
            files_to_create = [
                f"{test_prefix}/keep.txt",
                f"{test_prefix}/delete_me.txt",
            ]
            for filename in files_to_create:
                sink.store(filename, f"content of {filename}".encode())

            time.sleep(1)

            # Create cached file list
            source1 = FileSource.from_source(
                test_path,
                file_list_name=cache_file,
                fetch_file_list=True,
            )
            assert len(source1.file_list) == 2
            source1.close()

            # Delete one file from Azure
            from filestag.azure.source import AzureStorageFileSource
            delete_source = FileSource.from_source(get_connection_string())
            if isinstance(delete_source, AzureStorageFileSource):
                blob_client = delete_source.container_client.get_blob_client(
                    f"{test_prefix}/delete_me.txt"
                )
                blob_client.delete_blob()
            delete_source.close()

            time.sleep(1)

            # With validation, should detect the deletion
            source2 = FileSource.from_source(
                test_path,
                file_list_name=cache_file,
                fetch_file_list=True,
                validate_cache=True,
            )
            assert len(source2.file_list) == 1, f"Should detect deletion. Got {len(source2.file_list)}"
            source2.close()

        finally:
            # Cleanup
            cleanup_source = FileSource.from_source(
                get_connection_string(),
                search_path=test_prefix,
                fetch_file_list=True,
            )
            for entry in cleanup_source.file_list:
                try:
                    from filestag.azure.source import AzureStorageFileSource
                    if isinstance(cleanup_source, AzureStorageFileSource):
                        blob_client = cleanup_source.container_client.get_blob_client(
                            cleanup_source.search_path + entry.filename
                        )
                        blob_client.delete_blob()
                except Exception:
                    pass
            cleanup_source.close()
