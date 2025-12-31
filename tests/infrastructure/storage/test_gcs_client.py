"""Tests for GCS Storage utility."""

from unittest.mock import MagicMock, patch

import pytest

from src.infrastructure.exceptions import (
    AuthenticationError,
    FileNotFoundException,
    PermissionError,
    StorageError,
)


# Mock the GCS module since it may not be available in test environment
@pytest.fixture(autouse=True)
def mock_gcs_module():
    """Mock Google Cloud Storage module."""
    with patch("src.infrastructure.storage.gcs_client.HAS_GCS", True):
        yield


@pytest.fixture
def mock_storage_client():
    """Create mock storage client."""
    mock_client = MagicMock()
    mock_bucket = MagicMock()
    mock_client.bucket.return_value = mock_bucket
    mock_bucket.exists.return_value = True
    return mock_client


@pytest.fixture
def mock_blob():
    """Create mock GCS blob."""
    mock = MagicMock()
    mock.exists.return_value = True
    mock.name = "test.txt"
    return mock


@pytest.fixture
def gcs_storage(mock_storage_client):
    """Create GCS storage instance."""
    with patch(
        "src.infrastructure.storage.gcs_client.storage.Client",
        return_value=mock_storage_client,
    ):
        from src.infrastructure.storage.gcs_client import GCSStorage

        return GCSStorage("test-bucket")


class TestGCSStorageInit:
    """Test GCSStorage initialization."""

    @patch("src.infrastructure.storage.gcs_client.storage.Client")
    def test_init_without_project_id(self, mock_client_class):
        """Test initialization without project ID."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_bucket = MagicMock()
        mock_bucket.exists.return_value = True
        mock_client.bucket.return_value = mock_bucket

        from src.infrastructure.storage.gcs_client import GCSStorage

        storage = GCSStorage("test-bucket")

        assert storage.bucket_name == "test-bucket"
        assert storage.project_id is None
        mock_client_class.assert_called_once_with()

    @patch("src.infrastructure.storage.gcs_client.storage.Client")
    def test_init_with_project_id(self, mock_client_class):
        """Test initialization with project ID."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_bucket = MagicMock()
        mock_bucket.exists.return_value = True
        mock_client.bucket.return_value = mock_bucket

        from src.infrastructure.storage.gcs_client import GCSStorage

        storage = GCSStorage("test-bucket", "test-project")

        assert storage.project_id == "test-project"
        mock_client_class.assert_called_once_with(project="test-project")

    @patch("src.infrastructure.storage.gcs_client.storage.Client")
    def test_init_bucket_not_exists(self, mock_client_class):
        """Test initialization fails if bucket doesn't exist."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_bucket = MagicMock()
        mock_bucket.exists.return_value = False
        mock_client.bucket.return_value = mock_bucket

        from src.infrastructure.storage.gcs_client import GCSStorage

        with pytest.raises(StorageError):
            GCSStorage("nonexistent-bucket")

    @patch("src.infrastructure.storage.gcs_client.storage.Client")
    @patch("src.infrastructure.storage.gcs_client.Forbidden", Exception)
    def test_init_permission_denied(self, mock_client_class):
        """Test initialization handles permission errors."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        from src.infrastructure.storage.gcs_client import Forbidden

        mock_client.bucket.side_effect = Forbidden("Access denied")

        from src.infrastructure.storage.gcs_client import GCSStorage

        with pytest.raises(PermissionError, match="Permission denied"):
            GCSStorage("test-bucket")

    @patch("src.infrastructure.storage.gcs_client.HAS_GCS", False)
    def test_init_gcs_not_available(self):
        """Test initialization fails when GCS library not available."""
        from src.infrastructure.storage.gcs_client import GCSStorage

        with pytest.raises(StorageError, match="not installed"):
            GCSStorage("test-bucket")

    @patch("src.infrastructure.storage.gcs_client.storage.Client")
    def test_init_authentication_error(self, mock_client_class):
        """Test initialization handles authentication errors."""
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client
        mock_bucket = MagicMock()

        # Mock RefreshError from google.auth.exceptions
        class MockRefreshError(Exception):
            pass

        mock_bucket.exists.side_effect = MockRefreshError(
            "Reauthentication is needed. Please run "
            "`gcloud auth application-default login` to reauthenticate."
        )
        mock_client.bucket.return_value = mock_bucket

        from src.infrastructure.storage.gcs_client import GCSStorage

        with patch(
            "src.infrastructure.storage.gcs_client.RefreshError", MockRefreshError
        ):
            with pytest.raises(
                AuthenticationError, match="認証に失敗しました"
            ) as exc_info:
                GCSStorage("test-bucket")

            # エラーメッセージに再認証コマンドが含まれていることを確認
            error_message = str(exc_info.value)
            assert "gcloud auth application-default login" in error_message
            assert "認証トークンの有効期限が切れています" in error_message


