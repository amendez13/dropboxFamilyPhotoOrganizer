"""Unit tests for DropboxClient."""

import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest
from dropbox.exceptions import ApiError, AuthError
from dropbox.files import FileMetadata, FolderMetadata

# Add scripts directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Local import must come after path modification
from dropbox_client import DropboxClient  # noqa: E402


class TestDropboxClientInit:
    """Test DropboxClient initialization."""

    def test_init_with_access_token_only(self):
        """Test initialization with legacy access token."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            client = DropboxClient(access_token="test_token")

            assert client.auth_mode == "legacy"
            assert client.access_token == "test_token"
            assert client.refresh_token is None
            mock_dropbox.assert_called_once_with("test_token")

    def test_init_with_refresh_token(self):
        """Test initialization with OAuth refresh token."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            client = DropboxClient(
                refresh_token="refresh_token",
                app_key="app_key",
                app_secret="app_secret",
            )

            assert client.auth_mode == "oauth"
            assert client.refresh_token == "refresh_token"
            assert client.access_token is None
            assert client.app_key == "app_key"
            assert client.app_secret == "app_secret"
            mock_dropbox.assert_called_once_with(
                oauth2_refresh_token="refresh_token",
                app_key="app_key",
                app_secret="app_secret",
            )

    def test_init_with_refresh_token_no_secret(self):
        """Test initialization with refresh token but no app secret."""
        with patch("dropbox.Dropbox"):
            client = DropboxClient(
                refresh_token="refresh_token",
                app_key="app_key",
            )

            assert client.auth_mode == "oauth"
            assert client.app_secret is None

    def test_init_with_token_callback(self):
        """Test initialization with token refresh callback."""
        callback = Mock()
        with patch("dropbox.Dropbox"):
            client = DropboxClient(
                refresh_token="refresh_token",
                app_key="app_key",
                token_refresh_callback=callback,
            )

            assert client.token_refresh_callback == callback

    def test_init_no_tokens_raises_value_error(self):
        """Test that init raises ValueError when no tokens provided."""
        with pytest.raises(ValueError) as exc_info:
            DropboxClient()

        assert "Either access_token or refresh_token must be provided" in str(exc_info.value)

    def test_init_refresh_token_without_app_key_raises_value_error(self):
        """Test that refresh token without app key raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            DropboxClient(refresh_token="refresh_token")

        assert "app_key is required when using refresh_token" in str(exc_info.value)


class TestDropboxClientHelpers:
    """Test DropboxClient helper methods."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock DropboxClient instance."""
        mock_dbx = MagicMock()
        client = DropboxClient.__new__(DropboxClient)
        client.dbx = mock_dbx
        client.logger = Mock()
        return client

    def test_normalize_folder_path_empty_string(self, mock_client):
        """Test normalizing empty folder path."""
        result = mock_client._normalize_folder_path("")
        assert result == ""

    def test_normalize_folder_path_root_slash(self, mock_client):
        """Test normalizing root slash to empty string."""
        result = mock_client._normalize_folder_path("/")
        assert result == ""

    def test_normalize_folder_path_adds_leading_slash(self, mock_client):
        """Test adding leading slash to path."""
        result = mock_client._normalize_folder_path("Photos")
        assert result == "/Photos"

    def test_normalize_folder_path_preserves_existing_slash(self, mock_client):
        """Test that existing leading slash is preserved."""
        result = mock_client._normalize_folder_path("/Photos")
        assert result == "/Photos"

    def test_normalize_folder_path_complex_path(self, mock_client):
        """Test normalizing complex folder path."""
        result = mock_client._normalize_folder_path("Photos/Family/2024")
        assert result == "/Photos/Family/2024"

    def test_should_include_file_no_extensions_filter(self, mock_client):
        """Test file inclusion with no extension filter."""
        result = mock_client._should_include_file("photo.jpg", None)
        assert result is True

    def test_should_include_file_empty_extensions_filter(self, mock_client):
        """Test file inclusion with empty extension filter."""
        result = mock_client._should_include_file("photo.jpg", [])
        assert result is True

    def test_should_include_file_matching_extension(self, mock_client):
        """Test file inclusion with matching extension."""
        result = mock_client._should_include_file("photo.jpg", [".jpg", ".png"])
        assert result is True

    def test_should_include_file_case_insensitive_match(self, mock_client):
        """Test case-insensitive extension matching."""
        result = mock_client._should_include_file("PHOTO.JPG", [".jpg", ".png"])
        assert result is True

    def test_should_include_file_non_matching_extension(self, mock_client):
        """Test file exclusion with non-matching extension."""
        result = mock_client._should_include_file("photo.gif", [".jpg", ".png"])
        assert result is False

    def test_should_include_file_heic_format(self, mock_client):
        """Test HEIC file format inclusion."""
        result = mock_client._should_include_file("IMG_1234.HEIC", [".jpg", ".jpeg", ".png", ".heic"])
        assert result is True

    def test_should_include_file_no_extension(self, mock_client):
        """Test file without extension is excluded."""
        result = mock_client._should_include_file("README", [".jpg", ".png"])
        assert result is False

    def test_should_include_file_multiple_dots(self, mock_client):
        """Test file with multiple dots in name."""
        result = mock_client._should_include_file("photo.backup.jpg", [".jpg"])
        assert result is True


