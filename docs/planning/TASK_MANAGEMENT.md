# Task Management

This document tracks all tasks for the Dropbox Family Photo Organizer project, organized by priority and category based on the comprehensive architecture review.

## Project Development Phases

The project is structured into three main phases:

### Phase 1: Dropbox API Integration ✅ (Complete)
- Dropbox authentication
- Folder listing and file traversal
- File download and thumbnail retrieval
- File moving capabilities

### Phase 2: Face Recognition Integration 🔲 (In Planning)
- Load reference photos
- Process images with face detection
- Match faces against reference encodings
- Generate match reports

### Phase 3: Automation and Polish 🔲 (Future)
- Command-line interface
- Progress bars and better logging
- Resume capability for interrupted runs
- Statistics and reporting

## Architecture Review Tasks

The following tasks were identified through a comprehensive architecture review. They are organized by priority (P1-P3) and category.

### Task Summary Table

| Priority | Issue # | Task | Category | Effort | Impact | Phase | Status |
|----------|---------|------|----------|--------|--------|-------|--------|
| **P1** | [#10](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/10) | Implement Secure Access Token Storage | Security | Low | High | Now | 🔲 |
| **P1** | [#11](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/11) | Implement OAuth 2.0 Authorization Flow with Refresh Tokens | Security | Medium | High | Now | 🔲 |
| **P1** | [#12](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/12) | Implement State Persistence and Resume Capability | Reliability | Medium | Critical | Now | 🔲 |
| **P1** | [#13](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/13) | Create Comprehensive Test Suite | Testing | Medium | High | Ongoing | 🔄 |
| **P1** | [#14](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/14) | Set Up CI/CD Pipeline with GitHub Actions | Infrastructure | Low | High | Now | ✅ |
| **P1** | [#15](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/15) | Document Privacy and Biometric Data Handling | Documentation | Low | High | Now | 🔲 |
| **P2** | [#16](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/16) | Implement Two-Pass Face Recognition Strategy | Face Recognition | Medium | Medium | Phase 2 | 🔲 |
| **P2** | [#17](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/17) | Implement Multiple Reference Photo Voting Strategy | Face Recognition | Medium | Medium | Phase 2 | 🔲 |
| **P2** | [#18](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/18) | Add HEIC Support or Document Limitation | Enhancement | Low | Low | Phase 2 | 🔲 |
| **P2** | [#19](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/19) | Change Default Operation from Move to Copy | Safety | Low | Medium | Phase 2 | ✅ |
| **P2** | [#20](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/20) | Implement API Rate Limiting and Exponential Backoff | Reliability | Low | Medium | Phase 2 | 🔲 |
| **P2** | [#21](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/21) | Add Configuration Schema Validation with Pydantic | Reliability | Low | Medium | Phase 2 | 🔲 |
| **P2** | [#22](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/22) | Implement Structured Logging Infrastructure | Observability | Low | Medium | Phase 2 | 🔲 |
| **P2** | [#23](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/23) | Establish Performance Benchmarks and Monitoring | Performance | Medium | Medium | Phase 2 | 🔲 |
| **P2** | [#24](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/24) | Implement Content Hash-Based Duplicate Detection | Enhancement | Low | Medium | Phase 2 | 🔲 |
| **P2** | [#28](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/28) | Address Race Condition in Audit Logging | Reliability | Low | Medium | Phase 2 | 🔲 |
| **P2** | [#29](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/29) | Prevent Log Injection Vulnerability in Audit Logging | Security | Low | Medium | Phase 2 | 🔲 |
| **P2** | [#33](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/33) | Enforce flake8 Checks: Remove --exit-zero Flag and Fix Warnings | Code Quality | Low | Medium | Phase 2 | 🔲 |
| **P2** | [#34](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/34) | Enforce mypy Type Checking: Remove \|\| true and Fix Type Errors | Code Quality | Medium | Medium | Phase 2 | 🔲 |
| **P2** | [#35](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/35) | Make Security Checks Blocking: Enforce bandit and safety Scans | Security | Low | High | Phase 2 | 🔲 |
| **P3** | [#25](https://github.com/amendez13/dropboxFamilyPhotoOrganizer/issues/25) | Implement Concurrent Processing with AsyncIO and Multiprocessing | Performance | High | Medium | Phase 3 | 🔲 |

## Tasks by Category

### Security (P1)
Critical security improvements that must be implemented before production use:

1. **[#10] Secure Access Token Storage**
   - Replace plaintext config with keyring/OAuth
   - Prevent token leakage through backups or accidental commits
   - Dependencies: `keyring>=24.0.0`

2. **[#11] OAuth 2.0 Authorization Flow**
   - Implement proper auth with refresh tokens
   - Eliminate manual token management
   - Use PKCE for enhanced security

### Reliability (P1-P2)

#### Critical (P1)
3. **[#12] State Persistence and Resume Capability**
   - SQLite-based checkpoint system
   - Resume interrupted runs without reprocessing
   - Essential for processing large photo libraries

#### High Priority (P2)
4. **[#20] API Rate Limiting and Backoff**
   - Handle Dropbox API limits gracefully
   - Exponential backoff on 429 responses
   - Configurable retry logic

5. **[#21] Configuration Validation (Pydantic)**
   - Schema validation for config files
   - Clear error messages on invalid config
   - Range validation for numeric values

### Testing & Infrastructure (P1)
6. **[#13] Comprehensive Test Suite**
   - Unit, integration, and accuracy tests
   - >80% code coverage target
   - Benchmark suite for face matching accuracy

7. **[#14] CI/CD Pipeline** ✅
   - GitHub Actions workflow
   - Automated testing on Python 3.10, 3.11, 3.12
   - Linting and code quality checks
   - Status: Completed on 2026-01-01 (see [CI.md](../CI.md))

### Documentation & Privacy (P1)
8. **[#15] Privacy and Data Handling Documentation**
   - GDPR/BIPA compliance considerations
   - Document where face encodings are stored
   - Data retention and deletion policies

### Face Recognition (P2)
9. **[#16] Two-Pass Face Recognition Strategy**
   - Larger thumbnails for initial detection
   - Full resolution for accurate matching
   - Improves accuracy vs bandwidth trade-off

10. **[#17] Multiple Reference Photo Handling**
    - Voting strategy across 5-10 reference photos
    - Better handling of different angles/lighting
    - Configurable matching threshold

### Safety & Data Protection (P2)
11. **[#19] Copy vs Move Strategy** ✅
    - Default to non-destructive operations
    - Operations audit log for undo capability
    - Prevent accidental data loss
    - Status: Completed in PR #27

12. **[#28] Race Condition in Audit Logging**
    - Handle concurrent writes to log file
    - Use file locking or logging module
    - Document limitations for multi-process scenarios
    - Follow-up to #19

13. **[#29] Log Injection Prevention**
    - Sanitize file paths before logging
    - Prevent control character injection
    - Defense-in-depth security for audit logs
    - Follow-up to #19

### Observability (P2)
14. **[#22] Structured Logging Infrastructure**
    - Comprehensive logging with rotation
    - Debug and verbose modes
    - Track all major operations

15. **[#23] Performance Benchmarks**
    - Establish baseline metrics
    - Photos per minute, API calls per photo
    - Memory usage monitoring

### Code Quality & CI Enforcement (P2)
16. **[#33] Enforce flake8 Checks**
    - Remove --exit-zero flag from CI pipeline
    - Fix all PEP 8 style violations
    - Enforce code complexity and line length standards
    - Follow-up to CI/CD pipeline implementation

17. **[#34] Enforce mypy Type Checking**
    - Remove || true bypass from CI pipeline
    - Fix all type errors in strict mode
    - Add type hints to public functions and classes
    - Improve code quality and IDE support

18. **[#35] Make Security Checks Blocking**
    - Remove || true from bandit and safety checks
    - Address all security warnings
    - Consider migration to pip-audit
    - Prevent introduction of new vulnerabilities

### Enhancements (P2-P3)
19. **[#18] HEIC Support**
    - Add proper HEIC support or document limitation
    - Dependencies: `pillow-heif>=0.10.0`
    - Important for iPhone photos

20. **[#24] Duplicate Detection**
    - Content hash-based deduplication
    - Skip previously processed files
    - Detect duplicates in current run

21. **[#25] Concurrent Processing** (P3)
    - Async I/O for downloads
    - Multiprocessing for face detection
    - 3-5x performance improvement target

## Recommended Implementation Order

### Immediate (Pre-Phase 2)
These foundational tasks should be completed before starting face recognition implementation:

1. [#12] State Persistence and Resume Capability
2. [#11] OAuth 2.0 Authorization Flow
3. [#10] Secure Access Token Storage
4. [#14] CI/CD Pipeline ✅ (Completed 2026-01-01)
5. [#15] Privacy Documentation

### Phase 2 Preparation
Implement these alongside face recognition development:

6. [#20] Rate Limiting and Backoff
7. [#21] Configuration Validation
8. [#22] Structured Logging
9. [#13] Comprehensive Test Suite (ongoing)
10. [#33] Enforce flake8 Checks (CI quality enforcement)
11. [#34] Enforce mypy Type Checking (CI quality enforcement)
12. [#35] Make Security Checks Blocking (CI security enforcement)

### Phase 2 Enhancements
After basic face recognition works:

13. [#16] Two-Pass Face Recognition
14. [#17] Multiple Reference Photo Handling
15. [#19] Copy vs Move Strategy ✅ (Completed in PR #27)
16. [#28] Race Condition in Audit Logging
17. [#29] Log Injection Prevention
18. [#18] HEIC Support
19. [#24] Duplicate Detection
20. [#23] Performance Benchmarks

### Phase 3 Optimization
Final polish for production readiness:

21. [#25] Concurrent Processing

## Progress Tracking

Track task completion status here:

- [ ] Phase 1 Complete (Dropbox API)
- [ ] P1 Security Tasks Complete (#10, #11)
- [ ] P1 Reliability Tasks Complete (#12)
- [x] P1 Infrastructure - CI/CD Complete (#14) - 2026-01-01
- [ ] P1 Infrastructure - Testing & Docs Complete (#13, #15)
- [ ] Phase 2 Core Complete (Face Recognition)
- [ ] P2 Enhancement Tasks Complete
- [ ] Phase 3 Complete (Automation & Polish)

## Notes

- All tasks include detailed acceptance criteria in their respective issues
- Code examples and configuration snippets are provided in each issue
- Dependencies are documented in individual issues
- Estimated effort levels: Low (1-2 days), Medium (3-5 days), High (1-2 weeks)

## References

- [Architecture Review Document](../ARCHITECTURE_ISSUES.md) - Full architecture review with detailed recommendations
- [CLAUDE.md](../../CLAUDE.md) - Development guidelines and project overview
- [README.md](../../README.md) - Project documentation and current status
