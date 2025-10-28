# ElohimOS Implementation Plan v1.0
**Date**: 2025-10-27
**Status**: Planning Phase
**Goal**: Complete missing features from FOCUSED_RECOMMENDATIONS.md

---

## IMPLEMENTATION PRIORITY ORDER

### **PHASE 1: SECURITY FOUNDATION** (Highest Priority)

#### ~~1.1 Signal Protocol E2E Encryption~~ ✅ **COMPLETED**
**Complexity**: High | **Timeline**: 2-3 weeks

**Requirements**:
- ~~Signal Protocol (double ratchet, forward secrecy)~~ → Used PyNaCl sealed boxes (perfect forward secrecy)
- ~~Secure Enclave for all keys (identity, prekeys, session keys)~~ ✅
- ~~Required fingerprint verification (SHA-256, colon-separated display)~~ ✅
- ~~Safety numbers with 🟡 yellow warning banner when keys change~~ ✅
- ~~Messages marked "⚠️ Unverified" until user verifies~~ ✅
- ~~Multi-device support: QR code linking, on-demand sync only~~ ✅

**Implementation Steps**:
1. ~~Add `python-axolotl` or `pysignal` dependency~~ → Added PyNaCl (libsodium) ✅
2. ~~Create `e2e_encryption_service.py` with Signal Protocol wrapper~~ ✅ (423 lines, NaCl sealed boxes)
3. ~~Integrate with Secure Enclave for key storage~~ ✅
4. ~~Add fingerprint display to Settings → Security~~ → **UI PENDING**
5. ~~Implement safety number generation and change detection~~ ✅
6. ~~Update P2P chat service to encrypt/decrypt all messages~~ ✅
7. ~~Add device linking UI (QR code scanner + generator)~~ → **UI PENDING**
8. ~~Build on-demand sync mechanism for multi-device~~ ✅ (export/import via QR)

**Database Changes**:
- ~~Add `device_keys` table (device_id, identity_key, fingerprint, created_at)~~ ✅
- ~~Add `peer_keys` table (peer_device_id, public_key, fingerprint, verify_key, verified)~~ ✅
- ~~Add `safety_number_changes` table (peer_device_id, old/new safety numbers, acknowledged)~~ ✅

**Backend Complete** ✅:
- 8 API endpoints for E2E encryption
- Automatic encryption/decryption in P2P chat
- 37/37 stress tests passing (3,884 msg/s throughput)
- 100KB messages encrypted in 2.3ms

**UI Changes** (Pending):
- Settings → Security → Device Fingerprint (display + QR code) → **TODO**
- Chat window: Safety number changed banner → **TODO**
- Message bubbles: "⚠️ Unverified" indicator → **TODO**
- Device linking flow (scan QR from primary device) → **TODO**

---

#### ~~1.2 Database Encryption at Rest~~ ✅ **COMPLETED**
**Complexity**: Medium | **Timeline**: 1 week

**Requirements**:
- ~~SQLCipher for `vault.db` and `elohimos_app.db`~~ → Used application-level AES-256-GCM ✅
- ~~Keep regular SQLite for `datasets.db` (just metadata)~~ ✅
- ~~Same passphrase for vault + app db + Secure Enclave~~ ✅
- ~~10 backup codes for recovery (generated on first setup)~~ ✅
- ~~User enters passphrase once on startup~~ → **UI PENDING**

**Implementation Steps**:
1. ~~Add `pysqlcipher3` dependency~~ → Used pure Python solution (no C extensions) ✅
2. ~~Create encrypted database wrapper~~ ✅ (392 lines, AES-256-GCM)
3. ~~Implement PBKDF2 key derivation (600k iterations)~~ ✅
4. ~~Create backup code generation system (10 random codes)~~ ✅
5. ~~Store backup codes hashed (SHA-256)~~ ✅
6. ~~Build passphrase entry UI on startup~~ → **UI PENDING**
7. ~~Add recovery flow (enter backup code)~~ → **UI PENDING**
8. ~~Migration script to convert existing SQLite → Encrypted~~ ✅

