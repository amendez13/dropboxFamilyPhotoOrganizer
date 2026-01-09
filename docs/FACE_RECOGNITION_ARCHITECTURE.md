# Face Recognition Architecture

This document describes the architecture, design decisions, and implementation details of the face recognition component in the Dropbox Photo Organizer.

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Design Decisions](#design-decisions)
- [Provider Implementations](#provider-implementations)
- [Configuration](#configuration)
- [TODO & Future Enhancements](#todo--future-enhancements)

---

## Overview

The face recognition component is designed to detect a specific person in photos stored in Dropbox. It uses a **provider pattern** to support multiple face recognition backends, allowing users to choose between local (offline) processing or cloud-based AI services.

### Core Workflow

```
1. Load Reference Photos → Extract face encodings of target person
2. Scan Dropbox Folder → List all photos recursively
3. For Each Photo:
   a. Download thumbnail (for efficiency)
   b. Detect faces
   c. Compare against reference encodings
   d. If match: Add to results
4. Move/Report Matches → Based on configuration (dry-run or actual move)
```

---

## Architecture

### Design Pattern: Strategy + Factory

The architecture uses two key design patterns:

1. **Strategy Pattern**: Allows switching between different face recognition algorithms at runtime
2. **Factory Pattern**: Provides a centralized way to instantiate providers

### Module Structure

```
scripts/face_recognition/
├── __init__.py                  # Factory for creating providers
├── base_provider.py             # Abstract base class (interface)
└── providers/
    ├── __init__.py
    ├── local_provider.py        # Local face_recognition (dlib)
    ├── aws_provider.py          # AWS Rekognition
    └── azure_provider.py        # Azure Face API
```

### Class Hierarchy

```
BaseFaceRecognitionProvider (ABC)
│
├── LocalFaceRecognitionProvider
│   └── Uses: face_recognition library (dlib)
│
├── AWSFaceRecognitionProvider
│   └── Uses: boto3 → AWS Rekognition API
│
└── AzureFaceRecognitionProvider
    └── Uses: Azure Cognitive Services Face API
```

### Core Data Models

#### `FaceEncoding`
```python
@dataclass
class FaceEncoding:
    encoding: np.ndarray           # Face feature vector
    source: str                    # Source file/identifier
    confidence: Optional[float]    # Detection confidence (0-1)
    bounding_box: Optional[Tuple]  # (top, right, bottom, left)
```

#### `FaceMatch`
```python
@dataclass
class FaceMatch:
    is_match: bool                 # Whether face matches reference
    confidence: float              # Match confidence (0-1)
    distance: float                # Distance metric (lower = more similar)
    matched_encoding: Optional[FaceEncoding]
```

### Interface Contract

All providers must implement:

| Method | Description | Returns |
|--------|-------------|---------|
| `load_reference_photos(paths)` | Load and encode reference photos | Count of faces loaded |
| `detect_faces(image_data, source)` | Detect faces in an image | List[FaceEncoding] |
| `compare_faces(encoding, tolerance)` | Compare face against references | FaceMatch |
| `find_matches_in_image(image_data, source, tolerance)` | Complete workflow | (matches, total_faces) |
| `get_provider_name()` | Get provider identifier | str |
| `validate_configuration()` | Validate provider config | (is_valid, error_msg) |

---

## Design Decisions

### 1. Provider Abstraction

**Decision**: Use abstract base class with multiple concrete implementations

**Rationale**:
- Different use cases require different solutions:
  - Local: Privacy-conscious users, no API costs, offline
  - AWS/Azure: Production scale, higher accuracy, no local setup
- Easy to add new providers (Google Vision, custom models)
- Users can switch providers without changing application code

**Trade-offs**:
- More complex than single implementation
- Each provider has different setup requirements
- Need to maintain multiple implementations

### 2. Lazy Loading of Providers

**Decision**: Provider dependencies are optional; imported only when used

**Rationale**:
- Users don't need to install all dependencies
- Smaller installation footprint
- Faster setup for single-provider use

**Implementation**:
```python
try:
    import face_recognition
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
```

### 3. Configuration-Driven Selection

**Decision**: Provider selection via YAML configuration

**Rationale**:
- Easy to switch between providers for testing
- No code changes needed
- Can store different configs for different scenarios

**Example**:
```yaml
face_recognition:
  provider: "local"  # or "aws" or "azure"
```

### 4. Thumbnail-Based Processing (Default)

**Decision**: Use Dropbox thumbnails (256x256) instead of full images by default

**Rationale**:
- **Bandwidth**: 10-50x less data to download
- **Speed**: Faster processing (smaller images)
- **Accuracy**: Sufficient for face detection in most cases
- **Cost**: Lower API costs for cloud providers

**Trade-off**: May miss faces that are very small or distant in original image

**Future**: Implement hybrid approach (thumbnail first, full image for uncertain matches)

### 5. Reference Encoding Pre-computation

**Decision**: Compute reference face encodings once at startup

**Rationale**:
- Reference photos don't change during processing
- Avoids re-processing reference images for each comparison
- Much faster (one-time cost vs. per-photo cost)

**Implementation**: Stored in `provider.reference_encodings` list

### 6. Provider-Specific Optimizations

**Decision**: Each provider uses its API's strengths, not forced into common pattern

**Examples**:
- **Local**: Uses face_recognition's batch encoding
- **AWS**: Uses `compare_faces` API (compares images directly, more efficient than detect + compare)
- **Azure**: Uses Person Groups with training (persistent face database)

**Trade-off**: Providers work slightly differently, but each is optimized

---

## Provider Implementations

### Local Provider (`local_provider.py`) ✅ Implemented

**Technology**: `face_recognition` library (dlib-based)

**Pros**:
- ✅ Free, no API costs
- ✅ Works offline
- ✅ Privacy-friendly (data never leaves machine)
- ✅ Good accuracy for family photos
- ✅ Simple setup once dependencies installed

**Cons**:
- ❌ Complex installation (requires cmake, C++ compiler, dlib)
- ❌ Slower than cloud APIs (CPU-only by default)
- ❌ No GPU acceleration without additional setup

**Configuration**:
```yaml
face_recognition:
  local:
    model: "hog"       # 'hog' (faster) or 'cnn' (more accurate)
    num_jitters: 1     # Higher = more accurate, slower
```

**Best For**: Getting started, small libraries (<10k photos), privacy-conscious users

---

### AWS Provider (`aws_provider.py`)

**Technology**: AWS Rekognition via boto3

**Pros**:
- ✅ High accuracy
- ✅ Fast processing
- ✅ Highly scalable
- ✅ No local setup/dependencies
- ✅ Optimized `compare_faces` API

**Cons**:
- ❌ Requires AWS account
- ❌ API costs ($1 per 1,000 images)
- ❌ Data sent to AWS
- ❌ Requires internet connection

**Configuration**:
```yaml
face_recognition:
  aws:
    aws_access_key_id: "..."      # Optional if using AWS CLI
    aws_secret_access_key: "..."  # Optional if using AWS CLI
    aws_region: "us-east-1"
    similarity_threshold: 80.0    # 0-100 percentage
```

**Best For**: Production deployments, large libraries (>10k photos), cloud-first architecture

**API Usage**:
- Reference photos: `detect_faces` (one-time)
- Per photo: `compare_faces` (compares directly)

---

### Azure Provider (`azure_provider.py`) ✅ Implemented

**Technology**: Azure Cognitive Services Face API

**Pros**:
- ✅ High accuracy
- ✅ Persistent face data (Person Groups)
- ✅ Pre-trained models
- ✅ Good for multi-person scenarios
- ✅ Face identification (not just verification)
- ✅ No local dependencies (no dlib/cmake required)

**Cons**:
- ❌ Requires Azure account
- ❌ API costs (30k transactions free/month)
- ❌ Data sent to Azure
- ❌ More complex setup (Person Groups, training)
- ❌ Requires internet connection

**Configuration**:
```yaml
face_recognition:
  azure:
    azure_api_key: "..."
    azure_endpoint: "https://eastus.api.cognitive.microsoft.com"
    person_group_id: "dropbox-photo-organizer"
    confidence_threshold: 0.5
    training_timeout: 300  # seconds
```

**Best For**: Enterprise deployments, scenarios requiring persistent face database, multi-person identification

**API Usage**:
- Reference photos:
  1. Create Person Group
  2. Create Person
  3. Add faces to Person
  4. Train Person Group (async with timeout)
- Per photo:
  1. Detect faces
  2. Identify against Person Group

**Setup Guide**: See [AZURE_FACE_RECOGNITION_SETUP.md](AZURE_FACE_RECOGNITION_SETUP.md) for detailed instructions.

---

## Configuration

### Provider Selection

```yaml
face_recognition:
  provider: "local"  # Choose: local, aws, or azure
```

### Common Settings

```yaml
face_recognition:
  reference_photos_dir: "./reference_photos"
  tolerance: 0.6              # Lower = stricter matching
  thumbnail_size: "w256h256"  # Dropbox thumbnail size
```

### Provider-Specific Settings

Each provider has its own configuration section:

```yaml
face_recognition:
  local:
    model: "hog"
    num_jitters: 1

  aws:
    aws_region: "us-east-1"
    similarity_threshold: 80.0

  azure:
    azure_api_key: "..."
    person_group_id: "..."
    confidence_threshold: 0.5
```

---

## TODO & Future Enhancements

### High Priority

- [ ] **Implement photo processor pipeline** (`photo_processor.py`)
  - State management for resume capability
  - Progress tracking
  - Error handling and retry logic
  - Batch processing with configurable batch size

- [ ] **Create main organizer script** (`organize_photos.py`)
  - CLI interface
  - Dry-run mode
  - Statistics reporting
  - Move/copy operations

- [ ] **Add caching layer**
  - Cache reference encodings to file
  - Cache processed photo results
  - Support resume after interruption

- [ ] **Comprehensive error handling**
  - Network failures
  - API rate limits
  - Malformed images
  - Missing faces in reference photos

### Medium Priority

- [ ] **Hybrid processing mode**
  - Start with thumbnails
  - Re-process uncertain matches with full images
  - Configurable confidence threshold for re-processing

- [ ] **Progress indicators**
  - Terminal progress bar (tqdm)
  - ETA calculation
  - Speed metrics (photos/second)

- [ ] **Multiple target persons**
  - Support multiple reference photo sets
  - Move to different folders per person
  - Label/tag system

- [ ] **Result persistence**
  - SQLite database for processed photos
  - CSV export of matches
  - JSON report generation

- [ ] **Testing suite**
  - Unit tests for each provider
  - Integration tests with mock providers
  - Performance benchmarks

### Low Priority / Future

- [ ] **Additional providers**
  - Google Cloud Vision
  - Face++ API
  - Custom TensorFlow/PyTorch models

- [ ] **Performance optimizations**
  - Parallel processing (multiprocessing)
  - GPU acceleration for local provider
  - Async I/O for API calls

- [ ] **Web interface**
  - Flask/FastAPI web UI
  - Preview matches before moving
  - Manual verification workflow

- [ ] **Advanced features**
  - Face clustering (group by person automatically)
  - Age/gender filtering
  - Emotion detection
  - Face tagging in EXIF metadata

- [ ] **Quality improvements**
  - Face quality scoring
  - Blur detection
  - Lighting quality assessment
  - Automatic reference photo selection

---

## Implementation Notes

### Adding a New Provider

To add a new face recognition provider:

1. Create new file in `scripts/face_recognition/providers/`
2. Inherit from `BaseFaceRecognitionProvider`
3. Implement all abstract methods
4. Add provider to factory in `__init__.py`
5. Update configuration schema
6. Update documentation

Example skeleton:

```python
from scripts.face_recognition.base_provider import BaseFaceRecognitionProvider

class CustomProvider(BaseFaceRecognitionProvider):
    def get_provider_name(self) -> str:
        return "custom"

    def validate_configuration(self):
        # Check API keys, etc.
        pass

    def load_reference_photos(self, photo_paths):
        # Load and encode reference photos
        pass

    def detect_faces(self, image_data, source):
        # Detect faces in image
        pass

    def compare_faces(self, face_encoding, tolerance):
        # Compare against references
        pass
```

### Testing Providers

Each provider should be testable independently:

```python
# Test script
from scripts.face_recognition import get_provider

config = {...}
provider = get_provider("local", config)

# Validate
is_valid, error = provider.validate_configuration()
assert is_valid

# Load references
count = provider.load_reference_photos(["ref1.jpg"])
assert count > 0

# Test detection
with open("test.jpg", "rb") as f:
    matches, total = provider.find_matches_in_image(f.read())
```

---

## Performance Considerations

### Bottlenecks

1. **Network I/O**: Downloading photos from Dropbox
   - Mitigation: Use thumbnails, batch downloads

2. **API Rate Limits**: Cloud providers have rate limits
   - Mitigation: Implement backoff, respect limits

3. **Face Detection**: CPU-intensive for local provider
   - Mitigation: Use 'hog' model, consider GPU

4. **Sequential Processing**: Photos processed one by one
   - Future: Implement parallel processing

### Optimization Strategies

- Use thumbnails for initial scan
- Batch API calls where possible
- Cache results to avoid reprocessing
- Implement resume capability for large libraries
- Consider pre-processing (face quality filtering)

---

## Security & Privacy

### Local Provider
- ✅ All processing happens locally
- ✅ No data leaves the machine
- ✅ Full privacy

### Cloud Providers (AWS, Azure)
- ⚠️ Images sent to cloud provider
- ⚠️ Face data processed on provider's servers
- ⚠️ Subject to provider's data retention policies
- ⚠️ Requires secure credential management

**Recommendation**: Use local provider for sensitive/private photos. Use cloud providers for non-sensitive or professional use cases.

---

## References

- [face_recognition library](https://github.com/ageitgey/face_recognition)
- [AWS Rekognition Documentation](https://docs.aws.amazon.com/rekognition/)
- [Azure Face API Documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/face/)
- [dlib face recognition](http://dlib.net/face_recognition.py.html)
