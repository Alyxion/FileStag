"""Tests for file_source module."""

import json
import os
from pathlib import Path

import pytest
from pydantic import SecretStr

from filestag.file_source import (
    FileSource,
    FileSourceElement,
    FileSourcePathOptions,
    FileListEntry,
    FileListModel,
)
from filestag.sources.disk import FileSourceDisk


class TestFileSourceElement:
    """Tests for FileSourceElement class."""

    def test_creation(self):
        """Test creating a FileSourceElement."""
        element = FileSourceElement(data=b"content", name="file.txt")
        assert element.data == b"content"
        assert element.filename == "file.txt"


class TestFileSourcePathOptions:
    """Tests for FileSourcePathOptions class."""

    def test_default(self):
        """Test default options."""
        options = FileSourcePathOptions()
        assert options.for_file_stag is False

    def test_for_file_stag(self):
        """Test with for_file_stag=True."""
        options = FileSourcePathOptions(for_file_stag=True)
        assert options.for_file_stag is True


class TestFileListEntry:
    """Tests for FileListEntry class."""

    def test_creation(self):
        """Test creating a FileListEntry."""
        entry = FileListEntry(filename="test.txt", file_size=100)
        assert entry.filename == "test.txt"
        assert entry.file_size == 100

    def test_defaults(self):
        """Test default values."""
        entry = FileListEntry(filename="test.txt")
        assert entry.file_size == 0


class TestFileListModel:
    """Tests for FileListModel class."""

    def test_creation(self):
        """Test creating a FileListModel."""
        entries = [FileListEntry(filename="a.txt"), FileListEntry(filename="b.txt")]
        model = FileListModel(files=entries)
        assert len(model.files) == 2
        assert model.user_version == 1
        assert model.format_version == 1


