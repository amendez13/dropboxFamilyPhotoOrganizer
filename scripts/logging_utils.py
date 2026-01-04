"""
Structured logging utilities for the photo organizer application.

Provides centralized logging configuration with file rotation, console output,
and support for verbose logging levels.
"""

import logging
import os
from logging.handlers import RotatingFileHandler
from typing import Optional

# Configuration constants
LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5  # Number of backup files to keep
DEFAULT_LOG_DIR = "logs"
DEFAULT_LOG_FILE = "photo_organizer.log"

# Track handlers we add to avoid interfering with third-party logging
_added_handlers: set[logging.Handler] = set()


def setup_logging(verbose: bool = False, log_file: Optional[str] = None) -> None:
    """
    Configure logging for the application.

    Sets up both file and console logging with rotation for production use.
    File logs are rotated at 10MB with 5 backup files kept.

    This function is designed to be called once at application startup.
    Subsequent calls will update the configuration without removing existing
    third-party handlers.

    Args:
        verbose: If True, set log level to DEBUG, otherwise INFO
        log_file: Path to the log file (default: 'logs/photo_organizer.log')
    """
    level = logging.DEBUG if verbose else logging.INFO

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Get root logger
    root_logger = logging.getLogger()

    # Remove only handlers we previously added to avoid interfering with third-party logging
    for handler in list(_added_handlers):
        if handler in root_logger.handlers:
            root_logger.removeHandler(handler)
    _added_handlers.clear()

    # Use default log file if none specified
    if log_file is None:
        log_file = os.path.join(DEFAULT_LOG_DIR, DEFAULT_LOG_FILE)

    # Try to create file handler, fallback to console-only if it fails
    file_handler = None
    try:
        # Ensure log directory exists
        log_dir = os.path.dirname(os.path.abspath(log_file))
        if log_dir:  # Only create if there's a directory component
            os.makedirs(log_dir, exist_ok=True)

        # File handler with rotation
        file_handler = RotatingFileHandler(log_file, maxBytes=LOG_MAX_BYTES, backupCount=LOG_BACKUP_COUNT)
        file_handler.setFormatter(formatter)
        file_handler.setLevel(level)
    except (OSError, IOError, PermissionError) as e:
        # Log the error to console (since file logging failed)
        print(f"Warning: Could not create log file '{log_file}': {e}")
        print("Falling back to console-only logging.")

    # Console handler (always available)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)

    # Add handlers to root logger and track them
    if file_handler:
        root_logger.addHandler(file_handler)
        _added_handlers.add(file_handler)

    root_logger.addHandler(console_handler)
    _added_handlers.add(console_handler)

    # Set root logger level to the most permissive level of our handlers
    root_logger.setLevel(level)

    # Log initialization message
    logger = logging.getLogger(__name__)
    logger.info(f"Logging initialized - Level: {logging.getLevelName(level)}, File: {log_file}")


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance for the specified module name.

    This ensures all loggers use the centralized configuration.

    Args:
        name: Module name (typically __name__)

    Returns:
        Logger instance
    """
    return logging.getLogger(name)
