"""Unit tests for OAuth 2.0 authentication functionality."""

import json
import sys
import time
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from scripts.auth.client_factory import DropboxClientFactory  # noqa: E402
from scripts.auth.oauth_manager import OAuthManager, TokenStorage  # noqa: E402


class TestOAuthManager:
    """Test cases for OAuthManager class."""

    def test_init(self):
        """Test OAuthManager initialization."""
        manager = OAuthManager(app_key="test_key", app_secret="test_secret")
        assert manager.app_key == "test_key"
        assert manager.app_secret == "test_secret"
        assert manager.logger is not None

    @patch("scripts.auth.oauth_manager.DropboxOAuth2FlowNoRedirect")
    def test_start_authorization_flow_success(self, mock_flow_class):
        """Test successful authorization flow start."""
        mock_flow = Mock()
        mock_flow.start.return_value = "https://www.dropbox.com/oauth2/authorize?..."
        mock_flow_class.return_value = mock_flow

        manager = OAuthManager(app_key="test_key", app_secret="test_secret")
        url = manager.start_authorization_flow()

        assert url == "https://www.dropbox.com/oauth2/authorize?..."
        mock_flow_class.assert_called_once_with(
            consumer_key="test_key",
            consumer_secret="test_secret",
            use_pkce=True,
            token_access_type="offline",
        )
        mock_flow.start.assert_called_once()
        assert hasattr(manager, "_auth_flow")

    @patch("scripts.auth.oauth_manager.DropboxOAuth2FlowNoRedirect")
    def test_start_authorization_flow_failure(self, mock_flow_class):
        """Test authorization flow start failure."""
        mock_flow_class.side_effect = Exception("Network error")

        manager = OAuthManager(app_key="test_key")
        with pytest.raises(Exception, match="Network error"):
            manager.start_authorization_flow()

    @patch("scripts.auth.oauth_manager.DropboxOAuth2FlowNoRedirect")
    def test_complete_authorization_flow_success(self, mock_flow_class):
        """Test successful authorization flow completion."""
        mock_oauth_result = Mock()
        mock_oauth_result.access_token = "test_access_token"
        mock_oauth_result.refresh_token = "test_refresh_token"
        mock_oauth_result.account_id = "test_account_id"

        mock_flow = Mock()
        mock_flow.finish.return_value = mock_oauth_result
        mock_flow_class.return_value = mock_flow

        manager = OAuthManager(app_key="test_key")
        manager.start_authorization_flow()

        with patch("time.time", return_value=1000000):
            tokens = manager.complete_authorization_flow("test_auth_code")

        assert tokens["access_token"] == "test_access_token"
        assert tokens["refresh_token"] == "test_refresh_token"
        assert tokens["account_id"] == "test_account_id"
        assert tokens["expires_at"] == str(1000000 + 14400)  # 4 hours = 14400 seconds
        mock_flow.finish.assert_called_once_with("test_auth_code")
        assert not hasattr(manager, "_auth_flow")  # Should be cleaned up

    def test_complete_authorization_flow_without_start(self):
        """Test completing authorization flow without starting it first."""
        manager = OAuthManager(app_key="test_key")
        with pytest.raises(ValueError, match="Authorization flow not started"):
            manager.complete_authorization_flow("test_auth_code")

    def test_refresh_access_token_success(self):
        """Test successful access token refresh."""
        with patch("dropbox.Dropbox") as mock_dropbox_class:
            mock_dbx = Mock()
            mock_dbx._oauth2_access_token = "new_access_token"
            mock_dropbox_class.return_value = mock_dbx

            manager = OAuthManager(app_key="test_key", app_secret="test_secret")

            with patch("time.time", return_value=2000000):
                result = manager.refresh_access_token("test_refresh_token")

            assert result["access_token"] == "new_access_token"
            assert result["expires_at"] == str(2000000 + 14400)
            mock_dropbox_class.assert_called_once_with(
                oauth2_refresh_token="test_refresh_token",
                app_key="test_key",
                app_secret="test_secret",
            )
            mock_dbx.users_get_current_account.assert_called_once()

    def test_refresh_access_token_no_token_attribute(self):
        """Test refresh when SDK doesn't have _oauth2_access_token attribute."""
        with patch("dropbox.Dropbox") as mock_dropbox_class:
            mock_dbx = Mock()
            # Simulate missing attribute
            mock_dbx.configure_mock(**{"_oauth2_access_token": None})
            mock_dropbox_class.return_value = mock_dbx

            manager = OAuthManager(app_key="test_key")
            with pytest.raises(RuntimeError, match="Unable to retrieve access token"):
                manager.refresh_access_token("test_refresh_token")

    def test_refresh_access_token_failure(self):
        """Test access token refresh failure."""
        with patch("dropbox.Dropbox") as mock_dropbox_class:
            mock_dropbox_class.side_effect = Exception("API error")

            manager = OAuthManager(app_key="test_key")
            with pytest.raises(Exception, match="API error"):
                manager.refresh_access_token("test_refresh_token")

    def test_is_token_expired_valid_token(self):
        """Test token expiry check with valid token."""
        manager = OAuthManager(app_key="test_key")
        future_time = int(time.time()) + 1000  # Expires in ~16 minutes
        assert not manager.is_token_expired(str(future_time))

    def test_is_token_expired_expired_token(self):
        """Test token expiry check with expired token."""
        manager = OAuthManager(app_key="test_key")
        past_time = int(time.time()) - 1000  # Expired 16 minutes ago
        assert manager.is_token_expired(str(past_time))

    def test_is_token_expired_buffer_zone(self):
        """Test token expiry check within 5-minute buffer."""
        manager = OAuthManager(app_key="test_key")
        # Token expires in 4 minutes (within 5-minute buffer)
        soon_time = int(time.time()) + 240
        assert manager.is_token_expired(str(soon_time))

    def test_is_token_expired_invalid_value(self):
        """Test token expiry check with invalid expires_at value."""
        manager = OAuthManager(app_key="test_key")
        assert manager.is_token_expired("invalid")
        assert manager.is_token_expired(None)


