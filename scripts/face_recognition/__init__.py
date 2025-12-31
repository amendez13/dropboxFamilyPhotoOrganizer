"""
Face recognition module with support for multiple providers.
Provides a factory pattern to easily instantiate different face recognition providers.
"""

import logging
from typing import Dict, Optional

from scripts.face_recognition.base_provider import BaseFaceRecognitionProvider
from scripts.face_recognition.providers.local_provider import LocalFaceRecognitionProvider

# Optional providers (will be None if dependencies not installed)
try:
    from scripts.face_recognition.providers.aws_provider import AWSFaceRecognitionProvider
except ImportError:
    AWSFaceRecognitionProvider = None

try:
    from scripts.face_recognition.providers.azure_provider import AzureFaceRecognitionProvider
except ImportError:
    AzureFaceRecognitionProvider = None


class FaceRecognitionFactory:
    """
    Factory for creating face recognition provider instances.

    Supported providers:
    - 'local': Local face_recognition library (dlib-based)
    - 'aws': AWS Rekognition
    - 'azure': Azure Face API
    """

    PROVIDERS = {
        'local': LocalFaceRecognitionProvider,
        'aws': AWSFaceRecognitionProvider,
        'azure': AzureFaceRecognitionProvider,
    }

    @staticmethod
    def create_provider(
        provider_name: str,
        config: Dict
    ) -> BaseFaceRecognitionProvider:
        """
        Create a face recognition provider instance.

        Args:
            provider_name: Name of the provider ('local', 'aws', 'azure')
            config: Provider-specific configuration dictionary

        Returns:
            BaseFaceRecognitionProvider instance

        Raises:
            ValueError: If provider name is invalid
            ImportError: If provider dependencies are not installed
        """
        logger = logging.getLogger(__name__)

        provider_name = provider_name.lower()

        if provider_name not in FaceRecognitionFactory.PROVIDERS:
            available = [k for k, v in FaceRecognitionFactory.PROVIDERS.items() if v is not None]
            raise ValueError(
                f"Unknown provider: '{provider_name}'. "
                f"Available providers: {', '.join(available)}"
            )

        provider_class = FaceRecognitionFactory.PROVIDERS[provider_name]

        if provider_class is None:
            raise ImportError(
                f"Provider '{provider_name}' dependencies not installed. "
                f"See requirements.txt for installation instructions."
            )

        logger.info(f"Creating {provider_name} face recognition provider")

        try:
            provider = provider_class(config)

            # Validate configuration
            is_valid, error_message = provider.validate_configuration()
            if not is_valid:
                raise ValueError(f"Provider configuration invalid: {error_message}")

            return provider

        except Exception as e:
            logger.error(f"Failed to create {provider_name} provider: {e}")
            raise

    @staticmethod
    def list_available_providers() -> Dict[str, bool]:
        """
        List all providers and their availability status.

        Returns:
            Dictionary mapping provider name to availability (True/False)
        """
        return {
            name: provider is not None
            for name, provider in FaceRecognitionFactory.PROVIDERS.items()
        }


# Convenience function
def get_provider(provider_name: str, config: Dict) -> BaseFaceRecognitionProvider:
    """
    Convenience function to create a provider.

    Args:
        provider_name: Name of the provider
        config: Provider configuration

    Returns:
        BaseFaceRecognitionProvider instance
    """
    return FaceRecognitionFactory.create_provider(provider_name, config)
