# Dropbox Family Photo Organizer

![CI](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/workflows/CI/badge.svg)

Automatically scan your Dropbox photos, detect a specific person using face recognition, and organize matching photos into a designated folder.

## Features

- 🔍 Recursively scan Dropbox folders for photos
- 👤 Detect specific person using face recognition
- 📁 Automatically copy or move matching photos to destination folder
- 🔒 Safe by default: copies files instead of moving (preserves originals)
- 📝 Audit logging: tracks all file operations with timestamps
- 🚀 Efficient processing using thumbnails
- 🛡️ Dry-run mode to preview changes before copying/moving files
- 📊 Batch processing with progress tracking

## Quick Start

### 1. Setup Dropbox API

Follow the detailed instructions in [docs/DROPBOX_SETUP.md](docs/DROPBOX_SETUP.md) to:
- Create a Dropbox app
- Configure permissions
- Set up OAuth 2.0 authentication (recommended) or use legacy access tokens

### 2. Install Dependencies

#### Face Recognition Setup

The application supports multiple face recognition providers:

**Option A: Local Provider (Default)** - Runs offline, no API costs

For macOS users, use the automated installation script:

```bash
./scripts/installation/install_macos.sh
```

This script will install all required dependencies including dlib, face_recognition, and their system-level requirements. For manual installation or other operating systems, see [docs/FACE_RECOGNITION_LOCAL_SETUP.md](docs/FACE_RECOGNITION_LOCAL_SETUP.md).

**Option B: Azure Face API** - Cloud-based, high accuracy

```bash
pip install -r requirements-azure.txt
```

See [docs/AZURE_FACE_RECOGNITION_SETUP.md](docs/AZURE_FACE_RECOGNITION_SETUP.md) for Azure account setup and configuration.

**Option C: AWS Rekognition** - Cloud-based, highly scalable

```bash
pip install -r requirements-aws.txt
```

See [docs/AWS_FACE_RECOGNITION_SETUP.md](docs/AWS_FACE_RECOGNITION_SETUP.md) for AWS account setup and configuration.

#### Standard Installation

```bash
# Create a virtual environment (recommended)
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install required packages
pip install -r requirements.txt
```

### 3. Configure the Application

```bash
# Copy the example configuration
cp config/config.example.yaml config/config.yaml

# Edit config/config.yaml with your settings
# - Add your Dropbox app key and app secret (for OAuth 2.0)
# - Set source and destination folder paths
# - Configure face recognition settings
```

### 4. Authenticate with Dropbox

#### Option A: OAuth 2.0 (Recommended)

```bash
# Run the authorization script
python scripts/authorize_dropbox.py
```

This will guide you through:
- Visiting a Dropbox authorization URL
- Granting permissions to the app
- Storing refresh tokens securely in your system keyring

#### Option B: Legacy Access Token

See [docs/DROPBOX_SETUP.md](docs/DROPBOX_SETUP.md) for instructions on using legacy access tokens (not recommended).

### 5. Test the Connection

```bash
python scripts/test_dropbox_connection.py
```

This will verify:
- Your authentication is working (OAuth or legacy)
- The source folder is accessible
- Files can be listed and thumbnails retrieved
- Automatic token refresh is working (OAuth mode)

## Configuration

All settings are managed in `config/config.yaml`:

```yaml
dropbox:
  # OAuth 2.0 Authentication (Recommended)
  app_key: "YOUR_APP_KEY"
  app_secret: "YOUR_APP_SECRET"

  # Or Legacy Authentication (Not recommended)
  # access_token: "YOUR_TOKEN"

  source_folder: "/Photos/Family"
  destination_folder: "/Photos/PersonName"
  token_storage: "keyring"  # 'keyring' (secure) or 'config' (less secure)

face_recognition:
  reference_photos_dir: "./reference_photos"
  tolerance: 0.6
  thumbnail_size: "w256h256"

processing:
  operation: "copy"  # 'copy' (default) or 'move'
  log_operations: true  # Enable audit logging
  dry_run: true
  batch_size: 50
  image_extensions: [.jpg, .jpeg, .png, .heic]
```

