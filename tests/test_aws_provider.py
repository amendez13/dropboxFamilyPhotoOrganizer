"""Unit tests for aws_provider.py face recognition module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

# Add scripts directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


@pytest.fixture(autouse=True)
def mock_aws_available():
    """
    Mock AWS_AVAILABLE to True and patch boto3 modules for all tests.
    This allows tests to run in CI environments where boto3 is not installed.

    We inject the mock classes directly into the module before tests run.
    Each test gets fresh mock instances to ensure test isolation.
    """
    import scripts.face_recognizer.providers.aws_provider as aws_module

    # Store originals (if they exist)
    original_available = getattr(aws_module, "AWS_AVAILABLE", False)
    original_boto3 = getattr(aws_module, "boto3", None)
    original_client_error = getattr(aws_module, "ClientError", None)

    # Create fresh mocks for each test
    mock_boto3 = MagicMock()
    mock_client_error = type("ClientError", (Exception,), {})

    # Inject mocks
    aws_module.AWS_AVAILABLE = True
    aws_module.boto3 = mock_boto3
    aws_module.ClientError = mock_client_error

    yield {
        "boto3": mock_boto3,
        "ClientError": mock_client_error,
    }

    # Restore originals
    aws_module.AWS_AVAILABLE = original_available
    if original_boto3 is not None:
        aws_module.boto3 = original_boto3
    if original_client_error is not None:
        aws_module.ClientError = original_client_error


class TestAWSProviderImport:
    """Test import behavior when AWS SDK is not available."""

    def test_import_error_when_boto3_not_available(self):
        """Test that ImportError is raised when boto3 is not installed."""
        with patch(
            "scripts.face_recognizer.providers.aws_provider.AWS_AVAILABLE",
            False,
        ):
            from scripts.face_recognizer.providers import aws_provider

            config = {
                "aws_region": "us-east-1",
            }

            with pytest.raises(ImportError) as exc_info:
                aws_provider.AWSFaceRecognitionProvider(config)

            assert "boto3" in str(exc_info.value)


class TestAWSFaceRecognitionProviderInit:
    """Test AWSFaceRecognitionProvider initialization."""

    def test_init_with_minimal_config(self, mock_aws_available):
        """Test initialization with minimal configuration (using AWS CLI defaults)."""
        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        config = {}
        provider = AWSFaceRecognitionProvider(config)

        assert provider.similarity_threshold == 80.0
        assert provider.reference_images == []
        assert provider.reference_encodings == []

    def test_init_with_aws_credentials_in_config(self, mock_aws_available):
        """Test initialization with AWS credentials in config."""
        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        config = {
            "aws_access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "aws_secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "aws_region": "us-west-2",
        }
        AWSFaceRecognitionProvider(config)

        # Verify boto3.client was called with credentials
        mock_aws_available["boto3"].client.assert_called_once()
        call_kwargs = mock_aws_available["boto3"].client.call_args[1]
        assert call_kwargs["aws_access_key_id"] == "AKIAIOSFODNN7EXAMPLE"
        assert call_kwargs["aws_secret_access_key"] == "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"
        assert call_kwargs["region_name"] == "us-west-2"

    def test_init_uses_aws_cli_credentials_by_default(self, mock_aws_available):
        """Test that provider uses AWS CLI credentials when not in config."""
        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        config = {}
        AWSFaceRecognitionProvider(config)

        # Verify boto3.client was called without explicit credentials
        mock_aws_available["boto3"].client.assert_called_once()
        call_kwargs = mock_aws_available["boto3"].client.call_args[1]
        assert "aws_access_key_id" not in call_kwargs
        assert "aws_secret_access_key" not in call_kwargs

    def test_init_custom_region(self, mock_aws_available):
        """Test initialization with custom region."""
        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        config = {
            "aws_region": "eu-west-1",
        }
        AWSFaceRecognitionProvider(config)

        call_kwargs = mock_aws_available["boto3"].client.call_args[1]
        assert call_kwargs["region_name"] == "eu-west-1"

    def test_init_stores_default_similarity_threshold(self, mock_aws_available):
        """Test that default similarity threshold is 80.0."""
        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        config = {}
        provider = AWSFaceRecognitionProvider(config)

        assert provider.similarity_threshold == 80.0

    def test_init_custom_similarity_threshold(self, mock_aws_available):
        """Test initialization with custom similarity threshold."""
        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        config = {
            "similarity_threshold": 90.0,
        }
        provider = AWSFaceRecognitionProvider(config)

        assert provider.similarity_threshold == 90.0

    def test_init_stores_config(self, mock_aws_available):
        """Test that config is stored in parent class."""
        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        config = {
            "aws_region": "us-east-1",
            "custom_key": "value",
        }
        provider = AWSFaceRecognitionProvider(config)

        assert provider.config == config

    def test_init_client_creation_error(self, mock_aws_available):
        """Test that client creation error is raised."""
        mock_aws_available["boto3"].client.side_effect = Exception("Connection failed")

        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        config = {}

        with pytest.raises(Exception) as exc_info:
            AWSFaceRecognitionProvider(config)

        assert "Failed to initialize AWS Rekognition client" in str(exc_info.value)


class TestGetProviderName:
    """Test get_provider_name method."""

    def test_get_provider_name_returns_aws(self, mock_aws_available):
        """Test that get_provider_name returns 'aws'."""
        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        config = {}
        provider = AWSFaceRecognitionProvider(config)

        assert provider.get_provider_name() == "aws"


class TestValidateConfiguration:
    """Test validate_configuration method."""

    def test_validate_configuration_success(self, mock_aws_available):
        """Test validation passes when API call returns expected error."""
        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        config = {}
        provider = AWSFaceRecognitionProvider(config)

        # Mock API call that returns InvalidImageFormatException (expected with empty bytes)
        error_response = {"Error": {"Code": "InvalidImageFormatException"}}
        mock_error = mock_aws_available["ClientError"](error_response, "DetectFaces")
        mock_error.response = error_response
        provider.client.detect_faces.side_effect = mock_error

        is_valid, error = provider.validate_configuration()

        assert is_valid is True
        assert error is None

    def test_validate_configuration_boto3_unavailable(self, mock_aws_available):
        """Test validation fails when boto3 is not available."""
        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        config = {}
        provider = AWSFaceRecognitionProvider(config)

        # Override AWS_AVAILABLE after provider creation
        with patch(
            "scripts.face_recognizer.providers.aws_provider.AWS_AVAILABLE",
            False,
        ):
            is_valid, error = provider.validate_configuration()

            assert is_valid is False
            assert "not installed" in error

    def test_validate_configuration_invalid_credentials(self, mock_aws_available):
        """Test validation fails with invalid credentials."""
        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        config = {}
        provider = AWSFaceRecognitionProvider(config)

        # Mock API call that returns authentication error
        error_response = {"Error": {"Code": "UnrecognizedClientException"}}
        mock_error = mock_aws_available["ClientError"](error_response, "DetectFaces")
        mock_error.response = error_response
        provider.client.detect_faces.side_effect = mock_error

        is_valid, error = provider.validate_configuration()

        assert is_valid is False
        assert "authentication failed" in error.lower()

    def test_validate_configuration_generic_error(self, mock_aws_available):
        """Test validation fails with generic error."""
        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        config = {}
        provider = AWSFaceRecognitionProvider(config)

        # Mock generic error
        provider.client.detect_faces.side_effect = Exception("Network error")

        is_valid, error = provider.validate_configuration()

        assert is_valid is False
        assert "configuration error" in error.lower()


class TestLoadReferencePhotos:
    """Test load_reference_photos method."""

    @pytest.fixture
    def provider(self, mock_aws_available):
        """Create an AWSFaceRecognitionProvider instance."""
        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        config = {}
        return AWSFaceRecognitionProvider(config)

    @pytest.fixture
    def mock_image_file(self, tmp_path):
        """Create a temporary test image file."""
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        img_path = tmp_path / "test_face.jpg"
        img.save(img_path)
        return str(img_path)

    def test_load_reference_photos_success(self, provider, mock_image_file):
        """Test successful loading of reference photos."""
        # Mock successful face detection
        provider.client.detect_faces.return_value = {"FaceDetails": [{"Confidence": 99.5}]}

        count = provider.load_reference_photos([mock_image_file])

        assert count == 1
        assert len(provider.reference_images) == 1
        assert len(provider.reference_encodings) == 1
        assert provider.reference_encodings[0].source == mock_image_file

    def test_load_reference_photos_file_not_found(self, provider):
        """Test handling of non-existent reference photo."""
        with pytest.raises(Exception) as exc_info:
            provider.load_reference_photos(["/nonexistent/path/photo.jpg"])

        assert "No reference photos could be loaded" in str(exc_info.value)

    def test_load_reference_photos_no_faces_detected(self, provider, mock_image_file):
        """Test handling when no faces are detected in reference photo."""
        # Mock no faces detected
        provider.client.detect_faces.return_value = {"FaceDetails": []}

        with pytest.raises(Exception) as exc_info:
            provider.load_reference_photos([mock_image_file])

        assert "No reference photos could be loaded" in str(exc_info.value)

    def test_load_reference_photos_api_error(self, provider, mock_image_file, mock_aws_available):
        """Test handling of API errors during reference photo loading."""
        # Mock API error
        error_response = {"Error": {"Code": "InternalServerError"}}
        mock_error = mock_aws_available["ClientError"](error_response, "DetectFaces")
        mock_error.response = error_response
        provider.client.detect_faces.side_effect = mock_error

        with pytest.raises(Exception) as exc_info:
            provider.load_reference_photos([mock_image_file])

        assert "No reference photos could be loaded" in str(exc_info.value)

    def test_load_reference_photos_multiple_photos(self, provider, tmp_path):
        """Test loading multiple reference photos."""
        from PIL import Image

        # Create multiple test images
        img_paths = []
        for i in range(3):
            img = Image.new("RGB", (100, 100), color="red")
            img_path = tmp_path / f"test_face_{i}.jpg"
            img.save(img_path)
            img_paths.append(str(img_path))

        # Mock successful face detection
        provider.client.detect_faces.return_value = {"FaceDetails": [{"Confidence": 99.5}]}

        count = provider.load_reference_photos(img_paths)

        assert count == 3
        assert len(provider.reference_images) == 3
        assert len(provider.reference_encodings) == 3

    def test_load_reference_photos_clears_previous(self, provider, mock_image_file):
        """Test that loading reference photos clears previous references."""
        # Mock successful face detection
        provider.client.detect_faces.return_value = {"FaceDetails": [{"Confidence": 99.5}]}

        # Load first time
        provider.load_reference_photos([mock_image_file])
        assert len(provider.reference_images) == 1

        # Load second time - should clear previous
        provider.load_reference_photos([mock_image_file])
        assert len(provider.reference_images) == 1  # Still just 1, not 2

    def test_load_reference_photos_partial_success(self, provider, tmp_path):
        """Test loading when some photos succeed and some fail."""
        from PIL import Image

        # Create valid image
        img = Image.new("RGB", (100, 100), color="red")
        valid_path = tmp_path / "valid_face.jpg"
        img.save(valid_path)

        # Mock different results for different calls
        call_count = [0]

        def mock_detect_faces(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return {"FaceDetails": [{"Confidence": 99.5}]}
            else:
                return {"FaceDetails": []}  # No faces

        provider.client.detect_faces.side_effect = mock_detect_faces

        count = provider.load_reference_photos([str(valid_path), str(valid_path)])

        assert count == 1  # Only first one should succeed


class TestDetectFaces:
    """Test detect_faces method."""

    @pytest.fixture
    def provider(self, mock_aws_available):
        """Create an AWSFaceRecognitionProvider instance."""
        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        config = {}
        return AWSFaceRecognitionProvider(config)

    @pytest.fixture
    def test_image_bytes(self):
        """Create test image bytes."""
        import io

        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        return buffer.getvalue()

    def test_detect_faces_success(self, provider, test_image_bytes):
        """Test successful face detection."""
        provider.client.detect_faces.return_value = {
            "FaceDetails": [{"Confidence": 99.5, "BoundingBox": {"Left": 0.1, "Top": 0.2, "Width": 0.3, "Height": 0.4}}]
        }

        faces = provider.detect_faces(test_image_bytes, source="test.jpg")

        assert len(faces) == 1
        assert faces[0].source == "test.jpg"
        assert faces[0].confidence == pytest.approx(0.995)  # 99.5/100

    def test_detect_faces_no_faces_found(self, provider, test_image_bytes):
        """Test when no faces are detected."""
        provider.client.detect_faces.return_value = {"FaceDetails": []}

        faces = provider.detect_faces(test_image_bytes, source="test.jpg")

        assert faces == []

    def test_detect_faces_multiple_faces(self, provider, test_image_bytes):
        """Test detecting multiple faces."""
        provider.client.detect_faces.return_value = {
            "FaceDetails": [
                {"Confidence": 99.5},
                {"Confidence": 95.0},
            ]
        }

        faces = provider.detect_faces(test_image_bytes, source="test.jpg")

        assert len(faces) == 2
        assert faces[0].confidence == pytest.approx(0.995)
        assert faces[1].confidence == pytest.approx(0.95)

    def test_detect_faces_api_error(self, provider, test_image_bytes, mock_aws_available):
        """Test handling of API errors during detection."""
        error_response = {"Error": {"Code": "InternalServerError"}}
        mock_error = mock_aws_available["ClientError"](error_response, "DetectFaces")
        mock_error.response = error_response
        provider.client.detect_faces.side_effect = mock_error

        faces = provider.detect_faces(test_image_bytes, source="test.jpg")

        assert faces == []

    def test_detect_faces_confidence_normalization(self, provider, test_image_bytes):
        """Test that confidence is normalized from 0-100 to 0-1."""
        provider.client.detect_faces.return_value = {"FaceDetails": [{"Confidence": 75.0}]}

        faces = provider.detect_faces(test_image_bytes, source="test.jpg")

        assert len(faces) == 1
        assert faces[0].confidence == pytest.approx(0.75)

    def test_detect_faces_default_source(self, provider, test_image_bytes):
        """Test detect_faces with default source parameter."""
        provider.client.detect_faces.return_value = {"FaceDetails": [{"Confidence": 99.5}]}

        faces = provider.detect_faces(test_image_bytes)

        assert len(faces) == 1
        assert faces[0].source == "unknown"

    def test_detect_faces_generic_error(self, provider, test_image_bytes):
        """Test handling of generic errors during detection."""
        provider.client.detect_faces.side_effect = Exception("Network timeout")

        faces = provider.detect_faces(test_image_bytes, source="test.jpg")

        assert faces == []


class TestCompareFaces:
    """Test compare_faces method."""

    @pytest.fixture
    def provider(self, mock_aws_available):
        """Create an AWSFaceRecognitionProvider instance."""
        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        config = {}
        return AWSFaceRecognitionProvider(config)

    @pytest.fixture
    def test_face_encoding(self):
        """Create a test face encoding."""
        from scripts.face_recognizer.base_provider import FaceEncoding

        return FaceEncoding(
            encoding=np.array([]),  # Empty for AWS
            source="test.jpg",
        )

    def test_compare_faces_returns_no_match(self, provider, test_face_encoding):
        """Test that compare_faces returns no match (documented limitation)."""
        result = provider.compare_faces(test_face_encoding)

        assert result.is_match is False
        assert result.confidence == 0.0
        assert result.distance == 1.0


class TestFindMatchesInImage:
    """Test find_matches_in_image method."""

    @pytest.fixture
    def provider(self, mock_aws_available):
        """Create an AWSFaceRecognitionProvider instance with reference images."""
        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        config = {
            "similarity_threshold": 80.0,
        }
        provider = AWSFaceRecognitionProvider(config)
        # Add a mock reference image
        provider.reference_images = [b"fake_reference_image_bytes"]
        return provider

    @pytest.fixture
    def test_image_bytes(self):
        """Create test image bytes."""
        import io

        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")
        return buffer.getvalue()

    def test_find_matches_success(self, provider, test_image_bytes):
        """Test successful face matching."""
        provider.client.compare_faces.return_value = {
            "FaceMatches": [{"Similarity": 95.0, "Face": {"Confidence": 99.0}}],
            "UnmatchedFaces": [],
        }

        matches, total_faces = provider.find_matches_in_image(test_image_bytes, source="test.jpg")

        assert len(matches) == 1
        assert matches[0].is_match is True
        assert matches[0].confidence == pytest.approx(0.95)
        assert matches[0].distance == pytest.approx(0.05)

    def test_find_matches_no_match(self, provider, test_image_bytes):
        """Test when no faces match."""
        provider.client.compare_faces.return_value = {
            "FaceMatches": [],
            "UnmatchedFaces": [{"Confidence": 99.0}],
        }

        matches, total_faces = provider.find_matches_in_image(test_image_bytes, source="test.jpg")

        assert len(matches) == 0
        assert total_faces == 1

    def test_find_matches_multiple_references(self, provider, test_image_bytes):
        """Test matching against multiple reference images."""
        # Add more reference images
        provider.reference_images = [b"ref1", b"ref2", b"ref3"]

        # Each reference returns a match
        provider.client.compare_faces.return_value = {
            "FaceMatches": [{"Similarity": 90.0, "Face": {"Confidence": 99.0}}],
            "UnmatchedFaces": [],
        }

        matches, total_faces = provider.find_matches_in_image(test_image_bytes, source="test.jpg")

        # Should only return unique best match
        assert len(matches) <= 1
        # Should have called compare_faces for each reference
        assert provider.client.compare_faces.call_count == 3

    def test_find_matches_api_error(self, provider, test_image_bytes, mock_aws_available):
        """Test handling of API errors during matching."""
        error_response = {"Error": {"Code": "InternalServerError"}}
        mock_error = mock_aws_available["ClientError"](error_response, "CompareFaces")
        mock_error.response = error_response
        provider.client.compare_faces.side_effect = mock_error

        matches, total_faces = provider.find_matches_in_image(test_image_bytes, source="test.jpg")

        assert len(matches) == 0
        assert total_faces == 0

    def test_find_matches_custom_tolerance(self, provider, test_image_bytes):
        """Test matching with custom tolerance."""
        provider.client.compare_faces.return_value = {
            "FaceMatches": [{"Similarity": 90.0}],
            "UnmatchedFaces": [],
        }

        matches, _ = provider.find_matches_in_image(test_image_bytes, tolerance=90.0)

        # Verify custom tolerance was passed to API
        call_kwargs = provider.client.compare_faces.call_args[1]
        assert call_kwargs["SimilarityThreshold"] == 90.0

    def test_find_matches_uses_default_threshold(self, provider, test_image_bytes):
        """Test that default similarity threshold is used."""
        provider.client.compare_faces.return_value = {
            "FaceMatches": [],
            "UnmatchedFaces": [],
        }

        provider.find_matches_in_image(test_image_bytes)

        call_kwargs = provider.client.compare_faces.call_args[1]
        assert call_kwargs["SimilarityThreshold"] == 80.0

    def test_find_matches_total_faces_count(self, provider, test_image_bytes):
        """Test that total faces count includes matched and unmatched."""
        provider.client.compare_faces.return_value = {
            "FaceMatches": [{"Similarity": 95.0}],
            "UnmatchedFaces": [{"Confidence": 90.0}, {"Confidence": 85.0}],
        }

        matches, total_faces = provider.find_matches_in_image(test_image_bytes)

        assert total_faces == 3  # 1 matched + 2 unmatched

    def test_find_matches_generic_error(self, provider, test_image_bytes):
        """Test handling of generic errors during matching."""
        provider.client.compare_faces.side_effect = Exception("Network error")

        matches, total_faces = provider.find_matches_in_image(test_image_bytes)

        assert len(matches) == 0
        assert total_faces == 0

    def test_find_matches_no_reference_images(self, mock_aws_available, test_image_bytes):
        """Test matching when no reference images are loaded."""
        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        config = {}
        provider = AWSFaceRecognitionProvider(config)
        # Don't add any reference images

        matches, total_faces = provider.find_matches_in_image(test_image_bytes)

        assert len(matches) == 0
        assert total_faces == 0
        provider.client.compare_faces.assert_not_called()


class TestAWSProviderIntegration:
    """Integration tests for AWSFaceRecognitionProvider."""

    def test_full_workflow_mock(self, tmp_path, mock_aws_available):
        """Test the full workflow with mocked AWS SDK."""
        import io

        from PIL import Image

        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        # Create test reference image
        ref_path = tmp_path / "reference.jpg"
        Image.new("RGB", (100, 100), color="red").save(ref_path)

        # Create test candidate image
        test_img = Image.new("RGB", (100, 100), color="blue")
        buffer = io.BytesIO()
        test_img.save(buffer, format="JPEG")
        test_bytes = buffer.getvalue()

        config = {
            "similarity_threshold": 80.0,
        }
        provider = AWSFaceRecognitionProvider(config)

        # Setup mocks for load_reference_photos
        provider.client.detect_faces.return_value = {"FaceDetails": [{"Confidence": 99.5}]}

        # Load reference
        count = provider.load_reference_photos([str(ref_path)])
        assert count == 1
        assert len(provider.reference_images) == 1

        # Test detect_faces
        provider.client.detect_faces.return_value = {"FaceDetails": [{"Confidence": 95.0}]}
        faces = provider.detect_faces(test_bytes, source="test.jpg")
        assert len(faces) == 1

        # Setup mocks for find_matches_in_image
        provider.client.compare_faces.return_value = {
            "FaceMatches": [{"Similarity": 92.5}],
            "UnmatchedFaces": [],
        }

        # Find matches
        matches, total_faces = provider.find_matches_in_image(test_bytes, source="test.jpg")
        assert len(matches) == 1
        assert matches[0].is_match is True
        assert matches[0].confidence == pytest.approx(0.925)

    def test_provider_name_constant(self, mock_aws_available):
        """Test that provider name is always 'aws'."""
        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        provider = AWSFaceRecognitionProvider({})
        assert provider.get_provider_name() == "aws"

    def test_empty_encoding_for_aws(self, mock_aws_available):
        """Test that AWS provider uses empty encodings (since it compares images directly)."""
        from scripts.face_recognizer.providers.aws_provider import AWSFaceRecognitionProvider

        config = {}
        provider = AWSFaceRecognitionProvider(config)

        # Mock successful detection
        provider.client.detect_faces.return_value = {"FaceDetails": [{"Confidence": 99.5}]}

        import io

        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG")

        faces = provider.detect_faces(buffer.getvalue())

        assert len(faces) == 1
        # Encoding should be empty array for AWS
        assert len(faces[0].encoding) == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
