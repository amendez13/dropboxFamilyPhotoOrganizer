# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python-based tool to scan Dropbox directories for photos containing a specific person using face recognition, then move matching photos to a designated folder.

**Core workflow**: Access Dropbox → List photos recursively → Process with face detection → Copy/move matches to target directory.

**Default operation**: Copy (safer, preserves originals) with optional move mode for when space is critical.

## Architecture

### Technology Stack
- **Dropbox SDK**: `dropbox` Python package for file operations
- **Face Recognition**: `face_recognition` library (dlib-based) for person identification
- **Image Processing**: Use Dropbox thumbnails via `/files/get_thumbnail` for faster processing

### Key Components
1. **Dropbox Integration**:
   - Required scopes: `files.content.read`, `files.content.write`, `files.metadata.read`
   - Use `/files/list_folder` with `recursive=True` for directory traversal
   - Handle pagination via `has_more` and `/files/list_folder/continue`
   - Copy files with `/files/copy_v2` (default, safer operation)
   - Move files with `/files/move_v2` (optional, space-efficient but destructive)
   - Both operations support `autorename` for conflicts

2. **Face Recognition Pipeline**:
   - Pre-compute face encodings from reference photos of target person
   - Process thumbnails (256x256) to reduce bandwidth and processing time
   - Compare face encodings with tolerance ~0.6
   - Filter for supported image formats: .jpg, .jpeg, .png, .heic

3. **Processing Strategy**:
   - Default to copy operation (safer, preserves originals)
   - Audit logging of all file operations to `operations.log`
   - Batch processing with progress tracking
   - Dry-run mode for safe testing
   - Handle Dropbox API rate limits
   - Support resume on errors for large photo libraries

## Development Commands

### Initial Setup

```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows

# Install dependencies
pip install -r requirements.txt

# Copy and configure settings
cp config/config.example.yaml config/config.yaml
# Edit config/config.yaml with your Dropbox access token and folder paths
```

### Running the Test Script

```bash
# Activate virtual environment (if not already active)
source venv/bin/activate

# Run Dropbox connection test
python scripts/test_dropbox_connection.py
```

### Common Commands

```bash
# Activate virtual environment
source venv/bin/activate

# Update dependencies
pip install --upgrade -r requirements.txt

# Check account details
python scripts/check_account.py

# List Dropbox folders
python scripts/list_folders.py

# Deactivate virtual environment when done
deactivate
```

### Running the Main Script

```bash
# Activate virtual environment
source venv/bin/activate

# Dry run (preview without changes)
python scripts/organize_photos.py --dry-run

# Copy mode (default - safer, preserves originals)
python scripts/organize_photos.py

# Move mode (space-efficient but destructive)
python scripts/organize_photos.py --move

# With verbose logging
python scripts/organize_photos.py --verbose
```
