"""Tests for protocols module."""

from filestag.protocols import (
    AZURE_PROTOCOL_HEADER,
    AZURE_DEFAULT_ENDPOINTS_HEADER,
    AZURE_SAS_URL_COMPONENT,
    ZIP_SOURCE_PROTOCOL,
    HTTPS_PROTOCOL_URL_HEADER,
    HTTP_PROTOCOL_URL_HEADER,
    FILE_PATH_PROTOCOL_URL_HEADER,
    is_azure_storage_source,
)


class TestProtocolConstants:
    """Tests for protocol constants."""

    def test_azure_protocol_header(self):
        """Test Azure protocol header constant."""
        assert AZURE_PROTOCOL_HEADER == "azure://"

    def test_azure_default_endpoints_header(self):
        """Test Azure default endpoints header constant."""
        assert AZURE_DEFAULT_ENDPOINTS_HEADER == "DefaultEndpoints"

    def test_azure_sas_url_component(self):
        """Test Azure SAS URL component constant."""
        assert AZURE_SAS_URL_COMPONENT == "blob.core.windows.net"

    def test_zip_source_protocol(self):
        """Test ZIP source protocol constant."""
        assert ZIP_SOURCE_PROTOCOL == "zip://"

    def test_https_protocol(self):
        """Test HTTPS protocol header constant."""
        assert HTTPS_PROTOCOL_URL_HEADER == "https://"

    def test_http_protocol(self):
        """Test HTTP protocol header constant."""
        assert HTTP_PROTOCOL_URL_HEADER == "http://"

    def test_file_path_protocol(self):
        """Test file path protocol header constant."""
        assert FILE_PATH_PROTOCOL_URL_HEADER == "file://"


class TestIsAzureStorageSource:
    """Tests for is_azure_storage_source function."""

    def test_azure_protocol(self):
        """Test detection of azure:// protocol."""
        assert is_azure_storage_source("azure://some/path") is True

    def test_default_endpoints(self):
        """Test detection of DefaultEndpoints connection string."""
        assert is_azure_storage_source("DefaultEndpointsProtocol=https;AccountName=test") is True

    def test_sas_url_https(self):
        """Test detection of SAS URL with https."""
        assert is_azure_storage_source("https://account.blob.core.windows.net/container?sv=...") is True

    def test_sas_url_http(self):
        """Test detection of SAS URL with http."""
        assert is_azure_storage_source("http://account.blob.core.windows.net/container?sv=...") is True

    def test_regular_https_url(self):
        """Test that regular HTTPS URLs are not detected as Azure."""
        assert is_azure_storage_source("https://example.com/file.txt") is False

    def test_local_path(self):
        """Test that local paths are not detected as Azure."""
        assert is_azure_storage_source("/path/to/file.txt") is False

    def test_zip_protocol(self):
        """Test that ZIP protocol is not detected as Azure."""
        assert is_azure_storage_source("zip://archive.zip/file.txt") is False

    def test_file_protocol(self):
        """Test that file protocol is not detected as Azure."""
        assert is_azure_storage_source("file:///path/to/file.txt") is False

    def test_empty_string(self):
        """Test with empty string."""
        assert is_azure_storage_source("") is False
