# Continuous Integration (CI) Pipeline

This document details the CI/CD pipeline setup for the Dropbox Family Photo Organizer project using GitHub Actions.

## Overview

The CI pipeline automatically runs quality checks, tests, and security scans on every push and pull request to ensure code quality and prevent regressions. All checks must pass before code can be merged to the main branch.

## Pipeline Architecture

### Workflow File

Location: `.github/workflows/ci.yml`

**Triggers:**
- Push to `main` or `develop` branches
- Pull requests targeting `main` or `develop` branches

### CI Jobs

The pipeline consists of 6 independent jobs that run in parallel:

1. **Lint and Code Quality**
2. **Testing** (matrix across Python versions)
3. **Coverage Check** (non-voting)
4. **Security Checks**
5. **Configuration Validation**
6. **Build Status Check** (runs after all other jobs)

## Job Details

### 1. Lint and Code Quality

Ensures consistent code style and catches common errors.

**Tools Used:**
- **Black** - Code formatter
- **isort** - Import statement organizer
- **flake8** - Linting and style guide enforcement
- **mypy** - Static type checking

**Checks Performed:**
```bash
# Code formatting (Black)
black --check --diff scripts/

# Import sorting (isort)
isort --check-only --diff scripts/

# Linting (flake8)
flake8 scripts/ --count --select=E9,F63,F7,F82  # Critical errors
flake8 scripts/ --count --exit-zero --max-complexity=10

# Type checking (mypy)
mypy scripts/ --ignore-missing-imports
```

**Configuration Files:**
- `.flake8` - Flake8 settings
- `.pylintrc` - Pylint configuration
- `pyproject.toml` - Black, isort, and mypy settings

### 2. Testing

Runs the test suite across multiple Python versions to ensure compatibility.

**Test Matrix:**
- Python 3.10
- Python 3.11
- Python 3.12

**Tools Used:**
- **pytest** - Test framework
- **pytest-cov** - Coverage reporting
- **pytest-mock** - Mocking utilities

**Commands:**
```bash
# Run tests with coverage
pytest tests/ -v --cov=scripts --cov-report=xml --cov-report=term-missing

# Upload coverage to Codecov (Python 3.12 only)
# Requires CODECOV_TOKEN secret to be configured
```

**Test Configuration:**
- Located in `pyproject.toml` under `[tool.pytest.ini_options]`
- Test directory: `tests/`
- Coverage source: `scripts/`

**Current Test Suite:**
- `tests/test_basic.py` - Basic validation tests
  - Python version validation
  - Dependency import checks
  - Configuration file validation

### 3. Coverage Check (Voting)

Monitors code coverage with a 95% target. This check is **voting** - builds will fail if coverage is below the threshold.

**Target:** 95% code coverage

**Status:** Required (blocks merges if below threshold)

**Tools Used:**
- **pytest-cov** - Coverage measurement
- **coverage.py** - Coverage reporting

**Commands:**
```bash
# Run tests with coverage and fail if below threshold
pytest tests/ -v --cov=scripts --cov-report=term-missing --cov-report=html --cov-fail-under=95
```

**Configuration:**
Located in `pyproject.toml` under `[tool.coverage.run]` and `[tool.coverage.report]`

**Whitelisting Files:**
Files that are difficult to unit test (e.g., interactive CLI scripts, cloud providers requiring external services) can be excluded from coverage requirements:

```toml
[tool.coverage.run]
omit = [
    # Interactive CLI scripts
    "scripts/authorize_dropbox.py",
    "scripts/check_account.py",
    # Cloud providers (require external services)
    "scripts/face_recognizer/providers/aws_provider.py",
    "scripts/face_recognizer/providers/azure_provider.py",
]
```

**Whitelisting Code Patterns:**
Specific code patterns can be excluded using `exclude_lines`:

```toml
[tool.coverage.report]
exclude_lines = [
    "pragma: no cover",          # Explicit exclusion comment
    "if __name__ == .__main__.:", # Main blocks
    "def main\\(\\):",            # Main entry points
    "@abstractmethod",            # Abstract methods
]
```

**Inline Exclusion:**
Use `# pragma: no cover` to exclude specific lines:

