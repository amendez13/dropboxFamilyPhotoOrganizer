"""
Local face recognition provider using the face_recognition library (dlib-based).
Runs entirely offline without external API calls.
"""

import os
import logging
from typing import List, Dict, Tuple, Optional
import numpy as np

try:
    import face_recognition
    from PIL import Image
    import io
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False

import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from scripts.face_recognition.base_provider import (
    BaseFaceRecognitionProvider,
    FaceEncoding,
    FaceMatch
)
from scripts.face_recognition.encoding_cache import EncodingCache


class LocalFaceRecognitionProvider(BaseFaceRecognitionProvider):
    """
    Local face recognition provider using face_recognition library.

    Pros:
    - Free, no API costs
    - Works offline
    - Good accuracy for family photos
    - Privacy-friendly (no data leaves your machine)

    Cons:
    - Requires dlib installation (can be complex)
    - Slower than cloud APIs for large batches
    - Limited to CPU processing (no GPU acceleration by default)
    """

    def __init__(self, config: Dict):
        """
        Initialize local face recognition provider.

        Args:
            config: Configuration dictionary with optional keys:
                - model: 'hog' (faster, CPU) or 'cnn' (more accurate, GPU)
                - num_jitters: Number of times to re-sample face for encoding (default: 1)
                - tolerance: Default matching tolerance (default: 0.6)
                - cache_file: Path to cache file for persisting encodings (optional)
        """
        super().__init__(config)
        self.logger = logging.getLogger(__name__)

        if not FACE_RECOGNITION_AVAILABLE:
            raise ImportError(
                "face_recognition library not installed. "
                "Install with: pip install face-recognition"
            )

        self.model = config.get('model', 'hog')  # 'hog' or 'cnn'
        self.num_jitters = config.get('num_jitters', 1)
        self.default_tolerance = config.get('tolerance', 0.6)

        # Initialize encoding cache
        cache_file = config.get('cache_file')
        self.encoding_cache = EncodingCache(cache_file)

    def get_provider_name(self) -> str:
        """Get provider name."""
        return "local"

    def validate_configuration(self) -> Tuple[bool, Optional[str]]:
        """Validate configuration."""
        if not FACE_RECOGNITION_AVAILABLE:
            return False, "face_recognition library not installed"

        if self.model not in ['hog', 'cnn']:
            return False, f"Invalid model: {self.model}. Must be 'hog' or 'cnn'"

        return True, None

    def load_reference_photos(self, photo_paths: List[str]) -> int:
        """
        Load reference photos and extract face encodings.
        Uses cache if available and valid, otherwise generates new encodings.

        Args:
            photo_paths: List of paths to reference photos

        Returns:
            Number of faces successfully encoded
        """
        # Try to load from cache first
        cached_encodings = self.encoding_cache.load_encodings(
            photo_paths,
            self.config,
            self.get_provider_name()
        )

        if cached_encodings is not None:
            self.reference_encodings = cached_encodings
            self.logger.info(
                f"Loaded {len(self.reference_encodings)} reference face(s) from cache"
            )
            return len(self.reference_encodings)

        # Cache miss - generate encodings from reference photos
        self.logger.info("Generating face encodings from reference photos...")
        self.reference_encodings = []

        for photo_path in photo_paths:
            if not os.path.exists(photo_path):
                self.logger.warning(f"Reference photo not found: {photo_path}")
                continue

            try:
                # Load image
                image = face_recognition.load_image_file(photo_path)

                # Find faces
                face_locations = face_recognition.face_locations(image, model=self.model)

                if len(face_locations) == 0:
                    self.logger.warning(f"No faces found in reference photo: {photo_path}")
                    continue

                if len(face_locations) > 1:
                    self.logger.warning(
                        f"Multiple faces found in {photo_path}. "
                        f"Using the first face only."
                    )

                # Encode faces
                encodings = face_recognition.face_encodings(
                    image,
                    known_face_locations=face_locations,
                    num_jitters=self.num_jitters
                )

                if encodings:
                    # Use first face
                    self.reference_encodings.append(FaceEncoding(
                        encoding=encodings[0],
                        source=photo_path,
                        bounding_box=face_locations[0]
                    ))
                    self.logger.info(f"Loaded reference face from: {photo_path}")

            except Exception as e:
                self.logger.error(f"Error processing reference photo {photo_path}: {e}")

        if len(self.reference_encodings) == 0:
            raise Exception("No reference faces could be loaded")

        self.logger.info(f"Generated {len(self.reference_encodings)} reference face(s)")

        # Save to cache for future use
        self.encoding_cache.save_encodings(
            self.reference_encodings,
            photo_paths,
            self.config,
            self.get_provider_name()
        )

        return len(self.reference_encodings)

    def detect_faces(self, image_data: bytes, source: str = "unknown") -> List[FaceEncoding]:
        """
        Detect faces in image data.

        Args:
            image_data: Raw image bytes
            source: Image source identifier

        Returns:
            List of detected face encodings
        """
        try:
            # Convert bytes to image
            image = Image.open(io.BytesIO(image_data))

            # Convert to RGB if necessary
            if image.mode != 'RGB':
                image = image.convert('RGB')

            # Convert to numpy array
            image_array = np.array(image)

            # Find faces
            face_locations = face_recognition.face_locations(image_array, model=self.model)

            if not face_locations:
                return []

            # Encode faces
            encodings = face_recognition.face_encodings(
                image_array,
                known_face_locations=face_locations,
                num_jitters=self.num_jitters
            )

            # Create FaceEncoding objects
            face_encodings = []
            for encoding, location in zip(encodings, face_locations):
                face_encodings.append(FaceEncoding(
                    encoding=encoding,
                    source=source,
                    bounding_box=location
                ))

            return face_encodings

        except Exception as e:
            self.logger.error(f"Error detecting faces in {source}: {e}")
            return []

    def compare_faces(
        self,
        face_encoding: FaceEncoding,
        tolerance: Optional[float] = None
    ) -> FaceMatch:
        """
        Compare a face encoding against reference encodings.

        Args:
            face_encoding: Face encoding to compare
            tolerance: Matching tolerance (default: 0.6, lower = stricter)

        Returns:
            FaceMatch object
        """
        if tolerance is None:
            tolerance = self.default_tolerance

        if not self.reference_encodings:
            return FaceMatch(
                is_match=False,
                confidence=0.0,
                distance=1.0
            )

        # Get reference encodings as list
        reference_encodings_list = [ref.encoding for ref in self.reference_encodings]

        # Calculate distances
        distances = face_recognition.face_distance(
            reference_encodings_list,
            face_encoding.encoding
        )

        # Find best match
        best_match_idx = np.argmin(distances)
        best_distance = distances[best_match_idx]

        # Check if match is within tolerance
        is_match = best_distance <= tolerance

        # Convert distance to confidence (0.0 = different, 1.0 = identical)
        # Distance of 0.0 = perfect match (confidence 1.0)
        # Distance of 1.0 or more = no match (confidence 0.0)
        confidence = max(0.0, 1.0 - best_distance)

        return FaceMatch(
            is_match=is_match,
            confidence=confidence,
            distance=float(best_distance),
            matched_encoding=self.reference_encodings[best_match_idx] if is_match else None
        )
