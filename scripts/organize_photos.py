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
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.face_recognizer import get_provider  # noqa: E402


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


def safe_organize(dbx, source_path: str, dest_path: str, operation: str = "copy", log_file: Optional[str] = None) -> dict:
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


def _download_image(dbx_client, file_path, face_config, use_full_size):
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


def process_images(image_files, dbx_client, provider, face_config, use_full_size, tolerance, verbose_processing, logger):
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
        Tuple of (matches, processed, errors) where:
        - matches: List of dicts with file_path, num_matches, total_faces, matches
        - processed: Total number of images processed
        - errors: Number of images that failed to process
    """
    matches = []
    processed = 0
    errors = 0

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

        except (OSError, IOError) as e:
            logger.error(f"Image processing error for {file_path}: {e}")
            errors += 1
        except ValueError as e:
            logger.warning(f"Invalid image data for {file_path}: {e}")
            errors += 1
        except Exception as e:
            logger.error(f"Unexpected error processing {file_path}: {e}", exc_info=True)
            errors += 1

    return matches, processed, errors


def perform_operations(matches, destination_folder, dbx_client, operation, log_file, dry_run, logger):
    """
    Perform copy/move operations on files that matched face recognition.

    Copies or moves matched files to the destination folder, handling duplicates
    and logging all operations for audit purposes.

    Args:
        matches: List of match dicts from process_images(), each containing
                 file_path, num_matches, total_faces, and matches keys
        destination_folder: Dropbox path where matched files will be copied/moved
        dbx_client: Initialized DropboxClient instance for file operations
        operation: Operation type - either 'copy' or 'move'
        log_file: Path to log file for recording operations, or None to disable
        dry_run: If True, only report what would be done without actual operations
        logger: Logger instance for output

    Returns:
        None. Results are logged via the logger parameter.
    """
    if not matches:
        logger.info("No matching images found")
        return

    logger.info(f"Found {len(matches)} image(s) with matching faces:")
    for match in matches:
        logger.info(f"  - {match['file_path']} ({match['num_matches']} face(s) matched)")

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
        log_entry = safe_organize(dbx_client, source_path, dest_path, operation, log_file)

        if log_entry["success"]:
            success_count += 1
            logger.info(f"✓ {operation.capitalize()}d: {source_path} → {dest_path}")
        else:
            logger.error(f"✗ Failed to {operation}: {source_path}")

    logger.info("")
    logger.info(f"Successfully {operation}d {success_count}/{len(matches)} file(s)")
    if skipped_count > 0:
        logger.info(f"Skipped {skipped_count} file(s) with duplicate filenames")


def _get_reference_photos(reference_photos_dir, image_extensions):
    """
    Find reference photos in the specified directory.

    Args:
        reference_photos_dir: Path to directory containing reference photos
        image_extensions: List of valid image extensions (e.g., ['.jpg', '.png'])

    Returns:
        List of paths to reference photo files, excluding system files.
    """
    import glob

    reference_photos = []
    for ext in image_extensions:
        pattern = f"{reference_photos_dir}/*{ext}"
        reference_photos.extend(glob.glob(pattern))

    # Remove duplicates and system files
    reference_photos = list(set(reference_photos))
    reference_photos = [p for p in reference_photos if not os.path.basename(p).startswith(".")]
    return reference_photos


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

        # Extract Dropbox configuration
        dropbox_config = config.get("dropbox", {})
        source_folder = dropbox_config.get("source_folder")
        destination_folder = dropbox_config.get("destination_folder")

        # Validate required configuration
        if not source_folder or not destination_folder:
            logger.error("Source and destination folders must be configured")
            return 1
        if source_folder == destination_folder:
            logger.error("Source and destination folders must be different")
            return 1

        # Get face recognition configuration
        face_config = config.get("face_recognition", {})
        provider_name = face_config.get("provider", "local")
        reference_photos_dir = face_config.get("reference_photos_dir", "./reference_photos")
        tolerance = face_config.get("tolerance", 0.6)

        # Get processing configuration
        processing = config.get("processing", {})
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

        provider = get_provider(provider_name, provider_config)

        # Load reference photos
        logger.info(f"Loading reference photos from {reference_photos_dir}...")
        reference_photos = _get_reference_photos(reference_photos_dir, image_extensions)

        if not reference_photos:
            logger.error(f"No reference photos found in {reference_photos_dir}")
            logger.error("Please add reference photos and run scripts/train_face_model.py first")
            return 1

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
        matches, processed, errors = process_images(
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

        # Perform operations
        perform_operations(matches, destination_folder, dbx_client, operation, log_file, dry_run, logger)

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
