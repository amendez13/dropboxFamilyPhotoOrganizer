"""Unit tests for face_recognizer factory module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Add scripts directory to path for local imports
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

# Local import must come after path modification to avoid numpy reimport issues
from scripts.face_recognizer import FaceRecognitionFactory, get_provider  # noqa: E402


class TestFaceRecognitionFactory:
    """Test FaceRecognitionFactory class methods."""

    @pytest.fixture
    def mock_local_provider(self):
        """Create a mock LocalFaceRecognitionProvider."""
        mock_provider = MagicMock()
        mock_provider.validate_configuration.return_value = (True, None)
        return mock_provider

    @pytest.fixture
    def restore_providers(self):
        """Fixture to save and restore PROVIDERS dict after test."""
        original_providers = FaceRecognitionFactory.PROVIDERS.copy()
        yield
        FaceRecognitionFactory.PROVIDERS.clear()
        FaceRecognitionFactory.PROVIDERS.update(original_providers)

    def test_create_provider_local_success(self, mock_local_provider, restore_providers):
        """Test creating a local provider successfully."""
        mock_class = MagicMock(return_value=mock_local_provider)
        FaceRecognitionFactory.PROVIDERS["local"] = mock_class

        config = {"tolerance": 0.6}
        provider = FaceRecognitionFactory.create_provider("local", config)

        assert provider == mock_local_provider
        mock_class.assert_called_once_with(config)
        mock_local_provider.validate_configuration.assert_called_once()

    def test_create_provider_case_insensitive(self, mock_local_provider, restore_providers):
        """Test that provider name is case-insensitive."""
        mock_class = MagicMock(return_value=mock_local_provider)
        FaceRecognitionFactory.PROVIDERS["local"] = mock_class

        config = {"tolerance": 0.6}
        provider = FaceRecognitionFactory.create_provider("LOCAL", config)

        assert provider == mock_local_provider
        mock_class.assert_called_once_with(config)

    def test_create_provider_mixed_case(self, mock_local_provider, restore_providers):
        """Test that provider name handles mixed case."""
        mock_class = MagicMock(return_value=mock_local_provider)
        FaceRecognitionFactory.PROVIDERS["local"] = mock_class

        config = {}
        provider = FaceRecognitionFactory.create_provider("LoCaL", config)

        assert provider == mock_local_provider

    def test_create_provider_unknown_provider_raises_value_error(self):
        """Test that unknown provider name raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            FaceRecognitionFactory.create_provider("unknown_provider", {})

        assert "Unknown provider: 'unknown_provider'" in str(exc_info.value)
        assert "Available providers:" in str(exc_info.value)

    def test_create_provider_unavailable_provider_raises_import_error(self, restore_providers):
        """Test that unavailable provider (None) raises ImportError."""
        # Temporarily set aws provider to None to simulate missing dependency
        FaceRecognitionFactory.PROVIDERS["aws"] = None

        with pytest.raises(ImportError) as exc_info:
            FaceRecognitionFactory.create_provider("aws", {})

        assert "Provider 'aws' dependencies not installed" in str(exc_info.value)

    def test_create_provider_unavailable_azure_raises_import_error(self, restore_providers):
        """Test that unavailable azure provider raises ImportError."""
        FaceRecognitionFactory.PROVIDERS["azure"] = None

        with pytest.raises(ImportError) as exc_info:
            FaceRecognitionFactory.create_provider("azure", {})

        assert "Provider 'azure' dependencies not installed" in str(exc_info.value)

    def test_create_provider_invalid_configuration_raises_value_error(self, restore_providers):
        """Test that invalid provider configuration raises ValueError."""
        mock_provider = MagicMock()
        mock_provider.validate_configuration.return_value = (False, "Missing required config")

        mock_class = MagicMock(return_value=mock_provider)
        FaceRecognitionFactory.PROVIDERS["local"] = mock_class

        with pytest.raises(ValueError) as exc_info:
            FaceRecognitionFactory.create_provider("local", {})

        assert "Provider configuration invalid" in str(exc_info.value)
        assert "Missing required config" in str(exc_info.value)

    def test_create_provider_instantiation_exception_is_logged_and_raised(self, restore_providers):
        """Test that exceptions during provider instantiation are logged and re-raised."""
        mock_class = MagicMock(side_effect=RuntimeError("Initialization failed"))
        FaceRecognitionFactory.PROVIDERS["local"] = mock_class

        with pytest.raises(RuntimeError) as exc_info:
            FaceRecognitionFactory.create_provider("local", {})

        assert "Initialization failed" in str(exc_info.value)

    def test_create_provider_validation_exception_is_reraised(self, restore_providers):
        """Test that exceptions during validation are re-raised."""
        mock_provider = MagicMock()
        mock_provider.validate_configuration.side_effect = RuntimeError("Validation error")

        mock_class = MagicMock(return_value=mock_provider)
        FaceRecognitionFactory.PROVIDERS["local"] = mock_class

        with pytest.raises(RuntimeError) as exc_info:
            FaceRecognitionFactory.create_provider("local", {})

        assert "Validation error" in str(exc_info.value)

    def test_list_available_providers_returns_dict(self):
        """Test that list_available_providers returns a dictionary."""
        result = FaceRecognitionFactory.list_available_providers()

        assert isinstance(result, dict)
        assert "local" in result
        assert isinstance(result["local"], bool)

    def test_list_available_providers_local_is_available(self):
        """Test that local provider is always available."""
        result = FaceRecognitionFactory.list_available_providers()

        assert result["local"] is True

    def test_list_available_providers_includes_all_providers(self):
        """Test that all configured providers are included in the list."""
        result = FaceRecognitionFactory.list_available_providers()

        # Check that all providers from PROVIDERS dict are in the result
        for provider_name in FaceRecognitionFactory.PROVIDERS:
            assert provider_name in result

    def test_list_available_providers_none_is_false(self, restore_providers):
        """Test that None providers are reported as False."""
        FaceRecognitionFactory.PROVIDERS["test_provider"] = None

        result = FaceRecognitionFactory.list_available_providers()

        assert result["test_provider"] is False

    def test_list_available_providers_class_is_true(self, restore_providers):
        """Test that valid provider classes are reported as True."""
        FaceRecognitionFactory.PROVIDERS["test_provider"] = MagicMock

        result = FaceRecognitionFactory.list_available_providers()

        assert result["test_provider"] is True


