# Python Application Setup Proposal

## Executive Summary

This document proposes a transformation of the current script-based structure into a proper Python application package. This will improve maintainability, simplify imports, enable proper installation, and follow Python packaging best practices.

## Current State Analysis

### Directory Structure

```
dropboxFamilyPhotoOrganizer/
├── scripts/                      # Main code directory (NOT a package)
│   ├── auth/                     # OAuth and authentication (IS a package)
│   ├── face_recognizer/          # Face recognition providers (IS a package)
│   ├── aws_tests/                # AWS-specific tests (NOT in tests/)
│   ├── github/                   # GitHub automation scripts
│   ├── installation/             # Installation scripts
│   ├── dropbox_client.py         # Core Dropbox integration
│   ├── logging_utils.py          # Logging utilities
│   ├── metrics.py                # Metrics collection
│   ├── organize_photos.py        # Main photo organizer
│   ├── train_face_model.py       # Face model training
│   ├── authorize_dropbox.py      # OAuth authorization
│   ├── test_dropbox_connection.py # Connection testing
│   ├── check_account.py          # Account verification
│   ├── list_folders.py           # Folder listing
│   └── debug_dashboard.py        # Debug web dashboard
├── tests/                        # Unit tests
├── config/                       # Configuration files
├── docs/                         # Documentation
├── requirements.txt              # Dependencies
└── pyproject.toml               # Tool configuration (no package metadata)
```

### Key Issues

1. **Import Path Manipulation**: Every script uses `sys.path.insert()` to enable imports
   ```python
   sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
   from scripts.dropbox_client import DropboxClient
   ```

2. **No Package Installation**: Cannot install with `pip install -e .`

3. **Inconsistent Module Organization**:
   - `auth/` and `face_recognizer/` are proper packages
   - Top-level scripts are not in a package
   - `aws_tests/` contains tests but lives in scripts/

4. **No Entry Points**: CLI tools must be run with full paths
   ```bash
   python scripts/organize_photos.py
   ```

5. **Test Imports**: Tests duplicate path manipulation
   ```python
   sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
   ```

6. **No Package Metadata**: pyproject.toml only has tool configuration, no project metadata

## Proposed Solution

### New Directory Structure

```
dropboxFamilyPhotoOrganizer/
├── src/
│   └── photo_organizer/          # Main package (renamed from scripts)
│       ├── __init__.py           # Package initialization
│       ├── __main__.py           # Entry point for `python -m photo_organizer`
│       ├── auth/                 # OAuth and authentication
│       ├── face_recognizer/      # Face recognition providers
│       ├── cli/                  # CLI commands (new)
│       │   ├── __init__.py
│       │   ├── organize.py       # organize-photos command
│       │   ├── authorize.py      # authorize-dropbox command
│       │   ├── train.py          # train-face-model command
│       │   ├── test_connection.py # test-dropbox command
│       │   ├── check_account.py  # check-account command
│       │   ├── list_folders.py   # list-folders command
│       │   └── debug_dashboard.py # debug-dashboard command
│       ├── dropbox_client.py     # Core Dropbox integration
│       ├── logging_utils.py      # Logging utilities
│       ├── metrics.py            # Metrics collection
│       └── utils/                # Utility modules (new)
│           └── __init__.py
├── tests/                        # Unit tests (no path manipulation needed)
│   ├── integration/              # Integration tests (new)
│   │   ├── __init__.py
│   │   ├── test_aws_connection.py     # Moved from scripts/aws_tests
│   │   └── test_aws_reference.py      # Moved from scripts/aws_tests
│   └── unit/                     # Unit tests (existing tests moved here)
├── scripts/                      # Utility scripts ONLY (shell, setup)
│   ├── github/                   # GitHub automation
│   └── installation/             # Installation scripts
├── config/                       # Configuration files
├── docs/                         # Documentation
├── requirements.txt              # Runtime dependencies
├── requirements-dev.txt          # Development dependencies
├── requirements-aws.txt          # AWS provider dependencies
├── requirements-azure.txt        # Azure provider dependencies
└── pyproject.toml               # Full project configuration + metadata
```

### Key Changes

#### 1. Proper Package Structure

**Create `src/photo_organizer/` as main package**:
- Follows src-layout best practice
- Prevents accidental imports from source
- Clear separation from tests

**Add `__init__.py` with version**:
```python
"""Dropbox Family Photo Organizer."""

__version__ = "0.1.0"
__all__ = ["DropboxClient", "get_provider"]

from photo_organizer.dropbox_client import DropboxClient
from photo_organizer.face_recognizer import get_provider
```

