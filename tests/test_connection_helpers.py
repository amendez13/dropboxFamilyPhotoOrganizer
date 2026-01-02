"""Unit tests for test_dropbox_connection helper functions."""

import sys
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from test_dropbox_connection import _test_connection, _test_file_listing, _test_thumbnail  # noqa: E402


class TestConnectionHelpers:
    """Test helper functions from test_dropbox_connection."""

    @pytest.fixture
    def mock_client(self):
        """Create a mock Dropbox client."""
        client = MagicMock()
        return client

    def test_test_connection_success(self, mock_client):
        """Test connection verification when successful."""
        mock_client.verify_connection.return_value = True

        with patch("sys.stdout", new=StringIO()) as fake_out:
            result = _test_connection(mock_client)

        assert result is True
        assert "Successfully connected" in fake_out.getvalue()
        mock_client.verify_connection.assert_called_once()

    def test_test_connection_failure(self, mock_client):
        """Test connection verification when failed."""
        mock_client.verify_connection.return_value = False

        with patch("sys.stdout", new=StringIO()) as fake_out:
            result = _test_connection(mock_client)

        assert result is False
        assert "Failed to connect" in fake_out.getvalue()
        mock_client.verify_connection.assert_called_once()

    def test_test_file_listing_with_files(self, mock_client):
        """Test file listing when files are found."""
        # Mock file metadata
        mock_files = [MagicMock(path_display=f"/Photos/file{i}.jpg", size=1024 * i) for i in range(1, 6)]
        mock_client.list_folder_recursive.return_value = iter(mock_files)

        with patch("sys.stdout", new=StringIO()) as fake_out:
            count = _test_file_listing(mock_client, "/Photos", [".jpg", ".png"])

        assert count == 5
        assert "Found 5 image files" in fake_out.getvalue()
        mock_client.list_folder_recursive.assert_called_once_with("/Photos", [".jpg", ".png"])

    def test_test_file_listing_no_files(self, mock_client):
        """Test file listing when no files are found."""
        mock_client.list_folder_recursive.return_value = iter([])

        with patch("sys.stdout", new=StringIO()) as fake_out:
            count = _test_file_listing(mock_client, "/Empty", [".jpg"])

        assert count == 0
        assert "Found 0 image files" in fake_out.getvalue()
        assert "No image files found" in fake_out.getvalue()

    def test_test_file_listing_shows_first_10(self, mock_client):
        """Test file listing shows only first 10 files."""
        # Mock 15 files
        mock_files = [MagicMock(path_display=f"/Photos/file{i:02d}.jpg", size=1024) for i in range(1, 16)]
        mock_client.list_folder_recursive.return_value = iter(mock_files)

        with patch("sys.stdout", new=StringIO()) as fake_out:
            count = _test_file_listing(mock_client, "/Photos", [".jpg"])

        assert count == 15
        output = fake_out.getvalue()
        # Should show first 10 files plus ellipsis
        assert "file01.jpg" in output
        assert "file10.jpg" in output
        assert "..." in output
        # Should not show file 11-15 individually
        assert "file15.jpg" not in output

    def test_test_thumbnail_success(self, mock_client):
        """Test thumbnail download when successful."""
        mock_file = MagicMock(name="test.jpg", path_display="/Photos/test.jpg")
        mock_client.list_folder_recursive.return_value = iter([mock_file])
        mock_client.get_thumbnail.return_value = b"thumbnail_data" * 100  # 1400 bytes
        config = {"face_recognition": {"thumbnail_size": "w256h256"}}

        with patch("sys.stdout", new=StringIO()) as fake_out:
            _test_thumbnail(mock_client, "/Photos", [".jpg"], config)

        output = fake_out.getvalue()
        assert "Successfully retrieved thumbnail" in output
        assert "1400 bytes" in output
        mock_client.get_thumbnail.assert_called_once_with("/Photos/test.jpg", size="w256h256")

    def test_test_thumbnail_failure(self, mock_client):
        """Test thumbnail download when it fails."""
        mock_file = MagicMock(name="test.png", path_display="/Photos/test.png")
        mock_client.list_folder_recursive.return_value = iter([mock_file])
        mock_client.get_thumbnail.return_value = None
        config = {"face_recognition": {"thumbnail_size": "w256h256"}}

        with patch("sys.stdout", new=StringIO()) as fake_out:
            _test_thumbnail(mock_client, "/Photos", [".png"], config)

        output = fake_out.getvalue()
        assert "Could not retrieve thumbnail" in output
        assert "Some file types may not support thumbnails" in output

    def test_test_thumbnail_no_files(self, mock_client):
        """Test thumbnail download when no files exist."""
        mock_client.list_folder_recursive.return_value = iter([])
        config = {"face_recognition": {"thumbnail_size": "w256h256"}}

        with patch("sys.stdout", new=StringIO()) as fake_out:
            _test_thumbnail(mock_client, "/Empty", [".jpg"], config)

        output = fake_out.getvalue()
        assert "No files found to test thumbnail download" in output
        mock_client.get_thumbnail.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
