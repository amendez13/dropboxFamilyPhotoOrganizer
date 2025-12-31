#!/bin/bash
#
# macOS Installation Script for Face Recognition Local Setup
# This script automates the installation steps from docs/FACE_RECOGNITION_LOCAL_SETUP.md
#
# Usage: ./scripts/install_macos.sh
#

set -e  # Exit on error

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Track overall success
OVERALL_SUCCESS=true

# Logging functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
    OVERALL_SUCCESS=false
}

# Error handler
handle_error() {
    log_error "An error occurred on line $1"
    log_error "Installation failed. Please check the error above and try again."
    exit 1
}

trap 'handle_error $LINENO' ERR

# Banner
echo ""
echo "=============================================="
echo "  Face Recognition Local Setup - macOS"
echo "=============================================="
echo ""

# Determine script directory and project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"

log_info "Project root: $PROJECT_ROOT"
cd "$PROJECT_ROOT"

# Step 1: Check and install Xcode Command Line Tools
echo ""
log_info "Step 1: Checking Xcode Command Line Tools..."

if xcode-select -p &> /dev/null; then
    XCODE_PATH=$(xcode-select -p)
    log_success "Xcode Command Line Tools already installed at: $XCODE_PATH"
else
    log_warning "Xcode Command Line Tools not found. Installing..."

    # Trigger installation
    xcode-select --install &> /dev/null || true

    log_info "A dialog should appear to install Xcode Command Line Tools."
    log_info "Please complete the installation and press Enter to continue..."
    read -r

    # Verify installation
    if xcode-select -p &> /dev/null; then
        log_success "Xcode Command Line Tools installed successfully"
    else
        log_error "Xcode Command Line Tools installation failed"
        log_error "Please install manually and run this script again"
        exit 1
    fi
fi

# Step 2: Check and install Homebrew
echo ""
log_info "Step 2: Checking Homebrew..."

if command -v brew &> /dev/null; then
    BREW_VERSION=$(brew --version | head -n 1)
    log_success "Homebrew already installed: $BREW_VERSION"
else
    log_warning "Homebrew not found. Installing..."

    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add Homebrew to PATH for Apple Silicon Macs
    if [[ $(uname -m) == 'arm64' ]]; then
        if [[ -f /opt/homebrew/bin/brew ]]; then
            eval "$(/opt/homebrew/bin/brew shellenv)"
        fi
    fi

    # Verify installation
    if command -v brew &> /dev/null; then
        log_success "Homebrew installed successfully"
    else
        log_error "Homebrew installation failed"
        log_error "Please install manually from https://brew.sh and run this script again"
        exit 1
    fi
fi

# Step 3: Check and install CMake
echo ""
log_info "Step 3: Checking CMake..."

if command -v cmake &> /dev/null; then
    CMAKE_VERSION=$(cmake --version | head -n 1)
    log_success "CMake already installed: $CMAKE_VERSION"

    # Check version (need 3.8+)
    CMAKE_VERSION_NUM=$(cmake --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1)
    CMAKE_MAJOR=$(echo "$CMAKE_VERSION_NUM" | cut -d. -f1)
    CMAKE_MINOR=$(echo "$CMAKE_VERSION_NUM" | cut -d. -f2)

    if [[ $CMAKE_MAJOR -lt 3 ]] || [[ $CMAKE_MAJOR -eq 3 && $CMAKE_MINOR -lt 8 ]]; then
        log_warning "CMake version $CMAKE_VERSION_NUM is too old (need 3.8+). Upgrading..."
        brew upgrade cmake
        log_success "CMake upgraded to $(cmake --version | head -n 1)"
    fi
else
    log_warning "CMake not found. Installing..."

    brew install cmake

    # Verify installation
    if command -v cmake &> /dev/null; then
        CMAKE_VERSION=$(cmake --version | head -n 1)
        log_success "CMake installed successfully: $CMAKE_VERSION"
    else
        log_error "CMake installation failed"
        exit 1
    fi
fi

# Step 4: Check Python version
echo ""
log_info "Step 4: Checking Python version..."

if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    log_success "Python3 found: $PYTHON_VERSION"

    # Check version (need 3.7+)
    PYTHON_VERSION_NUM=$(python3 --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+')
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION_NUM" | cut -d. -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION_NUM" | cut -d. -f2)

    if [[ $PYTHON_MAJOR -lt 3 ]] || [[ $PYTHON_MAJOR -eq 3 && $PYTHON_MINOR -lt 7 ]]; then
        log_error "Python version $PYTHON_VERSION_NUM is too old (need 3.7+)"
        log_error "Please upgrade Python and run this script again"
        exit 1
    fi
else
    log_error "Python3 not found"
    log_error "Please install Python 3.7+ from https://www.python.org/downloads/"
    exit 1
fi

# Step 5: Create and activate virtual environment
echo ""
log_info "Step 5: Setting up virtual environment..."

VENV_DIR="$PROJECT_ROOT/venv"

