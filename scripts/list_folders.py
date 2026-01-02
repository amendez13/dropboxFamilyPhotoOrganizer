"""
Quick script to list top-level folders in your Dropbox to help find the correct path.
"""

import os
import sys

import yaml

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.dropbox_client import DropboxClient  # noqa: E402

# Load config
with open("config/config.yaml", "r") as f:
    config = yaml.safe_load(f)

client = DropboxClient(config["dropbox"]["access_token"])

print("Listing top-level folders in your Dropbox:\n")
print("=" * 60)

try:
    result = client.dbx.files_list_folder("")

    folders = []
    files = []

    for entry in result.entries:
        if hasattr(entry, "path_display"):
            if entry.__class__.__name__ == "FolderMetadata":
                folders.append(entry.path_display)
            else:
                files.append(entry.path_display)

    if folders:
        print("\nFOLDERS:")
        for folder in sorted(folders):
            print(f"  {folder}")

    if files:
        print("\nFILES (showing first 10):")
        for f in sorted(files)[:10]:
            print(f"  {f}")

    print("\n" + "=" * 60)
    print("\nTo explore a folder, update this script to use:")
    print('result = client.dbx.files_list_folder("/FolderName")')

except Exception as e:
    print(f"Error: {e}")
