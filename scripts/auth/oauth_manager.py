"""
OAuth 2.0 authentication manager for Dropbox.
Handles authorization flow with PKCE and refresh token management.
"""

import json
import logging
import time
from typing import Dict, Optional, Tuple

from dropbox import DropboxOAuth2FlowNoRedirect


class OAuthManager:
    """Manages OAuth 2.0 authentication and token refresh for Dropbox."""

    def __init__(self, app_key: str, app_secret: Optional[str] = None):
        """
        Initialize OAuth manager.

        Args:
            app_key: Dropbox app key
            app_secret: Dropbox app secret (optional, recommended for additional security)
        """
        self.app_key = app_key
        self.app_secret = app_secret
        self.logger = logging.getLogger(__name__)

    def start_authorization_flow(self) -> str:
        """
        Start the OAuth 2.0 authorization flow.

        Returns:
            Authorization URL for the user to visit
        """
        try:
            auth_flow = DropboxOAuth2FlowNoRedirect(
                consumer_key=self.app_key,
                consumer_secret=self.app_secret,
                use_pkce=True,  # Use PKCE for enhanced security
                token_access_type="offline",  # Request refresh token
            )

            authorize_url = auth_flow.start()
            self.logger.info("Authorization flow started")

            # Store auth flow state for completion
            # Note: In production, this should be persisted securely
            self._auth_flow = auth_flow

            return authorize_url

        except Exception as e:
            self.logger.error(f"Failed to start authorization flow: {e}")
            raise

    def complete_authorization_flow(self, auth_code: str) -> Dict[str, str]:
        """
        Complete the OAuth 2.0 authorization flow.

        Args:
            auth_code: Authorization code from user

        Returns:
            Dictionary containing:
                - access_token: Short-lived access token
                - refresh_token: Long-lived refresh token
                - expires_at: Unix timestamp when access token expires
                - account_id: Dropbox account ID
        """
        try:
            if not hasattr(self, "_auth_flow"):
                raise ValueError("Authorization flow not started. Call start_authorization_flow() first.")

            oauth_result = self._auth_flow.finish(auth_code)

            # Extract token information
            # Note: Dropbox access tokens typically expire after 4 hours (14400 seconds)
            # The OAuth result doesn't include expires_in, so we use the default
            tokens = {
                "access_token": oauth_result.access_token,
                "refresh_token": oauth_result.refresh_token,
                "expires_at": str(int(time.time()) + 14400),  # 4 hours default
                "account_id": oauth_result.account_id,
            }

            self.logger.info(f"Authorization successful for account: {oauth_result.account_id}")

            # Clean up auth flow state
            delattr(self, "_auth_flow")

            return tokens

        except Exception as e:
            self.logger.error(f"Failed to complete authorization flow: {e}")
            raise

    def refresh_access_token(self, refresh_token: str) -> Dict[str, str]:
        """
        Refresh the access token using a refresh token.

        Args:
            refresh_token: Long-lived refresh token

        Returns:
            Dictionary containing:
                - access_token: New short-lived access token
                - expires_at: Unix timestamp when new access token expires
        """
        try:
            from dropbox import Dropbox

            # Create a Dropbox instance with app credentials
            dbx = Dropbox(
                oauth2_refresh_token=refresh_token,
                app_key=self.app_key,
                app_secret=self.app_secret,
            )

            # Trigger token refresh by making an API call
            # The SDK will automatically refresh the token if needed
            dbx.users_get_current_account()

            # Get the refreshed access token
            # Note: The SDK handles refresh internally, but we need to expose the new token
            access_token = dbx._oauth2_access_token

            # Calculate new expiry (Dropbox access tokens typically last 4 hours)
            expires_at = str(int(time.time()) + 14400)  # 4 hours = 14400 seconds

            self.logger.info("Access token refreshed successfully")

            return {
                "access_token": access_token,
                "expires_at": expires_at,
            }

        except Exception as e:
            self.logger.error(f"Failed to refresh access token: {e}")
            raise

    def is_token_expired(self, expires_at: str) -> bool:
        """
        Check if an access token is expired or will expire soon.

        Args:
            expires_at: Unix timestamp when token expires

        Returns:
            True if token is expired or will expire within 5 minutes
        """
        try:
            expiry_time = int(expires_at)
            current_time = int(time.time())

            # Consider token expired if it expires within 5 minutes
            buffer_seconds = 300  # 5 minutes
            return (expiry_time - current_time) <= buffer_seconds

        except (ValueError, TypeError):
            self.logger.warning(f"Invalid expires_at value: {expires_at}")
            return True  # Treat as expired if we can't parse it


class TokenStorage:
    """Handles secure storage and retrieval of OAuth tokens."""

    def __init__(self, service_name: str = "dropbox-photo-organizer"):
        """
        Initialize token storage.

        Args:
            service_name: Service name for keyring storage
        """
        self.service_name = service_name
        self.logger = logging.getLogger(__name__)

        # Try to import keyring, but don't fail if not available
        try:
            import keyring

            self.keyring = keyring
            self.keyring_available = True
            self.logger.debug("Keyring available for secure token storage")
        except ImportError:
            self.keyring = None
            self.keyring_available = False
            self.logger.warning(
                "Keyring not available. Tokens will be stored in config file. "
                "Install keyring package for secure storage: pip install keyring"
            )

    def save_tokens(self, tokens: Dict[str, str], username: str = "default") -> bool:
        """
        Save OAuth tokens securely.

        Args:
            tokens: Dictionary containing access_token, refresh_token, expires_at
            username: Username for keyring (default: "default")

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.keyring_available:
                # Store tokens in system keyring
                token_data = json.dumps(tokens)
                self.keyring.set_password(self.service_name, username, token_data)
                self.logger.info(f"Tokens saved securely for user: {username}")
                return True
            else:
                # Fallback: Warn user about insecure storage
                self.logger.warning(
                    "Tokens cannot be saved securely without keyring. " "Please manually add tokens to config file."
                )
                return False

        except Exception as e:
            self.logger.error(f"Failed to save tokens: {e}")
            return False

    def load_tokens(self, username: str = "default") -> Optional[Dict[str, str]]:
        """
        Load OAuth tokens from secure storage.

        Args:
            username: Username for keyring (default: "default")

        Returns:
            Dictionary containing tokens, or None if not found
        """
        try:
            if self.keyring_available:
                token_data = self.keyring.get_password(self.service_name, username)
                if token_data:
                    tokens = json.loads(token_data)
                    self.logger.debug(f"Tokens loaded for user: {username}")
                    return tokens
                else:
                    self.logger.debug(f"No tokens found for user: {username}")
                    return None
            else:
                self.logger.warning("Keyring not available. Cannot load tokens from secure storage.")
                return None

        except Exception as e:
            self.logger.error(f"Failed to load tokens: {e}")
            return None

    def delete_tokens(self, username: str = "default") -> bool:
        """
        Delete OAuth tokens from secure storage.

        Args:
            username: Username for keyring (default: "default")

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.keyring_available:
                self.keyring.delete_password(self.service_name, username)
                self.logger.info(f"Tokens deleted for user: {username}")
                return True
            else:
                self.logger.warning("Keyring not available. Cannot delete tokens.")
                return False

        except Exception as e:
            self.logger.error(f"Failed to delete tokens: {e}")
            return False
