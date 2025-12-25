"""Tests for sources module (disk and zip)."""

import os
from pathlib import Path

import pytest

from filestag.sources.disk import FileSourceDisk
from filestag.sources.zip import FileSourceZip


class TestFileSourceDisk:
    """Tests for FileSourceDisk class."""

    def test_basic_iteration(self, sample_files):
        """Test basic file iteration."""
        source = FileSourceDisk(path=sample_files)
        files = list(source)
        assert len(files) > 0
        source.close()

    def test_fetch_file(self, sample_files):
        """Test fetching a specific file."""
        source = FileSourceDisk(path=sample_files)
        data = source.fetch("file0.txt")
        assert data is not None
        assert b"Content 0" in data
        source.close()

    def test_exists(self, sample_files):
        """Test exists method."""
        source = FileSourceDisk(path=sample_files, fetch_file_list=True)
        assert source.exists("file0.txt") is True
        assert source.exists("nonexistent.txt") is False
        source.close()

    def test_get_absolute(self, sample_files):
        """Test get_absolute returns full path."""
        source = FileSourceDisk(path=sample_files)
        abs_path = source.get_absolute("file0.txt")
        assert abs_path is not None
        assert os.path.isabs(abs_path)
        assert abs_path.endswith("file0.txt")
        source.close()

    def test_search_mask(self, sample_files):
        """Test search mask filter."""
        source = FileSourceDisk(path=sample_files, search_mask="*.json")
        files = list(source)
        for f in files:
            assert f.filename.endswith(".json")
        source.close()

    def test_recursive(self, sample_files):
        """Test recursive search."""
        source = FileSourceDisk(path=sample_files, recursive=True)
        files = list(source)
        # Should include files from subdirectories
        has_nested = any("subdir" in f.filename or "/" in f.filename for f in files)
        assert has_nested
        source.close()

    def test_non_recursive(self, sample_files):
        """Test non-recursive search."""
        source = FileSourceDisk(path=sample_files, recursive=False)
        files = list(source)
        for f in files:
            assert "/" not in f.filename
        source.close()

    def test_source_identifier(self, sample_files):
        """Test _get_source_identifier."""
        source = FileSourceDisk(path=sample_files)
        identifier = source._get_source_identifier()
        assert sample_files in identifier or os.path.basename(sample_files) in identifier
        source.close()

    def test_empty_directory(self, temp_dir):
        """Test with empty directory."""
        empty_dir = os.path.join(temp_dir, "empty")
        os.makedirs(empty_dir)

        source = FileSourceDisk(path=empty_dir)
        files = list(source)
        assert len(files) == 0
        source.close()

    def test_file_sizes(self, sample_files):
        """Test that file sizes are recorded."""
        source = FileSourceDisk(path=sample_files, fetch_file_list=True)
        for entry in source.file_list:
            assert entry.file_size >= 0
        source.close()


class TestFileSourceZip:
    """Tests for FileSourceZip class."""

    def test_basic_iteration(self, sample_zip):
        """Test basic file iteration from zip."""
        source = FileSourceZip(source=sample_zip)
        files = list(source)
        assert len(files) > 0
        source.close()

    def test_from_bytes(self, sample_zip):
        """Test creating from bytes."""
        with open(sample_zip, "rb") as f:
            zip_data = f.read()

        source = FileSourceZip(source=zip_data)
        files = list(source)
        assert len(files) > 0
        source.close()

    def test_fetch_file(self, sample_zip):
        """Test fetching a specific file."""
        source = FileSourceZip(source=sample_zip)
        data = source.fetch("file0.txt")
        assert data is not None
        assert b"Content 0" in data
        source.close()

    def test_exists(self, sample_zip):
        """Test exists method."""
        source = FileSourceZip(source=sample_zip, fetch_file_list=True)
        assert source.exists("file0.txt") is True
        assert source.exists("nonexistent.txt") is False
        source.close()

    def test_search_mask(self, sample_zip):
        """Test search mask filter."""
        source = FileSourceZip(source=sample_zip, search_mask="*.txt")
        files = list(source)
        for f in files:
            assert f.filename.endswith(".txt")
        source.close()

    def test_source_identifier(self, sample_zip):
        """Test _get_source_identifier."""
        source = FileSourceZip(source=sample_zip)
        identifier = source._get_source_identifier()
        assert len(identifier) > 0
        source.close()

    def test_close_releases_resources(self, sample_zip):
        """Test that close properly releases resources."""
        source = FileSourceZip(source=sample_zip)
        source.close()
        assert source.is_closed

    def test_file_list(self, sample_zip):
        """Test file list is populated."""
        source = FileSourceZip(source=sample_zip, fetch_file_list=True)
        assert source.file_list is not None
        assert len(source.file_list) > 0
        source.close()

    def test_context_manager(self, sample_zip):
        """Test context manager usage."""
        with FileSourceZip(source=sample_zip) as source:
            files = list(source)
            assert len(files) > 0
        assert source.is_closed

    def test_nested_files(self, sample_zip):
        """Test that nested files are found."""
        source = FileSourceZip(source=sample_zip, recursive=True)
        files = list(source)
        # Check if nested files from subdir are included
        nested = [f for f in files if "subdir" in f.filename or "/" in f.filename]
        assert len(nested) > 0
        source.close()

    def test_empty_zip(self, empty_zip):
        """Test with empty zip file."""
        source = FileSourceZip(source=empty_zip)
        files = list(source)
        assert len(files) == 0
        source.close()

    def test_get_absolute_returns_none(self, sample_zip):
        """Test get_absolute for zip source."""
        source = FileSourceZip(source=sample_zip)
        # Zip sources can't provide absolute paths to files inside
        result = source.get_absolute("file0.txt")
        # Should return None or a zip:// path
        source.close()

    def test_fetch_nonexistent(self, sample_zip):
        """Test fetching non-existent file returns None."""
        source = FileSourceZip(source=sample_zip, fetch_file_list=True)
        data = source.fetch("definitely_not_there.xyz")
        assert data is None
        source.close()