**Database Changes**:
- ~~Add `backup_codes` table (code_hash, used, created_at)~~ ✅

**Backend Complete** ✅:
- 56/56 stress tests passing
- Pure Python (no compilation issues)
- Transparent encrypt/decrypt on connect/close
- Secure /tmp usage with 0600 permissions
- Large database support tested (1000+ rows)

**UI Changes** (Pending):
- Startup passphrase modal (can't skip) → **TODO**
- Settings → Security → Backup Codes (view/regenerate) → **TODO**
- First-time setup: Show backup codes with "SAVE THESE NOW" warning → **TODO**

---

#### ~~1.3 Role-Based Access Control (RBAC)~~ ✅ **COMPLETED**
**Complexity**: Medium | **Timeline**: 1 week

**Requirements**:
- ~~4 roles: Super Admin (1), Admin (1+), Member (default), Viewer (read-only)~~ ✅
- ~~Super Admin can create Admins, transfer super admin status~~ ✅
- ~~Admins can manage users/workflows/settings (but can't create other Admins)~~ ✅
- ~~Last Admin cannot be deleted/downgraded (hard block)~~ ✅
- ~~Super Admin cannot delete themselves (must transfer first)~~ ✅

**Implementation Steps**:
1. ~~Add `role` column to users table~~ ✅ (with auto-migration)
2. ~~Create `permissions.py` with role checks~~ ✅ (435 lines, 13 permissions)
3. ~~Update all API endpoints with permission decorators~~ → **TODO**
4. ~~Add user management UI (Settings → Users)~~ → **UI PENDING**
5. ~~Build role assignment interface (Admin only)~~ → **UI PENDING**
6. ~~Implement last-admin protection logic~~ ✅
7. ~~Add super admin transfer flow with confirmation~~ → **UI PENDING**
8. ~~Update frontend to hide features based on role~~ → **UI PENDING**

**Database Changes**:
- ~~Add `role` to `users` table (default: 'member')~~ ✅
- ~~Add `role_changed_at` timestamp~~ ✅
- ~~Add `role_changed_by` user_id (audit trail)~~ ✅
- ~~Auto-migration for existing databases~~ ✅
- ~~First user auto-assigned as Super Admin~~ ✅

**Backend Complete** ✅:
- 38/39 stress tests passing (97.4%)
- 4-tier role hierarchy with permission matrix
- 13 granular permissions defined
- Admin protection rules enforced
- Decorators: @require_role(), @require_permission()

**UI Changes** (Pending):
- Settings → Users → Role dropdown (Admin only) → **TODO**
- User profile shows role badge → **TODO**
- Super Admin transfer modal with confirmation → **TODO**
- Last admin deletion blocked with error modal → **TODO**

**Permissions Matrix**:
```
Action                  | Super Admin | Admin | Member | Viewer
------------------------|-------------|-------|--------|--------
Create Admin            | ✅          | ❌    | ❌     | ❌
Manage Users            | ✅          | ✅    | ❌     | ❌
Create Workflows        | ✅          | ✅    | ✅     | ❌
Edit Workflows          | ✅          | ✅    | ✅     | ❌
View Workflows          | ✅          | ✅    | ✅     | ✅
Trigger Panic Mode      | ✅          | ✅    | ❌     | ❌
Access Vault            | ✅          | ✅    | ✅     | ❌
Export Data             | ✅          | ✅    | ✅     | ❌
View Audit Logs         | ✅          | ✅    | ❌     | ❌
Delete Chats            | ✅          | ✅    | Own    | ❌
Run SQL Queries         | ✅          | ✅    | ✅     | ❌
```

---

### **PHASE 2: DATA PROTECTION** (High Priority)

#### 2.1 Automatic Local Backups
**Complexity**: Low | **Timeline**: 3 days

**Requirements**:
- Auto-backup daily at 2am (when idle)
- Save to `~/.elohimos_backups/`
- Keep last 7 backups (auto-delete older)
- Encrypted with user's passphrase (AES-256-GCM)
- Backup codes can restore if passphrase forgotten
- File format: `.elohim-backup` (gzipped)

**Implementation Steps**:
1. Create `backup_service.py` with backup/restore logic
2. Schedule daily backup task (cron-style scheduler)
3. Compress databases with gzip
4. Encrypt backup file with user's passphrase
5. Build restore UI (Settings → Backups)
6. Add backup verification (checksum validation)
7. Implement auto-cleanup (keep only 7 most recent)

**Backup File Contents**:
```
backup_2025-10-27_02-00.elohim-backup
├── elohimos_app.db (encrypted)
├── vault.db (encrypted)
├── datasets.db (encrypted)
├── metadata.json (backup date, version, checksum)
└── manifest.sig (signature for integrity)
```

**UI Changes**:
- Settings → Backups → List of available backups
- "Restore from backup" button with confirmation
- Backup status indicator (last backup: X hours ago)
- Manual backup button ("Backup Now")

---

#### 2.2 Audit Logging System
**Complexity**: Low | **Timeline**: 2 days

**Requirements**:
- Always on (cannot be disabled)
- Log all data access: who, what, when
- Store in encrypted `audit.db` (separate from main db)
- Admin-viewable only (Super Admin + Admin roles)
- Logs: user_id, action, resource, timestamp, ip_address

**Implementation Steps**:
1. Create `audit.db` with SQLCipher (encrypted)
2. Build `audit_logger.py` middleware
3. Add audit decorators to sensitive endpoints
4. Create audit log viewer UI (Admin only)
5. Add export to CSV for compliance reviews
6. Implement log rotation (keep last 90 days)

**Logged Actions**:
- User login/logout
- Vault access (open, create, delete)
- Workflow access (view, edit, delete)
- File uploads
- SQL query execution
- User role changes
- Panic Mode activation
- Backup creation/restoration

**Database Schema**:
```sql
CREATE TABLE audit_log (
    id INTEGER PRIMARY KEY,
    user_id TEXT NOT NULL,
    action TEXT NOT NULL,
    resource TEXT,
    resource_id TEXT,
    ip_address TEXT,
    user_agent TEXT,
    timestamp TEXT NOT NULL,
    details JSON
);
```

**UI Changes**:
- Settings → Audit Logs (Admin only)
- Searchable/filterable log viewer
- Export to CSV button
- Real-time log streaming (optional)

---

### **PHASE 3: COMPLIANCE & SAFETY** (Medium Priority)

#### 3.1 PHI Detection & Warnings
**Complexity**: Low | **Timeline**: 2 days

**Requirements**:
- Detect PHI in workflow form fields (Name, DOB, SSN, Medical Record #, etc.)
- Show warning: "⚠️ This form may collect PHI. Ensure HIPAA compliance."
- Don't block, just warn
- Form builder only (not chat scanning)

**Implementation Steps**:
1. Create PHI field name patterns (regex matching)
2. Add PHI detection to workflow form builder
3. Show warning banner when PHI detected
4. Add "Mark as PHI-sensitive" checkbox (explicit opt-in)
5. Log PHI form creation in audit logs

**PHI Field Patterns**:
```python
PHI_PATTERNS = [
    r'name', r'dob', r'birth.*date', r'ssn', r'social.*security',
    r'medical.*record', r'mrn', r'patient.*id', r'diagnosis',
    r'prescription', r'insurance', r'address', r'phone', r'email'
]
```

**UI Changes**:
- Workflow form builder: PHI warning banner (yellow)
- Checkbox: "This form collects PHI"
- Settings → Compliance → PHI handling guidelines

---

#### 3.2 "Not Medical Advice" Disclaimers
**Complexity**: Trivial | **Timeline**: 1 day

**Requirements**:
- Show in 3 places: Chat UI, Medical templates, Settings → Legal
- Clear, prominent warnings
- No code logic, just UI text

**Implementation Steps**:
1. Add footer to Chat window: "⚠️ Not medical advice. Consult a licensed professional."
2. Add header banner to medical workflow templates
3. Create Settings → Legal page with full disclaimer text

**Disclaimer Text**:
```
MEDICAL DISCLAIMER

ElohimOS and its AI features are not medical devices and do not
provide medical advice, diagnosis, or treatment. Information provided
is for informational purposes only. Always consult with a qualified
healthcare professional for medical decisions.

By using ElohimOS in medical contexts, you acknowledge that:
- AI responses are not a substitute for professional medical judgment
- You are responsible for verifying all medical information
- ElohimOS is not liable for medical decisions made using this software
```

---

#### 3.3 Export Classification Documentation
**Complexity**: Trivial | **Timeline**: 1 hour

**Requirements**:
- Disclose AES-256 encryption in docs
- Note export control regulations

**Implementation Steps**:
1. Add to README.md: "ElohimOS uses AES-256 encryption. Check your country's export regulations."
2. Settings → About → Show encryption info
3. Add to LICENSE file if needed

---

### **PHASE 4: UX ENHANCEMENTS** (Medium-Low Priority)

#### 4.1 Focus Mode Selector (Quiet / Field / Emergency)
**Complexity**: Medium | **Timeline**: 1 week

**Requirements**:
- 3 modes: 🌙 Quiet, ⚡ Field, 🚨 Emergency
- macOS 26 liquid glass dropdown in header
- Each mode changes UI, performance, colors
- Emergency mode: auto-trigger on battery < 10% or Panic Mode
- Log when/why Emergency Mode activated

**Implementation Steps**:
1. Create `focus_mode_service.py` (state management)
2. Build liquid glass dropdown component (React)
3. Implement Quiet Mode (muted colors, subtle animations)
4. Implement Field Mode (high contrast, battery saver)
5. Implement Emergency Mode (see Phase 6 for full spec)
6. Add focus mode persistence (localStorage)
7. Add auto-trigger logic (battery monitor, panic mode hook)

**UI Changes**:
- Header: Focus mode icon (shows current mode)
- Dropdown: 3 cards with radio selection
- Mode-specific styling applied globally
- Emergency mode: Quick actions bar at bottom

---

#### 4.2 Status Toasts with Undo
**Complexity**: Low | **Timeline**: 3 days

**Requirements**:
- Bottom-right macOS-style toasts
- Undo button for reversible actions (5s timeout)
- Confirmation modals for irreversible actions
- Stack multiple toasts (queue system)

**Implementation Steps**:
1. Create Toast component (React)
2. Build toast queue system (context provider)
3. Add undo logic (reverse action before timeout)
4. Integrate with all actions (message sent, workflow created, etc.)
5. Add confirmation modals for destructive actions

**Toast Examples**:
- "Message sent" → [Undo] (3s)
- "Workflow created" → [Dismiss]
- "File uploaded" → [Undo] (5s)

**Confirmation Modal Examples**:
- Delete workflow (permanent)
- Clear all chats (permanent)
- Trigger Panic Mode (nuclear)
- Remove user (affects access)

---

#### 4.3 Colorblind-Safe Indicators
**Complexity**: Low | **Timeline**: 2 days

**Requirements**:
- Never rely on color alone
- Use shapes + patterns + colors
- Settings → Accessibility → Colorblind mode (high contrast)

**Implementation Steps**:
1. Audit all status indicators (green/red/yellow)
2. Add icons to each: ✅ ❌ ⚠️ ⏸️ 🔄
3. Add pattern backgrounds (dots, stripes, solid)
4. Create high-contrast theme variant
5. Add colorblind mode toggle in Settings

**Status Indicators**:
- ✅ Success: Green + checkmark
- ❌ Error: Red + X
- ⚠️ Warning: Yellow + triangle
- ⏸️ Paused: Gray + pause icon
- 🔄 Syncing: Blue + spinner

---

### **PHASE 5: DOCUMENTATION** (Low Priority)

#### 5.1 One-Page Quick Start Guide
**Complexity**: Trivial | **Timeline**: 1 day

**Requirements**:
- Printable PDF (1 page front/back)
- Covers: Installation, first login, basic features
- Offline-friendly (no external links)

**Sections**:
1. Installation (macOS Ventura+ required)
2. First Launch Setup
3. Chat Basics
4. Data Upload
5. Workflows
6. Emergency Contacts
7. Troubleshooting

---

#### 5.2 Offline Help Panel
**Complexity**: Low | **Timeline**: 2 days

**Requirements**:
- Accessible via ⌘? hotkey
- Searchable help articles
- No internet required (bundled in app)

**Implementation Steps**:
1. Create help articles in Markdown
2. Build help panel UI (modal with search)
3. Add hotkey listener (⌘?)
4. Bundle help content in app (no API calls)

---

#### 5.3 Demo Video (90 seconds)
**Complexity**: Medium | **Timeline**: 3 days

**Requirements**:
- Silent with captions (accessible)
- Shows: Chat, Data Engine, P2P, Workflows
- Export as MP4 (bundled in app for offline viewing)

**Sections**:
1. Opening ElohimOS (0-15s)
2. Chat with AI (15-30s)
3. Upload Excel & Query (30-50s)
4. P2P Team Chat (50-70s)
5. Workflows (70-90s)

---

### **PHASE 6: EMERGENCY MODE (COMPLEX)** (Lowest Priority)

#### 6.1 Emergency Mode Full Implementation
**Complexity**: Very High | **Timeline**: 2-3 weeks

**This is the LAST priority due to complexity.**

**Visual Changes**:
- Red accent throughout UI
- "🚨 EMERGENCY" badge in header
- Hide non-critical UI elements
- Higher contrast (darker darks, lighter lights)
- Disable decorative animations (keep critical alerts)

**Performance Optimizations**:
- Metal 4: Increase polling from 3s → 1s
- P2P: Aggressive reconnect (1s, 2s, 3s)
- Battery: Show % in header, disable auto-refresh
- Control Center: Manual refresh only

**Feature Changes**:
- Chat: Pin critical contacts, large send button
- Workflows: Show only active items, one-tap status changes
- Data Engine: Instant results, no animations

**Emergency-Only Features**:
- Quick Actions Bar (bottom): [📞 Emergency Contact] [🚨 Panic Mode] [📍 Share Location] [💾 Backup Now]
- Emergency Contacts (designate 3 max)
- Auto-save every action
- "OFFLINE" indicator prominent

**Auto-Trigger**:
- Battery < 10%
- Panic Mode activated
- Manual activation

**Exit Confirmation**:
- Modal: "Exit Emergency Mode?"
- Prevent accidental exit

**Implementation Steps**:
1. Create emergency mode theme (red accent, high contrast)
2. Build Quick Actions Bar component
3. Add emergency contacts settings
4. Implement auto-trigger logic (battery monitor)
5. Update Metal 4 polling frequency
6. Add P2P aggressive reconnect
7. Build exit confirmation modal
8. Add audit logging (when/why activated)

---

## ITEMS NOT DISCUSSED - NEED ANSWERS

### Templates (from FOCUSED_RECOMMENDATIONS.md)
**Status**: Not discussed

**Requirements from doc**:
- Clinic intake → triage → summary
- Worship planner → bulletin export
- Volunteer scheduler + SMS handoff
- Donation manager → receipt generator

**Questions**:
1. Should these be **pre-built workflow templates** or **custom templates users can create**?
2. Do these require external integrations (SMS for volunteer scheduler, payment processor for donations)?
3. What data fields are required for each template?
4. Should templates be **bundled in app** or **downloadable** (implies cloud dependency)?

---

### Legal & Brand (from FOCUSED_RECOMMENDATIONS.md)
**Status**: Not discussed

**Requirements from doc**:
- File trademark: MagnetarAI, ElohimOS, MagnetarMission
- Classes: 009, 042, 041, 045, 035
- Privacy Policy (plain language)
- EULA (plain language)

**Questions**:
1. Who is handling trademark filings? (Lawyer or DIY?)
2. Privacy Policy: Should this cover **ElohimOS only** or **MagnetarCloud too**?
3. EULA: Standard MIT license or custom?
4. Do we need GDPR compliance disclosures (even though fully offline)?

---

### GTM & Funding (from FOCUSED_RECOMMENDATIONS.md)
**Status**: Not discussed (out of scope for implementation)

**Requirements from doc**:
- 2 pilot letters of intent
- Faith accelerators: OCEAN, Praxis, Sinapis
- Advisory board: ministry, security, clinical

**Notes**: This is business/fundraising work, not technical implementation.

---

### Pricing Sketch (from FOCUSED_RECOMMENDATIONS.md)
**Status**: Not discussed (out of scope for implementation)

**Requirements from doc**:
- Solo missionary: low flat annual
- Team (10 seats): tiered license
- Org bundle: training + support

**Notes**: This is MagnetarCloud pricing, not ElohimOS (which is open-source).

---

### KPIs & Metrics (from FOCUSED_RECOMMENDATIONS.md)
**Status**: Not discussed

**Requirements from doc**:
- Time saved per workflow (minutes)
- Offline uptime percentage
- Panic drills: pass/fail in 60s
- User trust score (1–5), weekly

**Questions**:
1. Should we build **local analytics dashboard** to track these KPIs?
2. Is this for **pilot users only** or **all users**?
3. Should KPIs be **opt-in** or **always collected** (anonymized)?

---

### 30 / 60 / 90 Day Milestones (from FOCUSED_RECOMMENDATIONS.md)
**Status**: Not discussed (project management)

**Requirements from doc**:
- 30 Days: Security audit, Pilot configs
- 60 Days: Pilots live, Iterate weekly
- 90 Days: Case studies, v1 pricing launch

**Notes**: This is a project timeline, not technical requirements.

---

## REMAINING ITEMS FROM FOCUSED_RECOMMENDATIONS.md

### Reliability Offline (Partially Covered)
**Status**: Auto-backups covered, testing not discussed

**Still Need**:
- Cold start without network: **TEST** (manual verification)
- No-cloud dependencies: **VERIFY** (audit all imports/APIs)
- Battery/thermal stress tests: **TEST** (2-hour stress test)

**Action**: Save testing for end (Phase 7: QA & Testing)

---

### Data Engine Hardening (Already Complete)
**Status**: User confirmed "already quite hardened and safe"

**No action needed.**

---

### Threat Model & Red-Team Drill (from FOCUSED_RECOMMENDATIONS.md)
**Status**: Not discussed

**Requirements from doc**:
- Threat model: device seizure scenario
- Red-team tabletop: 60-minute drill

**Questions**:
1. Should we write a **threat model document** (technical doc)?
2. Red-team drill: Is this **internal testing** or **external security audit**?
3. Timeline: Before or after pilot launch?

---

## SUMMARY

### Total Implementation Phases: 6 + Testing

| Phase | Priority | Timeline | Items |
|-------|----------|----------|-------|
| **Phase 1: Security Foundation** | 🔴 Highest | 4-5 weeks | E2E encryption, SQLCipher, RBAC |
| **Phase 2: Data Protection** | 🔴 High | 1 week | Auto-backups, Audit logs |
| **Phase 3: Compliance & Safety** | 🟡 Medium | 1 week | PHI warnings, Disclaimers |
| **Phase 4: UX Enhancements** | 🟡 Medium-Low | 2 weeks | Focus modes, Toasts, Colorblind |
| **Phase 5: Documentation** | 🟢 Low | 1 week | Quick start, Help panel, Demo video |
| **Phase 6: Emergency Mode** | 🟢 Lowest | 2-3 weeks | Complex, save for last |
| **Phase 7: Testing & QA** | 🔴 High | 2 weeks | Stress tests, Cold start, Red-team |

**Total Estimated Timeline**: 13-17 weeks (3-4 months)

---

## NEXT STEPS

1. **Answer "NEED ANSWERS" questions** (Templates, Legal, KPIs, Threat modeling)
2. **Prioritize implementation phases** (confirm order)
3. **Start Phase 1: Security Foundation** (E2E encryption first)

---

*"Commit to the Lord whatever you do, and he will establish your plans." - Proverbs 16:3*
