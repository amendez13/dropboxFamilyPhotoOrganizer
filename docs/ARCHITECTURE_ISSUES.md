# GitHub Issues from Architecture Review

This document contains detailed issue templates based on the architecture review completed on December 31, 2025. Each issue below should be created as a separate GitHub issue.

---

## Issue 1: Implement Secure Access Token Storage

**Priority:** Critical (P1)
**Label:** security, enhancement
**Effort:** Low
**Impact:** High

### Description

Currently, the Dropbox access token is stored in plaintext in `config/config.yaml`. Even though this file is gitignored, this approach is problematic and poses security risks:

- Tokens in config files are easily leaked through backups, file sharing, or accidental commits
- No token refresh mechanism exists (access tokens expire)
- No encryption at rest
- Credential leakage could compromise the user's entire Dropbox account

### Recommended Solution

Implement one of the following secure storage mechanisms:

**Option 1: Environment Variables**
```python
import os
access_token = os.environ.get('DROPBOX_ACCESS_TOKEN')
```

**Option 2: System Keyring (Recommended)**
```python
import keyring
access_token = keyring.get_password('dropbox_photo_organizer', 'access_token')
```

**Option 3: OAuth 2.0 with Refresh Tokens (Best - see Issue #2)**

### References

- [Dropbox API Authentication Guide](https://www.dropbox.com/developers/documentation/http/documentation#authorization)
- [Python keyring library](https://pypi.org/project/keyring/)
- [OWASP Secrets Management Cheat Sheet](https://cheatsheetseries.owasp.org/cheatsheets/Secrets_Management_Cheat_Sheet.html)

### Acceptance Criteria

- [ ] Access tokens are not stored in plaintext files
- [ ] Secure storage mechanism is documented in README
- [ ] Migration guide provided for existing users
- [ ] Config example updated to reflect new approach

---

## Issue 2: Implement OAuth 2.0 Authorization Flow

**Priority:** Critical (P1)
**Label:** security, enhancement, authentication
**Effort:** Medium
**Impact:** High

### Description

The current design requires manually generating and pasting access tokens from the Dropbox App Console. This approach is:

- Poor user experience (tokens expire, requiring manual renewal)
- Not production-ready for long-running operations
- Fragile and error-prone
- Does not support automatic token refresh

Users will experience authentication failures during extended processing runs when tokens expire.

### Recommended Solution

Implement OAuth 2.0 authorization code flow with PKCE (Proof Key for Code Exchange):

```python
from dropbox import DropboxOAuth2FlowNoRedirect

auth_flow = DropboxOAuth2FlowNoRedirect(
    app_key,
    use_pkce=True,
    token_access_type='offline'  # Gets refresh token
)

# 1. Get authorization URL
authorize_url = auth_flow.start()
print(f"1. Go to: {authorize_url}")
print("2. Click 'Allow' (you might have to log in first)")
print("3. Copy the authorization code.")
auth_code = input("Enter the authorization code here: ").strip()

# 2. Exchange for access token and refresh token
oauth_result = auth_flow.finish(auth_code)
access_token = oauth_result.access_token
refresh_token = oauth_result.refresh_token

# 3. Store refresh_token securely, use it to get new access_tokens automatically
```

### References

- [Dropbox OAuth Guide](https://www.dropbox.com/developers/documentation/http/documentation#oauth2-authorize)
- [OAuth 2.0 with PKCE](https://oauth.net/2/pkce/)
- [Dropbox Python SDK OAuth Examples](https://github.com/dropbox/dropbox-sdk-python/tree/main/example)

### Acceptance Criteria

- [ ] OAuth 2.0 flow implemented with PKCE
- [ ] Refresh tokens stored securely (using system keyring or similar)
- [ ] Automatic token refresh before expiration
- [ ] First-run setup wizard for user authorization
- [ ] Updated documentation with OAuth setup instructions
- [ ] Backward compatibility considered for existing users

---

## Issue 3: Implement State Persistence and Resume Capability

**Priority:** Critical (P1)
**Label:** enhancement, reliability
**Effort:** Medium
**Impact:** Critical

### Description

Currently, if the processing crashes mid-run, all progress is lost. For a tool that may process thousands of photos over hours, this is unacceptable:

- No checkpoint mechanism exists
- No transaction log
- Users may lose hours of processing time on interruption
- No way to track which files have already been processed

The README mentions "Resume capability" as a Phase 3 feature, but this is essential from the start for any batch processing tool.

### Recommended Solution

Implement state tracking using SQLite:

```python
import sqlite3
from datetime import datetime

def init_db():
    conn = sqlite3.connect('processing_state.db')
    conn.execute('''
        CREATE TABLE IF NOT EXISTS processed_files (
            file_path TEXT PRIMARY KEY,
            file_hash TEXT,
            processed_at TIMESTAMP,
            match_result BOOLEAN,
            moved_to TEXT,
            error_message TEXT
        )
    ''')
    conn.commit()
    return conn

def is_processed(conn, file_path):
    cursor = conn.execute(
        'SELECT 1 FROM processed_files WHERE file_path = ?',
        (file_path,)
    )
    return cursor.fetchone() is not None

def mark_processed(conn, file_path, file_hash, match_result, moved_to=None, error=None):
    conn.execute('''
        INSERT OR REPLACE INTO processed_files
        (file_path, file_hash, processed_at, match_result, moved_to, error_message)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (file_path, file_hash, datetime.now(), match_result, moved_to, error))
    conn.commit()
```

### Additional Features

- Add `--resume` flag to continue from last checkpoint
- Add `--reset` flag to clear state and start fresh
- Track file content hashes to detect if files have changed
- Store error messages for failed files
- Generate summary reports of processed files

### References

- [SQLite Python Documentation](https://docs.python.org/3/library/sqlite3.html)
- [Dropbox file metadata and content_hash](https://www.dropbox.com/developers/documentation/http/documentation#files-get_metadata)

### Acceptance Criteria

- [ ] SQLite database for state tracking implemented
- [ ] Files are checked against database before processing
- [ ] State updated after each file (or small batches)
- [ ] `--resume` flag to continue interrupted runs
- [ ] `--reset` flag to clear state
- [ ] Summary report of processed/skipped/failed files
- [ ] Documentation updated with resume capability
- [ ] Handle edge cases (corrupted database, moved files, etc.)

---

## Issue 4: Improve Face Recognition Accuracy with Two-Pass Strategy

**Priority:** Medium-High (P2)
**Label:** enhancement, face-recognition
**Effort:** Medium
**Impact:** Medium-High

### Description

The current design suggests using `w256h256` thumbnails for face recognition. While efficient for bandwidth, this approach causes:

- Missed faces in group photos (faces too small at 256px resolution)
- False negatives for distant subjects
- Poor accuracy compared to full-resolution processing
- Core functionality may significantly underperform

This directly impacts the primary value proposition of the tool.

### Recommended Solution

Implement a two-pass approach that balances efficiency and accuracy:

**Pass 1: Quick Scan with Thumbnails**
```python
# Use medium-sized thumbnails for initial detection
thumbnail = get_thumbnail(file_path, size='w640h480')
face_locations = face_recognition.face_locations(thumbnail)

if face_locations:
    # Pass 2: Download full resolution only if faces detected
    full_image = download_full_image(file_path)
    encodings = face_recognition.face_encodings(full_image, face_locations)
    # Perform actual matching on high-res encodings
    matches = compare_faces(reference_encodings, encodings)
```

**Alternative Approach:** Use larger thumbnails (`w1024h768`) as a single-pass compromise between bandwidth and accuracy.

### Testing Requirements

- Create test suite with known photos at various resolutions
- Benchmark accuracy vs. thumbnail size
- Measure bandwidth usage and processing time
- Compare false positive/negative rates

### References

- [face_recognition library documentation](https://github.com/ageitgey/face_recognition)
- [Dropbox thumbnail sizes](https://www.dropbox.com/developers/documentation/http/documentation#files-get_thumbnail)

### Acceptance Criteria

- [ ] Two-pass strategy implemented (or justified single-pass with larger thumbnails)
- [ ] Configurable thumbnail size in config.yaml
- [ ] Accuracy benchmarks documented
- [ ] Performance metrics (time, bandwidth) documented
- [ ] Test suite with various photo sizes and distances
- [ ] Updated documentation explaining the approach

---

## Issue 5: Enhance Reference Photo Handling with Multiple Encodings

**Priority:** Medium (P2)
**Label:** enhancement, face-recognition
**Effort:** Medium
**Impact:** Medium

### Description

The design uses `reference_photos_dir` for target identification, but lacks guidance on:

- Recommended number of reference photos
- How multiple reference encodings are handled
- Dealing with different angles, ages, or lighting conditions
- Voting/averaging strategy for multiple references

This affects matching accuracy and reliability.

### Recommended Solution

**1. Multiple Reference Photos (5-10 recommended)**
```python
def load_reference_encodings(reference_dir):
    encodings = []
    for photo_path in Path(reference_dir).glob('*'):
        image = face_recognition.load_image_file(photo_path)
        face_encodings = face_recognition.face_encodings(image)
        if face_encodings:
            encodings.append(face_encodings[0])
        else:
            logging.warning(f"No face found in reference photo: {photo_path}")

    if len(encodings) < 3:
        logging.warning("Less than 3 reference photos found. Accuracy may be reduced.")

    return encodings
```

**2. Voting Strategy for Matching**
```python
def is_match(face_encoding, reference_encodings, tolerance=0.6, threshold=0.5):
    """
    Returns True if face matches reference encodings based on voting.

    Args:
        threshold: Fraction of reference encodings that must match (0.5 = 50%)
    """
    distances = face_recognition.face_distance(reference_encodings, face_encoding)
    matches = sum(1 for d in distances if d <= tolerance)
    return matches >= len(reference_encodings) * threshold
```

### Configuration

Add to `config.yaml`:
```yaml
face_recognition:
  reference_photos_dir: "/path/to/reference/photos"
  tolerance: 0.6
  voting_threshold: 0.5  # 50% of reference photos must match
  min_reference_photos: 3
```

### References

- [face_recognition accuracy tips](https://github.com/ageitgey/face_recognition/wiki/Face-Recognition-Accuracy-Tips)
- Research on face recognition ensemble methods

### Acceptance Criteria

- [ ] Support for multiple reference photos
- [ ] Voting/consensus strategy implemented
- [ ] Warning if less than recommended reference photos
- [ ] Configurable voting threshold
- [ ] Documentation on selecting good reference photos
- [ ] Test cases with various reference photo counts

---

## Issue 6: Clarify HEIC Support or Remove from Supported Formats

**Priority:** Low-Medium (P2)
**Label:** enhancement, image-formats
**Effort:** Low
**Impact:** Low-Medium

### Description

The configuration lists `.heic` as a supported format, but:

- `face_recognition` library doesn't natively support HEIC
- Requires additional dependencies (`pillow-heif`, `pyheif`, or ImageMagick)
- Not mentioned in `requirements.txt`
- May fail silently or with unclear errors

HEIC is the default format on iPhones, so users may expect it to work.

### Recommended Solution

**Option A: Add Proper HEIC Support (Recommended)**

Add to `requirements.txt`:
```
pillow-heif>=0.10.0
```

Add to initialization code:
```python
from pillow_heif import register_heif_opener
register_heif_opener()
# Now PIL/Pillow can open HEIC files
```

**Option B: Remove HEIC from Supported Formats**

Update documentation to clearly state HEIC is not supported and provide conversion guidance:
```bash
# Users can convert HEIC to JPEG before running
# Using ImageMagick:
magick mogrify -format jpg *.heic
```

### References

- [pillow-heif library](https://pypi.org/project/pillow-heif/)
- [HEIC format information](https://en.wikipedia.org/wiki/High_Efficiency_Image_File_Format)

### Acceptance Criteria

- [ ] Decision made: support or remove HEIC
- [ ] If supported: dependencies added and tested
- [ ] If not supported: removed from supported formats list
- [ ] Documentation updated accordingly
- [ ] Error handling for unsupported formats improved

---

## Issue 7: Change Default Operation from Move to Copy

**Priority:** Medium (P2)
**Label:** enhancement, safety
**Effort:** Low
**Impact:** Medium

### Description

The current design moves files rather than copies them. This is destructive and could lead to:

- Data loss if bugs exist
- Difficulty reverting mistakes
- Broken shared links or file references in Dropbox
- User anxiety about irreversible operations

### Recommended Solution

**1. Default to Copy, Not Move**
```python
def safe_organize(source_path, dest_path, operation='copy', dry_run=True):
    """
    Organize photos with operation logging for undo capability.

    Args:
        operation: 'copy' or 'move'
    """
    operation_log = {
        'timestamp': datetime.now().isoformat(),
        'source': source_path,
        'destination': dest_path,
        'action': operation
    }

    if not dry_run:
        if operation == 'copy':
            dbx.files_copy_v2(source_path, dest_path)
        elif operation == 'move':
            dbx.files_move_v2(source_path, dest_path)

        log_operation(operation_log)

    return operation_log
```

**2. Add Configuration Option**
```yaml
processing:
  operation: copy  # 'copy' or 'move'
  dry_run: true
```

**3. Implement Undo/Rollback**
```python
def rollback_operations(log_file, since_timestamp=None):
    """Revert operations from log file."""
    # Read operation log
    # Reverse operations (copy -> delete, move -> move back)
```

### References

- [Dropbox files_copy_v2 API](https://www.dropbox.com/developers/documentation/http/documentation#files-copy)
- [Dropbox files_move_v2 API](https://www.dropbox.com/developers/documentation/http/documentation#files-move)

### Acceptance Criteria

- [ ] Default operation changed to 'copy'
- [ ] Configuration option for 'copy' vs 'move'
- [ ] Operation logging implemented
- [ ] Clear warnings when using 'move' mode
- [ ] Documentation updated with safety recommendations
- [ ] Optional: Implement rollback functionality

---

## Issue 8: Implement Rate Limiting and Exponential Backoff

**Priority:** Medium (P2)
**Label:** enhancement, reliability
**Effort:** Low
**Impact:** Medium

### Description

Dropbox API has strict rate limits. The current design doesn't address:

- Exponential backoff for rate limit errors
- Request throttling
- Graceful handling of 429 (Too Many Requests) responses
- Potential for permanent bans due to aggressive API usage

### Recommended Solution

```python
import time
from dropbox.exceptions import RateLimitError

def api_call_with_backoff(func, *args, max_retries=5, **kwargs):
    """
    Wrapper for Dropbox API calls with exponential backoff.

    Args:
        func: The Dropbox API function to call
        max_retries: Maximum number of retry attempts

    Returns:
        Result of the API call

    Raises:
        Exception if max retries exceeded
    """
    for attempt in range(max_retries):
        try:
            return func(*args, **kwargs)
        except RateLimitError as e:
            if attempt == max_retries - 1:
                raise

            # Use backoff time from error if available, else exponential
            wait_time = e.backoff if hasattr(e, 'backoff') else (2 ** attempt)
            logging.warning(
                f"Rate limited. Waiting {wait_time}s before retry "
                f"(attempt {attempt + 1}/{max_retries})"
            )
            time.sleep(wait_time)

    raise Exception(f"Max retries ({max_retries}) exceeded")

# Usage
files = api_call_with_backoff(
    dbx.files_list_folder,
    path='/Photos',
    recursive=True
)
```

### Additional Considerations

- Add configurable delay between API calls
- Track API call count and rate
- Display progress with estimated time remaining

### References

- [Dropbox API Rate Limiting](https://www.dropbox.com/developers/documentation/http/documentation#rate-limiting)
- [Exponential Backoff Algorithm](https://en.wikipedia.org/wiki/Exponential_backoff)

### Acceptance Criteria

- [ ] Exponential backoff wrapper implemented
- [ ] All Dropbox API calls wrapped with retry logic
- [ ] Configurable max retries and backoff strategy
- [ ] Proper logging of rate limit events
- [ ] Graceful error messages to user
- [ ] Optional: Rate tracking and throttling

---

## Issue 9: Implement Concurrent Processing for Performance

**Priority:** Medium (P3)
**Label:** enhancement, performance
**Effort:** High
**Impact:** Medium

### Description

Processing thousands of photos sequentially is slow. The current design doesn't address parallel processing, which could significantly improve performance:

- Downloading thumbnails is I/O bound (benefits from async)
- Face recognition is CPU bound (benefits from multiprocessing)
- Sequential processing may take hours for large libraries

### Recommended Solution

Hybrid approach using both async I/O and multiprocessing:

```python
import asyncio
import aiohttp
from concurrent.futures import ProcessPoolExecutor

async def download_thumbnail(session, file_path):
    """Async download of thumbnail."""
    # Async Dropbox API call
    async with session.get(thumbnail_url) as response:
        return await response.read()

async def download_batch(file_paths):
    """Download multiple thumbnails concurrently."""
    async with aiohttp.ClientSession() as session:
        tasks = [download_thumbnail(session, path) for path in file_paths]
        return await asyncio.gather(*tasks)

def process_face_recognition(image_data):
    """CPU-intensive face recognition (runs in separate process)."""
    image = face_recognition.load_image_file(io.BytesIO(image_data))
    encodings = face_recognition.face_encodings(image)
    return encodings

async def process_photos_parallel(file_paths, max_workers=4):
    """
    Process photos with concurrent I/O and parallel CPU work.

    Args:
        max_workers: Number of CPU processes for face recognition
    """
    # I/O bound: async downloads
    images = await download_batch(file_paths)

    # CPU bound: process pool for face recognition
    with ProcessPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_face_recognition, images))

    return results
```

### Configuration

Add to `config.yaml`:
```yaml
processing:
  max_concurrent_downloads: 10
  max_worker_processes: 4
  batch_size: 100
```

### Considerations

- Monitor memory usage (multiple images in memory)
- Graceful degradation if resources limited
- Progress tracking with concurrent operations
- Error handling in parallel context

### References

- [Python asyncio documentation](https://docs.python.org/3/library/asyncio.html)
- [ProcessPoolExecutor](https://docs.python.org/3/library/concurrent.futures.html#processpoolexecutor)
- [Dropbox Python SDK async support](https://github.com/dropbox/dropbox-sdk-python)

### Acceptance Criteria

- [ ] Async I/O for Dropbox downloads
- [ ] Multiprocessing for face recognition
- [ ] Configurable concurrency limits
- [ ] Progress tracking works with parallel processing
- [ ] Error handling and graceful degradation
- [ ] Performance benchmarks showing improvement
- [ ] Memory usage monitoring and limits
- [ ] Documentation on performance tuning

---

## Issue 10: Add Configuration Validation with Pydantic

**Priority:** Medium (P2)
**Label:** enhancement, config
**Effort:** Low
**Impact:** Medium

### Description

Currently, there is no schema validation for `config.yaml`. Invalid configurations fail silently or with cryptic errors:

- Missing required fields not caught early
- Invalid values (e.g., tolerance > 1.0) not validated
- Type mismatches cause runtime errors
- Poor user experience troubleshooting config issues

### Recommended Solution

Use Pydantic for comprehensive configuration validation:

```python
from pydantic import BaseModel, Field, validator, DirectoryPath
from typing import Literal
from pathlib import Path

class DropboxConfig(BaseModel):
    """Dropbox API configuration."""
    # Don't store token in config - use secure storage
    app_key: str = Field(..., description="Dropbox app key")
    app_secret: str = Field(..., description="Dropbox app secret")

class FaceRecognitionConfig(BaseModel):
    """Face recognition settings."""
    reference_photos_dir: DirectoryPath = Field(
        ...,
        description="Directory containing reference photos of target person"
    )
    tolerance: float = Field(
        0.6,
        ge=0.1,
        le=1.0,
        description="Face matching tolerance (lower = stricter)"
    )
    thumbnail_size: Literal['w256h256', 'w640h480', 'w1024h768'] = Field(
        'w640h480',
        description="Thumbnail size for face detection"
    )
    voting_threshold: float = Field(
        0.5,
        ge=0.0,
        le=1.0,
        description="Fraction of reference photos that must match"
    )

    @validator('reference_photos_dir')
    def validate_reference_photos(cls, v):
        if not v.exists():
            raise ValueError(f"Reference photos directory does not exist: {v}")

        photo_files = list(v.glob('*.jpg')) + list(v.glob('*.jpeg')) + list(v.glob('*.png'))
        if len(photo_files) < 1:
            raise ValueError(f"No reference photos found in {v}")

        return v

class ProcessingConfig(BaseModel):
    """Processing behavior settings."""
    source_folder: str = Field(..., description="Dropbox folder to scan")
    target_folder: str = Field(..., description="Dropbox folder for matching photos")
    operation: Literal['copy', 'move'] = Field(
        'copy',
        description="Whether to copy or move matching photos"
    )
    dry_run: bool = Field(
        True,
        description="Preview mode - don't actually modify files"
    )
    batch_size: int = Field(
        100,
        ge=1,
        le=1000,
        description="Number of files to process in each batch"
    )
    max_concurrent_downloads: int = Field(
        10,
        ge=1,
        le=50,
        description="Maximum concurrent thumbnail downloads"
    )

class Config(BaseModel):
    """Main configuration."""
    dropbox: DropboxConfig
    face_recognition: FaceRecognitionConfig
    processing: ProcessingConfig

    @classmethod
    def from_yaml(cls, path: str):
        """Load and validate configuration from YAML file."""
        import yaml
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)

# Usage
try:
    config = Config.from_yaml('config/config.yaml')
except ValidationError as e:
    print("Configuration errors:")
    for error in e.errors():
        print(f"  - {error['loc']}: {error['msg']}")
    sys.exit(1)
```

### Update Dependencies

Add to `requirements.txt`:
```
pydantic>=2.0.0
pydantic[email]>=2.0.0  # If email validation needed
```

### References

- [Pydantic documentation](https://docs.pydantic.dev/)
- [Pydantic validators](https://docs.pydantic.dev/latest/concepts/validators/)

### Acceptance Criteria

- [ ] Pydantic models for all config sections
- [ ] Validation for all config fields
- [ ] Clear error messages for invalid config
- [ ] Type hints throughout configuration
- [ ] Updated config.example.yaml with comments
- [ ] Documentation on configuration options
- [ ] Migration guide for existing configs

---

## Issue 11: Implement Structured Logging Infrastructure

**Priority:** Medium (P2)
**Label:** enhancement, logging
**Effort:** Low
**Impact:** Medium

### Description

The README mentions "better logging" as a future feature, but any production tool needs structured logging from the start:

- No visibility into processing progress
- Difficult to debug issues
- No audit trail of operations
- Cannot track performance metrics

### Recommended Solution

Implement structured logging with multiple handlers:

```python
import logging
import sys
from pathlib import Path

def setup_logging(log_dir='logs', verbose=False, log_file='photo_organizer.log'):
    """
    Configure structured logging with file and console output.

    Args:
        log_dir: Directory for log files
        verbose: Enable DEBUG level logging
        log_file: Name of the log file
    """
    # Create logs directory
    log_path = Path(log_dir)
    log_path.mkdir(exist_ok=True)

    # Determine log level
    level = logging.DEBUG if verbose else logging.INFO

    # Create formatters
    file_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    console_formatter = logging.Formatter(
        '%(levelname)s: %(message)s'
    )

    # File handler (detailed)
    file_handler = logging.FileHandler(log_path / log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(file_formatter)

    # Console handler (user-friendly)
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(console_formatter)

    # Configure root logger
    logging.basicConfig(
        level=logging.DEBUG,
        handlers=[file_handler, console_handler]
    )

    # Suppress verbose third-party logs
    logging.getLogger('dropbox').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)

# Usage in main script
logger = logging.getLogger(__name__)

def process_photo(file_path):
    logger.info(f"Processing: {file_path}")
    logger.debug(f"Downloading thumbnail for {file_path}")

    try:
        # ... processing logic ...
        logger.info(f"Match found: {file_path}")
    except Exception as e:
        logger.error(f"Failed to process {file_path}: {e}", exc_info=True)
```

### Enhanced Logging with Metrics

```python
import time

class MetricsLogger:
    """Track and log performance metrics."""

    def __init__(self):
        self.metrics = {
            'files_processed': 0,
            'matches_found': 0,
            'errors': 0,
            'api_calls': 0,
            'processing_time': 0
        }
        self.start_time = time.time()

    def log_file_processed(self, matched=False, error=False):
        self.metrics['files_processed'] += 1
        if matched:
            self.metrics['matches_found'] += 1
        if error:
            self.metrics['errors'] += 1

    def log_api_call(self):
        self.metrics['api_calls'] += 1

    def summary(self):
        elapsed = time.time() - self.start_time
        self.metrics['processing_time'] = elapsed

        logger.info("=" * 50)
        logger.info("Processing Summary")
        logger.info("=" * 50)
        logger.info(f"Files processed: {self.metrics['files_processed']}")
        logger.info(f"Matches found: {self.metrics['matches_found']}")
        logger.info(f"Errors: {self.metrics['errors']}")
        logger.info(f"API calls: {self.metrics['api_calls']}")
        logger.info(f"Processing time: {elapsed:.2f}s")
        logger.info(f"Average per file: {elapsed/max(1, self.metrics['files_processed']):.2f}s")
        logger.info("=" * 50)
```

### Configuration

Add to `config.yaml`:
```yaml
logging:
  level: INFO  # DEBUG, INFO, WARNING, ERROR
  log_dir: logs
  log_file: photo_organizer.log
  console_output: true
```

### References

- [Python logging documentation](https://docs.python.org/3/library/logging.html)
- [Logging best practices](https://docs.python-guide.org/writing/logging/)

### Acceptance Criteria

- [ ] Structured logging configured with file and console handlers
- [ ] Different log levels for file (DEBUG) and console (INFO)
- [ ] Metrics tracking for processing statistics
- [ ] Summary report at end of processing
- [ ] Configurable log levels and paths
- [ ] Log rotation for large log files (optional)
- [ ] Documentation on interpreting logs

---

## Issue 12: Create Comprehensive Test Suite

**Priority:** High (P1)
**Label:** testing, quality
**Effort:** Medium
**Impact:** High

### Description

No test suite currently exists. For a tool that processes user photos, comprehensive testing is critical:

- No unit tests for face matching logic
- No integration tests for Dropbox API client
- No accuracy benchmarks with known test images
- Risk of regressions with future changes

### Recommended Test Structure

```
tests/
├── __init__.py
├── conftest.py              # Pytest fixtures
├── test_config.py           # Configuration validation tests
├── test_dropbox_client.py   # Dropbox API integration tests
├── test_face_recognition.py # Face matching accuracy tests
├── test_state_management.py # State persistence tests
├── test_processing.py       # End-to-end processing tests
└── fixtures/
    ├── test_photos/         # Known test images
    ├── reference_faces/     # Reference photos for testing
    └── mock_responses/      # Mock Dropbox API responses
```

### Test Categories

**1. Unit Tests**
```python
# test_face_recognition.py
import pytest
from scripts.face_matcher import is_match, load_reference_encodings

def test_load_reference_encodings():
    """Test loading reference encodings from directory."""
    encodings = load_reference_encodings('tests/fixtures/reference_faces')
    assert len(encodings) > 0
    assert all(len(enc) == 128 for enc in encodings)

def test_face_matching_with_known_photos():
    """Test matching with known positive and negative cases."""
    reference = load_reference_encodings('tests/fixtures/reference_faces')

    # Test positive match
    positive_encoding = get_encoding('tests/fixtures/test_photos/match.jpg')
    assert is_match(positive_encoding, reference, tolerance=0.6)

    # Test negative match
    negative_encoding = get_encoding('tests/fixtures/test_photos/no_match.jpg')
    assert not is_match(negative_encoding, reference, tolerance=0.6)
```

**2. Integration Tests**
```python
# test_dropbox_client.py
import pytest
from scripts.dropbox_client import DropboxClient

@pytest.fixture
def mock_dropbox():
    """Mock Dropbox client for testing."""
    # Use pytest-mock or unittest.mock
    pass

def test_list_files_with_pagination(mock_dropbox):
    """Test handling of paginated file listings."""
    # Test with mock that requires multiple pages
    pass

def test_rate_limit_handling(mock_dropbox):
    """Test exponential backoff on rate limits."""
    # Simulate 429 response
    pass
```

**3. Accuracy Benchmarks**
```python
# test_face_recognition.py
def test_accuracy_benchmark():
    """Benchmark face recognition accuracy with known dataset."""
    test_cases = load_test_dataset('tests/fixtures/benchmark_set.json')

    results = {
        'true_positives': 0,
        'false_positives': 0,
        'true_negatives': 0,
        'false_negatives': 0
    }

    for test_case in test_cases:
        prediction = classify_photo(test_case['photo'])
        actual = test_case['expected']

        if prediction and actual:
            results['true_positives'] += 1
        elif prediction and not actual:
            results['false_positives'] += 1
        elif not prediction and actual:
            results['false_negatives'] += 1
        else:
            results['true_negatives'] += 1

    # Calculate metrics
    precision = results['true_positives'] / (results['true_positives'] + results['false_positives'])
    recall = results['true_positives'] / (results['true_positives'] + results['false_negatives'])

    assert precision > 0.9, f"Precision too low: {precision}"
    assert recall > 0.85, f"Recall too low: {recall}"
```

### Dependencies

Add to `requirements-dev.txt`:
```
pytest>=7.4.0
pytest-asyncio>=0.21.0
pytest-cov>=4.1.0
pytest-mock>=3.11.0
responses>=0.23.0  # Mock HTTP responses
```

### References

- [pytest documentation](https://docs.pytest.org/)
- [Testing best practices](https://docs.pytest.org/en/latest/explanation/goodpractices.html)
- [Face recognition test datasets](https://github.com/ageitgey/face_recognition/tree/master/tests)

### Acceptance Criteria

- [ ] Test suite structure created
- [ ] Unit tests for core functionality (>80% coverage)
- [ ] Integration tests for Dropbox client
- [ ] Accuracy benchmarks with known test set
- [ ] Mock fixtures for Dropbox API responses
- [ ] CI integration (see Issue #13)
- [ ] Test documentation and running instructions
- [ ] Minimum coverage threshold enforced

---

## Issue 13: Set Up CI/CD Pipeline with GitHub Actions

**Priority:** High (P1)
**Label:** ci-cd, infrastructure
**Effort:** Medium
**Impact:** High

### Description

No CI/CD pipeline currently exists. Automated testing and quality checks are essential for maintaining code quality:

- No automated testing on pull requests
- No linting or code style enforcement
- No automated security checks
- Risk of merging broken code

### Recommended GitHub Actions Workflow

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

jobs:
  lint:
    name: Lint and Code Quality
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install flake8 black isort mypy
          pip install -r requirements.txt

      - name: Run flake8
        run: flake8 scripts/ --max-line-length=100 --exclude=venv

      - name: Check code formatting with black
        run: black --check scripts/

      - name: Check import sorting with isort
        run: isort --check-only scripts/

      - name: Run type checking with mypy
        run: mypy scripts/ --ignore-missing-imports

  test:
    name: Test Suite
    runs-on: ubuntu-latest
    strategy:
      matrix:
        python-version: ['3.9', '3.10', '3.11', '3.12']

    steps:
      - uses: actions/checkout@v4

      - name: Set up Python ${{ matrix.python-version }}
        uses: actions/setup-python@v4
        with:
          python-version: ${{ matrix.python-version }}

      - name: Install system dependencies
        run: |
          sudo apt-get update
          sudo apt-get install -y cmake

      - name: Install Python dependencies
        run: |
          python -m pip install --upgrade pip
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run tests with coverage
        run: |
          pytest tests/ \
            --cov=scripts \
            --cov-report=xml \
            --cov-report=term-missing \
            --cov-fail-under=80

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          file: ./coverage.xml
          fail_ci_if_error: false

  security:
    name: Security Checks
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          python -m pip install --upgrade pip
          pip install safety bandit

      - name: Run safety check
        run: safety check --file requirements.txt

      - name: Run bandit security linter
        run: bandit -r scripts/ -f json -o bandit-report.json
```

### Additional Workflows

**Dependency Updates**: Create `.github/workflows/dependabot.yml`
```yaml
version: 2
updates:
  - package-ecosystem: "pip"
    directory: "/"
    schedule:
      interval: "weekly"
    open-pull-requests-limit: 10
```

**Release Workflow**: Automate versioning and releases
```yaml
name: Release

on:
  push:
    tags:
      - 'v*'

jobs:
  release:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Create Release
        uses: actions/create-release@v1
        env:
          GITHUB_TOKEN: ${{ secrets.GITHUB_TOKEN }}
        with:
          tag_name: ${{ github.ref }}
          release_name: Release ${{ github.ref }}
          draft: false
          prerelease: false
```

### Code Quality Tools Configuration

**`.flake8`**
```ini
[flake8]
max-line-length = 100
exclude = venv,.git,__pycache__,.pytest_cache
ignore = E203,W503
```

**`pyproject.toml`**
```toml
[tool.black]
line-length = 100
target-version = ['py39', 'py310', 'py311']
include = '\.pyi?$'
exclude = '''
/(
    \.git
  | \.venv
  | build
  | dist
)/
'''

[tool.isort]
profile = "black"
line_length = 100
```

### Dependencies

Add to `requirements-dev.txt`:
```
flake8>=6.0.0
black>=23.0.0
isort>=5.12.0
mypy>=1.5.0
safety>=2.3.0
bandit>=1.7.5
```

### References

- [GitHub Actions documentation](https://docs.github.com/en/actions)
- [Python testing with GitHub Actions](https://docs.github.com/en/actions/automating-builds-and-tests/building-and-testing-python)
- [Codecov GitHub Action](https://github.com/codecov/codecov-action)

### Acceptance Criteria

- [ ] CI workflow created and running on PRs
- [ ] Linting with flake8, black, isort
- [ ] Type checking with mypy
- [ ] Test suite runs on multiple Python versions
- [ ] Code coverage reporting (80% minimum)
- [ ] Security checks with safety and bandit
- [ ] Dependabot for automated dependency updates
- [ ] Status badges in README
- [ ] Documentation on CI/CD process

---

## Issue 14: Establish Performance Benchmarks and Monitoring

**Priority:** Medium (P2)
**Label:** performance, monitoring
**Effort:** Medium
**Impact:** Medium

### Description

No baseline performance metrics exist. Without benchmarks, it's impossible to:

- Identify performance regressions
- Optimize critical paths
- Set user expectations
- Measure improvement from changes

### Recommended Approach

**1. Benchmark Suite**

Create `tests/benchmarks/test_performance.py`:
```python
import pytest
import time
from scripts.face_matcher import process_photo
from scripts.dropbox_client import DropboxClient

class Timer:
    def __enter__(self):
        self.start = time.time()
        return self

    def __exit__(self, *args):
        self.end = time.time()
        self.elapsed = self.end - self.start

def test_thumbnail_download_performance(benchmark_photos):
    """Benchmark thumbnail download speed."""
    with Timer() as t:
        thumbnails = download_thumbnails(benchmark_photos[:100])

    avg_time = t.elapsed / 100
    assert avg_time < 0.5, f"Average thumbnail download too slow: {avg_time}s"

    print(f"Thumbnail download: {avg_time:.3f}s per photo")

def test_face_recognition_performance(benchmark_images):
    """Benchmark face recognition processing speed."""
    with Timer() as t:
        for image in benchmark_images[:50]:
            encodings = face_recognition.face_encodings(image)

    avg_time = t.elapsed / 50
    assert avg_time < 1.0, f"Face recognition too slow: {avg_time}s"

    print(f"Face recognition: {avg_time:.3f}s per photo")

def test_end_to_end_performance():
    """Benchmark complete processing pipeline."""
    test_files = get_test_files(count=100)

    with Timer() as t:
        results = process_batch(test_files)

    photos_per_minute = (100 / t.elapsed) * 60

    print(f"Processing speed: {photos_per_minute:.1f} photos/minute")
    print(f"API calls per photo: {api_call_count / 100:.1f}")
    print(f"Memory usage: {get_memory_usage():.1f} MB")
```

**2. Performance Profiling**

```python
import cProfile
import pstats
from pstats import SortKey

def profile_processing():
    """Profile the processing function to identify bottlenecks."""
    profiler = cProfile.Profile()
    profiler.enable()

    # Run processing
    process_photos(test_files)

    profiler.disable()

    # Print stats
    stats = pstats.Stats(profiler)
    stats.sort_stats(SortKey.CUMULATIVE)
    stats.print_stats(20)  # Top 20 functions
```

**3. Memory Profiling**

```python
from memory_profiler import profile

@profile
def process_batch_with_memory_tracking(files):
    """Track memory usage during batch processing."""
    # Processing logic
    pass
```

**4. Monitoring Dashboard**

Create `scripts/performance_monitor.py`:
```python
import json
from datetime import datetime
from pathlib import Path

class PerformanceMonitor:
    def __init__(self, log_file='performance_metrics.json'):
        self.log_file = Path(log_file)
        self.metrics = []

    def record_run(self, metrics):
        """Record performance metrics from a run."""
        entry = {
            'timestamp': datetime.now().isoformat(),
            'files_processed': metrics['files_processed'],
            'processing_time': metrics['processing_time'],
            'photos_per_minute': metrics['photos_per_minute'],
            'api_calls': metrics['api_calls'],
            'memory_peak_mb': metrics['memory_peak_mb'],
            'errors': metrics['errors']
        }

        self.metrics.append(entry)
        self._save()

    def _save(self):
        with open(self.log_file, 'w') as f:
            json.dump(self.metrics, f, indent=2)

    def generate_report(self):
        """Generate performance report."""
        if not self.metrics:
            return "No metrics recorded"

        recent = self.metrics[-10:]  # Last 10 runs

        avg_speed = sum(m['photos_per_minute'] for m in recent) / len(recent)
        avg_api_calls = sum(m['api_calls'] for m in recent) / sum(m['files_processed'] for m in recent)

        return f"""
Performance Report (Last {len(recent)} runs)
===========================================
Average speed: {avg_speed:.1f} photos/minute
API calls per photo: {avg_api_calls:.2f}
Average memory usage: {sum(m['memory_peak_mb'] for m in recent) / len(recent):.1f} MB
Total files processed: {sum(m['files_processed'] for m in recent)}
        """
```

### Baseline Targets

Establish these baseline targets (adjust based on actual testing):

| Metric | Target | Notes |
|--------|--------|-------|
| Photos per minute | 30+ | With face recognition |
| API calls per photo | 2-3 | List + thumbnail + move/copy |
| Memory usage | < 500MB | For 100 concurrent photos |
| Accuracy (precision) | > 90% | On benchmark test set |
| Accuracy (recall) | > 85% | On benchmark test set |

### Dependencies

Add to `requirements-dev.txt`:
```
pytest-benchmark>=4.0.0
memory-profiler>=0.61.0
psutil>=5.9.0  # System monitoring
```

### References

- [Python profiling](https://docs.python.org/3/library/profile.html)
- [pytest-benchmark](https://pytest-benchmark.readthedocs.io/)
- [memory-profiler](https://pypi.org/project/memory-profiler/)

### Acceptance Criteria

- [ ] Benchmark suite for key operations
- [ ] Performance profiling scripts
- [ ] Memory usage monitoring
- [ ] Baseline metrics documented
- [ ] Performance regression tests in CI
- [ ] Monitoring dashboard/reports
- [ ] Documentation on interpreting metrics

---

## Issue 15: Document Privacy and Data Handling Policies

**Priority:** High (P1)
**Label:** documentation, privacy, security
**Effort:** Low
**Impact:** High

### Description

Face data is biometric information and highly sensitive. The project currently has no documentation on:

- Where face encodings are stored
- Data retention policies
- Whether data leaves the local machine
- GDPR/privacy compliance considerations
- User consent and transparency

This is a critical gap for any tool handling biometric data.

### Recommended Documentation

Create `docs/PRIVACY.md`:

```markdown
# Privacy and Data Handling

## Overview

The Dropbox Family Photo Organizer processes facial recognition data, which is considered biometric information in many jurisdictions. This document explains how the tool handles your data.

## Data Collection and Processing

### What Data is Processed

- **Reference Photos**: Photos you provide of the target person
- **Face Encodings**: Mathematical representations of faces (128-dimensional vectors)
- **Dropbox Photos**: Photos from your Dropbox account
- **Processing Metadata**: File paths, timestamps, match results

### Where Data is Stored

**Local Storage Only**
- All processing happens on your local machine
- Face encodings are stored in: `[location]`
- Processing state database: `processing_state.db`
- No data is sent to external servers (except Dropbox API calls)

**Dropbox Storage**
- Original photos remain in your Dropbox account
- No face data or encodings are uploaded to Dropbox
- Only file operations (copy/move) interact with Dropbox

### Data Retention

- Face encodings from reference photos: Stored until manually deleted
- Processing state: Persisted across runs, can be cleared with `--reset`
- Logs: Rotated after [X] days or [Y] MB

## Privacy Protections

### No Cloud Processing
- Face recognition happens entirely on your local machine
- Face encodings never leave your device
- No third-party face recognition services used

### Secure Credential Storage
- Dropbox access tokens stored in system keyring (not plaintext)
- OAuth refresh tokens encrypted at rest

### Minimal Data Collection
- Only processes files you explicitly specify
- No telemetry or analytics collected
- No usage data sent to developers

## User Control

### Your Rights
- **Access**: All data is stored locally and accessible to you
- **Deletion**: Delete `processing_state.db` and reference encodings anytime
- **Portability**: All data in open formats (SQLite, JSON logs)

### Data Deletion
```bash
# Clear all processing state
rm processing_state.db

# Clear reference encodings
rm -r [reference_encodings_dir]

# Clear logs
rm -r logs/
```

## Compliance Considerations

### GDPR (Europe)
- Processing biometric data requires explicit consent
- Users have right to access, rectify, and delete their data
- This tool processes data locally under your control

### CCPA (California)
- Biometric information is protected under CCPA
- Users retain all rights to their biometric data
- No sale or sharing of biometric information

### BIPA (Illinois)
- Requires informed consent for biometric collection
- Must disclose retention and deletion policies
- This tool allows user-controlled deletion

**Important**: This tool is for personal use. If using for commercial purposes or processing others' photos, consult legal counsel regarding biometric privacy laws.

## Best Practices

1. **Obtain Consent**: If processing photos of others, obtain their consent
2. **Secure Your Machine**: Face encodings are only as secure as your local storage
3. **Regular Cleanup**: Periodically delete processing state and old logs
4. **Limit Reference Photos**: Only store necessary reference photos
5. **Review Logs**: Logs may contain file paths; secure or redact as needed

## Transparency

### What This Tool Does NOT Do
- ❌ Upload face data to cloud services
- ❌ Share data with third parties
- ❌ Collect telemetry or usage statistics
- ❌ Store unencrypted credentials
- ❌ Process data outside your control

### What This Tool DOES Do
- ✅ Process everything locally on your machine
- ✅ Store face encodings only on your device
- ✅ Give you full control over your data
- ✅ Use secure credential storage
- ✅ Provide transparent data handling

## Questions or Concerns

If you have questions about how your data is handled, please:
- Review the source code (it's open source)
- Open an issue on GitHub
- Contact [maintainer contact]

## Updates to This Policy

This privacy policy may be updated as the tool evolves. Major changes will be noted in release notes.

**Last Updated**: [Date]
```

### Additional Files

**README.md Section**

Add prominent privacy section:
```markdown
## Privacy and Data Handling

This tool processes facial recognition data entirely on your local machine. No face data or encodings are uploaded to external services. See [PRIVACY.md](docs/PRIVACY.md) for complete details.

**Key Points**:
- ✅ All processing happens locally
- ✅ No data sent to external servers (except Dropbox API)
- ✅ Face encodings never leave your device
- ✅ You have full control and can delete all data anytime
```

**Consent Prompt**

Add to first-run setup:
```python
def obtain_user_consent():
    """Display privacy notice and obtain consent on first run."""
    print("""
    PRIVACY NOTICE
    ==============
    This tool will:
    - Process facial recognition data on your local machine
    - Store face encodings locally at: [path]
    - Access your Dropbox photos via API
    - NOT upload face data to external services

    By continuing, you acknowledge that you:
    - Have read the privacy policy (docs/PRIVACY.md)
    - Consent to local facial recognition processing
    - Have rights to process the photos in your Dropbox
    - Will obtain consent if processing others' photos

    Do you wish to continue? (yes/no):
    """)

    response = input().strip().lower()
    if response != 'yes':
        print("Setup cancelled. No data was processed.")
        sys.exit(0)
```

### References

- [GDPR Biometric Data](https://gdpr-info.eu/issues/biometric-data/)
- [CCPA Biometric Information](https://oag.ca.gov/privacy/ccpa)
- [Illinois BIPA](https://www.ilga.gov/legislation/ilcs/ilcs3.asp?ActID=3004)

### Acceptance Criteria

- [ ] PRIVACY.md document created
- [ ] Privacy section added to README
- [ ] First-run consent prompt implemented
- [ ] Data deletion instructions documented
- [ ] Compliance considerations noted
- [ ] Transparency about data handling
- [ ] Regular review schedule established

---

## Issue 16: Implement Duplicate Detection and Handling

**Priority:** Medium (P2)
**Label:** enhancement, data-integrity
**Effort:** Low-Medium
**Impact:** Medium

### Description

The current design doesn't address duplicate detection:

- Same photo may be processed multiple times
- Photos could be copied/moved multiple times to target folder
- No deduplication based on content hash
- Wastes API calls and processing time

This is especially important for resume capability and avoiding redundant operations.

### Recommended Solution

Use Dropbox's `content_hash` for duplicate detection:

```python
import hashlib

def get_content_hash(file_metadata):
    """
    Extract Dropbox content_hash from file metadata.

    Dropbox provides a SHA256-based hash that's consistent
    across clients and uniquely identifies file content.
    """
    return file_metadata.content_hash

def is_duplicate(conn, content_hash, file_path):
    """
    Check if file with same content hash was already processed.

    Args:
        conn: Database connection
        content_hash: Dropbox content_hash of the file
        file_path: Current file path (may differ from original)

    Returns:
        True if duplicate, False otherwise
    """
    cursor = conn.execute(
        'SELECT file_path, processed_at FROM processed_files WHERE file_hash = ?',
        (content_hash,)
    )
    result = cursor.fetchone()

    if result:
        original_path, processed_at = result
        logging.info(
            f"Duplicate detected: {file_path} "
            f"(same as {original_path} processed at {processed_at})"
        )
        return True

    return False

def process_with_deduplication(file_metadata, conn):
    """Process file with duplicate detection."""
    content_hash = get_content_hash(file_metadata)
    file_path = file_metadata.path_display

    # Check if already processed
    if is_duplicate(conn, content_hash, file_path):
        logging.info(f"Skipping duplicate: {file_path}")
        return {'status': 'skipped', 'reason': 'duplicate'}

    # Process the file
    result = process_photo(file_path)

    # Record in database
    mark_processed(
        conn,
        file_path=file_path,
        file_hash=content_hash,
        match_result=result['match'],
        moved_to=result.get('destination')
    )

    return result
```

### Target Folder Duplicate Handling

```python
def check_target_folder_duplicates(dbx, target_folder):
    """
    Build index of files already in target folder to avoid re-copying.

    Returns:
        Set of content hashes present in target folder
    """
    existing_hashes = set()

    try:
        result = dbx.files_list_folder(target_folder, recursive=True)

        while True:
            for entry in result.entries:
                if isinstance(entry, dropbox.files.FileMetadata):
                    existing_hashes.add(entry.content_hash)

            if not result.has_more:
                break

            result = dbx.files_list_folder_continue(result.cursor)

    except dropbox.exceptions.ApiError as e:
        logging.error(f"Error checking target folder: {e}")

    logging.info(f"Found {len(existing_hashes)} existing files in target folder")
    return existing_hashes

def should_copy_to_target(file_metadata, target_hashes):
    """Check if file should be copied to target folder."""
    content_hash = file_metadata.content_hash

    if content_hash in target_hashes:
        logging.info(f"File already exists in target folder: {file_metadata.path_display}")
        return False

    return True
```

### Configuration

Add to `config.yaml`:
```yaml
processing:
  skip_duplicates: true
  duplicate_check_method: content_hash  # or 'path'
```

### Database Schema Update

```sql
CREATE TABLE IF NOT EXISTS processed_files (
    file_path TEXT,
    file_hash TEXT NOT NULL,  -- Dropbox content_hash
    processed_at TIMESTAMP,
    match_result BOOLEAN,
    moved_to TEXT,
    error_message TEXT,
    PRIMARY KEY (file_hash, file_path)
);

CREATE INDEX idx_file_hash ON processed_files(file_hash);
CREATE INDEX idx_processed_at ON processed_files(processed_at);
```

### Statistics Tracking

```python
class DuplicateStats:
    def __init__(self):
        self.total_files = 0
        self.duplicates_skipped = 0
        self.unique_processed = 0

    def summary(self):
        if self.total_files == 0:
            return "No files processed"

        dup_percentage = (self.duplicates_skipped / self.total_files) * 100

        return f"""
Duplicate Detection Summary
============================
Total files scanned: {self.total_files}
Duplicates skipped: {self.duplicates_skipped} ({dup_percentage:.1f}%)
Unique files processed: {self.unique_processed}
API calls saved: {self.duplicates_skipped * 2}  # Approximate
        """
```

### References

- [Dropbox content_hash](https://www.dropbox.com/developers/reference/content-hash)
- [Dropbox file metadata](https://www.dropbox.com/developers/documentation/http/documentation#files-get_metadata)

### Acceptance Criteria

- [ ] Content hash-based duplicate detection implemented
- [ ] Check target folder for existing files before copying
- [ ] Database tracks file hashes
- [ ] Configurable duplicate handling
- [ ] Statistics on duplicates skipped
- [ ] Logging of duplicate detections
- [ ] Documentation on how deduplication works
- [ ] Handle edge cases (hash collisions, moved files)

---

## Summary

These 16 issues cover the complete set of recommendations from the architecture review:

### Critical Priority (P1) - Implement First
1. Secure Access Token Storage
2. OAuth 2.0 Authorization Flow
3. State Persistence and Resume Capability
4. Test Suite
5. CI/CD Pipeline
6. Privacy Documentation

### High Priority (P2) - Phase 2
7. Face Recognition Accuracy (Two-Pass)
8. Reference Photo Handling
9. HEIC Support Decision
10. Copy vs Move Strategy
11. Rate Limiting
12. Configuration Validation
13. Logging Infrastructure
14. Performance Benchmarks
15. Duplicate Detection

### Medium Priority (P3) - Phase 3
16. Concurrent Processing

Each issue includes:
- Clear problem statement
- Recommended solution with code examples
- References to relevant documentation
- Acceptance criteria for completion
- Effort and impact assessment

These issues can be prioritized and implemented incrementally to transform the project into a production-ready tool.
