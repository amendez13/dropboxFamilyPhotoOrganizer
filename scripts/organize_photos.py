"""
Main script for organizing photos based on face recognition.
Scans Dropbox directories for photos containing a specific person and copies/moves them to a designated folder.
"""

import argparse
import glob
import json
import logging
import os
import sys
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import yaml
from dropbox.files import FileMetadata

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.dropbox_client import DropboxClient  # noqa: E402
from scripts.face_recognizer import get_provider  # noqa: E402
from scripts.face_recognizer.base_provider import BaseFaceRecognitionProvider  # noqa: E402
from scripts.logging_utils import get_logger, setup_logging  # noqa: E402

# Global audit logger - initialized when setup_audit_logging is called
_audit_logger: Optional[logging.Logger] = None


def setup_audit_logging(log_file: str) -> logging.Logger:
    """
    Set up a dedicated logger for audit operations.

    Uses Python's logging module with a FileHandler to provide better
    concurrency handling compared to direct file I/O. The logging module
    handles thread safety internally.

    Args:
        log_file: Path to the audit log file

    Returns:
        Configured audit logger instance
    """
    # Create a unique logger for audit operations
    audit_logger = logging.getLogger("audit_operations")
    audit_logger.setLevel(logging.INFO)
    audit_logger.propagate = False  # Don't propagate to root logger

    # Close and remove any existing handlers to avoid duplicates and file handle leaks
    for handler in audit_logger.handlers[:]:
        handler.close()
        audit_logger.removeHandler(handler)

    # Ensure log directory exists
    log_dir = os.path.dirname(os.path.abspath(log_file))
    if log_dir:
        os.makedirs(log_dir, exist_ok=True)

    # Create file handler for audit log
    file_handler = logging.FileHandler(log_file, mode="a")
    file_handler.setLevel(logging.INFO)

    # Use a simple formatter that just outputs the message (which will be JSON)
    formatter = logging.Formatter("%(message)s")
    file_handler.setFormatter(formatter)

    audit_logger.addHandler(file_handler)

    return audit_logger


def load_config(config_path: str = "../config/config.yaml") -> Dict[str, Any]:
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
        config: Dict[str, Any] = yaml.safe_load(f)

    return config


def _sanitize_path_for_logging(path: str) -> str:
    """
    Sanitize file paths for safe logging by removing control characters.

    This prevents log injection attacks where malicious file paths containing
    newline characters or other control characters could break the JSON-per-line
    log format or inject false log entries.

    Args:
        path: The file path to sanitize

    Returns:
        Sanitized path with control characters removed
    """
    # Remove control characters (ASCII 0-31 and 127-159)
    # Keep printable characters (32-126), Unicode characters (160+), and path separators
    return "".join(char for char in path if (ord(char) >= 32 and ord(char) < 127) or ord(char) >= 160 or char in "/\\")


def safe_organize(dbx: DropboxClient, source_path: str, dest_path: str, operation: str = "copy") -> Dict[str, Any]:
    """
    Safely organize a file by copying or moving it, with audit logging.

    Audit logging is performed using a global audit logger configured via
    setup_audit_logging(). The logging module provides better thread safety
    for concurrent writes compared to direct file I/O.

    Args:
        dbx: Dropbox client instance
        source_path: Source file path in Dropbox
        dest_path: Destination file path in Dropbox
        operation: Operation to perform ('copy' or 'move')

    Returns:
        Log entry dictionary with operation details
    """
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "source": _sanitize_path_for_logging(source_path),
        "destination": _sanitize_path_for_logging(dest_path),
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
        dbx.logger.error(f"Error during {operation} operation from '{source_path}' to '{dest_path}': {e}")

    # Log operation using audit logger if available
    # The logging module provides better thread safety for concurrent writes
    # compared to direct file I/O
    if _audit_logger:
        try:
            _audit_logger.info(json.dumps(log_entry))
        except Exception as e:
            logging.error(f"Failed to write to audit log: {e}")

    return log_entry


