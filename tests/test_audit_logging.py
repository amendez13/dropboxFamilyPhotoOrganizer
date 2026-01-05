"""Unit tests for audit logging functionality in organize_photos."""

import json
import logging
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import Mock

import pytest


@pytest.fixture
def mock_dependencies():
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
def organize_photos_module(mock_dependencies):
    """Load the organize_photos module with mocked dependencies."""
    import importlib.util

    spec = importlib.util.spec_from_file_location(
        "organize_photos_module",
        Path(__file__).parent.parent / "scripts" / "organize_photos.py",
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_setup_audit_logging_creates_logger(organize_photos_module):
    """Test that setup_audit_logging creates a properly configured logger."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = os.path.join(tmpdir, "audit.log")

        # Call setup_audit_logging
        audit_logger = organize_photos_module.setup_audit_logging(log_file)

        # Verify logger properties
        assert audit_logger is not None
        assert audit_logger.name == "audit_operations"
        assert audit_logger.level == logging.INFO
        assert audit_logger.propagate is False
        assert len(audit_logger.handlers) == 1
        assert isinstance(audit_logger.handlers[0], logging.FileHandler)


def test_audit_logging_writes_json_entries(organize_photos_module):
    """Test that audit logging writes JSON entries to the log file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = os.path.join(tmpdir, "audit.log")

        # Setup audit logging
        audit_logger = organize_photos_module.setup_audit_logging(log_file)

        # Write multiple log entries
        entry1 = {"timestamp": "2024-01-01T00:00:00", "operation": "copy", "success": True}
        entry2 = {"timestamp": "2024-01-01T00:00:01", "operation": "move", "success": False}

        audit_logger.info(json.dumps(entry1))
        audit_logger.info(json.dumps(entry2))

        # Flush to ensure writes are complete
        for handler in audit_logger.handlers:
            handler.flush()

        # Verify file contents
        assert os.path.exists(log_file)
        with open(log_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 2
        # Each line should be valid JSON
        parsed_entry1 = json.loads(lines[0].strip())
        parsed_entry2 = json.loads(lines[1].strip())
        assert parsed_entry1["operation"] == "copy"
        assert parsed_entry2["operation"] == "move"


def test_audit_logging_thread_safety(organize_photos_module):
    """Test that audit logging can handle concurrent writes."""
    import threading

    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = os.path.join(tmpdir, "audit.log")

        # Setup audit logging
        audit_logger = organize_photos_module.setup_audit_logging(log_file)

        # Function to write log entries from multiple threads
        def write_entries(thread_id, count):
            for i in range(count):
                entry = {"thread": thread_id, "index": i, "operation": "test"}
                audit_logger.info(json.dumps(entry))

        # Create and start multiple threads
        threads = []
        num_threads = 5
        entries_per_thread = 10

        for i in range(num_threads):
            t = threading.Thread(target=write_entries, args=(i, entries_per_thread))
            threads.append(t)
            t.start()

        # Wait for all threads to complete
        for t in threads:
            t.join()

        # Flush handlers
        for handler in audit_logger.handlers:
            handler.flush()

        # Verify file contents
        with open(log_file, "r") as f:
            lines = f.readlines()

        # Should have exactly the expected number of entries
        expected_entries = num_threads * entries_per_thread
        assert len(lines) == expected_entries

        # Each line should be valid JSON
        for line in lines:
            entry = json.loads(line.strip())
            assert "thread" in entry
            assert "index" in entry
            assert entry["operation"] == "test"


def test_audit_logging_creates_directory_if_missing(organize_photos_module):
    """Test that setup_audit_logging creates the log directory if it doesn't exist."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a nested directory path that doesn't exist yet
        log_file = os.path.join(tmpdir, "logs", "nested", "audit.log")

        # Directory should not exist yet
        assert not os.path.exists(os.path.dirname(log_file))

        # Setup audit logging
        audit_logger = organize_photos_module.setup_audit_logging(log_file)

        # Directory should now exist
        assert os.path.exists(os.path.dirname(log_file))

        # Should be able to write to the log
        audit_logger.info(json.dumps({"test": "entry"}))
        for handler in audit_logger.handlers:
            handler.flush()

        assert os.path.exists(log_file)


def test_safe_organize_writes_to_audit_logger(organize_photos_module):
    """Test that safe_organize() writes operation details to global _audit_logger."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = os.path.join(tmpdir, "audit.log")

        # Setup audit logging and set the global _audit_logger
        audit_logger = organize_photos_module.setup_audit_logging(log_file)
        organize_photos_module._audit_logger = audit_logger

        # Create a mock Dropbox client
        mock_dbx = Mock()
        mock_dbx.copy_file.return_value = True
        mock_dbx.move_file.return_value = True
        mock_dbx.logger = Mock()

        # Call safe_organize with copy operation
        result = organize_photos_module.safe_organize(mock_dbx, "/source/photo.jpg", "/dest/photo.jpg", "copy")

        # Flush handlers to ensure writes are complete
        for handler in audit_logger.handlers:
            handler.flush()

        # Verify file contents
        assert os.path.exists(log_file)
        with open(log_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 1
        entry = json.loads(lines[0].strip())
        assert entry["source"] == "/source/photo.jpg"
        assert entry["destination"] == "/dest/photo.jpg"
        assert entry["operation"] == "copy"
        assert entry["success"] is True
        assert "timestamp" in entry

        # Verify the returned log entry matches
        assert result["success"] is True
        assert result["operation"] == "copy"

        # Clean up global state
        organize_photos_module._audit_logger = None


def test_safe_organize_logs_failed_operations(organize_photos_module):
    """Test that safe_organize() logs failed operations with error details."""
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = os.path.join(tmpdir, "audit.log")

        # Setup audit logging and set the global _audit_logger
        audit_logger = organize_photos_module.setup_audit_logging(log_file)
        organize_photos_module._audit_logger = audit_logger

        # Create a mock Dropbox client that raises an exception
        mock_dbx = Mock()
        mock_dbx.copy_file.side_effect = Exception("Network error")
        mock_dbx.logger = Mock()

        # Call safe_organize - should handle the exception gracefully
        organize_photos_module.safe_organize(mock_dbx, "/source/photo.jpg", "/dest/photo.jpg", "copy")

        # Flush handlers
        for handler in audit_logger.handlers:
            handler.flush()

        # Verify file contents
        with open(log_file, "r") as f:
            lines = f.readlines()

        assert len(lines) == 1
        entry = json.loads(lines[0].strip())
        assert entry["success"] is False
        assert entry["error"] == "Network error"
        assert entry["operation"] == "copy"

        # Verify error was logged
        mock_dbx.logger.error.assert_called_once()

        # Clean up global state
        organize_photos_module._audit_logger = None


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
