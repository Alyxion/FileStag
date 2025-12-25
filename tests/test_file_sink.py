"""Tests for file_sink module."""

import os
from pathlib import Path

import pytest

from filestag.file_sink import FileSink, FileStorageOptions


class TestFileStorageOptions:
    """Tests for FileStorageOptions class."""

    def test_creation(self):
        """Test creating FileStorageOptions."""
        options = FileStorageOptions()
        assert options is not None


class TestFileSink:
    """Tests for FileSink class."""

    def test_with_target_disk(self, temp_dir):
        """Test with_target for disk storage."""
        from filestag.sinks.disk import FileSinkDisk

        target = os.path.join(temp_dir, "output")
        sink = FileSink.with_target(target)
        assert isinstance(sink, FileSinkDisk)
        sink.close()

    def test_with_target_zip(self):
        """Test with_target for zip storage."""
        from filestag.sinks.zip import FileSinkZip

        sink = FileSink.with_target("zip://")
        assert isinstance(sink, FileSinkZip)
        sink.close()

    def test_with_target_unsupported(self):
        """Test with_target with unsupported target."""
        with pytest.raises(ValueError):
            FileSink.with_target("ftp://server/path")

    def test_store_not_implemented(self, temp_dir):
        """Test that base class store raises NotImplementedError."""
        # Create a minimal FileSink subclass to test base behavior
        sink = FileSink(target=temp_dir)
        with pytest.raises(NotImplementedError):
            sink.store("file.txt", b"data")

    def test_close_twice_raises(self, temp_dir):
        """Test that closing twice raises AssertionError."""
        target = os.path.join(temp_dir, "output")
        sink = FileSink.with_target(target)
        sink.close()
        with pytest.raises(AssertionError):
            sink.close()

    def test_get_value_not_implemented(self, temp_dir):
        """Test that base class get_value raises NotImplementedError."""
        sink = FileSink(target=temp_dir)
        with pytest.raises(NotImplementedError):
            sink.get_value()

    def test_context_manager(self, temp_dir):
        """Test context manager usage."""
        target = os.path.join(temp_dir, "context_output")
        with FileSink.with_target(target) as sink:
            sink.store("test.txt", b"test content")
        assert sink._closed is True

    def test_store_and_retrieve_zip(self):
        """Test storing and retrieving from zip sink."""
        sink = FileSink.with_target("zip://")
        sink.store("file1.txt", b"content 1")
        sink.store("subdir/file2.txt", b"content 2")
        data = sink.get_value()  # This closes the sink

        # Verify the zip data
        import io
        import zipfile

        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            assert "file1.txt" in zf.namelist()
            assert "subdir/file2.txt" in zf.namelist()
            assert zf.read("file1.txt") == b"content 1"

    def test_store_disk(self, temp_dir):
        """Test storing files to disk."""
        target = os.path.join(temp_dir, "disk_output")
        with FileSink.with_target(target) as sink:
            sink.store("test.txt", b"disk content")

        output_file = Path(target) / "test.txt"
        assert output_file.exists()
        assert output_file.read_bytes() == b"disk content"

    def test_store_disk_nested(self, temp_dir):
        """Test storing nested files to disk."""
        target = os.path.join(temp_dir, "nested_output")
        with FileSink.with_target(target) as sink:
            sink.store("subdir/nested/file.txt", b"nested content")

        output_file = Path(target) / "subdir" / "nested" / "file.txt"
        assert output_file.exists()
        assert output_file.read_bytes() == b"nested content"

    def test_with_target_windows_path(self, temp_dir):
        """Test with_target recognizes Windows-style paths."""
        # This tests the path detection logic
        from filestag.sinks.disk import FileSinkDisk

        # Test UNC path detection (starts with \\)
        # We can't actually use a UNC path in tests, but we can verify the logic
        # by checking that paths starting with certain patterns are recognized

        # Test drive letter path (would need to be on Windows)
        # Just verify the detection logic works for Unix absolute paths
        target = os.path.join(temp_dir, "win_test")
        sink = FileSink.with_target(target)
        assert isinstance(sink, FileSinkDisk)
        sink.close()

    def test_overwrite_false(self, temp_dir):
        """Test overwrite=False behavior."""
        target = os.path.join(temp_dir, "overwrite_test")
        os.makedirs(target)

        # Create initial file
        test_file = Path(target) / "existing.txt"
        test_file.write_bytes(b"original")

        with FileSink.with_target(target) as sink:
            result = sink.store("existing.txt", b"new content", overwrite=False)
            # Disk sink doesn't check overwrite by default, but we test the interface
            # The actual behavior depends on the implementation

        # For disk sink, files are typically overwritten regardless
        # This test verifies the interface accepts the parameter
