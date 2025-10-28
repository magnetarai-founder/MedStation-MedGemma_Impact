# ElohimOS

**Offline-first, encrypted field operations platform for secure data collection and AI-powered workflows.**

ElohimOS is a self-hosted, local-first application designed for field workers, researchers, and healthcare professionals who need secure, reliable data collection tools that work without internet connectivity.

---

## 🔐 Security & Encryption

ElohimOS implements **military-grade encryption** to protect sensitive data:

### Encryption Technologies

- **AES-256-GCM** encryption for data at rest
- **TLS 1.3** for data in transit
- **PyNaCl (libsodium)** for end-to-end encrypted P2P communications
- **PBKDF2** key derivation with 600,000 iterations
- **X25519** elliptic curve cryptography (256-bit)
- **SHA-256** cryptographic hashing

### 🚨 Export Control Notice

**IMPORTANT**: ElohimOS uses strong cryptographic algorithms that may be subject to export control regulations in some countries.

**Key Lengths:**
- AES-256 (256-bit symmetric encryption)
- X25519 (256-bit elliptic curve)
- SHA-256 (256-bit hashing)

**Compliance Responsibility:**

Users are responsible for ensuring compliance with:
- U.S. Export Administration Regulations (EAR)
- Wassenaar Arrangement on Export Controls
- Local import/export regulations in their jurisdiction

Before exporting, importing, or distributing ElohimOS, verify whether export licenses or authorizations are required in your country.

For more information about U.S. export controls, visit: https://www.bis.doc.gov/

---

## ✨ Features

### 🔒 Security Foundation
- ✅ **End-to-End Encryption** - PyNaCl sealed boxes with perfect forward secrecy
- ✅ **Database Encryption** - AES-256-GCM encryption for all databases
- ✅ **Secure Enclave** - Protected key storage using system keychain
- ✅ **Role-Based Access Control** - 4-tier permission system (Super Admin, Admin, Member, Viewer)
- ✅ **Automatic Backups** - Encrypted daily backups with 7-day retention
- ✅ **Audit Logging** - Comprehensive logging of all data access

### 🏥 Healthcare & Compliance
- ✅ **PHI Detection** - Automatic detection of Protected Health Information in forms
- ✅ **HIPAA Support** - Technical safeguards for HIPAA compliance
- ✅ **Medical Disclaimers** - Built-in medical advice disclaimers
- ⚠️ **Not a Medical Device** - See disclaimers below

### 📱 Core Functionality
- **Offline-First** - Works without internet connectivity
- **P2P Chat** - End-to-end encrypted peer-to-peer messaging
- **Workflow Builder** - Create custom data collection forms
- **Secure Vault** - Password-protected secrets manager
- **Dataset Management** - Import, analyze, and export datasets
- **AI Integration** - Local LLM support for offline AI assistance

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+** with pip
- **Node.js 18+** with npm
- **macOS, Linux, or Windows** (macOS recommended for Secure Enclave)

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/ElohimOS.git
cd ElohimOS

# Set up Python backend
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Set up frontend
cd apps/frontend
npm install
npm run build

# Start the backend
cd ../backend/api
python3 main.py

