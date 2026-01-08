"""Unit tests for local_provider.py face recognition module."""

import io
import sys
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pytest
from PIL import Image

# Add scripts directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestLocalProviderImport:
    """Test import behavior when face_recognition is not available."""

    def test_import_error_when_face_recognition_not_available(self):
        """Test that ImportError is raised when face_recognition is not installed."""
        from scripts.face_recognizer.providers import local_provider

        # Save the original value
        original_value = local_provider.FACE_RECOGNITION_AVAILABLE

        try:
            # Set to False to simulate face_recognition not being installed
            local_provider.FACE_RECOGNITION_AVAILABLE = False

            # The provider should raise ImportError when instantiated
            with pytest.raises(ImportError) as exc_info:
                local_provider.LocalFaceRecognitionProvider({})

            assert "face_recognition library not installed" in str(exc_info.value)
        finally:
            # Restore original value
            local_provider.FACE_RECOGNITION_AVAILABLE = original_value


class TestLocalFaceRecognitionProviderInit:
    """Test LocalFaceRecognitionProvider initialization."""

    @pytest.fixture
    def mock_face_recognition(self):
        """Mock face_recognition module."""
        with patch(
            "scripts.face_recognizer.providers.local_provider.FACE_RECOGNITION_AVAILABLE",
            True,
        ):
            yield

    def test_init_with_default_config(self, mock_face_recognition):
        """Test initialization with default configuration values."""
        from scripts.face_recognizer.providers.local_provider import LocalFaceRecognitionProvider

        provider = LocalFaceRecognitionProvider({})

        assert provider.model == "hog"
        assert provider.num_jitters == 1
        assert provider.encoding_model == "small"
        assert provider.default_tolerance == 0.6
        assert provider.reference_encodings == []

    def test_init_with_custom_config(self, mock_face_recognition):
        """Test initialization with custom configuration values."""
        from scripts.face_recognizer.providers.local_provider import LocalFaceRecognitionProvider

        config = {
            "model": "cnn",
            "num_jitters": 5,
            "encoding_model": "large",
            "tolerance": 0.4,
        }
        provider = LocalFaceRecognitionProvider(config)

        assert provider.model == "cnn"
        assert provider.num_jitters == 5
        assert provider.encoding_model == "large"
        assert provider.default_tolerance == 0.4

    def test_init_stores_config(self, mock_face_recognition):
        """Test that config is stored in parent class."""
        from scripts.face_recognizer.providers.local_provider import LocalFaceRecognitionProvider

        config = {"model": "hog", "custom_key": "value"}
        provider = LocalFaceRecognitionProvider(config)

        assert provider.config == config


class TestGetProviderName:
    """Test get_provider_name method."""

    def test_get_provider_name_returns_local(self):
        """Test that get_provider_name returns 'local'."""
        from scripts.face_recognizer.providers.local_provider import LocalFaceRecognitionProvider

        provider = LocalFaceRecognitionProvider({})
        assert provider.get_provider_name() == "local"


class TestValidateConfiguration:
    """Test validate_configuration method."""

    def test_validate_configuration_valid_hog_model(self):
        """Test validation passes for hog model."""
        from scripts.face_recognizer.providers.local_provider import LocalFaceRecognitionProvider

        provider = LocalFaceRecognitionProvider({"model": "hog"})
        is_valid, error = provider.validate_configuration()

        assert is_valid is True
        assert error is None

    def test_validate_configuration_valid_cnn_model(self):
        """Test validation passes for cnn model."""
        from scripts.face_recognizer.providers.local_provider import LocalFaceRecognitionProvider

        provider = LocalFaceRecognitionProvider({"model": "cnn"})
        is_valid, error = provider.validate_configuration()

        assert is_valid is True
        assert error is None

    def test_validate_configuration_invalid_model(self):
        """Test validation fails for invalid model."""
        from scripts.face_recognizer.providers.local_provider import LocalFaceRecognitionProvider

        provider = LocalFaceRecognitionProvider({"model": "invalid_model"})
        is_valid, error = provider.validate_configuration()

        assert is_valid is False
        assert "Invalid model" in error
        assert "invalid_model" in error
        assert "hog" in error
        assert "cnn" in error

    def test_validate_configuration_face_recognition_unavailable(self):
        """Test validation fails when face_recognition is not available."""
        from scripts.face_recognizer.providers import local_provider

        # Temporarily set FACE_RECOGNITION_AVAILABLE to False
        original_value = local_provider.FACE_RECOGNITION_AVAILABLE

        try:
            # We can't easily test this path without disrupting the import
            # Instead, test the validation logic directly by checking the method
            provider = local_provider.LocalFaceRecognitionProvider({})

            # Mock the availability flag on the module level
            local_provider.FACE_RECOGNITION_AVAILABLE = False
            is_valid, error = provider.validate_configuration()

            assert is_valid is False
            assert "face_recognition library not installed" in error
        finally:
            local_provider.FACE_RECOGNITION_AVAILABLE = original_value


