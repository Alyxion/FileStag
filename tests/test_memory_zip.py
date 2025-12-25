"""Tests for memory_zip module."""

import zipfile
from pathlib import Path

import pytest

from filestag.memory_zip import MemoryZip


class TestMemoryZip:
    """Tests for MemoryZip class."""

    def test_create_empty(self):
        """Test creating an empty MemoryZip."""
        mz = MemoryZip()
        data = mz.to_bytes()
        assert len(data) > 0

        # Verify it's valid zip data
        import io
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            assert len(zf.namelist()) == 0

    def test_add_file(self):
        """Test adding a file to MemoryZip."""
        mz = MemoryZip()
        mz.writestr("test.txt", "Hello, World!")
        data = mz.to_bytes()

        import io
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            assert "test.txt" in zf.namelist()
            assert zf.read("test.txt") == b"Hello, World!"

    def test_add_multiple_files(self):
        """Test adding multiple files."""
        mz = MemoryZip()
        mz.writestr("file1.txt", "Content 1")
        mz.writestr("file2.txt", "Content 2")
        mz.writestr("subdir/file3.txt", "Content 3")
        data = mz.to_bytes()

        import io
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            assert len(zf.namelist()) == 3
            assert zf.read("file1.txt") == b"Content 1"
            assert zf.read("file2.txt") == b"Content 2"
            assert zf.read("subdir/file3.txt") == b"Content 3"

    def test_load_from_bytes(self, sample_zip):
        """Test loading MemoryZip from bytes."""
        with open(sample_zip, "rb") as f:
            zip_data = f.read()

        mz = MemoryZip(zip_data)
        namelist = mz.namelist()
        assert len(namelist) > 0
        mz.close()

    def test_load_from_file(self, sample_zip):
        """Test loading MemoryZip from file path."""
        mz = MemoryZip(sample_zip)
        namelist = mz.namelist()
        assert len(namelist) > 0

        # Can read files from it
        for name in namelist:
            if not name.endswith("/"):
                data = mz.read(name)
                assert data is not None
        mz.close()

    def test_load_from_nonexistent_file(self):
        """Test loading from non-existent file raises error."""
        with pytest.raises(FileNotFoundError):
            MemoryZip("/nonexistent/path/to/file.zip")

    def test_to_bytes_closes_zip(self):
        """Test that to_bytes closes the zip."""
        mz = MemoryZip()
        mz.writestr("test.txt", "content")
        data = mz.to_bytes()

        # Calling to_bytes again should still work (returns cached data)
        data2 = mz.to_bytes()
        assert data == data2

    def test_close_multiple_times(self):
        """Test that close can be called multiple times safely."""
        mz = MemoryZip()
        mz.close()
        mz.close()  # Should not raise

    def test_add_binary_data(self):
        """Test adding binary data."""
        mz = MemoryZip()
        binary_data = bytes(range(256))
        mz.writestr("binary.bin", binary_data)
        data = mz.to_bytes()

        import io
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            assert zf.read("binary.bin") == binary_data

    def test_append_mode(self, sample_zip):
        """Test that loading from file allows appending."""
        mz = MemoryZip(sample_zip)
        original_count = len(mz.namelist())

        mz.writestr("new_file.txt", "New content")
        data = mz.to_bytes()

        import io
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            assert len(zf.namelist()) == original_count + 1
            assert "new_file.txt" in zf.namelist()
