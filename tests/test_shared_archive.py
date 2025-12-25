"""Tests for shared_archive module."""

import pytest

from filestag.shared_archive import SharedArchive
from filestag.protocols import ZIP_SOURCE_PROTOCOL


class TestSharedArchive:
    """Tests for SharedArchive class."""

    def setup_method(self):
        """Clean up shared archives before each test."""
        # Unload all registered archives
        for identifier in list(SharedArchive.archives.keys()):
            SharedArchive.unload(identifier=identifier)

    def teardown_method(self):
        """Clean up after each test."""
        for identifier in list(SharedArchive.archives.keys()):
            SharedArchive.unload(identifier=identifier)

    def test_register_from_file(self, sample_zip):
        """Test registering an archive from file."""
        archive = SharedArchive.register(sample_zip, "test_archive")
        assert archive is not None
        assert archive.identifier == "test_archive"
        assert "test_archive" in SharedArchive.archives

    def test_register_from_bytes(self, sample_zip):
        """Test registering an archive from bytes."""
        with open(sample_zip, "rb") as f:
            zip_data = f.read()

        archive = SharedArchive.register(zip_data, "bytes_archive")
        assert archive is not None
        assert archive.identifier == "bytes_archive"

    def test_register_with_cache(self, sample_zip):
        """Test registering an archive with caching enabled."""
        archive = SharedArchive.register(sample_zip, "cached_archive", cache=True)
        assert archive is not None

    def test_register_duplicate_returns_existing(self, sample_zip):
        """Test registering same identifier returns existing archive."""
        archive1 = SharedArchive.register(sample_zip, "duplicate_test")
        archive2 = SharedArchive.register(sample_zip, "duplicate_test")
        assert archive1 is archive2

    def test_find_files(self, sample_zip):
        """Test finding files in archive."""
        archive = SharedArchive.register(sample_zip, "find_test")
        files = archive.find_files("*.txt")
        assert len(files) > 0
        for f in files:
            assert f.endswith(".txt")

    def test_find_files_wildcard(self, sample_zip):
        """Test finding all files."""
        archive = SharedArchive.register(sample_zip, "wildcard_test")
        all_files = archive.find_files("*")
        txt_files = archive.find_files("*.txt")
        assert len(all_files) >= len(txt_files)

    def test_exists(self, sample_zip):
        """Test checking if file exists."""
        archive = SharedArchive.register(sample_zip, "exists_test")
        files = archive.find_files("*")
        if files:
            # Filter out directories
            file_list = [f for f in files if not f.endswith("/")]
            if file_list:
                assert archive.exists(file_list[0]) is True
        assert archive.exists("nonexistent_file.xyz") is False

    def test_read_file(self, sample_zip):
        """Test reading file content."""
        archive = SharedArchive.register(sample_zip, "read_test")
        files = archive.find_files("*.txt")
        if files:
            file_list = [f for f in files if not f.endswith("/")]
            if file_list:
                content = archive.read_file(file_list[0])
                assert content is not None
                assert isinstance(content, bytes)

    def test_read_nonexistent_file(self, sample_zip):
        """Test reading non-existent file returns None."""
        archive = SharedArchive.register(sample_zip, "read_none_test")
        content = archive.read_file("nonexistent.file")
        assert content is None

    def test_load_file_class_method(self, sample_zip):
        """Test loading file via class method."""
        SharedArchive.register(sample_zip, "load_test")
        files = SharedArchive.scan("load_test", "*.txt", long_identifier=False)
        if files:
            file_list = [f for f in files if not f.endswith("/")]
            if file_list:
                content = SharedArchive.load_file("load_test", file_list[0])
                assert content is not None

    def test_load_file_with_full_identifier(self, sample_zip):
        """Test loading file with full zip:// identifier."""
        SharedArchive.register(sample_zip, "full_id_test")
        files = SharedArchive.scan("full_id_test", "*.txt")
        if files:
            content = SharedArchive.load_file(files[0])
            assert content is not None

    def test_load_file_direct_from_zip(self, sample_zip):
        """Test loading file directly from zip file path."""
        identifier = f"zip://{sample_zip}/file0.txt"
        content = SharedArchive.load_file(identifier)
        assert content is not None

    def test_exists_at_source(self, sample_zip):
        """Test exists_at_source method."""
        SharedArchive.register(sample_zip, "exists_source_test")
        files = SharedArchive.scan("exists_source_test", "*.txt")
        if files:
            assert SharedArchive.exists_at_source(files[0]) is True

    def test_exists_at_source_direct(self, sample_zip):
        """Test exists_at_source with direct zip path."""
        identifier = f"zip://{sample_zip}/file0.txt"
        assert SharedArchive.exists_at_source(identifier) is True

    def test_exists_at_source_not_found(self, sample_zip):
        """Test exists_at_source with non-existent file."""
        SharedArchive.register(sample_zip, "exists_not_found_test")
        assert SharedArchive.exists_at_source("exists_not_found_test", "nonexistent.file") is False

    def test_exists_at_source_unregistered(self):
        """Test exists_at_source with unregistered archive."""
        assert SharedArchive.exists_at_source("unregistered_archive", "file.txt") is False

    def test_scan(self, sample_zip):
        """Test scanning archive."""
        SharedArchive.register(sample_zip, "scan_test")
        results = SharedArchive.scan("scan_test", "*.txt")
        assert isinstance(results, list)
        for r in results:
            assert r.startswith(ZIP_SOURCE_PROTOCOL)

    def test_scan_short_identifier(self, sample_zip):
        """Test scanning with short identifiers."""
        SharedArchive.register(sample_zip, "scan_short_test")
        results = SharedArchive.scan("scan_short_test", "*.txt", long_identifier=False)
        for r in results:
            assert not r.startswith(ZIP_SOURCE_PROTOCOL)

    def test_scan_with_protocol(self, sample_zip):
        """Test scanning with zip:// prefix."""
        SharedArchive.register(sample_zip, "scan_proto_test")
        results = SharedArchive.scan("zip://@scan_proto_test/", "*.txt")
        assert isinstance(results, list)

    def test_scan_unregistered(self):
        """Test scanning unregistered archive returns empty."""
        results = SharedArchive.scan("nonexistent_archive")
        assert results == []

    def test_is_loaded(self, sample_zip):
        """Test is_loaded method."""
        SharedArchive.register(sample_zip, "loaded_test")
        import os
        normalized = os.path.normpath(sample_zip)
        assert SharedArchive.is_loaded(normalized) is True
        assert SharedArchive.is_loaded("/nonexistent/path.zip") is False

    def test_unload_by_filename(self, sample_zip):
        """Test unloading by filename."""
        SharedArchive.register(sample_zip, "unload_file_test")
        import os
        normalized = os.path.normpath(sample_zip)
        assert SharedArchive.unload(filename=normalized) is True
        assert "unload_file_test" not in SharedArchive.archives

    def test_unload_by_identifier(self, sample_zip):
        """Test unloading by identifier."""
        SharedArchive.register(sample_zip, "unload_id_test")
        assert SharedArchive.unload(identifier="unload_id_test") is True
        assert "unload_id_test" not in SharedArchive.archives

    def test_unload_nonexistent(self):
        """Test unloading non-existent archive."""
        result = SharedArchive.unload(filename="/nonexistent.zip")
        assert result is False

    def test_close(self, sample_zip):
        """Test closing an archive."""
        archive = SharedArchive.register(sample_zip, "close_test")
        archive.close()
        assert archive.zip_file is None

    def test_split_identifier_and_filename(self):
        """Test _split_identifier_and_filename."""
        # Test with registered archive format
        identifier, filename = SharedArchive._split_identifier_and_filename(
            "zip://@myarchive/path/to/file.txt"
        )
        assert identifier == "myarchive"
        assert filename == "path/to/file.txt"

    def test_split_identifier_and_filename_direct_zip(self):
        """Test _split_identifier_and_filename with direct zip path."""
        identifier, filename = SharedArchive._split_identifier_and_filename(
            "zip://archive.zip/file.txt"
        )
        assert identifier == "archive.zip"
        assert filename == "file.txt"

    def test_split_identifier_missing_filename(self):
        """Test _split_identifier_and_filename with missing filename."""
        with pytest.raises(ValueError):
            SharedArchive._split_identifier_and_filename("zip://@myarchive")

    def test_split_identifier_missing_zip_extension(self):
        """Test _split_identifier_and_filename with missing .zip extension."""
        with pytest.raises(ValueError):
            SharedArchive._split_identifier_and_filename("zip://archive/file.txt")

    def test_load_file_from_zip_direct(self, sample_zip):
        """Test loading file directly from zip."""
        content = SharedArchive.load_file_from_zip_direct(sample_zip, "file0.txt")
        assert content is not None
        assert b"Content 0" in content

    def test_check_in_zip_direct(self, sample_zip):
        """Test checking file exists directly in zip."""
        assert SharedArchive.check_in_zip_direct(sample_zip, "file0.txt") is True
        assert SharedArchive.check_in_zip_direct(sample_zip, "nonexistent.file") is False

    def test_load_file_unregistered_returns_none(self):
        """Test load_file with unregistered archive returns None."""
        result = SharedArchive.load_file("unregistered_archive", "file.txt")
        assert result is None
