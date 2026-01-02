#!/bin/bash

# macOS Face Recognition Setup Script
# Automates the installation steps from docs/FACE_RECOGNITION_LOCAL_SETUP.md
# for macOS systems

set -e  # Exit on error

# Parse command line arguments
FORCE_RECREATE=false
NON_INTERACTIVE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --force|-f)
            FORCE_RECREATE=true
            shift
            ;;
        --yes|-y)
            NON_INTERACTIVE=true
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  -f, --force          Force recreate virtual environment if it exists"
            echo "  -y, --yes            Non-interactive mode (auto-answer yes to prompts)"
            echo "  -h, --help           Show this help message"
            echo ""
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print colored messages
print_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1 (line $BASH_LINENO)" >&2
}

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to compare version numbers
version_ge() {
    # Returns 0 (true) if $1 >= $2
    printf '%s\n%s\n' "$2" "$1" | sort -V -C
}

# Trap errors and provide helpful messages
trap 'print_error "Installation failed at step: $BASH_COMMAND"' ERR

print_info "Starting macOS Face Recognition setup..."
echo ""

# Step 1: Check for Xcode Command Line Tools
print_info "Step 1: Checking Xcode Command Line Tools..."
if xcode-select -p >/dev/null 2>&1; then
    print_success "Xcode Command Line Tools already installed"
else
    print_warning "Xcode Command Line Tools not found"
    print_info "Please install Xcode Command Line Tools:"
    print_info "  1. Run: xcode-select --install"
    print_info "  2. Follow the prompts to install"
    print_info "  3. Re-run this script after installation"
    exit 1
fi

# Step 2: Check for Homebrew
print_info "Step 2: Checking Homebrew..."
if command_exists brew; then
    print_success "Homebrew already installed"
else
    print_warning "Homebrew not found. Installing..."
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

    # Add Homebrew to PATH for Apple Silicon Macs
    if [[ $(uname -m) == 'arm64' ]]; then
        print_info "Detected Apple Silicon Mac. Adding Homebrew to PATH..."
        # Only add to .zprofile if not already present
        if ! grep -q '/opt/homebrew/bin/brew shellenv' ~/.zprofile 2>/dev/null; then
            echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
        fi
        eval "$(/opt/homebrew/bin/brew shellenv)"
    fi

    if command_exists brew; then
        print_success "Homebrew installed successfully"
    else
        print_error "Homebrew installation failed"
        exit 1
    fi
fi

# Step 3: Check for CMake
print_info "Step 3: Checking CMake..."
if command_exists cmake; then
    CMAKE_VERSION=$(cmake --version | head -n1 | cut -d' ' -f3)
    print_info "Found CMake version $CMAKE_VERSION"

    if version_ge "$CMAKE_VERSION" "3.8.0"; then
        print_success "CMake version is sufficient (>= 3.8.0)"
    else
        print_warning "CMake version $CMAKE_VERSION is too old. Upgrading..."
        brew upgrade cmake
        print_success "CMake upgraded"
    fi
else
    print_warning "CMake not found. Installing..."
    brew install cmake

    if command_exists cmake; then
        CMAKE_VERSION=$(cmake --version | head -n1 | cut -d' ' -f3)
        print_success "CMake $CMAKE_VERSION installed successfully"
    else
        print_error "CMake installation failed"
        exit 1
    fi
fi

# Step 4: Check Python version and install Python 3.12 if needed
print_info "Step 4: Checking Python version..."

# Check for Python 3.12 specifically (best compatibility with dlib)
PYTHON_CMD="python3"
if command_exists python3.12; then
    PYTHON_CMD="python3.12"
    PYTHON_VERSION=$(python3.12 --version | cut -d' ' -f2)
    print_info "Found Python 3.12 version $PYTHON_VERSION"
    print_success "Python 3.12 is installed (recommended for dlib compatibility)"
elif command_exists python3; then
    PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
    PYTHON_MAJOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f1)
    PYTHON_MINOR=$(echo "$PYTHON_VERSION" | cut -d'.' -f2)

    print_info "Found Python version $PYTHON_VERSION"

    # Check if Python 3.13+ (has dlib compilation issues)
    if [[ "$PYTHON_MAJOR" -eq 3 && "$PYTHON_MINOR" -ge 13 ]]; then
        print_warning "Python 3.13+ has known compatibility issues with dlib compilation"
        print_info "Installing Python 3.12 for better compatibility..."

        brew install python@3.12

        if command_exists python3.12; then
            PYTHON_CMD="python3.12"
            PYTHON_VERSION=$(python3.12 --version | cut -d' ' -f2)
            print_success "Python 3.12 installed successfully"
        else
            print_error "Failed to install Python 3.12"
            exit 1
        fi
    elif version_ge "$PYTHON_VERSION" "3.7.0"; then
        print_success "Python version is sufficient (>= 3.7)"
    else
        print_error "Python version $PYTHON_VERSION is too old. Python 3.7+ required."
        print_info "Install a newer Python version and re-run this script"
        exit 1
    fi
else
    print_error "Python 3 not found. Installing Python 3.12..."
    brew install python@3.12

    if command_exists python3.12; then
        PYTHON_CMD="python3.12"
        PYTHON_VERSION=$(python3.12 --version | cut -d' ' -f2)
        print_success "Python 3.12 installed successfully"
    else
        print_error "Failed to install Python 3.12"
        exit 1
    fi
fi