#### 2. Add Project Metadata to pyproject.toml

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "photo-organizer"
version = "0.1.0"
description = "Automatically scan Dropbox photos and organize them using face recognition"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "Your Name", email = "your.email@example.com"}
]
keywords = ["dropbox", "face-recognition", "photos", "automation"]
classifiers = [
    "Development Status :: 3 - Alpha",
    "Intended Audience :: End Users/Desktop",
    "License :: OSI Approved :: MIT License",
    "Programming Language :: Python :: 3",
    "Programming Language :: Python :: 3.10",
    "Programming Language :: Python :: 3.11",
    "Programming Language :: Python :: 3.12",
]

dependencies = [
    "dropbox>=11.36.0",
    "PyYAML>=6.0",
    "python-dateutil>=2.8.0",
    "numpy>=1.21.0",
    "keyring>=24.0.0",
    "Pillow>=10.0.0",
]

[project.optional-dependencies]
local = [
    "face-recognition>=1.3.0",
    "dlib>=19.24.0",
]
aws = [
    "boto3>=1.26.0",
]
azure = [
    "azure-cognitiveservices-vision-face>=0.6.0",
    "msrest>=0.7.0",
]
dev = [
    "pytest>=7.0.0",
    "pytest-cov>=4.0.0",
    "pytest-mock>=3.10.0",
    "black>=23.0.0",
    "isort>=5.12.0",
    "flake8>=6.0.0",
    "mypy>=1.0.0",
    "pre-commit>=3.0.0",
    "bandit>=1.7.0",
    "safety>=2.3.0",
]

[project.urls]
Homepage = "https://github.com/amendez13/dropboxFamilyPhotoOrganizer"
Documentation = "https://github.com/amendez13/dropboxFamilyPhotoOrganizer/tree/main/docs"
Repository = "https://github.com/amendez13/dropboxFamilyPhotoOrganizer"
Issues = "https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues"

[project.scripts]
organize-photos = "photo_organizer.cli.organize:main"
authorize-dropbox = "photo_organizer.cli.authorize:main"
train-face-model = "photo_organizer.cli.train:main"
test-dropbox = "photo_organizer.cli.test_connection:main"
check-account = "photo_organizer.cli.check_account:main"
list-folders = "photo_organizer.cli.list_folders:main"
debug-dashboard = "photo_organizer.cli.debug_dashboard:main"

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]

# ... existing tool configurations (black, isort, pytest, mypy, coverage)
```

#### 3. Console Scripts (Entry Points)

After installation, users can run:
```bash
organize-photos --verbose
authorize-dropbox
train-face-model
test-dropbox
```

Instead of:
```bash
python scripts/organize_photos.py --verbose
python scripts/authorize_dropbox.py
python scripts/train_face_model.py
python scripts/test_dropbox_connection.py
```

#### 4. Remove All sys.path.insert() Statements

**Before**:
```python
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from scripts.dropbox_client import DropboxClient
```

**After**:
```python
from photo_organizer.dropbox_client import DropboxClient
```

#### 5. Reorganize Tests

Move tests into organized structure:
```
tests/
├── __init__.py
├── conftest.py              # Shared fixtures
├── unit/                    # Unit tests
│   ├── __init__.py
│   ├── test_dropbox_client.py
│   ├── test_auth.py
│   ├── test_face_recognizer.py
│   └── ...
└── integration/             # Integration tests
    ├── __init__.py
    ├── test_aws_connection.py
    └── test_aws_reference.py
```

Tests will import directly:
```python
from photo_organizer.dropbox_client import DropboxClient
```

#### 6. Update Installation Process

**Development Installation**:
```bash
# Clone repository
git clone https://github.com/amendez13/dropboxFamilyPhotoOrganizer.git
cd dropboxFamilyPhotoOrganizer

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install in editable mode with all providers and dev tools
pip install -e ".[local,aws,azure,dev]"