class TestGetCurrentAccessToken:
    """Test get_current_access_token method."""

    def test_oauth_mode_returns_sdk_token(self):
        """Test that OAuth mode returns token from SDK."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dbx._oauth2_access_token = "sdk_access_token"
            mock_dropbox.return_value = mock_dbx

            client = DropboxClient(
                refresh_token="refresh_token",
                app_key="app_key",
            )

            result = client.get_current_access_token()
            assert result == "sdk_access_token"

    def test_oauth_mode_returns_none_when_no_token(self):
        """Test that OAuth mode returns None when SDK has no token."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock(spec=[])  # No _oauth2_access_token attribute
            mock_dropbox.return_value = mock_dbx

            client = DropboxClient(
                refresh_token="refresh_token",
                app_key="app_key",
            )

            result = client.get_current_access_token()
            assert result is None

    def test_legacy_mode_returns_access_token(self):
        """Test that legacy mode returns stored access token."""
        with patch("dropbox.Dropbox"):
            client = DropboxClient(access_token="legacy_token")

            result = client.get_current_access_token()
            assert result == "legacy_token"


class TestVerifyConnection:
    """Test verify_connection method."""

    def test_verify_connection_success(self):
        """Test successful connection verification."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_account = MagicMock()
            mock_account.email = "test@example.com"
            mock_dbx.users_get_current_account.return_value = mock_account
            mock_dropbox.return_value = mock_dbx

            client = DropboxClient(access_token="test_token")
            result = client.verify_connection()

            assert result is True
            mock_dbx.users_get_current_account.assert_called_once()

    def test_verify_connection_auth_error(self):
        """Test connection verification with auth error."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dbx.users_get_current_account.side_effect = AuthError("test", "invalid_token")
            mock_dropbox.return_value = mock_dbx

            client = DropboxClient(access_token="bad_token")
            result = client.verify_connection()

            assert result is False

    def test_verify_connection_generic_exception(self):
        """Test connection verification with generic exception."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dbx.users_get_current_account.side_effect = Exception("Network error")
            mock_dropbox.return_value = mock_dbx

            client = DropboxClient(access_token="test_token")
            result = client.verify_connection()

            assert result is False

    def test_verify_connection_oauth_token_refresh_callback(self):
        """Test that token refresh callback is called when token changes."""
        callback = Mock()

        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dbx._oauth2_access_token = "new_access_token"
            mock_account = MagicMock()
            mock_account.email = "test@example.com"
            mock_dbx.users_get_current_account.return_value = mock_account
            mock_dropbox.return_value = mock_dbx

            client = DropboxClient(
                refresh_token="refresh_token",
                app_key="app_key",
                token_refresh_callback=callback,
            )

            result = client.verify_connection()

            assert result is True
            callback.assert_called_once()
            # Verify callback was called with new token and expires_at
            call_args = callback.call_args[0]
            assert call_args[0] == "new_access_token"
            assert client.access_token == "new_access_token"

    def test_verify_connection_oauth_no_callback(self):
        """Test OAuth mode without token refresh callback."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dbx._oauth2_access_token = "new_access_token"
            mock_account = MagicMock()
            mock_account.email = "test@example.com"
            mock_dbx.users_get_current_account.return_value = mock_account
            mock_dropbox.return_value = mock_dbx

            client = DropboxClient(
                refresh_token="refresh_token",
                app_key="app_key",
            )

            result = client.verify_connection()
            assert result is True

    def test_verify_connection_oauth_same_token(self):
        """Test OAuth mode when token hasn't changed."""
        callback = Mock()

        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dbx._oauth2_access_token = "same_token"
            mock_account = MagicMock()
            mock_account.email = "test@example.com"
            mock_dbx.users_get_current_account.return_value = mock_account
            mock_dropbox.return_value = mock_dbx

            client = DropboxClient(
                refresh_token="refresh_token",
                app_key="app_key",
                token_refresh_callback=callback,
            )
            # Pre-set the access token to the same value
            client.access_token = "same_token"

            result = client.verify_connection()

            assert result is True
            callback.assert_not_called()


