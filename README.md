# Dropbox Family Photo Organizer

Automatically scan your Dropbox photos, detect a specific person using face recognition, and organize matching photos into a designated folder.

## Features

- 🔍 Recursively scan Dropbox folders for photos
- 👤 Detect specific person using face recognition
- 📁 Automatically copy or move matching photos to destination folder
- 🔒 Safe by default: copies files instead of moving (preserves originals)
- 📝 Audit logging: tracks all file operations with timestamps
- 🚀 Efficient processing using thumbnails
- ⚡ Face encoding cache for faster startup (no need to reprocess reference photos)
- 🛡️ Dry-run mode to preview changes before copying/moving files
- 📊 Batch processing with progress tracking

## Quick Start

### 1. Setup Dropbox API

Follow the detailed instructions in [docs/DROPBOX_SETUP.md](docs/DROPBOX_SETUP.md) to:
- Create a Dropbox app
- Configure permissions
- Generate an access token

### 2. Install Dependencies

#### Face Recognition Setup (macOS)

For macOS users, use the automated installation script:

```bash
./scripts/installation/install_macos.sh
```

This script will install all required dependencies including dlib, face_recognition, and their system-level requirements. For manual installation or other operating systems, see [docs/FACE_RECOGNITION_LOCAL_SETUP.md](docs/FACE_RECOGNITION_LOCAL_SETUP.md).

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
# - Add your Dropbox access token
# - Set source and destination folder paths
# - Configure face recognition settings
```

### 4. Test the Connection

```bash
python scripts/test_dropbox_connection.py
```

This will verify:
- Your Dropbox access token is valid
- The source folder is accessible
- Files can be listed and thumbnails retrieved

## Configuration

All settings are managed in `config/config.yaml`:

```yaml
dropbox:
  access_token: "YOUR_TOKEN"
  source_folder: "/Photos/Family"
  destination_folder: "/Photos/PersonName"

face_recognition:
  reference_photos_dir: "./reference_photos"
  tolerance: 0.6
  thumbnail_size: "w256h256"
  local:
    cache_file: "./cache/face_encodings.pkl"  # Optional: enables caching

processing:
  operation: "copy"  # 'copy' (default) or 'move'
  log_operations: true  # Enable audit logging
  dry_run: true
  batch_size: 50
  image_extensions: [.jpg, .jpeg, .png, .heic]
```

### Key Settings

- **access_token**: Your Dropbox API token (from App Console)
- **source_folder**: Folder to scan for photos
- **destination_folder**: Where matching photos will be copied/moved
- **reference_photos_dir**: Local folder with reference photos of the target person
- **tolerance**: Face matching sensitivity (0.4-0.6 typical, lower = stricter)
- **cache_file**: Optional path to cache file for face encodings (speeds up subsequent runs)
- **operation**: Operation mode - `copy` (default, safer) or `move` (destructive)
- **log_operations**: If true, logs all operations to `operations.log`
- **dry_run**: If true, lists matches without copying/moving files

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

### Face Encoding Cache

The face recognition system supports caching to improve performance:

**How it works:**
- First run: Generates face encodings from reference photos and saves to cache file
- Subsequent runs: Loads encodings from cache (much faster than regenerating)
- Auto-invalidation: Cache automatically regenerates if:
  - Reference photos are added, removed, or modified
  - Face recognition settings change (model, tolerance, etc.)
  - Cache file is corrupted or incompatible

**Configuration:**
```yaml
face_recognition:
  local:
    cache_file: "./cache/face_encodings.pkl"  # Enable caching
    # cache_file: null  # Disable caching (always regenerate)
```

**Benefits:**
- ⚡ Faster startup (skip face encoding generation)
- 💾 Encodings computed once and reused
- 🔄 Automatic cache invalidation ensures accuracy
- 🎯 Transparent to users (works automatically)

**Managing the cache:**
- Cache is stored in `./cache/` directory (gitignored)
- To force regeneration: delete the cache file or modify reference photos
- Cache is provider-specific (local/AWS/Azure use separate caches)

## Security Notes

- **Never commit `config/config.yaml`** - it contains your access token
- The `.gitignore` file excludes `config/config.yaml` by default
- Access tokens provide full access to your Dropbox - keep them secure
- Consider using environment variables for sensitive data in production

## Troubleshooting

### "Invalid access token"
- Verify token is copied correctly from App Console
- Regenerate token if needed

### "Insufficient permissions" or 403 errors
- Check app permissions in App Console → Permissions tab
- Ensure these scopes are enabled:
  - `files.metadata.read`
  - `files.metadata.write`
  - `files.content.read`
  - `files.content.write`
- Generate a new token after updating permissions

### "Path not found"
- Verify folder paths start with `/`
- Check folder exists in Dropbox
- Paths are case-sensitive

See [docs/DROPBOX_SETUP.md](docs/DROPBOX_SETUP.md) for more troubleshooting tips.

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
