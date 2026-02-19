# MedStation — Mac App Store Submission Roadmap

## Post-Competition | Full App Store Release

---

## Current Status: Working App, Architecture Migrated

### What Works Now
- Full MedGemma 1.5 4B on-device inference via MLX Swift (4-bit quantized, ~3GB)
- 5-step agentic medical workflow with chain-of-thought reasoning + graceful degradation
- 9-category safety validation (emergency, drug interactions, bias, vitals, etc.)
- Patient check-in wizard (6-step guided flow with editable results)
- Follow-up chat with streaming responses (MLX native)
- On-device image analysis (Vision framework, no cloud) with failed layer tracking
- FHIR R4 / Clinical JSON / Text export
- SHA-256 audit logging (HAI-DEF compliant, save failures now propagated)
- 10-vignette benchmark harness
- Native macOS SwiftUI app targeting macOS 14+

### Completed (Feb 2026)
1. ~~**Python backend launched via `Process()`**~~ -- ELIMINATED (MLX Swift native inference)
2. ~~**Empty `MedStation.entitlements`**~~ -- Configured (sandbox disabled for dev, entitlements set)
3. ~~**Unused code bloat**~~ -- ~1,500 lines removed (dead workspace abstractions, backend integration)
4. ~~**Streaming errors calling onDone()**~~ -- FIXED (onError callback added)
5. ~~**Triage defaults to semi-urgent on parse failure**~~ -- FIXED (.undetermined case added)
6. ~~**Audit log swallows save failures**~~ -- FIXED (uses trySave() with fault-level logging)

### Remaining Blockers
1. **Patient data stored as unencrypted JSON** — privacy/HIPAA concern
2. **No code signing or notarization** — required for distribution
3. **App Sandbox disabled for dev** — needs re-enabling with model download into sandbox container
4. **Dead networking code** — ~19 files from pre-MLX architecture still compile but are unused

---

## PHASE 1: ARCHITECTURE (Must-Do — App Sandbox Compliance)

### 1.1 Eliminate the Python Backend (CRITICAL BLOCKER)

**Problem:** `BackendManager.swift` uses `Process()` to launch `uvicorn` with a Python venv. Apple's App Sandbox **strictly prohibits** launching child processes. This is the single biggest blocker.

**Current Architecture:**
```
SwiftUI App → HTTP → Python FastAPI → HuggingFace Transformers → MPS
```

**Required Architecture (choose one):**