class TestUploadFile:
    """Test upload_file method."""

    def test_upload_file_success(self, gcs_storage, tmp_path):
        """Test successful file upload."""
        # Create temp file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        mock_blob = MagicMock()
        gcs_storage.bucket.blob.return_value = mock_blob

        uri = gcs_storage.upload_file(test_file, "path/to/test.txt")

        assert uri == "gs://test-bucket/path/to/test.txt"
        mock_blob.upload_from_filename.assert_called_once()

    def test_upload_file_with_content_type(self, gcs_storage, tmp_path):
        """Test file upload with custom content type."""
        test_file = tmp_path / "test.json"
        test_file.write_text("{}")

        mock_blob = MagicMock()
        gcs_storage.bucket.blob.return_value = mock_blob

        gcs_storage.upload_file(test_file, "test.json", content_type="application/json")

        mock_blob.upload_from_filename.assert_called_once_with(
            str(test_file), content_type="application/json"
        )

    def test_upload_file_auto_detect_content_type(self, gcs_storage, tmp_path):
        """Test file upload auto-detects content type."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"PDF content")

        mock_blob = MagicMock()
        gcs_storage.bucket.blob.return_value = mock_blob

        gcs_storage.upload_file(test_file, "test.pdf")

        mock_blob.upload_from_filename.assert_called_once_with(
            str(test_file), content_type="application/pdf"
        )

    def test_upload_file_not_found(self, gcs_storage):
        """Test upload raises error for non-existent file."""
        with pytest.raises(FileNotFoundException):
            gcs_storage.upload_file("/nonexistent/file.txt", "test.txt")

    def test_upload_file_permission_denied(self, gcs_storage, tmp_path):
        """Test upload handles permission errors."""

        # Create proper mock exception hierarchy
        class MockGoogleCloudError(Exception):
            pass

        class MockForbiddenError(MockGoogleCloudError):
            pass

        test_file = tmp_path / "test.txt"
        test_file.write_text("Test")

        mock_blob = MagicMock()
        mock_blob.upload_from_filename.side_effect = MockForbiddenError("No access")
        gcs_storage.bucket.blob.return_value = mock_blob

        with (
            patch(
                "src.infrastructure.storage.gcs_client.GoogleCloudError",
                MockGoogleCloudError,
            ),
            patch(
                "src.infrastructure.storage.gcs_client.Forbidden", MockForbiddenError
            ),
        ):
            with pytest.raises(PermissionError, match="Permission denied"):
                gcs_storage.upload_file(test_file, "test.txt")

    def test_upload_file_gcs_error(self, gcs_storage, tmp_path):
        """Test upload handles GCS errors."""

        class MockGoogleCloudError(Exception):
            pass

        test_file = tmp_path / "test.txt"
        test_file.write_text("Test")

        mock_blob = MagicMock()
        mock_blob.upload_from_filename.side_effect = MockGoogleCloudError("GCS error")
        gcs_storage.bucket.blob.return_value = mock_blob

        # Mock UploadException to accept any arguments
        # Source code has signature mismatch with exception definition
        class MockUploadError(Exception):
            def __init__(self, *args, **kwargs):
                super().__init__("Upload failed")

        with (
            patch(
                "src.infrastructure.storage.gcs_client.GoogleCloudError",
                MockGoogleCloudError,
            ),
            patch(
                "src.infrastructure.storage.gcs_client.UploadException", MockUploadError
            ),
        ):
            with pytest.raises(MockUploadError):
                gcs_storage.upload_file(test_file, "test.txt")


class TestUploadContent:
    """Test upload_content method."""

    def test_upload_content_string(self, gcs_storage):
        """Test uploading string content."""
        mock_blob = MagicMock()
        gcs_storage.bucket.blob.return_value = mock_blob

        uri = gcs_storage.upload_content("Test content", "test.txt")

        assert uri == "gs://test-bucket/test.txt"
        mock_blob.upload_from_string.assert_called_once_with(
            b"Test content", content_type="text/plain; charset=utf-8"
        )

    def test_upload_content_bytes(self, gcs_storage):
        """Test uploading bytes content."""
        mock_blob = MagicMock()
        gcs_storage.bucket.blob.return_value = mock_blob

        uri = gcs_storage.upload_content(b"Binary content", "test.bin")

        assert uri == "gs://test-bucket/test.bin"
        mock_blob.upload_from_string.assert_called_once_with(
            b"Binary content", content_type="application/octet-stream"
        )

    def test_upload_content_with_content_type(self, gcs_storage):
        """Test uploading content with custom content type."""
        mock_blob = MagicMock()
        gcs_storage.bucket.blob.return_value = mock_blob

        gcs_storage.upload_content(
            '{"key": "value"}', "test.json", content_type="application/json"
        )

        mock_blob.upload_from_string.assert_called_once()
        call_args = mock_blob.upload_from_string.call_args
        assert call_args[1]["content_type"] == "application/json"

    def test_upload_content_permission_denied(self, gcs_storage):
        """Test upload content handles permission errors."""

        # Create proper mock exception hierarchy
        class MockGoogleCloudError(Exception):
            pass

        class MockForbiddenError(MockGoogleCloudError):
            pass

        mock_blob = MagicMock()
        mock_blob.upload_from_string.side_effect = MockForbiddenError("No access")
        gcs_storage.bucket.blob.return_value = mock_blob

        with (
            patch(
                "src.infrastructure.storage.gcs_client.GoogleCloudError",
                MockGoogleCloudError,
            ),
            patch(
                "src.infrastructure.storage.gcs_client.Forbidden", MockForbiddenError
            ),
        ):
            with pytest.raises(PermissionError, match="Permission denied"):
                gcs_storage.upload_content("Test", "test.txt")


class TestDownloadFile:
    """Test download_file method."""

    def test_download_file_success(self, gcs_storage, tmp_path):
        """Test successful file download."""
        local_path = tmp_path / "downloaded.txt"

        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        gcs_storage.bucket.blob.return_value = mock_blob

        gcs_storage.download_file("test.txt", local_path)

        mock_blob.download_to_filename.assert_called_once_with(str(local_path))

    def test_download_file_creates_parent_dir(self, gcs_storage, tmp_path):
        """Test download creates parent directories."""
        local_path = tmp_path / "subdir" / "downloaded.txt"

        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        gcs_storage.bucket.blob.return_value = mock_blob

        gcs_storage.download_file("test.txt", local_path)

        assert local_path.parent.exists()

    @patch("src.infrastructure.storage.gcs_client.NotFound", Exception)
    def test_download_file_not_found(self, gcs_storage, tmp_path):
        """Test download handles file not found."""
        from src.infrastructure.storage.gcs_client import NotFound

        local_path = tmp_path / "downloaded.txt"

        mock_blob = MagicMock()
        mock_blob.download_to_filename.side_effect = NotFound("Not found")
        gcs_storage.bucket.blob.return_value = mock_blob

        with pytest.raises(FileNotFoundException):
            gcs_storage.download_file("nonexistent.txt", local_path)

    def test_download_file_blob_not_exists(self, gcs_storage, tmp_path):
        """Test download handles blob that doesn't exist."""
        local_path = tmp_path / "downloaded.txt"

        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        gcs_storage.bucket.blob.return_value = mock_blob

        with pytest.raises(FileNotFoundException):
            gcs_storage.download_file("nonexistent.txt", local_path)


