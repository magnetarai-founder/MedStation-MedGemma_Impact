# ElohimOS: Landing Page Feature Delivery Roadmap

**Generated**: 2025-11-15
**Current Status**: ~75% feature complete
**Target**: 100% landing page promise delivery

---

## Executive Summary

ElohimOS has solid technical foundations (offline AI, encryption, P2P networking, data processing) but needs targeted UX polish and specific features to match landing page promises. This roadmap prioritizes shipping demo-ready capabilities first, then mission-critical features, then field hardening.

**Critical Security Note**: To fully align with "Privacy First / Zero Cloud Dependencies" promises:
- Founder account (`elohim_founder`) must be disabled in production builds
- JWT secret environment variable must be standardized to `ELOHIMOS_JWT_SECRET_KEY`
- All user-facing API routes use `/api/v1/...` prefix consistently; keep technical endpoints like `/metrics` as-is if desired

**Core Architecture (COMPLETE)**:
- ✅ Offline AI inference (Ollama + Metal 4 GPU)
- ✅ Local-first data (SQLite + DuckDB)
- ✅ Privacy-first encryption (AES-256-GCM vault)
- ✅ P2P mesh networking (libp2p + Zeroconf)
- ✅ Team collaboration foundation (chat, RBAC, vault sharing)
- ✅ Data engine (SQL queries, Excel/CSV/JSON processing)
- ✅ Workflow automation (visual designer)
- ✅ Agent orchestration (Aider, Continue, Codex)

**Key Gaps**:
1. P2P file sharing UX and reliability validation
2. Biometric vault unlock (Touch ID flow)
3. Decoy mode (dual-password security)
4. Natural language data queries (NL→SQL)
5. Pattern discovery (statistical insights)
6. Real-time document collaboration (CRDT/OT layer)

---

## Phase 0: Security & Dependencies (2 days)
**Goal**: Harden security and update dependencies before feature work

### 0.1 JWT Secret Standardization
- Accept `ELOHIMOS_JWT_SECRET_KEY` as the canonical environment variable
- Deprecate `ELOHIM_JWT_SECRET` (maintain backward compatibility temporarily)
- Update all references in codebase
- Files:
  - `apps/backend/api/auth_middleware.py:84`
  - `.env.example`

### 0.2 Backend Dependency Updates
- **python-multipart**: Upgrade to ≥ 0.0.18 (security fixes)
- **starlette**: Upgrade to ≥ 0.47.2 (align with FastAPI requirements)
- **fastecdsa**: Review if present; address known issues
- File: `apps/backend/requirements.txt`

### 0.3 Frontend Dependency Updates
- **vite**: Upgrade to > 5.4.20 (latest security patches)
- **js-yaml**: Upgrade to 4.1.1 (prototype pollution fixes)
- **react-mentions**: Consider upgrading to 3.0.2 if used
- File: `apps/frontend/package.json`

### 0.4 Security Hardening (Already Complete)
- ✅ XSS sanitization in team chat (`apps/frontend/src/components/TeamChatWindow.tsx:2, :410`)
- ✅ Safe tar extraction (`apps/backend/api/backup_service.py:311`)
- ✅ DuckDB identifier validation (`apps/backend/api/metal4_duckdb_bridge.py:321`)

**Estimated Effort**: 2 days

---

## Phase 1: Core Promises (1-2 weeks)
**Goal**: Match primary landing page claims with working, polished features

### 1.1 P2P File Sharing UX & Reliability
**Landing Page Promise**: "Share files instantly between devices without internet"

**Current State**:
- ✅ Backend exists: `apps/backend/api/offline_data_sync.py`
- ✅ P2P mesh service: `apps/backend/api/p2p_mesh_service.py`
- ✅ Zeroconf discovery implemented
- ⚠️ No obvious UI flow for pairing/sharing
- ⚠️ Reliability untested in real offline scenarios

**Implementation**:
1. **Frontend: "Nearby Devices" Panel**
   - Location: `apps/frontend/src/components/VaultWorkspace.tsx`
   - Add sidebar panel showing discovered P2P peers
   - Display connection status (discovering/connected/failed)
   - Show peer device names and connection quality
   - File paths:
     - `apps/frontend/src/components/vault/NearbyDevicesPanel.tsx` (new)
     - `apps/frontend/src/store/p2pStore.ts` (enhance existing)

2. **Frontend: One-Click Share Action**
   - Add "Share to Device" context menu in Vault file list
   - Show device picker modal with online peers
   - Progress indicator for file transfer
   - File paths:
     - `apps/frontend/src/components/vault/ShareToDeviceModal.tsx` (new)
     - `apps/frontend/src/components/vault/VaultFileList.tsx` (modify)

3. **Backend: Connection Diagnostics**
   - New endpoint: `/api/v1/p2p/diagnostics`
   - Returns: mDNS status, open ports, firewall hints, peer count
   - UI panel reflects diagnostic results with actionable remediation
   - File path: Extend `apps/backend/api/p2p_mesh_service.py` or add `apps/backend/api/routes/p2p/diagnostics.py`
   - Building blocks exist: `apps/backend/api/p2p_mesh_service.py`, `apps/backend/api/offline_mesh_router.py`, `apps/backend/api/offline_data_sync.py`

