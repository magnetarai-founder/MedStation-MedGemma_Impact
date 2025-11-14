# ElohimOS Documentation

**"My God is my rock, in whom I take refuge"** - 2 Samuel 22:3

Welcome to the ElohimOS documentation. This guide will help you navigate the codebase, understand the architecture, and contribute to the project.

---

## 📚 Documentation Structure

### 🏗️ Architecture
System design, philosophy, and technical decisions.

- **[SYSTEM_ARCHITECTURE.md](architecture/SYSTEM_ARCHITECTURE.md)** - Complete system architecture (875 lines)
- **[ARCHITECTURE_PHILOSOPHY.md](architecture/ARCHITECTURE_PHILOSOPHY.md)** - Design principles and philosophy

### 💾 Database
Schema documentation and database design.

- **[SCHEMA.md](database/SCHEMA.md)** - Database schema (8 SQLite databases)

### 👨‍💻 Development
Getting started, development workflow, and tools.

- **[README.md](development/README.md)** - Getting started guide
- **[ONBOARDING.md](development/ONBOARDING.md)** - New developer onboarding
- **[API_REFERENCE.md](development/API_REFERENCE.md)** - Complete REST API documentation ⭐
- **[PRE_COMMIT_SETUP.md](development/PRE_COMMIT_SETUP.md)** - Pre-commit hooks setup
- **[FOUNDER_RIGHTS_LOGIN.md](development/FOUNDER_RIGHTS_LOGIN.md)** - Founder rights authentication
- **[DEVELOPMENT_NOTES.md](development/DEVELOPMENT_NOTES.md)** - Development tips and notes
- **[CODE_TAB.md](development/CODE_TAB.md)** - Code Tab feature guide (Monaco editor + terminal)

### 🚀 Deployment
Production deployment guides and checklists.

- **[DEPLOYMENT_CHECKLIST.md](deployment/DEPLOYMENT_CHECKLIST.md)** - Pre-deployment checklist
- **[DISCLAIMERS.md](deployment/DISCLAIMERS.md)** - Legal disclaimers and notices

### 🗺️ Roadmap
Future plans, features, and optimization strategies.

- **[ELOHIMOS_FOUNDATION_ROADMAP.md](roadmap/ELOHIMOS_FOUNDATION_ROADMAP.md)** - Platform-wide development roadmap
- **[CODE_TAB_ROADMAP.md](roadmap/CODE_TAB_ROADMAP.md)** - Code Tab phases 1-10 implementation plan
- **[REFACTORING_ROADMAP.md](roadmap/REFACTORING_ROADMAP.md)** - Vault/Team service refactoring (R1-R11)
- **[METAL4_OPTIMIZATION.md](roadmap/METAL4_OPTIMIZATION.md)** - Apple Silicon GPU optimization
- **[P2P_MESH.md](roadmap/P2P_MESH.md)** - P2P mesh networking implementation
- **[PERFORMANCE.md](roadmap/PERFORMANCE.md)** - Performance optimization strategies
- **[ENHANCEMENT_PLAN.md](roadmap/ENHANCEMENT_PLAN.md)** - Future enhancements

### 🔄 Migrations
Completed and active migration projects.

#### Completed
- **[ROUTER_MIGRATION_STATUS.md](migrations/completed/ROUTER_MIGRATION_STATUS.md)** - Service layer pattern migration (5/5 routers)
- **[PHASE_1_E2E_VALIDATION.md](migrations/completed/PHASE_1_E2E_VALIDATION.md)** - Phase 1 E2E validation
- **[ElohimOS_Refactor_Progress.md](migrations/completed/ElohimOS_Refactor_Progress.md)** - SQL/JSON endpoint refactor (Phases 1-3)
- **[ElohimOS_Refactor_Implementation_Plan_v2.md](migrations/completed/ElohimOS_Refactor_Implementation_Plan_v2.md)** - Refactor implementation plan
- **[ElohimOS_Phase4_SQL_JSON_Migration_Spec.md](migrations/completed/ElohimOS_Phase4_SQL_JSON_Migration_Spec.md)** - SQL/JSON migration spec

### 📝 Changelog
Version history and release notes.

- **[CHANGELOG.md](changelog/CHANGELOG.md)** - Version history and changes

### 📦 Archive
Old/duplicate documentation kept for reference.

