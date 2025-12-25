"""Tests for file_stag module."""

import io
import json
import os
from pathlib import Path

import pytest
from pydantic import SecretStr

from filestag.file_stag import FileStag
from filestag.shared_archive import SharedArchive


class TestFileStag:
    """Tests for FileStag class."""

    def setup_method(self):
        """Clean up shared archives before each test."""
        for identifier in list(SharedArchive.archives.keys()):
            SharedArchive.unload(identifier=identifier)

    def test_is_simple_local_path(self):
        """Test is_simple with local path."""
        assert FileStag.is_simple("/path/to/file.txt") is True

    def test_is_simple_url(self):
        """Test is_simple with URL."""
        assert FileStag.is_simple("https://example.com/file.txt") is False

    def test_is_simple_zip(self):
        """Test is_simple with zip protocol."""
        assert FileStag.is_simple("zip://archive.zip/file.txt") is False

    def test_is_simple_secret_str(self):
        """Test is_simple with SecretStr."""
        secret = SecretStr("https://example.com")
        assert FileStag.is_simple(secret) is False

        secret_local = SecretStr("/local/path")
        assert FileStag.is_simple(secret_local) is True

    def test_resolve_name_local(self):
        """Test resolve_name with local path."""
        result = FileStag.resolve_name("/path/to/file.txt")
        assert result == "/path/to/file.txt"

    def test_resolve_name_file_protocol(self):
        """Test resolve_name with file:// protocol."""
        result = FileStag.resolve_name("file:///path/to/file.txt")
        assert result == "/path/to/file.txt"

    def test_resolve_name_secret_str(self):
        """Test resolve_name with SecretStr."""
        secret = SecretStr("/secret/path")
        result = FileStag.resolve_name(secret)
        assert result == "/secret/path"

    def test_resolve_name_bytes(self):
        """Test resolve_name with bytes (should pass through)."""
        data = b"some data"
        result = FileStag.resolve_name(data)
        assert result == data

    def test_load_local_file(self, temp_dir):
        """Test loading a local file."""
        test_file = Path(temp_dir) / "test.txt"
        test_file.write_bytes(b"Hello, World!")

        result = FileStag.load(str(test_file))
        assert result == b"Hello, World!"

    def test_load_nonexistent_file(self, temp_dir):
        """Test loading non-existent file returns None."""
        result = FileStag.load(os.path.join(temp_dir, "nonexistent.txt"))
        assert result is None

    def test_load_bytes_passthrough(self):
        """Test loading bytes passes through."""
        data = b"Test data"
        result = FileStag.load(data)
        assert result == data

    def test_load_as_stream(self, temp_dir):
        """Test loading as BytesIO stream."""
        test_file = Path(temp_dir) / "stream.txt"
        test_file.write_bytes(b"Stream content")

        result = FileStag.load(str(test_file), as_stream=True)
        assert isinstance(result, io.BytesIO)
        assert result.read() == b"Stream content"

    def test_load_from_zip(self, sample_zip):
        """Test loading from zip:// protocol."""
        identifier = f"zip://{sample_zip}/file0.txt"
        result = FileStag.load(identifier)
        assert result is not None
        assert b"Content 0" in result

    def test_save_local_file(self, temp_dir):
        """Test saving a local file."""
        test_file = Path(temp_dir) / "output.txt"
        result = FileStag.save(str(test_file), b"Saved content")

        assert result is True
        assert test_file.read_bytes() == b"Saved content"

    def test_save_none_raises(self, temp_dir):
        """Test saving None raises ValueError."""
        test_file = Path(temp_dir) / "none.txt"
        with pytest.raises(ValueError, match="No data"):
            FileStag.save(str(test_file), None)

    def test_save_to_nonexistent_dir(self, temp_dir):
        """Test saving to non-existent directory fails."""
        test_file = Path(temp_dir) / "nonexistent" / "output.txt"
        result = FileStag.save(str(test_file), b"data")
        assert result is False

    def test_save_non_simple_raises(self):
        """Test saving to non-simple target raises."""
        with pytest.raises(NotImplementedError):
            FileStag.save("https://example.com/file.txt", b"data")

    def test_delete_file(self, temp_dir):
        """Test deleting a file."""
        test_file = Path(temp_dir) / "to_delete.txt"
        test_file.write_bytes(b"delete me")

        result = FileStag.delete(str(test_file))
        assert result is True
        assert not test_file.exists()

    def test_delete_nonexistent(self, temp_dir):
        """Test deleting non-existent file returns False."""
        result = FileStag.delete(os.path.join(temp_dir, "nonexistent.txt"))
        assert result is False

    def test_delete_non_simple_raises(self):
        """Test deleting non-simple target raises."""
        with pytest.raises(NotImplementedError):
            FileStag.delete("https://example.com/file.txt")

    def test_load_text(self, temp_dir):
        """Test loading text file."""
        test_file = Path(temp_dir) / "text.txt"
        test_file.write_text("Hello, text!", encoding="utf-8")

        result = FileStag.load_text(str(test_file))
        assert result == "Hello, text!"

    def test_load_text_nonexistent(self, temp_dir):
        """Test loading non-existent text file returns None."""
        result = FileStag.load_text(os.path.join(temp_dir, "nonexistent.txt"))
        assert result is None

    def test_load_text_crlf_to_lf(self, temp_dir):
        """Test converting CRLF to LF."""
        test_file = Path(temp_dir) / "crlf.txt"
        test_file.write_bytes(b"line1\r\nline2\r\n")

        result = FileStag.load_text(str(test_file), crlf=False)
        assert result == "line1\nline2\n"

    def test_load_text_lf_to_crlf(self, temp_dir):
        """Test converting LF to CRLF."""
        test_file = Path(temp_dir) / "lf.txt"
        test_file.write_bytes(b"line1\nline2\n")

        result = FileStag.load_text(str(test_file), crlf=True)
        assert result == "line1\r\nline2\r\n"

    def test_load_text_keep_original(self, temp_dir):
        """Test keeping original line endings."""
        test_file = Path(temp_dir) / "original.txt"
        test_file.write_bytes(b"line1\r\nline2\n")

        result = FileStag.load_text(str(test_file), crlf=None)
        assert result == "line1\r\nline2\n"

    def test_save_text(self, temp_dir):
        """Test saving text file."""
        test_file = Path(temp_dir) / "save_text.txt"

        result = FileStag.save_text(str(test_file), "Hello, saved!")
        assert result is True
        assert test_file.read_text(encoding="utf-8") == "Hello, saved!"

    def test_save_text_none_raises(self, temp_dir):
        """Test saving None text raises ValueError."""
        test_file = Path(temp_dir) / "none.txt"
        with pytest.raises(ValueError, match="No data"):
            FileStag.save_text(str(test_file), None)

    def test_load_json(self, temp_dir):
        """Test loading JSON file."""
        test_file = Path(temp_dir) / "data.json"
        test_file.write_text('{"key": "value", "num": 42}', encoding="utf-8")

        result = FileStag.load_json(str(test_file))
        assert result == {"key": "value", "num": 42}

    def test_load_json_nonexistent(self, temp_dir):
        """Test loading non-existent JSON returns None."""
        result = FileStag.load_json(os.path.join(temp_dir, "nonexistent.json"))
        assert result is None

    def test_save_json(self, temp_dir):
        """Test saving JSON file."""
        test_file = Path(temp_dir) / "output.json"
        data = {"name": "test", "values": [1, 2, 3]}

        result = FileStag.save_json(str(test_file), data)
        assert result is True

        loaded = json.loads(test_file.read_text(encoding="utf-8"))
        assert loaded == data

    def test_save_json_with_indent(self, temp_dir):
        """Test saving JSON with indentation."""
        test_file = Path(temp_dir) / "indented.json"
        data = {"key": "value"}

        result = FileStag.save_json(str(test_file), data, indent=2)
        assert result is True

        content = test_file.read_text(encoding="utf-8")
        assert "\n" in content  # Should be formatted

    def test_save_json_none_raises(self, temp_dir):
        """Test saving None JSON raises ValueError."""
        test_file = Path(temp_dir) / "none.json"
        with pytest.raises(ValueError, match="No data"):
            FileStag.save_json(str(test_file), None)

    def test_copy_local(self, temp_dir):
        """Test copying local file."""
        source = Path(temp_dir) / "source.txt"
        target = Path(temp_dir) / "target.txt"
        source.write_bytes(b"Copy me")

        result = FileStag.copy(str(source), str(target))
        assert result is True
        assert target.read_bytes() == b"Copy me"

    def test_copy_to_nonexistent_dir_without_create(self, temp_dir):
        """Test copying to non-existent directory fails without create_dir."""
        source = Path(temp_dir) / "source.txt"
        target = Path(temp_dir) / "subdir" / "target.txt"
        source.write_bytes(b"data")

        result = FileStag.copy(str(source), str(target), create_dir=False)
        assert result is False

    def test_copy_to_nonexistent_dir_with_create(self, temp_dir):
        """Test copying to non-existent directory succeeds with create_dir."""
        source = Path(temp_dir) / "source.txt"
        target = Path(temp_dir) / "new_subdir" / "target.txt"
        source.write_bytes(b"data")

        result = FileStag.copy(str(source), str(target), create_dir=True)
        assert result is True
        assert target.read_bytes() == b"data"

    def test_copy_nonexistent_source(self, temp_dir):
        """Test copying non-existent source fails."""
        target = Path(temp_dir) / "target.txt"

        result = FileStag.copy(
            os.path.join(temp_dir, "nonexistent.txt"), str(target)
        )
        assert result is False

    def test_exists_local(self, temp_dir):
        """Test exists with local file."""
        test_file = Path(temp_dir) / "exists.txt"
        test_file.write_bytes(b"data")

        assert FileStag.exists(str(test_file)) is True
        assert FileStag.exists(os.path.join(temp_dir, "nonexistent.txt")) is False

    def test_exists_zip(self, sample_zip):
        """Test exists with zip:// protocol."""
        assert FileStag.exists(f"zip://{sample_zip}/file0.txt") is True
        assert FileStag.exists(f"zip://{sample_zip}/nonexistent.txt") is False

    def test_load_file_protocol(self, temp_dir):
        """Test loading with file:// protocol."""
        test_file = Path(temp_dir) / "file_proto.txt"
        test_file.write_bytes(b"file protocol content")

        result = FileStag.load(f"file://{test_file}")
        assert result == b"file protocol content"

    def test_save_file_protocol(self, temp_dir):
        """Test saving with file:// protocol."""
        test_file = Path(temp_dir) / "file_proto_save.txt"

        result = FileStag.save(f"file://{test_file}", b"saved via protocol")
        assert result is True
        assert test_file.read_bytes() == b"saved via protocol"