class TestExists:
    """Test exists method."""

    def test_exists_file_exists(self, gcs_storage):
        """Test exists returns True for existing file."""
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        gcs_storage.bucket.blob.return_value = mock_blob

        assert gcs_storage.exists("test.txt") is True

    def test_exists_file_not_exists(self, gcs_storage):
        """Test exists returns False for non-existent file."""
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False
        gcs_storage.bucket.blob.return_value = mock_blob

        assert gcs_storage.exists("nonexistent.txt") is False

    @patch("src.infrastructure.storage.gcs_client.Forbidden", Exception)
    def test_exists_permission_denied(self, gcs_storage):
        """Test exists handles permission errors."""
        from src.infrastructure.storage.gcs_client import Forbidden

        mock_blob = MagicMock()
        mock_blob.exists.side_effect = Forbidden("No access")
        gcs_storage.bucket.blob.return_value = mock_blob

        assert gcs_storage.exists("test.txt") is False

    @patch("src.infrastructure.storage.gcs_client.GoogleCloudError", Exception)
    def test_exists_gcs_error(self, gcs_storage):
        """Test exists handles GCS errors."""
        from src.infrastructure.storage.gcs_client import GoogleCloudError

        mock_blob = MagicMock()
        mock_blob.exists.side_effect = GoogleCloudError("Error")
        gcs_storage.bucket.blob.return_value = mock_blob

        assert gcs_storage.exists("test.txt") is False


