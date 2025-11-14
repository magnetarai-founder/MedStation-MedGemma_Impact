# Changelog

All notable changes to ElohimOS will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

Sections are auto-generated from git commit history using conventional commit format:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `perf:` - Performance improvements
- `refactor:` - Code refactoring
- `test:` - Test additions/changes
- `ci:` - CI/CD changes
- `chore:` - Maintenance tasks

---

## v1.0.0-rc1 — 2025-11-14

### Features

- **vault**: Harden share link security with IP throttles, one-time links, and TTL defaults (Batch B) (`947b5489`)
- **tests**: Add comprehensive API test coverage (Batch A) (`7f368454`)
- **terminal**: Add socket/start endpoint for external terminal capture (`f0ce43ed`)
- **vault**: Add rate limiting and audit logging to vault endpoints (`5d6f4a7d`)
- **vault**: Add pagination with Load More UI to vault endpoints (`045ee694`)
- **frontend**: Complete Vault modals batch 3/3 - Analytics, Preview, Advanced Search (`da0cee34`)
- **frontend**: Implement Vault modals batch 2/3 - Comments, Pinned, Audit, Export (`f09c2bc2`)
- **auth**: Complete forced password change flow with PBKDF2 consistency (`a312d1ac`)
- **backend**: Implement Founder Admin password reset with forced password change flow (`e8749af8`)
- **backend**: Implement Phase 1.6 - Per-user model preloader replacing JSON (`013d1a00`)
- **frontend**: Implement 4 vault modals with real API integration (Batch 2) (`c2d2f645`)
- **frontend**: Wire BackupsTab to real backup API endpoints (`dfe9c480`)

### Fixes

- **backend**: Resolve critical startup errors in Code Editor, Terminal, Vault, and model services (`481d4867`)

### Documentation

- **api**: Add comprehensive API reference documentation (Batch C) (`29c99f1a`)

### Chore

- **release**: Prepare v1.0.0-rc1 release (`528386bc`)
- **backend**: Complete R8 backend route modularization and verification (`c9ba529f`)

### CI/CD

- **backend**: Add GitHub Actions workflow for pytest with caching and summaries (Batch D) (`82b90598`)

### API Additions

- Table of Contents
- Authentication
- Forced Password Change Flow
- Vault API
- File Operations
- Comments
- Versions
- Trash
- Search
- Sharing
- Analytics
- Pagination Contract
- Rate Limiting
- Vault Rate Limits
- Share Link IP Throttles
- Error Codes
- Authentication Errors
- Share Link Errors
- Vault Errors
- Model Preloader
- Behavior
- Support

---
