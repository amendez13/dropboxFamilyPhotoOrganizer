# AWS Face Recognition Provider Integration Plan

## Overview

Complete the AWS Rekognition face recognition provider integration by reviewing the existing implementation, adding comprehensive tests, creating setup documentation, and implementing missing features like retry logic. The provider implementation already exists at `scripts/face_recognizer/providers/aws_provider.py`.

## Current State Analysis

### What Exists
- **Implementation**: `scripts/face_recognizer/providers/aws_provider.py` (260 lines)
- **Factory Registration**: AWS provider registered in `scripts/face_recognizer/__init__.py`
- **Configuration**: AWS config section exists in `config/config.example.yaml`
- **Architecture Docs**: AWS mentioned in `docs/FACE_RECOGNITION_ARCHITECTURE.md`

### What's Missing
- Unit tests (no `tests/test_aws_provider.py`)
- Setup guide (no `docs/AWS_FACE_RECOGNITION_SETUP.md`)
- Optional dependencies file (no `requirements-aws.txt`)
- Retry logic for transient API failures
- Rate limit handling (unlike Azure provider)
- Documentation updates to reflect completion status

---

## Implementation Plan

### Phase 0: Code Review and Improvements

**File**: `scripts/face_recognizer/providers/aws_provider.py`

Review and improve existing implementation:

1. **Add Retry Logic** (Critical)
   - Port `@retry_with_backoff` decorator from Azure provider
   - Apply to `detect_faces`, `compare_faces`, and `load_reference_photos` API calls
   - Handle AWS rate limits (ThrottlingException)
   - Handle transient errors (ServiceUnavailableException, InternalServerError)

2. **Improve Error Handling**
   - Add specific exception handling for common AWS errors
   - Better error messages for credential failures
   - Handle image size limits (5MB for API, 15MB for S3)

3. **Enhance Configuration Validation**
   - Add region validation
   - Check for valid credential combinations
   - Validate similarity_threshold range (0-100)

4. **Code Quality**
   - Complete type hints
   - Consistent logging format (match Azure provider)
   - Add bounding box extraction from AWS response

---

### Phase 1: Unit Tests (`tests/test_aws_provider.py`)

Create comprehensive unit tests following patterns from `test_azure_provider.py`:

```
tests/test_aws_provider.py
├── TestAWSProviderImport
│   └── test_import_error_when_boto3_not_available
├── TestAWSFaceRecognitionProviderInit
│   ├── test_init_with_required_config
│   ├── test_init_with_aws_credentials_in_config
│   ├── test_init_uses_aws_cli_credentials_by_default
│   ├── test_init_custom_region
│   └── test_init_stores_default_similarity_threshold
├── TestGetProviderName
│   └── test_get_provider_name_returns_aws
├── TestValidateConfiguration
│   ├── test_validate_configuration_success
│   ├── test_validate_configuration_boto3_unavailable
│   ├── test_validate_configuration_invalid_credentials
│   └── test_validate_configuration_invalid_region
├── TestLoadReferencePhotos
│   ├── test_load_reference_photos_success
│   ├── test_load_reference_photos_file_not_found
│   ├── test_load_reference_photos_no_faces_detected
│   ├── test_load_reference_photos_api_error
│   ├── test_load_reference_photos_multiple_photos
│   └── test_load_reference_photos_clears_previous
├── TestDetectFaces
│   ├── test_detect_faces_success
│   ├── test_detect_faces_no_faces_found
│   ├── test_detect_faces_api_error
│   ├── test_detect_faces_throttling_retry
│   └── test_detect_faces_confidence_normalization
├── TestCompareFaces
│   └── test_compare_faces_returns_no_match (documented limitation)
├── TestFindMatchesInImage
│   ├── test_find_matches_success
│   ├── test_find_matches_no_match
│   ├── test_find_matches_multiple_references
│   ├── test_find_matches_api_error
│   ├── test_find_matches_custom_tolerance
│   └── test_find_matches_throttling_retry
└── TestAWSProviderIntegration
    └── test_full_workflow_mock
```