class TestTokenStorage:
    """Test cases for TokenStorage class."""

    def test_init_with_keyring(self):
        """Test TokenStorage initialization with keyring available."""
        # Create a mock keyring module
        mock_keyring_module = Mock()

        # Patch the import within the __init__ method
        with patch.dict("sys.modules", {"keyring": mock_keyring_module}):
            storage = TokenStorage(service_name="test-service")
            assert storage.service_name == "test-service"
            assert storage.keyring_available is True
            assert storage.keyring is mock_keyring_module

    def test_init_without_keyring(self):
        """Test TokenStorage initialization without keyring."""
        # Simulate keyring import failure
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "keyring":
                raise ImportError("No module named 'keyring'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            storage = TokenStorage(service_name="test-service")
            assert storage.keyring_available is False
            assert storage.keyring is None

    def test_save_tokens_success(self):
        """Test successful token saving to keyring."""
        mock_keyring_module = Mock()

        with patch.dict("sys.modules", {"keyring": mock_keyring_module}):
            storage = TokenStorage()
            tokens = {"access_token": "test_access", "refresh_token": "test_refresh", "expires_at": "123456"}

            result = storage.save_tokens(tokens, username="testuser")

            assert result is True
            mock_keyring_module.set_password.assert_called_once()
            args = mock_keyring_module.set_password.call_args
            assert args[0][0] == "dropbox-photo-organizer"
            assert args[0][1] == "testuser"
            assert "test_access" in args[0][2]

    def test_save_tokens_without_keyring(self):
        """Test token saving when keyring is not available."""
        # Force ImportError
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "keyring":
                raise ImportError("No module named 'keyring'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            storage = TokenStorage()
            assert storage.keyring_available is False

            tokens = {"access_token": "test"}
            result = storage.save_tokens(tokens)

            assert result is False

    def test_save_tokens_failure(self):
        """Test token saving failure."""
        mock_keyring_module = Mock()
        mock_keyring_module.set_password.side_effect = Exception("Keyring error")

        with patch.dict("sys.modules", {"keyring": mock_keyring_module}):
            storage = TokenStorage()
            tokens = {"access_token": "test"}
            result = storage.save_tokens(tokens)

            assert result is False

    def test_load_tokens_success(self):
        """Test successful token loading from keyring."""
        tokens = {"access_token": "test_access", "refresh_token": "test_refresh", "expires_at": "123456"}
        mock_keyring_module = Mock()
        mock_keyring_module.get_password.return_value = json.dumps(tokens)

        with patch.dict("sys.modules", {"keyring": mock_keyring_module}):
            storage = TokenStorage()
            loaded_tokens = storage.load_tokens(username="testuser")

            assert loaded_tokens == tokens
            mock_keyring_module.get_password.assert_called_once_with("dropbox-photo-organizer", "testuser")

    def test_load_tokens_not_found(self):
        """Test loading tokens when none exist."""
        mock_keyring_module = Mock()
        mock_keyring_module.get_password.return_value = None

        with patch.dict("sys.modules", {"keyring": mock_keyring_module}):
            storage = TokenStorage()
            loaded_tokens = storage.load_tokens()

            assert loaded_tokens is None

    def test_load_tokens_without_keyring(self):
        """Test loading tokens when keyring is not available."""
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "keyring":
                raise ImportError("No module named 'keyring'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            storage = TokenStorage()
            loaded_tokens = storage.load_tokens()

            assert loaded_tokens is None

    def test_load_tokens_failure(self):
        """Test loading tokens failure due to an exception."""
        mock_keyring_module = Mock()
        mock_keyring_module.get_password.side_effect = Exception("Keyring read error")

        with patch.dict("sys.modules", {"keyring": mock_keyring_module}):
            storage = TokenStorage()
            loaded_tokens = storage.load_tokens(username="testuser")

            assert loaded_tokens is None
            mock_keyring_module.get_password.assert_called_once_with("dropbox-photo-organizer", "testuser")

    def test_delete_tokens_success(self):
        """Test successful token deletion."""
        mock_keyring_module = Mock()

        with patch.dict("sys.modules", {"keyring": mock_keyring_module}):
            storage = TokenStorage()
            result = storage.delete_tokens(username="testuser")

            assert result is True
            mock_keyring_module.delete_password.assert_called_once_with("dropbox-photo-organizer", "testuser")

    def test_delete_tokens_without_keyring(self):
        """Test token deletion when keyring is not available."""
        import builtins

        original_import = builtins.__import__

        def mock_import(name, *args, **kwargs):
            if name == "keyring":
                raise ImportError("No module named 'keyring'")
            return original_import(name, *args, **kwargs)

        with patch("builtins.__import__", side_effect=mock_import):
            storage = TokenStorage()
            result = storage.delete_tokens()

            assert result is False

    def test_delete_tokens_failure(self):
        """Test token deletion failure due to an exception."""
        mock_keyring_module = Mock()
        mock_keyring_module.delete_password.side_effect = Exception("Deletion error")

        with patch.dict("sys.modules", {"keyring": mock_keyring_module}):
            storage = TokenStorage()
            result = storage.delete_tokens(username="testuser")

            assert result is False
            mock_keyring_module.delete_password.assert_called_once_with("dropbox-photo-organizer", "testuser")


class TestDropboxClientFactory:
    """Test cases for DropboxClientFactory class."""

    def test_init(self):
        """Test DropboxClientFactory initialization."""
        config = {"dropbox": {}}
        factory = DropboxClientFactory(config)
        assert factory.config == config
        assert factory.logger is not None

    @patch("scripts.auth.client_factory.DropboxClient")
    @patch("scripts.auth.client_factory.TokenStorage")
    def test_create_client_with_oauth_keyring(self, mock_storage_class, mock_client_class):
        """Test creating client with OAuth using keyring storage."""
        mock_storage = Mock()
        mock_storage.keyring_available = True
        mock_storage.load_tokens.return_value = {
            "refresh_token": "test_refresh_token",
            "access_token": "test_access_token",
            "expires_at": "123456",
        }
        mock_storage_class.return_value = mock_storage

        config = {"dropbox": {"app_key": "test_app_key", "app_secret": "test_app_secret", "token_storage": "keyring"}}

        factory = DropboxClientFactory(config)
        factory.create_client()

        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args[1]
        assert call_kwargs["refresh_token"] == "test_refresh_token"
        assert call_kwargs["app_key"] == "test_app_key"
        assert call_kwargs["app_secret"] == "test_app_secret"
        assert call_kwargs["token_refresh_callback"] is not None

    @patch("scripts.auth.client_factory.DropboxClient")
    def test_create_client_with_oauth_config_storage(self, mock_client_class):
        """Test creating client with OAuth using config file storage."""
        config = {"dropbox": {"app_key": "test_app_key", "refresh_token": "test_refresh_token", "token_storage": "config"}}

        factory = DropboxClientFactory(config)
        factory.create_client()

        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args[1]
        assert call_kwargs["refresh_token"] == "test_refresh_token"
        assert call_kwargs["app_key"] == "test_app_key"

    @patch("scripts.auth.client_factory.DropboxClient")
    def test_create_client_with_legacy_token(self, mock_client_class):
        """Test creating client with legacy access token."""
        config = {"dropbox": {"access_token": "legacy_access_token"}}

        factory = DropboxClientFactory(config)
        factory.create_client()

        mock_client_class.assert_called_once()
        call_kwargs = mock_client_class.call_args[1]
        assert call_kwargs["access_token"] == "legacy_access_token"

    @patch("scripts.auth.client_factory.TokenStorage")
    def test_create_client_no_credentials(self, mock_storage_class):
        """Test creating client with no credentials."""
        mock_storage = Mock()
        mock_storage.keyring_available = False
        mock_storage_class.return_value = mock_storage

        config = {"dropbox": {}}

        factory = DropboxClientFactory(config)
        with pytest.raises(ValueError, match="No valid Dropbox credentials found"):
            factory.create_client()

    @patch("scripts.auth.client_factory.TokenStorage")
    def test_create_client_oauth_no_refresh_token(self, mock_storage_class):
        """Test creating client with OAuth configured but no refresh token."""
        mock_storage = Mock()
        mock_storage.keyring_available = True
        mock_storage.load_tokens.return_value = None
        mock_storage_class.return_value = mock_storage

        config = {"dropbox": {"app_key": "test_app_key"}}

        factory = DropboxClientFactory(config)
        with pytest.raises(ValueError, match="No valid Dropbox credentials found"):
            factory.create_client()

    def test_get_refresh_token_from_config(self):
        """Test getting refresh token from config file."""
        config = {"dropbox": {"refresh_token": "config_refresh_token", "token_storage": "config"}}

        factory = DropboxClientFactory(config)
        token = factory._get_refresh_token(config["dropbox"], "config")

        assert token == "config_refresh_token"

    @patch("scripts.auth.client_factory.TokenStorage")
    def test_get_refresh_token_from_keyring(self, mock_storage_class):
        """Test getting refresh token from keyring."""
        mock_storage = Mock()
        mock_storage.keyring_available = True
        mock_storage.load_tokens.return_value = {"refresh_token": "keyring_refresh_token"}
        mock_storage_class.return_value = mock_storage

        config = {"dropbox": {}}

        factory = DropboxClientFactory(config)
        token = factory._get_refresh_token(config["dropbox"], "keyring")

        assert token == "keyring_refresh_token"

    @patch("scripts.auth.client_factory.TokenStorage")
    def test_get_refresh_token_keyring_fallback_to_config(self, mock_storage_class):
        """Test fallback to config when keyring fails."""
        mock_storage = Mock()
        mock_storage.keyring_available = True
        mock_storage.load_tokens.return_value = None
        mock_storage_class.return_value = mock_storage

        config = {"dropbox": {"refresh_token": "config_fallback_token"}}

        factory = DropboxClientFactory(config)
        token = factory._get_refresh_token(config["dropbox"], "keyring")

        assert token == "config_fallback_token"

    @patch("scripts.auth.client_factory.DropboxClient")
    @patch("scripts.auth.client_factory.TokenStorage")
    def test_create_client_with_invalid_refresh_token_empty(self, mock_storage_class, mock_client_class):
        """Test creating client with empty refresh token."""
        mock_storage = Mock()
        mock_storage.keyring_available = True
        mock_storage.load_tokens.return_value = {
            "refresh_token": "   ",  # Whitespace only
            "access_token": "test_access_token",
            "expires_at": "123456",
        }
        mock_storage_class.return_value = mock_storage

        config = {"dropbox": {"app_key": "test_app_key", "token_storage": "keyring"}}

        factory = DropboxClientFactory(config)
        with pytest.raises(ValueError, match="Invalid refresh token format"):
            factory.create_client()

    @patch("scripts.auth.client_factory.DropboxClient")
    def test_create_client_with_invalid_refresh_token_not_string(self, mock_client_class):
        """Test creating client with non-string refresh token."""
        config = {"dropbox": {"app_key": "test_app_key", "refresh_token": 12345, "token_storage": "config"}}  # Not a string

        factory = DropboxClientFactory(config)
        with pytest.raises(ValueError, match="Invalid refresh token format"):
            factory.create_client()

    @patch("scripts.auth.client_factory.DropboxClient")
    @patch("scripts.auth.client_factory.TokenStorage")
    def test_token_refresh_callback_execution(self, mock_storage_class, mock_client_class):
        """Test that token_refresh_callback is properly created and can be executed."""
        mock_storage = Mock()
        mock_storage.keyring_available = True
        mock_storage.load_tokens.return_value = {
            "refresh_token": "test_refresh_token",
            "access_token": "test_access_token",
            "expires_at": "123456",
        }
        mock_storage_class.return_value = mock_storage

        config = {"dropbox": {"app_key": "test_app_key", "app_secret": "test_app_secret", "token_storage": "keyring"}}

        factory = DropboxClientFactory(config)
        factory.create_client()

        # Get the callback that was passed to DropboxClient
        call_kwargs = mock_client_class.call_args[1]
        callback = call_kwargs["token_refresh_callback"]

        # Execute the callback to cover lines 57-58
        callback("new_access_token", "new_expires_at")

    def test_get_refresh_token_config_mode_no_token(self):
        """Test getting refresh token from config mode when no token exists."""
        config = {"dropbox": {"token_storage": "config"}}  # No refresh_token

        factory = DropboxClientFactory(config)
        token = factory._get_refresh_token(config["dropbox"], "config")

        assert token is None

    @patch("scripts.auth.client_factory.TokenStorage")
    def test_get_refresh_token_keyring_unavailable(self, mock_storage_class):
        """Test getting refresh token when keyring is not available."""
        mock_storage = Mock()
        mock_storage.keyring_available = False
        mock_storage_class.return_value = mock_storage

        config = {"dropbox": {}}  # No config fallback

        factory = DropboxClientFactory(config)
        token = factory._get_refresh_token(config["dropbox"], "keyring")

        assert token is None

    @patch("scripts.auth.client_factory.TokenStorage")
    def test_get_refresh_token_keyring_unavailable_with_invalid_config_fallback(self, mock_storage_class):
        """Test fallback to config with invalid type when keyring is unavailable."""
        mock_storage = Mock()
        mock_storage.keyring_available = False
        mock_storage_class.return_value = mock_storage

        config = {"dropbox": {"refresh_token": 12345}}  # Invalid type in fallback

        factory = DropboxClientFactory(config)
        with pytest.raises(ValueError, match="Invalid refresh token format"):
            factory._get_refresh_token(config["dropbox"], "keyring")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
