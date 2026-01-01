# Dropbox API Setup Guide

This guide walks you through setting up a Dropbox app and configuring authentication for the photo organizer.

**Recommended**: Use OAuth 2.0 with refresh tokens for automatic token management and enhanced security.

## Prerequisites

- A Dropbox account (free or paid)
- Access to the [Dropbox App Console](https://www.dropbox.com/developers/apps)
- Python 3.10 or higher installed

## Step 1: Create a Dropbox App

1. Go to the [Dropbox App Console](https://www.dropbox.com/developers/apps)
2. Click **"Create app"**
3. Choose the following settings:
   - **API**: Select **"Scoped access"**
   - **Access type**: Select **"Full Dropbox"** (to access all folders and files)
   - **Name**: Give your app a unique name (e.g., "Family Photo Organizer")
4. Click **"Create app"**

## Step 2: Configure App Permissions

After creating the app, you'll be taken to the app's settings page. You need to configure the permissions (scopes) for your app.

1. Navigate to the **"Permissions"** tab
2. Enable the following permissions:
   - **`files.metadata.write`** - To read folder/file metadata
   - **`files.metadata.read`** - To list folder contents
   - **`files.content.write`** - To move files
   - **`files.content.read`** - To download files and thumbnails
3. Click **"Submit"** at the bottom of the page

> **Important**: You must configure permissions before generating an access token, or the token won't have the necessary scopes.

## Step 3: Get App Credentials

1. Go to the **"Settings"** tab
2. Find the **"App key"** and **"App secret"** in the **"OAuth 2"** section
3. Copy these values - you'll need them for OAuth authentication

> **Note**: The App secret is optional but recommended for additional security.

## Step 4: Choose Authentication Method

### Option A: OAuth 2.0 with Refresh Tokens (Recommended)

OAuth 2.0 provides automatic token refresh and better security. This is the recommended approach.

#### 4A.1: Install Dependencies

```bash
# Activate your virtual environment
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages (including keyring for secure storage)
pip install -r requirements.txt
```

#### 4A.2: Configure App Credentials

1. Copy the example configuration file:
   ```bash
   cp config/config.example.yaml config/config.yaml
   ```

2. Edit `config/config.yaml` and add your app credentials:
   ```yaml
   dropbox:
     app_key: "YOUR_APP_KEY_HERE"
     app_secret: "YOUR_APP_SECRET_HERE"  # Optional but recommended
     source_folder: "/path/to/your/photos"
     destination_folder: "/path/to/destination"
     token_storage: "keyring"  # Use keyring for secure storage
   ```

#### 4A.3: Run Authorization Script

Run the authorization script to authenticate and obtain refresh tokens:

```bash
python scripts/authorize_dropbox.py
```

The script will:
1. Provide a URL for you to visit in your browser
2. Ask you to log in to Dropbox and authorize the app
3. Request an authorization code that Dropbox provides
4. Exchange the code for access and refresh tokens
5. Store the refresh token securely in your system keyring

**Follow the on-screen instructions carefully.**

#### 4A.4: Verify the Setup

Run the test script to verify your OAuth connection:

```bash
python scripts/test_dropbox_connection.py
```

This will:
- Test authentication using your refresh token
- Automatically refresh the access token if needed
- List files in your source folder
- Verify permissions are correctly configured

### Option B: Legacy Access Token (Not Recommended)

**Warning**: Legacy access tokens have limitations:
- Expire after a short time (typically 4 hours)
- No automatic refresh capability
- Require manual regeneration when expired
- Less secure than OAuth 2.0

**Only use this method if you cannot use OAuth 2.0.**

#### 4B.1: Generate an Access Token

1. Go to the **"Settings"** tab in App Console
2. Scroll down to the **"OAuth 2"** section
3. Under **"Generated access token"**, click **"Generate"**
4. Copy the generated token

#### 4B.2: Configure the Application

1. Copy the example configuration file:
   ```bash
   cp config/config.example.yaml config/config.yaml
   ```

2. Edit `config/config.yaml` and add your access token:
   ```yaml
   dropbox:
     access_token: "YOUR_GENERATED_TOKEN_HERE"
     source_folder: "/path/to/your/photos"
     destination_folder: "/path/to/destination"
   ```

3. Set the correct folder paths (see note below)

#### 4B.3: Verify the Setup

Run the test script to verify your Dropbox connection:

```bash
python scripts/test_dropbox_connection.py
```

This will test authentication with your access token and list files in your source folder.

---

## Folder Path Configuration

Set the correct folder paths in `config/config.yaml`:

- **source_folder**: The Dropbox folder containing photos to scan (e.g., `"/Photos/Family"` or `"/Camera Uploads"`)
- **destination_folder**: Where matching photos will be copied/moved (e.g., `"/Photos/PersonName"`)

> **Note**: Paths are relative to your Dropbox root and should:
> - Start with `/`
> - Use forward slashes `/`, not backslashes `\`
> - Be case-sensitive
>
> To find the exact path:
> - Open the folder in Dropbox web interface - the path is shown in the URL
> - Or right-click a folder in the desktop app and select "Copy Dropbox Link"

## Troubleshooting

### Authentication Issues

#### "Invalid access token" or "Authentication failed"
- **OAuth mode**: Run `python scripts/authorize_dropbox.py` to re-authenticate
- **Legacy mode**: Regenerate a new access token from the App Console
- Verify the token/credentials are copied correctly without extra spaces
- Check that your app credentials haven't been revoked in the App Console

#### "No refresh token found" or "Cannot load tokens"
- **First time setup**: Run `python scripts/authorize_dropbox.py` to get tokens
- **Keyring issues**: Try `--force-config-storage` flag to use config file instead
  ```bash
  python scripts/authorize_dropbox.py --force-config-storage
  ```
- **Missing keyring**: Install with `pip install keyring`

#### "Insufficient permissions" or 403 errors
- Return to the App Console → Permissions tab
- Verify all required permissions are enabled:
  - `files.metadata.write`
  - `files.metadata.read`
  - `files.content.write`
  - `files.content.read`
- **OAuth mode**: Re-run authorization after changing permissions
- **Legacy mode**: Generate a new access token (old tokens don't get updated permissions)

### File/Folder Issues

#### "Path not found" errors
- Check that folder paths start with `/`
- Verify the folder exists in your Dropbox
- Path is case-sensitive
- Use forward slashes `/`, not backslashes `\`

#### "App key not found in configuration"
- Add your app credentials to `config/config.yaml`:
  ```yaml
  dropbox:
    app_key: "YOUR_APP_KEY_HERE"
    app_secret: "YOUR_APP_SECRET_HERE"
  ```

### Keyring Issues

#### Keyring not available on your system
Some systems don't have a keyring backend by default. Install one:

**macOS**: Built-in (Keychain)

**Linux**:
```bash
# Install a keyring backend
sudo apt-get install gnome-keyring  # For GNOME
# or
sudo apt-get install kwallet        # For KDE
```

**Windows**: Built-in (Credential Manager)

**Alternative**: Use config file storage (less secure):
```bash
python scripts/authorize_dropbox.py --force-config-storage
```

## Understanding Keyring Storage

The keyring system provides secure, encrypted storage for your OAuth refresh token. This section explains how it works and how to manage your stored credentials.

### What is Stored in the Keyring?

When you complete the OAuth authorization flow, the following information is stored in your system keyring:

```json
{
  "access_token": "sl.xxx...",       // Short-lived (4 hours)
  "refresh_token": "xxx...",         // Long-lived (never expires)
  "expires_at": "1234567890",        // Unix timestamp
  "account_id": "dbid:xxx..."        // Your Dropbox account ID
}
```

**Key Point**: Only the **refresh token** is critical for long-term storage. The access token is automatically refreshed by the application.

### How Keyring Works by Platform

#### macOS (Keychain)
- **Storage location**: macOS Keychain (same place Safari stores passwords)
- **Service name**: `dropbox-photo-organizer`
- **Account name**: `default`
- **Security**: Encrypted by macOS, protected by your login password

**Viewing stored tokens**:
1. Open **Keychain Access** app (in Applications → Utilities)
2. Search for `dropbox-photo-organizer`
3. Double-click the entry to view details
4. Click "Show password" to see the stored JSON (requires your Mac password)

**Manually deleting tokens**:
```bash
# Using Python
python -c "import keyring; keyring.delete_password('dropbox-photo-organizer', 'default')"

# Or via Keychain Access GUI
# Find "dropbox-photo-organizer" → Right-click → Delete
```

#### Windows (Credential Manager)
- **Storage location**: Windows Credential Manager
- **Service name**: `dropbox-photo-organizer`
- **Account name**: `default`
- **Security**: Encrypted by Windows, protected by your Windows account

**Viewing stored tokens**:
1. Open **Control Panel** → **Credential Manager**
2. Click **Windows Credentials**
3. Look for `dropbox-photo-organizer`
4. Click to expand and view details

**Manually deleting tokens**:
```powershell
# Using Python
python -c "import keyring; keyring.delete_password('dropbox-photo-organizer', 'default')"

# Or via Credential Manager GUI
# Find "dropbox-photo-organizer" → Remove
```

#### Linux (gnome-keyring / kwallet)
- **Storage location**: GNOME Keyring or KWallet (depending on desktop environment)
- **Service name**: `dropbox-photo-organizer`
- **Account name**: `default`
- **Security**: Encrypted, typically protected by your login keyring password

**Viewing stored tokens (GNOME)**:
1. Open **Seahorse** (Passwords and Keys app)
2. Look in "Login" keyring
3. Search for `dropbox-photo-organizer`

**Viewing stored tokens (KDE)**:
1. Open **KWalletManager**
2. Look in your default wallet
3. Search for `dropbox-photo-organizer`

**Manually deleting tokens**:
```bash
# Using Python
python -c "import keyring; keyring.delete_password('dropbox-photo-organizer', 'default')"

# Or use GUI tools (Seahorse/KWalletManager)
```

### Verifying Keyring Storage

To verify that your tokens are stored correctly in the keyring:

```bash
# Check if tokens exist in keyring
python -c "
import keyring
token_data = keyring.get_password('dropbox-photo-organizer', 'default')
if token_data:
    print('✓ Tokens found in keyring')
    import json
    tokens = json.loads(token_data)
    print(f'Account ID: {tokens.get(\"account_id\", \"N/A\")}')
    print(f'Has refresh token: {\"refresh_token\" in tokens}')
else:
    print('✗ No tokens found in keyring')
"
```

### Keyring vs Config File Storage

The application supports two storage modes:

| Feature | Keyring (Recommended) | Config File |
|---------|----------------------|-------------|
| **Security** | Encrypted by OS | Plain text in YAML |
| **Portability** | Platform-dependent | Easy to backup/transfer |
| **Setup complexity** | Requires keyring backend | No extra setup needed |
| **Best for** | Production use | Development/testing |

**Setting storage mode in config.yaml**:
```yaml
dropbox:
  token_storage: "keyring"  # or "config"
```

### Common Keyring Scenarios

#### Scenario 1: Moving to a New Computer
Your keyring is tied to your user account on a specific machine. When moving to a new computer:

1. **Option A** (Recommended): Re-authorize on the new computer
   ```bash
   python scripts/authorize_dropbox.py
   ```

2. **Option B**: Export and import tokens manually
   ```bash
   # On old computer: Export tokens to config
   python scripts/authorize_dropbox.py --force-config-storage

   # Copy config/config.yaml to new computer

   # On new computer: Import to keyring
   python scripts/authorize_dropbox.py
   # (will read refresh_token from config and save to keyring)
   ```

#### Scenario 2: Multiple Dropbox Accounts
To use different Dropbox accounts, modify the username parameter:

```python
# In your custom script
from scripts.auth.oauth_manager import TokenStorage

storage = TokenStorage()
storage.save_tokens(tokens, username="personal")
storage.save_tokens(tokens, username="work")

# Load specific account
personal_tokens = storage.load_tokens(username="personal")
work_tokens = storage.load_tokens(username="work")
```

#### Scenario 3: Keyring Access Issues
If you encounter permission errors accessing the keyring:

**macOS**:
- Ensure Keychain Access is not locked
- Grant Terminal/IDE access to Keychain when prompted
- Reset keyring: Open Keychain Access → Keychain First Aid

**Linux**:
- Ensure keyring daemon is running: `ps aux | grep gnome-keyring`
- Unlock keyring: `gnome-keyring-daemon --unlock`
- Set password: Use Seahorse to set a keyring password

**Windows**:
- Run terminal as Administrator if needed
- Check User Account Control settings

#### Scenario 4: Debugging Token Issues
If tokens aren't working as expected:

```bash
# 1. Verify tokens are stored
python -c "import keyring; print(keyring.get_password('dropbox-photo-organizer', 'default'))"

# 2. Test token refresh manually
python -c "
from scripts.auth.oauth_manager import OAuthManager, TokenStorage
import json

storage = TokenStorage()
tokens = storage.load_tokens()

if tokens:
    oauth_mgr = OAuthManager(app_key='YOUR_APP_KEY', app_secret='YOUR_APP_SECRET')
    new_tokens = oauth_mgr.refresh_access_token(tokens['refresh_token'])
    print('✓ Token refresh successful')
    print(f'New access token: {new_tokens[\"access_token\"][:20]}...')
else:
    print('✗ No tokens found')
"

# 3. Delete and re-authorize if issues persist
python -c "import keyring; keyring.delete_password('dropbox-photo-organizer', 'default')"
python scripts/authorize_dropbox.py
```

### Security Best Practices

1. **Never commit tokens to version control**
   - The `.gitignore` file excludes `config/config.yaml`
   - Keep keyring-stored tokens safe

2. **Use keyring on production systems**
   - Config file storage is acceptable for development
   - Always use keyring for deployed applications

3. **Rotate tokens periodically**
   - Revoke and re-authorize every 6-12 months
   - Immediately revoke if credentials are compromised

4. **Monitor connected apps**
   - Review [connected apps](https://www.dropbox.com/account/connected_apps) regularly
   - Remove unused or suspicious authorizations

5. **Limit app permissions**
   - Only grant necessary scopes in App Console
   - Use "App Folder" access type if possible (instead of "Full Dropbox")

## Token Management

### OAuth 2.0 Tokens (Recommended)

#### Security
- **Refresh tokens** are stored in system keyring (secure) or config file (less secure)
- **Access tokens** are managed automatically by the application
- Tokens are never logged or displayed after initial authorization
- The `config.yaml` file is gitignored by default

#### Token Refresh
- Access tokens expire after ~4 hours
- The application automatically refreshes them using the refresh token
- No manual intervention required
- Refresh tokens don't expire unless revoked

#### Revoking OAuth Access
To revoke access:
1. Go to [Dropbox Account Settings](https://www.dropbox.com/account/connected_apps)
2. Find your app in the list
3. Click "Revoke" to remove access
4. Delete stored tokens:
   ```bash
   # If using keyring
   python -c "import keyring; keyring.delete_password('dropbox-photo-organizer', 'default')"

   # If using config file
   # Remove the refresh_token line from config/config.yaml
   ```

### Legacy Access Tokens (Not Recommended)

#### Security
- Store access tokens only in `config.yaml` (gitignored)
- Never commit or share access tokens
- Tokens provide full access to your Dropbox account

#### Token Expiration
- Short-lived tokens expire after ~4 hours
- Long-lived tokens don't expire but can be revoked
- No automatic refresh capability
- **Recommendation**: Migrate to OAuth 2.0 for automatic token management

#### Revoking Legacy Tokens
1. Go to Dropbox App Console
2. Select your app
3. Settings tab → "Generated access token" section
4. Click "Revoke" next to your token

## Next Steps

Once setup is complete:
1. Add reference photos to the `reference_photos/` directory
2. Configure face recognition settings in `config.yaml`
3. Run the main script with `dry_run: true` to test
4. Review results and set `dry_run: false` to move files

## Additional Resources

- [Dropbox API Documentation](https://www.dropbox.com/developers/documentation)
- [Python SDK Reference](https://dropbox-sdk-python.readthedocs.io/)
- [Dropbox API Explorer](https://dropbox.github.io/dropbox-api-v2-explorer/) - Test API calls interactively