**Key Testing Considerations:**
- Mock `boto3.client('rekognition')`
- Mock `botocore.exceptions.ClientError` for error scenarios
- Use `autouse` fixture pattern for `AWS_AVAILABLE` mocking
- Test retry behavior for ThrottlingException
- Test confidence/similarity conversion (percentage to 0-1)

---

### Phase 2: Setup Documentation (`docs/AWS_FACE_RECOGNITION_SETUP.md`)

Create comprehensive setup guide (~400-500 lines):

```markdown
# AWS Face Recognition Setup Guide

## Table of Contents
- Overview
- Prerequisites
- AWS Account Setup
  - Creating AWS Account
  - Creating IAM User/Role
  - Setting Up Permissions (rekognition:*)
  - Getting Access Keys
- Installation
  - Python Dependencies
  - AWS CLI Configuration (optional)
  - Verifying Installation
- Configuration
  - config.yaml Settings
  - Credential Options (config vs AWS CLI vs IAM role)
- First Run
  - Preparing Reference Photos
  - Testing Connection
  - Running Photo Organizer
- API Usage and Costs
  - Pricing Breakdown ($1 per 1,000 images)
  - Free Tier (5,000 images/month for 12 months)
  - Rate Limits (50 TPS default)
  - Cost Optimization Tips
- Troubleshooting
  - Authentication Errors
  - Rate Limit Errors
  - Image Format Issues
  - Region Configuration
- Security Considerations
  - IAM Best Practices
  - Credential Management
  - Data Privacy
- Comparison with Other Providers
- Next Steps
```

**Key Content Areas:**
- Step-by-step AWS Console instructions with screenshots references
- IAM policy JSON for minimum required permissions
- Three credential methods: config file, AWS CLI, IAM role
- Pricing calculator and cost estimates
- Rate limit guidance and when to request increases

---

### Phase 3: Requirements File (`requirements-aws.txt`)

Create optional dependencies file:

```
# AWS Face Recognition Provider Dependencies
# Install with: pip install -r requirements-aws.txt

boto3>=1.26.0
botocore>=1.29.0
```

---

### Phase 4: Documentation Updates

#### 4.1 Update `docs/INDEX.md`
Add AWS setup guide link under "Setup Guides" section.

#### 4.2 Update `docs/FACE_RECOGNITION_ARCHITECTURE.md`
- Mark AWS provider as ✅ Implemented
- Add implementation notes from code review

#### 4.3 Update `README.md`
- Add AWS as Option C in Face Recognition Setup section
- Reference `requirements-aws.txt`
- Link to AWS setup guide

#### 4.4 Update `config/config.example.yaml`
- Ensure AWS configuration section is complete with comments

---

### Phase 5: Validation

1. Run new tests: `pytest tests/test_aws_provider.py -v`
2. Run full test suite: `pytest tests/ -v --cov=scripts`
3. Verify coverage: `pytest tests/test_aws_provider.py -v --cov=scripts/face_recognizer/providers/aws_provider --cov-report=term-missing`
4. Run pre-commit hooks: `pre-commit run --all-files`
5. Verify documentation renders correctly

---

## Files to Create/Modify

### New Files

| File | Purpose | Est. Lines |
|------|---------|------------|
| `tests/test_aws_provider.py` | Comprehensive unit tests | ~400 |
| `docs/AWS_FACE_RECOGNITION_SETUP.md` | User setup guide | ~500 |
| `requirements-aws.txt` | Optional AWS SDK dependencies | ~5 |

### Modified Files

| File | Changes |
|------|---------|
| `scripts/face_recognizer/providers/aws_provider.py` | Add retry logic, improve error handling |
| `docs/INDEX.md` | Add AWS setup guide link |
| `docs/FACE_RECOGNITION_ARCHITECTURE.md` | Mark AWS as complete |
| `README.md` | Add AWS provider option |
| `config/config.example.yaml` | Complete AWS config section |

---

## GitHub Issues (Discrete Tasks)

### Issue 1: AWS provider baseline tests and requirements file
**Labels**: `testing`, `aws-provider`, `dependencies`

**Description**: Create comprehensive unit tests for the existing AWS Rekognition provider implementation and add the optional dependencies file. This establishes test coverage for the current codebase before adding new features.

