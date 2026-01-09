"""Unit tests for azure_provider.py face recognition module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import UUID

import numpy as np
import pytest

# Add scripts directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))


class TestRetryWithBackoff:
    """Test retry_with_backoff decorator."""

    def test_retry_succeeds_on_first_attempt(self):
        """Test function succeeds without retry."""
        from scripts.face_recognizer.providers.azure_provider import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def success_func():
            nonlocal call_count
            call_count += 1
            return "success"

        result = success_func()

        assert result == "success"
        assert call_count == 1

    def test_retry_on_rate_limit_error(self):
        """Test retry on 429 rate limit error."""
        from scripts.face_recognizer.providers.azure_provider import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def rate_limited_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise Exception("Error 429: Rate limit exceeded")
            return "success"

        result = rate_limited_func()

        assert result == "success"
        assert call_count == 3

    def test_retry_on_timeout_error(self):
        """Test retry on timeout error."""
        from scripts.face_recognizer.providers.azure_provider import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def timeout_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Connection timeout")
            return "success"

        result = timeout_func()

        assert result == "success"
        assert call_count == 2

    def test_retry_on_connection_error(self):
        """Test retry on connection error."""
        from scripts.face_recognizer.providers.azure_provider import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def connection_func():
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise Exception("Connection refused")
            return "success"

        result = connection_func()

        assert result == "success"
        assert call_count == 2

    def test_no_retry_on_non_retryable_error(self):
        """Test that non-retryable errors are raised immediately."""
        from scripts.face_recognizer.providers.azure_provider import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=3, base_delay=0.01)
        def auth_error_func():
            nonlocal call_count
            call_count += 1
            raise Exception("Authentication failed: invalid API key")

        with pytest.raises(Exception) as exc_info:
            auth_error_func()

        assert "Authentication failed" in str(exc_info.value)
        assert call_count == 1  # No retries for auth errors

    def test_max_retries_exceeded(self):
        """Test that error is raised after max retries."""
        from scripts.face_recognizer.providers.azure_provider import retry_with_backoff

        call_count = 0

        @retry_with_backoff(max_retries=2, base_delay=0.01)
        def always_rate_limited():
            nonlocal call_count
            call_count += 1
            raise Exception("Error 429: Rate limit exceeded")

        with pytest.raises(Exception) as exc_info:
            always_rate_limited()

        assert "429" in str(exc_info.value)
        assert call_count == 3  # Initial + 2 retries


@pytest.fixture(autouse=True)
def mock_azure_available():
    """
    Mock AZURE_AVAILABLE to True and patch Azure SDK modules for all tests.
    This allows tests to run in CI environments where Azure SDK is not installed.

    We inject the mock classes directly into the module before tests run.
    Each test gets fresh mock instances to ensure test isolation.
    """
    import scripts.face_recognizer.providers.azure_provider as azure_module

    # Store originals (if they exist)
    original_available = getattr(azure_module, "AZURE_AVAILABLE", False)
    original_face_client = getattr(azure_module, "FaceClient", None)
    original_training_status = getattr(azure_module, "TrainingStatusType", None)
    original_credentials = getattr(azure_module, "CognitiveServicesCredentials", None)

    # Create fresh mocks for each test
    mock_face_client_class = MagicMock()
    mock_training_status_type = MagicMock()
    mock_training_status_type.succeeded = "succeeded"
    mock_training_status_type.failed = "failed"
    mock_training_status_type.running = "running"
    mock_training_status_type.nonstarted = "nonstarted"
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
    }

    # Restore originals
    azure_module.AZURE_AVAILABLE = original_available
    if original_face_client is not None:
        azure_module.FaceClient = original_face_client
    if original_training_status is not None:
        azure_module.TrainingStatusType = original_training_status
    if original_credentials is not None:
        azure_module.CognitiveServicesCredentials = original_credentials


class TestAzureProviderImport:
    """Test import behavior when Azure SDK is not available."""

    def test_import_error_when_azure_not_available(self):
        """Test that ImportError is raised when Azure SDK is not installed."""
        with patch(
            "scripts.face_recognizer.providers.azure_provider.AZURE_AVAILABLE",
            False,
        ):
            from scripts.face_recognizer.providers import azure_provider

            config = {
                "azure_api_key": "test-key",
                "azure_endpoint": "https://test.cognitiveservices.azure.com",
            }

            with pytest.raises(ImportError) as exc_info:
                azure_provider.AzureFaceRecognitionProvider(config)

            assert "azure-cognitiveservices-vision-face" in str(exc_info.value)


class TestAzureFaceRecognitionProviderInit:
    """Test AzureFaceRecognitionProvider initialization."""

    def test_init_with_required_config(self, mock_azure_available):
        """Test initialization with required configuration values."""
        from scripts.face_recognizer.providers.azure_provider import AzureFaceRecognitionProvider

        config = {
            "azure_api_key": "test-api-key",
            "azure_endpoint": "https://test.cognitiveservices.azure.com",
        }
        provider = AzureFaceRecognitionProvider(config)

        assert provider.person_group_id == "dropbox-photo-organizer"
        assert provider.confidence_threshold == 0.5
        assert provider.training_timeout == 300
        assert provider.person_id is None
        assert provider.reference_encodings == []

    def test_init_with_custom_config(self, mock_azure_available):
        """Test initialization with custom configuration values."""
        from scripts.face_recognizer.providers.azure_provider import AzureFaceRecognitionProvider

        config = {
            "azure_api_key": "test-api-key",
            "azure_endpoint": "https://test.cognitiveservices.azure.com",
            "person_group_id": "custom-group",
            "confidence_threshold": 0.7,
            "training_timeout": 600,
        }
        provider = AzureFaceRecognitionProvider(config)

        assert provider.person_group_id == "custom-group"
        assert provider.confidence_threshold == 0.7
        assert provider.training_timeout == 600

    def test_init_missing_api_key_raises_error(self, mock_azure_available):
        """Test that ValueError is raised when api_key is missing."""
        from scripts.face_recognizer.providers.azure_provider import AzureFaceRecognitionProvider

        config = {
            "azure_endpoint": "https://test.cognitiveservices.azure.com",
        }

        with pytest.raises(ValueError) as exc_info:
            AzureFaceRecognitionProvider(config)

        assert "azure_api_key" in str(exc_info.value)

    def test_init_missing_endpoint_raises_error(self, mock_azure_available):
        """Test that ValueError is raised when endpoint is missing."""
        from scripts.face_recognizer.providers.azure_provider import AzureFaceRecognitionProvider

        config = {
            "azure_api_key": "test-api-key",
        }

        with pytest.raises(ValueError) as exc_info:
            AzureFaceRecognitionProvider(config)

        assert "azure_endpoint" in str(exc_info.value)

    def test_init_stores_config(self, mock_azure_available):
        """Test that config is stored in parent class."""
        from scripts.face_recognizer.providers.azure_provider import AzureFaceRecognitionProvider

        config = {
            "azure_api_key": "test-api-key",
            "azure_endpoint": "https://test.cognitiveservices.azure.com",
            "custom_key": "value",
        }
        provider = AzureFaceRecognitionProvider(config)

        assert provider.config == config


class TestGetProviderName:
    """Test get_provider_name method."""

    def test_get_provider_name_returns_azure(self, mock_azure_available):
        """Test that get_provider_name returns 'azure'."""
        from scripts.face_recognizer.providers.azure_provider import AzureFaceRecognitionProvider

        config = {
            "azure_api_key": "test-api-key",
            "azure_endpoint": "https://test.cognitiveservices.azure.com",
        }
        provider = AzureFaceRecognitionProvider(config)

        assert provider.get_provider_name() == "azure"


class TestValidateConfiguration:
    """Test validate_configuration method."""

    def test_validate_configuration_success(self, mock_azure_available):
        """Test validation passes when API call succeeds."""
        from scripts.face_recognizer.providers.azure_provider import AzureFaceRecognitionProvider

        config = {
            "azure_api_key": "test-api-key",
            "azure_endpoint": "https://test.cognitiveservices.azure.com",
        }
        provider = AzureFaceRecognitionProvider(config)

        # Mock successful API call
        provider.client.person_group.list.return_value = []

        is_valid, error = provider.validate_configuration()

        assert is_valid is True
        assert error is None

    def test_validate_configuration_azure_unavailable(self, mock_azure_available):
        """Test validation fails when Azure SDK is not available."""
        from scripts.face_recognizer.providers.azure_provider import AzureFaceRecognitionProvider

        config = {
            "azure_api_key": "test-api-key",
            "azure_endpoint": "https://test.cognitiveservices.azure.com",
        }
        provider = AzureFaceRecognitionProvider(config)

        # Override AZURE_AVAILABLE after provider creation
        with patch(
            "scripts.face_recognizer.providers.azure_provider.AZURE_AVAILABLE",
            False,
        ):
            is_valid, error = provider.validate_configuration()

            assert is_valid is False
            assert "not installed" in error

    def test_validate_configuration_api_error(self, mock_azure_available):
        """Test validation fails when API call fails."""
        from scripts.face_recognizer.providers.azure_provider import AzureFaceRecognitionProvider

        config = {
            "azure_api_key": "test-api-key",
            "azure_endpoint": "https://test.cognitiveservices.azure.com",
        }
        provider = AzureFaceRecognitionProvider(config)

        # Mock API error
        provider.client.person_group.list.side_effect = Exception("Authentication failed")

        is_valid, error = provider.validate_configuration()

        assert is_valid is False
        assert "Azure Face API error" in error
        assert "Authentication failed" in error


class TestPersonGroupManagement:
    """Test person group management methods."""

    @pytest.fixture
    def provider(self, mock_azure_available):
        """Create an AzureFaceRecognitionProvider instance."""
        from scripts.face_recognizer.providers.azure_provider import AzureFaceRecognitionProvider

        config = {
            "azure_api_key": "test-api-key",
            "azure_endpoint": "https://test.cognitiveservices.azure.com",
        }
        return AzureFaceRecognitionProvider(config)

    def test_create_or_get_person_group_existing(self, provider):
        """Test using an existing person group."""
        # Mock existing person group
        provider.client.person_group.get.return_value = MagicMock()

        provider._create_or_get_person_group()

        provider.client.person_group.get.assert_called_once_with(provider.person_group_id)
        provider.client.person_group.create.assert_not_called()

    def test_create_or_get_person_group_new(self, provider):
        """Test creating a new person group."""
        # Mock person group not found
        provider.client.person_group.get.side_effect = Exception("Not found")

        provider._create_or_get_person_group()

        provider.client.person_group.create.assert_called_once()
        call_kwargs = provider.client.person_group.create.call_args[1]
        assert call_kwargs["person_group_id"] == provider.person_group_id
        assert call_kwargs["recognition_model"] == "recognition_04"

    def test_create_or_get_person_existing(self, provider):
        """Test getting an existing person."""
        mock_person = MagicMock()
        mock_person.person_id = "existing-person-id"
        mock_person.name = "Test Person"
        provider.client.person_group_person.list.return_value = [mock_person]

        provider._create_or_get_person()

        assert provider.person_id == "existing-person-id"
        provider.client.person_group_person.create.assert_not_called()

    def test_create_or_get_person_new(self, provider):
        """Test creating a new person."""
        provider.client.person_group_person.list.return_value = []
        mock_new_person = MagicMock()
        mock_new_person.person_id = "new-person-id"
        provider.client.person_group_person.create.return_value = mock_new_person

        provider._create_or_get_person()

        assert provider.person_id == "new-person-id"
        provider.client.person_group_person.create.assert_called_once()


class TestLoadReferencePhotos:
    """Test load_reference_photos method."""

    @pytest.fixture
    def provider(self, mock_azure_available):
        """Create an AzureFaceRecognitionProvider instance."""
        from scripts.face_recognizer.providers.azure_provider import AzureFaceRecognitionProvider

        config = {
            "azure_api_key": "test-api-key",
            "azure_endpoint": "https://test.cognitiveservices.azure.com",
            "training_timeout": 5,  # Short timeout for tests
        }
        return AzureFaceRecognitionProvider(config)

    @pytest.fixture
    def mock_image_file(self, tmp_path):
        """Create a temporary test image file."""
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        img_path = tmp_path / "test_face.jpg"
        img.save(img_path)
        return str(img_path)

    def test_load_reference_photos_success(self, provider, mock_image_file, mock_azure_available):
        """Test successful loading of reference photos."""
        # Setup mocks
        provider.client.person_group.get.return_value = MagicMock()
        provider.client.person_group_person.list.return_value = []
        mock_person = MagicMock()
        mock_person.person_id = "test-person-id"
        provider.client.person_group_person.create.return_value = mock_person
        provider.client.person_group_person.add_face_from_stream.return_value = MagicMock()

        # Mock training status
        mock_status = MagicMock()
        mock_status.status = mock_azure_available["TrainingStatusType"].succeeded
        provider.client.person_group.get_training_status.return_value = mock_status

        count = provider.load_reference_photos([mock_image_file])

        assert count == 1
        assert len(provider.reference_encodings) == 1
        assert provider.reference_encodings[0].source == mock_image_file

    def test_load_reference_photos_file_not_found(self, provider, mock_azure_available):
        """Test handling of non-existent reference photo."""
        # Setup mocks for person group creation
        provider.client.person_group.get.return_value = MagicMock()
        provider.client.person_group_person.list.return_value = []
        mock_person = MagicMock()
        mock_person.person_id = "test-person-id"
        provider.client.person_group_person.create.return_value = mock_person

        with pytest.raises(Exception) as exc_info:
            provider.load_reference_photos(["/nonexistent/path/photo.jpg"])

        assert "No reference faces could be added" in str(exc_info.value)

    def test_load_reference_photos_training_success(self, provider, mock_image_file, mock_azure_available):
        """Test training completes successfully."""
        # Setup mocks
        provider.client.person_group.get.return_value = MagicMock()
        provider.client.person_group_person.list.return_value = []
        mock_person = MagicMock()
        mock_person.person_id = "test-person-id"
        provider.client.person_group_person.create.return_value = mock_person
        provider.client.person_group_person.add_face_from_stream.return_value = MagicMock()

        # Mock training status - succeed on first check
        mock_status = MagicMock()
        mock_status.status = mock_azure_available["TrainingStatusType"].succeeded
        provider.client.person_group.get_training_status.return_value = mock_status

        count = provider.load_reference_photos([mock_image_file])

        assert count == 1
        provider.client.person_group.train.assert_called_once()

    def test_load_reference_photos_training_failure(self, provider, mock_image_file, mock_azure_available):
        """Test handling of training failure."""
        # Setup mocks
        provider.client.person_group.get.return_value = MagicMock()
        provider.client.person_group_person.list.return_value = []
        mock_person = MagicMock()
        mock_person.person_id = "test-person-id"
        provider.client.person_group_person.create.return_value = mock_person
        provider.client.person_group_person.add_face_from_stream.return_value = MagicMock()

        # Mock training status - fail
        mock_status = MagicMock()
        mock_status.status = mock_azure_available["TrainingStatusType"].failed
        mock_status.message = "Training failed due to insufficient data"
        provider.client.person_group.get_training_status.return_value = mock_status

        with pytest.raises(Exception) as exc_info:
            provider.load_reference_photos([mock_image_file])

        assert "Training failed" in str(exc_info.value)

    def test_load_reference_photos_training_timeout(self, provider, mock_image_file, mock_azure_available):
        """Test handling of training timeout."""
        # Setup mocks
        provider.client.person_group.get.return_value = MagicMock()
        provider.client.person_group_person.list.return_value = []
        mock_person = MagicMock()
        mock_person.person_id = "test-person-id"
        provider.client.person_group_person.create.return_value = mock_person
        provider.client.person_group_person.add_face_from_stream.return_value = MagicMock()

        # Mock training status - always running (will timeout)
        mock_status = MagicMock()
        mock_status.status = "running"
        provider.client.person_group.get_training_status.return_value = mock_status

        # Set very short timeout
        provider.training_timeout = 0.1

        with pytest.raises(TimeoutError) as exc_info:
            provider.load_reference_photos([mock_image_file])

        assert "timed out" in str(exc_info.value)

    def test_load_reference_photos_training_running_then_success(self, provider, mock_image_file, mock_azure_available):
        """Test training that starts running then succeeds."""
        # Setup mocks
        provider.client.person_group.get.return_value = MagicMock()
        provider.client.person_group_person.list.return_value = []
        mock_person = MagicMock()
        mock_person.person_id = "test-person-id"
        provider.client.person_group_person.create.return_value = mock_person
        provider.client.person_group_person.add_face_from_stream.return_value = MagicMock()

        # Mock training status - first running, then succeeded
        mock_status_running = MagicMock()
        mock_status_running.status = mock_azure_available["TrainingStatusType"].running
        mock_status_success = MagicMock()
        mock_status_success.status = mock_azure_available["TrainingStatusType"].succeeded

        provider.client.person_group.get_training_status.side_effect = [
            mock_status_running,
            mock_status_success,
        ]

        count = provider.load_reference_photos([mock_image_file])

        assert count == 1
        # Verify training status was checked multiple times
        assert provider.client.person_group.get_training_status.call_count == 2

    def test_load_reference_photos_training_nonstarted_then_success(self, provider, mock_image_file, mock_azure_available):
        """Test training that starts as nonstarted then succeeds."""
        # Setup mocks
        provider.client.person_group.get.return_value = MagicMock()
        provider.client.person_group_person.list.return_value = []
        mock_person = MagicMock()
        mock_person.person_id = "test-person-id"
        provider.client.person_group_person.create.return_value = mock_person
        provider.client.person_group_person.add_face_from_stream.return_value = MagicMock()

        # Mock training status - first nonstarted, then succeeded
        mock_status_nonstarted = MagicMock()
        mock_status_nonstarted.status = mock_azure_available["TrainingStatusType"].nonstarted
        mock_status_success = MagicMock()
        mock_status_success.status = mock_azure_available["TrainingStatusType"].succeeded

        provider.client.person_group.get_training_status.side_effect = [
            mock_status_nonstarted,
            mock_status_success,
        ]

        count = provider.load_reference_photos([mock_image_file])

        assert count == 1

    def test_load_reference_photos_training_unexpected_status(self, provider, mock_image_file, mock_azure_available):
        """Test training with unexpected status still continues polling."""
        # Setup mocks
        provider.client.person_group.get.return_value = MagicMock()
        provider.client.person_group_person.list.return_value = []
        mock_person = MagicMock()
        mock_person.person_id = "test-person-id"
        provider.client.person_group_person.create.return_value = mock_person
        provider.client.person_group_person.add_face_from_stream.return_value = MagicMock()

        # Mock training status - unexpected status, then succeeded
        mock_status_unexpected = MagicMock()
        mock_status_unexpected.status = "unexpected_status"
        mock_status_success = MagicMock()
        mock_status_success.status = mock_azure_available["TrainingStatusType"].succeeded

        provider.client.person_group.get_training_status.side_effect = [
            mock_status_unexpected,
            mock_status_success,
        ]

        count = provider.load_reference_photos([mock_image_file])

        assert count == 1
        # Verify training status was checked multiple times (didn't get stuck)
        assert provider.client.person_group.get_training_status.call_count == 2


class TestDetectFaces:
    """Test detect_faces method."""

    @pytest.fixture
    def provider(self, mock_azure_available):
        """Create an AzureFaceRecognitionProvider instance."""
        from scripts.face_recognizer.providers.azure_provider import AzureFaceRecognitionProvider

        config = {
            "azure_api_key": "test-api-key",
            "azure_endpoint": "https://test.cognitiveservices.azure.com",
        }
        return AzureFaceRecognitionProvider(config)

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
        mock_face = MagicMock()
        mock_face.face_id = "face-uuid-12345"
        provider.client.face.detect_with_stream.return_value = [mock_face]

        faces = provider.detect_faces(test_image_bytes, source="test.jpg")

        assert len(faces) == 1
        assert faces[0].source == "test.jpg"
        # Verify face_id is stored correctly as string
        assert str(faces[0].encoding[0]) == "face-uuid-12345"

    def test_detect_faces_no_faces_found(self, provider, test_image_bytes):
        """Test when no faces are detected."""
        provider.client.face.detect_with_stream.return_value = []

        faces = provider.detect_faces(test_image_bytes, source="test.jpg")

        assert faces == []

    def test_detect_faces_multiple_faces(self, provider, test_image_bytes):
        """Test detecting multiple faces."""
        mock_face1 = MagicMock()
        mock_face1.face_id = "face-uuid-1"
        mock_face2 = MagicMock()
        mock_face2.face_id = "face-uuid-2"
        provider.client.face.detect_with_stream.return_value = [mock_face1, mock_face2]

        faces = provider.detect_faces(test_image_bytes, source="test.jpg")

        assert len(faces) == 2
        assert str(faces[0].encoding[0]) == "face-uuid-1"
        assert str(faces[1].encoding[0]) == "face-uuid-2"

    def test_detect_faces_api_error(self, provider, test_image_bytes):
        """Test handling of API errors during detection."""
        provider.client.face.detect_with_stream.side_effect = Exception("API error")

        faces = provider.detect_faces(test_image_bytes, source="test.jpg")

        assert faces == []

    def test_detect_faces_default_source(self, provider, test_image_bytes):
        """Test detect_faces with default source parameter."""
        mock_face = MagicMock()
        mock_face.face_id = "face-uuid-12345"
        provider.client.face.detect_with_stream.return_value = [mock_face]

        faces = provider.detect_faces(test_image_bytes)

        assert len(faces) == 1
        assert faces[0].source == "unknown"

    def test_detect_faces_stores_uuid_object(self, provider, test_image_bytes):
        """Test that detect_faces stores UUID objects directly."""
        test_uuid = UUID("12345678-1234-5678-1234-567812345678")
        mock_face = MagicMock()
        mock_face.face_id = test_uuid
        provider.client.face.detect_with_stream.return_value = [mock_face]

        faces = provider.detect_faces(test_image_bytes, source="test.jpg")

        assert len(faces) == 1
        # The UUID should be stored directly (not converted to string)
        assert faces[0].encoding[0] == test_uuid

    def test_detect_faces_retry_on_rate_limit(self, provider, test_image_bytes):
        """Test that detect_faces retries on rate limit errors."""
        mock_face = MagicMock()
        mock_face.face_id = "face-uuid-12345"

        # First call fails with rate limit, second succeeds
        provider.client.face.detect_with_stream.side_effect = [
            Exception("Error 429: Rate limit exceeded"),
            [mock_face],
        ]

        faces = provider.detect_faces(test_image_bytes, source="test.jpg")

        assert len(faces) == 1
        assert provider.client.face.detect_with_stream.call_count == 2


class TestCompareFaces:
    """Test compare_faces method."""

    @pytest.fixture
    def provider_with_person(self, mock_azure_available):
        """Create a provider with a person_id set."""
        from scripts.face_recognizer.providers.azure_provider import AzureFaceRecognitionProvider

        config = {
            "azure_api_key": "test-api-key",
            "azure_endpoint": "https://test.cognitiveservices.azure.com",
            "confidence_threshold": 0.5,
        }
        provider = AzureFaceRecognitionProvider(config)
        provider.person_id = "target-person-id"
        return provider

    @pytest.fixture
    def test_face_encoding(self):
        """Create a test face encoding."""
        from scripts.face_recognizer.base_provider import FaceEncoding

        return FaceEncoding(
            encoding=np.array(["face-uuid-12345"], dtype=object),
            source="test.jpg",
        )

    def test_compare_faces_match_found(self, provider_with_person, test_face_encoding):
        """Test comparing a face that matches."""
        mock_candidate = MagicMock()
        mock_candidate.person_id = "target-person-id"
        mock_candidate.confidence = 0.85

        mock_result = MagicMock()
        mock_result.candidates = [mock_candidate]
        provider_with_person.client.face.identify.return_value = [mock_result]

        result = provider_with_person.compare_faces(test_face_encoding)

        assert result.is_match is True
        assert result.confidence == 0.85
        assert result.distance == pytest.approx(0.15)  # 1.0 - 0.85

    def test_compare_faces_no_match(self, provider_with_person, test_face_encoding):
        """Test comparing a face that doesn't match."""
        # No candidates returned
        mock_result = MagicMock()
        mock_result.candidates = []
        provider_with_person.client.face.identify.return_value = [mock_result]

        result = provider_with_person.compare_faces(test_face_encoding)

        assert result.is_match is False
        assert result.confidence == 0.0
        assert result.distance == 1.0

    def test_compare_faces_different_person(self, provider_with_person, test_face_encoding):
        """Test when identified person is not the target."""
        mock_candidate = MagicMock()
        mock_candidate.person_id = "different-person-id"
        mock_candidate.confidence = 0.9

        mock_result = MagicMock()
        mock_result.candidates = [mock_candidate]
        provider_with_person.client.face.identify.return_value = [mock_result]

        result = provider_with_person.compare_faces(test_face_encoding)

        assert result.is_match is False
        assert result.confidence == 0.0

    def test_compare_faces_no_person_id(self, mock_azure_available, test_face_encoding):
        """Test comparing when no person_id is set."""
        from scripts.face_recognizer.providers.azure_provider import AzureFaceRecognitionProvider

        config = {
            "azure_api_key": "test-api-key",
            "azure_endpoint": "https://test.cognitiveservices.azure.com",
        }
        provider = AzureFaceRecognitionProvider(config)
        # Don't set person_id

        result = provider.compare_faces(test_face_encoding)

        assert result.is_match is False
        assert result.confidence == 0.0
        assert result.distance == 1.0

    def test_compare_faces_api_error(self, provider_with_person, test_face_encoding):
        """Test handling of API errors during comparison."""
        provider_with_person.client.face.identify.side_effect = Exception("API error")

        result = provider_with_person.compare_faces(test_face_encoding)

        assert result.is_match is False
        assert result.confidence == 0.0
        assert result.distance == 1.0

    def test_compare_faces_custom_tolerance(self, provider_with_person, test_face_encoding):
        """Test comparing with custom tolerance parameter."""
        mock_candidate = MagicMock()
        mock_candidate.person_id = "target-person-id"
        mock_candidate.confidence = 0.85

        mock_result = MagicMock()
        mock_result.candidates = [mock_candidate]
        provider_with_person.client.face.identify.return_value = [mock_result]

        provider_with_person.compare_faces(test_face_encoding, tolerance=0.8)

        # Verify custom tolerance was passed to API
        call_kwargs = provider_with_person.client.face.identify.call_args[1]
        assert call_kwargs["confidence_threshold"] == 0.8

    def test_compare_faces_with_uuid_object(self, provider_with_person):
        """Test comparing with UUID object in encoding."""
        from scripts.face_recognizer.base_provider import FaceEncoding

        test_uuid = UUID("12345678-1234-5678-1234-567812345678")
        face_encoding = FaceEncoding(
            encoding=np.array([test_uuid], dtype=object),
            source="test.jpg",
        )

        mock_candidate = MagicMock()
        mock_candidate.person_id = "target-person-id"
        mock_candidate.confidence = 0.85

        mock_result = MagicMock()
        mock_result.candidates = [mock_candidate]
        provider_with_person.client.face.identify.return_value = [mock_result]

        result = provider_with_person.compare_faces(face_encoding)

        assert result.is_match is True
        # Verify UUID was converted to string for API call
        call_args = provider_with_person.client.face.identify.call_args[0]
        assert call_args[0] == [str(test_uuid)]

    def test_compare_faces_retry_on_rate_limit(self, provider_with_person, test_face_encoding):
        """Test that compare_faces retries on rate limit errors."""
        mock_candidate = MagicMock()
        mock_candidate.person_id = "target-person-id"
        mock_candidate.confidence = 0.85

        mock_result = MagicMock()
        mock_result.candidates = [mock_candidate]

        # First call fails with rate limit, second succeeds
        provider_with_person.client.face.identify.side_effect = [
            Exception("Error 429: Rate limit exceeded"),
            [mock_result],
        ]

        result = provider_with_person.compare_faces(test_face_encoding)

        assert result.is_match is True
        assert provider_with_person.client.face.identify.call_count == 2


