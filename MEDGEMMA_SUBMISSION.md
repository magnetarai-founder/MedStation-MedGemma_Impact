# MedGemma Impact Challenge -- MedStation

### Project name
**MedStation** -- On-Device Medical Triage Assistant

### Team
MedStation (Solo developer)

### Track
Main Track + Agentic Workflow Prize

### Model
`alibayram/medgemma:4b` (4B parameters, GGUF quantized, Ollama runtime)

### License
CC BY 4.0

---

## Problem Statement

Emergency department overcrowding is a global crisis: 130M+ annual ED visits in the US alone, with average wait times exceeding 2 hours. Delayed triage leads to adverse outcomes -- patients with time-critical conditions (STEMI, stroke, sepsis) may not receive care within clinically meaningful windows.

Existing AI triage tools require cloud connectivity, raising HIPAA concerns and failing in bandwidth-constrained settings (rural clinics, disaster response, field medicine). **No patient data should ever need to leave the device to receive AI-assisted triage.**

## Overall Solution

MedStation is a **privacy-first, on-device medical triage assistant** that runs MedGemma 4B entirely locally via Ollama. It implements a **5-step agentic reasoning workflow** that mirrors clinical decision-making:

1. **Symptom Analysis** -- Identifies primary symptoms, red flags, and temporal progression
2. **Triage Assessment** -- 5-level classification (Emergency/Urgent/Semi-Urgent/Non-Urgent/Self-Care) with clinical justification
3. **Differential Diagnosis** -- Top 3-5 conditions with probability estimates and rationale
4. **Risk Stratification** -- Patient-specific risk factors, comorbidity interactions, complication likelihood
5. **Recommended Actions** -- Prioritized interventions, self-care instructions, escalation triggers

Each step receives cumulative context from prior steps, forming a chain-of-thought that builds progressively -- the same reasoning pattern clinicians use.

**Zero patient data leaves the device.** All inference, safety validation, audit logging, and case storage happen locally.

### Architecture

```
macOS Native App (SwiftUI)
    |
MedicalPanel (2,459 lines) -- Patient intake, results, chat, export
    |
MedicalWorkflowEngine (473 lines) -- 5-step agentic orchestrator
    |
MedicalSafetyGuard (691 lines) -- 9 post-processing safety checks
    |
MedicalAIService (318 lines) -- Ollama client, model lifecycle
    |
Ollama Runtime (localhost:11434)
    |
MedGemma 4B GGUF (on-device, ~3GB)
```

A Python FastAPI backend provides additional API routes for model management, chat streaming, and health monitoring.

## Technical Details

### Agentic Workflow Design

The `MedicalWorkflowEngine` orchestrates 5 sequential LLM calls with **context threading** -- each step's prompt includes the output of all prior steps. This is critical because:

- Step 2 (Triage) needs symptom analysis to classify correctly
- Step 3 (Differential Dx) needs triage level to calibrate severity
- Step 5 (Recommendations) needs the full clinical picture

When medical images are attached (X-rays, lab results, skin photos), a **5-layer Vision pipeline** runs before the workflow: OCR extraction, object detection, scene classification, segmentation analysis, and description generation. Results are injected into patient context so MedGemma reasons over both structured data and visual findings.

### Safety Guard (9 Categories)

Every workflow output passes through `MedicalSafetyGuard.validate()` -- a rule-based post-processing layer that catches errors MedGemma might miss:

| Category | What It Catches |
|---|---|
| **Emergency Escalation** | Life-threatening conditions (stroke, MI, anaphylaxis, sepsis) -- escalates even when the model under-triages |
| **Red Flag Symptoms** | 12 pattern-matched flags (thunderclap headache, hemoptysis, acute weakness) |
| **Critical Vitals** | Age-banded thresholds for HR, BP, temp, SpO2, RR across 6 age tiers (neonate to geriatric) |
| **Medication Interactions** | 12 drug-drug interaction categories (SSRIs+MAOIs, warfarin+CYP, QT prolongation, etc.) |
| **Confidence Calibration** | Warns on flat probability distributions and single-diagnosis anchoring |
| **Demographic Bias** | Sex-condition mismatch, age-condition mismatch, clinical bias awareness |
| **Pregnancy Risks** | Preeclampsia, eclampsia, ectopic pregnancy, placental abruption screening |
| **Input Robustness** | Contradictory vitals, excessive symptoms, vague complaints |
| **Guideline References** | Attaches citations from 9 evidence-based clinical guideline databases (AHA/ACC, GINA, ATS/IDSA, ADA, etc.) |

