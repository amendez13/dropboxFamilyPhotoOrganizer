"""Unit tests for organize_photos script functions."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, Mock

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from organize_photos import _sanitize_path_for_logging, perform_operations, process_images  # noqa: E402


class TestSanitizePathForLogging:
    """Test _sanitize_path_for_logging function."""

    def test_sanitizes_control_characters(self):
        """Test that control characters are removed from paths."""
        # Test various control characters
        malicious_path = "/Photos/test\x00\x01\x02\x03.jpg"  # Null and other control chars
        result = _sanitize_path_for_logging(malicious_path)
        assert result == "/Photos/test.jpg"
        assert "\x00" not in result
        assert "\x01" not in result

    def test_sanitizes_newline_characters(self):
        """Test that newline characters are removed (log injection prevention)."""
        malicious_path = "/Photos/test\n.jpg"
        result = _sanitize_path_for_logging(malicious_path)
        assert result == "/Photos/test.jpg"
        assert "\n" not in result

    def test_sanitizes_carriage_return(self):
        """Test that carriage return characters are removed."""
        malicious_path = "/Photos/test\r.jpg"
        result = _sanitize_path_for_logging(malicious_path)
        assert result == "/Photos/test.jpg"
        assert "\r" not in result

    def test_sanitizes_tab_characters(self):
        """Test that tab characters are removed."""
        malicious_path = "/Photos/test\t.jpg"
        result = _sanitize_path_for_logging(malicious_path)
        assert result == "/Photos/test.jpg"
        assert "\t" not in result

    def test_preserves_path_separators(self):
        """Test that path separators are preserved."""
        path_with_separators = "/Photos/Family\\2023\\holiday.jpg"
        result = _sanitize_path_for_logging(path_with_separators)
        assert result == path_with_separators
        assert "/" in result
        assert "\\" in result

    def test_preserves_printable_characters(self):
        """Test that printable characters are preserved."""
        normal_path = "/Photos/Family Vacation 2023 (Summer).jpg"
        result = _sanitize_path_for_logging(normal_path)
        assert result == normal_path

    def test_handles_empty_string(self):
        """Test handling of empty string input."""
        result = _sanitize_path_for_logging("")
        assert result == ""

    def test_handles_unicode_characters(self):
        """Test that Unicode characters outside control range are preserved."""
        path_with_unicode = "/Photos/фото.jpg"
        result = _sanitize_path_for_logging(path_with_unicode)
        assert result == path_with_unicode

    def test_removes_extended_control_characters(self):
        """Test removal of extended control characters (128-159)."""
        malicious_path = "/Photos/test\x80\x9f.jpg"  # Extended control chars
        result = _sanitize_path_for_logging(malicious_path)
        assert result == "/Photos/test.jpg"
        assert "\x80" not in result
        assert "\x9f" not in result

    def test_complex_malicious_path(self):
        """Test sanitization of a complex malicious path with multiple control chars."""
        malicious_path = "/Photos/test\n\r\t\x00\x01\x7f\x80.jpg"
        result = _sanitize_path_for_logging(malicious_path)
        assert result == "/Photos/test.jpg"
        # Ensure no control characters remain
        for char in malicious_path:
            if ord(char) < 32 or (ord(char) >= 127 and ord(char) < 160):
                if char not in "/\\":  # Path separators are allowed
                    assert char not in result


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
        """Test non-verbose logging logs progress less frequently than verbose mode."""
        # Mock multiple files - make them NOT match so we only see progress logs
        image_files = []
        for i in range(25):
            mock_file = MagicMock()
            mock_file.path_display = f"/Photos/test{i}.jpg"
            image_files.append(mock_file)

        # No matches - so we only count progress logging
        mock_provider.find_matches_in_image.return_value = ([], 0)

        matches, processed, errors = process_images(
            image_files, mock_dbx_client, mock_provider, {}, False, 0.6, False, mock_logger
        )

        assert processed == 25
        # In non-verbose mode, progress is logged every 10th file (files 10, 20)
        # Plus 3 header lines = 5 info calls, much less than 25 files
        # Verify that "Processing X/25" appears only for files 10 and 20
        progress_calls = [call for call in mock_logger.info.call_args_list if "Processing" in str(call) and "/" in str(call)]
        assert len(progress_calls) == 2  # Only files 10 and 20


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
        """Test that duplicate filenames from different folders are detected and skipped."""
        # Two files with the SAME filename but in different source folders
        matches = [
            {"file_path": "/Photos/folder1/photo.jpg", "num_matches": 1, "total_faces": 1, "matches": []},
            {"file_path": "/Photos/folder2/photo.jpg", "num_matches": 1, "total_faces": 1, "matches": []},
        ]
        destination_folder = "/Matches"

        mock_dbx_client.copy_file.return_value = True

        perform_operations(matches, destination_folder, mock_dbx_client, "copy", None, False, mock_logger)

        # Should only call copy_file once (second file has duplicate filename)
        assert mock_dbx_client.copy_file.call_count == 1
        mock_dbx_client.copy_file.assert_called_once_with("/Photos/folder1/photo.jpg", "/Matches/photo.jpg")
        # Should log the skipped duplicate
        mock_logger.info.assert_any_call("⊘ Skipped (duplicate filename): /Photos/folder2/photo.jpg")

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
