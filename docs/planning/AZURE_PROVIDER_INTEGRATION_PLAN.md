# Azure Face Recognition Provider Integration Plan

## Overview

Complete the Azure Face API provider integration by reviewing the existing implementation, adding comprehensive tests, and creating extensive documentation. The provider implementation already exists at `scripts/face_recognizer/providers/azure_provider.py`.

## Current State Analysis

### What Exists
- **Implementation**: `scripts/face_recognizer/providers/azure_provider.py` (264 lines)
- **Factory Registration**: Azure provider registered in `scripts/face_recognizer/__init__.py`
- **Configuration**: Azure config section in `config/config.example.yaml`
- **Architecture Docs**: Azure described in `docs/FACE_RECOGNITION_ARCHITECTURE.md`

### What's Missing
- Unit tests (no `tests/test_azure_provider.py`)
- Setup guide (no `docs/AZURE_FACE_RECOGNITION_SETUP.md`)
- Optional dependencies file for Azure
- Documentation updates to reflect completion status

---

## Implementation Plan

### Phase 0: Code Review (`scripts/face_recognizer/providers/azure_provider.py`)

Review existing implementation for:

1. **Error Handling**
   - API error responses (rate limits, auth failures, invalid images)
   - Network timeouts and retries
   - Graceful degradation

2. **Best Practices**
   - Type hints completeness
   - Logging consistency
   - Resource cleanup

3. **Azure API Usage**
   - Recognition model version (currently recognition_04 - latest)
   - Detection model version (currently detection_03 - latest)
   - Person Group handling edge cases
   - Training timeout handling

4. **Potential Improvements Identified**
   - [ ] Add retry logic for transient API failures
   - [ ] Add configurable training timeout
   - [ ] Improve error messages for common failures
   - [ ] Add face quality attributes usage (optional)

---

### Phase 1: Unit Tests (`tests/test_azure_provider.py`)

Create comprehensive unit tests following patterns from `test_local_provider.py`:

```
tests/test_azure_provider.py
├── TestAzureProviderImport
│   └── test_import_error_when_azure_not_available
├── TestAzureFaceRecognitionProviderInit
│   ├── test_init_with_required_config
│   ├── test_init_missing_api_key_raises_error
│   ├── test_init_missing_endpoint_raises_error
│   └── test_init_stores_default_values
├── TestGetProviderName
│   └── test_get_provider_name_returns_azure
├── TestValidateConfiguration
│   ├── test_validate_configuration_success
│   ├── test_validate_configuration_azure_unavailable
│   └── test_validate_configuration_api_error
├── TestPersonGroupManagement
│   ├── test_create_or_get_person_group_existing
│   ├── test_create_or_get_person_group_new
│   └── test_create_or_get_person_existing_person
├── TestLoadReferencePhotos
│   ├── test_load_reference_photos_success
│   ├── test_load_reference_photos_file_not_found
│   ├── test_load_reference_photos_training_success
│   └── test_load_reference_photos_training_failure
├── TestDetectFaces
│   ├── test_detect_faces_success
│   ├── test_detect_faces_no_faces_found
│   └── test_detect_faces_api_error
├── TestCompareFaces
│   ├── test_compare_faces_match_found
│   ├── test_compare_faces_no_match
│   ├── test_compare_faces_no_person_id
│   └── test_compare_faces_api_error
└── TestAzureProviderIntegration
    └── test_full_workflow_mock
```

**Key Testing Considerations:**
- Mock `azure.cognitiveservices.vision.face.FaceClient`
- Mock `msrest.authentication.CognitiveServicesCredentials`
- Mock `TrainingStatusType` for training workflow tests
- Use `autouse` fixture pattern for `AZURE_AVAILABLE` mocking
- Test API error handling (authentication, rate limits, etc.)

---

### Phase 2: Setup Documentation (`docs/AZURE_FACE_RECOGNITION_SETUP.md`)

Create comprehensive setup guide following structure of `FACE_RECOGNITION_LOCAL_SETUP.md`:

