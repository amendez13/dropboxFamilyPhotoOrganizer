"""
Check Dropbox account details and app access type.
"""

import sys
import os
import yaml

# Add parent directory to path to import modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.dropbox_client import DropboxClient

# Load config
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

client = DropboxClient(config['dropbox']['access_token'])

print("=" * 60)
print("Dropbox Account Information")
print("=" * 60)

try:
    # Get account info
    account = client.dbx.users_get_current_account()
    print(f"\nAccount:")
    print(f"  Name: {account.name.display_name}")
    print(f"  Email: {account.email}")
    print(f"  Account ID: {account.account_id}")

    # Get space usage
    space = client.dbx.users_get_space_usage()
    used_gb = space.used / (1024**3)

    if hasattr(space, 'allocation') and hasattr(space.allocation, 'get_individual'):
        allocated_gb = space.allocation.get_individual().allocated / (1024**3)
        print(f"\nSpace Usage:")
        print(f"  Used: {used_gb:.2f} GB")
        print(f"  Allocated: {allocated_gb:.2f} GB")
    else:
        print(f"\nSpace Used: {used_gb:.2f} GB")

    # Try to list root folder with more details
    print(f"\nTrying to list root folder...")
    result = client.dbx.files_list_folder("", limit=20)

    print(f"\nFound {len(result.entries)} items in root:")
    for entry in result.entries:
        entry_type = "📁" if entry.__class__.__name__ == 'FolderMetadata' else "📄"
        print(f"  {entry_type} {entry.name}")

    # Check if there are more entries
    if result.has_more:
        print(f"\n  ... and more items (showing first 20)")

except Exception as e:
    print(f"\nError: {e}")
    print("\nThis might indicate:")
    print("  1. App is configured with 'App Folder' access (not 'Full Dropbox')")
    print("  2. Missing permissions")
    print("  3. Token needs to be regenerated after permission changes")