class TestListFolderRecursive:
    """Test list_folder_recursive method."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock DropboxClient instance."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            client = DropboxClient(access_token="test_token")
            return client

    def test_list_folder_recursive_returns_files(self, mock_client):
        """Test that list_folder_recursive yields file entries."""
        mock_file1 = MagicMock(spec=FileMetadata)
        mock_file1.name = "photo1.jpg"
        mock_file2 = MagicMock(spec=FileMetadata)
        mock_file2.name = "photo2.png"
        mock_folder = MagicMock(spec=FolderMetadata)

        mock_result = MagicMock()
        mock_result.entries = [mock_file1, mock_folder, mock_file2]
        mock_result.has_more = False

        mock_client.dbx.files_list_folder.return_value = mock_result

        files = list(mock_client.list_folder_recursive("/Photos"))

        assert len(files) == 2
        assert files[0] == mock_file1
        assert files[1] == mock_file2

    def test_list_folder_recursive_with_extension_filter(self, mock_client):
        """Test list_folder_recursive with extension filter."""
        mock_file1 = MagicMock(spec=FileMetadata)
        mock_file1.name = "photo1.jpg"
        mock_file2 = MagicMock(spec=FileMetadata)
        mock_file2.name = "document.pdf"

        mock_result = MagicMock()
        mock_result.entries = [mock_file1, mock_file2]
        mock_result.has_more = False

        mock_client.dbx.files_list_folder.return_value = mock_result

        files = list(mock_client.list_folder_recursive("/Photos", extensions=[".jpg"]))

        assert len(files) == 1
        assert files[0].name == "photo1.jpg"

    def test_list_folder_recursive_handles_pagination(self, mock_client):
        """Test that list_folder_recursive handles pagination."""
        mock_file1 = MagicMock(spec=FileMetadata)
        mock_file1.name = "photo1.jpg"
        mock_file2 = MagicMock(spec=FileMetadata)
        mock_file2.name = "photo2.jpg"

        # First page
        mock_result1 = MagicMock()
        mock_result1.entries = [mock_file1]
        mock_result1.has_more = True
        mock_result1.cursor = "cursor1"

        # Second page
        mock_result2 = MagicMock()
        mock_result2.entries = [mock_file2]
        mock_result2.has_more = False

        mock_client.dbx.files_list_folder.return_value = mock_result1
        mock_client.dbx.files_list_folder_continue.return_value = mock_result2

        files = list(mock_client.list_folder_recursive("/Photos"))

        assert len(files) == 2
        mock_client.dbx.files_list_folder_continue.assert_called_once_with("cursor1")

    def test_list_folder_recursive_api_error(self, mock_client):
        """Test that API errors are raised."""
        mock_client.dbx.files_list_folder.side_effect = ApiError("test", "path_not_found", "Path not found", "en")

        with pytest.raises(ApiError):
            list(mock_client.list_folder_recursive("/NonexistentPath"))


class TestGetFileCount:
    """Test get_file_count method."""

    def test_get_file_count_returns_count(self):
        """Test that get_file_count returns correct count."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_file1 = MagicMock(spec=FileMetadata)
            mock_file1.name = "photo1.jpg"
            mock_file2 = MagicMock(spec=FileMetadata)
            mock_file2.name = "photo2.jpg"

            mock_result = MagicMock()
            mock_result.entries = [mock_file1, mock_file2]
            mock_result.has_more = False

            mock_dbx.files_list_folder.return_value = mock_result

            client = DropboxClient(access_token="test_token")
            count = client.get_file_count("/Photos")

            assert count == 2

    def test_get_file_count_with_extensions(self):
        """Test get_file_count with extension filter."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_file1 = MagicMock(spec=FileMetadata)
            mock_file1.name = "photo1.jpg"
            mock_file2 = MagicMock(spec=FileMetadata)
            mock_file2.name = "doc.pdf"

            mock_result = MagicMock()
            mock_result.entries = [mock_file1, mock_file2]
            mock_result.has_more = False

            mock_dbx.files_list_folder.return_value = mock_result

            client = DropboxClient(access_token="test_token")
            count = client.get_file_count("/Photos", extensions=[".jpg"])

            assert count == 1


class TestDownloadFile:
    """Test download_file method."""

    def test_download_file_success(self):
        """Test successful file download."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_response = MagicMock()
            mock_response.content = b"file content"
            mock_dbx.files_download.return_value = (MagicMock(), mock_response)

            client = DropboxClient(access_token="test_token")

            with tempfile.TemporaryDirectory() as tmpdir:
                local_path = os.path.join(tmpdir, "subdir", "test.jpg")
                result = client.download_file("/remote/test.jpg", local_path)

                assert result is True
                assert os.path.exists(local_path)
                with open(local_path, "rb") as f:
                    assert f.read() == b"file content"

    def test_download_file_api_error(self):
        """Test download file with API error."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_dbx.files_download.side_effect = ApiError("test", "path_not_found", "File not found", "en")

            client = DropboxClient(access_token="test_token")

            with tempfile.TemporaryDirectory() as tmpdir:
                local_path = os.path.join(tmpdir, "test.jpg")
                result = client.download_file("/remote/missing.jpg", local_path)

                assert result is False


class TestGetThumbnail:
    """Test get_thumbnail method."""

    def test_get_thumbnail_default_params(self):
        """Test get_thumbnail with default parameters."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_response = MagicMock()
            mock_response.content = b"thumbnail_bytes"
            mock_dbx.files_get_thumbnail.return_value = (MagicMock(), mock_response)

            client = DropboxClient(access_token="test_token")
            result = client.get_thumbnail("/remote/photo.jpg")

            assert result == b"thumbnail_bytes"
            mock_dbx.files_get_thumbnail.assert_called_once()

    def test_get_thumbnail_custom_size(self):
        """Test get_thumbnail with custom size."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_response = MagicMock()
            mock_response.content = b"thumbnail_bytes"
            mock_dbx.files_get_thumbnail.return_value = (MagicMock(), mock_response)

            client = DropboxClient(access_token="test_token")
            result = client.get_thumbnail("/remote/photo.jpg", size="w128h128")

            assert result == b"thumbnail_bytes"

    def test_get_thumbnail_png_format(self):
        """Test get_thumbnail with PNG format."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_response = MagicMock()
            mock_response.content = b"png_thumbnail"
            mock_dbx.files_get_thumbnail.return_value = (MagicMock(), mock_response)

            client = DropboxClient(access_token="test_token")
            result = client.get_thumbnail("/remote/photo.jpg", format="png")

            assert result == b"png_thumbnail"

    def test_get_thumbnail_unknown_size_uses_default(self):
        """Test that unknown size falls back to default."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_response = MagicMock()
            mock_response.content = b"thumbnail_bytes"
            mock_dbx.files_get_thumbnail.return_value = (MagicMock(), mock_response)

            client = DropboxClient(access_token="test_token")
            result = client.get_thumbnail("/remote/photo.jpg", size="invalid_size")

            assert result == b"thumbnail_bytes"

    def test_get_thumbnail_api_error(self):
        """Test get_thumbnail with API error."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_dbx.files_get_thumbnail.side_effect = ApiError("test", "unsupported", "Unsupported format", "en")

            client = DropboxClient(access_token="test_token")
            result = client.get_thumbnail("/remote/document.pdf")

            assert result is None


