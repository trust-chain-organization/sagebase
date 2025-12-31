"""GCS storage service implementation."""

import asyncio

from src.domain.services.interfaces.storage_service import IStorageService
from src.infrastructure.storage.gcs_client import GCSStorage


class GCSStorageService(IStorageService):
    """GCS implementation of storage service."""

    def __init__(self, bucket_name: str, project_id: str | None = None):
        """Initialize GCS storage service.

        Args:
            bucket_name: GCS bucket name
            project_id: GCP project ID (optional)
        """
        self._gcs = GCSStorage(bucket_name=bucket_name, project_id=project_id)

    async def download_file(self, uri: str) -> bytes:
        """Download file from storage.

        Args:
            uri: Storage URI (e.g., gs://bucket/path/to/file)

        Returns:
            Content as bytes

        Raises:
            StorageError: If download fails
        """
        # GCSStorage.download_content is sync, so wrap it in asyncio.to_thread
        content = await asyncio.to_thread(self._gcs.download_content, uri)
        if content is None:
            raise ValueError(f"Failed to download content from {uri}")
        return content.encode("utf-8")

    async def upload_file(
        self, file_path: str, content: bytes, content_type: str | None = None
    ) -> str:
        """Upload file to storage.

        Args:
            file_path: Destination path in storage
            content: Content to upload as bytes
            content_type: Optional content type

        Returns:
            URI of uploaded content

        Raises:
            StorageError: If upload fails
        """
        # Convert bytes to string for GCSStorage
        content_str = content.decode("utf-8")
        # GCSStorage.upload_content is sync, so wrap it
        return await asyncio.to_thread(self._gcs.upload_content, content_str, file_path)

    async def exists(self, uri: str) -> bool:
        """Check if file exists in storage.

        Args:
            uri: Storage URI

        Returns:
            True if file exists, False otherwise
        """
        # TODO: Implement exists check in GCSStorage
        # For now, try to download and catch exception
        try:
            await self.download_file(uri)
            return True
        except Exception:
            return False

    async def delete_file(self, uri: str) -> bool:
        """Delete file from storage.

        Args:
            uri: Storage URI

        Returns:
            True if deletion was successful

        Raises:
            StorageError: If deletion fails
        """
        # TODO: Implement delete in GCSStorage
        raise NotImplementedError("Delete operation not yet implemented for GCS")
