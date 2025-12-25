"""
FileStag - Fast local and cloud-based file access and storage.

This library provides a unified interface for reading and writing files from
various sources including local disk, ZIP archives, HTTP URLs, and Azure Blob Storage.

Basic usage:

    from filestag import FileStag

    # Read a file
    data = FileStag.load("path/to/file.txt")

    # Write a file
    FileStag.save("path/to/output.txt", data)

    # Load from URL
    data = FileStag.load("https://example.com/file.txt")

    # Load from ZIP
    data = FileStag.load("zip://archive.zip/file.txt")

For Azure Blob Storage support, install with: pip install filestag[azure]
"""

from filestag._version import __version__
from filestag.file_stag import FileStag
from filestag.file_source import FileSource, FileListEntry, FileSourcePathOptions
from filestag.file_sink import FileSink, FileStorageOptions
from filestag.file_source_iterator import FileSourceIterator, FilterCallback
from filestag.file_path import FilePath
from filestag.memory_zip import MemoryZip
from filestag.shared_archive import SharedArchive
from filestag.protocols import (
    AZURE_PROTOCOL_HEADER,
    AZURE_DEFAULT_ENDPOINTS_HEADER,
    AZURE_SAS_URL_COMPONENT,
    ZIP_SOURCE_PROTOCOL,
    is_azure_storage_source,
)

# Web submodule
from filestag.web import WebCache, web_fetch, web_fetch_async

# Cache submodule
from filestag.cache import Cache, CacheRef, DiskCache, get_global_cache

# Source implementations
from filestag.sources import FileSourceDisk, FileSourceZip

# Sink implementations
from filestag.sinks import FileSinkDisk, FileSinkZip, ArchiveFileSinkProto

__all__ = [
    # Version
    "__version__",
    # Core classes
    "FileStag",
    "FileSource",
    "FileSink",
    "FileListEntry",
    "FileSourceIterator",
    "FilterCallback",
    "FileSourcePathOptions",
    "FileStorageOptions",
    # Utilities
    "FilePath",
    "MemoryZip",
    "SharedArchive",
    # Protocols
    "AZURE_PROTOCOL_HEADER",
    "AZURE_DEFAULT_ENDPOINTS_HEADER",
    "AZURE_SAS_URL_COMPONENT",
    "ZIP_SOURCE_PROTOCOL",
    "is_azure_storage_source",
    # Web
    "WebCache",
    "web_fetch",
    "web_fetch_async",
    # Cache
    "Cache",
    "CacheRef",
    "DiskCache",
    "get_global_cache",
    # Sources
    "FileSourceDisk",
    "FileSourceZip",
    # Sinks
    "FileSinkDisk",
    "FileSinkZip",
    "ArchiveFileSinkProto",
]


def __getattr__(name: str):
    """Lazy loading for Azure modules (optional dependency)."""
    if name in ("AzureBlobPath", "AzureStorageFileSource", "AzureStorageFileSink"):
        try:
            from filestag import azure

            return getattr(azure, name)
        except ImportError as e:
            raise ImportError(
                f"{name} requires the 'azure' extra. "
                f"Install with: pip install filestag[azure]"
            ) from e
    raise AttributeError(f"module 'filestag' has no attribute '{name}'")
