# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

FileStag is a standalone Python library for fast local and cloud-based file access and storage. It provides a unified interface for reading and writing files from various sources including local disk, ZIP archives, HTTP URLs, and Azure Blob Storage.

Extracted from SciStag as a standalone library with no SciStag dependency.

## Architecture

```
filestag/
├── __init__.py              # Public API exports with lazy Azure loading
├── _version.py              # Version string
├── _lock.py                 # StagLock (thread safety)
├── _env.py                  # Environment variable utilities
├── _iter.py                 # Iterator utilities
├── protocols.py             # Protocol constants (azure://, zip://)
├── file_path.py             # FilePath utilities
├── file_stag.py             # High-level FileStag API
├── file_source.py           # FileSource base class
├── file_source_iterator.py  # Iterator implementation
├── file_sink.py             # FileSink base class
├── memory_zip.py            # MemoryZip helper
├── shared_archive.py        # zip:// protocol support
├── web/
│   ├── __init__.py
│   ├── fetch.py             # web_fetch function
│   └── web_cache.py         # WebCache class
├── sources/
│   ├── __init__.py
│   ├── disk.py              # FileSourceDisk
│   └── zip.py               # FileSourceZip
├── sinks/
│   ├── __init__.py
│   ├── disk.py              # FileSinkDisk
│   ├── zip.py               # FileSinkZip
│   └── archive.py           # ArchiveFileSinkProto
├── azure/                   # Optional dependency
│   ├── __init__.py
│   ├── blob_path.py         # AzureBlobPath
│   ├── source.py            # AzureStorageFileSource
│   ├── sink.py              # AzureStorageFileSink
│   ├── async_source.py      # AsyncAzureStorageFileSource
│   └── async_sink.py        # AsyncAzureStorageFileSink
└── cache/
    ├── __init__.py
    ├── cache.py             # Cache class
    ├── cache_ref.py         # CacheRef
    ├── disk_cache.py        # DiskCache
    └── _bundle.py           # JSON-based serialization
```

## Key Classes

- **FileStag**: High-level API for load/save/copy/delete operations
- **FileSource**: Base class for reading files, supports iteration
- **FileSink**: Base class for writing files
- **AsyncAzureStorageFileSource**: Async Azure blob source (uses `azure.storage.blob.aio`)
- **AsyncAzureStorageFileSink**: Async Azure blob sink (uses `azure.storage.blob.aio`)
- **Cache/DiskCache**: Caching utilities with versioning support
- **WebCache**: HTTP file caching with TTL

## Development Setup

```bash
# Install with Poetry
poetry install

# Install with Azure support
poetry install -E azure

# Or with pip
pip install -e .
pip install -e ".[azure]"
pip install -e ".[dev]"
```

## Common Commands

```bash
# Run tests
poetry run pytest

# Type checking
poetry run mypy filestag

# Linting
poetry run ruff check filestag

# Format code
poetry run ruff format filestag
```

## Protocol Support

- `file://` or plain paths - Local filesystem
- `zip://path/to/archive.zip/file.txt` - ZIP archive access
- `http://` / `https://` - Web fetching with caching
- `azure://DefaultEndpoints.../container/path` - Azure Blob Storage (optional)

## Dependencies

Core:
- pydantic (>=2.0.0) - Data validation
- requests (>=2.28.0) - HTTP requests

Optional (azure):
- azure-storage-blob (>=12.0.0) - Azure Blob Storage support
- aiohttp (>=3.8.0) - Required for async Azure operations

Dev:
- pytest, mypy, ruff

## Git Commit Rules

**Do NOT include any of the following in commit messages:**
- `Co-Authored-By` lines
- `Generated with [Claude Code]` or similar attribution
- Any reference to Claude or AI assistance

Commit messages should be clean and appear as if written by the repository owner.

## License

MIT License
