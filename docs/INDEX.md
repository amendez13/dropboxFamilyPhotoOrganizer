# Documentation Index

Welcome to the Dropbox Family Photo Organizer documentation. This index provides easy access to all documentation in this repository.

## Quick Links

**For Users:**
- [Getting Started](#getting-started) - Start here if you're new
- [Dropbox Setup](#setup-guides) - Configure your Dropbox API access

**For Developers:**
- [Architecture](#architecture) - Technical design and implementation details
- [Developer Guide](#developer-resources) - Contributing and development workflow

---

## Getting Started

**[README.md](../README.md)**
- Project overview and features
- Quick start guide
- Installation instructions
- Basic configuration
- Usage examples
- Troubleshooting common issues
- Development status and roadmap

---

## Setup Guides

**[DROPBOX_SETUP.md](DROPBOX_SETUP.md)**
- Step-by-step Dropbox API setup
- Creating a Dropbox app
- Configuring permissions and scopes
- Generating access tokens
- Security best practices
- Token management
- Troubleshooting permission issues

**[FACE_RECOGNITION_LOCAL_SETUP.md](FACE_RECOGNITION_LOCAL_SETUP.md)**
- Local face recognition provider setup
- System prerequisites and dependencies
- Installation guide for macOS, Linux, and Windows
- Configuration instructions
- First training run with reference photos
- Parameter tuning and troubleshooting

---

## Architecture

**[FACE_RECOGNITION_ARCHITECTURE.md](FACE_RECOGNITION_ARCHITECTURE.md)**
- Face recognition architecture and design
- Provider pattern implementation (Local, AWS, Azure)
- Design decisions and trade-offs
- Performance considerations
- Security and privacy implications
- Implementation guides for adding new providers
- TODO and future enhancements

---

## Developer Resources

**[CLAUDE.md](../CLAUDE.md)**
- Project overview for AI assistants
- Technology stack details
- Core workflow and key components
- Development commands and setup
- Common development tasks

**[CI.md](CI.md)**
- Continuous Integration (CI) pipeline documentation
- GitHub Actions workflow details
- Code quality and testing automation
- Local development workflow
- Running CI checks locally
- Troubleshooting CI failures
- Best practices for development

---

## Project Status

**Current Phase:** Dropbox API integration
- Dropbox authentication
- Folder listing and file traversal
- File download and thumbnail retrieval
- File moving capabilities

**Next Phase:** Face recognition integration
- Load reference photos
- Process images with face detection
- Match faces against reference encodings

**Future:** Automation and polish
- Command-line interface
- Progress tracking and logging
- Resume capability
- Statistics and reporting

---

## Quick Reference

| Document | Purpose | Audience |
|----------|---------|----------|
| [README.md](../README.md) | Getting started, installation, usage | All users |
| [DROPBOX_SETUP.md](DROPBOX_SETUP.md) | Dropbox API configuration | All users |
| [FACE_RECOGNITION_LOCAL_SETUP.md](FACE_RECOGNITION_LOCAL_SETUP.md) | Local face recognition setup | All users |
| [FACE_RECOGNITION_ARCHITECTURE.md](FACE_RECOGNITION_ARCHITECTURE.md) | Technical architecture and design | Developers |
| [CI.md](CI.md) | CI/CD pipeline and development workflow | Developers |
| [CLAUDE.md](../CLAUDE.md) | AI assistant guidance | Claude Code |

---

## Additional Resources

- [Dropbox API Documentation](https://www.dropbox.com/developers/documentation)
- [Python SDK Reference](https://dropbox-sdk-python.readthedocs.io/)
- [face_recognition Library](https://github.com/ageitgey/face_recognition)
- [AWS Rekognition](https://docs.aws.amazon.com/rekognition/)
- [Azure Face API](https://docs.microsoft.com/en-us/azure/cognitive-services/face/)
