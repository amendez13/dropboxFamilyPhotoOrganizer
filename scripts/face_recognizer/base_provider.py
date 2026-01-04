"""
Base abstract class for face recognition providers.
Defines the interface that all face recognition providers must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


@dataclass
class FaceEncoding:
    """Represents a face encoding with metadata."""

    encoding: np.ndarray
    source: str  # Source file path or identifier
    confidence: Optional[float] = None
    bounding_box: Optional[Tuple[int, int, int, int]] = None  # (top, right, bottom, left)


@dataclass
class FaceMatch:
    """Represents a face match result."""

    is_match: bool
    confidence: float  # 0.0 to 1.0
    distance: float  # Distance metric (lower = more similar)
    matched_encoding: Optional[FaceEncoding] = None


class BaseFaceRecognitionProvider(ABC):
    """
    Abstract base class for face recognition providers.
    All providers (local, AWS, Azure, etc.) must implement these methods.
    """

    def __init__(self, config: Dict[str, Any]):
        """
        Initialize the provider with configuration.

        Args:
            config: Provider-specific configuration dictionary
        """
        self.config = config
        self.reference_encodings: List[FaceEncoding] = []

    @abstractmethod
    def load_reference_photos(self, photo_paths: List[str]) -> int:
        """
        Load and encode reference photos of the target person.

        Args:
            photo_paths: List of file paths to reference photos

        Returns:
            Number of faces successfully encoded

        Raises:
            Exception if no faces found in any reference photo
        """
        pass

    @abstractmethod
    def detect_faces(self, image_data: bytes, source: str = "unknown") -> List[FaceEncoding]:
        """
        Detect faces in an image and return their encodings.

        Args:
            image_data: Raw image bytes
            source: Optional identifier for the image source

        Returns:
            List of FaceEncoding objects (empty if no faces detected)
        """
        pass

    @abstractmethod
    def compare_faces(self, face_encoding: FaceEncoding, tolerance: float = 0.6) -> FaceMatch:
        """
        Compare a face encoding against reference encodings.

        Args:
            face_encoding: The face encoding to compare
            tolerance: Matching tolerance (provider-specific meaning)

        Returns:
            FaceMatch object with match results
        """
        pass

    def find_matches_in_image(
        self, image_data: bytes, source: str = "unknown", tolerance: float = 0.6
    ) -> Tuple[List[FaceMatch], int]:
        """
        Detect faces in an image and check for matches against reference faces.

        Args:
            image_data: Raw image bytes
            source: Identifier for the image source
            tolerance: Matching tolerance

        Returns:
            Tuple of (list of matches, total faces detected)
        """
        detected_faces = self.detect_faces(image_data, source)
        matches = []

        for face in detected_faces:
            match = self.compare_faces(face, tolerance)
            if match.is_match:
                matches.append(match)

        return matches, len(detected_faces)

    @abstractmethod
    def get_provider_name(self) -> str:
        """
        Get the name of the provider.

        Returns:
            Provider name (e.g., "local", "aws", "azure")
        """
        pass

    def get_reference_count(self) -> int:
        """
        Get the number of reference face encodings loaded.

        Returns:
            Count of reference encodings
        """
        return len(self.reference_encodings)

    @abstractmethod
    def validate_configuration(self) -> Tuple[bool, Optional[str]]:
        """
        Validate the provider configuration.

        Returns:
            Tuple of (is_valid, error_message)
        """
        pass