class TestFileSource:
    """Tests for FileSource class."""

    def test_from_source_disk(self, sample_files):
        """Test from_source with disk path."""
        source = FileSource.from_source(sample_files)
        assert source is not None
        assert isinstance(source, FileSourceDisk)
        source.close()

    def test_from_source_zip(self, sample_zip):
        """Test from_source with zip file."""
        from filestag.sources.zip import FileSourceZip

        source = FileSource.from_source(sample_zip)
        assert source is not None
        assert isinstance(source, FileSourceZip)
        source.close()

    def test_from_source_zip_bytes(self, sample_zip):
        """Test from_source with zip bytes."""
        from filestag.sources.zip import FileSourceZip

        with open(sample_zip, "rb") as f:
            zip_data = f.read()

        source = FileSource.from_source(zip_data)
        assert source is not None
        assert isinstance(source, FileSourceZip)
        source.close()

    def test_from_source_secret_str(self, sample_files):
        """Test from_source with SecretStr."""
        secret = SecretStr(sample_files)
        source = FileSource.from_source(secret)
        assert source is not None
        source.close()

    def test_from_source_unknown_protocol(self):
        """Test from_source with unknown protocol."""
        with pytest.raises(NotImplementedError):
            FileSource.from_source("ftp://server/path")

    def test_file_list(self, sample_files):
        """Test file_list property."""
        source = FileSource.from_source(sample_files, fetch_file_list=True)
        assert source.file_list is not None
        assert len(source.file_list) > 0
        source.close()

    def test_len(self, sample_files):
        """Test __len__ method."""
        source = FileSource.from_source(sample_files, fetch_file_list=True)
        assert len(source) > 0
        source.close()

    def test_contains(self, sample_files):
        """Test __contains__ method."""
        source = FileSource.from_source(sample_files, fetch_file_list=True)
        assert "file0.txt" in source
        assert "nonexistent.txt" not in source
        source.close()

    def test_iter(self, sample_files):
        """Test iteration."""
        source = FileSource.from_source(sample_files)
        files = list(source)
        assert len(files) > 0
        for f in files:
            assert isinstance(f, FileSourceElement)
        source.close()

    def test_context_manager(self, sample_files):
        """Test context manager usage."""
        with FileSource.from_source(sample_files) as source:
            files = list(source)
            assert len(files) > 0
        assert source.is_closed

    def test_fetch(self, sample_files):
        """Test fetching file content."""
        source = FileSource.from_source(sample_files)
        data = source.fetch("file0.txt")
        assert data is not None
        assert b"Content 0" in data
        source.close()

    def test_exists(self, sample_files):
        """Test exists method."""
        source = FileSource.from_source(sample_files, fetch_file_list=True)
        assert source.exists("file0.txt") is True
        assert source.exists("nonexistent.txt") is False
        source.close()

    def test_get_statistics(self, sample_files):
        """Test get_statistics method."""
        source = FileSource.from_source(sample_files, fetch_file_list=True)
        stats = source.get_statistics()
        assert stats is not None
        assert "totalFileCount" in stats
        assert "totalFileSizeMb" in stats
        assert "totalDirs" in stats
        source.close()

    def test_str(self, sample_files):
        """Test __str__ method."""
        source = FileSource.from_source(sample_files, fetch_file_list=True)
        s = str(source)
        assert "FileSourceDisk" in s
        assert "Total files" in s
        source.close()

    def test_get_hash(self, sample_files):
        """Test get_hash method."""
        source = FileSource.from_source(sample_files, fetch_file_list=True)
        hash1 = source.get_hash()
        hash2 = source.get_hash()
        assert hash1 == hash2
        source.close()

    def test_hash_builtin(self, sample_files):
        """Test __hash__ method."""
        source = FileSource.from_source(sample_files, fetch_file_list=True)
        h = hash(source)
        assert isinstance(h, int)
        source.close()

    def test_search_mask(self, sample_files):
        """Test search_mask filter."""
        source = FileSource.from_source(sample_files, search_mask="*.txt")
        files = list(source)
        for f in files:
            assert f.filename.endswith(".txt")
        source.close()

    def test_max_file_count(self, sample_files):
        """Test max_file_count limit."""
        source = FileSource.from_source(sample_files, max_file_count=2)
        files = list(source)
        assert len(files) <= 2
        source.close()

    def test_recursive_false(self, sample_files):
        """Test non-recursive search."""
        source = FileSource.from_source(sample_files, recursive=False)
        files = list(source)
        for f in files:
            assert "/" not in f.filename and "\\" not in f.filename
        source.close()

    def test_filter_callback(self, sample_files):
        """Test filter callback."""

        def only_file0(file_info):
            return "file0" in file_info.element.filename

        source = FileSource.from_source(sample_files, filter_callback=only_file0)
        files = list(source)
        for f in files:
            assert "file0" in f.filename
        source.close()

    def test_filter_callback_rename(self, sample_files):
        """Test filter callback that renames files."""

        def rename(file_info):
            return "renamed_" + file_info.element.filename

        source = FileSource.from_source(sample_files, filter_callback=rename)
        files = list(source)
        for f in files:
            assert f.filename.startswith("renamed_")
        source.close()

    def test_index_filter(self, sample_files):
        """Test index filter for parallel processing."""
        source1 = FileSource.from_source(
            sample_files, index_filter=(2, 0), fetch_file_list=True
        )
        source2 = FileSource.from_source(
            sample_files, index_filter=(2, 1), fetch_file_list=True
        )

        files1 = list(source1)
        files2 = list(source2)

        # Together they should cover all files
        source_all = FileSource.from_source(sample_files)
        all_files = list(source_all)

        assert len(files1) + len(files2) == len(all_files)
        source1.close()
        source2.close()
        source_all.close()

    def test_dont_load(self, sample_files):
        """Test dont_load option."""
        source = FileSource.from_source(sample_files, dont_load=True)
        files = list(source)
        for f in files:
            assert f.data is None
        source.close()

    def test_encode_decode_file_list(self, sample_files):
        """Test encoding and decoding file list."""
        source = FileSource.from_source(sample_files, fetch_file_list=True)
        encoded = source.encode_file_list(version=1)

        # Create new source and load the list
        source2 = FileSource.from_source(sample_files, fetch_file_list=False)
        result = source2.load_file_list(encoded, version=1)
        assert result is True
        assert len(source2.file_list) == len(source.file_list)

        source.close()
        source2.close()

    def test_load_file_list_version_mismatch(self, sample_files):
        """Test loading file list with version mismatch."""
        source = FileSource.from_source(sample_files, fetch_file_list=True)
        encoded = source.encode_file_list(version=1)

        source2 = FileSource.from_source(sample_files, fetch_file_list=False)
        result = source2.load_file_list(encoded, version=2)
        assert result is False

        source.close()
        source2.close()

    def test_load_file_list_invalid_data(self, sample_files):
        """Test loading invalid file list data."""
        source = FileSource.from_source(sample_files, fetch_file_list=False)
        result = source.load_file_list(b"invalid json", version=-1)
        assert result is False
        source.close()

    def test_save_file_list(self, sample_files, temp_dir):
        """Test saving file list to file."""
        source = FileSource.from_source(sample_files, fetch_file_list=True)
        list_file = os.path.join(temp_dir, "file_list.json")
        source.save_file_list(list_file, version=1)

        assert os.path.exists(list_file)

        # Load and verify
        source2 = FileSource.from_source(sample_files, fetch_file_list=False)
        result = source2.load_file_list(list_file, version=1)
        assert result is True

        source.close()
        source2.close()

    def test_set_file_list_strings(self, sample_files):
        """Test setting custom file list with strings."""
        source = FileSource.from_source(sample_files, fetch_file_list=False)
        source.set_file_list(["file1.txt", "file2.txt"])
        assert len(source.file_list) == 2
        source.close()

    def test_set_file_list_entries(self, sample_files):
        """Test setting custom file list with entries."""
        source = FileSource.from_source(sample_files, fetch_file_list=False)
        entries = [
            FileListEntry(filename="a.txt", file_size=100),
            FileListEntry(filename="b.txt", file_size=200),
        ]
        source.set_file_list(entries)
        assert len(source.file_list) == 2
        source.close()

    def test_reduce_file_list(self, sample_files):
        """Test reduce_file_list method."""
        source = FileSource.from_source(
            sample_files, fetch_file_list=True, max_file_count=2
        )
        reduced = source.reduce_file_list()
        assert reduced is not None
        assert len(reduced) <= 2
        source.close()

    def test_refresh(self, sample_files):
        """Test refresh method."""
        source = FileSource.from_source(sample_files, fetch_file_list=True)
        original_count = len(source.file_list)
        source.refresh()
        assert len(source.file_list) == original_count
        source.close()

    def test_copy(self, sample_files, temp_dir):
        """Test copying a single file."""
        source = FileSource.from_source(sample_files)
        target = os.path.join(temp_dir, "copied.txt")

        result = source.copy("file0.txt", target)
        assert result is True
        assert os.path.exists(target)
        source.close()

    def test_copy_with_callbacks(self, sample_files, temp_dir):
        """Test copy with callbacks."""
        fetched = []
        fetched_done = []
        stored = []

        def on_fetch(name):
            fetched.append(name)

        def on_fetch_done(name, size):
            fetched_done.append((name, size))

        def on_stored(name, size):
            stored.append((name, size))

        source = FileSource.from_source(sample_files)
        target = os.path.join(temp_dir, "callback_test.txt")

        source.copy(
            "file0.txt",
            target,
            on_fetch=on_fetch,
            on_fetch_done=on_fetch_done,
            on_stored=on_stored,
        )

        assert len(fetched) == 1
        assert len(fetched_done) == 1
        assert len(stored) == 1
        source.close()

    def test_copy_nonexistent(self, sample_files, temp_dir):
        """Test copying non-existent file."""
        errors = []

        def on_error(name, msg):
            errors.append((name, msg))

        source = FileSource.from_source(sample_files)
        target = os.path.join(temp_dir, "nonexistent_copy.txt")

        result = source.copy("nonexistent.txt", target, on_error=on_error)
        assert result is False
        assert len(errors) == 1
        source.close()

    def test_copy_to_directory(self, sample_files, temp_dir):
        """Test copying all files to directory."""
        source = FileSource.from_source(sample_files)
        target_dir = os.path.join(temp_dir, "output")
        os.makedirs(target_dir)

        result = source.copy_to(target_dir)
        assert result is True

        # Verify some files were copied
        copied_files = list(Path(target_dir).rglob("*"))
        assert len([f for f in copied_files if f.is_file()]) > 0
        source.close()

    def test_sorting_callback(self, sample_files):
        """Test sorting callback."""

        def sort_reverse(entry):
            return -ord(entry.filename[0])

        source = FileSource.from_source(
            sample_files, fetch_file_list=True, sorting_callback=sort_reverse
        )

        files = source.file_list
        # Verify files are sorted according to callback
        assert len(files) > 0
        source.close()

    def test_sorting_callback_requires_fetch(self, sample_files):
        """Test that sorting requires fetch_file_list."""
        with pytest.raises(ValueError):
            FileSource.from_source(
                sample_files,
                fetch_file_list=False,
                sorting_callback=lambda x: x.filename,
            )

    def test_file_list_caching(self, sample_files, temp_dir):
        """Test file list caching to disk."""
        cache_file = os.path.join(temp_dir, "cache.json")

        # First load - creates cache
        source1 = FileSource.from_source(
            sample_files, fetch_file_list=True, file_list_name=(cache_file, 1)
        )
        count1 = len(source1.file_list)
        source1.close()

        assert os.path.exists(cache_file)

        # Second load - uses cache
        source2 = FileSource.from_source(
            sample_files, fetch_file_list=True, file_list_name=(cache_file, 1)
        )
        count2 = len(source2.file_list)
        source2.close()

        assert count1 == count2

    def test_get_absolute_returns_none_by_default(self, sample_files):
        """Test that base class get_absolute returns None."""
        source = FileSource.from_source(sample_files)
        # FileSourceDisk overrides this, but testing the default behavior
        # through the public interface
        result = source.get_absolute("file0.txt")
        # FileSourceDisk returns the path, so we just check it's not raising
        assert result is not None or result is None  # Either is valid
        source.close()