```python
def debug_only_function():  # pragma: no cover
    """This function is excluded from coverage."""
    pass
```

**Coverage Artifacts:**
The HTML coverage report is uploaded as an artifact and retained for 14 days. Download from the Actions run summary page.

### 4. Security Checks

Scans for security vulnerabilities in code and dependencies. **Security checks are blocking** - builds will fail if vulnerabilities are found.

**Tools Used:**
- **bandit** - Security vulnerability scanner for Python code
- **pip-audit** - Checks for known security vulnerabilities in dependencies (replaced deprecated `safety` tool)

**Commands:**
```bash
# Scan code for security issues (medium and higher severity)
bandit -r scripts/ -ll

# Check dependencies for known vulnerabilities
pip-audit --requirement requirements.txt
```

**Handling False Positives:**
- Use `# nosec BXXX` inline comments to suppress false positives
- Always include a brief justification in the comment
- Example: `token_access_type="offline",  # nosec B106 - Request refresh token`

### 5. Configuration Validation

Validates configuration files and Python syntax.

**Checks:**
1. **YAML Validation** - Ensures `config/config.example.yaml` is valid YAML
2. **Python Syntax** - Validates all Python files compile correctly

**Commands:**
```bash
# Validate YAML
python -c "import yaml; yaml.safe_load(open('config/config.example.yaml'))"

# Check Python syntax
python -m py_compile scripts/**/*.py
```

### 6. Integration Tests

Tests actual Dropbox API connectivity using GitHub Secrets.

**When It Runs:**
- Only on pushes to `main` branch (not on PRs)
- Only when `RUN_INTEGRATION_TESTS` variable is set to `true`
- Requires GitHub Secrets to be configured

**What It Tests:**
- Dropbox authentication with access token
- Source folder accessibility
- File listing capability
- Thumbnail download functionality

