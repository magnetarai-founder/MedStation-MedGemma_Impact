# MedStation Roadmap

Mac-first. On-device only. Approved medical models only. Gated for patient safety.

---

## Layer 0: Architecture — Kill the Python Backend

**The single biggest blocker.** `BackendManager.swift` uses `Process()` to launch `uvicorn` with a Python venv. Apple's App Sandbox strictly prohibits launching child processes. Nothing else matters until this is solved.

Current:
```
SwiftUI App → HTTP → Python FastAPI → HuggingFace Transformers → MPS
```

Target:
```
SwiftUI App → MLX Swift → Apple Silicon GPU
```

### 0.1 Native Inference via MLX Swift

Replace the entire Python backend with [MLX Swift](https://github.com/ml-explore/mlx-swift) for on-device LLM inference. Apple's own framework, built for Apple Silicon, sandbox-compliant.

- Convert MedGemma 1.5 4B weights to MLX format
- Replace `MedicalAIService.swift` HTTP calls with direct MLX inference
- Remove `BackendManager.swift` entirely
- Remove `apps/backend/` directory entirely
- Remove `APIConfiguration.swift` backend URL config

Alternative paths if MLX doesn't support MedGemma's architecture:
- **Core ML** — convert via `coremltools`, use Core ML API
- **ONNX Runtime** — export to ONNX, use `onnxruntime-swift`
- **llama.cpp** — if GGUF quantization is available for MedGemma

### 0.2 App Sandbox Entitlements

Configure `MedStation.entitlements`:
- `com.apple.security.app-sandbox` — required
- `com.apple.security.files.user-selected.read-write` — model weights, patient data
- `com.apple.security.files.downloads.read-write` — Application Support directory
- `com.apple.security.network.client` — initial model download from HuggingFace
- `com.apple.security.keychain` — encryption keys and auth tokens

### 0.3 Model Distribution

MedGemma 4B weights are ~8GB. Apple has a 4GB app size limit (20GB with On Demand Resources).

**Initial approach:** In-app download from HuggingFace on first launch. Store in `~/Library/Application Support/MedStation/models/`. Show download progress UI.

**Future:** On-Demand Resources (Apple CDN) or Core ML with 4-bit quantization (~2-3GB, bundleable).

---

## Layer 1: Security & Privacy

No PHI is ever written to disk unencrypted. No patient data ever leaves the device.

### 1.1 Encrypt Patient Data at Rest

`PersistenceHelpers.save()` currently writes plain JSON. Replace with AES-GCM encryption using CryptoKit. Store encryption key in Keychain via Secure Enclave. Unlock with Touch ID or password.

Files affected:
- `PersistenceHelpers.swift` — add `saveEncrypted` / `loadEncrypted`
- `MedicalPanel.swift` — `saveCaseToFile` uses encrypted persistence
- `MedicalAuditLogger.swift` — audit entries encrypted

### 1.2 HIPAA Audit Trail

Extend `MedicalAuditLogger` with full access logging:
- Every read, write, export, AI query, and login recorded
- Fields: timestamp, user_id, patient_id, encounter_id, action, resource, outcome
- Append-only SQLite table with SHA-256 chain (tamper detection)
- 7-year retention policy enforced at the storage layer
- Use `trySave()` instead of `save()` — audit log failures must not be swallowed

### 1.3 Model Safety Gate

MedStation runs one model at a time, and only approved medical models.
- Hardcoded allowlist: `google/medgemma-1.5-4b-it` (expand as Google releases new versions)
- Model integrity check on load (SHA-256 hash verification)
- Version pinning — clinician must acknowledge model version changes
- If model fails to load: clear "AI Unavailable" state, never serve stale output

### 1.4 Input Validation

- Prompt length cap (10,000 chars)
- `max_tokens` range (1-2048), `temperature` range (0.0-2.0)
- Image file path validation (no path traversal, allowed directories only)
- Base64 image size cap (10MB decoded)

---

## Layer 2: Silent Failure Remediation

Patient safety issues found by automated analysis. Fix before any feature work.

### Critical

| Issue | File | Problem | Fix |
|-------|------|---------|-----|
| Triage defaults to Semi-Urgent on parse failure | `MedicalWorkflowEngine.swift` | Emergency could be mis-triaged | Log warning, add `parse_failed` flag, surface uncertainty to user |
| Streaming errors call `onDone()` | `MedicalAIService.swift` | Truncated medical responses shown as complete | Add error parameter to `onDone` or separate `onError` callback |
| Model load failure returns error as HTTP 200 | `medgemma.py` service | Frontend displays error string as medical advice | Return HTTP 503 for model failures |
| No partial results on workflow failure | `MedicalWorkflowEngine.swift` | Step 3/5 fails = all patient data lost | Return partial results with warning instead of total failure |
| Empty catch block in health check | `BackendManager.swift` | User gets no diagnostic info | Log error details (moot after Layer 0, but fix for pre-migration) |

### High

| Issue | File | Problem | Fix |
|-------|------|---------|-----|
| Failed image analysis layers not recorded | `ImageAnalysisService.swift` | Medical image findings silently incomplete | Add `failedLayers` field to `ImageAnalysisResult` |
| Audit log save failure not propagated | `PersistenceHelpers.swift` | Compliance trail can silently break | Use `trySave()` in `MedicalAuditLogger`, handle failure explicitly |
| Unloadable images silently skipped | `MedicalWorkflowEngine.swift` | Attached images ignored without warning | Surface warning to user |
| Image analysis returns nil silently | `ChatStore.swift` | No indication analysis failed | Return error state, not nil |

---

## Layer 3: Code Cleanup

~40% of Swift code is vestigial from the multi-workspace Magnetar Studio design. Remove before building new features.

### Dead Code Removal (~900 lines)

| File | Why It's Dead |
|------|---------------|
| `NavigationStore.swift` | Single workspace, entire store unused |
| `WorkspacePanelType.swift` | Single `.medical` case |
| `WorkspaceHubStore.swift` | Unused, `WorkspaceHub` renders `MedicalPanel` directly |
| `WorkspaceSidebarView.swift` | Never instantiated |
| `WorkspaceAIContext.swift` | 5 of 6 cases unused (code, writing, sheets, voice, general) |
| `WorkspaceType.swift` | 3 of 4 cases unused |
| `ChatStore.swift` | Calls non-existent backend endpoints, orchestrator routing for single-model app |
| `WindowOpener.swift` | No-op view modifier, `windowOpenerConfigurator()` returns `self` |

### Unused Imports

| File | Import |
|------|--------|
| `MedStationApp.swift` | `import SwiftData` |
| `ContentView.swift` | `import AppKit` |

### Unused Backend Dependencies

Remove from `requirements.txt`: `duckdb`, `pandas`, `pyarrow`, `openpyxl`, `sqlparse`, `openai-whisper`, `ffmpeg-python`, `redis`, `boto3`, `zeroconf`, `websockets`, `libp2p`, `webauthn`, `PyJWT`, `slowapi`, `PyNaCl`, `keyring`, `pyobjc-framework-*`

(Most of this becomes moot when the Python backend is removed entirely in Layer 0.)

### Code Deduplication

- Duration calculation — duplicated 4x across `MedicalWorkflowEngine` and `MedicalBenchmarkHarness`
- Model status check — duplicated in `MedicalAIService` and `MedicalWorkflowEngine`
- Benchmark directory path — duplicated in `MedicalBenchmarkHarness`

---

## Layer 4: Patient Records System

Replace the flat case list with a proper patient → encounter hierarchy.

### 4.1 Schema

SQLite with WAL mode. Tables: `patients`, `encounters`, `vitals`, `medications`, `allergies`, `diagnoses`, `attachments`, `ai_sessions`. All encrypted at rest.

- **Patient profiles** — demographics, contact, insurance, primary care provider, permanent medical history, allergies, medications (persists across encounters)
- **Encounters** — each visit is an encounter under a patient. Chief complaint, vitals, symptoms, images, triage result, AI reasoning, export history. Chronological, timestamped.
- **Migration** — existing MedicalCase data auto-migrates into the new schema on first launch

### 4.2 Provider Profile

- Clinician identity: name, NPI, specialty, practice name
- Appears on exports, audit logs, printed documents
- Single provider for individual tier

---

## Layer 5: Clinical Intelligence

### 5.1 Per-Encounter AI Chat

Chat tied to a specific encounter, persisted with that encounter. Context injection: automatically include that encounter's vitals, symptoms, triage result, diagnoses. Safety guard runs on every response. Chat history exports with the encounter.

### 5.2 Patient-Level AI Chat

Scoped to the entire patient profile across all encounters. "Has this patient had cardiac symptoms before?" Pulls relevant encounter summaries into context using semantic similarity. Same safety guard, same model gate.

### 5.3 Semantic Search

On-device FAISS + embedding pipeline. Index patient records, encounter notes, AI chat history, diagnoses, medications. Search by natural language. Results ranked by relevance with encounter context previews. All indexing and search is local.

### 5.4 Clinical Templates

Pre-built prompt templates:
- SOAP note generation from encounter data
- Discharge summary drafting
- Referral letter generation
- Patient-friendly explanation of diagnosis
- Medication reconciliation review
- Templates are editable — clinicians customize to their practice style

---

## Layer 6: Documentation & Export

### 6.1 Voice Transcription

On-device via SFSpeechRecognizer (Apple Neural Engine). Dictate encounter notes hands-free. Auto-structure into SOAP format using MedGemma post-processing. Attach raw audio + transcript to encounter. Medical vocabulary boosting.

### 6.2 Enhanced Export

Extend existing FHIR R4 / Clinical JSON / Text Report system:
- **PDF reports** — professional clinical layout with headers, demographics, provider signature block, disclaimer
- **HL7 FHIR R4 Bundle** — verify compliance with US Core profiles
- **C-CDA** — standard EHR interoperability format, required for hospital integration
- **CSV bulk export** — quality metrics, research datasets, practice analytics
- **Print** — encounter summaries, prescriptions, lab orders
- Audit log entry for every export

### 6.3 Medical Imaging

Attach images to encounters (X-rays, dermatology photos, EKGs, wound photos). MedGemma 1.5 is multimodal — images feed into the agentic workflow. Encrypted at rest. DICOM viewer (stretch).

---

## Layer 7: App Store Submission

### 7.1 Code Signing & Distribution

- Apple Developer Program enrollment ($99/year)
- Distribution certificate and provisioning profile
- Hardened Runtime enabled
- Notarized by Apple
- Bundle ID: `com.medstation.app`

### 7.2 App Store Metadata

- Category: **Medical** (primary), **Health & Fitness** (secondary)
- Age Rating: 17+ (medical content)
- Privacy Policy URL
- Data Collection disclosure (Apple privacy nutrition labels)
- Screenshots: intake wizard, triage results, safety alerts, export

### 7.3 Medical App Compliance

- Disclaimer visible on first launch, in app description, in About section, before every analysis
- No diagnostic claims — "educational screening" or "triage assistance"
- Document what data stays on-device vs transmitted
- FDA: position as educational/informational to avoid 510(k). Never claim to diagnose or treat.

### 7.4 First-Launch Experience

1. Welcome screen explaining what MedStation does
2. Model download progress (show ETA)
3. Privacy notice + disclaimer acceptance
4. Quick tutorial / sample case walkthrough
5. Ready state

### 7.5 Testing

- Unit tests: triage extraction, diagnosis parsing, safety guard (all 9 categories), vital sign validation, drug interaction detection, persistence encrypt/decrypt round-trip
- UI tests: intake wizard flow, demo case loading, export, settings
- Performance: model load time, inference time per step, memory under sustained load
- App Review: launches without crash, works offline (after model download), handles low memory, handles interruptions, no hardcoded demo data visible

### 7.6 Accessibility

- VoiceOver support for all UI elements
- Dynamic Type support
- Sufficient color contrast (especially triage levels)
- Keyboard navigation

---

## Layer 8: Practice Management

### 8.1 Dashboard & Analytics

Patient panel overview, AI usage metrics, quality metrics, exportable reports.

### 8.2 Scheduling Awareness

Encounter date/time tracking with calendar view. Follow-up reminders. Not a full scheduling system — just enough context for what happened and what's pending.

### 8.3 Pricing

| Tier | Price | Includes |
|------|-------|----------|
| **Free** | $0 | 5 patients, 10 encounters/month, single provider, full AI + safety |
| **Individual** | $19/mo | Unlimited patients/encounters, voice transcription, full export, semantic search |
| **Team** | $39/provider/mo | Multi-provider, case handoffs, shared AI, sync, role-based access |

Field/humanitarian deployments: free.

---

## Layer 9: Team Tier

### 9.1 Multi-Provider Access

Shared patient database across 2+ clinicians on the same network. Role-based access: attending, resident, nurse, admin (read-only). Provider-scoped audit trail.

### 9.2 Case Handoffs

Assign encounter to another provider with notes. Handoff summary auto-generated by MedGemma. Notification system for pending handoffs.

### 9.3 Sync Architecture

Local-first: each Mac has a full copy. Sync via encrypted HTTPS to shared backend (self-hosted or MedStation cloud). Conflict resolution: last-write-wins for metadata, append-only for AI chat and audit logs. Offline-capable.

---

## Layer 10: Field Deployment

### 10.1 Offline-First Hardening

Full functionality with zero internet after initial model download. No telemetry, no analytics, no phone-home. Battery-optimized inference.

### 10.2 Low-Resource Mode

Quantized model (INT8/INT4) for 8GB Macs. Reduced safety guard (core checks only) for faster throughput in mass casualty. Simplified UI: intake → triage → next patient.

### 10.3 Bulk Intake

CSV/JSON import of patient lists. Batch triage with auto-save. Priority queue: emergencies surface to top.

---

## Model Strategy

MedStation is not a general-purpose AI app. It runs approved medical models only.

**Current:** MedGemma 1.5 4B (Google HAI-DEF, float32, Apple Silicon MPS)

**Future approved models (as released):**
- MedGemma larger variants (7B, 13B)
- Google CXR Foundation (chest X-ray)
- Google Derm Foundation (dermatology)
- Google Path Foundation (pathology)
- Google HeAR (health audio — stethoscope, lung sounds)

**Model approval process:**
1. Open-weight with medical use license
2. Runs on-device (no cloud inference)
3. Passes MedStation's benchmark harness (10+ vignettes, composite score threshold)
4. Safety guard rules updated for the model's capabilities
5. Version pinned — no auto-updates, clinician explicitly upgrades

**What MedStation will never do:**
- Run arbitrary models from Ollama/HuggingFace
- Send patient data to cloud APIs
- Allow model hot-swapping during an encounter
- Serve inference without the safety guard layer

---

## Non-Goals

- **Not an EHR** — no billing, no insurance claims, no e-prescribing, no lab ordering
- **Not a general AI platform** — one model, one purpose
- **Not a diagnostic tool** — assists clinicians, does not diagnose, every output carries a disclaimer
- **Not cloud-dependent** — cloud is for team sync only, individual tier is 100% offline after model download