**Files to Create**:
- `tests/test_aws_provider.py` - Unit tests for existing functionality
- `requirements-aws.txt` - Optional AWS SDK dependencies

**Acceptance Criteria**:
- [ ] Test file created at `tests/test_aws_provider.py`
- [ ] Tests cover: init, get_provider_name, validate_configuration, load_reference_photos, detect_faces, compare_faces, find_matches_in_image
- [ ] Error scenarios covered (file not found, API errors, no faces detected)
- [ ] `requirements-aws.txt` created with boto3 and botocore
- [ ] Test coverage for aws_provider.py > 80%
- [ ] CI pipeline passes

---

### Issue 2: Add retry logic and error handling to AWS provider
**Labels**: `enhancement`, `aws-provider`

**Description**: Port the `@retry_with_backoff` decorator from Azure provider to handle transient AWS API failures. Improve error handling for common failure scenarios. Include tests for all new functionality.

**Files to Modify**:
- `scripts/face_recognizer/providers/aws_provider.py` - Add retry decorator and improved error handling

**Tests to Add** (in same PR):
- `test_detect_faces_throttling_retry`
- `test_find_matches_throttling_retry`
- `test_load_reference_photos_retry`
- Tests for specific AWS error codes

**Acceptance Criteria**:
- [ ] Retry decorator added with exponential backoff (max_retries=3, base_delay=1.0)
- [ ] Applied to detect_faces, find_matches_in_image, load_reference_photos API calls
- [ ] Handles ThrottlingException, ServiceUnavailableException, InternalServerError
- [ ] Unit tests for retry behavior included
- [ ] All tests pass

---

### Issue 3: Create AWS Face Recognition setup documentation
**Labels**: `documentation`, `aws-provider`

**Description**: Create comprehensive setup guide for AWS Rekognition provider with step-by-step instructions for AWS account setup, IAM configuration, and troubleshooting.

**Files to Create**:
- `docs/AWS_FACE_RECOGNITION_SETUP.md` - Complete setup guide (~500 lines)

**Acceptance Criteria**:
- [ ] AWS account setup instructions
- [ ] IAM user/role creation with minimum permissions
- [ ] IAM policy JSON provided
- [ ] Three credential methods documented (config file, AWS CLI, IAM role)
- [ ] Pricing breakdown ($1/1000 images, free tier info)
- [ ] Rate limits and optimization tips
- [ ] Troubleshooting section (auth errors, rate limits, image format)
- [ ] Security best practices

---

### Issue 4: Update documentation for AWS provider completion
**Labels**: `documentation`, `aws-provider`

**Description**: Update all relevant documentation files to reflect AWS provider completion and integrate the new setup guide.

**Files to Modify**:
- `docs/INDEX.md` - Add AWS setup guide link under "Setup Guides"
- `docs/FACE_RECOGNITION_ARCHITECTURE.md` - Mark AWS as ✅ Implemented
- `README.md` - Add AWS as Option C in Face Recognition Setup, reference requirements-aws.txt
- `config/config.example.yaml` - Ensure AWS config section is complete with comments

**Acceptance Criteria**:
- [ ] AWS setup guide linked in INDEX.md
- [ ] AWS marked as ✅ Implemented in architecture doc
- [ ] README includes AWS provider option with install instructions
- [ ] config.example.yaml has complete AWS section with documentation
- [ ] All cross-references are correct

---

## Dependencies

AWS SDK requirements:
- `boto3>=1.26.0` - AWS SDK for Python
- `botocore>=1.29.0` - Core functionality for boto3

---

## Success Criteria

- [ ] All new tests pass
- [ ] Test coverage for aws_provider.py > 80%
- [ ] Pre-commit hooks pass
- [ ] Documentation is clear and actionable
- [ ] CI pipeline passes
- [ ] Retry logic handles rate limits gracefully

---

## References

- [AWS Rekognition Documentation](https://docs.aws.amazon.com/rekognition/)
- [AWS Rekognition Python SDK](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/rekognition.html)
- [AWS Rekognition Pricing](https://aws.amazon.com/rekognition/pricing/)
- [Existing Azure Provider Tests](../tests/test_azure_provider.py)
- [Face Recognition Architecture](./FACE_RECOGNITION_ARCHITECTURE.md)
