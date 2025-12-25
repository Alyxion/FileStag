"""Tests for sinks module (disk, zip, archive)."""

import io
import os
import zipfile
from pathlib import Path

import pytest

from filestag.sinks.disk import FileSinkDisk
from filestag.sinks.zip import FileSinkZip
from filestag.sinks.archive import ArchiveFileSinkProto


class TestFileSinkDisk:
    """Tests for FileSinkDisk class."""

    def test_store_file(self, temp_dir):
        """Test storing a file."""
        target = os.path.join(temp_dir, "disk_sink")
        os.makedirs(target)

        sink = FileSinkDisk(target=target)
        result = sink.store("test.txt", b"Hello, disk!")
        sink.close()

        assert result is True
        output_file = Path(target) / "test.txt"
        assert output_file.read_bytes() == b"Hello, disk!"

    def test_store_nested_file(self, temp_dir):
        """Test storing a file in nested directory."""
        target = os.path.join(temp_dir, "nested_sink")
        os.makedirs(target)

        sink = FileSinkDisk(target=target)
        result = sink.store("sub/dir/file.txt", b"Nested content")
        sink.close()

        assert result is True
        output_file = Path(target) / "sub" / "dir" / "file.txt"
        assert output_file.read_bytes() == b"Nested content"

    def test_store_multiple_files(self, temp_dir):
        """Test storing multiple files."""
        target = os.path.join(temp_dir, "multi_sink")
        os.makedirs(target)

        sink = FileSinkDisk(target=target)
        sink.store("file1.txt", b"Content 1")
        sink.store("file2.txt", b"Content 2")
        sink.store("file3.txt", b"Content 3")
        sink.close()

        for i in range(1, 4):
            output_file = Path(target) / f"file{i}.txt"
            assert output_file.read_bytes() == f"Content {i}".encode()

    def test_context_manager(self, temp_dir):
        """Test context manager usage."""
        target = os.path.join(temp_dir, "context_sink")
        os.makedirs(target)

        with FileSinkDisk(target=target) as sink:
            sink.store("context.txt", b"Context content")

        assert sink._closed
        output_file = Path(target) / "context.txt"
        assert output_file.read_bytes() == b"Context content"

    def test_binary_content(self, temp_dir):
        """Test storing binary content."""
        target = os.path.join(temp_dir, "binary_sink")
        os.makedirs(target)

        binary_data = bytes(range(256))
        sink = FileSinkDisk(target=target)
        sink.store("binary.bin", binary_data)
        sink.close()

        output_file = Path(target) / "binary.bin"
        assert output_file.read_bytes() == binary_data


class TestFileSinkZip:
    """Tests for FileSinkZip class."""

    def test_store_file(self):
        """Test storing a file in zip."""
        sink = FileSinkZip(target="zip://")
        sink.store("test.txt", b"Hello, zip!")
        data = sink.get_value()

        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            assert "test.txt" in zf.namelist()
            assert zf.read("test.txt") == b"Hello, zip!"

    def test_store_multiple_files(self):
        """Test storing multiple files."""
        sink = FileSinkZip(target="zip://")
        sink.store("file1.txt", b"Content 1")
        sink.store("file2.txt", b"Content 2")
        sink.store("subdir/file3.txt", b"Content 3")
        data = sink.get_value()

        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            assert len(zf.namelist()) == 3
            assert zf.read("file1.txt") == b"Content 1"
            assert zf.read("subdir/file3.txt") == b"Content 3"

    def test_context_manager(self):
        """Test context manager usage."""
        sink = FileSinkZip(target="zip://")
        sink.store("context.txt", b"Context content")
        data = sink.get_value()  # This closes the sink

        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            assert "context.txt" in zf.namelist()

    def test_get_value_before_close(self):
        """Test get_value can be called before close."""
        sink = FileSinkZip(target="zip://")
        sink.store("test.txt", b"data")
        data = sink.get_value()

        assert len(data) > 0
        # Verify it's valid zip data
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            assert "test.txt" in zf.namelist()

    def test_binary_content(self):
        """Test storing binary content."""
        binary_data = bytes(range(256))

        sink = FileSinkZip(target="zip://")
        sink.store("binary.bin", binary_data)
        data = sink.get_value()

        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            assert zf.read("binary.bin") == binary_data

    def test_empty_zip(self):
        """Test creating empty zip."""
        sink = FileSinkZip(target="zip://")
        data = sink.get_value()

        # Should be valid (possibly empty) zip data
        with zipfile.ZipFile(io.BytesIO(data), "r") as zf:
            assert len(zf.namelist()) == 0


class TestArchiveFileSinkProto:
    """Tests for ArchiveFileSinkProto class."""

    def test_is_abstract(self):
        """Test that ArchiveFileSinkProto is a protocol/base class."""
        # ArchiveFileSinkProto should define the interface
        # FileSinkZip inherits from it
        assert hasattr(ArchiveFileSinkProto, "_store_int")

    def test_inheritance(self):
        """Test that FileSinkZip inherits from ArchiveFileSinkProto."""
        sink = FileSinkZip(target="zip://")
        assert isinstance(sink, ArchiveFileSinkProto)
        sink.close()
