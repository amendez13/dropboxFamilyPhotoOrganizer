"""
Dropbox API client for photo organization.
Handles authentication, file listing, downloading, and moving files.
"""

import logging
import os
from typing import Dict, Generator, List, Optional

import dropbox
from dropbox.exceptions import ApiError, AuthError
from dropbox.files import FileMetadata, FolderMetadata, WriteMode


class DropboxClient:
    """Client for interacting with Dropbox API."""

    def __init__(self, access_token: str):
        """
        Initialize Dropbox client.

        Args:
            access_token: Dropbox API access token
        """
        self.access_token = access_token
        self.dbx = dropbox.Dropbox(access_token)
        self.logger = logging.getLogger(__name__)

    def verify_connection(self) -> bool:
        """
        Verify the Dropbox connection and access token.

        Returns:
            True if connection is valid, False otherwise
        """
        try:
            account = self.dbx.users_get_current_account()
            self.logger.info(f"Connected to Dropbox account: {account.email}")
            return True
        except AuthError as e:
            self.logger.error(f"Authentication failed: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Connection verification failed: {e}")
            return False

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
            # Normalize folder path
            if folder_path and not folder_path.startswith("/"):
                folder_path = "/" + folder_path
            if folder_path == "/":
                folder_path = ""

            self.logger.info(f"Listing files in: {folder_path or '/'}")

            # Initial request
            result = self.dbx.files_list_folder(folder_path, recursive=True)

            # Process results and handle pagination
            while True:
                for entry in result.entries:
                    # Only yield files, not folders
                    if isinstance(entry, FileMetadata):
                        # Filter by extension if specified
                        if extensions:
                            _, ext = os.path.splitext(entry.name.lower())
                            if ext in [e.lower() for e in extensions]:
                                yield entry
                        else:
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