class TestGetFileContent:
    """Test get_file_content method."""

    def test_get_file_content_returns_bytes(self):
        """Test that successful download returns bytes."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_response = MagicMock()
            mock_response.content = b"file_content_bytes"
            mock_dbx.files_download.return_value = (MagicMock(), mock_response)

            client = DropboxClient(access_token="test_token")
            result = client.get_file_content("/test/file.jpg")

            assert result == b"file_content_bytes"
            mock_dbx.files_download.assert_called_once_with("/test/file.jpg")

    def test_get_file_content_handles_api_error(self):
        """Test that API errors return None and are logged."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_dbx.files_download.side_effect = ApiError("test", "not_found", "File not found", "en")

            client = DropboxClient(access_token="test_token")
            result = client.get_file_content("/test/missing.jpg")

            assert result is None


class TestCopyFile:
    """Test copy_file method."""

    def test_copy_file_success(self):
        """Test successful file copy."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_result = MagicMock()
            mock_result.metadata.name = "copied_file.jpg"
            mock_dbx.files_copy_v2.return_value = mock_result

            client = DropboxClient(access_token="test_token")
            result = client.copy_file("/source/file.jpg", "/dest/file.jpg")

            assert result is True
            mock_dbx.files_copy_v2.assert_called_once_with(
                "/source/file.jpg",
                "/dest/file.jpg",
                autorename=True,
                allow_shared_folder=False,
            )

    def test_copy_file_with_options(self):
        """Test copy file with custom options."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_result = MagicMock()
            mock_result.metadata.name = "file.jpg"
            mock_dbx.files_copy_v2.return_value = mock_result

            client = DropboxClient(access_token="test_token")
            result = client.copy_file(
                "/source/file.jpg",
                "/dest/file.jpg",
                autorename=False,
                allow_shared_folder=True,
            )

            assert result is True
            mock_dbx.files_copy_v2.assert_called_once_with(
                "/source/file.jpg",
                "/dest/file.jpg",
                autorename=False,
                allow_shared_folder=True,
            )

    def test_copy_file_api_error(self):
        """Test copy file with API error."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_dbx.files_copy_v2.side_effect = ApiError("test", "path_not_found", "Source not found", "en")

            client = DropboxClient(access_token="test_token")
            result = client.copy_file("/missing/file.jpg", "/dest/file.jpg")

            assert result is False


class TestMoveFile:
    """Test move_file method."""

    def test_move_file_success(self):
        """Test successful file move."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_result = MagicMock()
            mock_result.metadata.name = "moved_file.jpg"
            mock_dbx.files_move_v2.return_value = mock_result

            client = DropboxClient(access_token="test_token")
            result = client.move_file("/source/file.jpg", "/dest/file.jpg")

            assert result is True
            mock_dbx.files_move_v2.assert_called_once_with(
                "/source/file.jpg",
                "/dest/file.jpg",
                autorename=True,
                allow_shared_folder=False,
            )

    def test_move_file_with_options(self):
        """Test move file with custom options."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_result = MagicMock()
            mock_result.metadata.name = "file.jpg"
            mock_dbx.files_move_v2.return_value = mock_result

            client = DropboxClient(access_token="test_token")
            result = client.move_file(
                "/source/file.jpg",
                "/dest/file.jpg",
                autorename=False,
                allow_shared_folder=True,
            )

            assert result is True
            mock_dbx.files_move_v2.assert_called_once_with(
                "/source/file.jpg",
                "/dest/file.jpg",
                autorename=False,
                allow_shared_folder=True,
            )

    def test_move_file_api_error(self):
        """Test move file with API error."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_dbx.files_move_v2.side_effect = ApiError("test", "path_not_found", "Source not found", "en")

            client = DropboxClient(access_token="test_token")
            result = client.move_file("/missing/file.jpg", "/dest/file.jpg")

            assert result is False