def _download_image(
    dbx_client: DropboxClient, file_path: str, face_config: Dict[str, Any], use_full_size: bool
) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Download image data from Dropbox.

    Args:
        dbx_client: Initialized DropboxClient instance
        file_path: Dropbox path to the image file
        face_config: Face recognition config dict (contains thumbnail_size)
        use_full_size: If True, download full-size; otherwise get thumbnail

    Returns:
        Tuple of (image_data, error_message) where image_data is bytes or None,
        and error_message is a string describing the failure or None on success.
    """
    if use_full_size:
        image_data = dbx_client.get_file_content(file_path)
        if not image_data:
            return None, f"Could not download full-size photo: {file_path}"
        return image_data, None

    thumbnail_size = face_config.get("thumbnail_size", "w256h256")
    image_data = dbx_client.get_thumbnail(file_path, size=thumbnail_size)
    if not image_data:
        return None, f"Could not get thumbnail for {file_path}"
    return image_data, None


def process_images(
    image_files: List[FileMetadata],
    dbx_client: DropboxClient,
    provider: BaseFaceRecognitionProvider,
    face_config: Dict[str, Any],
    use_full_size: bool,
    tolerance: float,
    verbose_processing: bool,
    logger: logging.Logger,
) -> Tuple[List[Dict[str, Any]], int, int, List[str]]:
    """
    Process images from Dropbox and find face matches.

    Downloads each image (as thumbnail or full-size) and runs face recognition
    to identify matches against the loaded reference photos.

    Args:
        image_files: List of Dropbox FileMetadata objects to process
        dbx_client: Initialized DropboxClient instance for downloading images
        provider: Face recognition provider with loaded reference encodings
        face_config: Face recognition configuration dict (contains thumbnail_size)
        use_full_size: If True, download full-size photos; otherwise use thumbnails
        tolerance: Face matching tolerance (lower = stricter matching)
        verbose_processing: If True, log every image; otherwise log every 10th
        logger: Logger instance for output

    Returns:
        Tuple of (matches, processed, errors, no_match_paths) where:
        - matches: List of dicts with file_path, num_matches, total_faces, matches
        - processed: Total number of images processed
        - errors: Number of images that failed to process
        - no_match_paths: List of file paths with no matches
    """
    matches = []
    processed = 0
    errors = 0
    no_match_paths = []

    logger.info("=" * 70)
    logger.info("Processing images...")
    logger.info("=" * 70)

    for file_metadata in image_files:
        file_path = file_metadata.path_display
        processed += 1

        if verbose_processing or processed % 10 == 0:
            logger.info(f"Processing {processed}/{len(image_files)}: {file_path}")

        try:
            # Download image data (full-size or thumbnail based on config)
            image_data, error_msg = _download_image(dbx_client, file_path, face_config, use_full_size)
            if not image_data:
                logger.warning(error_msg)
                errors += 1
                continue

            # Detect faces and check for matches
            face_matches, total_faces = provider.find_matches_in_image(image_data, source=file_path, tolerance=tolerance)

            if face_matches:
                match_info = {
                    "file_path": file_path,
                    "num_matches": len(face_matches),
                    "total_faces": total_faces,
                    "matches": face_matches,
                }
                matches.append(match_info)
                logger.info(f"✓ MATCH: {file_path} ({len(face_matches)}/{total_faces} faces matched)")
            else:
                no_match_paths.append(file_path)

        except (OSError, IOError) as e:
            logger.error(f"Image processing error for {file_path}: {e}")
            errors += 1
        except ValueError as e:
            logger.warning(f"Invalid image data for {file_path}: {e}")
            errors += 1
        except Exception as e:
            logger.error(f"Unexpected error processing {file_path}: {e}", exc_info=True)
            errors += 1

    return matches, processed, errors, no_match_paths


def perform_operations(
    matches: List[Dict[str, Any]],
    no_match_paths: List[str],
    destination_folder: str,
    dbx_client: DropboxClient,
    operation: str,
    dry_run: bool,
    logger: logging.Logger,
) -> None:
    """
    Perform copy/move operations on files that matched face recognition.

    Copies or moves matched files to the destination folder, handling duplicates
    and logging all operations for audit purposes using the global audit logger.

    Args:
        matches: List of match dicts from process_images(), each containing
                 file_path, num_matches, total_faces, and matches keys
        no_match_paths: List of file paths that had no face matches
        destination_folder: Dropbox path where matched files will be copied/moved
        dbx_client: Initialized DropboxClient instance for file operations
        operation: Operation type - either 'copy' or 'move'
        dry_run: If True, only report what would be done without actual operations
        logger: Logger instance for output

    Returns:
        None. Results are logged via the logger parameter.
    """
    if matches:
        logger.info(f"Found {len(matches)} image(s) with matching faces:")
        for match in matches:
            logger.info(f"  - {match['file_path']} ({match['num_matches']} face(s) matched)")
    else:
        logger.info("No matching images found")

    if no_match_paths:
        logger.info(f"Found {len(no_match_paths)} image(s) with no matching faces:")
        for path in no_match_paths:
            logger.info(f"  - {path}")

    if dry_run:
        logger.info("")
        logger.info("DRY RUN MODE - No files were copied/moved")
        logger.info("Remove --dry-run flag or set dry_run: false in config to perform actual operations")
        return

    logger.info("")
    logger.info(f"Performing {operation} operations...")

    success_count = 0
    skipped_count = 0
    processed_destinations = set()

    for match in matches:
        source_path = match["file_path"]
        # Generate destination path
        filename = os.path.basename(source_path)
        dest_path = os.path.join(destination_folder, filename)

        # Skip if we've already processed this destination in this run
        if dest_path in processed_destinations:
            skipped_count += 1
            logger.info(f"⊘ Skipped (duplicate filename): {source_path}")
            continue

        processed_destinations.add(dest_path)
        log_entry = safe_organize(dbx_client, source_path, dest_path, operation)

        if log_entry["success"]:
            success_count += 1
            # Use proper past tense for the operation
            past_tense = {"copy": "Copied", "move": "Moved"}.get(operation, operation.capitalize() + "d")
            logger.info(f"✓ {past_tense}: {source_path} → {dest_path}")
        else:
            logger.error(f"✗ Failed to {operation}: {source_path}")

    logger.info("")
    # Use proper past tense for the operation
    past_tense = {"copy": "copied", "move": "moved"}.get(operation, operation + "d")
    logger.info(f"Successfully {past_tense} {success_count}/{len(matches)} file(s)")
    if skipped_count > 0:
        logger.info(f"Skipped {skipped_count} file(s) with duplicate filenames")


def _get_reference_photos(reference_photos_dir: str, image_extensions: List[str]) -> List[str]:
    """
    Find reference photos in the specified directory.

    Args:
        reference_photos_dir: Path to directory containing reference photos
        image_extensions: List of valid image extensions (e.g., ['.jpg', '.png'])

    Returns:
        List of paths to reference photo files, excluding system files.
    """
    reference_photos: List[str] = []
    for ext in image_extensions:
        pattern = f"{reference_photos_dir}/*{ext}"
        reference_photos.extend(glob.glob(pattern))

    # Remove duplicates and system files
    reference_photos = list(set(reference_photos))
    reference_photos = [p for p in reference_photos if not os.path.basename(p).startswith(".")]
    return reference_photos


def _validate_config(
    config: Dict[str, Any], logger: logging.Logger
) -> Tuple[Dict[str, Any], Any, Any, Dict[str, Any], Dict[str, Any]]:
    """
    Validate and extract configuration values.

    Returns tuple of (dropbox_config, source_folder, destination_folder, face_config, processing_config)
    Raises ValueError if configuration is invalid.
    """
    dropbox_config = config.get("dropbox", {})
    source_folder = dropbox_config.get("source_folder")
    destination_folder = dropbox_config.get("destination_folder")

    if not source_folder or not destination_folder:
        raise ValueError("Source and destination folders must be configured")
    if source_folder == destination_folder:
        raise ValueError("Source and destination folders must be different")

    face_config = config.get("face_recognition", {})
    processing = config.get("processing", {})

    return dropbox_config, source_folder, destination_folder, face_config, processing


def _setup_face_provider(face_config: Dict[str, Any], tolerance: float, logger: logging.Logger) -> BaseFaceRecognitionProvider:
    """
    Initialize and configure the face recognition provider.

    Returns the configured provider instance.
    """
    provider_name = face_config.get("provider", "local")
    logger.info(f"Initializing {provider_name} face recognition provider...")
    local_config = face_config.get(provider_name, {})

    # Use recognition-specific num_jitters if available, otherwise fall back to default
    recognition_config = local_config.get("recognition", {})
    recognition_num_jitters = recognition_config.get("num_jitters", local_config.get("num_jitters", 1))

    # Build config for provider with recognition parameters
    provider_config = {
        "model": local_config.get("model", "hog"),
        "encoding_model": local_config.get("encoding_model", "large"),
        "num_jitters": recognition_num_jitters,
        "tolerance": tolerance,
    }

    logger.info(f"  Detection model: {provider_config['model']}")
    logger.info(f"  Encoding model: {provider_config['encoding_model']}")
    logger.info(f"  Num jitters (recognition): {provider_config['num_jitters']}")
    logger.info(f"  Tolerance: {tolerance}")

    return get_provider(provider_name, provider_config)


def _setup_audit_logger_if_enabled(log_file: Optional[str], logger: logging.Logger) -> None:
    """
    Setup audit logging if a log file is specified.

    Sets the global _audit_logger variable.
    """
    global _audit_logger
    if log_file:
        try:
            _audit_logger = setup_audit_logging(log_file)
            logger.info(f"Audit logging enabled: {log_file}")
        except Exception as e:
            logger.warning(f"Failed to setup audit logging: {e}")
            logger.warning("Continuing without audit logging")
            _audit_logger = None


def main() -> int:
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
    setup_logging(args.verbose)
    logger = get_logger(__name__)

    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = load_config(args.config)

        # Validate configuration
        _, source_folder, destination_folder, face_config, processing = _validate_config(config, logger)

        # Extract face recognition configuration
        reference_photos_dir = face_config.get("reference_photos_dir", "./reference_photos")
        tolerance = face_config.get("tolerance", 0.6)
        dry_run = args.dry_run or processing.get("dry_run", False)
        image_extensions = processing.get("image_extensions", [".jpg", ".jpeg", ".png", ".heic"])
        verbose_processing = processing.get("verbose", False)
        use_full_size = processing.get("use_full_size_photos", False)

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
        if use_full_size:
            logger.info("Image processing: Full-size photos")
        else:
            thumbnail_size = face_config.get("thumbnail_size", "w256h256")
            logger.info(f"Image processing: Thumbnails ({thumbnail_size})")
        logger.info(f"Source folder: {source_folder}")
        logger.info(f"Destination folder: {destination_folder}")
        logger.info(f"Log file: {log_file if log_file else 'disabled'}")

        # Initialize Dropbox client using OAuth
        logger.info("Connecting to Dropbox...")
        from scripts.auth.client_factory import DropboxClientFactory

        factory = DropboxClientFactory(config)
        dbx_client = factory.create_client()

        logger.info("✓ Connected to Dropbox")

        # Initialize face recognition provider
        provider = _setup_face_provider(face_config, tolerance, logger)

        # Load reference photos
        logger.info(f"Loading reference photos from {reference_photos_dir}...")
        reference_photos = _get_reference_photos(reference_photos_dir, image_extensions)

        if not reference_photos:
            if getattr(provider, "use_face_collection", False):
                logger.info("No local reference photos found; using AWS face collection")
                num_faces = provider.load_reference_photos([])
                logger.info(f"✓ Loaded {num_faces} reference face encoding(s)")
            else:
                logger.error(f"No reference photos found in {reference_photos_dir}")
                logger.error("Please add reference photos and run scripts/train_face_model.py first")
                return 1
        else:
            num_faces = provider.load_reference_photos(reference_photos)
            logger.info(f"✓ Loaded {num_faces} reference face encoding(s)")

        # List files in source folder
        logger.info(f"Scanning {source_folder} for photos...")
        files = list(dbx_client.list_folder_recursive(source_folder))

        # Filter for image files, excluding destination folder
        image_files = [
            f
            for f in files
            if any(f.path_lower.endswith(ext.lower()) for ext in image_extensions)
            and not f.path_lower.startswith(destination_folder.lower())
        ]

        logger.info(f"Found {len(image_files)} image file(s) to process")

        if len(image_files) == 0:
            logger.warning("No image files found in source folder")
            return 0

        # Process images
        matches, processed, errors, no_match_paths = process_images(
            image_files, dbx_client, provider, face_config, use_full_size, tolerance, verbose_processing, logger
        )

        # Print summary
        logger.info("=" * 70)
        logger.info("Processing Complete")
        logger.info("=" * 70)
        logger.info(f"Total images processed: {processed}")
        logger.info(f"Matching images found: {len(matches)}")
        logger.info(f"Errors: {errors}")
        logger.info("")

        # Setup audit logging if enabled
        _setup_audit_logger_if_enabled(log_file, logger)

        # Perform operations
        perform_operations(matches, no_match_paths, destination_folder, dbx_client, operation, dry_run, logger)

        return 0

    except ValueError as e:
        logger.error(str(e))
        return 1
    except FileNotFoundError as e:
        logger.error(f"Configuration file not found: {e}")
        logger.error("Please copy config/config.example.yaml to config/config.yaml and configure it")
        return 1
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