class TestLoadReferencePhotos:
    """Test load_reference_photos method."""

    @pytest.fixture
    def provider(self):
        """Create a LocalFaceRecognitionProvider instance."""
        from scripts.face_recognizer.providers.local_provider import LocalFaceRecognitionProvider

        return LocalFaceRecognitionProvider({})

    @pytest.fixture
    def mock_image_file(self, tmp_path):
        """Create a temporary test image file."""
        img = Image.new("RGB", (100, 100), color="red")
        img_path = tmp_path / "test_face.jpg"
        img.save(img_path)
        return str(img_path)

    def test_load_reference_photos_success(self, provider, mock_image_file):
        """Test successful loading of reference photos."""
        mock_encoding = np.random.rand(128)
        mock_location = (10, 100, 100, 10)  # top, right, bottom, left

        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.load_image_file.return_value = np.zeros((100, 100, 3))
            mock_fr.face_locations.return_value = [mock_location]
            mock_fr.face_encodings.return_value = [mock_encoding]

            count = provider.load_reference_photos([mock_image_file])

            assert count == 1
            assert len(provider.reference_encodings) == 1
            assert provider.reference_encodings[0].source == mock_image_file
            assert provider.reference_encodings[0].bounding_box == mock_location
            np.testing.assert_array_equal(provider.reference_encodings[0].encoding, mock_encoding)

    def test_load_reference_photos_file_not_found(self, provider):
        """Test handling of non-existent reference photo."""
        with patch("scripts.face_recognizer.providers.local_provider.face_recognition"):
            # This should not raise an exception, just log warning and skip
            with pytest.raises(Exception) as exc_info:
                provider.load_reference_photos(["/nonexistent/path/photo.jpg"])

            assert "No reference faces could be loaded" in str(exc_info.value)

    def test_load_reference_photos_no_faces_found(self, provider, mock_image_file):
        """Test handling when no faces are found in reference photo."""
        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.load_image_file.return_value = np.zeros((100, 100, 3))
            mock_fr.face_locations.return_value = []  # No faces found

            with pytest.raises(Exception) as exc_info:
                provider.load_reference_photos([mock_image_file])

            assert "No reference faces could be loaded" in str(exc_info.value)

    def test_load_reference_photos_multiple_faces_warning(self, provider, mock_image_file):
        """Test warning when multiple faces found in reference photo."""
        mock_encoding = np.random.rand(128)
        mock_locations = [
            (10, 100, 100, 10),
            (10, 200, 100, 110),
        ]  # Two faces

        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.load_image_file.return_value = np.zeros((100, 100, 3))
            mock_fr.face_locations.return_value = mock_locations
            mock_fr.face_encodings.return_value = [mock_encoding, mock_encoding]

            count = provider.load_reference_photos([mock_image_file])

            # Should still succeed but use only the first face
            assert count == 1
            assert len(provider.reference_encodings) == 1

    def test_load_reference_photos_exception_handling(self, provider, mock_image_file):
        """Test handling of exceptions during photo processing."""
        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.load_image_file.side_effect = Exception("Image load error")

            with pytest.raises(Exception) as exc_info:
                provider.load_reference_photos([mock_image_file])

            assert "No reference faces could be loaded" in str(exc_info.value)

    def test_load_reference_photos_multiple_photos(self, provider, tmp_path):
        """Test loading multiple reference photos."""
        # Create two test images
        img1_path = tmp_path / "face1.jpg"
        img2_path = tmp_path / "face2.jpg"
        Image.new("RGB", (100, 100), color="red").save(img1_path)
        Image.new("RGB", (100, 100), color="blue").save(img2_path)

        mock_encoding1 = np.random.rand(128)
        mock_encoding2 = np.random.rand(128)

        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.load_image_file.return_value = np.zeros((100, 100, 3))
            mock_fr.face_locations.return_value = [(10, 100, 100, 10)]
            mock_fr.face_encodings.side_effect = [[mock_encoding1], [mock_encoding2]]

            count = provider.load_reference_photos([str(img1_path), str(img2_path)])

            assert count == 2
            assert len(provider.reference_encodings) == 2

    def test_load_reference_photos_empty_encodings(self, provider, mock_image_file):
        """Test handling when face_encodings returns empty list."""
        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.load_image_file.return_value = np.zeros((100, 100, 3))
            mock_fr.face_locations.return_value = [(10, 100, 100, 10)]
            mock_fr.face_encodings.return_value = []  # Empty encodings

            with pytest.raises(Exception) as exc_info:
                provider.load_reference_photos([mock_image_file])

            assert "No reference faces could be loaded" in str(exc_info.value)

    def test_load_reference_photos_clears_previous_encodings(self, provider, mock_image_file):
        """Test that loading new photos clears previous encodings."""
        mock_encoding = np.random.rand(128)

        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.load_image_file.return_value = np.zeros((100, 100, 3))
            mock_fr.face_locations.return_value = [(10, 100, 100, 10)]
            mock_fr.face_encodings.return_value = [mock_encoding]

            # Load photos twice
            provider.load_reference_photos([mock_image_file])
            provider.load_reference_photos([mock_image_file])

            # Should only have one encoding from the second call
            assert len(provider.reference_encodings) == 1