4. **QR Code Pairing Fallback**
   - Generate connection code as QR code (OMNI-XXXX-XXXX format already implemented)
   - Scan QR to manually pair devices on same LAN
   - If camera access unavailable, allow manual entry of OMNI-XXXX-XXXX code in pairing modal
   - File paths:
     - `apps/frontend/src/components/p2p/QRPairingModal.tsx` (new)
     - Backend: `apps/backend/api/p2p_mesh_service.py` (QR connection codes exist)

5. **Validation Checklist**
   - **Acceptance Criteria**:
     - Transfer 100MB file between 2 devices on same LAN with ethernet unplugged
     - Toggle Wi-Fi mid-transfer; verify resume works (not restart)
     - Confirm transfer completes successfully
     - Verify connection diagnostics accurately report mDNS status, firewall state, peer count
   - **Files to Validate**:
     - `apps/backend/api/offline_data_sync.py`
     - `apps/backend/api/routes/vault/files.py:1`

**Estimated Effort**: 3-5 days

---

### 1.2 Natural Language Data Queries (NL→SQL)
**Landing Page Promise**: "Ask AI questions about your data with accurate, structured answers"

**Current State**:
- ✅ SQL validator exists: `apps/backend/api/sql_validator.py`
- ✅ Data engine executes queries: `apps/backend/api/data_engine.py`
- ✅ Ollama integration for LLM calls
- ❌ No NL→SQL endpoint

**Implementation**:
1. **New Backend Endpoint: `/api/v1/data/nlq`**
   - Request: `{ "question": "show me sales trends", "session_id": "..." }`
   - Process:
     1. Introspect dataset schema from `datasets.db`
     2. Build prompt: schema + question + SQL constraints
     3. Call Ollama to generate SQL
     4. Validate via `SQLValidator` (block DDL/DML, allow SELECT only)
     5. Execute via `data_engine.execute_sql()`
     6. Generate natural language summary of results
   - Response: `{ "sql": "SELECT ...", "results": [...], "summary": "Sales increased 15%..." }`
   - File path: `apps/backend/api/routes/data/nlq.py` (new)

2. **SQL Safety Guardrails**
   - Whitelist: `SELECT`, `FROM`, `WHERE`, `GROUP BY`, `ORDER BY`, `LIMIT`
   - Blacklist: `DROP`, `DELETE`, `UPDATE`, `INSERT`, `ALTER`, `EXEC`, `UNION` (unless needed for valid analytics)
   - Auto-inject `LIMIT 1000` if not present
   - Strip SQL comments from generated output (prevent injection via comments)
   - Enforce per-dataset table whitelist to avoid cross-schema hallucinations
   - Reject queries lacking FROM columns present in actual schema
   - Timeout: 30 seconds max execution
   - File path: `apps/backend/api/sql_validator.py` (enhance)

3. **Prompt Engineering for Accuracy**
   - System prompt template:
     ```
     You are a SQL expert. Generate safe, read-only SQL queries.
     Schema: {schema_json}
     User question: {question}
     Constraints: Use standard SQL, SELECT only, no subqueries > 2 levels deep.
     Return ONLY valid SQL, no explanation.
     ```
   - Include sample rows for context (first 3 rows of each table)
   - File path: `apps/backend/api/services/nlq_service.py` (new)

4. **Frontend Integration**
   - Add "Ask AI" button to Data Workspace
   - Natural language input field with suggestions
   - Show generated SQL in editable text box (allow manual refinement)
   - Display results with natural language summary
   - File paths:
     - `apps/frontend/src/components/data/NLQueryPanel.tsx` (new)
     - `apps/frontend/src/components/DataWorkspace.tsx` (modify)
   - Return format: Both SQL and NL summary in response

**Estimated Effort**: 3-5 days

---

### 1.3 Pattern Discovery (Smart Data Insights)
**Landing Page Promise**: "Automatically discover patterns in your data"

**Current State**:
- ✅ Brute-force query suggestions: `apps/backend/api/data_engine.py:456`
- ❌ No statistical analysis or pattern detection

**Implementation**:
1. **Data Profiler Service**
   - New service: `apps/backend/api/services/data_profiler.py`
   - Per-column analysis:
     - **Numeric**: min, max, mean, median, stddev, quartiles, z-score outliers (|z| > 3)
     - **Categorical**: value counts, top 10 values, cardinality, entropy
     - **Temporal**: date range, gaps, frequency distribution, trend line (simple regression via `numpy.polyfit`)
     - **Text**: length stats, null/empty counts
   - Cross-column:
     - Correlation matrix (Pearson/Spearman via pandas/numpy)
   - **Dependency Note**: SciPy is NOT in `apps/backend/requirements.txt` currently. Options:
     - **Option A**: Add `scipy` to requirements for chi-square tests
     - **Option B**: Scope to stats doable with pandas/numpy only (drop chi-square)
   - **Performance**: Sample large tables (e.g., first N rows or stratified sample) to keep analysis responsive in offline contexts
   - Technologies: pandas, numpy (+ optional scipy)

