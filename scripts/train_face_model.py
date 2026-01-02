#!/usr/bin/env python3
"""
Training script for local face recognition provider.

This script:
1. Loads all reference photos from the configured directory
2. Detects faces in each photo
3. Generates face encodings (the "training" process)
4. Validates the configuration
5. Provides diagnostic information about each photo

Usage:
    python scripts/train_face_model.py
"""

import glob
import logging
import os
import sys

# Add parent directory to path FIRST before other imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml  # noqa: E402

from scripts.face_recognizer.providers.local_provider import LocalFaceRecognitionProvider  # noqa: E402

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


def load_config():
    """Load configuration from config.yaml."""
    config_path = "config/config.yaml"
    if not os.path.exists(config_path):
        logger.error(f"Configuration file not found: {config_path}")
        logger.error("Please copy config/config.example.yaml to config/config.yaml and configure it")
        sys.exit(1)

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    return config


def get_reference_photos(reference_dir, image_extensions):
    """Get list of reference photos from directory."""
    if not os.path.exists(reference_dir):
        logger.error(f"Reference photos directory not found: {reference_dir}")
        sys.exit(1)

    photos = []
    for ext in image_extensions:
        # Handle both .jpg and jpg patterns
        pattern = f"{reference_dir}/*{ext}"
        photos.extend(glob.glob(pattern))
        # Also try without the dot
        if ext.startswith("."):
            pattern = f"{reference_dir}/*{ext[1:]}"
            photos.extend(glob.glob(pattern))

    # Remove duplicates
    photos = list(set(photos))

    # Filter out .DS_Store and other system files
    photos = [p for p in photos if not os.path.basename(p).startswith(".")]

    return sorted(photos)


def main():
    """Main training function."""
    print("=" * 70)
    print("Face Recognition Model Training")
    print("=" * 70)
    print()

    # Load configuration
    logger.info("Loading configuration...")
    config = load_config()

    face_config = config.get("face_recognition", {})
    reference_dir = face_config.get("reference_photos_dir", "./reference_photos")
    tolerance = face_config.get("tolerance", 0.6)
    image_extensions = config.get("processing", {}).get("image_extensions", [".jpg", ".jpeg", ".png", ".heic"])

    # Get local provider config (use defaults if not specified)
    local_config = face_config.get("local", {})

    # Use training-specific num_jitters if available, otherwise fall back to default
    training_config = local_config.get("training", {})
    training_num_jitters = training_config.get("num_jitters", local_config.get("num_jitters", 50))

    # Build config for provider with training parameters
    provider_config = {
        "model": local_config.get("model", "hog"),
        "encoding_model": local_config.get("encoding_model", "large"),
        "num_jitters": training_num_jitters,
        "tolerance": tolerance,
    }

    print("Configuration:")
    print(f"  Reference directory: {reference_dir}")
    print(f"  Tolerance: {tolerance}")
    print(f"  Detection model: {provider_config['model']}")
    print(f"  Encoding model: {provider_config['encoding_model']}")
    print(f"  Num jitters (training): {provider_config['num_jitters']}")
    print()

    # Get reference photos
    logger.info("Finding reference photos...")
    reference_photos = get_reference_photos(reference_dir, image_extensions)

    if not reference_photos:
        logger.error(f"No reference photos found in {reference_dir}")
        logger.error(f"Supported extensions: {', '.join(image_extensions)}")
        logger.error("")
        logger.error("Please add reference photos of the person you want to detect:")
        logger.error(f"  - Place 3-10 clear, well-lit photos in {reference_dir}")
        logger.error("  - Face should be clearly visible")
        logger.error("  - One face per photo (or target face should be prominent)")
        sys.exit(1)

    print(f"Found {len(reference_photos)} reference photo(s):")
    for photo in reference_photos:
        print(f"  - {os.path.basename(photo)}")
    print()

    # Initialize provider
    logger.info("Initializing local face recognition provider...")
    try:
        provider = LocalFaceRecognitionProvider(provider_config)
    except Exception as e:
        logger.error(f"Failed to initialize provider: {e}")
        logger.error(f"Exception type: {type(e).__name__}")
        import traceback

        traceback.print_exc()
        logger.error("")
        if isinstance(e, ImportError):
            logger.error("Please install face_recognition library:")
            logger.error("  macOS: ./scripts/installation/install_macos.sh")
            logger.error("  or manually: pip install face-recognition")
        sys.exit(1)

    # Validate configuration
    logger.info("Validating configuration...")
    is_valid, error_msg = provider.validate_configuration()
    if not is_valid:
        logger.error(f"Configuration validation failed: {error_msg}")
        sys.exit(1)

    print("✓ Configuration valid")
    print()

    # Load and process reference photos
    print("=" * 70)
    print("Processing Reference Photos")
    print("=" * 70)
    print()

    try:
        num_faces = provider.load_reference_photos(reference_photos)
        print()
        print("=" * 70)
        print("Training Complete!")
        print("=" * 70)
        print()
        print(f"✓ Successfully loaded {num_faces} reference face encoding(s)")
        print()
        print("Summary:")
        print(f"  Total photos processed: {len(reference_photos)}")
        print(f"  Faces detected: {num_faces}")
        print(f"  Success rate: {num_faces}/{len(reference_photos)} " f"({100.0 * num_faces / len(reference_photos):.1f}%)")
        print()
        print("Next Steps:")
        print("  1. Review any warnings above for photos that couldn't be processed")
        print("  2. Consider adding more reference photos if success rate is low")
        print("  3. Run the photo organizer with dry_run: true to test matching:")
        print("     python scripts/organize_photos.py")
        print()

    except Exception as e:
        logger.error(f"Training failed: {e}")
        print()
        print("Troubleshooting:")
        print("  - Ensure reference photos contain clear, visible faces")
        print("  - Try using different photos with better lighting")
        print("  - Check that photos are valid image files")
        print("  - Consider using 'cnn' model instead of 'hog' in config for better detection")
        sys.exit(1)


if __name__ == "__main__":
    main()
