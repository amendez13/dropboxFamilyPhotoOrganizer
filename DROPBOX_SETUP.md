# Dropbox API Setup Guide

This guide walks you through setting up a Dropbox app and obtaining the necessary API credentials to use this photo organizer.

## Prerequisites

- A Dropbox account (free or paid)
- Access to the [Dropbox App Console](https://www.dropbox.com/developers/apps)

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

## Step 3: Generate an Access Token

1. Go to the **"Settings"** tab
2. Scroll down to the **"OAuth 2"** section
3. Under **"Generated access token"**, click **"Generate"**
4. Copy the generated token - this is your `access_token`

> **Security Warning**:
> - This token provides full access to your Dropbox account
> - Never share it publicly or commit it to version control
> - Store it securely in your `config.yaml` file (which is gitignored)

## Step 4: Configure the Application

1. Copy the example configuration file:
   ```bash
   cp config.example.yaml config.yaml
   ```

2. Edit `config.yaml` and add your access token:
   ```yaml
   dropbox:
     access_token: "YOUR_GENERATED_TOKEN_HERE"
     source_folder: "/path/to/your/photos"
     destination_folder: "/path/to/destination"
   ```

3. Set the correct folder paths:
   - **source_folder**: The Dropbox folder containing photos to scan (e.g., `"/Photos/Family"`)
   - **destination_folder**: Where matching photos will be moved (e.g., `"/Photos/PersonName"`)

> **Note**: Paths are relative to your Dropbox root. You can find the exact path by:
> - Opening the folder in Dropbox web interface
> - The path is shown in the URL after `/home`
> - Or right-click a folder in the desktop app and select "Copy Dropbox Link"

## Step 5: Verify the Setup

Run the test script to verify your Dropbox connection:

```bash
python test_dropbox_connection.py
```

This will:
- Test authentication with your access token
- List files in your source folder
- Verify permissions are correctly configured

## Troubleshooting

### "Invalid access token"
- Make sure you copied the entire token
- Verify the token hasn't expired (tokens don't expire by default, but can be manually revoked)
- Regenerate a new token from the App Console if needed

### "Insufficient permissions" or 403 errors
- Return to the App Console → Permissions tab
- Verify all required permissions are enabled
- Generate a new access token (old tokens don't automatically get new permissions)

### "Path not found" errors
- Check that folder paths start with `/`
- Verify the folder exists in your Dropbox
- Path is case-sensitive
- Use forward slashes `/`, not backslashes `\`

## Token Management

### Token Security
- Keep your access token private
- Don't share it or commit it to repositories
- The `config.yaml` file is already in `.gitignore`

### Token Expiration
- By default, generated access tokens don't expire
- You can revoke them at any time from the App Console
- For production use, consider implementing OAuth 2.0 refresh tokens

### Revoking Access
To revoke access:
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