# Or install only what you need
pip install -e ".[local,dev]"    # Local provider + dev tools
pip install -e ".[aws,dev]"      # AWS provider + dev tools
```

**Production Installation** (future):
```bash
pip install photo-organizer[aws]  # From PyPI (when published)
```

## Benefits

### 1. Cleaner Imports
- No more `sys.path.insert()` hacks
- Clear module hierarchy
- IDE autocomplete works better

### 2. Proper Installation
- `pip install -e .` for development
- Eventually publish to PyPI
- Dependency management through pip

### 3. Entry Points
- Commands available in PATH
- Cross-platform (Windows, macOS, Linux)
- Consistent with other Python tools

### 4. Better Testing
- Tests import normally
- No path manipulation needed
- Easier to run with pytest

### 5. Professional Structure
- Follows Python packaging best practices
- Matches popular projects (requests, flask, etc.)
- Easier for contributors

### 6. Distribution Ready
- Can build wheels: `python -m build`
- Can publish to PyPI: `twine upload dist/*`
- Users can install with pip

## Migration Strategy

### Phase 1: Planning ✅
- [x] Analyze current structure
- [x] Create detailed proposal
- [ ] Review and approve proposal

### Phase 2: Structure Setup
- [ ] Create `src/photo_organizer/` directory
- [ ] Add `__init__.py` with version and exports
- [ ] Update pyproject.toml with project metadata
- [ ] Add console_scripts entry points

### Phase 3: Move Code
- [ ] Move all modules from `scripts/` to `src/photo_organizer/`
- [ ] Create `cli/` subdirectory for CLI commands
- [ ] Reorganize tests into `unit/` and `integration/`
- [ ] Keep only shell scripts in `scripts/`

### Phase 4: Update Imports
- [ ] Remove all `sys.path.insert()` statements
- [ ] Update imports to use `photo_organizer.*`
- [ ] Update tests to import from package
- [ ] Update CLI scripts to use new structure

### Phase 5: Testing
- [ ] Run full test suite
- [ ] Verify all CLI commands work
- [ ] Test installation in clean environment
- [ ] Update CI/CD to use new structure

### Phase 6: Documentation
- [ ] Update README.md with new installation steps
- [ ] Update CLAUDE.md with new structure
- [ ] Update all docs/ files
- [ ] Add migration guide for existing users

## Backward Compatibility

### Maintaining Old Scripts (Temporary)

Keep old `scripts/` structure temporarily with deprecation warnings:

```python
# scripts/organize_photos.py (deprecated wrapper)
"""
DEPRECATED: This script has moved to a package structure.
Please use: organize-photos (after pip install -e .)
Or: python -m photo_organizer.cli.organize
"""
import sys
import warnings

warnings.warn(
    "scripts/organize_photos.py is deprecated. "
    "Use 'organize-photos' command after installation.",
    DeprecationWarning,
    stacklevel=2
)

# Delegate to new location
from photo_organizer.cli.organize import main

if __name__ == "__main__":
    main()
```

Remove deprecated wrappers after 1-2 releases.

## Alternative Approaches Considered

### Alternative 1: Keep scripts/ as package (No src layout)
**Pros**: Less moving
**Cons**: Can accidentally import from source, not best practice

### Alternative 2: Flat structure (All in root)
**Pros**: Simple
**Cons**: Messy, mixes code with config/docs

### Alternative 3: Rename scripts/ to photo_organizer/ (No src/)
**Pros**: Simpler than src layout
**Cons**: Can still import from development directory

**Decision**: Use src layout (Proposed Solution) - Best practice, prevents import issues

## Implementation Risks and Mitigations

### Risk 1: Breaking CI/CD
**Mitigation**: Update CI workflow incrementally, test each change

### Risk 2: Breaking User Installations
**Mitigation**: Maintain backward compatibility wrappers, document migration

### Risk 3: Import Errors
**Mitigation**: Comprehensive testing, update all imports systematically

### Risk 4: Documentation Outdated
**Mitigation**: Update docs in same PR, use scripts to find references

## Success Criteria

- [ ] Can install with `pip install -e .`
- [ ] All CLI commands work as console scripts
- [ ] No `sys.path.insert()` statements remain
- [ ] All tests pass with new structure
- [ ] CI/CD pipeline works
- [ ] Documentation is updated
- [ ] Can build wheel: `python -m build`

## Timeline Estimate

- **Phase 1** (Planning): 0.5 days ✅
- **Phase 2** (Structure): 0.5 days
- **Phase 3** (Move Code): 1 day
- **Phase 4** (Update Imports): 1 day
- **Phase 5** (Testing): 1 day
- **Phase 6** (Documentation): 0.5 days

**Total**: ~4-5 days for complete migration

## Recommendations

1. **Approve this proposal** before implementation
2. **Create a feature branch** for the migration
3. **Implement in phases** with incremental commits
4. **Keep old scripts temporarily** for backward compatibility
5. **Update documentation** as part of the same PR
6. **Test thoroughly** before merging

## Questions for Review

1. Should we keep the name `photo_organizer` or use `dropbox_photo_organizer`?
2. Should we rename the repository to match the package name?
3. Should we publish to PyPI immediately or wait for v1.0?
4. Should we maintain backward compatibility wrappers, and for how long?
5. Any specific import patterns or naming conventions to preserve?

## References

- [Python Packaging Guide](https://packaging.python.org/en/latest/)
- [Setuptools Documentation](https://setuptools.pypa.io/en/latest/)
- [src Layout vs Flat Layout](https://packaging.python.org/en/latest/discussions/src-layout-vs-flat-layout/)
- [PEP 518 - pyproject.toml](https://peps.python.org/pep-0518/)
- [PEP 621 - Project Metadata](https://peps.python.org/pep-0621/)
