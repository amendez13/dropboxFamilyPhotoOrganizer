"""
Dropbox API client for photo organization.
Handles authentication, file listing, downloading, and moving files.
Supports both legacy access tokens and OAuth 2.0 with automatic token refresh.
"""

import logging
import os
from typing import Generator, List, Optional

import dropbox
from dropbox.exceptions import ApiError, AuthError
from dropbox.files import FileMetadata

from scripts.auth.constants import DROPBOX_ACCESS_TOKEN_EXPIRY_SECONDS


class DropboxClient:
    """Client for interacting with Dropbox API."""

    def __init__(
        self,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        app_key: Optional[str] = None,
        app_secret: Optional[str] = None,
        token_refresh_callback: Optional[callable] = None,
    ):
        """
        Initialize Dropbox client.

        Supports two authentication modes:
        1. Legacy: Direct access token (will expire, no auto-refresh)
        2. OAuth 2.0: Refresh token with automatic token refresh

        Args:
            access_token: Direct access token (legacy mode)
            refresh_token: OAuth 2.0 refresh token (recommended)
            app_key: Dropbox app key (required for OAuth mode)
            app_secret: Dropbox app secret (optional, for additional security)
            token_refresh_callback: Function to call when token is refreshed.
                                   Should accept (access_token, expires_at) as args.
                                   Note: Only called during verify_connection(), not
                                   during normal API operations.

        Raises:
            ValueError: If neither access_token nor refresh_token is provided
        """
        self.logger = logging.getLogger(__name__)

        # Validate authentication parameters
        if not access_token and not refresh_token:
            raise ValueError("Either access_token or refresh_token must be provided")

        if refresh_token and not app_key:
            raise ValueError("app_key is required when using refresh_token")

        self.app_key = app_key
        self.app_secret = app_secret
        self.token_refresh_callback = token_refresh_callback

        # Initialize Dropbox client
        if refresh_token:
            # OAuth 2.0 mode with automatic token refresh
            self.logger.info("Initializing Dropbox client with OAuth 2.0 refresh token")
            self.dbx = dropbox.Dropbox(
                oauth2_refresh_token=refresh_token,
                app_key=app_key,
                app_secret=app_secret,
            )
            self.auth_mode = "oauth"
            self.refresh_token = refresh_token
            self.access_token = None  # Will be set after first API call
        else:
            # Legacy mode with direct access token
            self.logger.info("Initializing Dropbox client with legacy access token")
            self.logger.warning("Using legacy access token. Consider migrating to OAuth 2.0 with refresh tokens.")
            self.dbx = dropbox.Dropbox(access_token)
            self.auth_mode = "legacy"
            self.access_token = access_token
            self.refresh_token = None

    def get_current_access_token(self) -> Optional[str]:
        """
        Get the current access token.

        In OAuth mode, this triggers a refresh if needed and returns the new token.

        Returns:
            Current access token, or None if unavailable

        Note:
            In OAuth mode, this accesses a private SDK attribute (_oauth2_access_token).
            This is necessary because the Dropbox SDK doesn't expose the current access
            token via public API. If this breaks in future SDK versions, the method
            will gracefully return None.
        """
        if self.auth_mode == "oauth":
            # Access private SDK attribute with defensive fallback
            # The SDK doesn't provide a public API for the current access token
            try:
                return getattr(self.dbx, "_oauth2_access_token", None)
            except AttributeError:
                self.logger.warning(
                    "Unable to access SDK access token. " "This may indicate a Dropbox SDK version incompatibility."
                )
                return None
        else:
            return self.access_token

    def verify_connection(self) -> bool:
        """
        Verify the Dropbox connection and access token.

        In OAuth mode, this will automatically refresh the token if expired.

        IMPORTANT - Token Refresh Callback Limitation:
        The token_refresh_callback is only triggered during this verify_connection()
        call, not during normal API operations (list_folder, download_file, etc.).

        This is because the Dropbox SDK handles token refresh automatically and
        internally during API calls, without exposing the refreshed token. We can
        only detect and expose token changes by explicitly checking before/after
        an API call, which we do here in verify_connection().

        For most use cases, this is sufficient - call verify_connection() periodically
        or before long-running operations to ensure tokens are fresh and saved.
        The automatic refresh during normal API calls will continue to work regardless.

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            account = self.dbx.users_get_current_account()
            self.logger.info(f"Connected to Dropbox account: {account.email}")

            # If in OAuth mode and we have a callback, notify about token refresh
            if self.auth_mode == "oauth" and self.token_refresh_callback:
                current_token = self.get_current_access_token()
                if current_token and current_token != self.access_token:
                    # Token was refreshed
                    self.access_token = current_token
                    import time

                    expires_at = str(int(time.time()) + DROPBOX_ACCESS_TOKEN_EXPIRY_SECONDS)
                    self.token_refresh_callback(current_token, expires_at)

            return True
        except AuthError as e:
            self.logger.error(f"Authentication failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Connection verification failed: {e}")
            return False

    def _normalize_folder_path(self, folder_path: str) -> str:
        """Normalize folder path for Dropbox API."""
        if folder_path and not folder_path.startswith("/"):
            folder_path = "/" + folder_path
        if folder_path == "/":
            folder_path = ""
        return folder_path

    def _should_include_file(self, filename: str, extensions: Optional[List[str]]) -> bool:
        """Check if file should be included based on extension filter."""
        if not extensions:
            return True
        _, ext = os.path.splitext(filename.lower())
        return ext in [e.lower() for e in extensions]

    def list_folder_recursive(
        self, folder_path: str, extensions: Optional[List[str]] = None
    ) -> Generator[FileMetadata, None, None]:
        """
        List all files in a folder recursively.

        Args:
            folder_path: Path to the folder in Dropbox (e.g., "/Photos")
            extensions: List of file extensions to filter (e.g., [".jpg", ".png"])
                       If None, returns all files.

        Yields:
            FileMetadata objects for each file
        """
        try:
            folder_path = self._normalize_folder_path(folder_path)
            self.logger.info(f"Listing files in: {folder_path or '/'}")

            # Initial request
            result = self.dbx.files_list_folder(folder_path, recursive=True)

            # Process results and handle pagination
            while True:
                for entry in result.entries:
                    # Only yield files, not folders
                    if isinstance(entry, FileMetadata):
                        if self._should_include_file(entry.name, extensions):
                            yield entry

                # Check if there are more results
                if not result.has_more:
                    break

                # Get next batch
                result = self.dbx.files_list_folder_continue(result.cursor)

        except ApiError as e:
            self.logger.error(f"Error listing folder '{folder_path}': {e}")
            raise

    def get_file_count(self, folder_path: str, extensions: Optional[List[str]] = None) -> int:
        """
        Count files in a folder (optionally filtered by extension).

        Args:
            folder_path: Path to the folder in Dropbox
            extensions: List of file extensions to filter

        Returns:
            Number of files found
        """
        count = 0
        for _ in self.list_folder_recursive(folder_path, extensions):
            count += 1
        return count

    def download_file(self, dropbox_path: str, local_path: str) -> bool:
        """
        Download a file from Dropbox.

        Args:
            dropbox_path: Path to file in Dropbox
            local_path: Local path where file will be saved

        Returns:
            True if successful, False otherwise
        """
        try:
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(local_path), exist_ok=True)

            # Download file
            self.logger.debug(f"Downloading: {dropbox_path} -> {local_path}")
            metadata, response = self.dbx.files_download(dropbox_path)

            # Write to local file
            with open(local_path, "wb") as f:
                f.write(response.content)

            return True

        except ApiError as e:
            self.logger.error(f"Error downloading file '{dropbox_path}': {e}")
            return False

    def get_thumbnail(self, dropbox_path: str, size: str = "w256h256", format: str = "jpeg") -> Optional[bytes]:
        """
        Get a thumbnail of an image file.

        Args:
            dropbox_path: Path to image in Dropbox
            size: Thumbnail size (w32h32, w64h64, w128h128, w256h256, w480h320,
                  w640h480, w960h640, w1024h768, w2048h1536)
            format: Output format ("jpeg" or "png")

        Returns:
            Thumbnail bytes, or None if failed
        """
        try:
            from dropbox.files import ThumbnailFormat, ThumbnailSize

            # Map size string to enum
            size_map = {
                "w32h32": ThumbnailSize.w32h32,
                "w64h64": ThumbnailSize.w64h64,
                "w128h128": ThumbnailSize.w128h128,
                "w256h256": ThumbnailSize.w256h256,
                "w480h320": ThumbnailSize.w480h320,
                "w640h480": ThumbnailSize.w640h480,
                "w960h640": ThumbnailSize.w960h640,
                "w1024h768": ThumbnailSize.w1024h768,
                "w2048h1536": ThumbnailSize.w2048h1536,
            }

            # Map format string to enum
            format_map = {
                "jpeg": ThumbnailFormat.jpeg,
                "png": ThumbnailFormat.png,
            }

            size_enum = size_map.get(size, ThumbnailSize.w256h256)
            format_enum = format_map.get(format, ThumbnailFormat.jpeg)

            metadata, response = self.dbx.files_get_thumbnail(dropbox_path, format=format_enum, size=size_enum)

            return response.content

        except ApiError as e:
            self.logger.warning(f"Could not get thumbnail for '{dropbox_path}': {e}")
            return None

    def get_file_content(self, dropbox_path: str) -> Optional[bytes]:
        """
        Download the full content of a file from Dropbox.

        Args:
            dropbox_path: Path to file in Dropbox

        Returns:
            File content as bytes, or None if failed
        """
        try:
            metadata, response = self.dbx.files_download(dropbox_path)
            return response.content

        except ApiError as e:
            self.logger.warning(f"Could not download file '{dropbox_path}': {e}")
            return None

    def copy_file(self, source_path: str, dest_path: str, autorename: bool = True, allow_shared_folder: bool = False) -> bool:
        """
        Copy a file to a different location in Dropbox.

        Args:
            source_path: Current path of the file
            dest_path: Destination path
            autorename: If True, rename file if destination already exists
            allow_shared_folder: Allow copying to/from shared folders

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Copying: {source_path} -> {dest_path}")

            result = self.dbx.files_copy_v2(
                source_path, dest_path, autorename=autorename, allow_shared_folder=allow_shared_folder
            )

            self.logger.debug(f"Copied successfully: {result.metadata.name}")
            return True

        except ApiError as e:
            self.logger.error(f"Error copying file '{source_path}': {e}")
            return False

    def move_file(self, source_path: str, dest_path: str, autorename: bool = True, allow_shared_folder: bool = False) -> bool:
        """
        Move a file to a different location in Dropbox.

        Args:
            source_path: Current path of the file
            dest_path: Destination path
            autorename: If True, rename file if destination already exists
            allow_shared_folder: Allow moving to/from shared folders

        Returns:
            True if successful, False otherwise
        """
        try:
            self.logger.info(f"Moving: {source_path} -> {dest_path}")

            result = self.dbx.files_move_v2(
                source_path, dest_path, autorename=autorename, allow_shared_folder=allow_shared_folder
            )

            self.logger.debug(f"Moved successfully: {result.metadata.name}")
            return True

        except ApiError as e:
            self.logger.error(f"Error moving file '{source_path}': {e}")
            return False

    def create_folder(self, folder_path: str) -> bool:
        """
        Create a folder in Dropbox (if it doesn't exist).

        Args:
            folder_path: Path to the folder to create

        Returns:
            True if successful or already exists, False otherwise
        """
        try:
            self.dbx.files_create_folder_v2(folder_path)
            self.logger.info(f"Created folder: {folder_path}")
            return True
        except ApiError as e:
            # Check if folder already exists
            if e.error.is_path() and e.error.get_path().is_conflict():
                self.logger.debug(f"Folder already exists: {folder_path}")
                return True
            else:
                self.logger.error(f"Error creating folder '{folder_path}': {e}")
                return False

    def get_file_metadata(self, file_path: str) -> Optional[FileMetadata]:
        """
        Get metadata for a file.

        Args:
            file_path: Path to the file in Dropbox

        Returns:
            FileMetadata object, or None if failed
        """
        try:
            metadata = self.dbx.files_get_metadata(file_path)
            if isinstance(metadata, FileMetadata):
                return metadata
            return None
        except ApiError as e:
            self.logger.error(f"Error getting metadata for '{file_path}': {e}")
            return None
