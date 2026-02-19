# MedStation — Product Roadmap

Mac-first. On-device only. One approved model at a time. Gated for patient safety.

---

## Phase 0: Kaggle Submission (Now — Feb 24, 2026)

**Goal:** Ship the competition entry.

- [ ] Record 3-min demo video
- [ ] Write 3-page Kaggle writeup (provided template)
- [x] Build HuggingFace Spaces demo (Gradio + MedGemma on T4)
- [ ] Create Kaggle Writeup submission, attach all links
- [ ] Track: Main Track + Edge AI Prize
- [x] Push final code to public repo
- [x] Eliminate Python backend (MLX Swift native inference)
- [x] Fix critical silent failures (streaming errors, triage parse, audit trail)
- [x] Remove dead code (~1,500 lines of vestigial workspace/backend code)
- [x] Add graceful workflow degradation (partial results on step failure)
- [x] Update README for MLX-native architecture

Everything after this is post-competition.

---

## Phase 1: Clinical Foundation (Mar — Apr 2026)

**Goal:** Transform MedStation from a triage demo into a real clinical data system.

### 1.1 Patient Records System

Replace the flat case list with a proper patient → encounter hierarchy.

- **Patient profiles** — demographics, contact, insurance, primary care provider, permanent medical history, allergies, medications (the stuff that persists across encounters)
- **Encounters** — each visit/case is an encounter under a patient. Chief complaint, vitals, symptoms, images, triage result, AI reasoning, follow-up chat, export history. Chronological, timestamped
- **Schema** — SQLite with WAL mode (port from Magnetar Studio's DatabaseStore pattern). Tables: `patients`, `encounters`, `vitals`, `medications`, `allergies`, `diagnoses`, `attachments`, `ai_sessions`
- **Migration** — existing MedicalCase data auto-migrates into the new schema on first launch

### 1.2 Encryption at Rest

Port Magnetar Studio's vault encryption layer. Every database file encrypted with Fernet (AES-128-CBC). Keys stored in macOS Keychain via Secure Enclave. Unlock with Touch ID or password.

- Port: `KeychainManager.swift`, `BiometricAuthService.swift`, vault encryption from `encryption.py`
- No PHI is ever written to disk unencrypted

### 1.3 HIPAA Audit Trail

Extend the existing MedicalAuditLogger with full access logging.

- Every read, write, export, AI query, and login recorded
- Fields: timestamp, user_id, patient_id, encounter_id, action, resource, outcome
- Append-only SQLite table with SHA-256 chain (tamper detection)
- 7-year retention policy enforced at the storage layer
- Port and extend: `audit_logger.py` patterns

### 1.4 Model Safety Gate

MedStation runs one model at a time, and only approved medical models.

- Hardcoded allowlist: `google/medgemma-1.5-4b-it` (expand as Google releases new versions)
- No arbitrary model loading — this is a medical device, not a playground
- Model integrity check on load (SHA-256 hash verification against known-good weights)
- Version pinning with explicit upgrade path (clinician must acknowledge model version change)
- Fallback behavior: if model fails to load, MedStation shows a clear "AI Unavailable" state — never serves stale or wrong-model output

---

## Phase 2: Clinical Intelligence (May — Jun 2026)

**Goal:** Make MedStation smart about the data it holds.

### 2.1 Per-Record AI Chat

Already exists — enhance it.

- Chat tied to a specific encounter, persisted with that encounter
- Context injection: automatically include that encounter's vitals, symptoms, triage result, diagnoses in the chat context window
- Safety guard runs on every AI response (already implemented, keep it)
- Chat history exports with the encounter

### 2.2 Patient-Level AI Chat

New. A second AI chat scoped to the entire patient profile.

- "Has this patient had cardiac symptoms before?" — searches across all encounters
- Context window: hierarchical memory system (port from Magnetar Studio's Jarvis/ElohimOS memory)
- Pulls relevant encounter summaries into context using semantic similarity
- Same safety guard layer, same model gate
- Separate chat history stored at the patient level

### 2.3 Semantic Search

Port Magnetar Studio's FAISS + embedding pipeline.

- Index: patient records, encounter notes, AI chat history, diagnoses, medications
- Search by natural language: "patients on metformin with elevated A1C", "chest pain cases triaged as emergency"
- On-device embeddings (Apple Neural Engine via the native HashEmbedder, or a small medical embedding model)
- Results ranked by relevance with encounter context previews
- No PHI leaves the device — all indexing and search is local

### 2.4 Clinical Templates

Pre-built prompt templates for common clinical tasks.

- SOAP note generation from encounter data
- Discharge summary drafting
- Referral letter generation
- Patient-friendly explanation of diagnosis (lower reading level)
- Medication reconciliation review
- Templates are editable — clinicians can customize to their practice style

---

## Phase 3: Documentation & Export (Jul — Aug 2026)

**Goal:** MedStation produces real clinical documents.

### 3.1 Voice Transcription

Port Magnetar Studio's TranscriptionService (SFSpeechRecognizer, Apple Neural Engine).

- Dictate encounter notes hands-free during patient interaction
- On-device transcription — PHI never hits a cloud API
- Auto-structure into SOAP format (Subjective, Objective, Assessment, Plan) using MedGemma post-processing
- Attach raw audio + transcript to the encounter record
- Medical vocabulary boosting (drug names, anatomy, procedures)

### 3.2 Enhanced Export

Extend the existing FHIR R4 / Clinical JSON / Text Report system.

- **PDF reports** — port NSPrintOperation from Magnetar Studio's ExportService. Professional clinical layout with headers, patient demographics, provider signature block, medical disclaimer
- **HL7 FHIR R4 Bundle** — already implemented, verify compliance with US Core profiles
- **C-CDA (Consolidated CDA)** — standard EHR interoperability format. Required for any serious hospital integration
- **CSV bulk export** — for quality metrics, research datasets, practice analytics
- **Print** — encounter summaries, prescriptions, lab orders
- Audit log entry for every export (who, what, when, format)

### 3.3 Medical Imaging Attachments

- Attach images to encounters (X-rays, dermatology photos, EKGs, wound photos)
- MedGemma 1.5 is multimodal — images feed into the agentic workflow
- Encrypted at rest alongside all other PHI
- DICOM viewer (stretch goal — basic display, not full radiology workstation)
- Port file management from Magnetar Studio's vault system

---

## Phase 4: Practice Management (Sep — Oct 2026)

**Goal:** MedStation runs a solo practice.

### 4.1 Dashboard & Analytics

- Patient panel overview: total patients, encounters this week/month, triage distribution
- AI usage metrics: queries per day, average response time, safety alert frequency
- Quality metrics: triage accuracy (from feedback), common diagnoses, follow-up rates
- Exportable reports for practice management and quality improvement

### 4.2 Scheduling Awareness

- Encounter date/time tracking with calendar view
- Follow-up reminders (flagged encounters that need revisiting)
- No full scheduling system — that's EHR territory. Just enough context to know when things happened and what's pending

### 4.3 Provider Profile

- Clinician identity: name, NPI, specialty, practice name
- Appears on exports, audit logs, printed documents
- Supports multiple providers on the same machine (individual tier = one provider, switch via profile selector)

### 4.4 Mac App Store Submission

- Sandbox compliance
- App Review guidelines for medical apps (disclaimers, intended use statements)
- No model weights bundled — download on first launch via HuggingFace
- Pricing: free tier (limited encounters/month) + paid individual license

---

## Phase 5: Team Tier (Nov 2026 — Jan 2027)

**Goal:** MedStation works for a care team.

### 5.1 Multi-Provider Access

- Shared patient database across 2+ clinicians on the same network
- Role-based access: attending, resident, nurse, admin (read-only)
- Provider-scoped audit trail (who did what to which patient)
- Authentication: provider login with biometric or password per session

### 5.2 Case Handoffs

- Assign encounter to another provider with notes
- Handoff summary auto-generated by MedGemma from encounter data
- Notification system (in-app) for pending handoffs
- Status tracking: pending, accepted, completed

### 5.3 Shared AI Context

- Team-level AI chat: "What have we seen in the last month that matches this presentation?"
- Aggregated semantic search across all providers' encounters
- Privacy controls: providers can mark encounters as restricted (visible only to them + admin)

### 5.4 Sync Architecture

- Local-first: each Mac has a full copy of the database
- Sync via encrypted HTTPS to a shared backend (self-hosted or MedStation cloud)
- Conflict resolution: last-write-wins for metadata, append-only for AI chat and audit logs
- Offline-capable: full functionality without network, syncs when reconnected
- Port patterns from Magnetar Studio's cloud relay, but HTTPS-only (no P2P — hospital networks won't allow it)

---

## Phase 6: Field Deployment (Feb — Apr 2027)

**Goal:** MedStation runs where there's no infrastructure.

### 6.1 Offline-First Hardening

- Full functionality with zero internet after initial model download
- Model weights cached locally, verified on launch
- No telemetry, no analytics, no phone-home
- Battery-optimized inference (throttle GPU usage on low power)

### 6.2 Low-Resource Mode

- Quantized model option (INT8 or INT4) for MacBooks with 8GB RAM
- Reduced safety guard (core checks only) for faster throughput in mass casualty scenarios
- Simplified UI mode: intake → triage → next patient (skip detailed diagnosis in surge)

### 6.3 Bulk Intake

- CSV/JSON import of patient lists (disaster registries, refugee camp rosters)
- Batch triage: run multiple cases sequentially with auto-save
- Priority queue: emergency cases surface to the top automatically

### 6.4 Data Export for Continuity

- Export entire patient database as encrypted archive
- Import on another MedStation instance (transfer between field teams)
- FHIR R4 bulk export for handoff to hospital EHR systems

---

## Phase 7: Magnetar Studio Integration (May — Jun 2027)

**Goal:** The upgrade path works.

### 7.1 Import Wizard

- One-click migration from MedStation → Magnetar Studio's MedStation module
- Transfers: all patients, encounters, AI chat histories, audit logs, attachments, provider profiles
- Preserves encryption — re-encrypts under Magnetar Studio's vault
- Verified migration with diff report (nothing lost)

### 7.2 MedStation Module in Magnetar Studio

- Full MedStation functionality inside the Magnetar Studio workspace
- Gains: notes, word processing, spreadsheets, code, terminal, general AI chat, voice, collaboration
- MedStation data stays in its own encrypted partition (not mixed with general workspace)
- Model gate still enforced — medical AI queries only go to approved medical models

### 7.3 Cross-Module Context

- Magnetar Studio's AI can reference MedStation data when the provider explicitly allows it
- Example: writing a research paper in the word processor, pulling patient statistics from MedStation's semantic search
- Always gated: clinician must approve each cross-module data access
- Audit logged at both the MedStation and Magnetar Studio level

---

## Model Strategy

MedStation is not a general-purpose AI app. It runs approved medical models only.

**Current:** MedGemma 1.5 4B (Google HAI-DEF, fp16, Apple Silicon MPS)

**Future approved models (as released):**
- MedGemma larger variants (7B, 13B when available)
- Google CXR Foundation (chest X-ray, if on-device feasible)
- Google Derm Foundation (dermatology)
- Google Path Foundation (pathology)
- Google HeAR (health audio — stethoscope, lung sounds)

**Model approval process:**
1. Model must be open-weight with a medical use license
2. Model must run on-device (no cloud inference)
3. Model must pass MedStation's benchmark harness (10+ vignettes, composite score threshold)
4. Safety guard rules must be updated for the model's capabilities
5. Version pinned — no auto-updates. Clinician explicitly upgrades

**What MedStation will never do:**
- Run arbitrary models from Ollama/HuggingFace
- Send patient data to cloud APIs
- Allow model hot-swapping during an encounter
- Serve inference without the safety guard layer

---

## Pricing (Tentative)

| Tier | Price | What You Get |
|------|-------|--------------|
| **Free** | $0 | 5 patients, 10 encounters/month, single provider, full AI + safety |
| **Individual** | $19/mo | Unlimited patients/encounters, voice transcription, full export suite, semantic search |
| **Team** | $39/provider/mo | Everything in Individual + multi-provider, case handoffs, shared AI, sync, role-based access |
| **Magnetar Studio upgrade** | Studio pricing | Full productivity suite + MedStation module, import wizard |

Field/humanitarian deployments: free via Magnetar Mission.

---

## Non-Goals (What MedStation Is Not)

- **Not an EHR** — no billing, no insurance claims, no e-prescribing, no lab ordering. MedStation is AI-powered clinical reasoning and documentation. It complements an EHR, doesn't replace one.
- **Not a general AI platform** — one model, one purpose. If you want general AI, use Magnetar Studio.
- **Not a diagnostic tool** — MedStation assists clinicians. It does not diagnose. Every output carries a disclaimer. The safety guard enforces this.
- **Not cloud-dependent** — cloud is for team sync only. Individual tier is 100% offline-capable after model download.
