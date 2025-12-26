"""Google Cloud Storage utility for uploading scraped minutes data.

Provides a type-safe interface for Google Cloud Storage operations with
comprehensive error handling.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING, Any


try:
    from google.api_core.exceptions import Forbidden, NotFound
    from google.auth.exceptions import RefreshError
    from google.cloud import storage
    from google.cloud.exceptions import GoogleCloudError

    HAS_GCS = True
except ImportError:
    HAS_GCS = False
    # Define dummy types for type checking
    if TYPE_CHECKING:
        from google.api_core.exceptions import Forbidden, NotFound
        from google.auth.exceptions import RefreshError
        from google.cloud import storage
        from google.cloud.exceptions import GoogleCloudError
    else:
        GoogleCloudError = Exception  # Dummy for runtime
        Forbidden = Exception
        NotFound = Exception
        RefreshError = Exception
        storage = None

from src.infrastructure.exceptions import (
    AuthenticationError,
    PermissionError,
    StorageError,
    UploadException,
)
from src.infrastructure.exceptions import (
    FileNotFoundException as PolibaseFileNotFoundError,
)


logger = logging.getLogger(__name__)


class GCSStorage:
    """Handle Google Cloud Storage operations for scraped minutes."""

    def __init__(self, bucket_name: str, project_id: str | None = None) -> None:
        """Initialize GCS storage client.

        Args:
            bucket_name: GCS bucket name
            project_id: GCP project ID (optional, uses default if not provided)

        Raises:
            StorageError: If GCS is not available or initialization fails
            PermissionError: If access to bucket is denied
        """
        self.client: Any
        self.bucket: Any

        if not HAS_GCS:
            raise StorageError(
                "Google Cloud Storage library not installed. "
                "Install with: pip install google-cloud-storage"
            )

        self.bucket_name = bucket_name
        self.project_id = project_id

        try:
            if project_id:
                self.client = storage.Client(project=project_id) if storage else None
            else:
                self.client = storage.Client() if storage else None

            self.bucket = self.client.bucket(bucket_name)

            # Verify bucket access
            exists: bool = self.bucket.exists()
            if not exists:
                raise StorageError(
                    f"Bucket '{bucket_name}' does not exist or is not accessible",
                    {"bucket_name": bucket_name, "project_id": project_id},
                )

        except Forbidden as e:
            logger.error(f"Permission denied accessing bucket: {e}")
            raise PermissionError(
                f"Permission denied accessing bucket '{bucket_name}'",
                {"bucket_name": bucket_name, "error": str(e)},
            ) from e
        except RefreshError as e:
            logger.error(f"GCS authentication failed: {e}")
            raise AuthenticationError(
                service="Google Cloud Storage",
                reason="認証トークンの有効期限が切れています",
                solution="以下のコマンドを実行して再認証してください:\n"
                "  gcloud auth application-default login\n\n"
                "Docker環境の場合:\n"
                "  1. ホストで上記コマンドを実行\n"
                "  2. コンテナを再起動",
            ) from e
        except Exception as e:
            logger.error(f"Failed to initialize GCS client: {e}")
            raise StorageError(
                "Failed to initialize Google Cloud Storage client",
                {"bucket_name": bucket_name, "project_id": project_id, "error": str(e)},
            ) from e

    def upload_file(
        self, local_path: str | Path, gcs_path: str, content_type: str | None = None
    ) -> str:
        """Upload a file to GCS.

        Args:
            local_path: Local file path to upload
            gcs_path: Destination path in GCS (without bucket name)
            content_type: MIME type of the file (auto-detected if not provided)

        Returns:
            Public URL of the uploaded file
        """
        local_path = Path(local_path)

        if not local_path.exists():
            raise PolibaseFileNotFoundError(str(local_path))

        try:
            blob: Any = self.bucket.blob(gcs_path)

            # Auto-detect content type if not provided
            if not content_type:
                content_type = self._get_content_type(local_path.suffix)

            blob.upload_from_filename(
                str(local_path), content_type=content_type or "application/octet-stream"
            )
            logger.info(f"Uploaded {local_path} to gs://{self.bucket_name}/{gcs_path}")

            return f"gs://{self.bucket_name}/{gcs_path}"

        except GoogleCloudError as e:
            if HAS_GCS and isinstance(e, Forbidden):
                logger.error(f"Permission denied during upload: {e}")
                raise PermissionError(
                    f"Permission denied uploading to '{gcs_path}'",
                    {"gcs_path": gcs_path, "error": str(e)},
                ) from e
            logger.error(f"GCS upload failed: {e}")
            raise UploadException(
                f"Failed to upload file to GCS: {gcs_path}",
                {"local_path": str(local_path), "gcs_path": gcs_path, "error": str(e)},
            ) from e

    def upload_content(
        self, content: str | bytes, gcs_path: str, content_type: str | None = None
    ) -> str:
        """Upload content directly to GCS without saving to disk.

        Args:
            content: Content to upload (string or bytes)
            gcs_path: Destination path in GCS (without bucket name)
            content_type: MIME type of the content

        Returns:
            Public URL of the uploaded file
        """
        try:
            blob: Any = self.bucket.blob(gcs_path)

            if isinstance(content, str):
                content = content.encode("utf-8")
                if not content_type:
                    content_type = "text/plain; charset=utf-8"

            # content_type is guaranteed to be str here if content is str
            blob.upload_from_string(
                content, content_type=content_type or "application/octet-stream"
            )
            logger.info(f"Uploaded content to gs://{self.bucket_name}/{gcs_path}")

            return f"gs://{self.bucket_name}/{gcs_path}"

        except GoogleCloudError as e:
            if HAS_GCS and isinstance(e, Forbidden):
                logger.error(f"Permission denied during upload: {e}")
                raise PermissionError(
                    f"Permission denied uploading to '{gcs_path}'",
                    {"gcs_path": gcs_path, "error": str(e)},
                ) from e
            logger.error(f"GCS upload failed: {e}")
            raise UploadException(
                f"Failed to upload content to GCS: {gcs_path}",
                {"gcs_path": gcs_path, "content_size": len(content), "error": str(e)},
            ) from e

    def download_file(self, gcs_path: str, local_path: str | Path) -> None:
        """Download a file from GCS.

        Args:
            gcs_path: Source path in GCS (without bucket name)
            local_path: Local destination path
        """
        local_path = Path(local_path)
        local_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            blob: Any = self.bucket.blob(gcs_path)

            exists: bool = blob.exists()
            if not exists:
                raise PolibaseFileNotFoundError(f"gs://{self.bucket_name}/{gcs_path}")

            blob.download_to_filename(str(local_path))
            logger.info(
                f"Downloaded gs://{self.bucket_name}/{gcs_path} to {local_path}"
            )

        except NotFound:
            raise PolibaseFileNotFoundError(
                f"gs://{self.bucket_name}/{gcs_path}"
            ) from None
        except GoogleCloudError as e:
            if HAS_GCS and isinstance(e, Forbidden):
                logger.error(f"Permission denied during download: {e}")
                raise PermissionError(
                    f"Permission denied downloading '{gcs_path}'",
                    {"gcs_path": gcs_path, "error": str(e)},
                ) from e
            logger.error(f"GCS download failed: {e}")
            raise StorageError(
                f"Failed to download file from GCS: {gcs_path}",
                {"gcs_path": gcs_path, "local_path": str(local_path), "error": str(e)},
            ) from e

    def exists(self, gcs_path: str) -> bool:
        """Check if a file exists in GCS.

        Args:
            gcs_path: Path in GCS (without bucket name)

        Returns:
            True if file exists, False otherwise
        """
        try:
            blob = self.bucket.blob(gcs_path)
            return blob.exists()
        except Forbidden:
            logger.warning(f"Permission denied checking existence of: {gcs_path}")
            return False
        except GoogleCloudError as e:
            logger.error(f"GCS exists check failed: {e}")
            return False

    def list_files(self, prefix: str = "") -> list[str]:
        """List files in GCS bucket with optional prefix.

        Args:
            prefix: Path prefix to filter files

        Returns:
            List of file paths in the bucket

        Raises:
            PermissionError: If access is denied
            StorageError: If listing fails
        """
        try:
            blobs = list(self.bucket.list_blobs(prefix=prefix))
            return [blob.name for blob in blobs]
        except Forbidden as e:
            logger.error(f"Permission denied listing files: {e}")
            raise PermissionError(
                f"Permission denied listing files with prefix '{prefix}'",
                {"prefix": prefix, "error": str(e)},
            ) from e
        except GoogleCloudError as e:
            logger.error(f"GCS list files failed: {e}")
            raise StorageError(
                "Failed to list files in bucket",
                {"bucket": self.bucket_name, "prefix": prefix, "error": str(e)},
            ) from e

    def _get_content_type(self, suffix: str) -> str | None:
        """Get content type based on file extension.

        Args:
            suffix: File extension (e.g., '.pdf')

        Returns:
            MIME type string or None
        """
        content_types = {
            ".pdf": "application/pdf",
            ".json": "application/json",
            ".txt": "text/plain",
            ".html": "text/html",
            ".csv": "text/csv",
            ".xml": "application/xml",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
        }
        return content_types.get(suffix.lower())

    def download_content(self, gcs_uri: str) -> str | None:
        """Download content from GCS URI

        Args:
            gcs_uri: GCS URI (gs://bucket-name/path/to/file)

        Returns:
            File content as string or None if failed
        """
        try:
            # Parse GCS URI
            if not gcs_uri.startswith("gs://"):
                logger.error(f"Invalid GCS URI format: {gcs_uri}")
                return None

            # Extract bucket and path
            uri_parts = gcs_uri[5:].split("/", 1)
            if len(uri_parts) != 2:
                logger.error(f"Invalid GCS URI format: {gcs_uri}")
                return None

            bucket_name, blob_path = uri_parts

            # Get bucket and blob
            bucket: Any = self.client.bucket(bucket_name)
            blob: Any = bucket.blob(blob_path)

            # Check if blob exists
            exists: bool = blob.exists()
            if not exists:
                logger.error(f"GCS object not found: {gcs_uri}")
                return None

            # Download content
            content = blob.download_as_text(encoding="utf-8")
            logger.info(f"Downloaded content from GCS: {gcs_uri}")
            return content

        except Forbidden as e:
            logger.error(f"Permission denied downloading from GCS: {e}")
            return None
        except GoogleCloudError as e:
            logger.error(f"Failed to download from GCS: {e}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error downloading from GCS: {e}")
            return None

    def download_file_from_uri(self, gcs_uri: str, local_path: str | Path) -> bool:
        """Download file from GCS URI to local path

        Args:
            gcs_uri: GCS URI (gs://bucket-name/path/to/file)
            local_path: Local file path to save to

        Returns:
            True if successful, False otherwise
        """
        try:
            # Parse GCS URI
            if not gcs_uri.startswith("gs://"):
                logger.error(f"Invalid GCS URI format: {gcs_uri}")
                return False

            # Extract bucket and path
            uri_parts = gcs_uri[5:].split("/", 1)
            if len(uri_parts) != 2:
                logger.error(f"Invalid GCS URI format: {gcs_uri}")
                return False

            bucket_name, blob_path = uri_parts

            # Get bucket and blob
            bucket: Any = self.client.bucket(bucket_name)
            blob: Any = bucket.blob(blob_path)

            # Check if blob exists
            exists: bool = blob.exists()
            if not exists:
                logger.error(f"GCS object not found: {gcs_uri}")
                return False

            # Ensure parent directory exists
            local_path = Path(local_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)

            # Download file
            blob.download_to_filename(str(local_path))
            logger.info(f"Downloaded file from GCS: {gcs_uri} to {local_path}")
            return True

        except Forbidden as e:
            logger.error(f"Permission denied downloading file from GCS: {e}")
            return False
        except GoogleCloudError as e:
            logger.error(f"Failed to download file from GCS: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error downloading file from GCS: {e}")
            return False
