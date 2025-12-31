# Dropbox Family Photo Organizer

Automatically scan your Dropbox photos, detect a specific person using face recognition, and organize matching photos into a designated folder.

## Features

- 🔍 Recursively scan Dropbox folders for photos
- 👤 Detect specific person using face recognition
- 📁 Automatically move matching photos to destination folder
- 🚀 Efficient processing using thumbnails
- 🛡️ Dry-run mode to preview changes before moving files
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

processing:
  dry_run: true
  batch_size: 50
  image_extensions: [.jpg, .jpeg, .png, .heic]
```

### Key Settings

- **access_token**: Your Dropbox API token (from App Console)
- **source_folder**: Folder to scan for photos
- **destination_folder**: Where matching photos will be moved
- **reference_photos_dir**: Local folder with reference photos of the target person
- **tolerance**: Face matching sensitivity (0.4-0.6 typical, lower = stricter)
- **dry_run**: If true, lists matches without moving files

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
# Dry run (preview matches without moving)
python scripts/organize_photos.py

# Actually move files (set dry_run: false in config/config.yaml)
python scripts/organize_photos.py
```

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
- File moving capabilities

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
