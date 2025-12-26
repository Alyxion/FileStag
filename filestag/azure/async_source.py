"""
Implements the :class:`AsyncAzureStorageFileSource` class which allows
async iteration of files stored in an Azure Blob Storage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

from filestag.azure.blob_path import AzureBlobPath
from filestag.file_source import FileListEntry
from filestag.protocols import is_azure_storage_source

if TYPE_CHECKING:
    from azure.storage.blob.aio import BlobServiceClient, ContainerClient


class AsyncAzureStorageFileSource:
    """
    Async FileSource implementation for processing files stored in Azure Blob Storage.

    Provides async iteration over files in an Azure container.

    Example usage::

        async with AsyncAzureStorageFileSource("azure://...") as source:
            async for entry in source:
                data = await source.read_file(entry.filename)
                print(f"{entry.filename}: {len(data)} bytes")
    """

    def __init__(
        self,
        source: str,
        search_path: str = "",
        mask: str | None = None,
        tag_filter: str | None = None,
        timeout: int = 30,
        max_file_count: int = -1,
    ):
        """
        Initialize the async Azure file source.

        :param source: The source data definition:
            ``azure://CONNECTION_STRING/container_name`` or
            ``azure://CONNECTION_STRING/container_name/searchPath``
        :param search_path: Additional search path prefix within the container
        :param mask: File mask for filtering (e.g., "*.png")
        :param tag_filter: Tag filter expression for Azure blob tags
        :param timeout: Connection timeout in seconds
        :param max_file_count: Maximum number of files to return (-1 for unlimited)
        """
        if not is_azure_storage_source(source):
            raise ValueError(
                "source has to be an SAS URL or connection string, in the form "
                "azure://DefaultEndpoints... or DefaultEndpoints..."
            )

        self.blob_path = AzureBlobPath.from_string(source)
        self.timeout = timeout
        self.mask = mask
        self.max_file_count = max_file_count
        self.tag_filter_expression = (
            tag_filter if tag_filter is not None and len(tag_filter) > 0 else None
        )

        if not self.blob_path.container_name and self.blob_path.sas_url is None:
            raise ValueError("Container name or SAS URL required")

        # Combine blob_path's blob_name with additional search_path
        combined_path = self.blob_path.blob_name + search_path
        self.search_path = combined_path + "/" if combined_path else ""

        self._service_client: "BlobServiceClient | None" = None
        self._container_client: "ContainerClient | None" = None
        self._owns_clients = False

    async def __aenter__(self) -> "AsyncAzureStorageFileSource":
        """Async context manager entry - initializes Azure clients."""
        await self._connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - closes Azure clients."""
        await self.close()

    async def _connect(self) -> None:
        """Establish connection to Azure Blob Storage."""
        if self._container_client is not None:
            return

        if self.blob_path.is_sas():
            from azure.storage.blob.aio import ContainerClient

            self._container_client = ContainerClient.from_container_url(
                self.blob_path.get_connection_string()
            )
            self._service_client = None
        else:
            from azure.storage.blob.aio import BlobServiceClient

            self._service_client = BlobServiceClient.from_connection_string(
                self.blob_path.get_connection_string()
            )
            self._container_client = self._service_client.get_container_client(
                self.blob_path.container_name
            )
        self._owns_clients = True

    async def close(self) -> None:
        """Close the Azure clients and release resources."""
        if self._owns_clients:
            if self._container_client is not None:
                await self._container_client.close()
            if self._service_client is not None:
                await self._service_client.close()
        self._container_client = None
        self._service_client = None
        self._owns_clients = False

    @property
    def container_client(self) -> "ContainerClient":
        """Get the container client, raising if not connected."""
        if self._container_client is None:
            raise RuntimeError(
                "Not connected. Use 'async with' or call '_connect()' first."
            )
        return self._container_client

    def _matches_mask(self, filename: str) -> bool:
        """Check if filename matches the configured mask."""
        if self.mask is None:
            return True
        import fnmatch

        return fnmatch.fnmatch(filename, self.mask)

    async def __aiter__(self) -> AsyncIterator[FileListEntry]:
        """Async iterate over files in the Azure container."""
        count = 0
        spl = len(self.search_path)

        if self.tag_filter_expression is not None:
            # Filter by tags
            async for blob in self.container_client.find_blobs_by_tags(
                filter_expression=self.tag_filter_expression,
                timeout=self.timeout,
            ):
                name = blob["name"]
                if not name.startswith(self.search_path):
                    continue
                filename = name[spl:]
                if not self._matches_mask(filename):
                    continue

                yield FileListEntry(filename=filename)
                count += 1
                if self.max_file_count != -1 and count >= self.max_file_count:
                    break
        else:
            # List blobs normally
            async for blob in self.container_client.list_blobs(
                name_starts_with=self.search_path,
                timeout=self.timeout,
            ):
                filename = blob.name[spl:]
                if not self._matches_mask(filename):
                    continue

                yield FileListEntry(
                    filename=filename,
                    file_size=blob.size,
                    modified=blob.last_modified,
                    created=blob.creation_time,
                )
                count += 1
                if self.max_file_count != -1 and count >= self.max_file_count:
                    break

    async def read_file(self, filename: str) -> bytes | None:
        """
        Read a file from Azure Blob Storage.

        :param filename: The filename relative to the search path
        :return: The file contents as bytes, or None if not found
        """
        from azure.core.exceptions import ResourceNotFoundError

        if not self._matches_mask(filename):
            return None

        try:
            blob_client = self.container_client.get_blob_client(
                self.search_path + filename
            )
            stream = await blob_client.download_blob()
            return await stream.readall()
        except ResourceNotFoundError:
            return None

    async def exists(self, filename: str) -> bool:
        """
        Check if a file exists in Azure Blob Storage.

        :param filename: The filename relative to the search path
        :return: True if the file exists
        """
        blob_client = self.container_client.get_blob_client(
            self.search_path + filename
        )
        return await blob_client.exists()

    async def get_file_list(self) -> list[FileListEntry]:
        """
        Get a list of all files matching the criteria.

        :return: List of FileListEntry objects
        """
        entries = []
        async for entry in self:
            entries.append(entry)
        return entries

    async def get_latest_modified_timestamp(self) -> str | None:
        """
        Get the latest modification timestamp from Azure.

        :return: ISO format timestamp of the most recently modified file,
            or None if no files exist or an error occurs.
        """
        try:
            latest = None
            async for blob in self.container_client.list_blobs(
                name_starts_with=self.search_path,
                timeout=self.timeout,
            ):
                if latest is None or blob.last_modified > latest:
                    latest = blob.last_modified

            return latest.isoformat() if latest else None
        except Exception:
            return None
