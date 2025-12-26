"""
Implements the :class:`AsyncAzureStorageFileSink` class which provides
async file uploads to Azure Blob Storage.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from filestag.azure.blob_path import AzureBlobPath
from filestag.protocols import (
    AZURE_PROTOCOL_HEADER,
    AZURE_DEFAULT_ENDPOINTS_HEADER,
)

if TYPE_CHECKING:
    from azure.storage.blob.aio import BlobServiceClient, ContainerClient


class AsyncAzureStorageFileSink:
    """
    Async helper class for storing files in Azure Blob Storage.

    Example usage::

        async with AsyncAzureStorageFileSink("azure://...") as sink:
            await sink.store("file.txt", b"Hello World")
            await sink.store("data.json", b'{"key": "value"}')
    """

    def __init__(
        self,
        target: str,
        create_container: bool = True,
        recreate_container: bool = False,
        sub_folder: str | None = None,
        delete_timeout_s: float = 60.0,
    ):
        """
        Initialize the async Azure file sink.

        :param target: A FileStag conform Azure Storage URL of the form
            azure://DefaultEndpoints.../ContainerName/SubFolder/ or
            azure://DefaultEndpoints.../ContainerName
        :param create_container: If True, create the container if it doesn't exist
        :param recreate_container: If True, delete and recreate the container
        :param sub_folder: Optional subfolder for all uploaded files
        :param delete_timeout_s: Timeout in seconds when recreating containers
        """
        if not target.startswith(AZURE_PROTOCOL_HEADER) and not target.startswith(
            AZURE_DEFAULT_ENDPOINTS_HEADER
        ):
            raise ValueError("Target has to be in the form azure://DefaultEndPoints...")

        self.blob_path = AzureBlobPath.from_string(target)

        if not self.blob_path.container_name:
            raise ValueError("Container name is required in the target URL")

        self.container_name = self.blob_path.container_name
        self.create_container = create_container
        self.recreate_container = recreate_container
        self.delete_timeout_s = delete_timeout_s

        # Determine sub_folder from blob_path or parameter
        if sub_folder is None:
            sub_folder = self.blob_path.blob_name
        if sub_folder and not sub_folder.endswith("/"):
            sub_folder += "/"
        self.sub_folder = sub_folder or ""

        self._service_client: "BlobServiceClient | None" = None
        self._container_client: "ContainerClient | None" = None
        self._owns_clients = False

    async def __aenter__(self) -> "AsyncAzureStorageFileSink":
        """Async context manager entry - initializes Azure clients."""
        await self._connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Async context manager exit - closes Azure clients."""
        await self.close()

    async def _connect(self) -> None:
        """Establish connection and setup container."""
        if self._container_client is not None:
            return

        from azure.storage.blob.aio import BlobServiceClient

        self._service_client = BlobServiceClient.from_connection_string(
            self.blob_path.get_connection_string()
        )

        self._container_client = await self._setup_container()
        self._owns_clients = True

    async def _setup_container(self) -> "ContainerClient":
        """Setup the container, creating or recreating as needed."""
        import asyncio
        from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError

        if self._service_client is None:
            raise RuntimeError("Service client not initialized")

        if not self.create_container:
            container = self._service_client.get_container_client(self.container_name)
            if not await container.exists():
                raise ValueError(f"Container '{self.container_name}' does not exist")
            return container

        if self.recreate_container:
            # Delete existing container first
            try:
                await self._service_client.delete_container(self.container_name)
            except ResourceNotFoundError:
                pass

            # Wait for deletion to complete
            start_time = asyncio.get_event_loop().time()
            while asyncio.get_event_loop().time() - start_time < self.delete_timeout_s:
                try:
                    return await self._service_client.create_container(
                        self.container_name
                    )
                except ResourceExistsError:
                    await asyncio.sleep(0.25)

            raise TimeoutError(
                f"Timeout waiting to recreate container '{self.container_name}'"
            )

        # Create or get existing container
        try:
            return await self._service_client.create_container(self.container_name)
        except ResourceExistsError:
            return self._service_client.get_container_client(self.container_name)

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

    async def store(
        self,
        filename: str,
        data: bytes,
        overwrite: bool = True,
    ) -> bool:
        """
        Upload a file to Azure Blob Storage.

        :param filename: The filename (relative to sub_folder)
        :param data: The file contents as bytes
        :param overwrite: If True, overwrite existing files
        :return: True if upload succeeded
        """
        from azure.core.exceptions import ClientAuthenticationError, ResourceExistsError

        full_path = self.sub_folder + filename

        try:
            blob_client = self.container_client.get_blob_client(full_path)
            await blob_client.upload_blob(data, overwrite=overwrite)
            return True
        except (ClientAuthenticationError, ResourceExistsError):
            return False

    async def store_text(
        self,
        filename: str,
        text: str,
        encoding: str = "utf-8",
        overwrite: bool = True,
    ) -> bool:
        """
        Upload text content to Azure Blob Storage.

        :param filename: The filename (relative to sub_folder)
        :param text: The text content
        :param encoding: Text encoding (default: utf-8)
        :param overwrite: If True, overwrite existing files
        :return: True if upload succeeded
        """
        return await self.store(filename, text.encode(encoding), overwrite=overwrite)

    async def delete(self, filename: str) -> bool:
        """
        Delete a file from Azure Blob Storage.

        :param filename: The filename (relative to sub_folder)
        :return: True if deletion succeeded
        """
        from azure.core.exceptions import ResourceNotFoundError

        full_path = self.sub_folder + filename

        try:
            blob_client = self.container_client.get_blob_client(full_path)
            await blob_client.delete_blob()
            return True
        except ResourceNotFoundError:
            return False

    async def exists(self, filename: str) -> bool:
        """
        Check if a file exists in Azure Blob Storage.

        :param filename: The filename (relative to sub_folder)
        :return: True if the file exists
        """
        full_path = self.sub_folder + filename
        blob_client = self.container_client.get_blob_client(full_path)
        return await blob_client.exists()

    def create_sas_url(
        self,
        blob_name: str,
        start_time_min: int = -15,
        end_time_days: float = 365.0,
    ) -> str:
        """
        Create a SAS URL for a blob.

        :param blob_name: The name of the blob
        :param start_time_min: Start time offset in minutes (default: -15)
        :param end_time_days: Expiry time in days (default: 365)
        :return: The SAS URL
        """
        return self.blob_path.create_sas_url(
            self.sub_folder + blob_name, start_time_min, end_time_days
        )
