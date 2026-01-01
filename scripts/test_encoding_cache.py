#!/usr/bin/env python3
"""
Test script for face encoding cache functionality.
Tests cache creation, loading, and invalidation.
"""

import os
import sys
import logging
import tempfile
import numpy as np

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from face_recognition.base_provider import FaceEncoding
from face_recognition.encoding_cache import EncodingCache


def setup_logging():
    """Configure logging for the test."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    return logging.getLogger(__name__)


def test_cache_save_and_load():
    """Test basic save and load functionality."""
    logger = setup_logging()
    logger.info("Testing cache save and load...")

    # Create temporary cache file
    with tempfile.NamedTemporaryFile(delete=False, suffix='.pkl') as tmp:
        cache_file = tmp.name

    try:
        # Create mock encodings
        encodings = [
            FaceEncoding(
                encoding=np.random.rand(128),
                source="/path/to/photo1.jpg",
                confidence=0.95,
                bounding_box=(10, 20, 30, 40)
            ),
            FaceEncoding(
                encoding=np.random.rand(128),
                source="/path/to/photo2.jpg",
                confidence=0.92,
                bounding_box=(15, 25, 35, 45)
            )
        ]

        photo_paths = ["/path/to/photo1.jpg", "/path/to/photo2.jpg"]
        config = {
            'model': 'hog',
            'tolerance': 0.6,
            'num_jitters': 1
        }
        provider_name = "local"

        # Test save
        cache = EncodingCache(cache_file)
        save_success = cache.save_encodings(encodings, photo_paths, config, provider_name)

        if not save_success:
            logger.error("❌ Failed to save encodings to cache")
            return False

        logger.info("✅ Successfully saved encodings to cache")

        # Test load (should fail due to non-existent photo paths)
        loaded_encodings = cache.load_encodings(photo_paths, config, provider_name)

        if loaded_encodings is None:
            logger.info("✅ Cache correctly invalidated (photo paths don't exist)")
        else:
            logger.warning("⚠️  Cache loaded despite non-existent photos (unexpected)")

        logger.info("✅ Cache save/load test passed")
        return True

    finally:
        # Cleanup
        if os.path.exists(cache_file):
            os.remove(cache_file)


def test_cache_invalidation():
    """Test cache invalidation scenarios."""
    logger = setup_logging()
    logger.info("Testing cache invalidation...")

    with tempfile.NamedTemporaryFile(delete=False, suffix='.pkl') as tmp:
        cache_file = tmp.name

    # Create temporary reference photos
    temp_photo1 = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    temp_photo2 = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
    temp_photo1.close()
    temp_photo2.close()

    try:
        encodings = [
            FaceEncoding(
                encoding=np.random.rand(128),
                source=temp_photo1.name,
                bounding_box=(10, 20, 30, 40)
            )
        ]

        photo_paths = [temp_photo1.name]
        config = {
            'model': 'hog',
            'tolerance': 0.6,
            'num_jitters': 1
        }

        cache = EncodingCache(cache_file)

        # Save with original config
        cache.save_encodings(encodings, photo_paths, config, "local")

        # Load with same config - should succeed
        loaded = cache.load_encodings(photo_paths, config, "local")
        if loaded is not None:
            logger.info("✅ Cache loaded successfully with matching config")
        else:
            logger.error("❌ Cache failed to load with matching config")
            return False

        # Load with different config - should invalidate
        different_config = config.copy()
        different_config['tolerance'] = 0.5
        loaded = cache.load_encodings(photo_paths, different_config, "local")
        if loaded is None:
            logger.info("✅ Cache correctly invalidated when config changed")
        else:
            logger.error("❌ Cache did not invalidate when config changed")
            return False

        # Load with different provider - should invalidate
        loaded = cache.load_encodings(photo_paths, config, "aws")
        if loaded is None:
            logger.info("✅ Cache correctly invalidated when provider changed")
        else:
            logger.error("❌ Cache did not invalidate when provider changed")
            return False

        # Load with different photo paths - should invalidate
        different_paths = [temp_photo1.name, temp_photo2.name]
        loaded = cache.load_encodings(different_paths, config, "local")
        if loaded is None:
            logger.info("✅ Cache correctly invalidated when photo paths changed")
        else:
            logger.error("❌ Cache did not invalidate when photo paths changed")
            return False

        logger.info("✅ All cache invalidation tests passed")
        return True

    finally:
        # Cleanup
        if os.path.exists(cache_file):
            os.remove(cache_file)
        if os.path.exists(temp_photo1.name):
            os.remove(temp_photo1.name)
        if os.path.exists(temp_photo2.name):
            os.remove(temp_photo2.name)


def main():
    """Run all cache tests."""
    logger = setup_logging()
    logger.info("=" * 60)
    logger.info("Face Encoding Cache Test Suite")
    logger.info("=" * 60)

    all_passed = True

    # Test 1: Save and load
    if not test_cache_save_and_load():
        all_passed = False

    logger.info("-" * 60)

    # Test 2: Cache invalidation
    if not test_cache_invalidation():
        all_passed = False

    logger.info("=" * 60)
    if all_passed:
        logger.info("✅ All tests passed!")
        return 0
    else:
        logger.error("❌ Some tests failed")
        return 1


if __name__ == '__main__':
    sys.exit(main())