```markdown
# Azure Face Recognition Setup Guide

## Table of Contents
- Overview
- Prerequisites
- Azure Account Setup
  - Creating Azure Account
  - Creating Face API Resource
  - Getting API Key and Endpoint
- Installation
  - Python Dependencies
  - Verifying Installation
- Configuration
  - config.yaml Settings
  - Person Groups Explained
- First Training Run
  - Preparing Reference Photos
  - Running Training Script
  - Verifying Training Status
- API Usage and Costs
  - Pricing Tiers
  - Rate Limits
  - Cost Optimization Tips
- Troubleshooting
  - Authentication Errors
  - Training Failures
  - Rate Limit Errors
- Security Considerations
  - API Key Management
  - Data Privacy (GDPR/CCPA)
- Next Steps
```

**Key Content Areas:**
- Step-by-step Azure Portal instructions
- Pricing information (30k free transactions/month)
- Person Group concept explanation
- Training workflow (async, requires polling)
- Recognition model versions (recognition_04)
- Detection model versions (detection_03)

---

### Phase 3: Documentation Updates

#### 3.1 Update `docs/INDEX.md`
Add Azure setup guide to documentation index under "Setup Guides" section.

#### 3.2 Update `docs/FACE_RECOGNITION_ARCHITECTURE.md`
- Mark Azure provider as ✅ Complete in TODO section
- Add any implementation notes discovered during testing

#### 3.3 Update `docs/planning/TASK_MANAGEMENT.md`
- Add task for Azure provider completion if not exists
- Mark as complete once done

#### 3.4 Update `README.md`
- Ensure Azure is mentioned in face recognition provider options
- Reference `requirements-azure.txt` for Azure dependencies

---

### Phase 4: Validation

1. Run new tests: `pytest tests/test_azure_provider.py -v`
2. Run full test suite: `pytest tests/ -v --cov=scripts`
3. Run pre-commit hooks: `pre-commit run --all-files`
4. Verify documentation renders correctly

---

## Files to Create/Modify

### New Files

| File | Purpose |
|------|---------|
| `tests/test_azure_provider.py` | Comprehensive unit tests (~400 lines) |
| `docs/AZURE_FACE_RECOGNITION_SETUP.md` | User setup guide (~500 lines) |
| `requirements-azure.txt` | Optional Azure SDK dependencies |

### Modified Files

| File | Changes |
|------|---------|
| `scripts/face_recognizer/providers/azure_provider.py` | Bug fixes and improvements from code review |
| `docs/INDEX.md` | Add Azure setup guide link |
| `docs/FACE_RECOGNITION_ARCHITECTURE.md` | Update completion status |
| `README.md` | Reference Azure setup guide and requirements-azure.txt |

---

## Dependencies

Create `requirements-azure.txt` with Azure provider dependencies:

```
# Azure Face Recognition Provider Dependencies
# Install with: pip install -r requirements-azure.txt

azure-cognitiveservices-vision-face>=0.6.0
msrest>=0.7.0
```

This keeps Azure dependencies optional and follows the pattern of:
- `requirements.txt` - Core dependencies
- `requirements-dev.txt` - Development dependencies (already exists)
- `requirements-azure.txt` - Azure provider dependencies (new)

---

## Estimated Effort

| Phase | Description | Effort |
|-------|-------------|--------|
| Phase 0 | Code Review | Review + improvements to azure_provider.py |
| Phase 1 | Unit Tests | ~300-400 lines of test code |
| Phase 2 | Setup Guide | ~400-500 lines of documentation |
| Phase 3 | Doc Updates | ~20-30 lines + requirements-azure.txt |
| Phase 4 | Validation | Testing and verification |

---

## Success Criteria

- [ ] All new tests pass
- [ ] Test coverage for azure_provider.py > 80%
- [ ] Pre-commit hooks pass
- [ ] Documentation is clear and actionable
- [ ] CI pipeline passes

---

## References

- [Azure Face API Documentation](https://docs.microsoft.com/en-us/azure/cognitive-services/face/)
- [Azure Face Python SDK](https://pypi.org/project/azure-cognitiveservices-vision-face/)
- [Existing Local Provider Tests](../tests/test_local_provider.py)
- [Face Recognition Architecture](./FACE_RECOGNITION_ARCHITECTURE.md)