### HAI-DEF Compliance

- **Audit logging** with SHA-256 privacy hashing (only first 8 bytes of patient data stored)
- **Model traceability** -- model ID, version, parameter count recorded per workflow
- **Workflow trace** -- per-step input/output hashes, character counts, duration
- **Consent tracking** -- medical disclaimer presented before every workflow execution; confirmation state propagated through the full pipeline
- **User feedback loop** -- Accurate / Partially Helpful / Incorrect ratings with notes, persisted with case data
- **In-app model card** -- intended use, limitations, bias considerations, privacy architecture

### Benchmark Evaluation

A built-in benchmark harness runs **10 clinically validated vignettes** across 6 specialties:

| # | Vignette | Expected Triage | Specialty |
|---|---|---|---|
| 1 | Acute STEMI | Emergency | Cardiology |
| 2 | Acute Ischemic Stroke | Emergency | Neurology |
| 3 | Anaphylaxis | Emergency | Allergy |
| 4 | Community-Acquired Pneumonia | Urgent | Pulmonology |
| 5 | Acute Appendicitis | Urgent | Surgery |
| 6 | Diabetic Ketoacidosis | Emergency | Endocrinology |
| 7 | Upper Respiratory Infection | Self-Care | General |
| 8 | Tension Headache | Self-Care | Neurology |
| 9 | Pediatric Asthma Exacerbation | Urgent | Pediatrics |
| 10 | Preeclampsia with Severe Features | Emergency | Obstetrics |

**Scoring:** Triage accuracy (40%) + Diagnosis recall (35%) + Safety coverage (25%). A 5x5 confusion matrix detects systematic over/under-triage bias.

### Export & Interoperability

- **FHIR R4 Bundle** -- Transaction Bundle with Patient, Condition, Observation (LOINC-coded: HR 8867-4, Temp 8310-5, RR 9279-1, SpO2 2708-6, BP 85354-9), and RiskAssessment resources
- **Clinical JSON** -- Structured export with intake, results, safety alerts, feedback, and audit entry
- **Text Report** -- Human-readable clinical summary

### Key Metrics

| Metric | Value |
|---|---|
| Full 5-step workflow | 30-60 seconds |
| Per-step inference | 6-12 seconds |
| Safety validation | <50ms (rule-based) |
| Image analysis | 2-5 seconds/image |
| External dependencies | Zero (Apple frameworks only) |
| Swift codebase | 7 core files, ~5,000 lines |

## Impact

### Target Use Cases

1. **Rural/Remote Triage** -- On-device AI provides structured clinical reasoning without internet connectivity
2. **ED Pre-Triage** -- Structured intake + AI pre-assessment reduces time-to-triage for walk-in patients
3. **Medical Education** -- Students practice clinical reasoning with AI-generated differentials while safety guardrails demonstrate common errors
4. **Telehealth Enhancement** -- FHIR R4 exports integrate with existing healthcare IT systems

### Why On-Device Matters

- **HIPAA alignment** -- No PHI transmitted over networks
- **Patient trust** -- Verifiable that no data leaves the Mac
- **Deployment simplicity** -- No cloud infrastructure, API keys, or data processing agreements
- **Regulatory clarity** -- Avoids cross-border data transfer concerns

---

## Medical Disclaimer

This application is for **educational and informational purposes only**. It is **NOT** a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of a qualified healthcare provider. If you think you may have a medical emergency, call 911 immediately.

---

*Built with MedGemma for the Kaggle MedGemma Impact Challenge 2026.*
