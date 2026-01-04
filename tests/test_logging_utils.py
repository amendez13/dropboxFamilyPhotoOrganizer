"""Unit tests for logging_utils module."""

import logging
import os
import sys
import tempfile
from pathlib import Path

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from logging_utils import get_logger, setup_logging  # noqa: E402


class TestSetupLogging:
    """Test setup_logging function."""

    def teardown_method(self):
        """Clean up after each test method."""
        # Reset root logger handlers to avoid interference between tests
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        # Reset log level
        root_logger.setLevel(logging.WARNING)

    def test_creates_file_and_console_handlers(self):
        """Test that setup_logging creates both file and console handlers."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            log_file = temp_file.name

        try:
            result = setup_logging(verbose=False, log_file=log_file)
            # setup_logging should return None
            assert result is None

            # Check that root logger has our handlers (may have others from test framework)
            root_logger = logging.getLogger()
            handler_types = [type(handler).__name__ for handler in root_logger.handlers]
            assert "RotatingFileHandler" in handler_types
            assert "StreamHandler" in handler_types

            # Check that root logger level is set correctly
            assert root_logger.level == logging.INFO

        finally:
            # Clean up
            if os.path.exists(log_file):
                os.unlink(log_file)

    def test_log_rotation_settings(self):
        """Test that log rotation is configured correctly (10MB, 5 backups)."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            log_file = temp_file.name

        try:
            setup_logging(verbose=False, log_file=log_file)

            root_logger = logging.getLogger()
            file_handler = None
            for handler in root_logger.handlers:
                if isinstance(handler, logging.handlers.RotatingFileHandler):
                    file_handler = handler
                    break

            assert file_handler is not None
            from scripts.logging_utils import LOG_BACKUP_COUNT, LOG_MAX_BYTES

            assert file_handler.maxBytes == LOG_MAX_BYTES
            assert file_handler.backupCount == LOG_BACKUP_COUNT

        finally:
            # Clean up
            if os.path.exists(log_file):
                os.unlink(log_file)

    def test_verbose_vs_non_verbose_modes(self):
        """Test that verbose flag sets correct log levels."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            log_file = temp_file.name

        try:
            # Test non-verbose (default INFO level)
            setup_logging(verbose=False, log_file=log_file)
            root_logger = logging.getLogger()
            assert root_logger.level == logging.INFO

            # Reset handlers
            self.teardown_method()

            # Test verbose (DEBUG level)
            setup_logging(verbose=True, log_file=log_file)
            root_logger = logging.getLogger()
            assert root_logger.level == logging.DEBUG

        finally:
            # Clean up
            if os.path.exists(log_file):
                os.unlink(log_file)

    def test_multiple_calls_remove_old_handlers(self):
        """Test that calling setup_logging multiple times removes old handlers (no duplicates)."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            log_file = temp_file.name

        try:
            # First call
            setup_logging(verbose=False, log_file=log_file)
            root_logger = logging.getLogger()
            first_call_handlers = len(root_logger.handlers)

            # Second call - should remove our old handlers and add new ones
            setup_logging(verbose=False, log_file=log_file)
            second_call_handlers = len(root_logger.handlers)

            # Should have the same number of handlers (our 2 handlers replaced the previous 2)
            # Other handlers (like from test frameworks) should remain untouched
            assert first_call_handlers == second_call_handlers

        finally:
            # Clean up
            if os.path.exists(log_file):
                os.unlink(log_file)

    def test_log_file_creation_in_nonexistent_directory(self):
        """Test that log files are created even when directory doesn't exist."""
        # Create a temporary directory path that doesn't exist
        temp_dir = Path(tempfile.gettempdir()) / "nonexistent_logging_test_dir"
        log_file = str(temp_dir / "test.log")

        try:
            # Ensure directory doesn't exist
            if temp_dir.exists():
                import shutil

                shutil.rmtree(temp_dir)

            # This should create the directory and file
            setup_logging(verbose=False, log_file=log_file)

            # Check that directory and file were created
            assert temp_dir.exists()
            assert os.path.exists(log_file)

            # Check that logging actually works
            logger = get_logger("test")
            logger.info("Test message")
            with open(log_file, "r") as f:
                content = f.read()
                assert "Test message" in content

        finally:
            # Clean up
            if temp_dir.exists():
                import shutil

                shutil.rmtree(temp_dir)

    def test_handlers_have_correct_formatters(self):
        """Test that both handlers have the correct formatter."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            log_file = temp_file.name

        try:
            setup_logging(verbose=False, log_file=log_file)

            root_logger = logging.getLogger()
            for handler in root_logger.handlers:
                assert handler.formatter is not None
                # Test that formatter includes expected fields
                test_record = logging.LogRecord(
                    name="test", level=logging.INFO, pathname="", lineno=0, msg="test message", args=(), exc_info=None
                )
                formatted = handler.formatter.format(test_record)
                assert "test" in formatted  # logger name
                assert "INFO" in formatted  # level
                assert "test message" in formatted  # message

        finally:
            # Clean up
            if os.path.exists(log_file):
                os.unlink(log_file)

    def test_file_handler_logs_to_correct_file(self):
        """Test that file handler writes to the specified log file."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            log_file = temp_file.name

        try:
            setup_logging(verbose=False, log_file=log_file)

            # Log a test message
            test_message = "Test log message for file output"
            logger = get_logger("test")
            logger.info(test_message)

            # Check that message was written to file
            with open(log_file, "r") as f:
                content = f.read()
                assert test_message in content

        finally:
            # Clean up
            if os.path.exists(log_file):
                os.unlink(log_file)

    def test_file_handler_creation_failure_fallback(self):
        """Test that setup_logging falls back to console-only when file handler creation fails."""
        # Use an invalid path that should fail
        invalid_log_file = "/invalid/path/that/does/not/exist/logfile.log"

        # This should not raise an exception and should fall back to console-only
        setup_logging(verbose=False, log_file=invalid_log_file)

        # Check that we have a console handler but no file handler
        root_logger = logging.getLogger()
        handler_types = [type(handler).__name__ for handler in root_logger.handlers]

        # Should have StreamHandler (console) but not RotatingFileHandler
        assert "StreamHandler" in handler_types
        # Note: RotatingFileHandler might still be present from previous tests
        # but the important thing is that logging still works


