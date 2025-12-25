"""
Azure Blob Storage support for FileStag.

This module provides FileSource and FileSink implementations for Azure Blob Storage.
Requires the optional `azure` dependency: `pip install filestag[azure]`
"""

from .blob_path import AzureBlobPath
from .source import AzureStorageFileSource
from .sink import AzureStorageFileSink

__all__ = ["AzureBlobPath", "AzureStorageFileSource", "AzureStorageFileSink"]