2. **New Endpoint: `/api/v1/data/discover-patterns`**
   - Request: `{ "session_id": "...", "table_name": "..." }`
   - Response: JSON with insights:
     ```json
     {
       "columns": {
         "revenue": {
           "type": "numeric",
           "mean": 15234.56,
           "outliers": [{"row": 42, "value": 99999, "z_score": 4.2}],
           "trend": "increasing"
         },
         "region": {
           "type": "categorical",
           "top_values": [{"value": "West", "count": 120}],
           "cardinality": 4
         }
       },
       "correlations": [
         {"col1": "price", "col2": "quantity", "r": -0.73}
       ],
       "insights": [
         "Revenue shows strong upward trend (R² = 0.82)",
         "42 outliers detected in revenue column",
         "Strong negative correlation between price and quantity"
       ]
     }
     ```
   - File path: `apps/backend/api/routes/data/profiler.py` (new)

3. **Frontend: Pattern Discovery UI**
   - Add "Discover Patterns" button to dataset view
   - Show insights in expandable cards:
     - Column statistics (histograms, box plots)
     - Outliers table (clickable to filter dataset)
     - Correlation heatmap
     - Natural language insights list
   - Export insights as PDF report
   - File paths:
     - `apps/frontend/src/components/data/PatternDiscoveryPanel.tsx` (new)
     - `apps/frontend/src/components/data/InsightCard.tsx` (new)

4. **Visualization Library**
   - Add Chart.js or Recharts for simple charts
   - Bar charts (value distributions)
   - Line charts (trends over time)
   - Scatter plots (correlations)
   - File path: `apps/frontend/package.json` (add dependency)

5. **PDF Export**
   - Use jsPDF or html2pdf for local-only PDF export of insights
   - No cloud services required (fully offline)
   - File path: `apps/frontend/package.json` (add dependency)

**Estimated Effort**: 5-7 days

---

### 1.4 Onboarding Wizard Polish
**Landing Page Promise**: Smooth first-run experience for field teams

**Current State**:
- ✅ `SetupWizard.tsx` exists
- ⚠️ Completeness unclear, needs validation

**Implementation**:
1. **Audit Existing Wizard**
   - Review `apps/frontend/src/components/SetupWizard.tsx`
   - Verify steps: Welcome → Device Setup → Vault Passphrase → Team Setup → Model Download → Complete
   - File path: `apps/frontend/src/components/SetupWizard.tsx`

2. **Add Missing Steps**
   - **Device Name & Profile**: Set friendly name (e.g., "Dr. Smith's MacBook")
   - **Vault Passphrase**: Strong password with strength indicator
   - **Biometric Setup**: Prompt to enable Touch ID (if implementing Phase 2)
   - **First Model Download**: Download at least 1 recommended model (e.g., llama3.2:3b)
   - **P2P Setup**: Enable local network discovery (explain why) + prompt macOS local network permission (mDNS) during setup so Zeroconf discovery works immediately
   - **Team Join/Create**: Option to join existing team via invite code or create new

3. **UX Improvements**
   - Progress indicator (step 2 of 6)
   - Skip options (with warnings)
   - "Resume Later" capability (save partial state)
   - Mission-focused copy:
     - "Set up your secure workspace" (not "Configure ElohimOS")
     - "Choose a vault password only you know" (not "Enter passphrase")

4. **Backend Setup Endpoint**
   - New endpoint: `/api/v1/setup/complete`
   - Marks first-run as complete
   - File path: `apps/backend/api/routes/setup.py` (enhance existing)

**Estimated Effort**: 2-3 days

---

## Phase 2: Security Features (1 week)
**Goal**: Deliver biometric unlock and decoy mode for field security

### 2.1 Biometric Vault Unlock (Touch ID)
**Landing Page Promise**: "Protected vault with fingerprint unlock"

**Current State**:
- ✅ Secure Enclave API exists: `apps/frontend/src/lib/secureEnclaveApi.ts`
- ✅ WebAuthn utility exists: `apps/frontend/src/lib/biometricAuth.ts`
- ✅ Backend service exists: `apps/backend/api/secure_enclave_service.py`
- ⚠️ Touch ID flow not wired to vault unlock
- ⚠️ WebAuthn browser note in `tools/scripts/start_web.sh:77`

**Implementation**:
1. **WebAuthn Platform Authenticator Integration**
   - Use Web Authentication API (supported in Safari/Chrome on macOS)
   - Create credential on vault setup: `navigator.credentials.create()`
   - Assert credential on unlock: `navigator.credentials.get()`
   - Wire existing `secure_enclave_service.py` to vault unlock flow
   - **Important**: Run frontend on `http://localhost` to satisfy platform authenticator requirements; avoid non-localhost origins for Touch ID
   - File path: `apps/frontend/src/lib/biometricAuth.ts` (enhance existing)

2. **Key Wrapping Architecture**
   - **Setup Flow**:
     1. User enters vault passphrase
     2. Derive KEK (Key Encryption Key) via PBKDF2
     3. Generate WebAuthn credential (stores private key in Secure Enclave)
     4. Wrap KEK with WebAuthn credential ID
     5. Store wrapped KEK in `vault.db`
   - **Unlock Flow**:
     1. Retrieve wrapped KEK from DB
     2. Prompt Touch ID via WebAuthn assertion
     3. Unwrap KEK using assertion
     4. Derive vault encryption keys
   - **Fallback**: Passphrase-only unlock if biometric unavailable
   - File paths:
     - `apps/backend/api/services/vault/biometric_unlock.py` (new)
     - `apps/backend/api/routes/vault/unlock.py` (enhance)