class TestDetectFaces:
    """Test detect_faces method."""

    @pytest.fixture
    def provider(self):
        """Create a LocalFaceRecognitionProvider instance."""
        from scripts.face_recognizer.providers.local_provider import LocalFaceRecognitionProvider

        return LocalFaceRecognitionProvider({})

    @pytest.fixture
    def test_image_bytes(self):
        """Create test image bytes."""
        img = Image.new("RGB", (100, 100), color="red")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        return buffer.getvalue()

    def test_detect_faces_success(self, provider, test_image_bytes):
        """Test successful face detection."""
        mock_encoding = np.random.rand(128)
        mock_location = (10, 100, 100, 10)

        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.face_locations.return_value = [mock_location]
            mock_fr.face_encodings.return_value = [mock_encoding]

            faces = provider.detect_faces(test_image_bytes, source="test.jpg")

            assert len(faces) == 1
            assert faces[0].source == "test.jpg"
            assert faces[0].bounding_box == mock_location
            np.testing.assert_array_equal(faces[0].encoding, mock_encoding)

    def test_detect_faces_no_faces_found(self, provider, test_image_bytes):
        """Test when no faces are detected."""
        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.face_locations.return_value = []

            faces = provider.detect_faces(test_image_bytes, source="test.jpg")

            assert faces == []

    def test_detect_faces_multiple_faces(self, provider, test_image_bytes):
        """Test detecting multiple faces."""
        mock_encodings = [np.random.rand(128), np.random.rand(128)]
        mock_locations = [(10, 100, 100, 10), (10, 200, 100, 110)]

        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.face_locations.return_value = mock_locations
            mock_fr.face_encodings.return_value = mock_encodings

            faces = provider.detect_faces(test_image_bytes, source="test.jpg")

            assert len(faces) == 2
            for i, face in enumerate(faces):
                assert face.bounding_box == mock_locations[i]

    def test_detect_faces_converts_rgba_to_rgb(self, provider):
        """Test that RGBA images are converted to RGB."""
        img = Image.new("RGBA", (100, 100), color=(255, 0, 0, 255))
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        rgba_bytes = buffer.getvalue()

        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.face_locations.return_value = []

            provider.detect_faces(rgba_bytes, source="test.png")

            # face_locations should be called with an RGB array
            mock_fr.face_locations.assert_called_once()
            call_args = mock_fr.face_locations.call_args[0][0]
            assert len(call_args.shape) == 3
            assert call_args.shape[2] == 3  # RGB has 3 channels

    def test_detect_faces_converts_grayscale_to_rgb(self, provider):
        """Test that grayscale images are converted to RGB."""
        img = Image.new("L", (100, 100), color=128)
        buffer = io.BytesIO()
        img.save(buffer, format="PNG")
        gray_bytes = buffer.getvalue()

        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.face_locations.return_value = []

            provider.detect_faces(gray_bytes, source="test.png")

            # face_locations should be called with an RGB array
            mock_fr.face_locations.assert_called_once()
            call_args = mock_fr.face_locations.call_args[0][0]
            assert len(call_args.shape) == 3
            assert call_args.shape[2] == 3  # RGB has 3 channels

    def test_detect_faces_exception_handling(self, provider):
        """Test handling of exceptions during detection."""
        with patch("scripts.face_recognizer.providers.local_provider.Image") as mock_image:
            mock_image.open.side_effect = Exception("Invalid image data")

            faces = provider.detect_faces(b"invalid_data", source="test.jpg")

            assert faces == []

    def test_detect_faces_default_source(self, provider, test_image_bytes):
        """Test detect_faces with default source parameter."""
        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.face_locations.return_value = [(10, 100, 100, 10)]
            mock_fr.face_encodings.return_value = [np.random.rand(128)]

            faces = provider.detect_faces(test_image_bytes)

            assert len(faces) == 1
            assert faces[0].source == "unknown"

    def test_detect_faces_uses_configured_model(self, test_image_bytes):
        """Test that detect_faces uses the configured model."""
        from scripts.face_recognizer.providers.local_provider import LocalFaceRecognitionProvider

        provider = LocalFaceRecognitionProvider({"model": "cnn"})

        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.face_locations.return_value = []

            provider.detect_faces(test_image_bytes)

            mock_fr.face_locations.assert_called_once()
            assert mock_fr.face_locations.call_args[1]["model"] == "cnn"

    def test_detect_faces_uses_configured_jitters_and_encoding_model(self, test_image_bytes):
        """Test that detect_faces uses configured num_jitters and encoding_model."""
        from scripts.face_recognizer.providers.local_provider import LocalFaceRecognitionProvider

        provider = LocalFaceRecognitionProvider({"num_jitters": 3, "encoding_model": "large"})

        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.face_locations.return_value = [(10, 100, 100, 10)]
            mock_fr.face_encodings.return_value = [np.random.rand(128)]

            provider.detect_faces(test_image_bytes)

            mock_fr.face_encodings.assert_called_once()
            call_kwargs = mock_fr.face_encodings.call_args[1]
            assert call_kwargs["num_jitters"] == 3
            assert call_kwargs["model"] == "large"


