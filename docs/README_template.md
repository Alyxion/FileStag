# FileStag

[![PyPI version](https://img.shields.io/pypi/v/filestag.svg)](https://pypi.org/project/filestag/)
[![Python Versions](https://img.shields.io/badge/python-{{PYTHON_VERSION}}+-blue.svg)](https://pypi.org/project/filestag/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)]({{GITHUB_PREFIX}}LICENSE)
[![Code style: ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

**FileStag** is a high-performance, unified file access library for Python. It provides a consistent API for reading, writing, and managing files across different storage backends—including the local filesystem, ZIP archives, HTTP/HTTPS URLs, and Azure Blob Storage.

Extracted from the [SciStag](https://github.com/scistag/scistag) framework, FileStag is designed to be lightweight, efficient, and developer-friendly.

## Key Features

*   **Unified API**: Use the same `load`, `save`, and `copy` methods regardless of the underlying storage.
*   **Protocol Support**:
    *   `file://` (Local filesystem)
    *   `zip://` (Direct access to files inside ZIP archives)
    *   `http://` & `https://` (Web fetching with built-in caching)
    *   `azure://` (Azure Blob Storage support)
*   **Smart Caching**: Built-in web caching to speed up repeated remote file access.
*   **Async Support**: Full `async`/`await` support for high-concurrency applications.
*   **Developer Friendly**: Type-hinted, intuitive methods for text, JSON, and binary data.

## Installation

Install FileStag via pip or poetry:

```bash
# Standard installation
pip install filestag

# With Azure Blob Storage support
pip install "filestag[azure]"
```

Using Poetry:

```bash
poetry add filestag
# or
poetry add filestag -E azure
```

## Quick Start

### Basic File Operations

FileStag makes file I/O simple and consistent.

```python
from filestag import FileStag

# Save text to a local file
FileStag.save_text("hello.txt", "Hello World!")

# Load it back
content = FileStag.load_text("hello.txt")
print(content)  # "Hello World!"

# Check if it exists
if FileStag.exists("hello.txt"):
    print("File exists!")
```

### JSON Handling

Read and write JSON with zero boilerplate.

```python
data = {"name": "FileStag", "version": "{{VERSION}}"}

# Save dictionary as JSON
FileStag.save_json("config.json", data, indent=4)

# Load JSON back into a dict
config = FileStag.load_json("config.json")
print(config["name"])
```

### Working with ZIP Archives

Access files directly inside ZIP archives without manual extraction.

```python
# Read a file directly from a ZIP archive
content = FileStag.load_text("zip://my_archive.zip/data/readme.txt")

# Check existence inside ZIP
if FileStag.exists("zip://my_archive.zip/images/logo.png"):
    print("Logo found in archive")
```

### Web Fetching & Caching

Download files from the web easily. Enable caching to prevent redundant network requests during development or analysis.

```python
# Fetch a file from the web
data = FileStag.load("https://example.com/data.csv")

# Fetch with caching (cached for 1 hour)
# If the file was downloaded recently, it loads from disk instead.
data = FileStag.load(
    "https://example.com/large_dataset.csv",
    max_cache_age=3600
)
```

### Async Support

Building a modern async application? FileStag has you covered.

```python
import asyncio
from filestag import FileStag

async def main():
    # Async load
    text = await FileStag.load_text_async("data.txt")

    # Async save
    await FileStag.save_text_async("output.txt", "Processed data")

    # Async web fetch
    data = await FileStag.load_async("https://api.example.com/data.json")

asyncio.run(main())
```

### Azure Blob Storage

(Requires `filestag[azure]` install)

Access Azure Blob Storage using connection strings or SAS URLs directly in the path.

```python
from filestag import FileSource, FileSink

# Using a connection string with container and path
conn_string = (
    "azure://DefaultEndpointsProtocol=https;"
    "AccountName=myaccount;AccountKey=mykey...;"
    "EndpointSuffix=core.windows.net/mycontainer/data"
)

# Iterate files from Azure
source = FileSource.from_source(conn_string)
for file in source:
    print(f"{file.filename}: {len(file.data)} bytes")

# Upload files to Azure
sink = FileSink.with_target(conn_string)
sink.store("output.json", b'{"result": "success"}')

# Using a SAS URL (read-only access via shared link)
sas_url = "https://myaccount.blob.core.windows.net/container?sp=r&sig=..."
source = FileSource.from_source(sas_url, search_path="data/")
print(f"Found {len(source.file_list)} files")
```

#### Local File List Caching

When working with Azure containers containing thousands of files, listing operations can be slow. FileStag can cache the file list locally for instant access on subsequent runs:

```python
# Cache the file list locally - huge speedup for large containers!
source = FileSource.from_source(
    conn_string,
    file_list_name="my_azure_cache.json",
)

# First run: fetches file list from Azure (may take seconds for 10k+ files)
# Subsequent runs: loads instantly from local cache file
print(f"Found {len(source.file_list)} files")

# Invalidate cache by bumping the version number:
source = FileSource.from_source(
    conn_string,
    file_list_name=("my_azure_cache.json", 2),  # Change 2 -> 3 to invalidate
)

# Or force refresh programmatically (re-fetches and updates cache):
source.refresh()

# Automatic cache validation - checks if Azure has newer files:
source = FileSource.from_source(
    conn_string,
    file_list_name="my_azure_cache.json",
    validate_cache=True,  # Auto-refreshes if files changed on Azure
)
```

#### Environment Variable Placeholders

Keep credentials out of your code using `{{env.VAR}}` syntax:

```python
# Credentials are substituted from environment variables
conn = "azure://...AccountName={{env.AZURE_ACCOUNT}};AccountKey={{env.AZURE_KEY}}..."
source = FileSource.from_source(conn + "/mycontainer")
```

## Contributing

Contributions are welcome!

1.  Clone the repository
2.  Install dependencies: `poetry install`
3.  Run tests: `poetry run pytest`
4.  Check types: `poetry run mypy filestag`

## License

This project is licensed under the MIT License - see the [LICENSE]({{GITHUB_PREFIX}}LICENSE) file for details.