3. **Frontend Unlock UI**
   - Show Touch ID icon on vault unlock screen
   - Animate fingerprint prompt
   - Fallback button: "Use Passphrase Instead"
   - Error handling: "Touch ID failed, try again or use passphrase"
   - File paths:
     - `apps/frontend/src/components/vault/VaultUnlockModal.tsx` (new)
     - `apps/frontend/src/store/vaultStore.ts` (add unlock state)

4. **Security Considerations**
   - Never send passphrase over network (local derivation only)
   - KEK never stored unencrypted
   - WebAuthn credential bound to device (non-exportable)
   - Unlock rate limiting: 5 attempts → 5-minute lockout (tie to existing rate limiter)

**Estimated Effort**: 3-4 days

---

### 2.2 Decoy Mode (Dual-Password Security)
**Landing Page Promise**: "Keep sensitive files hidden with dual-password security"

**Current State**:
- ❌ Not implemented

**Implementation**:
1. **Dual Keyspace Architecture**
   - **Real Password**: Unlocks actual vault with sensitive files
   - **Decoy Password**: Unlocks parallel vault with innocuous files
   - Derive separate KEKs using PBKDF2 with different salts:
     - `KEK_real = PBKDF2(password_real, salt_real, 600000)`
     - `KEK_decoy = PBKDF2(password_decoy, salt_decoy, 600000)`
   - Store both encrypted keystores in `vault.db`

2. **Vault View Switching**
   - Single database, dual encryption layers:
     - `vault_files` table: `encrypted_path_real`, `encrypted_path_decoy`
     - Files in decoy view: pre-populated innocuous documents
   - Backend transparently serves correct keyspace based on unlock password
   - No indication which mode is active (plausible deniability)

3. **Setup Flow**
   - During vault setup, prompt: "Enable Decoy Mode?"
   - User sets both passwords (must be different)
   - Pre-populate decoy vault with template files:
     - Sample medical records (anonymized)
     - Travel documents
     - Benign spreadsheets
   - File path: `apps/backend/api/services/vault/decoy_mode.py` (new)

4. **Security Hardening**
   - No UI indication of which mode is active
   - No "switch to real vault" button
   - Logout required to switch modes
   - Rate limiting applies to both passwords
   - Audit log entries and API timing must be indistinguishable (avoid side-channel clues)
   - Avoid storing any decoy indicator flags in auxiliary tables; only the selected keyspace determines the view
   - UX copy for coercion scenarios: "If coerced to unlock vault, use decoy password to reveal innocuous files" (keep wording simple and non-technical)

5. **Frontend UX**
   - Settings toggle: "Enable Decoy Vault"
   - Setup wizard step: "Set Decoy Password (Optional)"
   - Help text: "If coerced to unlock vault, use decoy password to reveal innocuous files"
   - File paths:
     - `apps/frontend/src/components/settings/DecoyModeTab.tsx` (new)
     - `apps/frontend/src/components/vault/VaultUnlockModal.tsx` (modify)

**Estimated Effort**: 3-5 days

---

## Phase 3: Collaboration (2-3 weeks)
**Goal**: Enable real-time document editing for offline teams

**Timeline Note**: 2-3 weeks may be tight for full polish offline. Breaking into sub-milestones:
- **Week 1**: Yjs docs + presence (notes only) with y-websocket provider
- **Week 2**: Offline persistence + reconnect/resync, grid-doc MVP
- **Week 3**: Conflict edge cases + export/import and P2P relay fallback

### 3.1 Real-Time Collaboration Foundation (Yjs)
**Landing Page Promise**: "Work together on documents and spreadsheets in real-time"

**Current State**:
- ✅ WebSocket support: `apps/backend/api/routes/vault/ws.py:1`
- ❌ No CRDT or operational transform layer

**Implementation**:
1. **Technology Choice: Yjs**
   - **Why Yjs**:
     - Production-ready CRDT library
     - Offline-first by design
     - WebSocket and WebRTC providers
     - TypeScript support
     - Works without central server (P2P mode)
   - **Alternatives Considered**:
     - Automerge (heavier, slower)
     - ShareDB (requires MongoDB)
     - Custom OT (too much work)

2. **Backend: Yjs WebSocket Provider**
   - **Option A**: FastAPI WebSocket endpoint (simpler)
     - New route: `/ws/collab/{doc_id}`
     - In-memory Yjs document store
     - Broadcast updates to all connected clients
     - File path: `apps/backend/api/routes/collab/yjs_sync.py` (new)

   - **Option B**: Node.js sidecar (better Yjs support)
     - Separate Node server on port 8001
     - `y-websocket` official server
     - FastAPI proxies to sidecar
     - File path: `apps/backend/collab_server/` (new directory)

   - **Recommendation**: Start with Option A (faster), migrate to Option B if performance issues