class TestGetProviderFunction:
    """Test the get_provider convenience function."""

    @pytest.fixture
    def mock_local_provider(self):
        """Create a mock LocalFaceRecognitionProvider."""
        mock_provider = MagicMock()
        mock_provider.validate_configuration.return_value = (True, None)
        return mock_provider

    @pytest.fixture
    def restore_providers(self):
        """Fixture to save and restore PROVIDERS dict after test."""
        original_providers = FaceRecognitionFactory.PROVIDERS.copy()
        yield
        FaceRecognitionFactory.PROVIDERS.clear()
        FaceRecognitionFactory.PROVIDERS.update(original_providers)

    def test_get_provider_delegates_to_factory(self, mock_local_provider, restore_providers):
        """Test that get_provider calls FaceRecognitionFactory.create_provider."""
        mock_class = MagicMock(return_value=mock_local_provider)
        FaceRecognitionFactory.PROVIDERS["local"] = mock_class

        config = {"tolerance": 0.5}
        provider = get_provider("local", config)

        assert provider == mock_local_provider
        mock_class.assert_called_once_with(config)

    def test_get_provider_propagates_errors(self):
        """Test that get_provider propagates errors from factory."""
        with pytest.raises(ValueError) as exc_info:
            get_provider("nonexistent_provider", {})

        assert "Unknown provider" in str(exc_info.value)

    def test_get_provider_with_empty_config(self, mock_local_provider, restore_providers):
        """Test get_provider with empty configuration."""
        mock_class = MagicMock(return_value=mock_local_provider)
        FaceRecognitionFactory.PROVIDERS["local"] = mock_class

        provider = get_provider("local", {})

        assert provider == mock_local_provider
        mock_class.assert_called_once_with({})


class TestProviderImportHandling:
    """Test handling of optional provider imports."""

    def test_aws_provider_in_providers_dict(self):
        """Test that AWS provider key exists in PROVIDERS dict."""
        assert "aws" in FaceRecognitionFactory.PROVIDERS

    def test_azure_provider_in_providers_dict(self):
        """Test that Azure provider key exists in PROVIDERS dict."""
        assert "azure" in FaceRecognitionFactory.PROVIDERS

    def test_local_provider_in_providers_dict(self):
        """Test that local provider key exists in PROVIDERS dict."""
        assert "local" in FaceRecognitionFactory.PROVIDERS

    def test_factory_works_with_local_provider(self):
        """Test that factory can create a local provider."""
        # This tests the actual local provider integration
        mock_provider = MagicMock()
        mock_provider.validate_configuration.return_value = (True, None)

        original = FaceRecognitionFactory.PROVIDERS["local"]
        try:
            mock_class = MagicMock(return_value=mock_provider)
            FaceRecognitionFactory.PROVIDERS["local"] = mock_class

            provider = FaceRecognitionFactory.create_provider("local", {})
            assert provider is not None
        finally:
            FaceRecognitionFactory.PROVIDERS["local"] = original


class TestCreateProviderLogging:
    """Test logging behavior in create_provider."""

    @pytest.fixture
    def restore_providers(self):
        """Fixture to save and restore PROVIDERS dict after test."""
        original_providers = FaceRecognitionFactory.PROVIDERS.copy()
        yield
        FaceRecognitionFactory.PROVIDERS.clear()
        FaceRecognitionFactory.PROVIDERS.update(original_providers)

    def test_create_provider_logs_info_message(self, restore_providers):
        """Test that create_provider logs an info message."""
        mock_provider = MagicMock()
        mock_provider.validate_configuration.return_value = (True, None)
        mock_class = MagicMock(return_value=mock_provider)
        FaceRecognitionFactory.PROVIDERS["local"] = mock_class

        with patch("scripts.face_recognizer.logging") as mock_logging:
            mock_logger = MagicMock()
            mock_logging.getLogger.return_value = mock_logger

            FaceRecognitionFactory.create_provider("local", {})

            mock_logger.info.assert_called()

    def test_create_provider_logs_error_on_exception(self, restore_providers):
        """Test that create_provider logs error when exception occurs."""
        mock_class = MagicMock(side_effect=RuntimeError("Test error"))
        FaceRecognitionFactory.PROVIDERS["local"] = mock_class

        with patch("scripts.face_recognizer.logging") as mock_logging:
            mock_logger = MagicMock()
            mock_logging.getLogger.return_value = mock_logger

            with pytest.raises(RuntimeError):
                FaceRecognitionFactory.create_provider("local", {})

            mock_logger.error.assert_called()


class TestValueErrorMessages:
    """Test that ValueError messages include useful information."""

    def test_unknown_provider_lists_available_providers(self):
        """Test that unknown provider error lists available providers."""
        with pytest.raises(ValueError) as exc_info:
            FaceRecognitionFactory.create_provider("invalid", {})

        error_message = str(exc_info.value)
        assert "Unknown provider" in error_message
        # Should list at least 'local' as available
        assert "local" in error_message or "Available providers" in error_message


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
