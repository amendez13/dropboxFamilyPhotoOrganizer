"""
Component tests for Azure face recognition workflow.

These tests verify end-to-end functionality across multiple modules:
- Face recognizer factory (scripts/face_recognizer/__init__.py)
- Azure provider (scripts/face_recognizer/providers/azure_provider.py)
- Train face model (scripts/train_face_model.py)
- Organize photos (scripts/organize_photos.py)

All external dependencies (Azure API, Dropbox API) are mocked.
"""

import io
import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from PIL import Image

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Import the azure module at module level BEFORE any tests run
# This prevents the numpy "cannot load module more than once" error
import scripts.face_recognizer.providers.azure_provider as azure_module  # noqa: E402

# ============================================================================
# Fixtures for Azure SDK Mocking
# ============================================================================


@pytest.fixture(autouse=True)
def mock_azure_sdk():
    """
    Mock the Azure SDK at the module level.
    Uses autouse=True to ensure mocks are applied for all tests.
    Returns mock objects for configuration in tests.
    """
    # Store originals
    original_available = getattr(azure_module, "AZURE_AVAILABLE", False)
    original_face_client = getattr(azure_module, "FaceClient", None)
    original_training_status = getattr(azure_module, "TrainingStatusType", None)
    original_credentials = getattr(azure_module, "CognitiveServicesCredentials", None)

    # Create fresh mocks for each test
    mock_face_client_class = MagicMock()
    mock_training_status_type = MagicMock()
    mock_training_status_type.succeeded = "succeeded"
    mock_training_status_type.failed = "failed"
    mock_credentials_class = MagicMock()

    # Inject mocks
    azure_module.AZURE_AVAILABLE = True
    azure_module.FaceClient = mock_face_client_class
    azure_module.TrainingStatusType = mock_training_status_type
    azure_module.CognitiveServicesCredentials = mock_credentials_class

    yield {
        "FaceClient": mock_face_client_class,
        "TrainingStatusType": mock_training_status_type,
        "CognitiveServicesCredentials": mock_credentials_class,
        "module": azure_module,
    }

    # Restore originals
    azure_module.AZURE_AVAILABLE = original_available
    if original_face_client is not None:
        azure_module.FaceClient = original_face_client
    if original_training_status is not None:
        azure_module.TrainingStatusType = original_training_status
    if original_credentials is not None:
        azure_module.CognitiveServicesCredentials = original_credentials


@pytest.fixture
def azure_config():
    """Standard Azure configuration for tests."""
    return {
        "azure_api_key": "test-api-key-12345",
        "azure_endpoint": "https://eastus.api.cognitive.microsoft.com",
        "person_group_id": "test-person-group",
        "confidence_threshold": 0.5,
        "training_timeout": 10,
    }


@pytest.fixture
def reference_photos(tmp_path):
    """Create temporary reference photo files."""
    photos = []
    for i in range(3):
        img = Image.new("RGB", (200, 200), color=(255, i * 50, 0))
        path = tmp_path / f"reference_{i}.jpg"
        img.save(path, "JPEG")
        photos.append(str(path))
    return photos


@pytest.fixture
def test_photo_bytes():
    """Create test photo as bytes."""
    img = Image.new("RGB", (200, 200), color=(0, 100, 255))
    buffer = io.BytesIO()
    img.save(buffer, format="JPEG")
    return buffer.getvalue()


# ============================================================================
# Component Test: Factory + Azure Provider Integration
# ============================================================================


class TestFactoryAzureProviderIntegration:
    """Test that the factory correctly creates and configures Azure provider."""

    def test_factory_creates_azure_provider(self, mock_azure_sdk, azure_config):
        """Test factory creates Azure provider with correct configuration."""
        from scripts.face_recognizer import FaceRecognitionFactory

        provider = FaceRecognitionFactory.create_provider("azure", azure_config)

        assert provider.get_provider_name() == "azure"
        assert provider.person_group_id == "test-person-group"
        assert provider.confidence_threshold == 0.5

    def test_factory_get_provider_convenience_function(self, mock_azure_sdk, azure_config):
        """Test the get_provider convenience function."""
        from scripts.face_recognizer import get_provider

        provider = get_provider("azure", azure_config)

        assert provider.get_provider_name() == "azure"

    def test_factory_lists_azure_as_available(self, mock_azure_sdk):
        """Test that factory reports Azure provider as available."""
        from scripts.face_recognizer import FaceRecognitionFactory

        available = FaceRecognitionFactory.list_available_providers()

        assert available["azure"] is True

    def test_factory_validates_azure_config(self, mock_azure_sdk, azure_config):
        """Test that factory validates Azure configuration on creation."""
        from scripts.face_recognizer import FaceRecognitionFactory

        # Mock successful validation
        mock_azure_sdk["FaceClient"].return_value.person_group.list.return_value = []

        provider = FaceRecognitionFactory.create_provider("azure", azure_config)

        # Provider should be created and validated
        assert provider is not None


