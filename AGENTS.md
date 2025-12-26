# FileStag - Project Rules

Rules for AI agents working on this repository.

---

## Project Overview

FileStag is a standalone Python library for fast local and cloud-based file access and storage. It provides a unified interface for reading and writing files from various sources including local disk, ZIP archives, HTTP URLs, and Azure Blob Storage.

**Package**: https://pypi.org/project/filestag/

## File Organization

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
│   ├── source.py            # AzureStorageFileSource (sync)
│   ├── sink.py              # AzureStorageFileSink (sync)
│   ├── async_source.py      # AsyncAzureStorageFileSource
│   └── async_sink.py        # AsyncAzureStorageFileSink
└── cache/
    ├── __init__.py
    ├── cache.py             # Cache class
    ├── cache_ref.py         # CacheRef
    ├── disk_cache.py        # DiskCache
    └── _bundle.py           # JSON-based serialization

scripts/
├── build.sh                 # Build wheel (--full rebuilds README)
├── build_readme.py          # Generate README.md from template
├── test_wheel.sh            # Test wheel in isolated venv
└── deploy_pypi.sh           # Deploy to PyPI (--test for TestPyPI)

docs/
└── README_template.md       # Source for README.md generation

tests/
├── conftest.py              # Fixtures, loads .env for Azure tests
└── test_*.py                # Test modules
```

**Generated files (DO NOT EDIT directly):**
- `README.md` - generated from `docs/README_template.md` via `scripts/build_readme.py`
- `README_PYPI.md` - generated from template via `scripts/build_readme.py`

## Key Classes

- **FileStag**: High-level API for load/save/copy/delete operations
- **FileSource**: Base class for reading files, supports iteration
- **FileSink**: Base class for writing files
- **AzureStorageFileSource/Sink**: Sync Azure blob access
- **AsyncAzureStorageFileSource/Sink**: Async Azure blob access (uses `azure.storage.blob.aio`)
- **Cache/DiskCache**: Caching utilities with versioning support
- **WebCache**: HTTP file caching with TTL

## Protocol Support

- `file://` or plain paths - Local filesystem
- `zip://path/to/archive.zip/file.txt` - ZIP archive access
- `http://` / `https://` - Web fetching with caching
- `azure://DefaultEndpoints.../container/path` - Azure Blob Storage (optional)

## Environment

This project uses Poetry for dependency management.

### Development Setup

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
# Run tests (do NOT pipe output - we need to see results)
poetry run pytest -v

# Run tests with coverage
poetry run pytest --cov=filestag --cov-report=term-missing

# Type checking
poetry run mypy filestag

# Linting
poetry run ruff check filestag

# Format code
poetry run ruff format filestag
```

## Testing

### Azure Tests

Azure tests require credentials in `.env` file (gitignored):

```
AZ_TEST_SOURCE_ACCOUNT_NAME=your_account
AZ_TEST_SOURCE_KEY=your_key
```

Tests use `{{env.VAR}}` syntax for connection strings - credentials are substituted at runtime.

### Test Coverage

- Minimum 90% coverage required (excluding `filestag/azure/*`)
- Azure tests run against real Azure storage and clean up after themselves
- Async tests use `pytest-asyncio` with `asyncio_mode = "auto"`

## Build and Deploy Workflow

```bash
# 1. Run tests
poetry run pytest -v

# 2. Build the wheel
./scripts/build.sh              # Quick build
./scripts/build.sh --full       # Rebuild README first

# 3. Test the wheel in isolated environment
./scripts/test_wheel.sh

# 4. Deploy to PyPI
./scripts/deploy_pypi.sh        # Production
./scripts/deploy_pypi.sh --test # TestPyPI first (recommended)
```

### What the Scripts Do

- **`build.sh`** - Cleans dist/, builds wheel with `poetry build`
- **`build.sh --full`** - Also rebuilds README.md from template
- **`test_wheel.sh`** - Creates temp venv, installs wheel, runs smoke tests
- **`deploy_pypi.sh`** - Tests wheel then publishes to PyPI
- **`deploy_pypi.sh --test`** - Publishes to TestPyPI first

## Dependencies

### Core (always installed)

- pydantic>=2.0 - Data validation
- requests>=2.28 - HTTP requests
- aiofiles>=23.0 - Async file operations
- httpx>=0.24 - Async HTTP client

### Optional (azure extra)

- azure-storage-blob>=12.0 - Azure Blob Storage
- aiohttp>=3.8 - Required for async Azure operations

### Dev

- pytest, pytest-cov, pytest-asyncio
- mypy, ruff
- python-dotenv (for loading .env in tests)

## pyproject.toml Guidelines

When updating dependencies:

1. **Use flexible version constraints** (`>=X.Y`, not `^X.Y.Z`)
2. **No upper bounds** unless absolutely necessary - allows future compatibility
3. **Include future Python versions** in classifiers (3.12, 3.13, 3.14)
4. **Add keywords** for discoverability
5. **Include project URLs** (Homepage, Repository, Issues)

## Git Commit Rules

**Do NOT include any of the following in commit messages:**
- `Co-Authored-By` lines
- `Generated with [Claude Code]` or similar attribution
- Any reference to Claude or AI assistance

Commit messages should be clean and appear as if written by the repository owner.

## Code Conventions

### Async Pattern for Azure

```python
from filestag.azure import AsyncAzureStorageFileSource, AsyncAzureStorageFileSink

# Always use async context manager
async with AsyncAzureStorageFileSource("azure://...") as source:
    async for entry in source:
        data = await source.read_file(entry.filename)

async with AsyncAzureStorageFileSink("azure://...") as sink:
    await sink.store("file.txt", b"content")
```

### File List Caching (Azure)

```python
# Cache file list locally for large containers
source = FileSource.from_source(
    conn_string,
    file_list_name="cache.json",        # Local cache file
    validate_cache=True,                 # Auto-refresh if Azure changed
)

# Manual invalidation via version bump
file_list_name=("cache.json", 2)         # Change 2 → 3 to invalidate
```

### Environment Variable Substitution

Connection strings support `{{env.VAR}}` syntax:

```python
conn = "azure://...AccountName={{env.AZURE_ACCOUNT}};AccountKey={{env.AZURE_KEY}}..."
```

## Security

- **Never commit credentials** - use `.env` files (gitignored)
- **Use environment variable placeholders** in connection strings
- **Azure tests clean up** - all test files are deleted after test runs

## License

MIT License
