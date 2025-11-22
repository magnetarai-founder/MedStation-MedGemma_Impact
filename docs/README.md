# MagnetarStudio Documentation

**"My God is my rock, in whom I take refuge"** - 2 Samuel 22:3

Welcome to the MagnetarStudio documentation. This streamlined guide provides everything you need to understand the architecture and contribute to the project.

---

## 📚 Documentation Structure

**Current Status**: Consolidated to 6 core documents (as of 2025-11-17)

### 🏗️ Architecture
System design, philosophy, technical decisions, and constraints.

- **[SYSTEM_ARCHITECTURE.md](architecture/SYSTEM_ARCHITECTURE.md)** - Complete system architecture
  - Technology stack (FastAPI, SQLite, DuckDB, Ollama, React, Zustand)
  - Component architecture (Neutron/Pulsar engines, services, routes)
  - High-level data flow
  - **Read this first for technical overview**

- **[PERMISSION_MODEL.md](architecture/PERMISSION_MODEL.md)** - RBAC permission system
  - Salesforce-style role-based access control
  - Founder rights, permission profiles, permission sets
  - Permission keys and resolution order
  - **Critical for understanding auth/security constraints**

- **[ARCHITECTURE_PHILOSOPHY.md](architecture/ARCHITECTURE_PHILOSOPHY.md)** - Design principles
  - "Dumb core that always works" philosophy
  - Offline-first design patterns
  - Battery efficiency (ANE routing)
  - Field-ready constraints

- **[refactoring-guide.md](architecture/refactoring-guide.md)** - Code quality guidelines
  - Refactoring best practices
  - Testing strategies
  - Module splitting patterns

### 🗺️ Roadmap
**Single source of truth for all refactoring and feature work.**

- **[MODULAR_REFACTORING_PLAN.md](roadmap/MODULAR_REFACTORING_PLAN.md)** ⭐ **PRIMARY ROADMAP**
  - **THIS IS THE MASTER PLAN** for all refactoring work (Phases 0-9)
  - 3-week execution plan with day-by-day tasks
  - Backend service splits (Team, Vault, Chat)
  - Frontend component modularization
  - Deferred features (Stealth Labels, Admin RBAC)
  - **All contributors should consult this document**

---

## 🚀 Quick Start

### For New Developers
1. **Start here**: Read [SYSTEM_ARCHITECTURE.md](architecture/SYSTEM_ARCHITECTURE.md) - understand the tech stack and component architecture
2. **Understand security**: Read [PERMISSION_MODEL.md](architecture/PERMISSION_MODEL.md) - learn RBAC constraints (critical!)
3. **Learn philosophy**: Read [ARCHITECTURE_PHILOSOPHY.md](architecture/ARCHITECTURE_PHILOSOPHY.md) - understand design principles
4. **Check roadmap**: Read [MODULAR_REFACTORING_PLAN.md](roadmap/MODULAR_REFACTORING_PLAN.md) - see what's being worked on

### For Contributors
1. **Review roadmap**: Check [MODULAR_REFACTORING_PLAN.md](roadmap/MODULAR_REFACTORING_PLAN.md) for current priorities (Phases 0-7)
2. **Understand constraints**: All refactoring must respect:
   - ✅ No breaking API changes
   - ✅ No RBAC regressions (see PERMISSION_MODEL.md)
   - ✅ No vault data corruption (encryption logic stays unchanged)
   - ✅ All tests must pass
3. **Follow patterns**: See [refactoring-guide.md](architecture/refactoring-guide.md) for best practices
4. **Start with Phase 0-1**: Low-risk template file splits (see roadmap Week 1 plan)

### For Architecture Decisions
- **Consult**: [SYSTEM_ARCHITECTURE.md](architecture/SYSTEM_ARCHITECTURE.md) for invariants
- **Consult**: [PERMISSION_MODEL.md](architecture/PERMISSION_MODEL.md) for RBAC rules
- **Consult**: [ARCHITECTURE_PHILOSOPHY.md](architecture/ARCHITECTURE_PHILOSOPHY.md) for design principles

---

## 🎯 Key Features

- **Offline-First AI** - Works without internet, all AI local (Ollama)
- **Zero-Knowledge Vault** - Server cannot decrypt user data (AES-256-GCM)
- **P2P Mesh** - Device-to-device sync without server (libp2p)
- **Metal 4 GPU** - Apple Silicon GPU acceleration (MPS)
- **RBAC Hierarchy** - Salesforce-style permissions with Founder Rights
- **Adaptive Learning** - System learns optimal model selection

**Current Version**: v1.0.0-rc1 (Release Candidate)

---

## 📊 Project Status (as of 2025-11-17)