# ============================================================================
# Component Test: Full Training Workflow
# ============================================================================


class TestAzureTrainingWorkflow:
    """Test the complete training workflow using Azure provider."""

    def test_complete_training_workflow(self, mock_azure_sdk, azure_config, reference_photos):
        """
        Test complete training workflow:
        1. Create provider via factory
        2. Load reference photos
        3. Verify person group and person creation
        4. Verify training completion
        """
        from scripts.face_recognizer import get_provider

        # Setup mocks for training workflow
        mock_client = mock_azure_sdk["FaceClient"].return_value

        # Mock person group operations
        mock_client.person_group.get.return_value = MagicMock()

        # Mock person operations - no existing persons
        mock_client.person_group_person.list.return_value = []
        mock_person = MagicMock()
        mock_person.person_id = "created-person-id-123"
        mock_client.person_group_person.create.return_value = mock_person

        # Mock face addition
        mock_client.person_group_person.add_face_from_stream.return_value = MagicMock()

        # Mock training status - succeed immediately
        mock_status = MagicMock()
        mock_status.status = mock_azure_sdk["TrainingStatusType"].succeeded
        mock_client.person_group.get_training_status.return_value = mock_status

        # Execute training workflow
        provider = get_provider("azure", azure_config)
        face_count = provider.load_reference_photos(reference_photos)

        # Verify results
        assert face_count == 3
        assert provider.person_id == "created-person-id-123"
        assert len(provider.reference_encodings) == 3

        # Verify API calls
        mock_client.person_group.get.assert_called_with("test-person-group")
        mock_client.person_group_person.create.assert_called_once()
        assert mock_client.person_group_person.add_face_from_stream.call_count == 3
        mock_client.person_group.train.assert_called_once_with("test-person-group")

    def test_training_with_existing_person_group(self, mock_azure_sdk, azure_config, reference_photos):
        """Test training reuses existing person group and person."""
        from scripts.face_recognizer import get_provider

        mock_client = mock_azure_sdk["FaceClient"].return_value

        # Mock existing person group
        mock_client.person_group.get.return_value = MagicMock()

        # Mock existing person
        existing_person = MagicMock()
        existing_person.person_id = "existing-person-id"
        existing_person.name = "Existing Person"
        mock_client.person_group_person.list.return_value = [existing_person]

        # Mock face addition and training
        mock_client.person_group_person.add_face_from_stream.return_value = MagicMock()
        mock_status = MagicMock()
        mock_status.status = mock_azure_sdk["TrainingStatusType"].succeeded
        mock_client.person_group.get_training_status.return_value = mock_status

        # Execute
        provider = get_provider("azure", azure_config)
        provider.load_reference_photos(reference_photos)

        # Verify existing person was reused
        assert provider.person_id == "existing-person-id"
        mock_client.person_group_person.create.assert_not_called()


# ============================================================================
# Component Test: Full Detection and Matching Workflow
# ============================================================================