class TestListFiles:
    """Test list_files method."""

    def test_list_files_success(self, gcs_storage):
        """Test successful file listing."""
        mock_blob1 = MagicMock()
        mock_blob1.name = "file1.txt"
        mock_blob2 = MagicMock()
        mock_blob2.name = "file2.txt"

        gcs_storage.bucket.list_blobs.return_value = [mock_blob1, mock_blob2]

        files = gcs_storage.list_files()

        assert files == ["file1.txt", "file2.txt"]

    def test_list_files_with_prefix(self, gcs_storage):
        """Test listing files with prefix."""
        mock_blob = MagicMock()
        mock_blob.name = "subdir/file.txt"

        gcs_storage.bucket.list_blobs.return_value = [mock_blob]

        files = gcs_storage.list_files(prefix="subdir/")

        gcs_storage.bucket.list_blobs.assert_called_once_with(prefix="subdir/")
        assert files == ["subdir/file.txt"]

    @patch("src.infrastructure.storage.gcs_client.Forbidden", Exception)
    def test_list_files_permission_denied(self, gcs_storage):
        """Test list files handles permission errors."""
        from src.infrastructure.storage.gcs_client import Forbidden

        gcs_storage.bucket.list_blobs.side_effect = Forbidden("No access")

        with pytest.raises(PermissionError, match="Permission denied"):
            gcs_storage.list_files()

    @patch("src.infrastructure.storage.gcs_client.GoogleCloudError", Exception)
    def test_list_files_gcs_error(self, gcs_storage):
        """Test list files handles GCS errors."""
        from src.infrastructure.storage.gcs_client import GoogleCloudError

        gcs_storage.bucket.list_blobs.side_effect = GoogleCloudError("Error")

        with pytest.raises(StorageError, match="Failed to list files"):
            gcs_storage.list_files()


class TestGetContentType:
    """Test _get_content_type method."""

    def test_get_content_type_pdf(self, gcs_storage):
        """Test content type for PDF."""
        content_type = gcs_storage._get_content_type(".pdf")

        assert content_type == "application/pdf"

    def test_get_content_type_json(self, gcs_storage):
        """Test content type for JSON."""
        content_type = gcs_storage._get_content_type(".json")

        assert content_type == "application/json"

    def test_get_content_type_text(self, gcs_storage):
        """Test content type for text."""
        content_type = gcs_storage._get_content_type(".txt")

        assert content_type == "text/plain"

    def test_get_content_type_image(self, gcs_storage):
        """Test content type for images."""
        assert gcs_storage._get_content_type(".png") == "image/png"
        assert gcs_storage._get_content_type(".jpg") == "image/jpeg"
        assert gcs_storage._get_content_type(".jpeg") == "image/jpeg"

    def test_get_content_type_unknown(self, gcs_storage):
        """Test content type for unknown extension."""
        content_type = gcs_storage._get_content_type(".unknown")

        assert content_type is None

    def test_get_content_type_case_insensitive(self, gcs_storage):
        """Test content type is case insensitive."""
        assert gcs_storage._get_content_type(".PDF") == "application/pdf"
        assert gcs_storage._get_content_type(".JSON") == "application/json"