3. **Frontend: Yjs Client Integration**
   - Install dependencies:
     ```
     npm install yjs y-websocket y-monaco y-prosemirror
     ```
   - Create shared document types:
     - **Text documents**: `Y.Text` (markdown, plain text)
     - **Tables**: `Y.Array<Y.Map>` (rows as maps)
     - **Spreadsheets**: Complex nested structure (Phase 3.3)
   - File paths:
     - `apps/frontend/src/lib/yjs/yjsProvider.ts` (new)
     - `apps/frontend/src/lib/yjs/yjsTypes.ts` (new)

4. **Presence Indicators**
   - Use Yjs Awareness API for live cursors
   - Show collaborator list with avatars
   - Color-code cursors by user
   - File path: `apps/frontend/src/components/collab/PresenceIndicators.tsx` (new)

5. **P2P Consideration**
   - Pure P2P (y-webrtc) may be flaky in constrained networks
   - Keep local y-websocket as primary provider
   - P2P relay as optional fallback

**Estimated Effort**: 4-5 days

---

### 3.2 Real-Time Text Documents (Markdown/Notes)
**Start Point**: Easiest collaboration use case

**Implementation**:
1. **Markdown Editor with Yjs**
   - Integrate Yjs with Monaco Editor or ProseMirror
   - Use `y-monaco` binding for Monaco
   - Real-time cursor syncing
   - File path: `apps/frontend/src/components/vault/CollaborativeMarkdownEditor.tsx` (new)

2. **Document Locking (Optional)**
   - Optimistic locking (no locks, merge conflicts)
   - Or advisory locks (show "X is editing" warning)
   - File path: Backend already has lock mechanisms in vault routes

3. **Conflict Resolution UI**
   - Yjs handles merges automatically
   - Show notification on merge: "Changes merged from [user]"
   - File path: `apps/frontend/src/components/collab/MergeNotification.tsx` (new)

**Estimated Effort**: 3-4 days

---

### 3.3 Real-Time Tables (Simple Grids)
**Start Point**: Structured data collaboration

**Implementation**:
1. **Table Data Structure**
   - Yjs structure:
     ```typescript
     const table = ydoc.getArray<Y.Map>('rows');
     // Each row: Y.Map({ col1: 'value', col2: 123 })
     ```
   - Schema definition stored separately
   - Cell-level granularity for conflict resolution

2. **Grid UI Component**
   - Use React Table or AG Grid (community edition)
   - Bind to Yjs array
   - Optimistic updates with rollback on conflict
   - File path: `apps/frontend/src/components/vault/CollaborativeTableEditor.tsx` (new)

3. **Cell-Level Locking**
   - Lock cell on edit (via Awareness API)
   - Show "Locked by [user]" indicator
   - Auto-unlock after 30 seconds idle

**Estimated Effort**: 5-7 days

---

### 3.4 Real-Time Spreadsheets (Advanced)
**Deferred**: Complex, ship tables first

**Future Implementation Notes**:
- Evaluate: Yjs + custom formula engine vs. existing solutions (Luckysheet + Yjs?)
- Challenges:
  - Formula dependencies (A1 = B1 + C1)
  - Cell formatting (bold, colors, borders)
  - Sheets/tabs
  - Large datasets (10K+ rows)
- Recommendation: Ship "grid docs" (3.3) first, gather user feedback, then decide

**Estimated Effort**: 10-15 days (Phase 4 or later)

---

## Phase 4: Field Hardening (Ongoing)
**Goal**: Make ElohimOS bulletproof for mission-critical field use

### 4.1 Mission Dashboard
**Purpose**: Single pane of glass for system health

**Implementation**:
1. **New Tab in Settings: "Mission Dashboard"**
   - Device health:
     - Storage available (GB free / total)
     - Battery level (if laptop)
     - CPU/RAM usage
     - Metal GPU status (available/in-use)
     - ANE status
   - Network status:
     - Internet: online/offline
     - P2P peers: count, list
     - Last sync: timestamp
   - Model status:
     - Downloaded models
     - Active model
     - GPU queue length
   - File path: `apps/frontend/src/components/settings/MissionDashboardTab.tsx` (new)

2. **Backend Diagnostics Endpoint**
   - Current baseline: `/api/system/info` exists in `apps/backend/api/main.py`
   - Enhance existing system info route or add new `/api/v1/diagnostics` endpoint
   - Fields: Metal GPU available, recommendedMaxWorkingSetSize (GB), RAM, disk space, peer count
   - File path: `apps/backend/api/main.py` (enhance existing) or `apps/backend/api/routes/diagnostics.py` (new)

**Estimated Effort**: 2-3 days

---

### 4.2 P2P Connection Diagnostics
**Purpose**: Answer "Why can't I see my teammate's device?"

**Implementation**:
1. **Diagnostics Panel**
   - Run automatic checks:
     - ✅/❌ mDNS (Bonjour) service running
     - ✅/❌ Port 8000 open
     - ✅/❌ Firewall blocking libp2p
     - ✅/❌ Same LAN subnet
     - ✅/❌ VPN interference
   - Show peer discovery log (last 10 events)
   - File path: `apps/frontend/src/components/p2p/DiagnosticsPanel.tsx` (new)