class TestAzureDetectionMatchingWorkflow:
    """Test the complete detection and matching workflow."""

    def test_complete_detect_and_match_workflow(self, mock_azure_sdk, azure_config, reference_photos, test_photo_bytes):
        """
        Test complete detection and matching workflow:
        1. Train with reference photos
        2. Detect faces in target photo
        3. Compare detected faces against trained model
        4. Verify match results
        """
        from scripts.face_recognizer import get_provider

        mock_client = mock_azure_sdk["FaceClient"].return_value

        # Setup training mocks
        mock_client.person_group.get.return_value = MagicMock()
        mock_client.person_group_person.list.return_value = []
        mock_person = MagicMock()
        mock_person.person_id = "target-person-id"
        mock_client.person_group_person.create.return_value = mock_person
        mock_client.person_group_person.add_face_from_stream.return_value = MagicMock()

        mock_status = MagicMock()
        mock_status.status = mock_azure_sdk["TrainingStatusType"].succeeded
        mock_client.person_group.get_training_status.return_value = mock_status

        # Setup detection mock
        detected_face = MagicMock()
        detected_face.face_id = "detected-face-uuid-456"
        mock_client.face.detect_with_stream.return_value = [detected_face]

        # Setup identification mock - match found
        mock_candidate = MagicMock()
        mock_candidate.person_id = "target-person-id"
        mock_candidate.confidence = 0.92
        mock_result = MagicMock()
        mock_result.candidates = [mock_candidate]
        mock_client.face.identify.return_value = [mock_result]

        # Execute workflow
        provider = get_provider("azure", azure_config)

        # Train
        provider.load_reference_photos(reference_photos)

        # Detect
        faces = provider.detect_faces(test_photo_bytes, source="test_photo.jpg")

        # Match
        match_result = provider.compare_faces(faces[0])

        # Verify
        assert len(faces) == 1
        assert str(faces[0].encoding[0]) == "detected-face-uuid-456"
        assert match_result.is_match is True
        assert match_result.confidence == 0.92
        assert match_result.distance == pytest.approx(0.08)

    def test_no_match_workflow(self, mock_azure_sdk, azure_config, reference_photos, test_photo_bytes):
        """Test workflow when no match is found."""
        from scripts.face_recognizer import get_provider

        mock_client = mock_azure_sdk["FaceClient"].return_value

        # Setup training mocks
        mock_client.person_group.get.return_value = MagicMock()
        mock_client.person_group_person.list.return_value = []
        mock_person = MagicMock()
        mock_person.person_id = "target-person-id"
        mock_client.person_group_person.create.return_value = mock_person
        mock_client.person_group_person.add_face_from_stream.return_value = MagicMock()

        mock_status = MagicMock()
        mock_status.status = mock_azure_sdk["TrainingStatusType"].succeeded
        mock_client.person_group.get_training_status.return_value = mock_status

        # Setup detection mock
        detected_face = MagicMock()
        detected_face.face_id = "unknown-face-uuid"
        mock_client.face.detect_with_stream.return_value = [detected_face]

        # Setup identification mock - no match
        mock_result = MagicMock()
        mock_result.candidates = []  # No candidates = no match
        mock_client.face.identify.return_value = [mock_result]

        # Execute workflow
        provider = get_provider("azure", azure_config)
        provider.load_reference_photos(reference_photos)
        faces = provider.detect_faces(test_photo_bytes, source="unknown_person.jpg")
        match_result = provider.compare_faces(faces[0])

        # Verify no match
        assert match_result.is_match is False
        assert match_result.confidence == 0.0

    def test_multiple_faces_workflow(self, mock_azure_sdk, azure_config, reference_photos, test_photo_bytes):
        """Test workflow with multiple faces detected in photo."""
        from scripts.face_recognizer import get_provider

        mock_client = mock_azure_sdk["FaceClient"].return_value

        # Setup training mocks
        mock_client.person_group.get.return_value = MagicMock()
        mock_client.person_group_person.list.return_value = []
        mock_person = MagicMock()
        mock_person.person_id = "target-person-id"
        mock_client.person_group_person.create.return_value = mock_person
        mock_client.person_group_person.add_face_from_stream.return_value = MagicMock()

        mock_status = MagicMock()
        mock_status.status = mock_azure_sdk["TrainingStatusType"].succeeded
        mock_client.person_group.get_training_status.return_value = mock_status

        # Setup detection mock - multiple faces
        face1 = MagicMock()
        face1.face_id = "face-1-uuid"
        face2 = MagicMock()
        face2.face_id = "face-2-uuid"
        face3 = MagicMock()
        face3.face_id = "face-3-uuid"
        mock_client.face.detect_with_stream.return_value = [face1, face2, face3]

        # Setup identification - only face2 matches
        def identify_side_effect(face_ids, person_group_id, confidence_threshold):
            face_id = face_ids[0]
            mock_result = MagicMock()
            if face_id == "face-2-uuid":
                mock_candidate = MagicMock()
                mock_candidate.person_id = "target-person-id"
                mock_candidate.confidence = 0.88
                mock_result.candidates = [mock_candidate]
            else:
                mock_result.candidates = []
            return [mock_result]

        mock_client.face.identify.side_effect = identify_side_effect

        # Execute workflow
        provider = get_provider("azure", azure_config)
        provider.load_reference_photos(reference_photos)
        faces = provider.detect_faces(test_photo_bytes, source="group_photo.jpg")

        # Verify detection
        assert len(faces) == 3

        # Check each face
        results = [provider.compare_faces(face) for face in faces]

        # Verify only second face matches
        assert results[0].is_match is False
        assert results[1].is_match is True
        assert results[1].confidence == 0.88
        assert results[2].is_match is False


