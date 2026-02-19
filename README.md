# MedStation

**Privacy-first medical triage assistant powered by [MedGemma 1.5 4B](https://huggingface.co/google/medgemma-1.5-4b-it).**

MedStation runs a 5-step agentic reasoning workflow entirely on your Mac using Apple Silicon -- no cloud, no API keys, no patient data ever leaves the device. Built for the [Kaggle MedGemma Impact Challenge](https://www.kaggle.com/competitions/med-gemma-impact-challenge).

---

## What It Does

1. **Patient Intake** -- Structured form: demographics, symptoms, vitals, medications, allergies, medical images
2. **5-Step Agentic Workflow** -- Symptom Analysis, Triage Assessment, Differential Diagnosis, Risk Stratification, Recommended Actions
3. **Safety Validation** -- 9-category post-processing guard catches errors the model might miss (emergency escalation, drug interactions, critical vitals, demographic bias, pregnancy risks, and more)
4. **Graceful Degradation** -- If a mid-pipeline step fails, completed steps are preserved and surfaced with a warning instead of losing all work
5. **Follow-Up Chat** -- Interactive Q&A with MedGemma after triage
6. **Export** -- FHIR R4 Bundle, Clinical JSON, or Text Report

All inference runs locally via [MLX Swift](https://github.com/ml-explore/mlx-swift-lm) on Apple Silicon (~3 GB 4-bit quantized model).

---

## Requirements

| Component | Requirement |
|---|---|
| Mac | Apple Silicon (M1/M2/M3/M4) -- **required** |
| OS | macOS 14.0+ (Sonoma) |
| RAM | 16 GB recommended (model uses ~3-4 GB during inference) |
| Storage | ~3 GB for model weights + ~200 MB for app |
| Xcode | 15.0+ |
| HuggingFace | Account with [MedGemma access](https://huggingface.co/google/medgemma-1.5-4b-it) approved |

No Python required. No backend. Pure Swift.

---

## Setup

### 1. Clone the Repository

```bash
git clone https://github.com/magnetarai-founder/MedStation-MedGemma_Impact.git
cd MedStation-MedGemma_Impact
```

### 2. Download the Model

Log into HuggingFace (you must have accepted the [HAI-DEF terms](https://huggingface.co/google/medgemma-1.5-4b-it)):

```bash
pip install huggingface_hub
huggingface-cli login
python3 -c "from huggingface_hub import snapshot_download; snapshot_download('mlx-community/medgemma-4b-it-4bit')"
```

This downloads the 4-bit quantized MLX model (~3 GB) to your HuggingFace cache. The app auto-detects it on launch.

### 3. Build and Run

```bash
open apps/native/MedStation.xcodeproj
# Build and run (Cmd+R)
```

Or from the command line:

```bash
xcodebuild -project apps/native/MedStation.xcodeproj \
  -scheme MedStation \
  -destination 'platform=macOS' \
  build
```

Model loads into memory on launch (~7s on M3, ~15s on M1).

---

## First Launch

1. MedStation opens directly into the **Medical Panel**
2. A **demo case** (58M with acute STEMI) is pre-loaded
3. Click **"I Understand -- Run Analysis"** to execute the 5-step agentic workflow
4. Watch MedGemma reason through each step with chain-of-thought
5. View results: triage level, differential diagnoses, safety alerts, recommended actions
6. Try the **follow-up chat** to ask clarifying questions
7. Export results as FHIR R4 Bundle, Clinical JSON, or Text Report
8. Run the **benchmark** (toolbar chart icon) to evaluate across 10 clinical vignettes

---

## Architecture

```
SwiftUI App --> MLX Swift --> Apple Silicon GPU (Metal)
```

No HTTP calls. No Python. No child processes. App Sandbox compatible.

### Key Components

```
apps/native/
  Shared/
    Services/AI/
      MLXInferenceEngine.swift      # On-device MLX inference (generate + stream)
      MedicalWorkflowEngine.swift   # 5-step agentic orchestrator
      MedicalAIService.swift        # Model lifecycle + API surface
      MedicalSafetyGuard.swift      # 9-category safety validation
      MedicalAuditLogger.swift      # SHA-256 audit trail (HAI-DEF)
      MedicalBenchmarkHarness.swift # 10-vignette evaluation harness
    Services/ImageAnalysis/
      ImageAnalysisService.swift    # 5-layer ML pipeline (Vision, Objects, Segmentation, Depth, Structured)
    Models/
      MedicalModels.swift           # Patient, case, triage data models
  macOS/
    Workspaces/Hub/Panels/
      MedicalPanel.swift            # Main UI (intake, results, chat, export)
      PatientCheckInFlow.swift      # 6-step patient intake wizard

spaces/
  app.py                            # HuggingFace Spaces Gradio demo
```

---

## Benchmark

MedStation includes a built-in benchmark harness with **10 clinically validated vignettes** across 8 specialties:

| # | Vignette | Specialty |
|---|----------|-----------|
| 1 | Acute STEMI | Cardiology |
| 2 | Acute Ischemic Stroke | Neurology |
| 3 | Anaphylaxis | Allergy |
| 4 | Community-Acquired Pneumonia | Pulmonology |
| 5 | Acute Appendicitis | Surgery |
| 6 | Diabetic Ketoacidosis | Endocrinology |
| 7 | Upper Respiratory Infection | General |
| 8 | Tension Headache | Neurology |
| 9 | Pediatric Asthma Exacerbation | Pediatrics |
| 10 | Preeclampsia with Severe Features | Obstetrics |

**Scoring (composite):**
- Triage accuracy: **40%** (exact match = 1.0, adjacent level = 0.5)
- Diagnosis recall: **35%** (keyword overlap with expected diagnoses)
- Safety coverage: **25%** (expected safety categories triggered)

To run: Open MedStation > Toolbar chart icon > **Run Benchmark**

Results include per-vignette scores, triage confusion matrix, and JSON export.

---

## Safety Guard (9 Categories)

Every workflow result passes through `MedicalSafetyGuard` which checks:

1. **Emergency escalation** -- Detects acute keywords missed by triage
2. **Drug interactions** -- Flags known dangerous medication pairs
3. **Critical vital signs** -- Age-banded vital sign validation
4. **Red flag symptoms** -- Pattern-matches high-risk presentations
5. **Demographic bias** -- Checks for known clinical biases (e.g. chest pain in women)
6. **Pregnancy risks** -- Flags pregnancy-specific complications
7. **Allergy warnings** -- Cross-references allergies with recommended treatments
8. **Medication contraindications** -- Checks age and condition-specific contraindications
9. **Patient safety summary** -- Aggregates all findings into actionable alerts

---

## Storage

| Data | Location |
|---|---|
| Model weights | `~/.cache/huggingface/hub/models--mlx-community--medgemma-4b-it-4bit/` |
| Patient cases | `~/Library/Application Support/MedStation/workspace/medical/*.json` |
| Audit logs | `~/Library/Application Support/MedStation/workspace/medical/audit/*.json` |
| Benchmarks | `~/Library/Application Support/MedStation/workspace/medical/benchmarks/*.json` |

---

## License

CC BY 4.0 -- See [LICENSE](./LICENSE) for details.

MedGemma model weights are subject to [Google HAI-DEF Terms of Use](https://developers.google.com/health-ai-developer-foundations/terms).

---

## Medical Disclaimer

This application is for **educational and informational purposes only**. It is NOT a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of a qualified healthcare provider. If you think you may have a medical emergency, call 911 immediately.
