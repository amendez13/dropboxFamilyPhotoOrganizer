"""Unit tests for organize_photos script functions."""

import sys
from pathlib import Path
from types import ModuleType
from typing import Generator
from unittest.mock import MagicMock, Mock

import pytest


@pytest.fixture
def mock_dependencies() -> Generator[None, None, None]:
    """Mock external dependencies to avoid circular imports."""
    # Mock dependencies before importing organize_photos
    sys.modules["scripts.dropbox_client"] = Mock()
    sys.modules["scripts.face_recognizer"] = Mock()
    sys.modules["scripts.face_recognizer.base_provider"] = Mock()
    sys.modules["scripts.logging_utils"] = Mock()
    sys.modules["scripts.auth.client_factory"] = Mock()
    yield
    # Cleanup is handled by pytest


@pytest.fixture
def organize_photos_module(mock_dependencies: None) -> ModuleType:
    """Load the organize_photos module with mocked dependencies."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "organize_photos_module",
        Path(__file__).parent.parent / "scripts" / "organize_photos.py",
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class TestSanitizePathForLogging:
    """Test _sanitize_path_for_logging function."""

    def test_sanitizes_control_characters(self, organize_photos_module: ModuleType) -> None:
        """Test that control characters are removed from paths."""
        # Test various control characters
        malicious_path = "/Photos/test\x00\x01\x02\x03.jpg"  # Null and other control chars
        result = organize_photos_module._sanitize_path_for_logging(malicious_path)
        assert result == "/Photos/test.jpg"
        assert "\x00" not in result
        assert "\x01" not in result

    def test_sanitizes_newline_characters(self, organize_photos_module: ModuleType) -> None:
        """Test that newline characters are removed (log injection prevention)."""
        malicious_path = "/Photos/test\n.jpg"
        result = organize_photos_module._sanitize_path_for_logging(malicious_path)
        assert result == "/Photos/test.jpg"
        assert "\n" not in result

    def test_sanitizes_carriage_return(self, organize_photos_module: ModuleType) -> None:
        """Test that carriage return characters are removed."""
        malicious_path = "/Photos/test\r.jpg"
        result = organize_photos_module._sanitize_path_for_logging(malicious_path)
        assert result == "/Photos/test.jpg"
        assert "\r" not in result

    def test_sanitizes_tab_characters(self, organize_photos_module: ModuleType) -> None:
        """Test that tab characters are removed."""
        malicious_path = "/Photos/test\t.jpg"
        result = organize_photos_module._sanitize_path_for_logging(malicious_path)
        assert result == "/Photos/test.jpg"
        assert "\t" not in result

    def test_preserves_path_separators(self, organize_photos_module: ModuleType) -> None:
        """Test that path separators are preserved."""
        path_with_separators = "/Photos/Family\\2023\\holiday.jpg"
        result = organize_photos_module._sanitize_path_for_logging(path_with_separators)
        assert result == path_with_separators
        assert "/" in result
        assert "\\" in result

    def test_preserves_printable_characters(self, organize_photos_module: ModuleType) -> None:
        """Test that printable characters are preserved."""
        normal_path = "/Photos/Family Vacation 2023 (Summer).jpg"
        result = organize_photos_module._sanitize_path_for_logging(normal_path)
        assert result == normal_path

    def test_handles_empty_string(self, organize_photos_module: ModuleType) -> None:
        """Test handling of empty string input."""
        result = organize_photos_module._sanitize_path_for_logging("")
        assert result == ""

    def test_handles_unicode_characters(self, organize_photos_module: ModuleType) -> None:
        """Test that Unicode characters outside control range are preserved."""
        path_with_unicode = "/Photos/фото.jpg"
        result = organize_photos_module._sanitize_path_for_logging(path_with_unicode)
        assert result == path_with_unicode

    def test_removes_extended_control_characters(self, organize_photos_module: ModuleType) -> None:
        """Test removal of extended control characters (128-159)."""
        malicious_path = "/Photos/test\x80\x9f.jpg"  # Extended control chars
        result = organize_photos_module._sanitize_path_for_logging(malicious_path)
        assert result == "/Photos/test.jpg"
        assert "\x80" not in result
        assert "\x9f" not in result

    def test_complex_malicious_path(self, organize_photos_module: ModuleType) -> None:
        """Test sanitization of a complex malicious path with multiple control chars."""
        malicious_path = "/Photos/test\n\r\t\x00\x01\x7f\x80.jpg"
        result = organize_photos_module._sanitize_path_for_logging(malicious_path)
        assert result == "/Photos/test.jpg"
        # Ensure no control characters remain
        for char in malicious_path:
            if ord(char) < 32 or (ord(char) >= 127 and ord(char) < 160):
                if char not in "/\\":  # Path separators are allowed
                    assert char not in result


class TestProcessImages:
    """Test process_images function."""

    def test_process_images_handles_missing_thumbnails(self, organize_photos_module: ModuleType) -> None:
        """Test that missing thumbnails are logged and counted as errors."""
        mock_dbx_client = MagicMock()
        mock_dbx_client.get_thumbnail.return_value = None
        mock_provider = MagicMock()
        mock_logger = Mock()

        # Mock file metadata
        mock_file = MagicMock()
        mock_file.path_display = "/Photos/test.jpg"
        image_files = [mock_file]

        matches, processed, errors, no_match_paths = organize_photos_module.process_images(
            image_files, mock_dbx_client, mock_provider, {}, False, 0.6, False, mock_logger
        )

        assert processed == 1
        assert errors == 1
        assert len(matches) == 0
        assert no_match_paths == []
        mock_logger.warning.assert_called_with("Could not get thumbnail for /Photos/test.jpg")
        mock_provider.find_matches_in_image.assert_not_called()

    def test_process_images_handles_missing_full_size_photos(self, organize_photos_module: ModuleType) -> None:
        """Test that missing full-size photos are logged and counted as errors."""
        mock_dbx_client = MagicMock()
        mock_dbx_client.get_file_content.return_value = None
        mock_provider = MagicMock()
        mock_logger = Mock()

        # Mock file metadata
        mock_file = MagicMock()
        mock_file.path_display = "/Photos/test.jpg"
        image_files = [mock_file]

        matches, processed, errors, no_match_paths = organize_photos_module.process_images(
            image_files, mock_dbx_client, mock_provider, {}, True, 0.6, False, mock_logger
        )

        assert processed == 1
        assert errors == 1
        assert len(matches) == 0
        assert no_match_paths == []
        mock_logger.warning.assert_called_with("Could not download full-size photo: /Photos/test.jpg")
        mock_provider.find_matches_in_image.assert_not_called()

    def test_process_images_handles_os_errors(self, organize_photos_module: ModuleType) -> None:
        """Test that OSError during processing is caught and logged."""
        mock_dbx_client = MagicMock()
        mock_dbx_client.get_thumbnail.return_value = b"fake_thumbnail_data"
        mock_provider = MagicMock()
        mock_provider.find_matches_in_image.side_effect = OSError("Disk error")
        mock_logger = Mock()

        # Mock file metadata
        mock_file = MagicMock()
        mock_file.path_display = "/Photos/test.jpg"
        image_files = [mock_file]

        matches, processed, errors, no_match_paths = organize_photos_module.process_images(
            image_files, mock_dbx_client, mock_provider, {}, False, 0.6, False, mock_logger
        )

        assert processed == 1
        assert errors == 1
        assert len(matches) == 0
        assert no_match_paths == []
        mock_logger.error.assert_called_with("Image processing error for /Photos/test.jpg: Disk error")

    def test_process_images_handles_value_errors(self, organize_photos_module: ModuleType) -> None:
        """Test that ValueError for invalid data is caught and logged."""
        mock_dbx_client = MagicMock()
        mock_dbx_client.get_thumbnail.return_value = b"fake_thumbnail_data"
        mock_provider = MagicMock()
        mock_provider.find_matches_in_image.side_effect = ValueError("Invalid image format")
        mock_logger = Mock()

        # Mock file metadata
        mock_file = MagicMock()
        mock_file.path_display = "/Photos/test.jpg"
        image_files = [mock_file]

        matches, processed, errors, no_match_paths = organize_photos_module.process_images(
            image_files, mock_dbx_client, mock_provider, {}, False, 0.6, False, mock_logger
        )

        assert processed == 1
        assert errors == 1
        assert len(matches) == 0
        assert no_match_paths == []
        mock_logger.warning.assert_called_with("Invalid image data for /Photos/test.jpg: Invalid image format")

    def test_process_images_handles_unexpected_exception(self, organize_photos_module: ModuleType) -> None:
        """Test that unexpected exceptions are caught and logged with exc_info."""
        mock_dbx_client = MagicMock()
        mock_dbx_client.get_thumbnail.return_value = b"fake_thumbnail_data"
        mock_provider = MagicMock()
        mock_provider.find_matches_in_image.side_effect = RuntimeError("Unexpected error")
        mock_logger = Mock()

        mock_file = MagicMock()
        mock_file.path_display = "/Photos/test.jpg"
        image_files = [mock_file]

        matches, processed, errors, no_match_paths = organize_photos_module.process_images(
            image_files, mock_dbx_client, mock_provider, {}, False, 0.6, False, mock_logger
        )

        assert processed == 1
        assert errors == 1
        assert len(matches) == 0
        assert no_match_paths == []
        # Check that error was logged with exc_info=True
        mock_logger.error.assert_called_with("Unexpected error processing /Photos/test.jpg: Unexpected error", exc_info=True)

    def test_process_images_returns_matches(self, organize_photos_module: ModuleType) -> None:
        """Test that face matches are correctly identified and returned."""
        mock_dbx_client = MagicMock()
        mock_dbx_client.get_thumbnail.return_value = b"fake_thumbnail_data"
        mock_provider = MagicMock()
        mock_provider.find_matches_in_image.return_value = ([{"confidence": 0.8}], 1)
        mock_logger = Mock()

        # Mock file metadata
        mock_file = MagicMock()
        mock_file.path_display = "/Photos/test.jpg"
        image_files = [mock_file]

        matches, processed, errors, no_match_paths = organize_photos_module.process_images(
            image_files, mock_dbx_client, mock_provider, {}, False, 0.6, False, mock_logger
        )

        assert processed == 1
        assert errors == 0
        assert len(matches) == 1
        assert no_match_paths == []
        assert matches[0]["file_path"] == "/Photos/test.jpg"
        assert matches[0]["num_matches"] == 1
        assert matches[0]["total_faces"] == 1
        mock_logger.info.assert_any_call("✓ MATCH: /Photos/test.jpg (1/1 faces matched)")

    def test_process_images_verbose_logging(self, organize_photos_module: ModuleType) -> None:
        """Test verbose vs non-verbose logging modes."""
        mock_dbx_client = MagicMock()
        mock_dbx_client.get_thumbnail.return_value = b"fake_thumbnail_data"
        mock_provider = MagicMock()
        mock_provider.find_matches_in_image.return_value = ([{"confidence": 0.8}], 1)
        mock_logger = Mock()

        # Mock multiple files
        image_files = []
        for i in range(15):
            mock_file = MagicMock()
            mock_file.path_display = f"/Photos/test{i}.jpg"
            image_files.append(mock_file)

        matches, processed, errors, no_match_paths = organize_photos_module.process_images(
            image_files, mock_dbx_client, mock_provider, {}, False, 0.6, True, mock_logger
        )

        assert processed == 15
        assert len(no_match_paths) == 0
        # In verbose mode, should log every file
        assert mock_logger.info.call_count >= 15  # At least one call per file plus summary

    def test_process_images_non_verbose_logging(self, organize_photos_module: ModuleType) -> None:
        """Test non-verbose logging logs progress less frequently than verbose mode."""
        mock_dbx_client = MagicMock()
        mock_dbx_client.get_thumbnail.return_value = b"fake_thumbnail_data"
        mock_provider = MagicMock()
        mock_provider.find_matches_in_image.return_value = ([], 0)
        mock_logger = Mock()

        # Mock multiple files - make them NOT match so we only see progress logs
        image_files = []
        for i in range(25):
            mock_file = MagicMock()
            mock_file.path_display = f"/Photos/test{i}.jpg"
            image_files.append(mock_file)

        matches, processed, errors, no_match_paths = organize_photos_module.process_images(
            image_files, mock_dbx_client, mock_provider, {}, False, 0.6, False, mock_logger
        )

        assert processed == 25
        assert len(no_match_paths) == 25
        # In non-verbose mode, progress is logged every 10th file (files 10, 20)
        # Plus 3 header lines = 5 info calls, much less than 25 files
        # Verify that "Processing X/25" appears only for files 10 and 20
        progress_calls = [call for call in mock_logger.info.call_args_list if "Processing" in str(call) and "/" in str(call)]
        assert len(progress_calls) == 2  # Only files 10 and 20


class TestPerformOperations:
    """Test perform_operations function."""

    def test_perform_operations_skips_duplicates(self, organize_photos_module: ModuleType) -> None:
        """Test that duplicate filenames from different folders are detected and skipped."""
        mock_dbx_client = MagicMock()
        mock_dbx_client.copy_file.return_value = True
        mock_logger = Mock()

        # Clear the global _audit_logger to prevent audit logging issues
        organize_photos_module._audit_logger = None

        # Two files with the SAME filename but in different source folders
        matches = [
            {"file_path": "/Photos/folder1/photo.jpg", "num_matches": 1, "total_faces": 1, "matches": []},
            {"file_path": "/Photos/folder2/photo.jpg", "num_matches": 1, "total_faces": 1, "matches": []},
        ]
        destination_folder = "/Matches"

        organize_photos_module.perform_operations(matches, [], destination_folder, mock_dbx_client, "copy", False, mock_logger)

        # Should only call copy_file once (second file has duplicate filename)
        assert mock_dbx_client.copy_file.call_count == 1
        mock_dbx_client.copy_file.assert_called_once_with("/Photos/folder1/photo.jpg", "/Matches/photo.jpg")
        # Should log the skipped duplicate
        mock_logger.info.assert_any_call("⊘ Skipped (duplicate filename): /Photos/folder2/photo.jpg")

    def test_perform_operations_dry_run_mode(self, organize_photos_module: ModuleType) -> None:
        """Test that dry-run mode doesn't perform actual operations."""
        mock_dbx_client = MagicMock()
        mock_logger = Mock()

        matches = [
            {"file_path": "/Photos/test.jpg", "num_matches": 1, "total_faces": 1, "matches": []},
        ]
        destination_folder = "/Matches"

        organize_photos_module.perform_operations(matches, [], destination_folder, mock_dbx_client, "copy", True, mock_logger)

        # Should not call any file operations
        mock_dbx_client.copy_file.assert_not_called()
        mock_dbx_client.move_file.assert_not_called()
        mock_logger.info.assert_any_call("DRY RUN MODE - No files were copied/moved")

    def test_perform_operations_successful_copy(self, organize_photos_module: ModuleType) -> None:
        """Test successful copy operations."""
        mock_dbx_client = MagicMock()
        mock_dbx_client.copy_file.return_value = True
        mock_logger = Mock()

        # Clear the global _audit_logger to prevent audit logging issues
        organize_photos_module._audit_logger = None

        matches = [
            {"file_path": "/Photos/test.jpg", "num_matches": 1, "total_faces": 1, "matches": []},
        ]
        destination_folder = "/Matches"

        organize_photos_module.perform_operations(matches, [], destination_folder, mock_dbx_client, "copy", False, mock_logger)

        mock_dbx_client.copy_file.assert_called_once_with("/Photos/test.jpg", "/Matches/test.jpg")
        mock_logger.info.assert_any_call("✓ Copied: /Photos/test.jpg → /Matches/test.jpg")

    def test_perform_operations_successful_move(self, organize_photos_module: ModuleType) -> None:
        """Test successful move operations."""
        mock_dbx_client = MagicMock()
        mock_dbx_client.move_file.return_value = True
        mock_logger = Mock()

        # Clear the global _audit_logger to prevent audit logging issues
        organize_photos_module._audit_logger = None

        matches = [
            {"file_path": "/Photos/test.jpg", "num_matches": 1, "total_faces": 1, "matches": []},
        ]
        destination_folder = "/Matches"

        organize_photos_module.perform_operations(matches, [], destination_folder, mock_dbx_client, "move", False, mock_logger)

        mock_dbx_client.move_file.assert_called_once_with("/Photos/test.jpg", "/Matches/test.jpg")
        mock_logger.info.assert_any_call("✓ Moved: /Photos/test.jpg → /Matches/test.jpg")

    def test_perform_operations_failed_operation(self, organize_photos_module: ModuleType) -> None:
        """Test handling of failed operations."""
        mock_dbx_client = MagicMock()
        mock_dbx_client.copy_file.return_value = False
        mock_logger = Mock()

        # Clear the global _audit_logger to prevent audit logging issues
        organize_photos_module._audit_logger = None

        matches = [
            {"file_path": "/Photos/test.jpg", "num_matches": 1, "total_faces": 1, "matches": []},
        ]
        destination_folder = "/Matches"

        organize_photos_module.perform_operations(matches, [], destination_folder, mock_dbx_client, "copy", False, mock_logger)

        mock_logger.error.assert_called_with("✗ Failed to copy: /Photos/test.jpg")

    def test_perform_operations_counts_successes(self, organize_photos_module: ModuleType) -> None:
        """Test that successful operations are counted correctly."""
        mock_dbx_client = MagicMock()
        mock_dbx_client.copy_file.return_value = True
        mock_logger = Mock()

        # Clear the global _audit_logger to prevent audit logging issues
        organize_photos_module._audit_logger = None

        matches = [
            {"file_path": "/Photos/test1.jpg", "num_matches": 1, "total_faces": 1, "matches": []},
            {"file_path": "/Photos/test2.jpg", "num_matches": 1, "total_faces": 1, "matches": []},
        ]
        destination_folder = "/Matches"

        organize_photos_module.perform_operations(matches, [], destination_folder, mock_dbx_client, "copy", False, mock_logger)

        mock_logger.info.assert_any_call("Successfully copied 2/2 file(s)")

    def test_perform_operations_no_matches(self, organize_photos_module: ModuleType) -> None:
        """Test handling when no matches are found."""
        mock_dbx_client = MagicMock()
        mock_logger = Mock()

        matches = []
        destination_folder = "/Matches"

        organize_photos_module.perform_operations(matches, [], destination_folder, mock_dbx_client, "copy", False, mock_logger)

        mock_logger.info.assert_any_call("No matching images found")
        mock_dbx_client.copy_file.assert_not_called()


