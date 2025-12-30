# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python-based tool to scan Dropbox directories for photos containing a specific person using face recognition, then move matching photos to a designated folder.

**Core workflow**: Access Dropbox → List photos recursively → Process with face detection → Move matches to target directory.

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
   - Move files with `/files/move_v2` (supports `autorename` for conflicts)

2. **Face Recognition Pipeline**:
   - Pre-compute face encodings from reference photos of target person
   - Process thumbnails (256x256) to reduce bandwidth and processing time
   - Compare face encodings with tolerance ~0.6
   - Filter for supported image formats: .jpg, .jpeg, .png, .heic

3. **Processing Strategy**:
   - Batch processing with logging and dry-run mode
   - Handle Dropbox API rate limits
   - Support resume on errors for large photo libraries

## Development Commands

*To be added once the project is initialized with a package manager and build tools.*