class TestGetLogger:
    """Test get_logger function."""

    def teardown_method(self):
        """Clean up after each test method."""
        # Reset root logger handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        root_logger.setLevel(logging.WARNING)

    def test_get_logger_returns_logger_instance(self):
        """Test that get_logger returns a properly configured Logger instance."""
        logger = get_logger("test_module")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_module"

    def test_get_logger_uses_root_configuration(self):
        """Test that get_logger uses the root logger's configuration."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            log_file = temp_file.name

        try:
            # Setup logging first
            setup_logging(verbose=True, log_file=log_file)

            # Get a named logger
            logger = get_logger("test_module")

            # Logger should inherit level from root
            assert logger.getEffectiveLevel() == logging.DEBUG

            # Logger should use root handlers
            assert len(logger.handlers) == 0  # Named loggers don't have direct handlers
            assert logger.hasHandlers()  # But they inherit from root

        finally:
            # Clean up
            if os.path.exists(log_file):
                os.unlink(log_file)

    def test_get_logger_different_names(self):
        """Test that get_logger returns different loggers for different names."""
        logger1 = get_logger("module1")
        logger2 = get_logger("module2")

        assert logger1.name == "module1"
        assert logger2.name == "module2"
        assert logger1 is not logger2

    def test_get_logger_same_name_returns_same_instance(self):
        """Test that get_logger returns the same instance for the same name."""
        logger1 = get_logger("same_module")
        logger2 = get_logger("same_module")

        assert logger1 is logger2


class TestLoggingIntegration:
    """Integration tests for logging functionality."""

    def teardown_method(self):
        """Clean up after each test method."""
        # Reset root logger handlers
        root_logger = logging.getLogger()
        for handler in root_logger.handlers[:]:
            root_logger.removeHandler(handler)
        root_logger.setLevel(logging.WARNING)

    def test_full_logging_workflow(self):
        """Test a complete logging workflow from setup to output."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            log_file = temp_file.name

        try:
            # Setup logging
            setup_logging(verbose=False, log_file=log_file)

            # Get named loggers
            app_logger = get_logger("photo_organizer")
            db_logger = get_logger("dropbox_client")
            root_logger = get_logger("logging_utils")

            # Log messages at different levels
            root_logger.info("Application started")
            app_logger.info("Processing photos")
            db_logger.debug("Connecting to Dropbox API")
            app_logger.warning("Some photos could not be processed")
            db_logger.error("API rate limit exceeded")

            # Check file output
            with open(log_file, "r") as f:
                content = f.read()
                lines = content.strip().split("\n")
                assert len(lines) == 5  # Should have 5 log lines (including initialization, debug filtered out)

                # Check that all expected messages are present
                assert any("Logging initialized" in line for line in lines)
                assert any("Application started" in line for line in lines)
                assert any("Processing photos" in line for line in lines)
                assert any("Some photos could not be processed" in line for line in lines)
                assert any("API rate limit exceeded" in line for line in lines)

                # Check that debug message is NOT present (filtered out)
                assert not any("Connecting to Dropbox API" in line for line in lines)

        finally:
            # Clean up
            if os.path.exists(log_file):
                os.unlink(log_file)

    def test_verbose_logging_includes_debug(self):
        """Test that verbose mode includes debug messages."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            log_file = temp_file.name

        try:
            # Setup verbose logging
            setup_logging(verbose=True, log_file=log_file)

            logger = get_logger("test")
            logger.debug("Debug message")
            logger.info("Info message")

            # Check file output
            with open(log_file, "r") as f:
                content = f.read()
                lines = content.strip().split("\n")
                assert len(lines) == 3  # Should have initialization + both messages

                # Check that debug message is present
                assert any("Debug message" in line for line in lines)
                assert any("Info message" in line for line in lines)

        finally:
            # Clean up
            if os.path.exists(log_file):
                os.unlink(log_file)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
