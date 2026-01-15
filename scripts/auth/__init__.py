"""
Authentication module for Dropbox Photo Organizer.
Provides OAuth 2.0 authentication and token management.
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from scripts.auth.client_factory import DropboxClientFactory
    from scripts.auth.oauth_manager import OAuthManager, TokenStorage

__all__ = ["OAuthManager", "TokenStorage", "DropboxClientFactory"]


def __getattr__(name: str) -> object:
    if name == "DropboxClientFactory":
        from scripts.auth.client_factory import DropboxClientFactory

        return DropboxClientFactory
    if name in {"OAuthManager", "TokenStorage"}:
        from scripts.auth.oauth_manager import OAuthManager, TokenStorage

        return {"OAuthManager": OAuthManager, "TokenStorage": TokenStorage}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
