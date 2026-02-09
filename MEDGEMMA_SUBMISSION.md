# MedGemma Impact Challenge — MagnetarStudio Medical Triage Assistant

> **On-device, privacy-first medical triage using MedGemma 4B with a 5-step agentic workflow, HAI-DEF safety validation, and automated clinical benchmarking.**

**Team:** MagnetarStudio
**Model:** `alibayram/medgemma:4b` (4B parameters, GGUF quantized)
**Platform:** macOS native (SwiftUI), 100% on-device inference via Ollama
**Codebase:** 7 files, 5,046 lines of Swift
**License:** Proprietary (competition submission)

---

## Table of Contents

1. [Problem Domain](#1-problem-domain)
2. [Solution Architecture](#2-solution-architecture)
3. [Execution & Features](#3-execution--features)
4. [HAI-DEF Compliance](#4-hai-def-compliance)
5. [Feasibility & Deployment](#5-feasibility--deployment)
6. [Impact & Clinical Utility](#6-impact--clinical-utility)
7. [Evaluation Benchmark](#7-evaluation-benchmark)
8. [Setup & Running](#8-setup--running)
9. [File Structure](#9-file-structure)
10. [Technical Details](#10-technical-details)

---

## 1. Problem Domain

### The Problem

Emergency department overcrowding is a global crisis. In the US alone, over 130 million ED visits occur annually, with average wait times exceeding 2 hours. Delayed triage leads to adverse outcomes — patients with time-critical conditions like STEMI or stroke may not receive care within clinically meaningful windows.

### Our Approach

MagnetarStudio's Medical Triage Assistant addresses this through **on-device AI pre-triage** — a privacy-preserving system that:

- Accepts structured patient intake (demographics, symptoms, vitals, history, medications, allergies, medical images)
- Runs a **5-step agentic reasoning workflow** powered by MedGemma 4B
- Produces triage classification, differential diagnoses, risk stratification, and actionable recommendations
- Validates all outputs through **9 safety guardrail categories** before presentation
- Logs every decision with **HAI-DEF compliant audit trails**

### Clinical Scenarios Supported

| Acuity Level | Example Conditions | Expected Response |
|---|---|---|
| Emergency | STEMI, Stroke, Anaphylaxis, DKA, Preeclampsia | Immediate 911 escalation with action buttons |
| Urgent | Pneumonia, Appendicitis, Asthma exacerbation | Seek care within 2-4 hours |
| Semi-Urgent | Moderate infections, musculoskeletal injuries | See doctor within 24 hours |
| Non-Urgent | Chronic condition follow-ups | Schedule appointment |
| Self-Care | URI, Tension headache, minor ailments | Monitor at home with guidance |

### Population Coverage

- **Age-banded vital sign ranges:** Neonate (<1), Toddler (1-5), Child (6-11), Adolescent (12-17), Adult (18-64), Geriatric (65+) — each with clinically calibrated HR/BP thresholds
- **Pregnancy-specific screening:** Preeclampsia, eclampsia, ectopic pregnancy, placental abruption
- **Demographic bias detection:** Sex-condition mismatch alerts, clinical bias awareness (e.g., chest pain under-triage in women)

---

## 2. Solution Architecture

### Agentic Workflow (5-Step Pipeline)

```
Patient Intake
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  Step 1: Symptom Analysis                               │
│  Identifies primary symptoms, red flags, progression    │
├─────────────────────────────────────────────────────────┤
│  Step 2: Triage Assessment                              │
│  5-level classification with clinical justification     │
├─────────────────────────────────────────────────────────┤
│  Step 3: Differential Diagnosis                         │
│  Top 3-5 conditions with probability + rationale        │
├─────────────────────────────────────────────────────────┤
│  Step 4: Risk Stratification                            │
│  Patient-specific risk factors and complications        │
├─────────────────────────────────────────────────────────┤
│  Step 5: Recommended Actions                            │
│  Prioritized interventions and self-care instructions   │
└─────────────────────────────────────────────────────────┘
     │
     ▼
┌─────────────────────────────────────────────────────────┐
│  Post-Processing: HAI-DEF Safety Validation             │
│  9 safety guard categories × output validation          │
│  Clinical guideline attachment (9 evidence databases)   │
│  Audit logging with SHA-256 privacy hashing             │
└─────────────────────────────────────────────────────────┘
     │
     ▼
  Results + Safety Alerts + Guidelines + Audit Trail
```

### Pre-Step: Medical Image Analysis

When medical images are attached (X-rays, lab results, skin photos), a **5-layer on-device Vision pipeline** runs before the workflow:

1. OCR text extraction
2. Object detection
3. Scene classification
4. Segmentation analysis
5. Description generation

Image analysis results are injected into the patient context so MedGemma reasons over both structured data and visual findings.

### Context Threading

Each workflow step receives cumulative context from prior steps:
- Step 2 sees Step 1's symptom analysis
- Step 3 sees triage level + symptom analysis
- Step 4 sees differential diagnoses
- Step 5 sees triage + risk factors

This chain-of-thought approach mirrors clinical reasoning — each step builds on prior conclusions.

---

## 3. Execution & Features

### Core Medical Features

| Feature | Description |
|---|---|
| **5-Step Agentic Workflow** | Symptom Analysis → Triage → Differential Dx → Risk Stratification → Recommendations |
| **Streaming Follow-Up Chat** | Interactive Q&A with MedGemma after initial triage, with cancel support |
| **Medical Image Analysis** | On-device Vision pipeline for X-rays, lab results, skin photos |
| **Patient Demographics** | Age, sex, pregnancy status — feeds into age-banded vital ranges and bias detection |
| **Vital Sign Validation** | Real-time form validation with physiologic range checking and Celsius auto-detection |
| **Blood Pressure Validation** | Systolic/diastolic format check, range validation, diastolic < systolic enforcement |
| **Temperature Auto-Conversion** | Values ≤50 auto-detected as Celsius and converted to Fahrenheit |

### Safety & Compliance Features

| Feature | Description |
|---|---|
| **9-Category Safety Guard** | Emergency escalation, red flags, critical vitals, medication interactions, confidence calibration, demographic bias, pregnancy risks, input robustness, guideline references |
| **12 Drug Interaction Categories** | SSRIs+MAOIs, warfarin+CYP, QT prolongation, PDE5+nitrates, lithium toxicity, and 7 more |
| **Age-Banded Vital Ranges** | 6 age tiers with clinically accurate HR/BP thresholds |
| **Clinical Guideline References** | 9 evidence-based guideline databases (AHA/ACC, GINA, ATS/IDSA, ADA, etc.) |
| **Demographic Bias Detection** | Sex-condition mismatch, age-condition mismatch, clinical bias awareness |
| **Pregnancy Screening** | Preeclampsia, eclampsia, ectopic pregnancy, placental abruption |
| **Input Robustness** | Contradictory vitals detection, excessive symptom count, brief complaint warnings |

### UX & Integration Features

| Feature | Description |
|---|---|
| **Case Management** | Create, archive, delete cases with persistent storage |
| **Search** | Filter cases by patient ID, complaint, or symptoms |
| **Demo Case** | Pre-loaded STEMI vignette on first launch with onboarding |
| **User Feedback** | Accurate / Partially Helpful / Incorrect ratings with notes (HAI-DEF feedback loop) |
| **Chat Persistence** | Follow-up messages saved to case file, survive app restart |
| **Retry on Failure** | Retry button when workflow fails, with Ollama setup guide |
| **Model Card** | In-app HAI-DEF model card (intended use, limitations, bias considerations, privacy) |
| **Impact Analytics** | Sidebar showing cases analyzed, emergency detections, avg triage time, feedback accuracy |

### Export & Interoperability

| Format | Description |
|---|---|
| **Text Report** | Human-readable clinical summary with all workflow steps |
| **Clinical JSON** | Structured export: intake + result + safety alerts + feedback + audit entry |
| **FHIR R4 Bundle** | Standards-compliant Transaction Bundle with Patient, Condition, Observation (LOINC-coded vital signs: HR 8867-4, Temp 8310-5, RR 9279-1, SpO2 2708-6, BP 85354-9), and RiskAssessment resources |

### Evaluation

| Feature | Description |
|---|---|
| **Benchmark Harness** | 10 clinically validated vignettes across 6 specialties |
| **3-Dimensional Scoring** | Triage accuracy (40%), diagnosis recall (35%), safety coverage (25%) |
| **Confusion Matrix** | 5×5 triage level confusion matrix for systematic bias detection |
| **Benchmark Export** | Full benchmark report as structured JSON |

---

## 4. HAI-DEF Compliance

### Safety Validation Pipeline

Every workflow output passes through `MedicalSafetyGuard.validate()` — a rule-based post-processing layer that runs **9 independent safety checks**:

1. **Emergency Escalation** — Detects life-threatening conditions (stroke, MI, anaphylaxis, sepsis, PE, meningitis, aortic dissection, tension pneumothorax, status epilepticus) and escalates even when MedGemma under-triages
2. **Red Flag Symptoms** — 12 pattern-matched red flags (thunderclap headache, hemoptysis, acute weakness, etc.)
3. **Critical Vitals** — Age-banded thresholds for HR, temperature, SpO2, RR with 6 age tiers
4. **Medication Interactions** — 12 drug-drug interaction categories with severity-appropriate alerts
5. **Confidence Calibration** — Warns on flat probability distributions and single-diagnosis anchoring
6. **Demographic Bias** — Sex-condition mismatch, age-condition mismatch, clinical bias awareness
7. **Pregnancy Risks** — Preeclampsia, eclampsia, ectopic pregnancy, placental abruption screening
8. **Input Robustness** — Contradictory vitals, excessive symptoms, vague complaints
9. **Guideline References** — Attaches citations from 9 evidence-based clinical guidelines

### Audit Logging

`MedicalAuditLogger` creates a full audit trail for every workflow execution:

- **Privacy-preserving:** Patient data hashed with SHA-256 (only first 8 bytes stored)
- **Model traceability:** Model ID, version, parameter count recorded
- **Workflow trace:** Per-step input/output hashes, character counts, duration
- **Safety record:** Alert count, category breakdown, severity summary
- **Consent tracking:** Disclaimer presentation and confirmation state (not hardcoded)
- **Performance metrics:** Total workflow time, per-step timing, thermal state, image analysis timing

### Consent & Disclaimer

- Medical disclaimer presented **before** every workflow execution (modal confirmation)
- Disclaimer confirmation state propagated through `MedicalWorkflowEngine.executeWorkflow(disclaimerConfirmed:)` → `MedicalAuditLogger.logWorkflowExecution(disclaimerConfirmed:)` → `AuditEntry`
- Standard disclaimer text always displayed alongside results

### Model Card (In-App)

The results view includes an expandable model card section covering:
- Model identification (MedGemma 4B, on-device via Ollama)
- Intended use (educational triage support, not clinical diagnosis)
- Known limitations (English only, no lab/imaging interpretation, prompt-sensitivity)
- Bias considerations (training data representation, clinical bias patterns)
- Safety framework (9-category guard, HAI-DEF audit)
- Privacy architecture (100% on-device, no network transmission)

### User Feedback Loop

After each analysis, users can rate triage accuracy (Accurate / Partially Helpful / Incorrect) with optional notes. Feedback is:
- Persisted with the case file
- Included in clinical JSON exports
- Aggregated in impact analytics (sidebar accuracy percentage)
- Available for model improvement analysis

---

## 5. Feasibility & Deployment

### On-Device Architecture

```
┌─────────────────────────────────────────┐
│  MagnetarStudio (macOS native app)      │
│                                         │
│  SwiftUI UI Layer                       │
│    ↕                                    │
│  MedicalWorkflowEngine (orchestrator)   │
│    ↕                                    │
│  MedicalAIService (model management)    │
│    ↕                                    │
│  Ollama Runtime (local inference)       │
│    ↕                                    │
│  MedGemma 4B GGUF (quantized weights)  │
│                                         │
│  ── No network required after setup ──  │
└─────────────────────────────────────────┘
```

**Zero patient data leaves the device.** All inference, safety validation, audit logging, and storage happen locally in `~/Library/Application Support/MagnetarStudio/workspace/medical/`.

### Hardware Requirements

| Component | Requirement |
|---|---|
| **OS** | macOS 14.0+ |
| **RAM** | 8 GB minimum (16 GB recommended) |
| **Storage** | ~3 GB for MedGemma 4B weights |
| **Processor** | Apple Silicon (M1+) recommended, Intel supported |
| **GPU** | Not required (CPU inference via Ollama) |

### Model Auto-Management

- On first use, MedGemma 4B auto-downloads via Ollama with progress tracking
- If Ollama is not running, an in-app setup guide with numbered steps and download link is displayed
- Model status tracked: Not Installed → Downloading (with %) → Ready

### Performance Characteristics

| Metric | Typical Value |
|---|---|
| **Full 5-step workflow** | 30-60 seconds |
| **Per-step inference** | 6-12 seconds |
| **Image analysis (5-layer)** | 2-5 seconds per image |
| **Safety validation** | <50ms (rule-based, no inference) |
| **Thermal impact** | Monitored per-workflow, recorded in audit |

### Export Interoperability

FHIR R4 Bundle export enables integration with existing healthcare IT systems:
- **Patient** resource with demographics
- **Condition** resources with differential diagnoses and probability extensions
- **Observation** resources with LOINC-coded vital signs
- **RiskAssessment** resource with triage level mapping

---

## 6. Impact & Clinical Utility

### Target Use Cases

1. **Rural/Remote Triage Support** — Where specialist access is limited, on-device AI provides structured clinical reasoning without requiring internet connectivity
2. **Emergency Department Pre-Triage** — Structured intake + AI pre-assessment reduces time-to-triage for walk-in patients
3. **Medical Education** — Students can practice clinical reasoning with AI-generated differential diagnoses and see how safety guardrails catch common errors
4. **Telehealth Enhancement** — Structured triage data (including FHIR R4 exports) can be shared with remote clinicians
5. **Clinical Decision Support** — Not replacing physicians, but providing a structured second opinion with evidence-based guideline references

### Privacy-First Healthcare AI

By running entirely on-device:
- **HIPAA alignment** — No PHI transmitted over networks
- **Patient trust** — Users can see that no data leaves their Mac
- **Deployment simplicity** — No cloud infrastructure, API keys, or data processing agreements
- **Regulatory clarity** — On-device processing avoids many cross-border data transfer concerns

### Impact Metrics (In-App Analytics)

The sidebar displays real-time impact analytics:
- Total cases analyzed
- Emergency conditions detected (potential lives impacted)
- Average triage time (demonstrating AI efficiency)
- User feedback accuracy rate (quality metric)

---

## 7. Evaluation Benchmark

### Methodology

The built-in benchmark harness (`MedicalBenchmarkHarness`) runs **10 clinically validated vignettes** through the complete 5-step workflow and scores against expected outcomes.

### Vignette Coverage

| # | Vignette | Category | Expected Triage | Key Challenge |
|---|---|---|---|---|
| 1 | Acute STEMI | Cardiology | Emergency | Classic cardiac emergency presentation |
| 2 | Acute Ischemic Stroke | Neurology | Emergency | Time-critical neurological emergency |
| 3 | Anaphylaxis | Allergy | Emergency | Rapid-onset systemic allergic reaction |
| 4 | Community-Acquired Pneumonia | Pulmonology | Urgent | Infectious disease with respiratory compromise |
| 5 | Acute Appendicitis | Surgery | Urgent | Pediatric surgical emergency |
| 6 | Diabetic Ketoacidosis | Endocrinology | Emergency | Metabolic emergency with altered consciousness |
| 7 | Upper Respiratory Infection | General | Self-Care | Mild condition — should NOT be over-triaged |
| 8 | Tension Headache | Neurology | Self-Care | Benign condition — tests specificity |
| 9 | Pediatric Asthma Exacerbation | Pediatrics | Urgent | Age-specific vital ranges + respiratory |
| 10 | Preeclampsia with Severe Features | Obstetrics | Emergency | Pregnancy-specific emergency |

### Scoring Dimensions

| Dimension | Weight | Methodology |
|---|---|---|
| **Triage Accuracy** | 40% | Exact match = 1.0, adjacent level = 0.5, else = 0.0 |
| **Diagnosis Recall** | 35% | Keyword overlap: matched expected keywords / total expected |
| **Safety Coverage** | 25% | Expected safety categories triggered / total expected |

**Composite Score** = (Triage × 0.40) + (Diagnosis × 0.35) + (Safety × 0.25)

A vignette **passes** at composite score ≥ 0.50.

### Confusion Matrix

The benchmark produces a 5×5 triage confusion matrix showing:
- Diagonal entries = correct classifications (green)
- Off-diagonal = misclassifications (red)
- Enables systematic bias detection (e.g., consistent over-triage or under-triage)

### Running the Benchmark

1. Open MagnetarStudio → Workspace → Medical panel
2. Click **Benchmark** (toolbar, chart icon)
3. Click **Run Benchmark** — takes ~5-10 minutes for all 10 vignettes
4. View results: composite score, per-vignette drill-down, confusion matrix
5. Export as JSON for reproducible analysis

---

## 8. Setup & Running

### Prerequisites

1. **macOS 14.0+** with Xcode 15+
2. **Ollama** installed and running:
   ```bash
   # Install Ollama
   brew install ollama

   # Start Ollama server
   ollama serve

   # (Optional) Pre-pull MedGemma — the app will auto-download if needed
   ollama pull alibayram/medgemma:4b
   ```

### Build & Run

```bash
git clone https://github.com/magnetarai-founder/magnetar-studio.git
cd magnetar-studio

# Build
xcodebuild -project apps/native/MagnetarStudio.xcodeproj \
  -scheme MagnetarStudio \
  -destination 'platform=macOS' \
  build

# Or open in Xcode
open apps/native/MagnetarStudio.xcodeproj
# ⌘R to build and run
```

### First Launch

1. Navigate to **Workspace** tab (⌘1) → **Medical** panel in sidebar
2. Onboarding alert explains the system capabilities
3. A **demo case** (58M with acute STEMI presentation) is pre-loaded
4. Click **"I Understand — Run Analysis"** to execute the 5-step workflow
5. View results: triage level, differential diagnoses, recommended actions, safety alerts
6. Try the **follow-up chat** to ask MedGemma clarifying questions
7. Run the **benchmark** to see evaluation results

### Storage Locations

| Data | Path |
|---|---|
| Cases | `~/Library/Application Support/MagnetarStudio/workspace/medical/*.json` |
| Audit Logs | `~/Library/Application Support/MagnetarStudio/workspace/medical/audit/*.json` |
| Benchmarks | `~/Library/Application Support/MagnetarStudio/workspace/medical/benchmarks/*.json` |

---

## 9. File Structure

```
apps/native/
├── Shared/
│   ├── Models/
│   │   └── MedicalModels.swift              # 323 lines — Data models
│   │       ├── PatientIntake                 #   Demographics, symptoms, vitals, history
│   │       ├── MedicalWorkflowResult         #   Triage, diagnoses, actions, reasoning
│   │       ├── MedicalCase                   #   Persistence unit with feedback + chat
│   │       ├── TriageFeedback                #   HAI-DEF user feedback loop
│   │       ├── FollowUpMessage               #   Persistent chat messages
│   │       └── PerformanceMetrics            #   Edge AI timing + thermal state
│   │
│   └── Services/AI/
│       ├── MedicalAIService.swift            # 318 lines — Model lifecycle
│       │   ├── Model auto-download via Ollama
│       │   ├── Non-streaming inference (workflow steps)
│       │   ├── Streaming inference (follow-up chat)
│       │   └── Cancellation support
│       │
│       ├── MedicalWorkflowEngine.swift       # 473 lines — Agentic orchestrator
│       │   ├── 5-step pipeline with context threading
│       │   ├── Medical image pre-analysis
│       │   ├── Output parsing (triage, diagnoses, actions)
│       │   └── HAI-DEF post-processing integration
│       │
│       ├── MedicalSafetyGuard.swift          # 691 lines — Safety validation
│       │   ├── 9 safety check categories
│       │   ├── 12 drug interaction databases
│       │   ├── Age-banded vital ranges (6 tiers)
│       │   ├── Clinical guideline references (9 databases)
│       │   └── SafetyAlert model with severity + category
│       │
│       ├── MedicalAuditLogger.swift          # 192 lines — HAI-DEF audit
│       │   ├── Privacy-preserving SHA-256 hashing
│       │   ├── Workflow trace with per-step records
│       │   └── Consent + performance + safety logging
│       │
│       └── MedicalBenchmarkHarness.swift     # 590 lines — Evaluation
│           ├── 10 clinical vignettes (6 specialties)
│           ├── 3-dimensional scoring engine
│           ├── Confusion matrix generation
│           └── Report persistence + export
│
└── macOS/Workspaces/Hub/Panels/
    └── MedicalPanel.swift                    # 2,459 lines — UI
        ├── Case management (CRUD + search + archive)
        ├── Patient intake form with vital validation
        ├── Workflow progress + results display
        ├── Safety alerts with action buttons
        ├── Model card disclosure group
        ├── Follow-up chat with streaming
        ├── User feedback collection
        ├── Export (Text + JSON + FHIR R4)
        ├── Impact analytics sidebar
        ├── Benchmark runner + results viewer
        └── Onboarding + demo case
```

**Total: 7 files, 5,046 lines of Swift**

---

## 10. Technical Details

### Model Configuration

| Parameter | Value |
|---|---|
| **Model** | `alibayram/medgemma:4b` |
| **Parameters** | 4 billion |
| **Format** | GGUF (quantized for edge deployment) |
| **Temperature** | 0.3 (low — prioritizes deterministic medical reasoning) |
| **Context Window** | 8,192 tokens |
| **Inference** | Ollama runtime, CPU/Metal acceleration |

### Edge AI Metrics

Every workflow records:
- **ContinuousClock** timing per step (nanosecond precision)
- **Thermal state** via `ProcessInfo.processInfo.thermalState` (nominal/fair/serious/critical)
- **Image analysis timing** when medical images are attached
- **Total workflow duration** including all 5 steps + safety validation

### Safety Alert Severity Levels

| Severity | Color | Action |
|---|---|---|
| **Critical** | Red | Requires immediate attention; may include "Call 911" or "Seek Emergency Care" action buttons |
| **Warning** | Orange | Important clinical consideration; may include "Consult Pharmacist" action |
| **Info** | Blue | Educational context; guideline references, bias awareness |

### Dependencies

- **Zero external Swift packages** — the entire medical system uses only Apple frameworks (Foundation, SwiftUI, CryptoKit, os)
- **Ollama** — local model runtime (not bundled, user-installed)
- **No cloud APIs, no API keys, no network calls during inference**

---

## Medical Disclaimer

This application is for **educational and informational purposes only**. It is **NOT** a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of a qualified healthcare provider with any questions about a medical condition. Never disregard professional medical advice or delay seeking it because of information from this system. If you think you may have a medical emergency, call 911 or your local emergency services immediately.

---

*Built with MedGemma for the Kaggle MedGemma Impact Challenge 2026.*
