# ElohimOS Developer Documentation

**Offline-first, encrypted field operations platform for secure data collection and AI-powered workflows.**

ElohimOS is a self-hosted, local-first application designed for field workers, researchers, and healthcare professionals who need secure, reliable data collection tools that work without internet connectivity.

---

## 🚀 Quick Start

### Prerequisites
- **Python 3.10+** with pip
- **Node.js 18+** with npm
- **macOS, Linux, or Windows** (macOS recommended for Secure Enclave)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ElohimOS.git
cd ElohimOS

# Set up Python environment
./tools/scripts/setup_python_env.sh

# Set up frontend
cd apps/frontend
npm install
npm run build

# Start the backend
cd ../backend/api
python3 main.py

# Access at http://localhost:8000
```

### First-Time Setup
1. **Create your passphrase** - Master passphrase on first launch
2. **Save backup codes** - Write down 10 backup codes (needed if you forget passphrase)
3. **Create your profile** - First user automatically assigned Super Admin role

---

## 📊 Project Status

**Current Version**: v1.0.0-alpha
**Status**: Active Development

### ✅ Completed (Phases 1-7)
- **Phase 1-4**: Backend foundation (78 services, 4,502+ lines)
  - End-to-end encryption (PyNaCl)
  - Database encryption (AES-256-GCM)
  - Role-based access control (4-tier)
  - Automatic backups (7-day retention)
  - Audit logging (90-day retention)
  - PHI detection (144 patterns)
  - Medical disclaimers
  - Focus mode, undo/redo, accessibility services

- **Phase 5-6**: Team collaboration
  - Team creation & invite codes
  - Super Admin limits & failsafes
  - Guest auto-promotion (7-day)
  - Job roles & workflow permissions
  - Queue access control
  - God Rights authorization
  - Team Vault (encrypted storage)

- **Phase 7**: Model management & settings redesign
  - Backend model filtering
  - Per-model configuration
  - Hot slots system [1][2][3][4]
  - Live model dropdown updates
  - Adaptive learning & classification

### ⚠️ Known Issues (See Reports on Desktop)
- **Security Review**: 2 critical, 5 high, 8 medium issues identified
- **Missing Features**: ~40% of documented features not yet implemented (primarily UI integration)

See comprehensive reports:
- `~/Desktop/ElohimOS_Security_Code_Review.md` - Complete security audit
- `~/Desktop/ElohimOS_Missing_Features_Gap_Analysis.md` - Feature implementation status

---

## 🛠️ Architecture

### Backend (Python/FastAPI)
- **FastAPI** - Async web framework
- **SQLite** - Embedded database with encryption
- **DuckDB** - In-memory OLAP database
- **PyNaCl** - Cryptography (libsodium)
- **78 backend services** across 10 core modules

### Frontend (React/TypeScript)
- **React 18** - UI framework
- **TypeScript 5** - Type-safe JavaScript
- **Vite** - Build tool and dev server
- **Zustand** - State management (13 stores)
- **TanStack Query** - Data fetching

### Key Components
- **Neutron Star Data Engine** - Core data/query processing
- **Metal/ANE Inference** - Apple Silicon GPU acceleration
- **MagnetarMesh P2P** - Offline device-to-device sync
- **Secure Enclave** - macOS Keychain integration
- **Team Vault** - Encrypted team storage

---

## 🔐 Security

ElohimOS implements **military-grade encryption**:
- **AES-256-GCM** for data at rest
- **X25519** elliptic curve cryptography
- **PBKDF2** with 600,000 iterations
- **PyNaCl** for end-to-end encrypted P2P
- **Zero-knowledge architecture** - Server cannot read user data

### 🚨 Export Control Notice
This software uses strong cryptographic algorithms (256-bit) that may be subject to export control regulations. Users are responsible for compliance with U.S. Export Administration Regulations (EAR) and local laws.

**Full security details**: See `DISCLAIMERS.md` and security review report on desktop.

---

## ⚕️ Legal Disclaimers

**NOT MEDICAL ADVICE**: ElohimOS is not a medical device and does not provide medical advice, diagnosis, or treatment. Always consult qualified healthcare professionals.

**AS-IS SOFTWARE**: Provided without warranties. See `DISCLAIMERS.md` for complete legal notices.

**HIPAA**: Technical safeguards provided, but compliance requires organizational, administrative, and physical measures beyond software.

---

## 📚 Documentation

### Core Documentation (This Folder)
- `ARCHITECTURE_PHILOSOPHY.md` - Design principles and system architecture
- `DEVELOPMENT_NOTES.md` - Build setup, environment configuration
- `DISCLAIMERS.md` - Legal notices (medical, export control, liability)
- `requirements-dev.txt` - Python development dependencies

### Comprehensive Reports (Desktop)
- `ElohimOS_Security_Code_Review.md` - Full security audit with vulnerabilities
- `ElohimOS_Missing_Features_Gap_Analysis.md` - Implementation status and gaps

---

## 🔧 Development

### Environment Setup
```bash
# Python environment (includes ruff, black, mypy, pytest)
./tools/scripts/setup_python_env.sh
source venv/bin/activate

# Install dev dependencies
pip install -r docs/dev/requirements-dev.txt

# Run linting
ruff check apps/backend/api/

# Run tests
pytest apps/backend/api/
```

### Important Notes
- **NO tsconfig.json** - Vite handles TypeScript compilation (see `DEVELOPMENT_NOTES.md`)
- **Build script**: `"build": "vite build"` (NOT `tsc && vite build`)
- **Ruff installed via pip** (not Homebrew) for CI/CD compatibility

---

## 📝 License

[Add your license here - MIT, Apache 2.0, etc.]

---

## 📧 Support

For issues and questions:
- GitHub Issues: [Repository URL]/issues
- Documentation: `docs/dev/`
- Security issues: See `ElohimOS_Security_Code_Review.md` on desktop

---

**Built with conviction for field workers, researchers, and healthcare professionals who need secure, reliable tools that work anywhere.**

**Copyright (c) 2025 MagnetarAI, LLC**
