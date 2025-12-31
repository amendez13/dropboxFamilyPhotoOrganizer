#!/usr/bin/env python3
"""
Main script for organizing photos using face recognition.
Defaults to copying files (safer) with optional move operation.
"""

import sys
import os
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.dropbox_client import DropboxClient
from scripts.config_loader import load_config


def safe_organize(
    dbx: DropboxClient,
    source_path: str,
    dest_path: str,
    operation: str = 'copy',
    log_file: str = 'operations.log',
    dry_run: bool = False
) -> dict:
    """
    Safely organize a file with audit logging.

    Args:
        dbx: DropboxClient instance
        source_path: Source file path in Dropbox
        dest_path: Destination file path in Dropbox
        operation: 'copy' (default, safer) or 'move'
        log_file: Path to operation log file
        dry_run: If True, only log what would happen without performing operation

    Returns:
        Log entry dictionary with operation details
    """
    log_entry = {
        'timestamp': datetime.now().isoformat(),
        'source': source_path,
        'destination': dest_path,
        'operation': operation,
        'dry_run': dry_run,
        'success': False
    }

    try:
        if dry_run:
            logging.info(f"[DRY RUN] Would {operation}: {source_path} -> {dest_path}")
            log_entry['success'] = True
        else:
            if operation == 'copy':
                success = dbx.copy_file(source_path, dest_path)
            elif operation == 'move':
                success = dbx.move_file(source_path, dest_path)
            else:
                raise ValueError(f"Invalid operation: {operation}. Must be 'copy' or 'move'")

            log_entry['success'] = success

            if success:
                logging.info(f"Successfully {operation}ed: {source_path} -> {dest_path}")
            else:
                logging.error(f"Failed to {operation}: {source_path} -> {dest_path}")

    except Exception as e:
        log_entry['error'] = str(e)
        logging.error(f"Error during {operation} operation: {e}")

    # Log operation to file
    try:
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
    except Exception as e:
        logging.error(f"Failed to write to log file: {e}")

    return log_entry


def main():
    """Main entry point for photo organization."""
    parser = argparse.ArgumentParser(
        description='Organize photos using face recognition with copy (default) or move operations.'
    )
    parser.add_argument(
        '--move',
        action='store_true',
        help='Use move operation instead of copy (destructive)'
    )
    parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview operations without executing them'
    )
    parser.add_argument(
        '--log-file',
        default='operations.log',
        help='Path to operation log file (default: operations.log)'
    )
    parser.add_argument(
        '--verbose',
        action='store_true',
        help='Enable verbose logging'
    )
    parser.add_argument(
        '--config',
        default='config/config.yaml',
        help='Path to configuration file (default: config/config.yaml)'
    )

    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    logger = logging.getLogger(__name__)

    # Determine operation mode
    operation = 'move' if args.move else 'copy'
    if args.move:
        logger.warning("⚠️  MOVE mode enabled - files will be deleted from source location")
    else:
        logger.info("✓ COPY mode enabled - files will be preserved in original location (safer)")

    try:
        # Load configuration
        logger.info(f"Loading configuration from: {args.config}")
        config = load_config(args.config)

        # Initialize Dropbox client
        access_token = config['dropbox']['access_token']
        if access_token == "YOUR_DROPBOX_ACCESS_TOKEN_HERE":
            logger.error("Please configure your Dropbox access token in config/config.yaml")
            return 1

        dbx = DropboxClient(access_token)

        # Verify connection
        if not dbx.verify_connection():
            logger.error("Failed to connect to Dropbox")
            return 1

        # Get configuration
        source_folder = config['dropbox']['source_folder']
        dest_folder = config['dropbox']['destination_folder']

        # Override operation if specified in config and not overridden by CLI
        config_operation = config.get('processing', {}).get('operation', 'copy')
        if not args.move and config_operation == 'move':
            operation = 'move'
            logger.warning("Operation set to 'move' via config file")

        # Override dry_run if specified in config and not overridden by CLI
        config_dry_run = config.get('processing', {}).get('dry_run', False)
        dry_run = args.dry_run or config_dry_run

        logger.info(f"Source folder: {source_folder}")
        logger.info(f"Destination folder: {dest_folder}")
        logger.info(f"Operation mode: {operation}")
        logger.info(f"Dry run: {dry_run}")
        logger.info(f"Log file: {args.log_file}")

        # TODO: Integrate with face recognition module
        # This is a placeholder for the actual photo organization logic
        # which would:
        # 1. List all photos in source_folder
        # 2. Process each photo with face recognition
        # 3. Call safe_organize() for matching photos

        logger.info("\n" + "="*60)
        logger.info("Photo organization functionality coming soon!")
        logger.info("This script currently demonstrates the safe_organize function.")
        logger.info("="*60 + "\n")

        # Example usage (commented out):
        # for file in dbx.list_folder_recursive(source_folder, extensions=['.jpg', '.jpeg', '.png']):
        #     if face_matches(file):
        #         dest_path = f"{dest_folder}/{file.name}"
        #         safe_organize(dbx, file.path_display, dest_path, operation, args.log_file, dry_run)

        return 0

    except FileNotFoundError:
        logger.error(f"Configuration file not found: {args.config}")
        logger.info("Copy config/config.example.yaml to config/config.yaml and configure it")
        return 1
    except Exception as e:
        logger.error(f"Unexpected error: {e}", exc_info=True)
        return 1


if __name__ == '__main__':
    sys.exit(main())
