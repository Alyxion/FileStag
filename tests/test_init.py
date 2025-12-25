"""Tests for filestag package initialization."""

import pytest


class TestLazyAzureLoading:
    """Tests for lazy Azure module loading."""

    def test_azure_lazy_loading(self):
        """Test that accessing Azure classes works or raises ImportError."""
        import filestag

        try:
            # Azure may or may not be installed
            blob_path = filestag.AzureBlobPath
            # If it imports, it should be a class
            assert blob_path is not None
        except ImportError as e:
            # If not installed, should have helpful message
            assert "azure" in str(e).lower()
            assert "pip install" in str(e)

    def test_azure_source_lazy_loading(self):
        """Test AzureStorageFileSource lazy loading."""
        import filestag

        try:
            source = filestag.AzureStorageFileSource
            assert source is not None
        except ImportError as e:
            assert "azure" in str(e).lower()

    def test_azure_sink_lazy_loading(self):
        """Test AzureStorageFileSink lazy loading."""
        import filestag

        try:
            sink = filestag.AzureStorageFileSink
            assert sink is not None
        except ImportError as e:
            assert "azure" in str(e).lower()

    def test_unknown_attribute_error(self):
        """Test that unknown attributes raise AttributeError."""
        import filestag

        with pytest.raises(AttributeError) as exc_info:
            _ = filestag.NonExistentClass

        assert "NonExistentClass" in str(exc_info.value)


class TestExports:
    """Tests for package exports."""

    def test_version_available(self):
        """Test that version is available."""
        import filestag

        assert hasattr(filestag, "__version__")
        assert isinstance(filestag.__version__, str)

    def test_core_classes_available(self):
        """Test that core classes are available."""
        import filestag

        assert hasattr(filestag, "FileStag")
        assert hasattr(filestag, "FileSource")
        assert hasattr(filestag, "FileSink")
        assert hasattr(filestag, "FilePath")

    def test_cache_classes_available(self):
        """Test that cache classes are available."""
        import filestag

        assert hasattr(filestag, "Cache")
        assert hasattr(filestag, "CacheRef")
        assert hasattr(filestag, "DiskCache")
        assert hasattr(filestag, "get_global_cache")

    def test_source_implementations_available(self):
        """Test that source implementations are available."""
        import filestag

        assert hasattr(filestag, "FileSourceDisk")
        assert hasattr(filestag, "FileSourceZip")

    def test_sink_implementations_available(self):
        """Test that sink implementations are available."""
        import filestag

        assert hasattr(filestag, "FileSinkDisk")
        assert hasattr(filestag, "FileSinkZip")

    def test_web_functions_available(self):
        """Test that web functions are available."""
        import filestag

        assert hasattr(filestag, "WebCache")
        assert hasattr(filestag, "web_fetch")
