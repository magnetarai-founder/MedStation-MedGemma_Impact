# MedStation Video Demo Script (3 minutes)

Target: Kaggle MedGemma Impact Challenge submission video

---

## 0:00-0:20 -- The Problem (voiceover + text slides)

**SHOW:** Title card: "MedStation -- On-Device Medical Triage with MedGemma"

**SAY:**
> "130 million emergency department visits happen in the US every year. Average wait times exceed two hours. For time-critical conditions like heart attacks or strokes, delayed triage costs lives.
>
> Existing AI triage tools require cloud connectivity -- raising privacy concerns and failing in rural or disconnected settings. MedStation solves this by running MedGemma entirely on-device. Zero patient data ever leaves your Mac."

---

## 0:20-1:00 -- Patient Intake (screen recording)

**SHOW:** MedStation app open on the Medical Panel

**SAY:**
> "Let me walk through a real clinical scenario. I'll create a new case."

**DO:**
1. Click "New Case"
2. Fill in patient demographics:
   - Patient ID: "DEMO-002"
   - Age: 58, Male
   - Chief complaint: "Crushing chest pain radiating to left arm, onset 30 minutes ago"
3. Enter vitals:
   - HR: 110, BP: 160/95, Temp: 98.6, RR: 22, SpO2: 94%
4. Add medical history: "Hypertension, Type 2 Diabetes, smoker"
5. Add medications: "Metformin, Lisinopril, Aspirin"

**SAY:**
> "Notice the real-time vital sign validation -- the system uses age-banded physiologic ranges. Heart rate of 110 is flagged as elevated for an adult."

**Pause briefly on the filled form.**

> "Now let's attach a chest X-ray."

**DO:** Upload a sample chest X-ray image.

> "The image will be processed through a 5-layer on-device Vision pipeline before the workflow begins."

---

## 1:00-1:40 -- Agentic Workflow Execution (screen recording)

**SHOW:** Click "I Understand -- Run Analysis" (after disclaimer confirmation)

**SAY:**
> "MedStation now runs a 5-step agentic reasoning workflow -- each step powered by MedGemma 4B running locally through Ollama."

**DO:** Show the progress indicator stepping through:
1. Symptom Analysis
2. Triage Assessment
3. Differential Diagnosis
4. Risk Stratification
5. Recommended Actions

**SAY (as steps progress):**
> "Step 1 analyzes symptoms and identifies red flags. Step 2 classifies triage level. Step 3 generates differential diagnoses with probabilities. Step 4 assesses patient-specific risk factors. Step 5 produces prioritized recommendations.
>
> Each step receives cumulative context from prior steps -- the same chain-of-thought reasoning clinicians use. The entire workflow takes about 30 to 60 seconds."

---

## 1:40-2:10 -- Results + Safety Alerts (screen recording)

**SHOW:** Scroll through the results view

**SAY:**
> "The system correctly classifies this as an Emergency -- suspected acute STEMI. The differential includes myocardial infarction, unstable angina, and aortic dissection, each with probability estimates."

**DO:** Point out:
- Triage level: Emergency (red badge)
- Top 3 differential diagnoses with percentages
- Recommended actions (Call 911, aspirin, etc.)

**SAY:**
> "Now look at the safety alerts."

**DO:** Scroll to safety alerts section

> "The 9-category safety guard runs independently of MedGemma. It catches critical vitals, flags medication interactions -- here Aspirin plus the patient's existing medications -- and attaches clinical guideline references from AHA/ACC. Even if the model under-triages, the safety guard escalates."

---

## 2:10-2:30 -- Follow-Up Chat + Image Analysis (screen recording)

**SAY:**
> "After triage, clinicians can ask follow-up questions."

**DO:** Type a follow-up: "What are the immediate next steps for this patient?"

**SHOW:** Streaming response from MedGemma

> "The image analysis results from the chest X-ray are integrated into the clinical context, so MedGemma reasons over both structured data and visual findings."

---

## 2:30-2:45 -- Benchmark + Export (screen recording)

**SAY:**
> "MedStation includes a built-in benchmark harness -- 10 clinically validated vignettes across 6 specialties."

**DO:** Quick cut to benchmark results screen showing:
- Composite score
- Per-vignette breakdown
- 5x5 confusion matrix

> "And all data exports as FHIR R4 Bundles with LOINC-coded observations -- ready for integration with existing healthcare IT systems."

**DO:** Quick flash of FHIR export dialog

---

## 2:45-3:00 -- Model Card + Close (screen recording + text slide)

**DO:** Expand the model card disclosure in the results view

**SAY:**
> "Every analysis includes an in-app model card -- intended use, known limitations, bias considerations, and privacy architecture. The full audit trail is logged with SHA-256 privacy hashing."

**SHOW:** Closing title card

> "MedStation. Privacy-first medical triage. 5-step agentic workflow. 9 safety guardrails. Zero data leaves the device. Built with MedGemma for the Kaggle Impact Challenge."

**END**

---

## Production Notes

- **Screen recording:** QuickTime Player, 1920x1080, 60fps
- **Voiceover:** Record separately, clean audio, calm/professional tone
- **Pacing:** Each section timed to fit -- practice transitions
- **Music:** Subtle background (royalty-free, low volume under voiceover)
- **Captions:** Add subtitles for accessibility
- **Pre-flight:** Ensure Ollama is running and MedGemma is loaded before recording
- **Fallback:** If a workflow takes too long, speed up the middle portion in editing