### Key Settings

**Authentication:**
- **app_key** / **app_secret**: Dropbox app credentials for OAuth 2.0 (recommended)
- **access_token**: Legacy access token (not recommended, tokens expire)
- **token_storage**: Where to store refresh tokens (`keyring` for secure storage, `config` for file storage)

**Folders:**
- **source_folder**: Folder to scan for photos
- **destination_folder**: Where matching photos will be copied/moved

**Face Recognition:**
- **reference_photos_dir**: Local folder with reference photos of the target person
- **tolerance**: Face matching sensitivity (0.4-0.6 typical, lower = stricter)

**Processing:**
- **operation**: Operation mode - `copy` (default, safer) or `move` (destructive)
- **log_operations**: If true, logs all operations to `operations.log`
- **dry_run**: If true, lists matches without copying/moving files

## Logging

The application provides comprehensive logging for monitoring, debugging, and audit trails. All scripts use a centralized logging system that writes to both console and rotating log files.

### Log Files

- **Location**: `logs/photo_organizer.log` (created automatically)
- **Rotation**: Files are rotated at 10MB with 5 backup files kept
- **Format**: `timestamp - module - level - message`

### Verbose Logging

Use the `--verbose` flag to enable debug-level logging:

```bash
# Enable verbose logging for detailed debug information
python scripts/organize_photos.py --verbose

# All scripts support the --verbose flag
python scripts/train_face_model.py --verbose
python scripts/test_dropbox_connection.py --verbose
```

### Log Levels

- **INFO** (default): General operation information and progress
- **DEBUG** (verbose): Detailed debugging information including API calls, file processing details, and internal state

### Custom Log File Location

You can specify a custom log file location:

```bash
# Use a custom log file path
python scripts/organize_photos.py --log-file /path/to/custom.log
```

### Log File Management

- Log files are automatically created in the `logs/` directory
- Old log files are rotated: `photo_organizer.log.1`, `photo_organizer.log.2`, etc.
- Maximum 5 backup files are kept (configurable in code)
- Log files include timestamps, module names, and log levels for easy filtering

### Audit Logging

In addition to application logs, file operations are also logged to `operations.log` (JSON format) for audit purposes:

```json
{"timestamp": "2024-01-04T23:59:42.123456", "source": "/Photos/Family/photo.jpg", "destination": "/Photos/Person/photo.jpg", "operation": "copy", "success": true}
```

The audit logging system uses Python's `logging` module with a dedicated `FileHandler`, providing thread-safe writes. This ensures that concurrent operations (if running multiple instances) won't corrupt log entries.

## Project Structure

```
dropboxFamilyPhotoOrganizer/
├── config/
│   ├── config.yaml          # Your configuration (gitignored)
│   └── config.example.yaml  # Configuration template
├── docs/
│   ├── DROPBOX_SETUP.md              # Dropbox setup instructions
│   └── FACE_RECOGNITION_LOCAL_SETUP.md  # Face recognition setup guide
├── scripts/
│   ├── installation/
│   │   └── install_macos.sh    # macOS installation automation script
│   ├── dropbox_client.py   # Dropbox API client
│   ├── organize_photos.py  # Main photo organizer script
│   ├── test_dropbox_connection.py  # Connection test script
│   ├── check_account.py    # Account verification utility
│   └── list_folders.py     # Folder listing utility
├── requirements.txt         # Python dependencies
├── CLAUDE.md               # Claude Code guidance
└── README.md               # This file
```

## Usage

### Test Dropbox Connection

```bash
python scripts/test_dropbox_connection.py
```

### Run Photo Organizer (Coming Soon)

```bash
# Dry run (preview matches without copying/moving)
python scripts/organize_photos.py

# Copy files (default, preserves originals)
python scripts/organize_photos.py

# Move files instead of copying (use --move flag)
python scripts/organize_photos.py --move

# Custom log file location
python scripts/organize_photos.py --log-file /path/to/custom.log

# Verbose output
python scripts/organize_photos.py --verbose
```

### Operation Modes

