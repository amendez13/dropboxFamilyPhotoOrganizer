# Face Recognition Local Setup Guide

This guide provides step-by-step instructions for setting up the local face recognition provider, which uses the `face_recognition` library (dlib-based) for offline face detection and matching.

## Table of Contents

- [Overview](#overview)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [macOS](#macos)
  - [Linux (Ubuntu/Debian)](#linux-ubuntudebian)
  - [Windows](#windows)
- [Configuration](#configuration)
- [First Training Run](#first-training-run)
- [Troubleshooting](#troubleshooting)

## Overview

The local face recognition provider offers:

- **Free**: No API costs
- **Privacy-friendly**: All processing happens on your machine
- **Offline**: Works without internet connection
- **Good accuracy**: Suitable for family photo organization

**Trade-offs**:
- Requires complex installation (dlib dependencies)
- Slower than cloud APIs for large batches
- CPU-only by default (no GPU acceleration)

## Prerequisites

The `face_recognition` library is built on top of dlib, which requires several system-level dependencies:

### Required Software

1. **Python 3.7 or higher**
   ```bash
   python3 --version
   ```

2. **C++ compiler and build tools**
   - macOS: Xcode Command Line Tools
   - Linux: GCC/G++
   - Windows: Visual Studio Build Tools

3. **CMake 3.8 or higher**
   - Required for building dlib
   ```bash
   cmake --version
   ```

4. **Python development headers**
   - Needed to compile Python extensions

## Installation

### macOS

1. **Install Xcode Command Line Tools**:
   ```bash
   xcode-select --install
   ```

2. **Install Homebrew** (if not already installed):
   ```bash
   /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
   ```

3. **Install CMake**:
   ```bash
   brew install cmake
   ```

4. **Create and activate virtual environment**:
   ```bash
   cd /path/to/dropboxFamilyPhotoOrganizer
   python3 -m venv venv
   source venv/bin/activate
   ```

5. **Install face_recognition**:
   ```bash
   pip install --upgrade pip
   pip install face-recognition
   ```

   This will automatically install:
   - dlib (the core face recognition library)
   - face-recognition (the Python wrapper)
   - numpy (numerical computing)
   - Pillow (image processing)

6. **Verify installation**:
   ```bash
   python -c "import face_recognition; print('Success! face_recognition version:', face_recognition.__version__)"
   ```

### Linux (Ubuntu/Debian)

1. **Install system dependencies**:
   ```bash
   sudo apt-get update
   sudo apt-get install -y \
       build-essential \
       cmake \
       libopenblas-dev \
       liblapack-dev \
       libx11-dev \
       libgtk-3-dev \
       python3-dev \
       python3-pip
   ```

2. **Create and activate virtual environment**:
   ```bash
   cd /path/to/dropboxFamilyPhotoOrganizer
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install face_recognition**:
   ```bash
   pip install --upgrade pip
   pip install face-recognition
   ```

4. **Verify installation**:
   ```bash
   python -c "import face_recognition; print('Success! face_recognition version:', face_recognition.__version__)"
   ```

### Windows

Windows installation can be challenging due to dlib's C++ dependencies. Here are two approaches:

#### Option 1: Using Pre-compiled Wheels (Recommended)

1. **Install Visual Studio Build Tools**:
   - Download from: https://visualstudio.microsoft.com/downloads/
   - Select "Desktop development with C++" workload
   - This provides MSVC compiler and Windows SDK

2. **Install CMake**:
   - Download from: https://cmake.org/download/
   - Add CMake to PATH during installation

3. **Create and activate virtual environment**:
   ```cmd
   cd C:\path\to\dropboxFamilyPhotoOrganizer
   python -m venv venv
   venv\Scripts\activate
   ```

4. **Install face_recognition**:
   ```cmd
   pip install --upgrade pip
   pip install face-recognition
   ```

5. **Verify installation**:
   ```cmd
   python -c "import face_recognition; print('Success!')"
   ```

#### Option 2: Using Anaconda (Alternative)

If the above fails, Anaconda provides pre-built binaries:

1. **Install Anaconda** from https://www.anaconda.com/download

2. **Create conda environment**:
   ```cmd
   conda create -n dropbox-organizer python=3.9
   conda activate dropbox-organizer
   ```

3. **Install via conda-forge**:
   ```cmd
   conda install -c conda-forge dlib
   pip install face-recognition
   ```

## Configuration

After installing the face_recognition library, configure your project:

1. **Copy the example configuration**:
   ```bash
   cp config/config.example.yaml config/config.yaml
   ```

2. **Edit `config/config.yaml`** to use the local provider:

   ```yaml
   face_recognition:
     # Set provider to 'local'
     provider: "local"

     # Path to reference photos directory
     reference_photos_dir: "./reference_photos"

     # Face matching tolerance (lower = more strict)
     # Recommended range: 0.4-0.6
     # 0.4 = very strict (fewer false positives)
     # 0.6 = more lenient (catches more matches)
     tolerance: 0.6

     # Local provider specific settings
     local:
       # Detection model: 'hog' or 'cnn'
       # - hog: Faster, CPU-based (recommended for most users)
       # - cnn: More accurate, requires GPU support
       model: "hog"

       # Number of times to re-sample face for encoding
       # Higher = more accurate but slower (1-10)
       num_jitters: 1
   ```

3. **Create reference photos directory**:
   ```bash
   mkdir -p reference_photos
   ```

## First Training Run

The "training" process for the local provider involves creating face encodings from reference photos of the person you want to detect.

### Step 1: Prepare Reference Photos

1. **Collect 3-10 high-quality photos** of the target person:
   - Clear, well-lit photos
   - Face clearly visible (frontal view preferred)
   - Different angles and expressions help
   - One face per photo (or the target face should be prominent)

2. **Copy photos to reference directory**:
   ```bash
   cp /path/to/photo1.jpg reference_photos/
   cp /path/to/photo2.jpg reference_photos/
   cp /path/to/photo3.jpg reference_photos/
   ```

   Supported formats: JPG, JPEG, PNG, HEIC

### Step 2: Test Face Detection

Create a test script to verify your reference photos work correctly:

```python
# test_face_detection.py
import face_recognition
import os

reference_dir = "./reference_photos"

print("Testing reference photos for face detection...\n")

for filename in os.listdir(reference_dir):
    if not filename.lower().endswith(('.jpg', '.jpeg', '.png')):
        continue

    filepath = os.path.join(reference_dir, filename)
    print(f"Processing: {filename}")

    # Load image
    image = face_recognition.load_image_file(filepath)

    # Detect faces
    face_locations = face_recognition.face_locations(image, model='hog')

    print(f"  Found {len(face_locations)} face(s)")

    if len(face_locations) == 0:
        print(f"  ⚠️  WARNING: No faces detected in {filename}")
    elif len(face_locations) > 1:
        print(f"  ⚠️  WARNING: Multiple faces found. Will use first face only.")
    else:
        print(f"  ✓ OK")

    print()

print("Done! Review warnings above and replace problematic photos if needed.")
```

Run the test:
```bash
source venv/bin/activate  # On macOS/Linux
# venv\Scripts\activate   # On Windows
python test_face_detection.py
```

### Step 3: Verify Configuration

Test that your configuration loads correctly:

```python
# test_provider.py
import yaml
from scripts.face_recognition.providers.local_provider import LocalFaceRecognitionProvider

# Load config
with open('config/config.yaml', 'r') as f:
    config = yaml.safe_load(f)

# Initialize provider
provider = LocalFaceRecognitionProvider(config['face_recognition']['local'])

# Validate
is_valid, error_msg = provider.validate_configuration()
if is_valid:
    print("✓ Configuration is valid")
else:
    print(f"✗ Configuration error: {error_msg}")

# Load reference photos
import glob
reference_photos = glob.glob(f"{config['face_recognition']['reference_photos_dir']}/*.jpg")
reference_photos += glob.glob(f"{config['face_recognition']['reference_photos_dir']}/*.jpeg")
reference_photos += glob.glob(f"{config['face_recognition']['reference_photos_dir']}/*.png")

print(f"\nFound {len(reference_photos)} reference photo(s)")

if reference_photos:
    num_faces = provider.load_reference_photos(reference_photos)
    print(f"✓ Successfully loaded {num_faces} reference face encoding(s)")
else:
    print("✗ No reference photos found!")
```

Run the test:
```bash
python test_provider.py
```

### Step 4: Understanding the Output

When you run the main photo organizer (future implementation), the local provider will:

1. **Load reference photos** at startup:
   ```
   INFO: Loaded reference face from: ./reference_photos/photo1.jpg
   INFO: Loaded reference face from: ./reference_photos/photo2.jpg
   INFO: Loaded 2 reference face(s)
   ```

2. **Process each Dropbox photo**:
   - Download thumbnail (256x256 for faster processing)
   - Detect faces in the photo
   - Compare each detected face against reference encodings
   - Calculate distance (lower = better match)

3. **Match criteria**:
   - Distance ≤ tolerance → Match found, photo will be moved
   - Distance > tolerance → No match, photo skipped

### Step 5: Tuning Parameters

If you're getting too many or too few matches, adjust these settings:

**Tolerance** (`config.yaml` → `face_recognition.tolerance`):
- Default: 0.6
- Lower (0.4-0.5): Stricter matching, fewer false positives
- Higher (0.6-0.7): More lenient, catches more variations
- Test with `dry_run: true` first!

**Detection Model** (`config.yaml` → `face_recognition.local.model`):
- `hog`: Fast, good for clear photos
- `cnn`: Slower but better for difficult angles/lighting (requires GPU)

**Num Jitters** (`config.yaml` → `face_recognition.local.num_jitters`):
- Default: 1 (fast)
- Higher (2-5): More accurate encoding, slower processing
- Recommended for reference photos: 5
- Recommended for batch processing: 1

## Troubleshooting

### Installation Issues

**Problem**: `error: Microsoft Visual C++ 14.0 or greater is required` (Windows)
- **Solution**: Install Visual Studio Build Tools (see Windows installation section)

**Problem**: `CMake must be installed to build dlib`
- **Solution**: Install CMake via your package manager (brew, apt, or download)

**Problem**: `fatal error: Python.h: No such file or directory`
- **Solution**: Install Python development headers:
  - Ubuntu/Debian: `sudo apt-get install python3-dev`
  - macOS: Included with Xcode Command Line Tools
  - Windows: Reinstall Python with "Development" option checked

### Runtime Issues

**Problem**: "No faces found in reference photo"
- **Solution**:
  - Ensure photo is clear and well-lit
  - Face should be at least 100x100 pixels
  - Try a different photo or use `model: "cnn"` for better detection

**Problem**: Too many false positives (wrong people matched)
- **Solution**:
  - Lower tolerance (try 0.5 or 0.4)
  - Add more diverse reference photos
  - Use higher quality reference photos

**Problem**: Missing real matches
- **Solution**:
  - Increase tolerance (try 0.65 or 0.7)
  - Add reference photos with different angles/lighting
  - Increase `num_jitters` for reference photo encoding

**Problem**: Processing is very slow
- **Solution**:
  - Ensure `model: "hog"` (not "cnn") for CPU-only systems
  - Reduce `num_jitters` to 1 for batch processing
  - Use smaller thumbnail size in config
  - Process in smaller batches

### Getting Help

For additional support:
- face_recognition library: https://github.com/ageitgey/face_recognition
- dlib documentation: http://dlib.net/
- Project issues: [Create an issue](../../issues)

## Next Steps

Once your local face recognition provider is set up:

1. Configure your Dropbox access token (see [DROPBOX_SETUP.md](./DROPBOX_SETUP.md))
2. Set your source and destination folders in `config/config.yaml`
3. Run the photo organizer with `dry_run: true` to preview matches
4. Review results and adjust tolerance if needed
5. Run with `dry_run: false` to actually move photos