class TestCompareFaces:
    """Test compare_faces method."""

    @pytest.fixture
    def provider_with_references(self):
        """Create a provider with loaded reference encodings."""
        from scripts.face_recognizer.base_provider import FaceEncoding
        from scripts.face_recognizer.providers.local_provider import LocalFaceRecognitionProvider

        provider = LocalFaceRecognitionProvider({"tolerance": 0.6})
        provider.reference_encodings = [
            FaceEncoding(
                encoding=np.array([0.1] * 128),
                source="ref1.jpg",
                bounding_box=(10, 100, 100, 10),
            ),
            FaceEncoding(
                encoding=np.array([0.2] * 128),
                source="ref2.jpg",
                bounding_box=(10, 100, 100, 10),
            ),
        ]
        return provider

    @pytest.fixture
    def test_face_encoding(self):
        """Create a test face encoding."""
        from scripts.face_recognizer.base_provider import FaceEncoding

        return FaceEncoding(
            encoding=np.array([0.1] * 128),  # Identical to ref1
            source="test.jpg",
            bounding_box=(10, 100, 100, 10),
        )

    def test_compare_faces_exact_match(self, provider_with_references, test_face_encoding):
        """Test comparing a face that matches exactly."""
        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.face_distance.return_value = np.array([0.0, 0.5])  # Exact match with ref1

            result = provider_with_references.compare_faces(test_face_encoding)

            # noqa: E712 - Use == instead of 'is' because numpy returns np.True_/np.False_
            assert result.is_match == True  # noqa: E712
            assert result.confidence == 1.0
            assert result.distance == 0.0
            assert result.matched_encoding is not None
            assert result.matched_encoding.source == "ref1.jpg"

    def test_compare_faces_close_match(self, provider_with_references, test_face_encoding):
        """Test comparing a face that is a close match."""
        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.face_distance.return_value = np.array([0.4, 0.8])  # Within tolerance

            result = provider_with_references.compare_faces(test_face_encoding)

            # noqa: E712 - Use == instead of 'is' because numpy returns np.True_/np.False_
            assert result.is_match == True  # noqa: E712
            assert result.confidence == 0.6  # 1.0 - 0.4
            assert result.distance == 0.4

    def test_compare_faces_no_match(self, provider_with_references, test_face_encoding):
        """Test comparing a face that doesn't match."""
        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.face_distance.return_value = np.array([0.8, 0.9])  # Outside tolerance

            result = provider_with_references.compare_faces(test_face_encoding)

            # noqa: E712 - Use == instead of 'is' because numpy returns np.True_/np.False_
            assert result.is_match == False  # noqa: E712
            assert abs(result.confidence - 0.2) < 0.0001  # 1.0 - 0.8
            assert result.distance == 0.8
            assert result.matched_encoding is None

    def test_compare_faces_no_reference_encodings(self, test_face_encoding):
        """Test comparing when no reference encodings are loaded."""
        from scripts.face_recognizer.providers.local_provider import LocalFaceRecognitionProvider

        provider = LocalFaceRecognitionProvider({})
        # Don't load any reference encodings

        result = provider.compare_faces(test_face_encoding)

        assert result.is_match is False
        assert result.confidence == 0.0
        assert result.distance == 1.0

    def test_compare_faces_custom_tolerance(self, provider_with_references, test_face_encoding):
        """Test comparing with custom tolerance parameter."""
        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.face_distance.return_value = np.array([0.5, 0.8])

            # With default tolerance 0.6, this should match
            result_default = provider_with_references.compare_faces(test_face_encoding)
            # noqa: E712 - Use == instead of 'is' because numpy returns np.True_/np.False_
            assert result_default.is_match == True  # noqa: E712

            # With stricter tolerance 0.3, this should not match
            result_strict = provider_with_references.compare_faces(test_face_encoding, tolerance=0.3)
            # noqa: E712 - Use == instead of 'is' because numpy returns np.True_/np.False_
            assert result_strict.is_match == False  # noqa: E712

    def test_compare_faces_uses_default_tolerance(self, test_face_encoding):
        """Test that default_tolerance is used when tolerance is None."""
        from scripts.face_recognizer.base_provider import FaceEncoding
        from scripts.face_recognizer.providers.local_provider import LocalFaceRecognitionProvider

        provider = LocalFaceRecognitionProvider({"tolerance": 0.8})
        provider.reference_encodings = [
            FaceEncoding(
                encoding=np.array([0.1] * 128),
                source="ref.jpg",
                bounding_box=(10, 100, 100, 10),
            )
        ]

        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.face_distance.return_value = np.array([0.7])

            # With default tolerance 0.8, distance 0.7 should match
            result = provider.compare_faces(test_face_encoding)
            # noqa: E712 - Use == instead of 'is' because numpy returns np.True_/np.False_
            assert result.is_match == True  # noqa: E712

    def test_compare_faces_confidence_capped_at_zero(self, provider_with_references, test_face_encoding):
        """Test that confidence is capped at 0.0 for very distant faces."""
        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            mock_fr.face_distance.return_value = np.array([1.5, 2.0])  # Very distant

            result = provider_with_references.compare_faces(test_face_encoding)

            assert result.confidence == 0.0  # max(0.0, 1.0 - 1.5)
            # noqa: E712 - Use == instead of 'is' because numpy returns np.True_/np.False_
            assert result.is_match == False  # noqa: E712

    def test_compare_faces_selects_best_match(self, provider_with_references, test_face_encoding):
        """Test that the best (lowest distance) match is selected."""
        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            # ref2 is closer than ref1
            mock_fr.face_distance.return_value = np.array([0.5, 0.3])

            result = provider_with_references.compare_faces(test_face_encoding)

            # noqa: E712 - Use == instead of 'is' because numpy returns np.True_/np.False_
            assert result.is_match == True  # noqa: E712
            assert result.distance == 0.3
            assert result.matched_encoding.source == "ref2.jpg"


