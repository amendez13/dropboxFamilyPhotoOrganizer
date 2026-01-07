"""Unit tests for base_provider.py module."""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from face_recognizer.base_provider import BaseFaceRecognitionProvider, FaceEncoding, FaceMatch  # noqa: E402

# Constants for realistic test data
# Face encodings from face_recognition library are 128-dimensional vectors
FACE_ENCODING_DIMENSION = 128


def create_mock_encoding(seed: int = 0) -> np.ndarray:
    """Create a deterministic mock face encoding for testing.

    Args:
        seed: Random seed for reproducibility

    Returns:
        A 128-dimensional numpy array representing a face encoding
    """
    np.random.seed(seed)
    return np.random.random(FACE_ENCODING_DIMENSION)


class TestFaceEncodingDataclass:
    """Test FaceEncoding dataclass."""

    def test_face_encoding_creation_with_required_fields(self) -> None:
        """Test creating FaceEncoding with only required fields."""
        encoding = create_mock_encoding(seed=42)
        face_encoding = FaceEncoding(encoding=encoding, source="test.jpg")

        assert np.array_equal(face_encoding.encoding, encoding)
        assert face_encoding.source == "test.jpg"
        assert face_encoding.confidence is None
        assert face_encoding.bounding_box is None
        # Verify encoding dimension
        assert len(face_encoding.encoding) == FACE_ENCODING_DIMENSION

    def test_face_encoding_creation_with_all_fields(self) -> None:
        """Test creating FaceEncoding with all fields."""
        encoding = create_mock_encoding(seed=43)
        face_encoding = FaceEncoding(
            encoding=encoding,
            source="test.jpg",
            confidence=0.95,
            bounding_box=(10, 200, 150, 50),
        )

        assert np.array_equal(face_encoding.encoding, encoding)
        assert face_encoding.source == "test.jpg"
        assert face_encoding.confidence == 0.95
        assert face_encoding.bounding_box == (10, 200, 150, 50)


class TestFaceMatchDataclass:
    """Test FaceMatch dataclass."""

    def test_face_match_creation_with_required_fields(self) -> None:
        """Test creating FaceMatch with only required fields."""
        face_match = FaceMatch(is_match=True, confidence=0.85, distance=0.3)

        assert face_match.is_match is True
        assert face_match.confidence == 0.85
        assert face_match.distance == 0.3
        assert face_match.matched_encoding is None

    def test_face_match_creation_with_all_fields(self) -> None:
        """Test creating FaceMatch with all fields."""
        encoding = create_mock_encoding(seed=44)
        face_encoding = FaceEncoding(encoding=encoding, source="reference.jpg")
        face_match = FaceMatch(
            is_match=True,
            confidence=0.9,
            distance=0.25,
            matched_encoding=face_encoding,
        )

        assert face_match.is_match is True
        assert face_match.confidence == 0.9
        assert face_match.distance == 0.25
        assert face_match.matched_encoding == face_encoding

    def test_face_match_no_match(self) -> None:
        """Test FaceMatch when there's no match."""
        face_match = FaceMatch(is_match=False, confidence=0.2, distance=0.8)

        assert face_match.is_match is False
        assert face_match.confidence == 0.2
        assert face_match.distance == 0.8


class ConcreteProvider(BaseFaceRecognitionProvider):
    """Concrete implementation of BaseFaceRecognitionProvider for testing."""

    def __init__(self, config: Dict[str, Any]) -> None:
        """Initialize the concrete provider."""
        super().__init__(config)
        self._mock_detected_faces: List[FaceEncoding] = []
        self._mock_match_result: Optional[FaceMatch] = None

    def set_mock_detected_faces(self, faces: List[FaceEncoding]) -> None:
        """Set mock detected faces for testing."""
        self._mock_detected_faces = faces

    def set_mock_match_result(self, result: FaceMatch) -> None:
        """Set mock match result for testing."""
        self._mock_match_result = result

    def load_reference_photos(self, photo_paths: List[str]) -> int:
        """Load reference photos implementation."""
        for path in photo_paths:
            encoding = FaceEncoding(
                encoding=create_mock_encoding(seed=hash(path) % 1000),
                source=path,
            )
            self.reference_encodings.append(encoding)
        return len(photo_paths)

    def detect_faces(self, image_data: bytes, source: str = "unknown") -> List[FaceEncoding]:
        """Detect faces implementation."""
        return self._mock_detected_faces

    def compare_faces(self, face_encoding: FaceEncoding, tolerance: float = 0.6) -> FaceMatch:
        """Compare faces implementation."""
        if self._mock_match_result:
            return self._mock_match_result
        return FaceMatch(is_match=False, confidence=0.0, distance=1.0)

    def get_provider_name(self) -> str:
        """Get provider name implementation."""
        return "concrete_test"

    def validate_configuration(self) -> Tuple[bool, Optional[str]]:
        """Validate configuration implementation."""
        if "invalid" in self.config:
            return False, "Configuration contains invalid key"
        return True, None