class TestAzureProviderIntegration:
    """Integration tests for AzureFaceRecognitionProvider."""

    def test_full_workflow_mock(self, tmp_path, mock_azure_available):
        """Test the full workflow with mocked Azure SDK."""
        from PIL import Image

        from scripts.face_recognizer.providers.azure_provider import AzureFaceRecognitionProvider

        # Create test images
        ref_path = tmp_path / "reference.jpg"
        Image.new("RGB", (100, 100), color="red").save(ref_path)

        import io

        test_img = Image.new("RGB", (100, 100), color="blue")
        buffer = io.BytesIO()
        test_img.save(buffer, format="JPEG")
        test_bytes = buffer.getvalue()

        config = {
            "azure_api_key": "test-api-key",
            "azure_endpoint": "https://test.cognitiveservices.azure.com",
            "confidence_threshold": 0.5,
        }
        provider = AzureFaceRecognitionProvider(config)

        # Setup mocks for load_reference_photos
        provider.client.person_group.get.return_value = MagicMock()
        provider.client.person_group_person.list.return_value = []
        mock_person = MagicMock()
        mock_person.person_id = "test-person-id"
        provider.client.person_group_person.create.return_value = mock_person
        provider.client.person_group_person.add_face_from_stream.return_value = MagicMock()

        mock_status = MagicMock()
        mock_status.status = mock_azure_available["TrainingStatusType"].succeeded
        provider.client.person_group.get_training_status.return_value = mock_status

        # Load reference
        count = provider.load_reference_photos([str(ref_path)])
        assert count == 1

        # Setup mocks for detect_faces
        mock_face = MagicMock()
        mock_face.face_id = "detected-face-uuid"
        provider.client.face.detect_with_stream.return_value = [mock_face]

        # Detect faces
        faces = provider.detect_faces(test_bytes, source="test.jpg")
        assert len(faces) == 1

        # Setup mocks for compare_faces
        mock_candidate = MagicMock()
        mock_candidate.person_id = "test-person-id"
        mock_candidate.confidence = 0.9

        mock_result = MagicMock()
        mock_result.candidates = [mock_candidate]
        provider.client.face.identify.return_value = [mock_result]

        # Compare
        result = provider.compare_faces(faces[0])
        assert result.is_match is True
        assert result.confidence == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