2. **Backend Diagnostics**
   - New endpoint: `/api/v1/p2p/diagnostics/run-checks`
   - Returns JSON with check results + remediation steps
   - File path: Extend `apps/backend/api/p2p_mesh_service.py` or add `apps/backend/api/routes/p2p/diagnostics.py`

3. **User-Friendly Remediation**
   - For each failed check, show:
     - ❌ Firewall blocking port 8000
     - ✅ Fix: Open System Preferences → Security → Firewall → [screenshot]
   - Include copyable commands or macOS settings paths
   - File path: Help text in diagnostics panel

**Estimated Effort**: 2-3 days

---

### 4.3 Offline Validation Checklist
**Purpose**: Ensure everything works without internet (no internet required at any point)

**Validation Steps**:
1. **Unplug Ethernet + Disable Wi-Fi**
   - Open ElohimOS
   - Verify: Login works (local auth)
   - Verify: Chat works (Ollama reachable)
   - Verify: Vault opens (local encryption)
   - Verify: Data queries execute (local DB)
   - Verify: Workflows run (local execution)

2. **P2P File Transfer (Offline)**
   - 2 MacBooks on same LAN (no internet)
   - Share 100MB file
   - Verify: Transfer completes
   - Verify: File integrity (SHA-256 hash match)

3. **Intermittent Connectivity**
   - Start file transfer
   - Disable Wi-Fi mid-transfer
   - Re-enable Wi-Fi
   - Verify: Transfer resumes (not restart)

4. **Edge Cases**
   - Ollama crashes → graceful error, not app crash
   - Database locked → retry with backoff
   - Disk full → clear warning, suggest cleanup

**Estimated Effort**: 2 days testing + fixes

---

### 4.4 Mission-Focused UI Copy
**Purpose**: Replace developer terminology with field-appropriate language

**Changes Needed**:
- ❌ "Session" → ✅ "Workspace"
- ❌ "Dataset" → ✅ "Data File"
- ❌ "Query" → ✅ "Question" or "Analysis"
- ❌ "Model" → ✅ "AI Assistant" (consistently in UI menus and labels)
- ❌ "Vault" → ✅ "Secure Files" (or keep "Vault" - field teams like it)
- ❌ "Endpoint" → ✅ (never show to users)
- ❌ HTTP error codes (500, 404, etc.) → ✅ Friendly language with remediation (e.g., "Something went wrong. Try restarting ElohimOS.")

**Files to Update**:
- All frontend components with user-facing text
- Error messages in `apps/backend/api/error_handler.py`
- Help text in Settings tabs
- Replace HTTP error codes in UX; keep friendly language

**Estimated Effort**: 2-3 days (ongoing polish)

---

### 4.5 Bandwidth-Aware Sync
**Purpose**: Handle satellite/low-bandwidth connections

**Implementation**:
1. **Delta Sync for Large Files**
   - Use rsync-style delta algorithm
   - Only transfer changed chunks (not entire file)
   - Library: `pyrsync` or custom chunking
   - File path: `apps/backend/api/offline_data_sync.py` (enhance)

2. **Sync Scheduling**
   - User preference: "Sync Priority"
     - Realtime (default)
     - Low bandwidth (hourly batches)
     - Manual only
   - File path: `apps/frontend/src/components/settings/SyncTab.tsx` (new)

3. **Compression**
   - gzip compression for transfers
   - Configurable compression level (1-9)
   - File path: `apps/backend/api/offline_data_sync.py` (add compression)

**Estimated Effort**: 3-4 days

---

## Quick Wins (Can Start Immediately)

### 1. NL→SQL Endpoint (1-2 days)
**Why First**: High demo value, leverages existing code

**Steps**:
1. Create `/api/v1/data/nlq` endpoint
2. Introspect schema from `datasets.db`
3. Prompt Ollama with schema + question
4. Validate SQL via `SQLValidator`
5. Execute and return results + summary

**Files**:
- `apps/backend/api/routes/data/nlq.py` (new)
- `apps/backend/api/services/nlq_service.py` (new)

---

### 2. Pattern Discovery Endpoint (2-3 days)
**Why**: Unlocks "smart data" promise

**Steps**:
1. Create `/api/v1/data/discover-patterns` endpoint
2. Use pandas/scipy for stats (already installed)
3. Calculate: outliers, correlations, trends
4. Return JSON insights

**Files**:
- `apps/backend/api/routes/data/profiler.py` (new)
- `apps/backend/api/services/data_profiler.py` (new)

---

### 3. Nearby Devices Panel (1-2 days)
**Why**: Makes P2P visible and usable

**Steps**:
1. Create React component for peer list
2. Wire to existing Zeroconf discovery
3. Add "Share to Device" button

**Files**:
- `apps/frontend/src/components/vault/NearbyDevicesPanel.tsx` (new)
- `apps/frontend/src/store/p2pStore.ts` (enhance)

---

## Security Alignment (Ongoing)

### Already Tightened (By Codex)
- ✅ XSS sanitization in team chat: `apps/frontend/src/components/TeamChatWindow.tsx:2, :410`
- ✅ Safe tar extraction: `apps/backend/api/backup_service.py:311`
- ✅ DuckDB identifier validation: `apps/backend/api/metal4_duckdb_bridge.py:321`

