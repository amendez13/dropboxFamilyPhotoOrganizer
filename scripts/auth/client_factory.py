"""
Factory for creating DropboxClient instances with proper authentication.
Handles both OAuth 2.0 and legacy access token authentication.
"""

import logging
from typing import Optional

from scripts.auth.oauth_manager import TokenStorage
from scripts.dropbox_client import DropboxClient


class DropboxClientFactory:
    """Factory for creating authenticated DropboxClient instances."""

    def __init__(self, config: dict):
        """
        Initialize factory with configuration.

        Args:
            config: Configuration dictionary from config.yaml
        """
        self.config = config
        self.logger = logging.getLogger(__name__)

    def create_client(self) -> DropboxClient:
        """
        Create an authenticated DropboxClient instance.

        Returns:
            Configured DropboxClient instance

        Raises:
            ValueError: If neither OAuth nor legacy credentials are provided
        """
        dropbox_config = self.config.get("dropbox", {})

        # Try OAuth 2.0 first (recommended)
        app_key = dropbox_config.get("app_key")
        app_secret = dropbox_config.get("app_secret")
        token_storage_mode = dropbox_config.get("token_storage", "keyring")

        if app_key:
            self.logger.info("Using OAuth 2.0 authentication")
            refresh_token = self._get_refresh_token(dropbox_config, token_storage_mode)

            if refresh_token:
                # Create token refresh callback
                def token_refresh_callback(access_token: str, expires_at: str):
                    """Callback to save refreshed tokens."""
                    self.logger.info("Access token refreshed")
                    # Could save to keyring here if needed for manual access

                return DropboxClient(
                    refresh_token=refresh_token,
                    app_key=app_key,
                    app_secret=app_secret,
                    token_refresh_callback=token_refresh_callback,
                )
            else:
                self.logger.warning("OAuth credentials configured but no refresh token found")
                self.logger.warning("Please run: python scripts/authorize_dropbox.py")

        # Fallback to legacy access token
        access_token = dropbox_config.get("access_token")
        if access_token:
            self.logger.warning("Using legacy access token authentication")
            self.logger.warning(
                "Consider migrating to OAuth 2.0 for automatic token refresh"
            )
            return DropboxClient(access_token=access_token)

        # No valid credentials found
        raise ValueError(
            "No valid Dropbox credentials found.\n"
            "Please either:\n"
            "1. Run 'python scripts/authorize_dropbox.py' for OAuth 2.0 (recommended)\n"
            "2. Add 'access_token' to config/config.yaml (legacy, not recommended)"
        )

    def _get_refresh_token(
        self, dropbox_config: dict, token_storage_mode: str
    ) -> Optional[str]:
        """
        Get refresh token from configured storage.

        Args:
            dropbox_config: Dropbox configuration section
            token_storage_mode: Storage mode ('keyring' or 'config')

        Returns:
            Refresh token if found, None otherwise
        """
        # Check config file first (for token_storage: config mode)
        config_refresh_token = dropbox_config.get("refresh_token")

        if token_storage_mode == "config":
            if config_refresh_token:
                self.logger.info("Using refresh token from config file")
                return config_refresh_token
            else:
                self.logger.warning("token_storage set to 'config' but no refresh_token in config")
                return None

        # Try keyring (default and recommended)
        token_storage = TokenStorage()

        if token_storage.keyring_available:
            tokens = token_storage.load_tokens()
            if tokens and "refresh_token" in tokens:
                self.logger.info("Using refresh token from system keyring")
                return tokens["refresh_token"]
            else:
                self.logger.debug("No tokens found in keyring")
        else:
            self.logger.warning("Keyring not available, install with: pip install keyring")

        # Fallback to config file if keyring fails
        if config_refresh_token:
            self.logger.info("Using refresh token from config file (keyring fallback)")
            return config_refresh_token

        return None