- **[archive/](archive/)** - Historical documents

---

## 🚀 Quick Start

### For New Developers
1. Read **[ONBOARDING.md](development/ONBOARDING.md)**
2. Review **[SYSTEM_ARCHITECTURE.md](architecture/SYSTEM_ARCHITECTURE.md)**
3. Set up **[PRE_COMMIT_SETUP.md](development/PRE_COMMIT_SETUP.md)**

### For Contributors
1. Check **[ELOHIMOS_FOUNDATION_ROADMAP.md](roadmap/ELOHIMOS_FOUNDATION_ROADMAP.md)** for platform roadmap
2. Review **[ARCHITECTURE_PHILOSOPHY.md](architecture/ARCHITECTURE_PHILOSOPHY.md)** for design principles
3. See **[DEVELOPMENT_NOTES.md](development/DEVELOPMENT_NOTES.md)** for tips
4. Check **[CODE_TAB_ROADMAP.md](roadmap/CODE_TAB_ROADMAP.md)** or **[REFACTORING_ROADMAP.md](roadmap/REFACTORING_ROADMAP.md)** for specific workstreams

### For Deployers
1. Follow **[DEPLOYMENT_CHECKLIST.md](deployment/DEPLOYMENT_CHECKLIST.md)**
2. Review **[DISCLAIMERS.md](deployment/DISCLAIMERS.md)**

---

## 📊 Project Status

### Recent Achievements
- ✅ **Frontend Large-File Refactor Complete** (R5-R7: 3 components, 55 modular files)
  - VaultWorkspace: 4,119 → 30 files
  - ProfileSettings: 982 → 13 files
  - AutomationTab: 902 → 12 files (+ template consolidation)
- ✅ **Code Tab Complete** (Monaco editor + terminal, production ready)
- ✅ **Router Migration Complete** (5/5 routers to service layer pattern)
- ✅ **SQL/JSON Endpoints Refactored** (Phases 1-3 complete)
- ✅ **Metal 4 GPU Acceleration** (10x faster embeddings)
- ✅ **P2P Mesh Networking** (Offline-first collaboration)

### Active Development
- 🚧 **Backend Route Modularization** (R8: Vault/Chat/Team routes)
- 🚧 **Vault/Team Service Refactoring** (R1-R11, see REFACTORING_ROADMAP.md)
- 🚧 **Metal 4 Optimization** (Phase 4.1-4.2)
- 🚧 **Database Tab AI Query Builder** (256 SQL templates)

---

## 🎯 Key Features

- **Offline-First AI** - Works without internet, all AI local (Ollama)
- **Zero-Knowledge Vault** - Server cannot decrypt user data
- **P2P Mesh** - Device-to-device sync without server
- **Metal 4 GPU** - Apple Silicon GPU acceleration
- **RBAC Hierarchy** - Salesforce-style permissions with Founder Rights
- **Adaptive Learning** - System learns optimal model selection

---

## 📖 Key Documents by Topic

### Architecture & Design
- [System Architecture](architecture/SYSTEM_ARCHITECTURE.md)
- [Architecture Philosophy](architecture/ARCHITECTURE_PHILOSOPHY.md)
- [Database Schema](database/SCHEMA.md)

### Development
- [Getting Started](development/README.md)
- [Onboarding Guide](development/ONBOARDING.md)
- [API Reference](development/API_REFERENCE.md) ⭐
- [Development Notes](development/DEVELOPMENT_NOTES.md)

### Roadmap
- [Platform Roadmap](roadmap/ELOHIMOS_FOUNDATION_ROADMAP.md)
- [Code Tab Roadmap](roadmap/CODE_TAB_ROADMAP.md)
- [Refactoring Roadmap](roadmap/REFACTORING_ROADMAP.md)
- [Metal4 Optimization](roadmap/METAL4_OPTIMIZATION.md)
- [Performance Optimization](roadmap/PERFORMANCE.md)

---

## 🔗 External Resources

- **GitHub:** https://github.com/indiedevhipps/ElohimOS
- **Documentation Site:** /docs
- **Community:** Contact founder for access

---

## 📄 License

[Your License Here]

---

**Last Updated:** 2025-11-14
**Documentation Version:** 2.2 (v1.0.0-rc1 release, API reference added)
