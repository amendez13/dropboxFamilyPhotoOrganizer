"""
Face encoding cache module for persisting and loading face encodings.
Provides efficient caching of face encodings to avoid recomputing them every time.
"""

import os
import pickle
import hashlib
import logging
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime
import numpy as np

from scripts.face_recognition.base_provider import FaceEncoding


@dataclass
class EncodingCacheMetadata:
    """Metadata for cached encodings to validate cache freshness."""
    reference_photo_paths: List[str]
    photo_mtimes: Dict[str, float]  # path -> modification time
    cache_created_at: str
    config_hash: str  # Hash of relevant config (tolerance, model, etc.)
    provider_name: str
    encoding_count: int


class EncodingCache:
    """
    Manages persistence and loading of face encodings with automatic cache invalidation.

    Features:
    - Save/load encodings to/from pickle file
    - Automatic cache invalidation when reference photos change
    - Config-aware caching (regenerates if settings change)
    - Safe fallback if cache is corrupted or outdated
    """

    def __init__(self, cache_file_path: Optional[str] = None):
        """
        Initialize encoding cache.

        Args:
            cache_file_path: Path to cache file. If None, caching is disabled.
        """
        self.cache_file_path = cache_file_path
        self.logger = logging.getLogger(__name__)

    def _compute_config_hash(self, config: Dict) -> str:
        """
        Compute hash of configuration to detect changes.

        Args:
            config: Configuration dictionary

        Returns:
            MD5 hash of relevant configuration values
        """
        # Extract only relevant config values that affect encoding
        relevant_config = {
            'tolerance': config.get('tolerance', 0.6),
            'model': config.get('model', 'hog'),
            'num_jitters': config.get('num_jitters', 1),
        }

        config_str = str(sorted(relevant_config.items()))
        return hashlib.md5(config_str.encode()).hexdigest()

    def _get_photo_mtimes(self, photo_paths: List[str]) -> Dict[str, float]:
        """
        Get modification times for reference photos.

        Args:
            photo_paths: List of photo file paths

        Returns:
            Dictionary mapping path to modification time
        """
        mtimes = {}
        for path in photo_paths:
            if os.path.exists(path):
                mtimes[path] = os.path.getmtime(path)
            else:
                # If photo doesn't exist, set mtime to 0 to force regeneration
                mtimes[path] = 0.0
        return mtimes

    def _validate_cache(
        self,
        metadata: EncodingCacheMetadata,
        reference_photo_paths: List[str],
        config: Dict,
        provider_name: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate cached encodings against current state.

        Args:
            metadata: Cached metadata
            reference_photo_paths: Current reference photo paths
            config: Current configuration
            provider_name: Current provider name

        Returns:
            Tuple of (is_valid, reason_if_invalid)
        """
        # Check provider name
        if metadata.provider_name != provider_name:
            return False, f"Provider changed from {metadata.provider_name} to {provider_name}"

        # Check config hash
        current_config_hash = self._compute_config_hash(config)
        if metadata.config_hash != current_config_hash:
            return False, "Configuration settings changed"

        # Check if reference photo paths changed
        cached_paths = set(metadata.reference_photo_paths)
        current_paths = set(reference_photo_paths)
        if cached_paths != current_paths:
            return False, "Reference photo paths changed"

        # Check if reference photos were modified
        current_mtimes = self._get_photo_mtimes(reference_photo_paths)
        for path, cached_mtime in metadata.photo_mtimes.items():
            current_mtime = current_mtimes.get(path, 0.0)
            if abs(current_mtime - cached_mtime) > 0.1:  # Allow small float differences
                return False, f"Reference photo modified: {path}"

        # Check if any reference photo is missing
        for path in reference_photo_paths:
            if not os.path.exists(path):
                return False, f"Reference photo not found: {path}"

        return True, None

    def save_encodings(
        self,
        encodings: List[FaceEncoding],
        reference_photo_paths: List[str],
        config: Dict,
        provider_name: str
    ) -> bool:
        """
        Save face encodings to cache file.

        Args:
            encodings: List of face encodings to cache
            reference_photo_paths: Paths to reference photos
            config: Configuration dictionary
            provider_name: Name of the provider

        Returns:
            True if saved successfully, False otherwise
        """
        if not self.cache_file_path:
            return False

        try:
            # Create metadata
            metadata = EncodingCacheMetadata(
                reference_photo_paths=reference_photo_paths,
                photo_mtimes=self._get_photo_mtimes(reference_photo_paths),
                cache_created_at=datetime.now().isoformat(),
                config_hash=self._compute_config_hash(config),
                provider_name=provider_name,
                encoding_count=len(encodings)
            )

            # Prepare cache data
            cache_data = {
                'metadata': asdict(metadata),
                'encodings': [
                    {
                        'encoding': enc.encoding.tolist(),  # Convert numpy to list
                        'source': enc.source,
                        'confidence': enc.confidence,
                        'bounding_box': enc.bounding_box
                    }
                    for enc in encodings
                ]
            }

            # Ensure cache directory exists
            cache_dir = os.path.dirname(os.path.abspath(self.cache_file_path))
            if cache_dir:
                os.makedirs(cache_dir, exist_ok=True)

            # Save to file
            with open(self.cache_file_path, 'wb') as f:
                pickle.dump(cache_data, f, protocol=pickle.HIGHEST_PROTOCOL)

            self.logger.info(
                f"Saved {len(encodings)} face encoding(s) to cache: {self.cache_file_path}"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to save encodings to cache: {e}")
            return False

    def load_encodings(
        self,
        reference_photo_paths: List[str],
        config: Dict,
        provider_name: str
    ) -> Optional[List[FaceEncoding]]:
        """
        Load face encodings from cache if valid.

        Args:
            reference_photo_paths: Expected reference photo paths
            config: Current configuration
            provider_name: Current provider name

        Returns:
            List of FaceEncoding objects if cache is valid, None otherwise
        """
        if not self.cache_file_path:
            self.logger.debug("Caching disabled (no cache file path)")
            return None

        if not os.path.exists(self.cache_file_path):
            self.logger.debug(f"Cache file not found: {self.cache_file_path}")
            return None

        try:
            # Load cache file
            with open(self.cache_file_path, 'rb') as f:
                cache_data = pickle.load(f)

            # Extract metadata
            metadata_dict = cache_data.get('metadata', {})
            metadata = EncodingCacheMetadata(**metadata_dict)

            # Validate cache
            is_valid, reason = self._validate_cache(
                metadata,
                reference_photo_paths,
                config,
                provider_name
            )

            if not is_valid:
                self.logger.info(f"Cache invalidated: {reason}")
                return None

            # Load encodings
            encodings_data = cache_data.get('encodings', [])
            encodings = []

            for enc_data in encodings_data:
                encoding = FaceEncoding(
                    encoding=np.array(enc_data['encoding']),
                    source=enc_data['source'],
                    confidence=enc_data['confidence'],
                    bounding_box=tuple(enc_data['bounding_box']) if enc_data['bounding_box'] else None
                )
                encodings.append(encoding)

            self.logger.info(
                f"Loaded {len(encodings)} face encoding(s) from cache "
                f"(created: {metadata.cache_created_at})"
            )
            return encodings

        except Exception as e:
            self.logger.error(f"Failed to load encodings from cache: {e}")
            self.logger.info("Will regenerate encodings from reference photos")
            return None

    def clear_cache(self) -> bool:
        """
        Delete the cache file.

        Returns:
            True if deleted successfully or file doesn't exist, False on error
        """
        if not self.cache_file_path:
            return True

        try:
            if os.path.exists(self.cache_file_path):
                os.remove(self.cache_file_path)
                self.logger.info(f"Cache file deleted: {self.cache_file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Failed to delete cache file: {e}")
            return False
