#!/usr/bin/env python3
"""
Dropbox OAuth 2.0 Authorization Script

This script guides users through the OAuth 2.0 authorization flow to obtain
refresh tokens for the Dropbox Photo Organizer application.

Usage:
    python scripts/authorize_dropbox.py

The script will:
1. Read app credentials from config/config.yaml
2. Start the OAuth authorization flow
3. Provide a URL for the user to authorize the app
4. Receive the authorization code from the user
5. Exchange the code for access and refresh tokens
6. Store tokens securely (keyring or config file)

For more information, see docs/DROPBOX_SETUP.md
"""

import argparse
import logging
import sys
from pathlib import Path

import yaml

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from scripts.auth import OAuthManager, TokenStorage


def setup_logging(verbose: bool = False):
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )


def load_config(config_path: Path) -> dict:
    """Load configuration from YAML file."""
    try:
        with open(config_path) as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        print(f"Error: Configuration file not found: {config_path}")
        print("\nPlease copy config/config.example.yaml to config/config.yaml")
        print("and add your Dropbox app credentials.")
        sys.exit(1)
    except yaml.YAMLError as e:
        print(f"Error parsing configuration file: {e}")
        sys.exit(1)


def save_tokens_to_config(config_path: Path, tokens: dict):
    """
    Save tokens to config file (fallback when keyring is not available).

    Args:
        config_path: Path to config.yaml
        tokens: Dictionary containing refresh_token and other token data
    """
    try:
        # Load current config
        with open(config_path) as f:
            config = yaml.safe_load(f)

        # Add refresh token to config
        if "dropbox" not in config:
            config["dropbox"] = {}

        config["dropbox"]["refresh_token"] = tokens["refresh_token"]

        # Save updated config
        with open(config_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        print(f"\n✓ Refresh token saved to: {config_path}")
        print("\nWARNING: Token is stored in plaintext in the config file.")
        print("For better security, install keyring: pip install keyring")

    except Exception as e:
        print(f"\nError saving tokens to config file: {e}")
        print("\nPlease manually add the following to your config.yaml:")
        print(f"\ndropbox:\n  refresh_token: \"{tokens['refresh_token']}\"")


def main():
    """Main authorization flow."""
    parser = argparse.ArgumentParser(
        description="Authorize Dropbox Photo Organizer with OAuth 2.0"
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=project_root / "config" / "config.yaml",
        help="Path to configuration file (default: config/config.yaml)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable verbose logging"
    )
    parser.add_argument(
        "--force-config-storage",
        action="store_true",
        help="Force storing tokens in config file instead of keyring",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    print("=" * 70)
    print("Dropbox Photo Organizer - OAuth 2.0 Authorization")
    print("=" * 70)

    # Load configuration
    config = load_config(args.config)

    # Get app credentials
    dropbox_config = config.get("dropbox", {})
    app_key = dropbox_config.get("app_key")
    app_secret = dropbox_config.get("app_secret")

    if not app_key:
        print("\nError: app_key not found in configuration file.")
        print("\nPlease add your Dropbox app key to config/config.yaml:")
        print("\ndropbox:\n  app_key: \"YOUR_APP_KEY_HERE\"")
        print("\nSee docs/DROPBOX_SETUP.md for instructions on creating a Dropbox app.")
        sys.exit(1)

    # Initialize OAuth manager
    oauth_manager = OAuthManager(app_key, app_secret)

    # Start authorization flow
    print("\nStarting OAuth 2.0 authorization flow...")
    print("\nThis will use PKCE (Proof Key for Code Exchange) for enhanced security.")
    print("You will receive a refresh token that can be used indefinitely.")

    try:
        authorize_url = oauth_manager.start_authorization_flow()

        print("\n" + "=" * 70)
        print("STEP 1: Authorize the application")
        print("=" * 70)
        print(f"\nPlease visit this URL in your browser:\n\n{authorize_url}\n")
        print("1. Log in to your Dropbox account (if not already logged in)")
        print("2. Click 'Allow' to grant access to the application")
        print("3. Copy the authorization code shown on the page")

        # Get authorization code from user
        print("\n" + "=" * 70)
        print("STEP 2: Enter the authorization code")
        print("=" * 70)
        auth_code = input("\nEnter the authorization code: ").strip()

        if not auth_code:
            print("\nError: No authorization code provided.")
            sys.exit(1)

        # Complete authorization flow
        print("\nExchanging authorization code for tokens...")
        tokens = oauth_manager.complete_authorization_flow(auth_code)

        print("\n" + "=" * 70)
        print("STEP 3: Save tokens securely")
        print("=" * 70)

        # Save tokens
        token_storage = TokenStorage()

        if not args.force_config_storage and token_storage.keyring_available:
            # Use keyring for secure storage
            print("\nSaving tokens to system keyring (secure storage)...")
            success = token_storage.save_tokens(tokens)

            if success:
                print("✓ Tokens saved successfully to system keyring!")
                print("\nYour refresh token is now stored securely.")
                print("The application will automatically refresh access tokens as needed.")
            else:
                print("\nFailed to save tokens to keyring. Falling back to config file...")
                save_tokens_to_config(args.config, tokens)
        else:
            # Fallback to config file
            if args.force_config_storage:
                print("\nForced config file storage (less secure)...")
            else:
                print("\nKeyring not available. Saving to config file (less secure)...")

            save_tokens_to_config(args.config, tokens)

        # Show success message
        print("\n" + "=" * 70)
        print("Authorization Complete!")
        print("=" * 70)
        print(f"\n✓ Account ID: {tokens['account_id']}")
        print("\nYou can now use the Dropbox Photo Organizer.")
        print("\nNext steps:")
        print("1. Test the connection: python scripts/test_dropbox_connection.py")
        print("2. Configure your source and destination folders in config/config.yaml")
        print("3. Run the photo organizer: python scripts/organize_photos.py")

    except KeyboardInterrupt:
        print("\n\nAuthorization cancelled by user.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Authorization failed: {e}", exc_info=args.verbose)
        print(f"\nError: Authorization failed: {e}")
        print("\nPlease check:")
        print("1. Your app_key is correct in config/config.yaml")
        print("2. You copied the authorization code correctly")
        print("3. Your Dropbox app has the required permissions")
        print("\nSee docs/DROPBOX_SETUP.md for more information.")
        sys.exit(1)


if __name__ == "__main__":
    main()
