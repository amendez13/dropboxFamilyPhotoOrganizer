"""Tests for lazy imports in scripts.auth."""

import pytest

from scripts import auth as auth_module


def test_auth_getattr_dropbox_client_factory() -> None:
    factory = getattr(auth_module, "DropboxClientFactory")
    assert factory.__name__ == "DropboxClientFactory"


def test_auth_getattr_oauth_manager() -> None:
    oauth_manager = getattr(auth_module, "OAuthManager")
    assert oauth_manager.__name__ == "OAuthManager"


def test_auth_getattr_token_storage() -> None:
    token_storage = getattr(auth_module, "TokenStorage")
    assert token_storage.__name__ == "TokenStorage"


def test_auth_getattr_unknown_attribute() -> None:
    with pytest.raises(AttributeError):
        getattr(auth_module, "DoesNotExist")