if [[ -d "$VENV_DIR" ]]; then
    log_success "Virtual environment already exists at: $VENV_DIR"

    # Check if it's valid
    if [[ -f "$VENV_DIR/bin/activate" ]]; then
        log_success "Virtual environment is valid"
    else
        log_warning "Virtual environment appears corrupted. Recreating..."
        rm -rf "$VENV_DIR"
        python3 -m venv "$VENV_DIR"
        log_success "Virtual environment recreated"
    fi
else
    log_info "Creating virtual environment..."
    python3 -m venv "$VENV_DIR"
    log_success "Virtual environment created at: $VENV_DIR"
fi

# Activate virtual environment
log_info "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Verify activation
if [[ "$VIRTUAL_ENV" != "" ]]; then
    log_success "Virtual environment activated: $VIRTUAL_ENV"
else
    log_error "Failed to activate virtual environment"
    exit 1
fi

# Step 6: Upgrade pip
echo ""
log_info "Step 6: Upgrading pip..."

CURRENT_PIP_VERSION=$(pip --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1)
log_info "Current pip version: $CURRENT_PIP_VERSION"

pip install --upgrade pip --quiet

NEW_PIP_VERSION=$(pip --version | grep -oE '[0-9]+\.[0-9]+\.[0-9]+' | head -n 1)
if [[ "$CURRENT_PIP_VERSION" != "$NEW_PIP_VERSION" ]]; then
    log_success "pip upgraded from $CURRENT_PIP_VERSION to $NEW_PIP_VERSION"
else
    log_success "pip is already up to date: $NEW_PIP_VERSION"
fi

# Step 7: Install face_recognition
echo ""
log_info "Step 7: Installing face_recognition library..."
log_warning "This may take several minutes as it compiles dlib..."

# Check if already installed
if python -c "import face_recognition" &> /dev/null; then
    FACE_REC_VERSION=$(python -c "import face_recognition; print(face_recognition.__version__)" 2>/dev/null || echo "unknown")
    log_info "face_recognition is already installed (version: $FACE_REC_VERSION)"

    read -p "Do you want to reinstall/upgrade? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        log_info "Skipping face_recognition installation"
    else
        log_info "Reinstalling face_recognition..."
        pip install --upgrade face-recognition
        log_success "face_recognition reinstalled"
    fi
else
    log_info "Installing face_recognition (this will also install dlib, numpy, and Pillow)..."

    # Install with progress
    pip install face-recognition

    log_success "face_recognition installation completed"
fi

# Step 8: Verify installation
echo ""
log_info "Step 8: Verifying installation..."

echo ""
log_info "Testing face_recognition import..."
if python -c "import face_recognition; print('face_recognition version:', face_recognition.__version__)" 2>&1; then
    log_success "face_recognition is working correctly"
else
    log_error "face_recognition import failed"
    exit 1
fi

echo ""
log_info "Testing dlib import..."
if python -c "import dlib; print('dlib version:', dlib.__version__)" 2>&1; then
    log_success "dlib is working correctly"
else
    log_error "dlib import failed"
    exit 1
fi

echo ""
log_info "Testing numpy import..."
if python -c "import numpy; print('numpy version:', numpy.__version__)" 2>&1; then
    log_success "numpy is working correctly"
else
    log_error "numpy import failed"
    exit 1
fi

echo ""
log_info "Testing Pillow import..."
if python -c "from PIL import Image; print('Pillow is working')" 2>&1; then
    log_success "Pillow is working correctly"
else
    log_error "Pillow import failed"
    exit 1
fi

# Step 9: Check for requirements.txt and verify all dependencies
echo ""
log_info "Step 9: Checking project dependencies..."

if [[ -f "$PROJECT_ROOT/requirements.txt" ]]; then
    log_info "Found requirements.txt. Installing all project dependencies..."
    pip install -r "$PROJECT_ROOT/requirements.txt" --quiet
    log_success "All project dependencies installed"
else
    log_warning "No requirements.txt found. Skipping project dependencies."
fi

# Summary
echo ""
echo "=============================================="
echo "  Installation Summary"
echo "=============================================="
echo ""

if [[ "$OVERALL_SUCCESS" == true ]]; then
    log_success "All installation steps completed successfully!"
    echo ""
    echo "Next steps:"
    echo "  1. Activate the virtual environment:"
    echo "     ${BLUE}source venv/bin/activate${NC}"
    echo ""
    echo "  2. Copy and configure the config file:"
    echo "     ${BLUE}cp config/config.example.yaml config/config.yaml${NC}"
    echo ""
    echo "  3. Create reference photos directory:"
    echo "     ${BLUE}mkdir -p reference_photos${NC}"
    echo ""
    echo "  4. Add reference photos of the person to detect"
    echo ""
    echo "  5. See docs/FACE_RECOGNITION_LOCAL_SETUP.md for more details"
    echo ""
else
    log_error "Installation completed with errors. Please review the messages above."
    exit 1
fi