print_info "Using Python: $PYTHON_CMD ($PYTHON_VERSION)"

# Step 5: Create virtual environment
print_info "Step 5: Setting up virtual environment..."
if [ -d "venv" ]; then
    print_warning "Virtual environment already exists at ./venv"

    RECREATE=false
    if [ "$FORCE_RECREATE" = true ] || [ "$NON_INTERACTIVE" = true ]; then
        RECREATE=true
    else
        read -p "Do you want to recreate it? (y/N): " -n 1 -r
        echo
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            RECREATE=true
        fi
    fi

    if [ "$RECREATE" = true ]; then
        print_info "Removing existing virtual environment..."
        rm -rf venv
        print_info "Creating new virtual environment with $PYTHON_CMD..."
        $PYTHON_CMD -m venv venv
        print_success "Virtual environment recreated"
    else
        print_info "Using existing virtual environment"
        print_warning "Note: Existing venv may be using a different Python version"
    fi
else
    print_info "Creating virtual environment with $PYTHON_CMD..."
    $PYTHON_CMD -m venv venv
    print_success "Virtual environment created"
fi

# Activate virtual environment
print_info "Activating virtual environment..."
source venv/bin/activate

if [[ "$VIRTUAL_ENV" != "" ]]; then
    print_success "Virtual environment activated: $VIRTUAL_ENV"
else
    print_error "Failed to activate virtual environment"
    exit 1
fi

# Step 6: Upgrade pip
print_info "Step 6: Upgrading pip..."
pip install --upgrade pip --quiet
PIP_VERSION=$(pip --version | cut -d' ' -f2)
print_success "pip upgraded to version $PIP_VERSION"

# Step 7: Install face_recognition library
print_info "Step 7: Installing face_recognition library..."
print_warning "This may take several minutes as it compiles dlib from source..."

# First, ensure setuptools is installed (required for face_recognition_models)
print_info "Installing setuptools (required for face_recognition_models)..."
pip install setuptools --quiet

# Try to install face-recognition (which includes dlib)
print_info "Installing face-recognition..."
if ! pip install face-recognition 2>/dev/null; then
    print_warning "Failed to compile dlib from source. Trying alternative method..."

    # Try installing dlib via Homebrew as a fallback
    print_info "Installing dlib via Homebrew..."
    if ! brew list dlib &>/dev/null; then
        brew install dlib
    fi

    # Install other dependencies first
    print_info "Installing face-recognition dependencies..."
    pip install numpy Pillow Click face-recognition-models

    # Try face-recognition again
    print_info "Retrying face-recognition installation..."
    if ! pip install --no-build-isolation face-recognition 2>/dev/null; then
        print_error "Failed to install face-recognition even with Homebrew dlib"
        print_info "This may be due to Python version incompatibility"
        print_info "Consider using Python 3.11 or 3.12 instead"
        exit 1
    fi
fi

print_info "Verifying installation..."

# Verify face_recognition
if python -c "import face_recognition" 2>/dev/null; then
    FR_VERSION=$(python -c "import face_recognition; print(face_recognition.__version__)" 2>/dev/null || echo "unknown")
    print_success "face_recognition installed (version: $FR_VERSION)"
else
    print_error "face_recognition installation verification failed"
    exit 1
fi

# Verify dlib
if python -c "import dlib" 2>/dev/null; then
    DLIB_VERSION=$(python -c "import dlib; print(dlib.__version__)" 2>/dev/null || echo "unknown")
    print_success "dlib installed (version: $DLIB_VERSION)"
else
    print_error "dlib installation verification failed"
    exit 1
fi

# Verify numpy
if python -c "import numpy" 2>/dev/null; then
    NUMPY_VERSION=$(python -c "import numpy; print(numpy.__version__)" 2>/dev/null || echo "unknown")
    print_success "numpy installed (version: $NUMPY_VERSION)"
else
    print_error "numpy installation verification failed"
    exit 1
fi

# Verify Pillow
if python -c "import PIL" 2>/dev/null; then
    PIL_VERSION=$(python -c "import PIL; print(PIL.__version__)" 2>/dev/null || echo "unknown")
    print_success "Pillow installed (version: $PIL_VERSION)"
else
    print_error "Pillow installation verification failed"
    exit 1
fi

# Step 8: Install project requirements if requirements.txt exists
if [ -f "requirements.txt" ]; then
    print_info "Step 8: Installing additional project requirements..."
    pip install -r requirements.txt --quiet
    print_success "Project requirements installed"
else
    print_info "Step 8: No requirements.txt found, skipping..."
fi

echo ""
print_success "================================================"
print_success "Face Recognition setup completed successfully!"
print_success "================================================"
echo ""
print_info "Next steps:"
echo "  1. Activate the virtual environment:"
echo "     ${BLUE}source venv/bin/activate${NC}"
echo ""
echo "  2. Copy and configure the config file:"
echo "     ${BLUE}cp config/config.example.yaml config/config.yaml${NC}"
echo "     ${BLUE}# Edit config/config.yaml with your settings${NC}"
echo ""
echo "  3. Create reference photos directory:"
echo "     ${BLUE}mkdir -p reference_photos${NC}"
echo ""
echo "  4. Add reference photos of the person to detect:"
echo "     ${BLUE}cp /path/to/your/photos/*.jpg reference_photos/${NC}"
echo ""
echo "  5. See ${BLUE}docs/FACE_RECOGNITION_LOCAL_SETUP.md${NC} for testing and usage"
echo ""
