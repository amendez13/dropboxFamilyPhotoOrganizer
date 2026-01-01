"""
Main script for organizing photos based on face recognition.
Scans Dropbox directories for photos containing a specific person and copies/moves them to a designated folder.
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime
from typing import Optional

import yaml

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dropbox_client import DropboxClient


def setup_logging(verbose: bool = False) -> logging.Logger:
    """
    Configure logging for the application.

    Args:
        verbose: If True, set log level to DEBUG, otherwise INFO

    Returns:
        Configured logger instance
    """
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    return logging.getLogger(__name__)


def load_config(config_path: str = "../config/config.yaml") -> dict:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to configuration file

    Returns:
        Configuration dictionary
    """
    # Resolve path relative to this script or use absolute path
    if os.path.isabs(config_path):
        full_path = config_path
    else:
        script_dir = os.path.dirname(os.path.abspath(__file__))
        full_path = os.path.abspath(os.path.join(script_dir, config_path))

    with open(full_path, "r") as f:
        config = yaml.safe_load(f)

    return config


def safe_organize(
    dbx: DropboxClient, source_path: str, dest_path: str, operation: str = "copy", log_file: Optional[str] = None
) -> dict:
    """
    Safely organize a file by copying or moving it, with audit logging.

    Args:
        dbx: Dropbox client instance
        source_path: Source file path in Dropbox
        dest_path: Destination file path in Dropbox
        operation: Operation to perform ('copy' or 'move')
        log_file: Path to log file for recording operations

    Returns:
        Log entry dictionary with operation details
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "source": source_path,
        "destination": dest_path,
        "operation": operation,
        "success": False,
    }

    try:
        if operation == "copy":
            success = dbx.copy_file(source_path, dest_path)
        elif operation == "move":
            success = dbx.move_file(source_path, dest_path)
        else:
            raise ValueError(f"Invalid operation: {operation}. Must be 'copy' or 'move'")

        log_entry["success"] = success

    except Exception as e:
        log_entry["error"] = str(e)
        dbx.logger.error(f"Error during {operation} operation: {e}")

    # Log operation to file if specified
    if log_file:
        try:
            # Ensure log directory exists
            log_dir = os.path.dirname(os.path.abspath(log_file))
            if log_dir:  # Only create if there's a directory component
                os.makedirs(log_dir, exist_ok=True)
            with open(log_file, "a") as f:
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logging.error(f"Failed to write to log file: {e}")

    return log_entry


def main():
    """Main entry point for the photo organizer."""
    parser = argparse.ArgumentParser(description="Organize Dropbox photos based on face recognition")
    parser.add_argument(
        "--config", default="../config/config.yaml", help="Path to configuration file (default: ../config/config.yaml)"
    )
    parser.add_argument("--move", action="store_true", help="Move files instead of copying them (default: copy)")
    parser.add_argument(
        "--dry-run", action="store_true", help="Run in dry-run mode (list matches without copying/moving files)"
    )
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    parser.add_argument("--log-file", default="operations.log", help="Path to operations log file (default: operations.log)")

    args = parser.parse_args()

    # Setup logging
    logger = setup_logging(args.verbose)

    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = load_config(args.config)

        # Extract configuration values
        access_token = config["dropbox"]["access_token"]
        source_folder = config["dropbox"]["source_folder"]
        dest_folder = config["dropbox"]["destination_folder"]

        # Get processing configuration
        processing = config.get("processing", {})
        dry_run = args.dry_run or processing.get("dry_run", False)
        image_extensions = processing.get("image_extensions", [".jpg", ".jpeg", ".png", ".heic"])

        # Determine operation mode (CLI flag takes precedence)
        if args.move:
            operation = "move"
        else:
            # Check config, default to 'copy'
            operation = processing.get("operation", "copy")

        # Check if logging is enabled
        log_operations = processing.get("log_operations", True)
        log_file = args.log_file if log_operations else None

        logger.info(f"Operation mode: {operation}")
        logger.info(f"Dry run: {dry_run}")
        logger.info(f"Log file: {log_file if log_file else 'disabled'}")

        # Initialize Dropbox client
        logger.info("Connecting to Dropbox...")
        dbx = DropboxClient(access_token)

        if not dbx.verify_connection():
            logger.error("Failed to connect to Dropbox. Please check your access token.")
            return 1

        # TODO: Implement face recognition pipeline
        # This is a placeholder for the actual implementation
        logger.warning("Face recognition pipeline not yet implemented")
        logger.info("This script currently only supports the safe_organize function")
        logger.info("Full implementation coming soon...")

        # Example usage of safe_organize (for demonstration)
        if not dry_run:
            logger.info("\nExample: To use safe_organize function:")
            logger.info(f"  safe_organize(dbx, '/source/file.jpg', '/dest/file.jpg', '{operation}', '{log_file}')")

        return 0

    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        logger.error("Please copy config/config.example.yaml to config/config.yaml and configure it")
        return 1
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