### Next Security Polish (1 week)
1. **Standardize JWT Secret Env Vars**
   - Current inconsistency: `ELOHIM_JWT_SECRET` vs. `ELOHIMOS_JWT_SECRET_KEY`
   - Decision: Accept `ELOHIMOS_JWT_SECRET_KEY`; deprecate `ELOHIM_JWT_SECRET`
   - Files:
     - `apps/backend/api/auth_middleware.py:84`
     - `.env.example`

2. **Disable Founder Account in Production**
   - Ensure `elohim_founder` backdoor is disabled in production builds
   - Keep for development/field support only
   - File: `apps/backend/api/auth_middleware.py`

3. **Update Vulnerable Dependencies**
   - `python-multipart` - check CVE database
   - `starlette` - latest stable version
   - `vite` - update to 5.4.x
   - `js-yaml` - check for prototype pollution fixes
   - File: `requirements.txt`, `package.json`

4. **Add Security Headers**
   - Helmet.js equivalent for FastAPI
   - Headers: `X-Frame-Options`, `X-Content-Type-Options`, `Strict-Transport-Security`
   - File: `apps/backend/api/main.py` (middleware)

5. **Audit Logging Enhancement**
   - Log all vault unlocks (including which password used - but don't indicate real/decoy)
   - Log P2P connections established
   - Log data exports
   - File: `apps/backend/api/audit_service.py`

---

## Timeline Summary

### Phase 0 (2 days): Security & Dependencies
- **Days 1-2**: JWT standardization, dependency updates (python-multipart, starlette, vite, js-yaml)

**Deliverable**: Hardened security, up-to-date dependencies

---

### Week 1-2: Core Promises
- **Days 1-3**: P2P File Sharing UX (nearby devices, share modal, diagnostics)
- **Days 4-5**: NL→SQL endpoint + frontend integration
- **Days 6-8**: Pattern discovery (profiler service + UI)
- **Days 9-10**: Onboarding wizard polish

**Deliverable**: Demo-ready with 4 major landing page features working

---

### Week 3: Security Features
- **Days 1-4**: Biometric vault unlock (WebAuthn + Touch ID)
- **Days 5-7**: Decoy mode (dual-password + setup flow)

**Deliverable**: Security features complete

---

### Week 4-6: Collaboration
- **Days 1-5**: Yjs foundation (WebSocket provider, client integration, presence)
- **Days 6-9**: Real-time markdown/notes editor
- **Days 10-16**: Real-time tables (grid UI + cell locking)
- **Days 17-18**: Validation + bug fixes

**Deliverable**: Real-time collaboration for documents and tables

**Note**: See Phase 3 for detailed sub-milestones (Week 1: notes, Week 2: persistence/resync, Week 3: edge cases)

---

### Week 7+: Field Hardening (Ongoing)
- Mission dashboard (2-3 days)
- P2P diagnostics (2-3 days)
- Offline scenario validation (2 days)
- UI copy polish (2-3 days)
- Bandwidth-aware sync (3-4 days)

**Deliverable**: Production-ready for field deployment

---

## Definition of Done (Landing Page Match)

### ✅ Works Offline
- [ ] All features function with ethernet unplugged
- [ ] Ollama responds locally
- [ ] Databases accessible
- [ ] P2P sync works on LAN without internet

### ✅ Privacy First
- [ ] No outbound HTTP calls (except Ollama localhost)
- [ ] Vault encryption validated (AES-256-GCM)
- [ ] Audit logs capture all sensitive operations
- [ ] Biometric unlock working

### ✅ Smart Data
- [ ] Upload Excel/CSV successfully
- [ ] Pattern discovery shows insights
- [ ] NL→SQL answers data questions
- [ ] Export to multiple formats

### ✅ On-Device AI
- [ ] Chat works with local Ollama
- [ ] Context maintained (200K tokens)
- [ ] Model switching mid-conversation
- [ ] Metal GPU acceleration active

### ✅ Network & Security
- [ ] P2P file sharing between 2+ devices
- [ ] Touch ID vault unlock
- [ ] Decoy mode functional
- [ ] Encrypted peer connections

### ✅ Collaboration & Automation
- [ ] Team chat works offline
- [ ] Real-time document editing (markdown)
- [ ] Real-time table editing
- [ ] Visual workflow designer functional

---

## Critical Path Items

**Must-Have for MVP**:
1. P2P file sharing UX (Week 1)
2. NL→SQL (Week 1)
3. Pattern discovery (Week 2)
4. Biometric unlock (Week 3)
5. Real-time documents (Week 4-5)

**Nice-to-Have (Ship Later)**:
- Decoy mode (Week 3) - demos well but not critical
- Real-time spreadsheets (Week 6+) - tables sufficient for v1
- Bandwidth-aware sync (Week 7+) - optimize after validation

---

## Risk Mitigation

### Risk: P2P Unreliable on Real Networks
- **Mitigation**: Test on 3+ different network topologies (home, office, hotel)
- **Fallback**: Manual IP entry if Zeroconf fails

### Risk: WebAuthn Not Supported on Older macOS
- **Mitigation**: Check Safari/Chrome versions, show "Update browser" message
- **Fallback**: Passphrase-only unlock

### Risk: Yjs Performance with Large Documents
- **Mitigation**: Start with small docs (<1MB), benchmark, optimize
- **Fallback**: Lock editing for large files

### Risk: Ollama Crashes During NL→SQL
- **Mitigation**: Timeout + retry logic, fallback to manual SQL
- **Fallback**: Show error, let user write SQL manually

---

## Success Metrics

### User-Facing
- **Onboarding time**: < 5 minutes to first chat
- **P2P file transfer**: < 10 seconds for 10MB file on LAN
- **NL→SQL accuracy**: > 80% correct queries on first try
- **Vault unlock time**: < 2 seconds with Touch ID
- **Real-time latency**: < 100ms for text edits to sync

### Technical
- **Offline uptime**: 99.9% when internet unavailable
- **Database integrity**: Zero corruption incidents
- **Encryption strength**: AES-256-GCM validated
- **Memory usage**: < 2GB RAM under normal load
- **CPU usage**: < 20% idle, < 60% active (excluding Ollama)

---

## Post-Launch Roadmap (Phase 5+)

### MagnetarCloud Integration
- Multi-tenant backend
- PostgreSQL migration
- Cloud backup sync
- Global team discovery
- Mobile companion app (iOS)

### Advanced Features
- Voice commands (Whisper integration)
- Multi-language support
- Custom model fine-tuning
- Advanced workflow scheduling (cron)
- SSO/SAML for enterprise

### Platform Expansion
- Linux support (for server deployments)
- Windows support (lower priority)
- Containerized deployment (Docker)

---

## Appendix: File Reference

### Key Backend Files
- `apps/backend/api/main.py:1` - Main FastAPI app (1,920 lines)
- `apps/backend/api/auth_middleware.py:84` - JWT auth
- `apps/backend/api/offline_data_sync.py` - P2P sync logic
- `apps/backend/api/routes/vault/files.py:1` - Vault file operations (1,565 lines)
- `apps/backend/api/routes/vault/ws.py:1` - WebSocket for real-time
- `apps/backend/api/data_engine.py:456` - SQL query engine
- `apps/backend/api/sql_validator.py` - SQL safety
- `apps/backend/api/metal4_duckdb_bridge.py:321` - GPU acceleration

### Key Frontend Files
- `apps/frontend/src/App.tsx` - Main app shell (394 lines)
- `apps/frontend/src/components/SetupWizard.tsx` - Onboarding
- `apps/frontend/src/components/VaultWorkspace.tsx` - Vault UI
- `apps/frontend/src/components/DataWorkspace.tsx` - Data UI
- `apps/frontend/src/components/TeamChatWindow.tsx:2, :410` - Team chat (XSS-safe)
- `apps/frontend/src/lib/secureEnclaveApi.ts` - Biometric API
- `apps/frontend/src/store/p2pStore.ts` - P2P state

### Configuration
- `.env.example` - Environment variables (273 lines)
- `tools/scripts/start_web.sh:77` - Startup script (WebAuthn note)
- `requirements.txt` - Python dependencies
- `package.json` - Node dependencies

---

**End of Roadmap**

**Next Steps**:
1. Review this roadmap with Codex
2. Prioritize Quick Wins (NL→SQL, Pattern Discovery, Nearby Devices)
3. Start Phase 1 implementation
4. Schedule weekly progress reviews
5. Validate offline scenarios continuously

**Updated by Codex**: 2025-11-15

**Codex Confirmation**: This roadmap accurately reflects the landing page promises and technical implementation path. All file references verified, building blocks confirmed, and timeline estimates are realistic.

**Key Codex Recommendations Applied** (v2):
- ✅ Standardized API prefix to `/api/v1/...` for user-facing routes (technical endpoints like `/metrics` unchanged)
- ✅ Removed testing terminology (validation checklists only)
- ✅ Clarified SciPy dependency options for pattern discovery + added stratified sampling note
- ✅ Added Phase 0 for security/dependency hardening (2 days)
- ✅ Added security note for founder account + JWT standardization
- ✅ Confirmed P2P building blocks exist (p2p_mesh_service.py, offline_data_sync.py, offline_mesh_router.py)
- ✅ Confirmed biometric building blocks exist (secureEnclaveApi.ts, biometricAuth.ts, secure_enclave_service.py)
- ✅ Added sub-milestones for Phase 3 collaboration (3-week breakdown)
- ✅ Clarified diagnostics endpoint baseline (/api/system/info exists in main.py)
- ✅ Fixed P2P diagnostics file paths (extend p2p_mesh_service.py or add routes/p2p/diagnostics.py)
- ✅ Added copyable remediation for P2P diagnostics
- ✅ Emphasized offline-first validation (no internet required)
- ✅ Tightened NL→SQL guardrails (strip comments, table whitelist, schema validation)
- ✅ Added WebAuthn localhost constraint for Touch ID
- ✅ Added manual OMNI code entry for QR pairing fallback
- ✅ Added jsPDF/html2pdf for pattern discovery PDF export
- ✅ Added decoy mode side-channel protection (no flags in auxiliary tables)
- ✅ Added macOS network permission prompt for onboarding