**Configuration Required:**
See [GitHub Secrets Setup](#github-secrets-setup) section below for configuration instructions.

### 7. Build Status Check

Final job that verifies all required checks passed.

**Dependencies:** lint, test, security, validate-config

**Behavior:**
- ✅ Passes if all dependent jobs succeed
- ❌ Fails if any required job fails (including security checks)
- ⚠️ Coverage check is non-voting and does not affect build status

## Configuration Files

### `.flake8`

Flake8 linting configuration.

**Key Settings:**
```ini
max-line-length = 127
max-complexity = 10
exclude = .git, __pycache__, venv, .venv, build, dist, *.egg-info
ignore = W503, W504  # Line break before/after binary operators
```

### `.pylintrc`

Pylint configuration (optional, not used in CI currently).

**Key Settings:**
```ini
max-line-length = 127
max-args = 7
max-locals = 15
disable = C0111, C0103, R0903, R0913, W0212
```

### `pyproject.toml`

Unified configuration for multiple tools.

**Black Settings:**
```toml
[tool.black]
line-length = 127
target-version = ['py310', 'py311', 'py312']
```

**isort Settings:**
```toml
[tool.isort]
profile = "black"
line_length = 127
```

**pytest Settings:**
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = ["--verbose", "--strict-markers", "--disable-warnings"]
```

**mypy Settings:**
```toml
[tool.mypy]
python_version = "3.10"
warn_return_any = true
ignore_missing_imports = true
```

**Coverage Settings:**
```toml
[tool.coverage.run]
source = ["scripts"]
omit = ["*/tests/*", "*/venv/*"]
```

## Development Dependencies

Location: `requirements-dev.txt`

**Testing:**
- pytest>=7.4.0
- pytest-cov>=4.1.0
- pytest-mock>=3.11.0

**Code Quality:**
- black>=23.7.0
- isort>=5.12.0
- flake8>=6.1.0
- pylint>=2.17.0
- mypy>=1.5.0

**Security:**
- bandit>=1.7.5
- pip-audit>=2.7.0

## Running CI Checks Locally

Before pushing code, run these commands locally to catch issues early:

### Install Development Dependencies

```bash
pip install -r requirements-dev.txt
```

### Format Code

```bash
# Auto-format with Black
black scripts/

# Sort imports
isort scripts/
```

### Run Linting

```bash
# Flake8 (syntax and style)
flake8 scripts/

# Pylint (optional, more detailed)
pylint scripts/

# Type checking
mypy scripts/
```

### Run Tests

```bash
# Run all tests
pytest tests/ -v

# Run with coverage
pytest tests/ -v --cov=scripts --cov-report=term-missing

# Run specific test file
pytest tests/test_basic.py -v
```

### Security Scans

```bash
# Scan code for security issues (medium and higher severity)
bandit -r scripts/ -ll

# Check dependencies for known vulnerabilities
pip-audit --requirement requirements.txt
```

### Validate Configuration

```bash
# Validate YAML
python -c "import yaml; yaml.safe_load(open('config/config.example.yaml'))"

# Check Python syntax
python -m py_compile scripts/**/*.py
```

## GitHub Secrets Setup

To enable integration tests in CI, you need to configure GitHub Secrets and Variables.

### Authentication Options

The CI workflow supports **two authentication methods**. Choose one:

#### Option A: OAuth 2.0 with Refresh Token (Recommended)

**Benefits:**
- ✅ Tokens never expire (auto-refresh)
- ✅ More secure than legacy tokens
- ✅ No manual token regeneration needed

**Required Secrets:**

Navigate to your repository Settings → Secrets and variables → Actions → Secrets:

1. **DROPBOX_APP_KEY**
   - Your Dropbox app key
   - Get it from [Dropbox App Console](https://www.dropbox.com/developers/apps) → Your App → Settings → OAuth 2
   - Example: `abc123xyz...`

2. **DROPBOX_APP_SECRET**
   - Your Dropbox app secret
   - Same location as app key
   - Example: `xyz789abc...`

3. **DROPBOX_REFRESH_TOKEN**
   - Long-lived refresh token
   - **How to get it:**
     ```bash
     # Run locally with --force-config-storage
     python scripts/authorize_dropbox.py --force-config-storage

     # Copy the refresh_token value from config/config.yaml
     # Then delete it from the file for security
     ```
   - Example: `sl.B1a2b3c4d5...xyz`

4. **DROPBOX_SOURCE_FOLDER**
   - Test folder path (e.g., `/Cargas de cámara/2013/08`)
   - Must start with `/`
   - Must exist and contain test images
   - Case-sensitive

5. **DROPBOX_DESTINATION_FOLDER**
   - Destination folder path (e.g., `/Test/CI_Organized`)
   - Must start with `/`
   - Can be created if it doesn't exist
   - Case-sensitive

#### Option B: Legacy Access Token

**Limitations:**
- ⚠️ Tokens expire (~4 hours for short-lived)
- ⚠️ No automatic refresh
- ⚠️ Requires manual regeneration

**Required Secrets:**

1. **DROPBOX_ACCESS_TOKEN**
   - Your Dropbox API access token
   - Get it from [Dropbox App Console](https://www.dropbox.com/developers/apps) → Your App → Settings → OAuth 2 → Generate
   - Security: Never commit this to your repository
   - **Note:** You'll need to update the CI workflow to use legacy auth (comment out OAuth lines, uncomment access_token line)

2. **DROPBOX_SOURCE_FOLDER** (same as above)

3. **DROPBOX_DESTINATION_FOLDER** (same as above)

### Required Variable

Navigate to your repository Settings → Secrets and variables → Actions → Variables:

1. **RUN_INTEGRATION_TESTS**
   - Value: `true` to enable integration tests, `false` to disable
   - Default: Not set (integration tests disabled)

### Setting Up Secrets

**Step 1: Add Secrets**
1. Go to your repository on GitHub
2. Click Settings → Secrets and variables → Actions
3. Click "New repository secret"
4. Add each secret with its name and value
5. Click "Add secret"

**Step 2: Add Variable**
1. Click on the "Variables" tab
2. Click "New repository variable"
3. Name: `RUN_INTEGRATION_TESTS`
4. Value: `true`
5. Click "Add variable"

**Step 3: Verify Setup**
1. Push a commit to `main` branch
2. Go to Actions tab
3. Check that "Integration Tests" job runs
4. Verify the Dropbox connection test passes

### Security Best Practices

**Token Rotation:**
- Rotate your Dropbox access token periodically
- Update the GitHub secret when you generate a new token

**Limiting Access:**
- Use a dedicated test folder, not your main photo library
- Consider creating a separate Dropbox app for testing
- Use a small subset of photos for faster tests

**Access Control:**
- Only repository administrators can view/edit secrets
- Secrets are encrypted at rest
- Secrets are not exposed in logs
- Pull requests from forks cannot access secrets

### Disabling Integration Tests

To disable integration tests:
1. Go to Settings → Secrets and variables → Actions → Variables
2. Either delete `RUN_INTEGRATION_TESTS` or set it to `false`

### Troubleshooting

**Integration tests not running:**
- Ensure `RUN_INTEGRATION_TESTS` variable is set to `true`
- Verify you pushed to `main` branch (not a PR)

**"Invalid access token" error:**
- Generate a new token in Dropbox App Console
- Update `DROPBOX_ACCESS_TOKEN` secret in GitHub

**"Path not found" error:**
- Verify folder exists in Dropbox
- Check path starts with `/`
- Ensure exact case-sensitive match
- Update `DROPBOX_SOURCE_FOLDER` or `DROPBOX_DESTINATION_FOLDER` secret

### Example Values

**OAuth 2.0 Setup (Recommended):**
```
DROPBOX_APP_KEY: abc123xyz789
DROPBOX_APP_SECRET: xyz789abc123
DROPBOX_REFRESH_TOKEN: sl.B1a2b3c4d5...xyz
DROPBOX_SOURCE_FOLDER: /Cargas de cámara/2013/08
DROPBOX_DESTINATION_FOLDER: /Test/CI_Organized
RUN_INTEGRATION_TESTS: true
```

**Legacy Access Token Setup:**
```
DROPBOX_ACCESS_TOKEN: sl.B1a2b3c4d5...xyz
DROPBOX_SOURCE_FOLDER: /Cargas de cámara/2013/08
DROPBOX_DESTINATION_FOLDER: /Test/CI_Organized
RUN_INTEGRATION_TESTS: true
```

**Note:** The example tokens are fake. Use your actual credentials.

## CI Status Badge

The README includes a CI status badge that shows the current build status:

```markdown
![CI](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/workflows/CI/badge.svg)
```

**Badge States:**
- ✅ **Passing** - All checks passed
- ❌ **Failing** - One or more checks failed
- 🟡 **Running** - CI is currently running

## Troubleshooting

### Flake8 Errors

**Problem:** Code doesn't meet style guidelines

**Solution:**
```bash
# Run Black to auto-format
black scripts/

# Check what flake8 complains about
flake8 scripts/ --show-source
```

### Import Order Issues

**Problem:** Imports not sorted correctly

**Solution:**
```bash
# Auto-fix with isort
isort scripts/
```

### Test Failures

**Problem:** Tests failing locally or in CI

**Steps:**
1. Run tests locally: `pytest tests/ -v`
2. Check test output for specific failures
3. Fix the failing tests
4. Verify fix: `pytest tests/ -v`

### Type Checking Issues

**Problem:** mypy reports type errors

**Solutions:**
- Add type hints to function signatures
- Use `# type: ignore` for unavoidable issues
- Add missing stub packages
- Configure `ignore_missing_imports = true` for external libraries

### Security Warnings

**Problem:** bandit reports security issues

**Steps:**
1. Review the reported issue
2. Fix the security vulnerability
3. If it's a false positive, add a `# nosec` comment with justification

### Cache Issues

**Problem:** CI using outdated dependencies

**Solution:**
- GitHub Actions automatically caches pip dependencies
- To force refresh, update dependency versions in `requirements.txt`

## Adding New Tests

### Test Structure

```
tests/
├── __init__.py           # Test package marker
├── test_basic.py         # Basic validation tests
├── test_dropbox.py       # Dropbox client tests (future)
├── test_face_recognition.py  # Face recognition tests (future)
└── conftest.py           # Shared fixtures (future)
```

### Example Test

```python
"""tests/test_example.py"""
import pytest
from pathlib import Path
import sys

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

def test_something():
    """Test description."""
    assert True

def test_with_fixture(tmp_path):
    """Test using pytest fixture."""
    test_file = tmp_path / "test.txt"
    test_file.write_text("content")
    assert test_file.read_text() == "content"

class TestGrouped:
    """Group related tests in a class."""

    def test_first(self):
        assert 1 == 1

    def test_second(self):
        assert 2 == 2
```

### Running Specific Tests

```bash
# Run specific test file
pytest tests/test_basic.py

# Run specific test function
pytest tests/test_basic.py::test_python_version

# Run tests matching pattern
pytest -k "test_config"

# Run with verbose output
pytest -v

# Run with coverage
pytest --cov=scripts
```

## Automated Dependency Updates with Dependabot

Dependabot is configured to automatically create pull requests for dependency updates, keeping the project secure and up-to-date.

### Configuration

Location: `.github/dependabot.yml`

**Update Schedule:**
- **Python dependencies**: Weekly on Monday mornings (9 AM ET)
- **GitHub Actions**: Monthly

**PR Limits:**
- Maximum 5 Python dependency PRs
- Maximum 3 GitHub Actions PRs

**Grouping Strategy:**
- Development dependencies (minor/patch) are grouped together
- Production dependencies (minor/patch) are grouped together
- Major version updates create individual PRs

### Reviewing Dependabot Pull Requests

When Dependabot creates a PR, follow this workflow:

**1. Check the CI Status**
- All CI checks must pass before merging
- Review test results for any new failures
- Check security scan results

**2. Review the Changes**
- Look at the version diff (e.g., `1.2.3` → `1.2.4`)
- Check if it's a patch, minor, or major update
- For major updates, review the changelog/release notes

**3. Understand the Update Type**

**Patch Updates (1.2.3 → 1.2.4)**
- Typically bug fixes only
- Safe to merge if CI passes
- Low risk of breaking changes

**Minor Updates (1.2.0 → 1.3.0)**
- New features, may include bug fixes
- Should be backward compatible
- Review release notes for new features
- Merge if CI passes and no concerning changes

**Major Updates (1.x.x → 2.0.0)**
- May contain breaking changes
- **Always review the migration guide**
- Check if code changes are needed
- Test locally if significant changes
- May need to update code before merging

**4. Security Updates**
- PRs labeled with `security` should be prioritized
- Review the CVE details if provided
- Merge promptly after CI validation

**5. Grouped Updates**
- Review all packages in the group
- If one package causes issues, ungroup and update individually
- Comment on the PR to exclude problematic packages

**6. Testing Locally (Optional)**

For major updates or concerning changes:
```bash
# Check out the Dependabot branch
gh pr checkout <PR_NUMBER>

# Install updated dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests locally
pytest tests/ -v

# Test the application
python scripts/test_dropbox_connection.py
```

**7. Merging**
- For safe updates (patches, minor): Merge via GitHub UI
- For major updates: Consider creating a feature branch for testing
- Use "Squash and merge" to keep history clean

### Managing Dependabot PRs

**Enable Auto-merge for Safe Updates:**
```bash
# For patch updates that pass CI
gh pr review <PR_NUMBER> --approve
gh pr merge <PR_NUMBER> --auto --squash
```

**Close Unwanted Updates:**
```bash
# If you want to skip a specific update
gh pr close <PR_NUMBER>
# Comment: "@dependabot ignore this major version"
```

**Rebase Outdated PRs:**
```bash
# Comment on the PR to trigger rebase
# Comment: "@dependabot rebase"
```

### Dependabot Commands

Comment on Dependabot PRs with these commands:

- `@dependabot rebase` - Rebase the PR
- `@dependabot recreate` - Recreate the PR from scratch
- `@dependabot merge` - Merge the PR after CI passes
- `@dependabot cancel merge` - Cancel auto-merge
- `@dependabot close` - Close the PR
- `@dependabot ignore this dependency` - Stop updates for this package
- `@dependabot ignore this major version` - Skip this major version
- `@dependabot ignore this minor version` - Skip this minor version
- `@dependabot reopen` - Reopen a closed PR

### Best Practices

**1. Regular Review Cadence**
- Review Dependabot PRs weekly (matches the schedule)
- Don't let PRs accumulate - stale PRs are harder to merge
- Prioritize security updates

**2. Test Critical Updates**
- Major version updates warrant local testing
- Updates to core dependencies (dropbox, face_recognition) need extra scrutiny
- Security updates should be tested but merged quickly

**3. Monitor for Issues**
- Watch for CI failures after merging updates
- Check error tracking for new issues
- Be prepared to revert if problems arise

**4. Update Strategy**
- Merge small updates frequently rather than batching
- Keep dependencies current to avoid large version jumps
- Don't ignore updates for too long

### Troubleshooting

**Dependabot PRs not appearing:**
- Check `.github/dependabot.yml` syntax
- Verify the schedule configuration
- Check repository settings for Dependabot enablement

**Merge conflicts:**
- Comment `@dependabot rebase` to resolve
- May need to merge main into the PR manually

**CI failures on Dependabot PRs:**
- Check if the update introduced breaking changes
- Review test failures and error messages
- May need to update code to accommodate changes
- Consider closing the PR and addressing separately

**Too many PRs:**
- Adjust `open-pull-requests-limit` in config
- Expand grouping rules to consolidate more updates
- Review and merge more frequently

## Claude Code Workflows

The project includes two GitHub Actions workflows for automated code assistance using Claude Code.

### Claude Code Review (`.github/workflows/claude-code-review.yml`)

**Purpose:** On-demand PR review workflow for getting detailed code review feedback from Claude.

**Triggers:**
- Comment with `/claude-review` on any pull request
- Manual workflow dispatch via GitHub Actions UI

**How to Use:**

*Option 1: Comment Trigger (Recommended)*
Simply comment `/claude-review` on any PR to trigger a review:
```
/claude-review
```

*Option 2: Manual Trigger via UI*
1. Go to the Actions tab in GitHub
2. Select "Claude Code Review" workflow
3. Click "Run workflow"
4. Enter the PR number you want to review
5. Click "Run workflow" button

**What It Does:**
- Analyzes the pull request code changes
- Provides feedback on code quality, best practices, potential bugs, performance, and security
- Posts review comments directly on the PR

**Configuration Notes:**
- **No automatic triggers on push:** Automatic triggers have been disabled to prevent Claude from reviewing after each push (issue #58)
- **Comment-based trigger:** Use `/claude-review` in a PR comment for easy access
- **Actor restriction:** Only `amendez13` can trigger this workflow

### Claude Code (@claude) (`.github/workflows/claude.yml`)

**Purpose:** Interactive Claude assistant triggered by mentions.

**Triggers:**
- Issue comments containing `@claude`
- Pull request review comments containing `@claude`
- Pull request reviews containing `@claude`
- Issues opened/assigned with `@claude` in title or body

**How to Use:**
Simply mention `@claude` in a comment or issue with your request:
- On a PR: "Hey @claude, can you help optimize this function?"
- In an issue: "Title: @claude implement feature X"

**What It Does:**
- Responds to specific requests
- Can create/update issues and PRs
- Can perform code changes based on instructions
- Uses repository's CLAUDE.md for guidance

**Actor Restriction:** Only `amendez13` can trigger this workflow

## Future Enhancements

### Planned Additions

1. **Integration Tests**
   - Test actual Dropbox API calls
   - Requires secrets configuration in GitHub

2. **Code Coverage Requirements**
   - Enforce minimum coverage threshold (e.g., 80%)
   - Fail CI if coverage drops below threshold

3. **Performance Testing**
   - Benchmark critical functions
   - Alert on performance regressions

4. **Automated Releases**
   - Version tagging
   - Changelog generation
   - Release notes automation

### Optional Integrations

- **Codecov** - Detailed coverage reporting and visualization
- **SonarCloud** - Advanced code quality metrics
- **Snyk** - Enhanced security scanning
- **CodeQL** - Semantic code analysis

## Best Practices

### Before Committing

1. Format code: `black scripts/ && isort scripts/`
2. Run linting: `flake8 scripts/`
3. Run tests: `pytest tests/ -v`
4. Check coverage: `pytest --cov=scripts --cov-report=term-missing`

### Writing Tests

1. Test one thing per test function
2. Use descriptive test names
3. Follow Arrange-Act-Assert pattern
4. Use fixtures for common setup
5. Mock external dependencies (Dropbox API, file system)

### Handling CI Failures

1. **Read the error message** - CI logs show exactly what failed
2. **Reproduce locally** - Run the same command that failed in CI
3. **Fix and verify** - Make the fix and confirm it works locally
4. **Push and monitor** - Push the fix and watch CI to ensure it passes

### Code Review Checklist

- [ ] All CI checks passing
- [ ] Code formatted with Black
- [ ] Imports sorted with isort
- [ ] Tests added for new functionality
- [ ] Documentation updated
- [ ] No security warnings
- [ ] Type hints added where appropriate

## References

- [GitHub Actions Documentation](https://docs.github.com/en/actions)
- [pytest Documentation](https://docs.pytest.org/)
- [Black Documentation](https://black.readthedocs.io/)
- [flake8 Documentation](https://flake8.pycqa.org/)
- [mypy Documentation](https://mypy.readthedocs.io/)
- [bandit Documentation](https://bandit.readthedocs.io/)

## Changelog

### 2026-01-01 - Initial CI Setup

**Added:**
- GitHub Actions CI workflow (`.github/workflows/ci.yml`)
- Code quality checks (Black, isort, flake8, mypy)
- Test suite with pytest
- Security scanning (bandit, safety)
- Configuration validation
- Development dependencies (`requirements-dev.txt`)
- Configuration files (`.flake8`, `.pylintrc`, `pyproject.toml`)
- Basic test suite (`tests/test_basic.py`)
- CI status badge in README
- This documentation

**Changes:**
- All Python code formatted with Black
- All imports sorted with isort
- README updated with Development section

### 2026-01-04 - Make Security Checks Blocking

**Changed:**
- Security checks (bandit, pip-audit) are now blocking - builds fail on security issues
- Migrated from deprecated `safety` to `pip-audit` for dependency vulnerability scanning
- Updated `.pre-commit-config.yaml` to include `pip-audit` hook with caching
- Updated `requirements-dev.txt` to use `pip-audit` instead of `safety`

**Added:**
- `# nosec` comments to document false positives:
  - `scripts/auth/client_factory.py:98` - B105 false positive for config mode string
  - `scripts/auth/oauth_manager.py:43` - B106 false positive for OAuth token type
- `.pip-audit-cache/` to `.gitignore` for pre-commit caching
- Performance note in README about pip-audit hook timing

**Removed:**
- `|| true` bypass from bandit and safety commands in CI workflow
- `continue-on-error: true` from security checks

### 2026-01-05 - Disable Automatic Claude PR Review

**Changed:**
- Claude Code Review workflow (`.github/workflows/claude-code-review.yml`) no longer triggers automatically on PR pushes (issue #58)
- Removed `pull_request` automatic triggers (types: `[opened, synchronize]`)
- Changed to on-demand workflow using comment trigger and manual dispatch

**Added:**
- Comment-based trigger: Use `/claude-review` in any PR comment to trigger a review
- `issue_comment` event listener for comment-based triggering
- Manual trigger input for PR number in Claude Code Review workflow (`workflow_dispatch`)
- Documentation section for Claude Code workflows in CI.md
- Instructions for both comment-based and manual UI-based triggering

### 2026-01-08 - Increase Coverage Threshold to 95%

**Changed:**
- Coverage threshold increased from 90% to 95% (issue #71)
- Coverage check is now voting (blocks merges if below threshold)
- Updated CI workflow name from "Coverage Check (90% target)" to "Coverage Check (95% target)"
- Updated build status failure message to reflect 95% target

**Added:**
- Comprehensive tests for `local_provider.py` achieving 98% coverage
- New test file `tests/test_local_provider.py` with 35 test cases covering:
  - Provider initialization with default and custom configurations
  - `get_provider_name()` method
  - `validate_configuration()` method
  - `load_reference_photos()` method with various scenarios
  - `detect_faces()` method including image format conversions
  - `compare_faces()` method with tolerance handling
  - Integration workflow tests

**Coverage Status:**
- Total coverage: 99.34%
- `local_provider.py`: 98% (only import exception handler untested)