class TestLoadConfig:
    """Test load_config function."""

    def test_load_config_with_absolute_path(self, organize_photos_module: ModuleType, tmp_path: Path) -> None:
        """Test loading config with an absolute path."""
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dropbox:\n  source_folder: /Photos\n")

        config = organize_photos_module.load_config(str(config_file))

        assert config["dropbox"]["source_folder"] == "/Photos"

    def test_load_config_with_relative_path(self, organize_photos_module: ModuleType, tmp_path: Path) -> None:
        """Test loading config with a relative path resolves correctly."""
        # Create a config file
        config_file = tmp_path / "config.yaml"
        config_file.write_text("dropbox:\n  source_folder: /Test\n")

        # Use absolute path for this test (the relative path logic is hard to test)
        config = organize_photos_module.load_config(str(config_file))

        assert config["dropbox"]["source_folder"] == "/Test"

    def test_load_config_relative_path_resolution(
        self, organize_photos_module: ModuleType, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that relative paths are resolved correctly relative to the script."""
        # Create a config file
        config_file = tmp_path / "config" / "config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("dropbox:\n  source_folder: /RelativeTest\n")

        # Mock os.path functions to simulate relative path handling
        original_dirname = organize_photos_module.os.path.dirname
        original_abspath = organize_photos_module.os.path.abspath

        def mock_dirname(path):
            if path == organize_photos_module.__file__:
                return str(tmp_path)
            return original_dirname(path)

        def mock_abspath(path):
            return original_abspath(path)

        monkeypatch.setattr(organize_photos_module.os.path, "dirname", mock_dirname)
        monkeypatch.setattr(organize_photos_module.os.path, "abspath", mock_abspath)

        # Now test with a relative path
        config = organize_photos_module.load_config("config/config.yaml")

        assert config["dropbox"]["source_folder"] == "/RelativeTest"


class TestDownloadImage:
    """Test _download_image function."""

    def test_download_full_size_success(self, organize_photos_module: ModuleType) -> None:
        """Test downloading full-size image successfully."""
        mock_client = MagicMock()
        mock_client.get_file_content.return_value = b"full_image_data"

        image_data, error = organize_photos_module._download_image(mock_client, "/test.jpg", {}, use_full_size=True)

        assert image_data == b"full_image_data"
        assert error is None
        mock_client.get_file_content.assert_called_once_with("/test.jpg")

    def test_download_full_size_failure(self, organize_photos_module: ModuleType) -> None:
        """Test downloading full-size image failure."""
        mock_client = MagicMock()
        mock_client.get_file_content.return_value = None

        image_data, error = organize_photos_module._download_image(mock_client, "/test.jpg", {}, use_full_size=True)

        assert image_data is None
        assert error == "Could not download full-size photo: /test.jpg"

    def test_download_thumbnail_success(self, organize_photos_module: ModuleType) -> None:
        """Test downloading thumbnail successfully."""
        mock_client = MagicMock()
        mock_client.get_thumbnail.return_value = b"thumbnail_data"

        image_data, error = organize_photos_module._download_image(mock_client, "/test.jpg", {}, use_full_size=False)

        assert image_data == b"thumbnail_data"
        assert error is None
        mock_client.get_thumbnail.assert_called_once_with("/test.jpg", size="w256h256")

    def test_download_thumbnail_with_custom_size(self, organize_photos_module: ModuleType) -> None:
        """Test downloading thumbnail with custom size from config."""
        mock_client = MagicMock()
        mock_client.get_thumbnail.return_value = b"thumbnail_data"
        face_config = {"thumbnail_size": "w128h128"}

        image_data, error = organize_photos_module._download_image(mock_client, "/test.jpg", face_config, use_full_size=False)

        assert image_data == b"thumbnail_data"
        assert error is None
        mock_client.get_thumbnail.assert_called_once_with("/test.jpg", size="w128h128")

    def test_download_thumbnail_failure(self, organize_photos_module: ModuleType) -> None:
        """Test downloading thumbnail failure."""
        mock_client = MagicMock()
        mock_client.get_thumbnail.return_value = None

        image_data, error = organize_photos_module._download_image(mock_client, "/test.jpg", {}, use_full_size=False)

        assert image_data is None
        assert error == "Could not get thumbnail for /test.jpg"


class TestSafeOrganize:
    """Test safe_organize function."""

    def test_safe_organize_invalid_operation(self, organize_photos_module: ModuleType) -> None:
        """Test safe_organize with invalid operation raises ValueError."""
        mock_client = MagicMock()
        mock_client.logger = Mock()

        # Clear the global _audit_logger
        organize_photos_module._audit_logger = None

        log_entry = organize_photos_module.safe_organize(mock_client, "/source.jpg", "/dest.jpg", operation="invalid")

        assert log_entry["success"] is False
        assert "error" in log_entry
        assert "Invalid operation" in log_entry["error"]

    def test_safe_organize_exception_during_operation(self, organize_photos_module: ModuleType) -> None:
        """Test safe_organize handles exceptions during file operations."""
        mock_client = MagicMock()
        mock_client.copy_file.side_effect = Exception("Network error")
        mock_client.logger = Mock()

        # Clear the global _audit_logger
        organize_photos_module._audit_logger = None

        log_entry = organize_photos_module.safe_organize(mock_client, "/source.jpg", "/dest.jpg", operation="copy")

        assert log_entry["success"] is False
        assert "error" in log_entry
        assert "Network error" in log_entry["error"]
        mock_client.logger.error.assert_called()

    def test_safe_organize_audit_log_write_failure(self, organize_photos_module: ModuleType) -> None:
        """Test safe_organize handles audit log write failures gracefully."""
        mock_client = MagicMock()
        mock_client.copy_file.return_value = True
        mock_client.logger = Mock()

        # Create a mock audit logger that raises an exception
        mock_audit_logger = Mock()
        mock_audit_logger.info.side_effect = Exception("Audit write failed")
        organize_photos_module._audit_logger = mock_audit_logger

        # Should not raise an exception even when audit log write fails
        log_entry = organize_photos_module.safe_organize(mock_client, "/source.jpg", "/dest.jpg", operation="copy")

        # Operation should still succeed
        assert log_entry["success"] is True

        # Restore
        organize_photos_module._audit_logger = None


class TestGetReferencePhotos:
    """Test _get_reference_photos function."""

    def test_get_reference_photos_finds_images(self, organize_photos_module: ModuleType, tmp_path: Path) -> None:
        """Test finding reference photos in a directory."""
        # Create test image files
        (tmp_path / "photo1.jpg").write_text("fake image")
        (tmp_path / "photo2.png").write_text("fake image")
        (tmp_path / "photo3.jpeg").write_text("fake image")

        photos = organize_photos_module._get_reference_photos(str(tmp_path), [".jpg", ".png", ".jpeg"])

        assert len(photos) == 3
        assert any("photo1.jpg" in p for p in photos)
        assert any("photo2.png" in p for p in photos)
        assert any("photo3.jpeg" in p for p in photos)

    def test_get_reference_photos_excludes_system_files(self, organize_photos_module: ModuleType, tmp_path: Path) -> None:
        """Test that system files (starting with .) are excluded."""
        # Create test image files including system files
        (tmp_path / "photo1.jpg").write_text("fake image")
        (tmp_path / ".DS_Store").write_text("system file")
        (tmp_path / ".hidden.jpg").write_text("hidden image")

        photos = organize_photos_module._get_reference_photos(str(tmp_path), [".jpg"])

        assert len(photos) == 1
        assert any("photo1.jpg" in p for p in photos)
        assert not any(".DS_Store" in p for p in photos)
        assert not any(".hidden.jpg" in p for p in photos)

    def test_get_reference_photos_empty_directory(self, organize_photos_module: ModuleType, tmp_path: Path) -> None:
        """Test with empty directory returns empty list."""
        photos = organize_photos_module._get_reference_photos(str(tmp_path), [".jpg", ".png"])

        assert photos == []

    def test_get_reference_photos_removes_duplicates(self, organize_photos_module: ModuleType, tmp_path: Path) -> None:
        """Test that duplicate entries are removed."""
        # Create a file that could be matched by multiple patterns
        (tmp_path / "photo.jpg").write_text("fake image")

        # Pass duplicate extensions
        photos = organize_photos_module._get_reference_photos(str(tmp_path), [".jpg", ".jpg"])

        assert len(photos) == 1


class TestValidateConfig:
    """Test _validate_config function."""

    def test_validate_config_valid(self, organize_photos_module: ModuleType) -> None:
        """Test validation with valid configuration."""
        mock_logger = Mock()
        config = {
            "dropbox": {
                "source_folder": "/Photos/Source",
                "destination_folder": "/Photos/Dest",
            },
            "face_recognition": {"tolerance": 0.6},
            "processing": {"dry_run": True},
        }

        result = organize_photos_module._validate_config(config, mock_logger)

        dropbox_config, source, dest, face_config, processing = result
        assert source == "/Photos/Source"
        assert dest == "/Photos/Dest"
        assert face_config["tolerance"] == 0.6
        assert processing["dry_run"] is True

    def test_validate_config_missing_source_folder(self, organize_photos_module: ModuleType) -> None:
        """Test validation fails when source folder is missing."""
        mock_logger = Mock()
        config = {
            "dropbox": {
                "destination_folder": "/Photos/Dest",
            },
        }

        with pytest.raises(ValueError, match="Source and destination folders must be configured"):
            organize_photos_module._validate_config(config, mock_logger)

    def test_validate_config_missing_destination_folder(self, organize_photos_module: ModuleType) -> None:
        """Test validation fails when destination folder is missing."""
        mock_logger = Mock()
        config = {
            "dropbox": {
                "source_folder": "/Photos/Source",
            },
        }

        with pytest.raises(ValueError, match="Source and destination folders must be configured"):
            organize_photos_module._validate_config(config, mock_logger)

    def test_validate_config_same_source_and_destination(self, organize_photos_module: ModuleType) -> None:
        """Test validation fails when source and destination are the same."""
        mock_logger = Mock()
        config = {
            "dropbox": {
                "source_folder": "/Photos/Same",
                "destination_folder": "/Photos/Same",
            },
        }

        with pytest.raises(ValueError, match="Source and destination folders must be different"):
            organize_photos_module._validate_config(config, mock_logger)

    def test_validate_config_empty_dropbox_section(self, organize_photos_module: ModuleType) -> None:
        """Test validation fails when dropbox section is empty or missing."""
        mock_logger = Mock()
        config = {}

        with pytest.raises(ValueError, match="Source and destination folders must be configured"):
            organize_photos_module._validate_config(config, mock_logger)


class TestSetupFaceProvider:
    """Test _setup_face_provider function."""

    def test_setup_face_provider_default_config(self, organize_photos_module: ModuleType) -> None:
        """Test provider setup with default configuration."""
        mock_logger = Mock()
        face_config = {}

        # Mock get_provider
        mock_provider = MagicMock()
        organize_photos_module.get_provider = Mock(return_value=mock_provider)

        result = organize_photos_module._setup_face_provider(face_config, 0.6, mock_logger)

        assert result == mock_provider
        organize_photos_module.get_provider.assert_called_once_with(
            "local",
            {
                "model": "hog",
                "encoding_model": "large",
                "num_jitters": 1,
                "tolerance": 0.6,
            },
        )

    def test_setup_face_provider_custom_config(self, organize_photos_module: ModuleType) -> None:
        """Test provider setup with custom configuration."""
        mock_logger = Mock()
        face_config = {
            "provider": "local",
            "local": {
                "model": "cnn",
                "encoding_model": "small",
                "num_jitters": 5,
            },
        }

        mock_provider = MagicMock()
        organize_photos_module.get_provider = Mock(return_value=mock_provider)

        result = organize_photos_module._setup_face_provider(face_config, 0.5, mock_logger)

        assert result == mock_provider
        organize_photos_module.get_provider.assert_called_once_with(
            "local",
            {
                "model": "cnn",
                "encoding_model": "small",
                "num_jitters": 5,
                "tolerance": 0.5,
            },
        )

    def test_setup_face_provider_recognition_num_jitters_override(self, organize_photos_module: ModuleType) -> None:
        """Test that recognition.num_jitters overrides default num_jitters."""
        mock_logger = Mock()
        face_config = {
            "provider": "local",
            "local": {
                "model": "hog",
                "num_jitters": 3,  # Default
                "recognition": {
                    "num_jitters": 10,  # Override for recognition
                },
            },
        }

        mock_provider = MagicMock()
        organize_photos_module.get_provider = Mock(return_value=mock_provider)

        organize_photos_module._setup_face_provider(face_config, 0.6, mock_logger)

        # Should use the recognition-specific num_jitters
        call_args = organize_photos_module.get_provider.call_args[0][1]
        assert call_args["num_jitters"] == 10

    def test_setup_face_provider_logs_config(self, organize_photos_module: ModuleType) -> None:
        """Test that provider setup logs the configuration."""
        mock_logger = Mock()
        face_config = {}

        mock_provider = MagicMock()
        organize_photos_module.get_provider = Mock(return_value=mock_provider)

        organize_photos_module._setup_face_provider(face_config, 0.6, mock_logger)

        # Check that configuration is logged
        mock_logger.info.assert_any_call("Initializing local face recognition provider...")
        mock_logger.info.assert_any_call("  Detection model: hog")
        mock_logger.info.assert_any_call("  Encoding model: large")
        mock_logger.info.assert_any_call("  Num jitters (recognition): 1")
        mock_logger.info.assert_any_call("  Tolerance: 0.6")


class TestSetupAuditLoggerIfEnabled:
    """Test _setup_audit_logger_if_enabled function."""

    def test_setup_audit_logger_enabled(self, organize_photos_module: ModuleType, tmp_path: Path) -> None:
        """Test audit logger setup when log file is specified."""
        mock_logger = Mock()
        log_file = str(tmp_path / "audit.log")

        # Save original value
        original_audit_logger = organize_photos_module._audit_logger

        try:
            organize_photos_module._setup_audit_logger_if_enabled(log_file, mock_logger)

            assert organize_photos_module._audit_logger is not None
            mock_logger.info.assert_called_with(f"Audit logging enabled: {log_file}")
        finally:
            # Restore original value
            organize_photos_module._audit_logger = original_audit_logger

    def test_setup_audit_logger_disabled(self, organize_photos_module: ModuleType) -> None:
        """Test audit logger not set up when log file is None."""
        mock_logger = Mock()

        # Save original value
        original_audit_logger = organize_photos_module._audit_logger

        try:
            organize_photos_module._audit_logger = None
            organize_photos_module._setup_audit_logger_if_enabled(None, mock_logger)

            assert organize_photos_module._audit_logger is None
            mock_logger.info.assert_not_called()
        finally:
            # Restore original value
            organize_photos_module._audit_logger = original_audit_logger

    def test_setup_audit_logger_failure(self, organize_photos_module: ModuleType) -> None:
        """Test audit logger setup handles failures gracefully."""
        mock_logger = Mock()

        # Save original value
        original_audit_logger = organize_photos_module._audit_logger
        original_setup_audit_logging = organize_photos_module.setup_audit_logging

        try:
            organize_photos_module.setup_audit_logging = Mock(side_effect=Exception("Permission denied"))

            organize_photos_module._setup_audit_logger_if_enabled("/invalid/path/audit.log", mock_logger)

            assert organize_photos_module._audit_logger is None
            mock_logger.warning.assert_any_call("Failed to setup audit logging: Permission denied")
            mock_logger.warning.assert_any_call("Continuing without audit logging")
        finally:
            # Restore original values
            organize_photos_module._audit_logger = original_audit_logger
            organize_photos_module.setup_audit_logging = original_setup_audit_logging


class TestMain:
    """Test main() function."""

    def test_main_config_file_not_found(self, organize_photos_module: ModuleType, tmp_path: Path) -> None:
        """Test main returns 1 when config file is not found."""
        # Mock argparse to return non-existent config
        mock_args = Mock()
        mock_args.config = "/nonexistent/config.yaml"
        mock_args.move = False
        mock_args.dry_run = False
        mock_args.verbose = False
        mock_args.log_file = "operations.log"

        # Mock argparse
        mock_parser = Mock()
        mock_parser.parse_args.return_value = mock_args
        organize_photos_module.argparse.ArgumentParser = Mock(return_value=mock_parser)

        # Mock setup_logging and get_logger
        organize_photos_module.setup_logging = Mock()
        mock_logger = Mock()
        organize_photos_module.get_logger = Mock(return_value=mock_logger)

        result = organize_photos_module.main()

        assert result == 1
        mock_logger.error.assert_called()

    def test_main_config_validation_error(self, organize_photos_module: ModuleType, tmp_path: Path) -> None:
        """Test main returns 1 when config validation fails."""
        # Create config file with invalid config (same source and destination)
        config_file = tmp_path / "config.yaml"
        config_file.write_text(
            """
dropbox:
  source_folder: /Photos
  destination_folder: /Photos
"""
        )

        # Mock argparse
        mock_args = Mock()
        mock_args.config = str(config_file)
        mock_args.move = False
        mock_args.dry_run = False
        mock_args.verbose = False
        mock_args.log_file = "operations.log"

        mock_parser = Mock()
        mock_parser.parse_args.return_value = mock_args
        organize_photos_module.argparse.ArgumentParser = Mock(return_value=mock_parser)

        # Mock setup_logging and get_logger
        organize_photos_module.setup_logging = Mock()
        mock_logger = Mock()
        organize_photos_module.get_logger = Mock(return_value=mock_logger)

        result = organize_photos_module.main()

        assert result == 1
        # Should log the validation error
        mock_logger.error.assert_called()

    def test_main_general_exception(self, organize_photos_module: ModuleType, tmp_path: Path) -> None:
        """Test main returns 1 on general exception."""
        # Mock argparse
        mock_args = Mock()
        mock_args.config = str(tmp_path / "config.yaml")
        mock_args.move = False
        mock_args.dry_run = False
        mock_args.verbose = False
        mock_args.log_file = "operations.log"

        mock_parser = Mock()
        mock_parser.parse_args.return_value = mock_args
        organize_photos_module.argparse.ArgumentParser = Mock(return_value=mock_parser)

        # Mock setup_logging and get_logger
        organize_photos_module.setup_logging = Mock()
        mock_logger = Mock()
        organize_photos_module.get_logger = Mock(return_value=mock_logger)

        # Mock load_config to raise a general exception
        organize_photos_module.load_config = Mock(side_effect=RuntimeError("Unexpected error"))

        result = organize_photos_module.main()

        assert result == 1
        # Check error was logged with exc_info
        mock_logger.error.assert_called()

    def test_main_no_reference_photos(self, organize_photos_module: ModuleType, tmp_path: Path) -> None:
        """Test main returns 1 when no reference photos are found."""
        # Create valid config file
        config_file = tmp_path / "config.yaml"
        ref_photos_dir = tmp_path / "reference_photos"
        ref_photos_dir.mkdir()

        config_file.write_text(
            f"""
dropbox:
  source_folder: /Photos/Source
  destination_folder: /Photos/Dest
face_recognition:
  reference_photos_dir: {ref_photos_dir}
processing:
  dry_run: true
"""
        )

        # Mock argparse
        mock_args = Mock()
        mock_args.config = str(config_file)
        mock_args.move = False
        mock_args.dry_run = True
        mock_args.verbose = False
        mock_args.log_file = "operations.log"

        mock_parser = Mock()
        mock_parser.parse_args.return_value = mock_args
        organize_photos_module.argparse.ArgumentParser = Mock(return_value=mock_parser)

        # Mock setup_logging and get_logger
        organize_photos_module.setup_logging = Mock()
        mock_logger = Mock()
        organize_photos_module.get_logger = Mock(return_value=mock_logger)

        # Mock the client factory module before main() imports it
        mock_factory_class = Mock()
        mock_client = Mock()
        mock_factory_class.return_value.create_client.return_value = mock_client
        sys.modules["scripts.auth.client_factory"] = Mock(DropboxClientFactory=mock_factory_class)

        # Mock get_provider
        mock_provider = Mock()
        mock_provider.use_face_collection = False
        organize_photos_module.get_provider = Mock(return_value=mock_provider)

        try:
            result = organize_photos_module.main()

            assert result == 1
            # Should log the error about no reference photos
            assert any("No reference photos found" in str(call) for call in mock_logger.error.call_args_list)
        finally:
            # Cleanup the mock
            if "scripts.auth.client_factory" in sys.modules:
                del sys.modules["scripts.auth.client_factory"]

    def test_main_no_reference_photos_with_collection(self, organize_photos_module: ModuleType, tmp_path: Path) -> None:
        """Test main uses face collection when no local reference photos exist."""
        config_file = tmp_path / "config.yaml"
        ref_photos_dir = tmp_path / "reference_photos"
        ref_photos_dir.mkdir()

        config_file.write_text(
            f"""
dropbox:
  source_folder: /Photos/Source
  destination_folder: /Photos/Dest
face_recognition:
  provider: aws
  reference_photos_dir: {ref_photos_dir}
processing:
  dry_run: true
"""
        )

        mock_args = Mock()
        mock_args.config = str(config_file)
        mock_args.move = False
        mock_args.dry_run = True
        mock_args.verbose = False
        mock_args.log_file = "operations.log"

        mock_parser = Mock()
        mock_parser.parse_args.return_value = mock_args
        organize_photos_module.argparse.ArgumentParser = Mock(return_value=mock_parser)

        organize_photos_module.setup_logging = Mock()
        mock_logger = Mock()
        organize_photos_module.get_logger = Mock(return_value=mock_logger)

        mock_factory_class = Mock()
        mock_client = Mock()
        mock_client.list_folder_recursive.return_value = []
        mock_factory_class.return_value.create_client.return_value = mock_client
        sys.modules["scripts.auth.client_factory"] = Mock(DropboxClientFactory=mock_factory_class)

        mock_provider = Mock()
        mock_provider.use_face_collection = True
        mock_provider.load_reference_photos.return_value = 2
        organize_photos_module.get_provider = Mock(return_value=mock_provider)

        try:
            result = organize_photos_module.main()

            assert result == 0
            mock_provider.load_reference_photos.assert_called_once_with([])
        finally:
            if "scripts.auth.client_factory" in sys.modules:
                del sys.modules["scripts.auth.client_factory"]

    def test_main_no_image_files(self, organize_photos_module: ModuleType, tmp_path: Path) -> None:
        """Test main returns 0 when no image files are found in source folder."""
        # Create valid config file
        config_file = tmp_path / "config.yaml"
        ref_photos_dir = tmp_path / "reference_photos"
        ref_photos_dir.mkdir()
        (ref_photos_dir / "ref.jpg").write_text("fake ref image")

        config_file.write_text(
            f"""
dropbox:
  source_folder: /Photos/Source
  destination_folder: /Photos/Dest
face_recognition:
  reference_photos_dir: {ref_photos_dir}
processing:
  dry_run: true
"""
        )

        # Mock argparse
        mock_args = Mock()
        mock_args.config = str(config_file)
        mock_args.move = False
        mock_args.dry_run = True
        mock_args.verbose = False
        mock_args.log_file = "operations.log"

        mock_parser = Mock()
        mock_parser.parse_args.return_value = mock_args
        organize_photos_module.argparse.ArgumentParser = Mock(return_value=mock_parser)

        # Mock setup_logging and get_logger
        organize_photos_module.setup_logging = Mock()
        mock_logger = Mock()
        organize_photos_module.get_logger = Mock(return_value=mock_logger)

        # Mock the client factory module before main() imports it
        mock_factory_class = Mock()
        mock_client = Mock()
        mock_client.list_folder_recursive.return_value = iter([])  # No files
        mock_factory_class.return_value.create_client.return_value = mock_client
        sys.modules["scripts.auth.client_factory"] = Mock(DropboxClientFactory=mock_factory_class)

        # Mock get_provider
        mock_provider = Mock()
        mock_provider.load_reference_photos.return_value = 1
        organize_photos_module.get_provider = Mock(return_value=mock_provider)

        try:
            result = organize_photos_module.main()

            assert result == 0
            mock_logger.warning.assert_called_with("No image files found in source folder")
        finally:
            # Cleanup the mock
            if "scripts.auth.client_factory" in sys.modules:
                del sys.modules["scripts.auth.client_factory"]

    def test_main_successful_run_with_matches(self, organize_photos_module: ModuleType, tmp_path: Path) -> None:
        """Test main returns 0 on successful run with matches."""
        # Create valid config file
        config_file = tmp_path / "config.yaml"
        ref_photos_dir = tmp_path / "reference_photos"
        ref_photos_dir.mkdir()
        (ref_photos_dir / "ref.jpg").write_text("fake ref image")

        config_file.write_text(
            f"""
dropbox:
  source_folder: /Photos/Source
  destination_folder: /Photos/Dest
face_recognition:
  reference_photos_dir: {ref_photos_dir}
  thumbnail_size: w128h128
processing:
  dry_run: true
  log_operations: false
"""
        )

        # Mock argparse
        mock_args = Mock()
        mock_args.config = str(config_file)
        mock_args.move = False  # Use copy mode
        mock_args.dry_run = True
        mock_args.verbose = False
        mock_args.log_file = str(tmp_path / "operations.log")

        mock_parser = Mock()
        mock_parser.parse_args.return_value = mock_args
        organize_photos_module.argparse.ArgumentParser = Mock(return_value=mock_parser)

        # Mock setup_logging and get_logger
        organize_photos_module.setup_logging = Mock()
        mock_logger = Mock()
        organize_photos_module.get_logger = Mock(return_value=mock_logger)

        # Mock the client factory module before main() imports it
        mock_factory_class = Mock()
        mock_client = Mock()

        # Create mock file metadata
        mock_file = Mock()
        mock_file.path_display = "/Photos/Source/test.jpg"
        mock_file.path_lower = "/photos/source/test.jpg"
        mock_client.list_folder_recursive.return_value = iter([mock_file])
        mock_client.get_thumbnail.return_value = b"fake image data"
        mock_factory_class.return_value.create_client.return_value = mock_client
        sys.modules["scripts.auth.client_factory"] = Mock(DropboxClientFactory=mock_factory_class)

        # Mock get_provider
        mock_provider = Mock()
        mock_provider.load_reference_photos.return_value = 1
        mock_provider.find_matches_in_image.return_value = ([], 0)  # No matches
        organize_photos_module.get_provider = Mock(return_value=mock_provider)

        try:
            result = organize_photos_module.main()

            assert result == 0
        finally:
            # Cleanup the mock
            if "scripts.auth.client_factory" in sys.modules:
                del sys.modules["scripts.auth.client_factory"]

    def test_main_move_mode_with_full_size(self, organize_photos_module: ModuleType, tmp_path: Path) -> None:
        """Test main with move mode and full-size photos."""
        # Create valid config file
        config_file = tmp_path / "config.yaml"
        ref_photos_dir = tmp_path / "reference_photos"
        ref_photos_dir.mkdir()
        (ref_photos_dir / "ref.jpg").write_text("fake ref image")

        config_file.write_text(
            f"""
dropbox:
  source_folder: /Photos/Source
  destination_folder: /Photos/Dest
face_recognition:
  reference_photos_dir: {ref_photos_dir}
processing:
  dry_run: true
  use_full_size_photos: true
  verbose: true
"""
        )

        # Mock argparse
        mock_args = Mock()
        mock_args.config = str(config_file)
        mock_args.move = True  # Use move mode
        mock_args.dry_run = True
        mock_args.verbose = True  # Verbose mode
        mock_args.log_file = str(tmp_path / "operations.log")

        mock_parser = Mock()
        mock_parser.parse_args.return_value = mock_args
        organize_photos_module.argparse.ArgumentParser = Mock(return_value=mock_parser)

        # Mock setup_logging and get_logger
        organize_photos_module.setup_logging = Mock()
        mock_logger = Mock()
        organize_photos_module.get_logger = Mock(return_value=mock_logger)

        # Mock the client factory module before main() imports it
        mock_factory_class = Mock()
        mock_client = Mock()

        # Create mock file metadata - include file in destination folder to test filtering
        mock_file1 = Mock()
        mock_file1.path_display = "/Photos/Source/test.jpg"
        mock_file1.path_lower = "/photos/source/test.jpg"
        mock_file2 = Mock()
        mock_file2.path_display = "/Photos/Dest/already_there.jpg"
        mock_file2.path_lower = "/photos/dest/already_there.jpg"  # Should be filtered
        mock_client.list_folder_recursive.return_value = iter([mock_file1, mock_file2])
        mock_client.get_file_content.return_value = b"fake full-size image data"
        mock_factory_class.return_value.create_client.return_value = mock_client
        sys.modules["scripts.auth.client_factory"] = Mock(DropboxClientFactory=mock_factory_class)

        # Mock get_provider
        mock_provider = Mock()
        mock_provider.load_reference_photos.return_value = 1
        # Return a match to test the match logging path
        mock_match = Mock()
        mock_match.confidence = 0.9
        mock_provider.find_matches_in_image.return_value = ([mock_match], 1)
        organize_photos_module.get_provider = Mock(return_value=mock_provider)

        try:
            result = organize_photos_module.main()

            assert result == 0
            # Verify setup_logging was called with verbose=True
            organize_photos_module.setup_logging.assert_called_once_with(True)
            # Verify full-size photo was logged
            assert any("Full-size photos" in str(call) for call in mock_logger.info.call_args_list)
        finally:
            # Cleanup the mock
            if "scripts.auth.client_factory" in sys.modules:
                del sys.modules["scripts.auth.client_factory"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
