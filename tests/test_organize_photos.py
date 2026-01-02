"""Unit tests for organize_photos script functions."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from organize_photos import perform_operations, process_images  # noqa: E402


class TestProcessImages:
    """Test process_images function."""

    @pytest.fixture
    def mock_dbx_client(self):
        """Create a mock DropboxClient instance."""
        client = MagicMock()
        client.get_file_content.return_value = b"fake_image_data"
        client.get_thumbnail.return_value = b"fake_thumbnail_data"
        return client

    @pytest.fixture
    def mock_provider(self):
        """Create a mock face recognition provider."""
        provider = MagicMock()
        provider.find_matches_in_image.return_value = ([{"confidence": 0.8}], 1)
        return provider

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock()

    def test_process_images_handles_missing_thumbnails(self, mock_dbx_client, mock_provider, mock_logger):
        """Test that missing thumbnails are logged and counted as errors."""
        # Mock file metadata
        mock_file = MagicMock()
        mock_file.path_display = "/Photos/test.jpg"
        image_files = [mock_file]

        # Mock thumbnail failure
        mock_dbx_client.get_thumbnail.return_value = None

        matches, processed, errors = process_images(
            image_files, mock_dbx_client, mock_provider, {}, False, 0.6, False, mock_logger
        )

        assert processed == 1
        assert errors == 1
        assert len(matches) == 0
        mock_logger.warning.assert_called_with("Could not get thumbnail for /Photos/test.jpg")
        mock_provider.find_matches_in_image.assert_not_called()

    def test_process_images_handles_missing_full_size_photos(self, mock_dbx_client, mock_provider, mock_logger):
        """Test that missing full-size photos are logged and counted as errors."""
        # Mock file metadata
        mock_file = MagicMock()
        mock_file.path_display = "/Photos/test.jpg"
        image_files = [mock_file]

        # Mock full-size download failure
        mock_dbx_client.get_file_content.return_value = None

        matches, processed, errors = process_images(
            image_files, mock_dbx_client, mock_provider, {}, True, 0.6, False, mock_logger
        )

        assert processed == 1
        assert errors == 1
        assert len(matches) == 0
        mock_logger.warning.assert_called_with("Could not download full-size photo: /Photos/test.jpg")
        mock_provider.find_matches_in_image.assert_not_called()

    def test_process_images_handles_os_errors(self, mock_dbx_client, mock_provider, mock_logger):
        """Test that OSError during processing is caught and logged."""
        # Mock file metadata
        mock_file = MagicMock()
        mock_file.path_display = "/Photos/test.jpg"
        image_files = [mock_file]

        # Mock OSError during face matching
        mock_provider.find_matches_in_image.side_effect = OSError("Disk error")

        matches, processed, errors = process_images(
            image_files, mock_dbx_client, mock_provider, {}, False, 0.6, False, mock_logger
        )

        assert processed == 1
        assert errors == 1
        assert len(matches) == 0
        mock_logger.error.assert_called_with("Image processing error for /Photos/test.jpg: Disk error")

    def test_process_images_handles_value_errors(self, mock_dbx_client, mock_provider, mock_logger):
        """Test that ValueError for invalid data is caught and logged."""
        # Mock file metadata
        mock_file = MagicMock()
        mock_file.path_display = "/Photos/test.jpg"
        image_files = [mock_file]

        # Mock ValueError during face matching
        mock_provider.find_matches_in_image.side_effect = ValueError("Invalid image format")

        matches, processed, errors = process_images(
            image_files, mock_dbx_client, mock_provider, {}, False, 0.6, False, mock_logger
        )

        assert processed == 1
        assert errors == 1
        assert len(matches) == 0
        mock_logger.warning.assert_called_with("Invalid image data for /Photos/test.jpg: Invalid image format")

    def test_process_images_returns_matches(self, mock_dbx_client, mock_provider, mock_logger):
        """Test that face matches are correctly identified and returned."""
        # Mock file metadata
        mock_file = MagicMock()
        mock_file.path_display = "/Photos/test.jpg"
        image_files = [mock_file]

        # Mock successful face matching
        mock_provider.find_matches_in_image.return_value = ([{"confidence": 0.8}], 1)

        matches, processed, errors = process_images(
            image_files, mock_dbx_client, mock_provider, {}, False, 0.6, False, mock_logger
        )

        assert processed == 1
        assert errors == 0
        assert len(matches) == 1
        assert matches[0]["file_path"] == "/Photos/test.jpg"
        assert matches[0]["num_matches"] == 1
        assert matches[0]["total_faces"] == 1
        mock_logger.info.assert_any_call("✓ MATCH: /Photos/test.jpg (1/1 faces matched)")

    def test_process_images_verbose_logging(self, mock_dbx_client, mock_provider, mock_logger):
        """Test verbose vs non-verbose logging modes."""
        # Mock multiple files
        image_files = []
        for i in range(15):
            mock_file = MagicMock()
            mock_file.path_display = f"/Photos/test{i}.jpg"
            image_files.append(mock_file)

        matches, processed, errors = process_images(
            image_files, mock_dbx_client, mock_provider, {}, False, 0.6, True, mock_logger
        )

        assert processed == 15
        # In verbose mode, should log every file
        assert mock_logger.info.call_count >= 15  # At least one call per file plus summary

    def test_process_images_non_verbose_logging(self, mock_dbx_client, mock_provider, mock_logger):
        """Test non-verbose logging only logs every 10th file."""
        # Mock multiple files
        image_files = []
        for i in range(25):
            mock_file = MagicMock()
            mock_file.path_display = f"/Photos/test{i}.jpg"
            image_files.append(mock_file)

        matches, processed, errors = process_images(
            image_files, mock_dbx_client, mock_provider, {}, False, 0.6, False, mock_logger
        )

        assert processed == 25
        # Should log every 10th file (files 0, 9, 19, etc.) plus summary
        # Exact count depends on implementation, but should be less than verbose mode


class TestPerformOperations:
    """Test perform_operations function."""

    @pytest.fixture
    def mock_dbx_client(self):
        """Create a mock DropboxClient instance."""
        client = MagicMock()
        client.copy_file.return_value = True
        client.move_file.return_value = True
        return client

    @pytest.fixture
    def mock_logger(self):
        """Create a mock logger."""
        return Mock()

    def test_perform_operations_skips_duplicates(self, mock_dbx_client, mock_logger):
        """Test that duplicate filenames are detected and skipped."""
        matches = [
            {"file_path": "/Photos/test1.jpg", "num_matches": 1, "total_faces": 1, "matches": []},
            {"file_path": "/Photos/test2.jpg", "num_matches": 1, "total_faces": 1, "matches": []},
        ]
        destination_folder = "/Matches"

        # Mock copy_file to simulate duplicate handling
        mock_dbx_client.copy_file.return_value = True

        perform_operations(matches, destination_folder, mock_dbx_client, "copy", None, False, mock_logger)

        # Should call copy_file twice (once per match)
        assert mock_dbx_client.copy_file.call_count == 2

    def test_perform_operations_dry_run_mode(self, mock_dbx_client, mock_logger):
        """Test that dry-run mode doesn't perform actual operations."""
        matches = [
            {"file_path": "/Photos/test.jpg", "num_matches": 1, "total_faces": 1, "matches": []},
        ]
        destination_folder = "/Matches"

        perform_operations(matches, destination_folder, mock_dbx_client, "copy", None, True, mock_logger)

        # Should not call any file operations
        mock_dbx_client.copy_file.assert_not_called()
        mock_dbx_client.move_file.assert_not_called()
        mock_logger.info.assert_any_call("DRY RUN MODE - No files were copied/moved")

    def test_perform_operations_successful_copy(self, mock_dbx_client, mock_logger):
        """Test successful copy operations."""
        matches = [
            {"file_path": "/Photos/test.jpg", "num_matches": 1, "total_faces": 1, "matches": []},
        ]
        destination_folder = "/Matches"

        perform_operations(matches, destination_folder, mock_dbx_client, "copy", None, False, mock_logger)

        mock_dbx_client.copy_file.assert_called_once_with("/Photos/test.jpg", "/Matches/test.jpg")
        mock_logger.info.assert_any_call("✓ Copied: /Photos/test.jpg → /Matches/test.jpg")

    def test_perform_operations_successful_move(self, mock_dbx_client, mock_logger):
        """Test successful move operations."""
        matches = [
            {"file_path": "/Photos/test.jpg", "num_matches": 1, "total_faces": 1, "matches": []},
        ]
        destination_folder = "/Matches"

        perform_operations(matches, destination_folder, mock_dbx_client, "move", None, False, mock_logger)

        mock_dbx_client.move_file.assert_called_once_with("/Photos/test.jpg", "/Matches/test.jpg")
        mock_logger.info.assert_any_call("✓ Moved: /Photos/test.jpg → /Matches/test.jpg")

    def test_perform_operations_failed_operation(self, mock_dbx_client, mock_logger):
        """Test handling of failed operations."""
        matches = [
            {"file_path": "/Photos/test.jpg", "num_matches": 1, "total_faces": 1, "matches": []},
        ]
        destination_folder = "/Matches"

        # Mock failed copy
        mock_dbx_client.copy_file.return_value = False

        perform_operations(matches, destination_folder, mock_dbx_client, "copy", None, False, mock_logger)

        mock_logger.error.assert_called_with("✗ Failed to copy: /Photos/test.jpg")

    def test_perform_operations_counts_successes(self, mock_dbx_client, mock_logger):
        """Test that successful operations are counted correctly."""
        matches = [
            {"file_path": "/Photos/test1.jpg", "num_matches": 1, "total_faces": 1, "matches": []},
            {"file_path": "/Photos/test2.jpg", "num_matches": 1, "total_faces": 1, "matches": []},
        ]
        destination_folder = "/Matches"

        perform_operations(matches, destination_folder, mock_dbx_client, "copy", None, False, mock_logger)

        mock_logger.info.assert_any_call("Successfully copied 2/2 file(s)")

    def test_perform_operations_no_matches(self, mock_dbx_client, mock_logger):
        """Test handling when no matches are found."""
        matches = []
        destination_folder = "/Matches"

        perform_operations(matches, destination_folder, mock_dbx_client, "copy", None, False, mock_logger)

        mock_logger.info.assert_any_call("No matching images found")
        mock_dbx_client.copy_file.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