### Recent Achievements
- ✅ **Documentation Consolidated** - 6 core docs (from 39+ files)
- ✅ **Frontend Large-File Refactor** (R5-R7: VaultWorkspace, ProfileSettings, AutomationTab)
- ✅ **Code Tab Complete** (Monaco editor + terminal, production ready)
- ✅ **Router Migration Complete** (5/5 routers to service layer pattern)
- ✅ **Metal 4 GPU Acceleration** (10x faster embeddings)
- ✅ **P2P Mesh Networking** (Offline-first collaboration)

### Active Work (Phase 0-2)
- 🚧 **Phase 0**: Docs alignment (you are here!)
- 🚧 **Phase 1**: Template file splits (2-3 days)
- 🚧 **Phase 2**: Backend service refactoring (Team: 2,872 lines → 9 files, Vault: 2,780 lines → 11 files)

### Critical Files Requiring Refactoring
- `apps/backend/api/services/team/core.py` - **2,872 lines** (Phase 2.1)
- `apps/backend/api/services/vault/core.py` - **2,780 lines** (Phase 2.2)
- `apps/backend/api/services/chat/core.py` - **1,751 lines** (Phase 2.3)
- `apps/backend/api/main.py` - **1,920 lines** (Phase 3.1)
- `apps/frontend/src/components/VaultWorkspace.tsx` - **4,119 lines** (Phase 4.1)

See [MODULAR_REFACTORING_PLAN.md](roadmap/MODULAR_REFACTORING_PLAN.md) for full breakdown.

---

## 📖 Documentation by Use Case

### I want to understand the codebase
1. [SYSTEM_ARCHITECTURE.md](architecture/SYSTEM_ARCHITECTURE.md) - Tech stack, components, data flow
2. [ARCHITECTURE_PHILOSOPHY.md](architecture/ARCHITECTURE_PHILOSOPHY.md) - Design principles

### I want to contribute code
1. [MODULAR_REFACTORING_PLAN.md](roadmap/MODULAR_REFACTORING_PLAN.md) - Current priorities
2. [refactoring-guide.md](architecture/refactoring-guide.md) - Best practices
3. [PERMISSION_MODEL.md](architecture/PERMISSION_MODEL.md) - RBAC constraints

### I want to understand security/permissions
1. [PERMISSION_MODEL.md](architecture/PERMISSION_MODEL.md) - Complete RBAC model
2. [SYSTEM_ARCHITECTURE.md](architecture/SYSTEM_ARCHITECTURE.md) - Encryption, auth flow

### I want to see the roadmap
1. [MODULAR_REFACTORING_PLAN.md](roadmap/MODULAR_REFACTORING_PLAN.md) - **SINGLE SOURCE OF TRUTH**
   - Phases 0-9 (refactoring + deferred features)
   - 3-week execution plan
   - Task breakdowns with acceptance criteria

---

## 🔗 External Resources

- **GitHub:** https://github.com/indiedevhipps/MagnetarStudio
- **Codebase**: `/Users/indiedevhipps/Documents/MagnetarStudio`
- **Community:** Contact founder for access

---

## 📝 Changelog Location

Version history is tracked in git commit messages using conventional commits:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `refactor:` - Code refactoring
- `test:` - Test changes

Run `git log --oneline --graph` to see recent changes.

---

## ⚠️ Important Notes

### Documentation Philosophy
- **Minimal & Focused**: Only 6 core docs to reduce duplication and maintenance burden
- **Single Source of Truth**: MODULAR_REFACTORING_PLAN.md is the master roadmap
- **Architecture First**: SYSTEM_ARCHITECTURE.md and PERMISSION_MODEL.md define invariants
- **No Stale Docs**: Old/duplicate docs have been removed (as of 2025-11-17)

### What Happened to Other Docs?
Previously, MagnetarStudio had 39+ documentation files including:
- `database/`, `development/`, `deployment/`, `monitoring/` directories
- Multiple roadmap files (ELOHIMOS_FOUNDATION_ROADMAP.md, CODE_TAB_ROADMAP.md, etc.)
- Duplicate/outdated migration docs

**These have been consolidated or removed** (2025-11-17) to maintain a lean, up-to-date documentation set. If you need historical context, check git history: `git log --all --full-history -- docs/`

### How to Contribute to Docs
1. **Update existing docs** in place (no new files unless critical)
2. **Update roadmap** via [MODULAR_REFACTORING_PLAN.md](roadmap/MODULAR_REFACTORING_PLAN.md)
3. **Update architecture docs** if system invariants change
4. **Keep docs DRY** - one source of truth per topic

---

**Last Updated:** 2025-11-17
**Documentation Version:** 3.0 (Consolidated to 6 core docs)
**Roadmap Version:** 2.0 (Execution Ready - see MODULAR_REFACTORING_PLAN.md)
