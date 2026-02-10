# MedStation

**On-device medical triage assistant powered by MedGemma 4B.**

MedStation runs a 5-step agentic reasoning workflow entirely on your Mac -- no cloud, no API keys, no patient data ever leaves the device. Built for the [Kaggle MedGemma Impact Challenge](https://www.kaggle.com/competitions/med-gemma-impact-challenge).

---

## What It Does

1. **Patient Intake** -- Structured form: demographics, symptoms, vitals, medications, allergies, medical images
2. **5-Step Agentic Workflow** -- Symptom Analysis, Triage Assessment, Differential Diagnosis, Risk Stratification, Recommended Actions
3. **Safety Validation** -- 9-category post-processing guard catches errors the model might miss (emergency escalation, drug interactions, critical vitals, demographic bias, pregnancy risks, and more)
4. **Follow-Up Chat** -- Interactive Q&A with MedGemma after triage
5. **Export** -- FHIR R4 Bundle, Clinical JSON, or Text Report

All inference runs locally via [Ollama](https://ollama.com) with MedGemma 4B (~3GB).

---

## Requirements

| Component | Requirement |
|---|---|
| OS | macOS 14.0+ (Sonoma) |
| RAM | 8 GB minimum, 16 GB recommended |
| Storage | ~3 GB for MedGemma weights |
| Processor | Apple Silicon (M1+) recommended, Intel supported |
| Xcode | 15.0+ (for building from source) |
| Python | 3.10+ (for backend) |

---

## Setup

### 1. Install Ollama

```bash
brew install ollama
ollama serve
```

Leave Ollama running in the background. MedStation will auto-download MedGemma 4B on first use, or you can pre-pull:

```bash
ollama pull alibayram/medgemma:4b
```

### 2. Build the macOS App

```bash
# Open in Xcode
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

### 3. Start the Backend (Optional)

The backend provides additional API routes for model management and chat streaming:

```bash
cd apps/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
uvicorn api.main:app --host 0.0.0.0 --port 8000
```

Health check: `http://localhost:8000/health`

---

## First Launch

1. MedStation opens directly into the **Medical Panel**
2. A **demo case** (58M with acute STEMI) is pre-loaded on first launch
3. Click **"I Understand -- Run Analysis"** to execute the 5-step workflow
4. View results: triage level, differential diagnoses, safety alerts, recommended actions
5. Try the **follow-up chat** to ask clarifying questions
6. Run the **benchmark** (toolbar chart icon) to evaluate across 10 clinical vignettes

---

## Project Structure

```
apps/
  native/                           # macOS SwiftUI app
    Shared/
      Services/AI/
        MedicalWorkflowEngine.swift   # 5-step agentic orchestrator
        MedicalSafetyGuard.swift      # 9-category safety validation
        MedicalAIService.swift        # Ollama client + model lifecycle
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
      router_registry.py              # Route registration
      routes/chat/                    # Chat + Ollama streaming
      services/
        ollama_client.py              # Ollama HTTP client
        chat_ollama.py                # Chat streaming service
```

---

## Benchmark

MedStation includes a built-in benchmark harness with 10 clinically validated vignettes across 6 specialties (Cardiology, Neurology, Allergy, Pulmonology, Surgery, Endocrinology, Pediatrics, Obstetrics).

**Scoring:** Triage accuracy (40%) + Diagnosis recall (35%) + Safety coverage (25%)

To run: Open MedStation > Click the chart icon in the toolbar > Run Benchmark (~5-10 min)

Results include per-vignette scores, a 5x5 confusion matrix, and JSON export.

---

## Storage

| Data | Location |
|---|---|
| Cases | `~/Library/Application Support/MedStation/workspace/medical/*.json` |
| Audit Logs | `~/Library/Application Support/MedStation/workspace/medical/audit/*.json` |
| Benchmarks | `~/Library/Application Support/MedStation/workspace/medical/benchmarks/*.json` |

---

## License

CC BY 4.0

See [LICENSE](./LICENSE) for details.

---

## Medical Disclaimer

This application is for **educational and informational purposes only**. It is NOT a substitute for professional medical advice, diagnosis, or treatment. Always seek the advice of a qualified healthcare provider. If you think you may have a medical emergency, call 911 immediately.