#### Option A: Swift-Native ML Inference (Recommended)
```
SwiftUI App → Core ML / MLX Swift → Apple Silicon GPU
```
- Convert MedGemma to Core ML format using `coremltools`
- Or use [MLX Swift](https://github.com/ml-explore/mlx-swift) for native inference
- Eliminates Python entirely — pure Swift app
- Best App Store compatibility
- **Effort:** 2-4 weeks

#### Option B: Embedded Python via PythonKit
```
SwiftUI App → PythonKit → Embedded Python → Transformers → MPS
```
- Bundle a Python framework inside the app
- Use PythonKit for in-process Python calls
- No child process = sandbox-compliant
- **Effort:** 1-2 weeks
- **Risk:** App Review may still flag embedded interpreters

#### Option C: ONNX Runtime
```
SwiftUI App → ONNX Runtime (C++) → Core ML EP → Apple Silicon
```
- Export MedGemma to ONNX format
- Use `onnxruntime-swift` package
- No Python, no Core ML conversion limitations
- **Effort:** 1-2 weeks

**Recommendation:** Option A (Core ML / MLX Swift) is the cleanest path. Apple explicitly supports Core ML models in sandboxed apps. MLX Swift is Apple's own framework for on-device LLMs.

**Files to modify/replace:**
- `apps/native/macOS/Managers/BackendManager.swift` — Remove entirely
- `apps/native/Shared/Services/AI/MedicalAIService.swift` — Replace HTTP calls with native inference
- `apps/native/Shared/Networking/APIConfiguration.swift` — Remove backend URL config
- `apps/backend/` — Entire directory becomes unnecessary

### 1.2 Configure App Sandbox Entitlements (REQUIRED)

**File:** `apps/native/MedStation.entitlements` (currently empty)

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>com.apple.security.app-sandbox</key>
    <true/>

    <!-- File access for model weights and patient data -->
    <key>com.apple.security.files.user-selected.read-write</key>
    <true/>

    <!-- Application Support directory for case files -->
    <key>com.apple.security.files.downloads.read-write</key>
    <true/>

    <!-- Network for initial model download from HuggingFace -->
    <key>com.apple.security.network.client</key>
    <true/>

    <!-- Keychain for encryption keys and auth tokens -->
    <key>com.apple.security.keychain</key>
    <true/>

    <!-- Camera for future telemedicine features (optional) -->
    <!-- <key>com.apple.security.device.camera</key> -->
    <!-- <true/> -->
</dict>
</plist>
```

### 1.3 Model Distribution Strategy

**Problem:** MedGemma 4B weights are ~8GB. Apple has a 4GB app size limit on the App Store (with On Demand Resources up to 20GB total).

**Options:**

#### Option A: On-Demand Resources (ODR)
- Package model as tagged ODR assets
- Download on first launch
- Apple hosts the files on their CDN
- **Best for App Store** — Apple-sanctioned approach

#### Option B: In-App Download from HuggingFace
- App downloads weights on first launch
- Store in `~/Library/Application Support/MedStation/models/`
- Show download progress UI
- **Simpler** but requires network entitlement permanently

#### Option C: Core ML Model with Compression
- Convert to Core ML with 4-bit quantization
- Model size drops to ~2-3GB
- Can bundle directly in app
- Some accuracy trade-off

**Recommendation:** Option B for initial release (simplest), migrate to Option A for polish.

---

## PHASE 2: SECURITY & PRIVACY (Required for App Review)

### 2.1 Encrypt Patient Data at Rest (CRITICAL)

**Found by:** Code Review Agent (Issue #4, Confidence: 100%)

**Problem:** `PersistenceHelpers.save()` writes plain JSON to disk. Patient data (symptoms, diagnoses, medications, allergies) is stored unencrypted at:
```
~/Library/Application Support/MedStation/workspace/medical/*.json
```

**Files affected:**
- `apps/native/Shared/Utilities/PersistenceHelpers.swift:17-24`
- `apps/native/macOS/Workspaces/Hub/Panels/MedicalPanel.swift` (saveCaseToFile)
- `apps/native/Shared/Services/AI/MedicalAuditLogger.swift` (saveAuditEntry)

**Fix:** Add AES-GCM encryption using CryptoKit:
```swift
import CryptoKit

extension PersistenceHelpers {
    static func saveEncrypted<T: Encodable>(_ value: T, to url: URL, key: SymmetricKey, label: String) {
        do {
            let data = try JSONEncoder().encode(value)
            let sealed = try AES.GCM.seal(data, using: key)
            try sealed.combined!.write(to: url, options: [.atomic, .completeFileProtection])
        } catch {
            logger.error("Failed to save encrypted \(label): \(error)")
        }
    }
}
```
- Store encryption key in Keychain via `KeychainService`
- Use `.completeFileProtection` for Data Protection API

### 2.2 Fix Backend Binding Address

**File:** `apps/native/macOS/Managers/BackendManager.swift:88`

Change `0.0.0.0` to `127.0.0.1`:
```swift
// BEFORE (exposes to entire network)
task.arguments = ["-m", "uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]

// AFTER (localhost only)
task.arguments = ["-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000"]
```

> Note: This file will be removed entirely when Phase 1.1 is complete, but fix it now for the competition build.

### 2.3 Restrict CORS Origins

**File:** `apps/backend/api/app_factory.py:66-72`

```python
# BEFORE
allow_origins=["*"],
allow_credentials=True,

# AFTER
allow_origins=["http://127.0.0.1:8000", "http://localhost:8000"],
allow_credentials=False,
allow_methods=["GET", "POST"],
allow_headers=["Content-Type"],
```

### 2.4 Add Input Validation to Backend

**Found by:** Code Review Agent (Issue #1, Confidence: 95%)

**File:** `apps/backend/api/routes/chat/medgemma.py`

Add validation for:
- Prompt length (max 10,000 chars)
- `max_tokens` range (1-2048)
- `temperature` range (0.0-2.0)
- Base64 image size (max 10MB decoded)

### 2.5 Validate Image File Paths

**Found by:** Code Review Agent (Issue #7, Confidence: 85%)

**File:** `apps/native/Shared/Services/AI/MedicalWorkflowEngine.swift:292-299`

Validate that `attachedImagePaths` are within allowed directories (temp, Application Support) and don't contain path traversal patterns.

### 2.6 Privacy Policy & Data Handling

**Required for App Store medical apps:**
- Privacy Policy URL in App Store Connect
- Data Collection disclosure (Apple privacy nutrition labels)
- In-app privacy notice explaining on-device processing
- HIPAA disclaimer (not a covered entity, educational use)

---

## PHASE 3: SILENT FAILURE REMEDIATION (Patient Safety)

**Found by:** Silent Failure Hunter Agent — 17 issues, 6 CRITICAL

### 3.1 Fix Model Error Appearing as Normal Response (CRITICAL-05)

**File:** `apps/backend/api/services/medgemma.py:120-123`

Model load failures return error strings as HTTP 200 responses. The Swift frontend displays them as AI medical advice.

**Fix:** Return proper HTTP 503 status codes for model failures.

### 3.2 Fix Streaming Errors Calling onDone() (CRITICAL-06)

**File:** `apps/native/Shared/Services/AI/MedicalAIService.swift:237-247`

When streaming fails, `onDone()` is called, signaling completion. Users see truncated medical responses as if complete.

**Fix:** Add error parameter to `onDone` callback, or use separate `onError` callback.

### 3.3 Fix Triage Default to Semi-Urgent on Parse Failure (HIGH-02)

**File:** `apps/native/Shared/Services/AI/MedicalWorkflowEngine.swift:322-347`

If MedGemma's triage output can't be parsed, it silently defaults to "Semi-Urgent" with no warning. An actual emergency could be mis-triaged.

**Fix:** Log warning, add "parse_failed" flag, and surface uncertainty to the user.

### 3.4 Fix Backend Health Check Empty Catch Block (CRITICAL-04)

**File:** `apps/native/macOS/Managers/BackendManager.swift:200-213`

Health check swallows ALL errors silently. User gets no diagnostic info.

**Fix:** Log error details at debug level for diagnostics.

### 3.5 Fix Image Analysis Failures Not Recorded (HIGH-01)

**File:** `apps/native/Shared/Services/ImageAnalysis/ImageAnalysisService.swift:200-328`

Failed analysis layers are not recorded in results. Medical image findings could be silently incomplete.

**Fix:** Add `failedLayers` field to `ImageAnalysisResult`.

### 3.6 Fix Audit Log Save Not Propagating Failure (HIGH-05)

**File:** `apps/native/Shared/Utilities/PersistenceHelpers.swift:17-24`

Audit logger uses `save()` (which swallows errors) instead of `trySave()`. HAI-DEF compliance trail can silently break.

**Fix:** Use `trySave()` in `MedicalAuditLogger` and handle failure explicitly.

---

## PHASE 4: CODE CLEANUP (App Review & Maintainability)

**Found by:** Code Simplifier Agent — 18 issues across 6 categories

### 4.1 Remove Dead Workspace Abstractions (HIGH PRIORITY)

The app was originally a multi-workspace platform. For the medical-only App Store app, remove:

| File | Issue |
|------|-------|
| `NavigationStore.swift` | Single workspace, entire store is dead code |
| `WorkspacePanelType.swift` | Single `.medical` case |
| `WorkspaceHubStore.swift` | Unused, `WorkspaceHub` renders `MedicalPanel` directly |
| `WorkspaceSidebarView.swift` | Never instantiated |
| `WorkspaceAIContext.swift` | 5 of 6 cases unused (code, writing, sheets, voice, general) |
| `WorkspaceType.swift` | 3 of 4 cases unused |

**Impact:** Removes ~500 lines of dead code, simplifies App Review.

### 4.2 Remove ChatStore Backend Integration (HIGH PRIORITY)

**File:** `apps/native/Shared/Stores/ChatStore.swift`

The ChatStore has elaborate session management calling backend endpoints (`/v1/chat/sessions/`) that **don't exist** in the Python backend. This code:
- Calls non-existent endpoints, producing silent connection errors
- Has orchestrator routing for a single-model app
- Contains `determineModelForQuery()` (45 lines) that always returns the same model

**Impact:** ~400 lines of dead code generating silent errors.

### 4.3 Remove Unused Dependencies

**File:** `apps/backend/requirements.txt`

Remove packages not used by the MedGemma workflow:
- `duckdb`, `pandas`, `pyarrow`, `openpyxl`, `sqlparse`
- `openai-whisper`, `ffmpeg-python`
- `redis`, `boto3`
- `zeroconf`, `websockets`, `libp2p`
- `webauthn`, `PyJWT`, `slowapi`, `PyNaCl`, `keyring`
- `pyobjc-framework-*`

### 4.4 Remove Unused Imports

| File | Unused Import |
|------|---------------|
| `MedStationApp.swift:9` | `import SwiftData` |
| `ContentView.swift:11` | `import AppKit` |
| `medgemma.py (routes):11` | `from fastapi import Request` |

### 4.5 Remove No-Op View Modifier

**File:** `apps/native/macOS/Windows/WindowOpener.swift:32-37`

`windowOpenerConfigurator()` returns `self` — does nothing. Remove.

### 4.6 Extract Duplicated Code

- **Duration calculation** — duplicated 4x across `MedicalWorkflowEngine` and `MedicalBenchmarkHarness`. Extract `Duration.milliseconds` extension.
- **Message building** — duplicated in `medgemma.py` `generate()` and `stream_generate()`. Extract `_build_messages()`.
- **Model status check** — duplicated in `MedicalAIService` and `MedicalWorkflowEngine`. Extract helper.
- **Benchmark directory path** — duplicated. Extract `benchmarkDirectory` static property.

---

## PHASE 5: APP STORE PREPARATION

### 5.1 Code Signing & Notarization

- Enroll in Apple Developer Program ($99/year)
- Create Distribution certificate and provisioning profile
- Configure Xcode signing: Team, Bundle ID (`com.medstation.app`), Provisioning Profile
- Enable Hardened Runtime
- Notarize for distribution outside App Store (Developer ID)

### 5.2 App Store Connect Setup

- Create App Store Connect record
- Bundle ID: `com.medstation.app`
- Primary Category: **Medical**
- Secondary Category: **Health & Fitness**
- Age Rating: 17+ (medical content)
- Price: Free / Freemium
- Availability: All territories or US-only initially

### 5.3 App Store Metadata

- **App Name:** MedStation
- **Subtitle:** Privacy-First Medical Triage AI
- **Keywords:** medical, triage, AI, MedGemma, on-device, privacy, diagnosis
- **Description:** Emphasize on-device processing, privacy, educational use
- **Screenshots:** 3-5 showing wizard, results, benchmark, export
- **App Preview (Video):** 30-second demo showing workflow

### 5.4 Medical App Compliance

Apple has special requirements for medical apps:

1. **Disclaimer:** "This app is for educational and informational purposes only. It is not intended to be a substitute for professional medical advice, diagnosis, or treatment." Must be:
   - Visible on first launch
   - In the app description
   - In the About section
   - Before every analysis

2. **No diagnostic claims:** Never say "diagnoses" — say "educational screening" or "triage assistance"

3. **Data handling:** Document what data stays on-device vs what's transmitted

4. **FDA considerations:** If positioned as a Clinical Decision Support tool, may require FDA 510(k) clearance. To avoid this:
   - Market as educational/informational only
   - Never claim to diagnose or treat
   - Include prominent disclaimers
   - Target general public, not clinicians specifically

### 5.5 App Icon & Branding

- Ensure 1024x1024 App Store icon
- Match iOS Human Interface Guidelines
- Medical cross + AI motif (already in `Assets.xcassets`)

### 5.6 Accessibility

Required for App Store best practices:
- VoiceOver support for all UI elements
- Dynamic Type support
- Sufficient color contrast (especially for triage levels)
- Keyboard navigation

---

## PHASE 6: TESTING (Required Before Submission)

### 6.1 Unit Tests (Critical Path)

**Current state:** `Tests/` directory exists but is empty.

**Minimum test coverage for App Store:**
- Triage level extraction (`extractTriageLevel`) — test all 5 levels + edge cases
- Diagnosis parsing (`parseDifferentialDiagnoses`) — test numbered/bulleted/empty
- Safety guard logic — test each of 9 categories
- Vital sign validation — test age-banded ranges
- Drug interaction detection — test all 12+ pairs
- Persistence helpers — test save/load/encrypt round-trip

### 6.2 UI Tests

- Patient check-in wizard flow (all 6 steps)
- Demo case loading
- Export functionality
- Settings persistence

### 6.3 Performance Tests

- Model load time (cold start)
- Inference time per step
- Memory usage under sustained load
- Thermal throttling behavior

### 6.4 App Store Review Test Cases

Apple reviewers will test:
- [ ] App launches without crash
- [ ] All features work without internet (after model download)
- [ ] App handles low memory gracefully
- [ ] App handles interruptions (phone call, sleep/wake)
- [ ] Privacy claims match actual behavior
- [ ] No hardcoded test data visible to users (remove DEMO-001 case)

---

## PHASE 7: POLISH & UX

### 7.1 First-Launch Experience

1. Welcome screen explaining what MedStation does
2. Model download progress (8GB, show ETA)
3. Privacy notice + disclaimer acceptance
4. Quick tutorial / sample case walkthrough
5. Ready state

### 7.2 Remove Demo Data

**File:** `apps/native/macOS/Workspaces/Hub/Panels/MedicalPanel.swift:288-314`

The hardcoded DEMO-001 case (58M chest pain) loads when no cases exist. For App Store:
- Replace with a "Try a sample case" button instead of auto-loading
- Don't show pre-filled patient data by default

### 7.3 Error States & Empty States

- No model downloaded → download prompt
- Model loading → progress indicator with ETA
- Inference failed → retry button with error details
- No cases → empty state with "Start New Case" CTA

### 7.4 macOS Integration

- Menu bar commands (already have `MedStationMenuCommands`)
- Keyboard shortcuts for common actions
- Touch Bar support (if targeting older Macs)
- Dock badge for active analysis

---

## Race Condition & Reliability Fixes

### Fix Model Loading Race Condition

**Found by:** Code Review Agent (Issue #5, Confidence: 85%)

**File:** `apps/backend/api/services/medgemma.py:38-46`

The busy-wait loop for concurrent model loading has no timeout and can hang forever if loading crashes.

**Fix:** Add asyncio.Lock and timeout:
```python
async def load(self, model_dir=None) -> bool:
    if self.loaded:
        return True
    async with self._load_lock:
        if self.loaded:
            return True
        # ... load with timeout
```

### Add Retry Logic for Inference

**Found by:** Code Review Agent (Issue #9, Confidence: 82%)

**File:** `apps/native/Shared/Services/AI/MedicalAIService.swift:104-151`

Add 3-attempt retry with exponential backoff for workflow steps. Medical workflows should not fail on a single transient error.

### Implement Graceful Workflow Degradation

**Found by:** Code Review Agent (Issue #6, Confidence: 90%)

If step 3 of 5 fails, return partial results with a warning instead of losing all work. Users entered 10+ minutes of patient data.

---

## Complete Issue Inventory (All 5 Agents)

### From Code Review Agent (12 issues)
| # | Severity | Issue | File |
|---|----------|-------|------|
| 1 | CRITICAL | No input sanitization on backend | `routes/chat/medgemma.py` |
| 2 | CRITICAL | CORS allows all origins + credentials | `app_factory.py` |
| 3 | CRITICAL | No auth on medical endpoints | `routes/chat/__init__.py` |
| 4 | CRITICAL | Patient data unencrypted on disk | `PersistenceHelpers.swift` |
| 5 | CRITICAL | Race condition in model loading | `services/medgemma.py` |
| 6 | CRITICAL | No partial results on workflow failure | `MedicalWorkflowEngine.swift` |
| 7 | IMPORTANT | Unvalidated file path injection | `MedicalWorkflowEngine.swift` |
| 8 | IMPORTANT | MainActor blocking during streaming | `MedicalAIService.swift` |
| 9 | IMPORTANT | No retry logic for inference | `MedicalAIService.swift` |
| 10 | IMPORTANT | SQL injection risk in audit hash | `MedicalAuditLogger.swift` |
| 11 | IMPORTANT | Unbounded approved domains set | `SecurityManager.swift` |
| 12 | IMPORTANT | No timeout for model loading | `services/medgemma.py` |

### From Silent Failure Hunter (17 issues)
| # | Severity | Issue | File |
|---|----------|-------|------|
| C-01 | CRITICAL | Streaming errors cause silent truncation | `services/medgemma.py` |
| C-02 | CRITICAL | Ollama returns empty 200 when down | `ollama_proxy.py` |
| C-03 | CRITICAL | Zero error handling on Ollama generate | `ollama_proxy.py` |
| C-04 | CRITICAL | Empty catch block in health check | `BackendManager.swift` |
| C-05 | CRITICAL | Model load failure returns error as 200 | `services/medgemma.py` |
| C-06 | CRITICAL | onDone() called on stream error | `MedicalAIService.swift` |
| H-01 | HIGH | Failed image layers not recorded | `ImageAnalysisService.swift` |
| H-02 | HIGH | Triage defaults to semi-urgent silently | `MedicalWorkflowEngine.swift` |
| H-03 | HIGH | Image analysis returns nil silently | `ChatStore.swift` |
| H-04 | HIGH | Unloadable images silently skipped | `MedicalWorkflowEngine.swift` |
| H-05 | HIGH | Audit log save failure not propagated | `PersistenceHelpers.swift` |
| H-06 | HIGH | Image hash fallback defeats caching | `ImageAnalysisService.swift` |
| M-01 | MEDIUM | os._exit(0) bypasses cleanup | `app_factory.py` |
| M-02 | MEDIUM | Device ID falls back to memory-only | `AuthService.swift` |
| M-03 | MEDIUM | Model preferences silently default | `ChatStore.swift` |
| M-04 | MEDIUM | Streaming JSON parse errors skipped | `APIClient.swift` |
| M-05 | MEDIUM | HotSlotManager URL guard returns silently | `HotSlotManager.swift` |

### From Code Simplifier (18 issues)
| # | Category | Issue | Files |
|---|----------|-------|-------|
| 1a | Dead Code | Single-case workspace enums | NavigationStore, WorkspacePanelType, WorkspaceType |
| 1b | Dead Code | Unused authenticated router | `routes/chat/__init__.py` |
| 1c | Dead Code | WorkspaceSidebarView never used | `WorkspaceSidebarView.swift` |
| 1d | Dead Code | WorkspaceHubStore unused | `WorkspaceHubStore.swift` |
| 1e | Dead Code | Non-medical AI context cases | `WorkspaceAIContext.swift` |
| 1f | Dead Code | Unused `import SwiftData` | `MedStationApp.swift` |
| 1g | Dead Code | Unused `import AppKit` | `ContentView.swift` |
| 2a | Duplication | Duration calc repeated 4x | `MedicalWorkflowEngine.swift` |
| 2b | Duplication | Message building duplicated | `services/medgemma.py` |
| 2c | Duplication | Model status check duplicated | `MedicalAIService.swift` |
| 2d | Duplication | Benchmark dir path duplicated | `MedicalBenchmarkHarness.swift` |
| 3a | Complexity | ChatStore orchestrator routing unused | `ChatStore.swift` |
| 3b | Complexity | Session backend integration for non-existent endpoints | `ChatStore.swift` |
| 4a | Verbosity | Repetitive MainActor.run wrappers | `APISettingsView.swift` |
| 4b | Verbosity | Verbose Ollama auto-start | `AppLifecycleManager.swift` |
| 5a | Imports | Unused `Request` import | `routes/chat/medgemma.py` |
| 5b | Imports | Python typing imports modernizable | `app_factory.py` |
| 6b | Structure | No-op view modifier | `WindowOpener.swift` |

---

## Timeline (Post-Competition)

| Week | Phase | Tasks |
|------|-------|-------|
| 1-2 | Phase 1 | Evaluate Core ML / MLX Swift for MedGemma. Proof of concept. |
| 3-4 | Phase 1 | Complete native inference migration. Remove Python backend. |
| 5 | Phase 2 | Implement data encryption. Configure entitlements. Fix security issues. |
| 6 | Phase 3 | Fix all CRITICAL silent failures. Fix HIGH priority issues. |
| 7 | Phase 4 | Remove dead code. Clean up imports. Extract duplicated code. |
| 8 | Phase 5 | Apple Developer enrollment. Code signing. App Store Connect setup. |
| 9-10 | Phase 6 | Write unit tests. UI tests. Performance tests. |
| 11 | Phase 7 | Polish UX. First-launch flow. Error states. Remove demo data. |
| 12 | Submit | App Store Review submission. |

---

## App Store Review Checklist

### Technical Requirements
- [ ] App Sandbox enabled with minimal entitlements
- [ ] No child process launching (`Process()`)
- [ ] Hardened Runtime enabled
- [ ] Code signed with Distribution certificate
- [ ] Notarized by Apple
- [ ] No private API usage
- [ ] No embedded interpreters (Python removed)
- [ ] All data encrypted at rest
- [ ] Network traffic is HTTPS only (except localhost)
- [ ] Minimum macOS 14.0 deployment target

### Content & Legal
- [ ] Medical disclaimer prominent and persistent
- [ ] Privacy Policy URL in App Store Connect
- [ ] No diagnostic claims in marketing
- [ ] Age rating: 17+
- [ ] CC BY 4.0 license compatible with App Store
- [ ] HAI-DEF model terms compliance documented
- [ ] EULA / Terms of Use

### User Experience
- [ ] First-launch onboarding flow
- [ ] Model download progress UI
- [ ] VoiceOver accessibility
- [ ] Keyboard navigation
- [ ] Empty states for all views
- [ ] Error states with recovery actions
- [ ] No hardcoded demo data

### Quality
- [ ] Unit test coverage > 60% on critical paths
- [ ] No memory leaks (Instruments profiling)
- [ ] No crashes in 24h stress test
- [ ] Performance: < 30s per workflow step
- [ ] Storage: < 100MB app (excluding model)

---

*Generated by deep codebase analysis across 5 specialized agents — February 13, 2026*
*Analysis covered: 90+ Swift files, 4 Python modules, all configuration files*
*Agents: Codebase Explorer, Architecture Analyzer, Code Reviewer, Silent Failure Hunter, Code Simplifier*
