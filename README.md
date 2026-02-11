# MedStation

**Privacy-first medical triage assistant powered by [MedGemma 1.5 4B](https://huggingface.co/google/medgemma-1.5-4b-it).**

MedStation runs a 5-step agentic reasoning workflow entirely on your Mac using Apple Silicon -- no cloud, no API keys, no patient data ever leaves the device. Built for the [Kaggle MedGemma Impact Challenge](https://www.kaggle.com/competitions/med-gemma-impact-challenge).

---

## What It Does

1. **Patient Intake** -- Structured form: demographics, symptoms, vitals, medications, allergies, medical images
2. **5-Step Agentic Workflow** -- Symptom Analysis, Triage Assessment, Differential Diagnosis, Risk Stratification, Recommended Actions
3. **Safety Validation** -- 9-category post-processing guard catches errors the model might miss (emergency escalation, drug interactions, critical vitals, demographic bias, pregnancy risks, and more)
4. **Follow-Up Chat** -- Interactive Q&A with MedGemma after triage
5. **Export** -- FHIR R4 Bundle, Clinical JSON, or Text Report

All inference runs locally via [HuggingFace Transformers](https://huggingface.co/google/medgemma-1.5-4b-it) on Apple Silicon MPS (~8 GB).

---

## Requirements

| Component | Requirement |
|---|---|
| Mac | Apple Silicon (M1/M2/M3/M4) -- **required** |
| OS | macOS 14.0+ (Sonoma) |
| RAM | 16 GB minimum (model loads in bfloat16) |
| Storage | ~8 GB for MedGemma weights + ~2 GB for app |
| Xcode | 15.0+ |
| Python | 3.10+ |
| HuggingFace | Account with [MedGemma access](https://huggingface.co/google/medgemma-1.5-4b-it) approved |

---

## Setup

### 1. Clone and Create Virtual Environment

```bash
git clone https://github.com/magnetarai-founder/MedStation-MedGemma_Impact.git
cd MedStation-MedGemma_Impact

python3 -m venv venv
source venv/bin/activate
pip install -r apps/backend/requirements.txt
pip install transformers accelerate huggingface_hub pillow
```

### 2. Download MedGemma 1.5 4B

Log into HuggingFace (you must have accepted the [HAI-DEF terms](https://huggingface.co/google/medgemma-1.5-4b-it)):

```bash
huggingface-cli login
huggingface-cli download google/medgemma-1.5-4b-it \
  --local-dir .models/medgemma-1.5-4b-it
```

This downloads ~8 GB of model weights to `.models/`.

### 3. Build and Run the macOS App

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

The app auto-starts the backend on launch. The backend loads MedGemma into memory on first inference request (~30s on M1, ~15s on M3+).

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

## Project Structure

```
.models/
  medgemma-1.5-4b-it/              # HuggingFace model weights (gitignored)

apps/
  native/                           # macOS SwiftUI app (Apple Silicon)
    Shared/
      Services/AI/
        MedicalWorkflowEngine.swift   # 5-step agentic orchestrator
        MedicalSafetyGuard.swift      # 9-category safety validation
        MedicalAIService.swift        # MedGemma client + model lifecycle
        MedicalAuditLogger.swift      # SHA-256 audit trail
        MedicalBenchmarkHarness.swift # 10-vignette evaluation harness
      Models/
        MedicalModels.swift           # Patient, case, triage data models
    macOS/
      Workspaces/Hub/Panels/
        MedicalPanel.swift            # Main UI (intake, results, chat, export)

  backend/                          # Python FastAPI
    api/
      main.py                         # App factory + health endpoint
      services/
        medgemma.py                   # MedGemma inference service (Transformers)
      routes/chat/
        medgemma.py                   # /medgemma/generate, /status, /load
        ollama_proxy.py               # Ollama proxy (fallback)
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

## API Endpoints

The backend runs on `http://localhost:8000` and provides:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Backend health check |
| `/api/v1/chat/medgemma/status` | GET | Model loaded status + device |
| `/api/v1/chat/medgemma/load` | POST | Explicitly load model into memory |
| `/api/v1/chat/medgemma/generate` | POST | Generate response (text or multimodal) |
| `/api/v1/chat/ollama/models` | GET | List local Ollama models (fallback) |
| `/api/v1/chat/ollama/generate` | POST | Generate via Ollama (fallback) |

---

## Storage

| Data | Location |
|---|---|
| Model weights | `.models/medgemma-1.5-4b-it/` (project root) |
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