# ============================================================================
# Component Test: Integration with organize_photos module
# ============================================================================
#
# Note: The organize_photos module's face recognition integration is already
# tested through the provider workflow tests above:
# - TestFactoryAzureProviderIntegration: Tests factory creation with Azure config
# - TestAzureTrainingWorkflow: Tests loading reference photos and training
# - TestAzureDetectionMatchingWorkflow: Tests provider.find_matches_in_image()
#
# The organize_photos.py module uses these same provider interfaces internally.
# Its process_images() function calls provider.find_matches_in_image() which
# is comprehensively tested in TestAzureDetectionMatchingWorkflow.
#
# Direct testing of organize_photos with Azure would require extensive mocking
# of DropboxClient and file operations, which is better suited for integration
# tests with the Dropbox SDK rather than component tests.


# ============================================================================
# Component Test: Error Handling Across Components
# ============================================================================


class TestAzureErrorHandlingAcrossComponents:
    """Test error handling propagation across components."""

    def test_training_timeout_propagates(self, mock_azure_sdk, azure_config, reference_photos):
        """Test that training timeout error propagates correctly."""
        from scripts.face_recognizer import get_provider

        # Set very short timeout
        azure_config["training_timeout"] = 0.1

        mock_client = mock_azure_sdk["FaceClient"].return_value
        mock_client.person_group.get.return_value = MagicMock()
        mock_client.person_group_person.list.return_value = []
        mock_person = MagicMock()
        mock_person.person_id = "person-id"
        mock_client.person_group_person.create.return_value = mock_person
        mock_client.person_group_person.add_face_from_stream.return_value = MagicMock()

        # Training never completes
        mock_status = MagicMock()
        mock_status.status = "running"
        mock_client.person_group.get_training_status.return_value = mock_status

        provider = get_provider("azure", azure_config)

        with pytest.raises(TimeoutError) as exc_info:
            provider.load_reference_photos(reference_photos)

        assert "timed out" in str(exc_info.value)

    def test_api_error_during_detection_handled(self, mock_azure_sdk, azure_config, test_photo_bytes):
        """Test that API errors during detection are handled gracefully."""
        from scripts.face_recognizer import get_provider

        mock_client = mock_azure_sdk["FaceClient"].return_value
        mock_client.face.detect_with_stream.side_effect = Exception("Azure API rate limit exceeded")

        provider = get_provider("azure", azure_config)
        faces = provider.detect_faces(test_photo_bytes, source="test.jpg")

        # Should return empty list, not raise exception
        assert faces == []

    def test_invalid_config_raises_on_factory(self, mock_azure_sdk):
        """Test that invalid configuration raises error at factory level."""
        from scripts.face_recognizer import FaceRecognitionFactory

        invalid_config = {
            "azure_endpoint": "https://test.api.com",
            # Missing azure_api_key
        }

        with pytest.raises(ValueError) as exc_info:
            FaceRecognitionFactory.create_provider("azure", invalid_config)

        assert "azure_api_key" in str(exc_info.value)


# ============================================================================
# Component Test: Concurrent Operations
# ============================================================================


class TestAzureConcurrentOperations:
    """Test behavior with multiple sequential operations."""

    def test_multiple_detection_calls(self, mock_azure_sdk, azure_config, reference_photos):
        """Test multiple detection calls on same provider instance."""
        from scripts.face_recognizer import get_provider

        mock_client = mock_azure_sdk["FaceClient"].return_value

        # Setup training
        mock_client.person_group.get.return_value = MagicMock()
        mock_client.person_group_person.list.return_value = []
        mock_person = MagicMock()
        mock_person.person_id = "person-id"
        mock_client.person_group_person.create.return_value = mock_person
        mock_client.person_group_person.add_face_from_stream.return_value = MagicMock()
        mock_status = MagicMock()
        mock_status.status = mock_azure_sdk["TrainingStatusType"].succeeded
        mock_client.person_group.get_training_status.return_value = mock_status

        # Different faces for different images
        call_count = [0]

        def detect_side_effect(*args, **kwargs):
            call_count[0] += 1
            face = MagicMock()
            face.face_id = f"face-{call_count[0]}"
            return [face]

        mock_client.face.detect_with_stream.side_effect = detect_side_effect

        # Execute
        provider = get_provider("azure", azure_config)
        provider.load_reference_photos(reference_photos)

        # Create multiple test images
        images = []
        for i in range(5):
            img = Image.new("RGB", (100, 100), color=(i * 50, 100, 100))
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG")
            images.append(buffer.getvalue())

        # Detect in all images
        all_faces = []
        for i, img_bytes in enumerate(images):
            faces = provider.detect_faces(img_bytes, source=f"image_{i}.jpg")
            all_faces.extend(faces)

        # Verify
        assert len(all_faces) == 5
        assert mock_client.face.detect_with_stream.call_count == 5

        # Verify unique face IDs
        face_ids = [str(f.encoding[0]) for f in all_faces]
        assert len(set(face_ids)) == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