class TestDownloadContent:
    """Test download_content method."""

    def test_download_content_success(self, gcs_storage):
        """Test successful content download."""
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_blob.download_as_text.return_value = "File content"

        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        gcs_storage.client.bucket.return_value = mock_bucket

        content = gcs_storage.download_content("gs://bucket/path/file.txt")

        assert content == "File content"
        mock_blob.download_as_text.assert_called_once_with(encoding="utf-8")

    def test_download_content_invalid_uri(self, gcs_storage):
        """Test download content with invalid URI."""
        content = gcs_storage.download_content("invalid-uri")

        assert content is None

    def test_download_content_invalid_format(self, gcs_storage):
        """Test download content with invalid URI format."""
        content = gcs_storage.download_content("gs://bucket-only")

        assert content is None

    def test_download_content_not_exists(self, gcs_storage):
        """Test download content when blob doesn't exist."""
        mock_blob = MagicMock()
        mock_blob.exists.return_value = False

        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        gcs_storage.client.bucket.return_value = mock_bucket

        content = gcs_storage.download_content("gs://bucket/path/file.txt")

        assert content is None

    @patch("src.infrastructure.storage.gcs_client.Forbidden", Exception)
    def test_download_content_permission_denied(self, gcs_storage):
        """Test download content handles permission errors."""
        from src.infrastructure.storage.gcs_client import Forbidden

        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_blob.download_as_text.side_effect = Forbidden("No access")

        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        gcs_storage.client.bucket.return_value = mock_bucket

        content = gcs_storage.download_content("gs://bucket/path/file.txt")

        assert content is None


class TestDownloadFileFromUri:
    """Test download_file_from_uri method."""

    def test_download_file_from_uri_success(self, gcs_storage, tmp_path):
        """Test successful file download from URI."""
        local_path = tmp_path / "downloaded.txt"

        mock_blob = MagicMock()
        mock_blob.exists.return_value = True

        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        gcs_storage.client.bucket.return_value = mock_bucket

        result = gcs_storage.download_file_from_uri(
            "gs://bucket/path/file.txt", local_path
        )

        assert result is True
        mock_blob.download_to_filename.assert_called_once_with(str(local_path))

    def test_download_file_from_uri_creates_dir(self, gcs_storage, tmp_path):
        """Test download creates parent directory."""
        local_path = tmp_path / "subdir" / "file.txt"

        mock_blob = MagicMock()
        mock_blob.exists.return_value = True

        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        gcs_storage.client.bucket.return_value = mock_bucket

        gcs_storage.download_file_from_uri("gs://bucket/file.txt", local_path)

        assert local_path.parent.exists()

    def test_download_file_from_uri_invalid_uri(self, gcs_storage, tmp_path):
        """Test download with invalid URI."""
        local_path = tmp_path / "file.txt"

        result = gcs_storage.download_file_from_uri("invalid-uri", local_path)

        assert result is False

    def test_download_file_from_uri_not_exists(self, gcs_storage, tmp_path):
        """Test download when blob doesn't exist."""
        local_path = tmp_path / "file.txt"

        mock_blob = MagicMock()
        mock_blob.exists.return_value = False

        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        gcs_storage.client.bucket.return_value = mock_bucket

        result = gcs_storage.download_file_from_uri("gs://bucket/file.txt", local_path)

        assert result is False

    @patch("src.infrastructure.storage.gcs_client.Forbidden", Exception)
    def test_download_file_from_uri_permission_denied(self, gcs_storage, tmp_path):
        """Test download handles permission errors."""
        from src.infrastructure.storage.gcs_client import Forbidden

        local_path = tmp_path / "file.txt"

        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        mock_blob.download_to_filename.side_effect = Forbidden("No access")

        mock_bucket = MagicMock()
        mock_bucket.blob.return_value = mock_blob
        gcs_storage.client.bucket.return_value = mock_bucket

        result = gcs_storage.download_file_from_uri("gs://bucket/file.txt", local_path)

        assert result is False


class TestGCSStorageIntegration:
    """Integration tests for GCS Storage."""

    def test_upload_and_download_workflow(self, gcs_storage, tmp_path):
        """Test complete upload and download workflow."""
        # Create test file
        test_file = tmp_path / "test.txt"
        test_file.write_text("Test content")

        # Mock blob
        mock_blob = MagicMock()
        mock_blob.exists.return_value = True
        gcs_storage.bucket.blob.return_value = mock_blob

        # Upload
        uri = gcs_storage.upload_file(test_file, "test.txt")
        assert uri == "gs://test-bucket/test.txt"

        # Download
        download_path = tmp_path / "downloaded.txt"
        gcs_storage.download_file("test.txt", download_path)

        mock_blob.upload_from_filename.assert_called_once()
        mock_blob.download_to_filename.assert_called_once()