class TestBaseFaceRecognitionProvider:
    """Test BaseFaceRecognitionProvider abstract base class."""

    def test_init_stores_config(self) -> None:
        """Test that __init__ stores the config dictionary."""
        config = {"model": "hog", "tolerance": 0.5}
        provider = ConcreteProvider(config)

        assert provider.config == config
        assert provider.config["model"] == "hog"
        assert provider.config["tolerance"] == 0.5

    def test_init_initializes_empty_reference_encodings(self) -> None:
        """Test that __init__ initializes an empty reference_encodings list."""
        provider = ConcreteProvider({})

        assert provider.reference_encodings == []
        assert isinstance(provider.reference_encodings, list)

    def test_get_reference_count_empty(self) -> None:
        """Test get_reference_count with no reference encodings."""
        provider = ConcreteProvider({})

        assert provider.get_reference_count() == 0

    def test_get_reference_count_with_encodings(self) -> None:
        """Test get_reference_count after loading reference photos."""
        provider = ConcreteProvider({})
        provider.load_reference_photos(["photo1.jpg", "photo2.jpg", "photo3.jpg"])

        assert provider.get_reference_count() == 3

    def test_find_matches_in_image_no_faces_detected(self) -> None:
        """Test find_matches_in_image when no faces are detected."""
        provider = ConcreteProvider({})
        provider.set_mock_detected_faces([])

        matches, total_faces = provider.find_matches_in_image(b"image_data", "test.jpg")

        assert matches == []
        assert total_faces == 0

    def test_find_matches_in_image_faces_detected_no_match(self) -> None:
        """Test find_matches_in_image when faces are detected but don't match."""
        provider = ConcreteProvider({})

        # Set up mock detected faces with realistic 128-d encoding
        face1 = FaceEncoding(encoding=create_mock_encoding(seed=100), source="test.jpg")
        provider.set_mock_detected_faces([face1])
        provider.set_mock_match_result(FaceMatch(is_match=False, confidence=0.3, distance=0.7))

        matches, total_faces = provider.find_matches_in_image(b"image_data", "test.jpg")

        assert matches == []
        assert total_faces == 1

    def test_find_matches_in_image_faces_detected_with_match(self) -> None:
        """Test find_matches_in_image when faces are detected and match."""
        provider = ConcreteProvider({})

        # Set up mock detected faces with realistic 128-d encoding
        face1 = FaceEncoding(encoding=create_mock_encoding(seed=101), source="test.jpg")
        provider.set_mock_detected_faces([face1])
        match_result = FaceMatch(is_match=True, confidence=0.9, distance=0.2)
        provider.set_mock_match_result(match_result)

        matches, total_faces = provider.find_matches_in_image(b"image_data", "test.jpg")

        assert len(matches) == 1
        assert matches[0].is_match is True
        assert matches[0].confidence == 0.9
        assert total_faces == 1

    def test_find_matches_in_image_multiple_faces_mixed_results(self) -> None:
        """Test find_matches_in_image with multiple faces, some matching."""
        provider = ConcreteProvider({})

        # Set up multiple detected faces with realistic 128-d encodings
        face1 = FaceEncoding(encoding=create_mock_encoding(seed=102), source="test.jpg")
        face2 = FaceEncoding(encoding=create_mock_encoding(seed=103), source="test.jpg")
        face3 = FaceEncoding(encoding=create_mock_encoding(seed=104), source="test.jpg")
        provider.set_mock_detected_faces([face1, face2, face3])

        # Create a provider that returns alternating match results
        call_count = [0]

        def alternating_match(face_encoding: FaceEncoding, tolerance: float = 0.6) -> FaceMatch:
            call_count[0] += 1
            if call_count[0] % 2 == 1:  # First and third calls match
                return FaceMatch(is_match=True, confidence=0.85, distance=0.3)
            return FaceMatch(is_match=False, confidence=0.2, distance=0.8)

        provider.compare_faces = alternating_match  # type: ignore[method-assign]

        matches, total_faces = provider.find_matches_in_image(b"image_data", "test.jpg")

        assert len(matches) == 2  # First and third faces match
        assert total_faces == 3

    def test_find_matches_in_image_uses_custom_tolerance(self) -> None:
        """Test that find_matches_in_image passes tolerance to compare_faces."""
        provider = ConcreteProvider({})
        face1 = FaceEncoding(encoding=create_mock_encoding(seed=105), source="test.jpg")
        provider.set_mock_detected_faces([face1])

        # Track the tolerance passed to compare_faces
        captured_tolerance: List[float] = []

        def capture_tolerance(face_encoding: FaceEncoding, tolerance: float = 0.6) -> FaceMatch:
            captured_tolerance.append(tolerance)
            return FaceMatch(is_match=False, confidence=0.0, distance=1.0)

        provider.compare_faces = capture_tolerance  # type: ignore[method-assign]

        provider.find_matches_in_image(b"image_data", "test.jpg", tolerance=0.4)

        assert len(captured_tolerance) == 1
        assert captured_tolerance[0] == 0.4

    def test_find_matches_in_image_uses_default_source(self) -> None:
        """Test find_matches_in_image with default source parameter."""
        provider = ConcreteProvider({})
        provider.set_mock_detected_faces([])

        # Just ensure it doesn't raise an error with default source
        matches, total_faces = provider.find_matches_in_image(b"image_data")

        assert matches == []
        assert total_faces == 0

    def test_concrete_provider_get_provider_name(self) -> None:
        """Test get_provider_name returns correct name."""
        provider = ConcreteProvider({})

        assert provider.get_provider_name() == "concrete_test"

    def test_concrete_provider_validate_configuration_valid(self) -> None:
        """Test validate_configuration with valid config."""
        provider = ConcreteProvider({"model": "hog"})

        is_valid, error = provider.validate_configuration()

        assert is_valid is True
        assert error is None

    def test_concrete_provider_validate_configuration_invalid(self) -> None:
        """Test validate_configuration with invalid config."""
        provider = ConcreteProvider({"invalid": True})

        is_valid, error = provider.validate_configuration()

        assert is_valid is False
        assert error == "Configuration contains invalid key"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