class TestLocalProviderIntegration:
    """Integration tests for LocalFaceRecognitionProvider."""

    def test_full_workflow_mock(self, tmp_path):
        """Test the full workflow with mocked face_recognition."""
        from scripts.face_recognizer.providers.local_provider import LocalFaceRecognitionProvider

        # Create test images
        ref_path = tmp_path / "reference.jpg"
        Image.new("RGB", (100, 100), color="red").save(ref_path)

        test_img = Image.new("RGB", (100, 100), color="blue")
        buffer = io.BytesIO()
        test_img.save(buffer, format="JPEG")
        test_bytes = buffer.getvalue()

        provider = LocalFaceRecognitionProvider({"tolerance": 0.6})

        with patch("scripts.face_recognizer.providers.local_provider.face_recognition") as mock_fr:
            ref_encoding = np.random.rand(128)
            test_encoding = ref_encoding + np.random.rand(128) * 0.1  # Similar

            # Setup mocks for load_reference_photos
            mock_fr.load_image_file.return_value = np.zeros((100, 100, 3))
            mock_fr.face_locations.return_value = [(10, 100, 100, 10)]
            mock_fr.face_encodings.return_value = [ref_encoding]

            # Load reference
            count = provider.load_reference_photos([str(ref_path)])
            assert count == 1

            # Setup mocks for detect_faces
            mock_fr.face_encodings.return_value = [test_encoding]
            mock_fr.face_distance.return_value = np.array([0.3])  # Similar

            # Detect faces
            faces = provider.detect_faces(test_bytes, source="test.jpg")
            assert len(faces) == 1

            # Compare
            result = provider.compare_faces(faces[0])
            # noqa: E712 - Use == instead of 'is' because numpy returns np.True_/np.False_
            assert result.is_match == True  # noqa: E712


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
