"""Shared fixtures for FileStag tests."""

import os
import tempfile
import shutil
import zipfile
from pathlib import Path

import pytest
from dotenv import load_dotenv

# Load environment variables from .env file before any tests run
load_dotenv()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for tests."""
    tmpdir = tempfile.mkdtemp()
    yield tmpdir
    shutil.rmtree(tmpdir, ignore_errors=True)


@pytest.fixture
def sample_files(temp_dir):
    """Create sample files in a temporary directory."""
    # Create text files
    for i in range(3):
        path = Path(temp_dir) / f"file{i}.txt"
        path.write_text(f"Content {i}")

    # Create a subdirectory with files
    subdir = Path(temp_dir) / "subdir"
    subdir.mkdir()
    (subdir / "nested.txt").write_text("Nested content")
    (subdir / "data.json").write_text('{"key": "value"}')

    return temp_dir


@pytest.fixture
def sample_zip(temp_dir, sample_files):
    """Create a sample ZIP file."""
    zip_path = Path(temp_dir) / "archive.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        for root, _, files in os.walk(sample_files):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, sample_files)
                zf.write(file_path, arcname)
    return str(zip_path)


@pytest.fixture
def empty_zip(temp_dir):
    """Create an empty ZIP file."""
    zip_path = Path(temp_dir) / "empty.zip"
    with zipfile.ZipFile(zip_path, "w"):
        pass
    return str(zip_path)