# Access the application
# Open http://localhost:8000 in your browser
```

### First-Time Setup

1. **Create your passphrase** - You'll be prompted to create a master passphrase on first launch
2. **Save backup codes** - Write down the 10 backup codes displayed (you'll need these if you forget your passphrase)
3. **Create your user profile** - First user is automatically assigned Super Admin role

---

## ⚕️ Medical Disclaimer

**NOT MEDICAL ADVICE**

ElohimOS and its AI features are **not medical devices** and do not provide medical advice, diagnosis, or treatment. Information provided is for informational purposes only.

**Always consult with a qualified healthcare professional for medical decisions.**

By using ElohimOS in medical contexts, you acknowledge that:
- AI responses are not a substitute for professional medical judgment
- You are responsible for verifying all medical information
- ElohimOS is not liable for medical decisions made using this software
- The software is not FDA-approved for clinical use

**In case of emergency**: Call emergency services (911 in the US) immediately. Do not rely on ElohimOS for emergency medical assistance.

See [DISCLAIMERS.md](docs/DISCLAIMERS.md) for complete legal notices.

---

## 🔐 Security Features

### Encryption at Rest
- All sensitive databases (vault, app data) are encrypted with AES-256-GCM
- Encryption keys derived using PBKDF2 with 600,000 iterations
- Keys stored securely in system keychain (Secure Enclave on macOS)

### End-to-End Encryption
- P2P chat messages encrypted with PyNaCl sealed boxes
- Perfect forward secrecy for all communications
- Fingerprint verification with safety numbers
- Device linking via QR codes

### Access Control
- **Super Admin** - Full system control, can create Admins
- **Admin** - Manage users, workflows, settings (cannot create other Admins)
- **Member** - Default role, create/edit own workflows, access vault
- **Viewer** - Read-only access

### Audit Logging
- All data access logged with timestamp, user, action, IP
- 90-day retention with automatic cleanup
- Admin-only access to logs
- CSV export for compliance reviews

### Automatic Backups
- Encrypted daily backups at 2am (when idle)
- 7-day retention (automatic cleanup of old backups)
- Stored in `~/.elohimos_backups/`
- One-click restore with integrity verification

---

## 🏥 HIPAA Compliance

ElohimOS provides **technical safeguards** that support HIPAA compliance, but **technical features alone do not ensure HIPAA compliance**.

### Technical Safeguards Provided
✅ Encryption at rest (AES-256-GCM)
✅ Encryption in transit (TLS 1.3)
✅ End-to-end encryption for communications
✅ Audit logging of data access
✅ Role-based access controls
✅ Automatic backup and recovery
✅ Secure key management

### Additional Requirements
Organizations handling PHI must also implement:
- Physical safeguards (facility access controls)
- Administrative safeguards (security management process)
- Business Associate Agreements (BAAs)
- Workforce security and training
- Breach notification procedures
- Regular security assessments

**ElohimOS is self-hosted software that you control.** The authors do not have access to your data and are not business associates under HIPAA.

See [HIPAA_COMPLIANCE.md](docs/HIPAA_COMPLIANCE.md) for detailed guidance.

---

## 📊 Data Privacy

### Local-First Architecture
- All data stored locally on your device by default
- No data sent to external servers without explicit user action
- P2P communications are end-to-end encrypted
- You maintain full control of your data

### No Telemetry
ElohimOS does **not** collect or transmit:
- Personal information to third parties
- Usage analytics or telemetry
- Crash reports or diagnostics
- Any data to the software authors

### User Responsibility
Users are responsible for:
- Protecting their device and encryption passphrase
- Implementing appropriate access controls
- Complying with privacy laws (GDPR, CCPA, etc.)
- Obtaining necessary consents
- Handling data subject rights requests

---

## 🛠️ Architecture

### Backend (Python/FastAPI)
- **FastAPI** - Modern async web framework
- **SQLite** - Embedded database with encryption
- **PyNaCl** - Cryptography library (libsodium)
- **Cryptography** - Additional crypto primitives

### Frontend (React/TypeScript)
- **React 18** - UI framework
- **TypeScript** - Type-safe JavaScript
- **Vite** - Build tool and dev server
- **TanStack Query** - Data fetching and caching

### Database Structure
- `elohimos_app.db` - Main application data (encrypted)
- `vault.db` - Password vault (encrypted)
- `datasets.db` - Dataset metadata (unencrypted)
- `audit.db` - Audit logs (encrypted)

---

## 📝 License

[Add your license here - MIT, Apache 2.0, etc.]

---

## 🤝 Contributing

[Add contribution guidelines]

---

## 📧 Support

For issues and questions:
- GitHub Issues: [yourusername/ElohimOS/issues]
- Documentation: [docs/](docs/)

---

## ⚖️ Legal Notices

### Liability Disclaimer

ElohimOS is provided "AS IS" without warranties of any kind. See [DISCLAIMERS.md](docs/DISCLAIMERS.md) for complete legal notices.

### Export Control

This software uses encryption technology subject to export controls. Users are responsible for compliance with export regulations. See "Export Control Notice" section above.

### Not Medical Advice

ElohimOS is not a medical device and does not provide medical advice. See "Medical Disclaimer" section above.

---

## 🏗️ Project Status

**Current Version**: v1.0.0-alpha
**Status**: Active Development

### Completed Features (Phase 1-3)
✅ End-to-end encryption (Phase 1.1)
✅ Database encryption (Phase 1.2)
✅ Role-based access control (Phase 1.3)
✅ Automatic backups (Phase 2.1)
✅ Audit logging (Phase 2.2)
✅ PHI detection (Phase 3.1)
✅ Medical disclaimers (Phase 3.2)
✅ Export controls documentation (Phase 3.3)

### In Development
- Focus mode selector (Quiet/Field/Emergency)
- Enhanced UI/UX features
- Additional compliance features

See [ROADMAP.md](docs/ROADMAP.md) for detailed development plans.

---

**Built with ❤️ for field workers, researchers, and healthcare professionals who need secure, reliable tools that work anywhere.**