**Copy (Default - Recommended)**
- Preserves original files in source location
- Safer option - no data loss if there are bugs
- Easy to revert - just delete destination files
- Maintains shared links and references
- Uses more Dropbox storage

**Move (Use with caution)**
- Removes files from source after copying
- Frees up storage in source folder
- Cannot be easily reversed
- May break shared links
- Enable with `--move` flag or set `operation: "move"` in config

All operations are logged to `operations.log` (unless disabled) for audit trail.

## Security Notes

- **Never commit `config/config.yaml`** - it may contain sensitive credentials
- The `.gitignore` file excludes `config/config.yaml` by default
- **OAuth 2.0 (recommended)**:
  - Refresh tokens are stored in system keyring by default (secure)
  - Can fallback to config file storage if keyring unavailable (less secure)
  - Access tokens are auto-managed and refreshed automatically
- **Legacy access tokens** (not recommended):
  - Provide full access to your Dropbox - keep them secure
  - Expire after ~4 hours with no automatic refresh
  - Store only in `config.yaml`, never commit or share

## Troubleshooting

### Authentication Issues

**"Invalid access token" or "Authentication failed"**
- **OAuth mode**: Run `python scripts/authorize_dropbox.py` to re-authenticate
- **Legacy mode**: Regenerate access token from App Console
- Verify credentials are copied correctly

**"No refresh token found"**
- Run `python scripts/authorize_dropbox.py` to complete OAuth setup
- If keyring unavailable, use `--force-config-storage` flag

**"Insufficient permissions" or 403 errors**
- Check app permissions in App Console → Permissions tab
- Ensure these scopes are enabled:
  - `files.metadata.read`
  - `files.metadata.write`
  - `files.content.read`
  - `files.content.write`
- Re-run authorization after changing permissions

### Other Issues

**"Path not found"**
- Verify folder paths start with `/`
- Check folder exists in Dropbox
- Paths are case-sensitive

**Keyring not available**
- Install keyring backend for your system (see DROPBOX_SETUP.md)
- Or use config file storage: `python scripts/authorize_dropbox.py --force-config-storage`

See [docs/DROPBOX_SETUP.md](docs/DROPBOX_SETUP.md) for comprehensive troubleshooting guide.

## Development

### Pre-commit Hooks (Optional but Recommended)

Install pre-commit hooks to automatically check code before commits:

```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

These hooks will automatically:
- Format code with Black
- Sort imports with isort
- Check for linting errors
- Scan for security issues (bandit)
- Check for dependency vulnerabilities (pip-audit)
- Validate YAML files
- Prevent committing secrets

**Note:** The `pip-audit` hook may take 10-30 seconds on first run as it queries vulnerability databases (subsequent runs use cache). For WIP commits, you can skip hooks with `git commit --no-verify`, but remember to run them before pushing.

### Running Tests Locally

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/ -v

# Run tests with coverage
pytest tests/ -v --cov=scripts --cov-report=term-missing

# Format code
black scripts/
isort scripts/

# Lint code
flake8 scripts/
```

### CI Pipeline

This project uses GitHub Actions for continuous integration. The CI pipeline runs on every push and pull request:

**Lint and Code Quality**
- Code formatting check (Black)
- Import sorting check (isort)
- Linting (flake8)
- Type checking (mypy)

**Testing**
- Unit tests across Python 3.10, 3.11, and 3.12
- Code coverage reporting

**Security**
- Security vulnerability scanning (bandit)
- Dependency vulnerability checks (safety)

**Configuration Validation**
- YAML syntax validation
- Python syntax checking

All checks must pass before code can be merged to the main branch.

## Development Status

✅ **Phase 1 (Current)**: Dropbox API integration
- Dropbox authentication
- Folder listing and file traversal
- File download and thumbnail retrieval
- File copy and move capabilities
- Audit logging for operations
- CLI with copy/move modes

🔲 **Phase 2 (Next)**: Face recognition integration
- Load reference photos
- Process images with face detection
- Match faces against reference encodings
- Generate match reports

🔲 **Phase 3 (Future)**: Automation and polish
- Command-line interface
- Progress bars and better logging
- Resume capability for interrupted runs
- Statistics and reporting

## License

MIT
