"""
Azure Blob Storage support for FileStag.

This module provides FileSource and FileSink implementations for Azure Blob Storage.
Requires the optional `azure` dependency: `pip install filestag[azure]`

Includes both sync and async implementations:
- AzureStorageFileSource / AsyncAzureStorageFileSource
- AzureStorageFileSink / AsyncAzureStorageFileSink
"""

from .blob_path import AzureBlobPath
from .source import AzureStorageFileSource
from .sink import AzureStorageFileSink
from .async_source import AsyncAzureStorageFileSource
from .async_sink import AsyncAzureStorageFileSink

__all__ = [
    "AzureBlobPath",
    "AzureStorageFileSource",
    "AzureStorageFileSink",
    "AsyncAzureStorageFileSource",
    "AsyncAzureStorageFileSink",
]
