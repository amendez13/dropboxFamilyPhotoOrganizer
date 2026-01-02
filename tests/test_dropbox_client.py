"""Unit tests for DropboxClient helper methods."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from dropbox_client import DropboxClient  # noqa: E402


class TestDropboxClientHelpers:
    """Test DropboxClient helper methods extracted during complexity refactoring."""

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


class TestGetFileContent:
    """Test get_file_content method."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock DropboxClient instance."""
        mock_dbx = MagicMock()
        client = DropboxClient.__new__(DropboxClient)
        client.dbx = mock_dbx
        client.logger = Mock()
        return client

    def test_get_file_content_returns_bytes(self, mock_client):
        """Test that successful download returns bytes."""
        # Mock successful download
        mock_response = MagicMock()
        mock_response.content = b"file_content_bytes"
        mock_client.dbx.files_download.return_value = (MagicMock(), mock_response)

        result = mock_client.get_file_content("/test/file.jpg")

        assert result == b"file_content_bytes"
        mock_client.dbx.files_download.assert_called_once_with("/test/file.jpg")

    def test_get_file_content_handles_api_error(self, mock_client):
        """Test that API errors return None and are logged."""
        from dropbox.exceptions import ApiError

        # Mock API error
        mock_client.dbx.files_download.side_effect = ApiError("test", "not_found", "File not found", "en")

        result = mock_client.get_file_content("/test/missing.jpg")

        assert result is None
        mock_client.logger.warning.assert_called_once()
        assert "Could not download file '/test/missing.jpg'" in mock_client.logger.warning.call_args[0][0]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