class TestCreateFolder:
    """Test create_folder method."""

    def test_create_folder_success(self):
        """Test successful folder creation."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            client = DropboxClient(access_token="test_token")
            result = client.create_folder("/new_folder")

            assert result is True
            mock_dbx.files_create_folder_v2.assert_called_once_with("/new_folder")

    def test_create_folder_already_exists(self):
        """Test that folder already exists returns True."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            # Create a proper ApiError for path conflict
            mock_error = MagicMock()
            mock_error.is_path.return_value = True
            mock_path_error = MagicMock()
            mock_path_error.is_conflict.return_value = True
            mock_error.get_path.return_value = mock_path_error

            api_error = ApiError("test", mock_error, "Path conflict", "en")
            mock_dbx.files_create_folder_v2.side_effect = api_error

            client = DropboxClient(access_token="test_token")
            result = client.create_folder("/existing_folder")

            assert result is True

    def test_create_folder_other_error(self):
        """Test that other errors return False."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            # Create a proper ApiError for a different error
            mock_error = MagicMock()
            mock_error.is_path.return_value = False

            api_error = ApiError("test", mock_error, "Permission denied", "en")
            mock_dbx.files_create_folder_v2.side_effect = api_error

            client = DropboxClient(access_token="test_token")
            result = client.create_folder("/no_permission")

            assert result is False


class TestGetFileMetadata:
    """Test get_file_metadata method."""

    def test_get_file_metadata_success(self):
        """Test successful metadata retrieval."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_metadata = MagicMock(spec=FileMetadata)
            mock_dbx.files_get_metadata.return_value = mock_metadata

            client = DropboxClient(access_token="test_token")
            result = client.get_file_metadata("/test/file.jpg")

            assert result == mock_metadata
            mock_dbx.files_get_metadata.assert_called_once_with("/test/file.jpg")

    def test_get_file_metadata_returns_none_for_folder(self):
        """Test that folder metadata returns None."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_metadata = MagicMock(spec=FolderMetadata)
            mock_dbx.files_get_metadata.return_value = mock_metadata

            client = DropboxClient(access_token="test_token")
            result = client.get_file_metadata("/test/folder")

            assert result is None

    def test_get_file_metadata_api_error(self):
        """Test metadata retrieval with API error."""
        with patch("dropbox.Dropbox") as mock_dropbox:
            mock_dbx = MagicMock()
            mock_dropbox.return_value = mock_dbx

            mock_dbx.files_get_metadata.side_effect = ApiError("test", "path_not_found", "Path not found", "en")

            client = DropboxClient(access_token="test_token")
            result = client.get_file_metadata("/missing/file.jpg")

            assert result is None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
