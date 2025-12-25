"""Tests for file_path module."""

import os
import tempfile
from pathlib import Path

import pytest

from filestag.file_path import FilePath


class TestFilePath:
    """Tests for FilePath class."""

    def test_dirname_basic(self):
        """Test dirname with basic path."""
        result = FilePath.dirname("/path/to/file.txt")
        assert result == "/path/to"

    def test_dirname_with_slash(self):
        """Test dirname with slash normalization."""
        # On all platforms, should normalize to forward slashes
        result = FilePath.dirname("/path/to/file.txt", slash=True)
        assert "\\" not in result

    def test_dirname_without_slash(self):
        """Test dirname without slash normalization."""
        result = FilePath.dirname("/path/to/file.txt", slash=False)
        assert result == os.path.dirname("/path/to/file.txt")

    def test_norm_path_basic(self):
        """Test norm_path with relative components."""
        result = FilePath.norm_path("/path/to/../file.txt")
        assert ".." not in result

    def test_norm_path_with_dots(self):
        """Test norm_path with current directory dots."""
        result = FilePath.norm_path("/path/./to/./file.txt")
        assert "/." not in result or result.endswith("/.")

    def test_norm_path_slash(self):
        """Test norm_path normalizes to forward slashes."""
        result = FilePath.norm_path("/path/to/file.txt", slash=True)
        assert "\\" not in result

    def test_exists_true(self, temp_dir):
        """Test exists with existing path."""
        test_file = Path(temp_dir) / "exists.txt"
        test_file.write_text("test")
        assert FilePath.exists(str(test_file)) is True

    def test_exists_false(self, temp_dir):
        """Test exists with non-existing path."""
        test_file = Path(temp_dir) / "nonexistent.txt"
        assert FilePath.exists(str(test_file)) is False

    def test_basename(self):
        """Test basename extraction."""
        assert FilePath.basename("/path/to/file.txt") == "file.txt"

    def test_basename_directory(self):
        """Test basename with directory path."""
        assert FilePath.basename("/path/to/dir/") == ""
        assert FilePath.basename("/path/to/dir") == "dir"

    def test_script_filename(self):
        """Test script_filename returns this test file."""
        filename = FilePath.script_filename()
        assert filename.endswith("test_file_path.py")

    def test_script_path(self):
        """Test script_path returns directory of this test file."""
        path = FilePath.script_path()
        assert "tests" in path or "test" in path

    def test_absolute_relative(self):
        """Test absolute with relative path."""
        result = FilePath.absolute(".")
        assert os.path.isabs(result)

    def test_absolute_already_absolute(self):
        """Test absolute with already absolute path."""
        abs_path = "/some/absolute/path"
        result = FilePath.absolute(abs_path)
        assert os.path.isabs(result)

    def test_absolute_comb(self, temp_dir):
        """Test absolute_comb combines paths correctly."""
        result = FilePath.absolute_comb("subdir/file.txt", temp_dir)
        assert temp_dir.replace("\\", "/") in result
        assert "subdir/file.txt" in result

    def test_absolute_comb_no_base(self):
        """Test absolute_comb without base path uses caller's path."""
        result = FilePath.absolute_comb("somefile.txt")
        assert os.path.isabs(result.replace("/", os.sep))

    def test_split_ext(self):
        """Test split_ext with various extensions."""
        name, ext = FilePath.split_ext("/path/to/file.txt")
        assert name == "/path/to/file"
        assert ext == ".txt"

    def test_split_ext_no_extension(self):
        """Test split_ext with no extension."""
        name, ext = FilePath.split_ext("/path/to/file")
        assert name == "/path/to/file"
        assert ext == ""

    def test_split_ext_multiple_dots(self):
        """Test split_ext with multiple dots."""
        name, ext = FilePath.split_ext("/path/to/file.tar.gz")
        assert name == "/path/to/file.tar"
        assert ext == ".gz"

    def test_split_path_components(self):
        """Test split_path_components."""
        components = FilePath.split_path_components("/path/to/file.txt")
        assert "path" in components
        assert "to" in components
        assert "file.txt" in components

    def test_split_path_components_backslash(self):
        """Test split_path_components normalizes backslashes."""
        components = FilePath.split_path_components("path\\to\\file.txt")
        assert "path" in components
        assert "to" in components
        assert "file.txt" in components

    def test_make_dirs_new(self, temp_dir):
        """Test make_dirs creates new directory."""
        new_dir = os.path.join(temp_dir, "new", "nested", "dir")
        result = FilePath.make_dirs(new_dir, exist_ok=True)
        assert result is True
        assert os.path.isdir(new_dir)

    def test_make_dirs_existing_with_exist_ok(self, temp_dir):
        """Test make_dirs with existing directory and exist_ok=True."""
        result = FilePath.make_dirs(temp_dir, exist_ok=True)
        assert result is True

    def test_make_dirs_existing_without_exist_ok(self, temp_dir):
        """Test make_dirs with existing directory and exist_ok=False."""
        result = FilePath.make_dirs(temp_dir, exist_ok=False)
        assert result is False

    def test_sep_constant(self):
        """Test SEP constant matches OS separator."""
        assert FilePath.SEP == os.path.sep
