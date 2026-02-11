### Project name
**MedStation** -- Privacy-First On-Device Medical Triage Assistant

### Your team
Josh Hipps -- Software Engineer. Solo developer. Designed architecture, implemented the 5-step agentic workflow, safety guard, benchmark harness, and native macOS app.

### Problem statement

Emergency department overcrowding is a global crisis: 130M+ annual ED visits in the US alone, with average wait times exceeding 2 hours. Delayed triage leads to adverse outcomes -- patients with time-critical conditions (STEMI, stroke, sepsis) may not receive care within clinically meaningful windows.

Existing AI triage tools require cloud connectivity, raising HIPAA concerns and failing in bandwidth-constrained settings (rural clinics, disaster response, field medicine). **No patient data should ever need to leave the device to receive AI-assisted triage.**

**Impact:** If MedStation reduces time-to-triage by even 15 minutes for 1% of US ED visits, that's 1.3M patients per year who reach clinical assessment faster. For time-critical conditions (stroke: 4.5hr window, STEMI: 90min door-to-balloon), this directly translates to improved outcomes.

**Target users:** ED triage nurses, rural clinic staff, medical students, telehealth providers, field medics.

### Overall solution

MedStation runs **MedGemma 1.5 4B** entirely on-device via HuggingFace Transformers on Apple Silicon (MPS). It implements a **5-step agentic reasoning workflow** that mirrors clinical decision-making:

1. **Symptom Analysis** -- Identifies primary symptoms, red flags, and temporal progression
2. **Triage Assessment** -- 5-level classification (Emergency / Urgent / Semi-Urgent / Non-Urgent / Self-Care) with clinical justification
3. **Differential Diagnosis** -- Top 3-5 conditions with probability estimates and rationale
4. **Risk Stratification** -- Patient-specific risk factors, comorbidity interactions, complication likelihood
5. **Recommended Actions** -- Prioritized interventions, self-care instructions, escalation triggers

Each step receives cumulative context from all prior steps, forming a chain-of-thought that builds progressively -- the same reasoning pattern clinicians use. MedGemma 1.5's built-in reasoning tokens (`<unused94>thought`) enhance this with structured internal deliberation before each response.

**Why MedGemma is the right model:** MedGemma 1.5 4B is multimodal (text + images), medically fine-tuned, and small enough to run on a laptop. Its 128K context window accommodates full patient histories. No other HAI-DEF model combines medical text reasoning with image understanding at this parameter count.

**Zero patient data leaves the device.** All inference, safety validation, audit logging, and case storage happen locally.

### Technical details

**Architecture:**

```
macOS Native App (SwiftUI, Apple Silicon)
    |
MedicalPanel.swift ---------- Patient intake, results, chat, FHIR export
    |
MedicalWorkflowEngine.swift - 5-step agentic orchestrator (context threading)
    |
MedicalSafetyGuard.swift ---- 9 post-processing safety checks (rule-based)
    |
Python FastAPI Backend ------ MedGemma inference service
    |
HuggingFace Transformers ---- google/medgemma-1.5-4b-it (bfloat16, MPS)
    |
Apple Silicon GPU ----------- On-device, ~8GB model weights
```

**Agentic workflow design:** The `MedicalWorkflowEngine` orchestrates 5 sequential LLM calls with context threading -- each step's prompt includes the output of all prior steps. When medical images are attached (X-rays, skin photos), a vision pipeline runs before the workflow: OCR, object detection, scene classification, segmentation, and description generation. Results are injected into patient context so MedGemma reasons over both structured data and visual findings.

**Safety guard (9 categories):** Every workflow output passes through `MedicalSafetyGuard.validate()` -- a rule-based post-processing layer:

| Category | What It Catches |
|---|---|
| Emergency Escalation | Life-threatening conditions -- escalates even when model under-triages |
| Red Flag Symptoms | 12 pattern-matched flags (thunderclap headache, hemoptysis, acute weakness) |
| Critical Vitals | Age-banded thresholds across 6 age tiers (neonate to geriatric) |
| Medication Interactions | 12 drug-drug interaction categories (SSRIs+MAOIs, warfarin+CYP, QT prolongation) |
| Confidence Calibration | Flat probability distributions, single-diagnosis anchoring |
| Demographic Bias | Sex-condition mismatch, age-condition mismatch |
| Pregnancy Risks | Preeclampsia, eclampsia, ectopic pregnancy, placental abruption |
| Input Robustness | Contradictory vitals, excessive symptoms, vague complaints |
| Guideline References | Citations from 9 evidence-based guideline databases (AHA/ACC, GINA, ATS/IDSA, ADA) |

**Benchmark evaluation:** 10 clinically validated vignettes across 8 specialties:

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

Composite scoring: Triage accuracy (40%) + Diagnosis recall (35%) + Safety coverage (25%). A 5x5 confusion matrix detects systematic over/under-triage bias.

**Export & interoperability:** FHIR R4 Transaction Bundles with Patient, Condition, Observation (LOINC-coded), and RiskAssessment resources. Also exports Clinical JSON and human-readable Text Reports.

**Audit trail:** SHA-256 privacy hashing (only first 8 bytes stored), model traceability (model ID, version, parameter count per workflow), per-step input/output hashes, consent tracking, user feedback loop (Accurate / Partially Helpful / Incorrect).

**Performance (Apple Silicon):**

| Metric | Value |
|---|---|
| Model load time | ~30s (M1), ~15s (M3+) |
| Full 5-step workflow | 30-60s |
| Safety validation | <50ms (rule-based) |
| Model size on disk | ~8 GB |
| External cloud dependencies | Zero |

**Deployment challenges:** MedGemma 1.5 4B requires 16GB RAM in bfloat16. For 8GB Macs, quantized GGUF variants via Ollama provide a fallback path at reduced quality. Production deployment would require validation against institution-specific clinical protocols and regulatory review.

**Links:**
- Code: https://github.com/magnetarai-founder/MedStation-MedGemma_Impact
- Model: https://huggingface.co/google/medgemma-1.5-4b-it
- Video: [TODO]

---

*Built with MedGemma 1.5 for the Kaggle MedGemma Impact Challenge 2026.*
