"""
Test script to verify Dropbox API connection and configuration.
Supports both OAuth 2.0 and legacy access token authentication.
"""

import os
import sys
from typing import Any, Dict, List

import yaml

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.auth import DropboxClientFactory  # noqa: E402
from scripts.dropbox_client import DropboxClient  # noqa: E402
from scripts.logging_utils import get_logger, setup_logging  # noqa: E402


def load_config(config_path: str = "config/config.yaml") -> Dict[str, Any]:
    """Load configuration from YAML file."""
    try:
        with open(config_path, "r") as f:
            config: Dict[str, Any] = yaml.safe_load(f)
            return config
    except FileNotFoundError:
        print(f"Error: Configuration file '{config_path}' not found.")
        print("Please copy config/config.example.yaml to config/config.yaml and fill in your settings.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing configuration file: {e}")
        sys.exit(1)


def _test_connection(client: DropboxClient) -> bool:
    """Test Dropbox connection."""
    print("\n[Test 1] Verifying Dropbox connection...")
    if client.verify_connection():
        print("✓ Successfully connected to Dropbox")
        return True
    else:
        print("✗ Failed to connect to Dropbox")
        print("  Please check your access token in config/config.yaml")
        return False


def _test_file_listing(client: DropboxClient, source_folder: str, image_extensions: List[str]) -> int:
    """Test file listing in source folder."""
    print(f"\n[Test 2] Listing files in source folder: {source_folder}")
    file_count = 0
    print(f"\nScanning for image files ({', '.join(image_extensions)})...")

    for file_metadata in client.list_folder_recursive(source_folder, image_extensions):
        file_count += 1
        if file_count <= 10:  # Show first 10 files
            print(f"  - {file_metadata.path_display} ({file_metadata.size} bytes)")
        elif file_count == 11:
            print("  ...")

    print(f"\n✓ Found {file_count} image files in '{source_folder}'")

    if file_count == 0:
        print("\nNote: No image files found. Please check:")
        print(f"  1. The folder path is correct: {source_folder}")
        print(f"  2. The folder contains images with extensions: {', '.join(image_extensions)}")
        print("  3. You have read permissions for this folder")

    return file_count


def _test_thumbnail(client: DropboxClient, source_folder: str, image_extensions: List[str], config: Dict[str, Any]) -> None:
    """Test thumbnail download."""
    print("\n[Test 3] Testing thumbnail download...")
    try:
        # Get first file for testing
        first_file = next(client.list_folder_recursive(source_folder, image_extensions))
        thumbnail_size = config["face_recognition"]["thumbnail_size"]

        print(f"Getting thumbnail for: {first_file.name}")
        thumbnail_data = client.get_thumbnail(first_file.path_display, size=thumbnail_size)

        if thumbnail_data:
            print(f"✓ Successfully retrieved thumbnail ({len(thumbnail_data)} bytes)")
        else:
            print("✗ Could not retrieve thumbnail")
            print("  Note: Some file types may not support thumbnails")
    except StopIteration:
        print("✗ No files found to test thumbnail download")
        print("  Note: Cannot test thumbnails without image files")


def main() -> None:
    """Test Dropbox connection and list files."""
    import argparse

    parser = argparse.ArgumentParser(description="Test Dropbox connection and configuration")
    parser.add_argument("--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()

    # Setup logging
    setup_logging(args.verbose)
    logger = get_logger(__name__)

    print("=" * 60)
    print("Dropbox Connection Test")
    print("=" * 60)

    # Load configuration
    logger.info("Loading configuration...")
    config = load_config()

    # Extract settings
    source_folder = config["dropbox"]["source_folder"]
    image_extensions = config["processing"]["image_extensions"]

    # Initialize Dropbox client using factory
    logger.info("Initializing Dropbox client...")
    try:
        factory = DropboxClientFactory(config)
        client = factory.create_client()
    except ValueError as e:
        print(f"\n✗ Failed to create Dropbox client: {e}")
        sys.exit(1)

    # Test 1: Verify connection
    if not _test_connection(client):
        sys.exit(1)

    # Test 2: List files in source folder
    try:
        file_count = _test_file_listing(client, source_folder, image_extensions)
    except Exception as e:
        print(f"✗ Error listing files: {e}")
        print("\nPossible issues:")
        print(f"  1. The folder '{source_folder}' doesn't exist")
        print("  2. Insufficient permissions (check App Console → Permissions)")
        print("  3. Invalid folder path (should start with '/')")
        sys.exit(1)

    # Test 3: Test thumbnail API
    if file_count > 0:
        try:
            _test_thumbnail(client, source_folder, image_extensions, config)
        except Exception as e:
            print(f"✗ Error testing thumbnail: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("Connection test completed successfully!")
    print("=" * 60)
    print("\nNext steps:")
    print("  1. Add reference photos to the 'reference_photos/' directory")
    print("  2. Update face_recognition settings in config/config.yaml")
    print("  3. Run the main photo organizer script")
    print()


if __name__ == "__main__":
    main()
