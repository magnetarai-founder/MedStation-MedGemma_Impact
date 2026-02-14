"""
MedStation — HuggingFace Spaces Demo
MedGemma 1.5 4B agentic triage workflow with safety guard.
Kaggle MedGemma Impact Challenge 2026.

Supports two modes:
  1. GPU mode (ZeroGPU / dedicated) — live inference with MedGemma
  2. Demo mode (CPU-basic fallback) — pre-computed results for the demo case,
     proving the workflow while the code remains fully auditable.
"""

import os
import time
import gradio as gr

# ZeroGPU support (free GPU on HuggingFace Spaces with Pro)
try:
    import spaces
    ON_SPACES = True
except ImportError:
    ON_SPACES = False

# Defer heavy imports (torch, transformers) to avoid OOM on CPU-basic.

# ---------------------------------------------------------------------------
# Model loading — attempt GPU first, fallback to demo mode.
# ---------------------------------------------------------------------------

MODEL_ID = "google/medgemma-1.5-4b-it"
_model = None
_processor = None
LIVE_MODE = False


def _has_gpu():
    """Check if a GPU is available without importing torch (saves RAM on CPU)."""
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def _try_load_model():
    """Attempt to load MedGemma. Only tries if GPU is available (CPU-basic OOMs)."""
    global _model, _processor, LIVE_MODE

    if not _has_gpu():
        print("No GPU detected — starting in DEMO mode (pre-computed results).")
        LIVE_MODE = False
        return False

    try:
        import torch
        from transformers import AutoProcessor, AutoModelForImageTextToText

        print(f"Loading processor for {MODEL_ID}...")
        _processor = AutoProcessor.from_pretrained(MODEL_ID)

        print(f"Loading model {MODEL_ID}...")
        _model = AutoModelForImageTextToText.from_pretrained(
            MODEL_ID, torch_dtype=torch.bfloat16, device_map="auto"
        )

        LIVE_MODE = True
        print("Model loaded — LIVE inference mode active.")
        return True
    except Exception as e:
        print(f"Model load failed ({type(e).__name__}: {e})")
        print("Falling back to DEMO mode with pre-computed results.")
        LIVE_MODE = False
        return False


# Attempt load at startup
_try_load_model()


def _generate(prompt: str, system_prompt: str = "You are an expert medical AI assistant.",
              max_tokens: int = 512, temperature: float = 0.3) -> str:
    """Generate text with MedGemma (only called in LIVE mode)."""
    import torch

    messages = [
        {"role": "system", "content": [{"type": "text", "text": system_prompt}]},
        {"role": "user", "content": [{"type": "text", "text": prompt}]},
    ]

    inputs = _processor.apply_chat_template(
        messages, add_generation_prompt=True,
        tokenize=True, return_dict=True, return_tensors="pt",
    ).to(_model.device, dtype=_model.dtype)

    input_len = inputs["input_ids"].shape[-1]

    with torch.inference_mode():
        output = _model.generate(
            **inputs, max_new_tokens=max_tokens,
            do_sample=temperature > 0,
            temperature=temperature if temperature > 0 else None,
        )

    return _processor.decode(output[0][input_len:], skip_special_tokens=True)


# ---------------------------------------------------------------------------
# Patient context formatting (mirrors MedicalWorkflowEngine.swift)
# ---------------------------------------------------------------------------

def _format_context(chief_complaint, symptoms, age, sex, hr, bp, temp, rr, spo2,
                    history, medications, allergies):
    ctx = f"Chief Complaint: {chief_complaint}\nSeverity: Reported by patient"

    if age:
        note = f"\nAge: {age} years"
        try:
            age_i = int(age)
            if age_i < 2:
                note += " (Neonate/Infant)"
            elif age_i < 18:
                note += " (Pediatric)"
            elif age_i > 65:
                note += " (Geriatric)"
        except ValueError:
            pass
        ctx += note

    if sex:
        ctx += f"\nBiological Sex: {sex}"

    if symptoms:
        ctx += f"\nSymptoms: {symptoms}"

    vitals_parts = []
    if hr:
        vitals_parts.append(f"HR: {hr} bpm")
    if bp:
        vitals_parts.append(f"BP: {bp}")
    if temp:
        vitals_parts.append(f"Temp: {temp}\u00b0F")
    if rr:
        vitals_parts.append(f"RR: {rr}/min")
    if spo2:
        vitals_parts.append(f"SpO2: {spo2}%")
    if vitals_parts:
        ctx += "\nVital Signs:\n  " + "\n  ".join(vitals_parts)

    if history:
        ctx += f"\nMedical History: {history}"
    if medications:
        ctx += f"\nMedications: {medications}"
    if allergies:
        ctx += f"\nAllergies: {allergies}"

    return ctx


# ---------------------------------------------------------------------------
# 5-step agentic workflow (mirrors MedicalWorkflowEngine.swift prompts)
# ---------------------------------------------------------------------------

STEPS = [
    ("Symptom Analysis", """Analyze the patient's symptoms. For each point, give 1-2 sentences max:
1. Primary symptoms and characteristics
2. Red flag symptoms requiring immediate attention
3. Associated symptoms suggesting specific conditions
4. Timeline and progression

Be concise and evidence-based. Use bullet points."""),

    ("Triage Assessment", """Your FIRST line must be exactly one of these (copy it verbatim):
TRIAGE: Emergency
TRIAGE: Urgent
TRIAGE: Semi-Urgent
TRIAGE: Non-Urgent
TRIAGE: Self-Care

Then justify in 2-3 sentences. Only classify as Emergency if immediately life-threatening RIGHT NOW."""),

    ("Differential Diagnosis", """List top 3 most likely diagnoses. For each, one line:
[Number]. [Condition] (high/medium/low likelihood) — [1 sentence reasoning]

Be concise. No more than 3 conditions."""),

    ("Risk Stratification", """List key risk factors as bullet points (1 sentence each):
- Patient-specific risk factors
- Warning signs requiring immediate care
- Complications to monitor

Be concise. Max 5 bullet points."""),

    ("Recommended Actions", """List 3-5 actionable recommendations, numbered by priority:
1. Most urgent action first
2. When/where to seek care
3. Key diagnostic tests
4. Red flags requiring emergency care

One sentence per recommendation."""),
]


def _extract_triage(text: str) -> str:
    for line in text.strip().splitlines()[:3]:
        line_upper = line.strip().upper()
        if "EMERGENCY" in line_upper:
            return "Emergency"
        if "URGENT" in line_upper and "NON" not in line_upper and "SEMI" not in line_upper:
            return "Urgent"
        if "SEMI" in line_upper:
            return "Semi-Urgent"
        if "NON" in line_upper:
            return "Non-Urgent"
        if "SELF" in line_upper:
            return "Self-Care"
    return "Urgent"


TRIAGE_COLORS = {
    "Emergency": "red",
    "Urgent": "orange",
    "Semi-Urgent": "#DAA520",
    "Non-Urgent": "green",
    "Self-Care": "blue",
}


# ---------------------------------------------------------------------------
# Safety guard (simplified — mirrors MedicalSafetyGuard.swift core checks)
# ---------------------------------------------------------------------------

EMERGENCY_KEYWORDS = [
    "cardiac arrest", "not breathing", "unconscious", "unresponsive",
    "severe bleeding", "chest pain", "stroke", "seizure", "anaphylaxis",
    "suicidal", "overdose", "gunshot", "stabbing",
]

DRUG_INTERACTIONS = {
    frozenset(["warfarin", "aspirin"]): "Increased bleeding risk",
    frozenset(["ssri", "maoi"]): "Serotonin syndrome risk",
    frozenset(["ace inhibitor", "potassium"]): "Hyperkalemia risk",
    frozenset(["metformin", "contrast"]): "Lactic acidosis risk",
    frozenset(["lisinopril", "potassium"]): "Hyperkalemia risk",
    frozenset(["sildenafil", "nitroglycerin"]): "Severe hypotension risk",
    frozenset(["viagra", "nitrate"]): "Severe hypotension risk",
}


def _run_safety_guard(context: str, triage: str, medications: str, hr, spo2, temp):
    alerts = []

    ctx_lower = context.lower()
    for kw in EMERGENCY_KEYWORDS:
        if kw in ctx_lower:
            alerts.append(f"\u26a0\ufe0f **EMERGENCY ESCALATION**: Detected '{kw}' \u2014 immediate medical attention required")
            break

    try:
        if hr and int(hr) > 150:
            alerts.append(f"\u2764\ufe0f **CRITICAL VITAL**: Heart rate {hr} bpm exceeds critical threshold (>150)")
        if hr and int(hr) < 40:
            alerts.append(f"\u2764\ufe0f **CRITICAL VITAL**: Heart rate {hr} bpm below critical threshold (<40)")
    except ValueError:
        pass

    try:
        if spo2 and int(spo2) < 90:
            alerts.append(f"\U0001fa7b **CRITICAL VITAL**: SpO2 {spo2}% \u2014 hypoxemia (<90%)")
    except ValueError:
        pass

    try:
        if temp and float(temp) > 104:
            alerts.append(f"\U0001f321\ufe0f **CRITICAL VITAL**: Temperature {temp}\u00b0F \u2014 hyperthermia (>104\u00b0F)")
    except ValueError:
        pass

    if medications:
        meds_lower = medications.lower()
        for pair, risk in DRUG_INTERACTIONS.items():
            if all(drug in meds_lower for drug in pair):
                alerts.append(f"\U0001f48a **DRUG INTERACTION**: {' + '.join(pair)} \u2014 {risk}")

    if triage in ("Non-Urgent", "Self-Care"):
        for kw in ["chest pain", "shortness of breath", "severe headache", "hemoptysis"]:
            if kw in ctx_lower:
                alerts.append(f"\u26a0\ufe0f **TRIAGE ESCALATION**: '{kw}' present but triage is {triage} \u2014 consider upgrading")
                break

    return alerts


# ---------------------------------------------------------------------------
# Pre-computed demo results (STEMI case — generated by MedGemma on Apple M4)
# These are real MedGemma outputs cached for the demo case.
# ---------------------------------------------------------------------------

DEMO_RESULTS = {
    "Symptom Analysis": (
        "**1. Primary Symptoms:**\n"
        "- Severe chest pain radiating to left arm, acute onset 20 minutes ago \u2014 classic anginal pattern\n"
        "- Shortness of breath with diaphoresis (profuse sweating) suggests cardiovascular compromise\n\n"
        "**2. Red Flag Symptoms:**\n"
        "- Chest pain + left arm radiation + diaphoresis = classic acute coronary syndrome presentation\n"
        "- Acute onset in 58-year-old male with hypertension/diabetes = high-risk profile\n\n"
        "**3. Associated Symptoms:**\n"
        "- Nausea + diaphoresis alongside chest pain strongly suggest acute MI (STEMI/NSTEMI)\n"
        "- Tachycardia (HR 110) and mildly reduced SpO2 (94%) support hemodynamic stress\n\n"
        "**4. Timeline:**\n"
        "- Hyperacute presentation (20 minutes) \u2014 within the critical treatment window for reperfusion therapy"
    ),
    "Triage Assessment": (
        "TRIAGE: Emergency\n\n"
        "This patient presents with classic ST-elevation myocardial infarction (STEMI) features: "
        "acute chest pain radiating to the left arm with diaphoresis, nausea, tachycardia, and "
        "borderline hypoxemia in a 58-year-old male with cardiovascular risk factors. "
        "Immediate activation of the cardiac catheterization lab and emergency medical services is required. "
        "Time to reperfusion is the critical determinant of outcome."
    ),
    "Differential Diagnosis": (
        "1. **ST-Elevation Myocardial Infarction (STEMI)** (high likelihood) \u2014 "
        "Classic presentation with chest pain, left arm radiation, diaphoresis, nausea, and cardiac risk factors in a 58M\n\n"
        "2. **Unstable Angina / NSTEMI** (medium likelihood) \u2014 "
        "Similar presentation but without confirmed ST-elevation; troponin and ECG needed to differentiate\n\n"
        "3. **Aortic Dissection** (low likelihood) \u2014 "
        "Severe chest pain and hypertension could suggest dissection, though radiation pattern and associated symptoms favor ACS"
    ),
    "Risk Stratification": (
        "- **Age + Sex**: 58-year-old male \u2014 peak demographic for acute coronary events\n"
        "- **Comorbidities**: Hypertension + Type 2 Diabetes = significant atherosclerotic risk factors\n"
        "- **Hemodynamic instability**: Tachycardia (HR 110) + borderline hypoxemia (SpO2 94%) suggest early cardiogenic compromise\n"
        "- **Medication interaction**: Lisinopril (ACE inhibitor) \u2014 monitor potassium levels; avoid in acute hypotension\n"
        "- **Critical window**: 20-minute onset \u2014 within 90-minute door-to-balloon target for PCI"
    ),
    "Recommended Actions": (
        "1. **Call 911 immediately** \u2014 activate EMS with STEMI alert for cardiac catheterization lab mobilization\n"
        "2. **Administer aspirin 325mg** (chewed) if no true allergy and not already taken \u2014 first-line antiplatelet therapy\n"
        "3. **Obtain 12-lead ECG** within 10 minutes of arrival to confirm STEMI and guide reperfusion strategy\n"
        "4. **Draw troponin, CBC, BMP, coagulation panel** \u2014 serial troponins to quantify myocardial injury\n"
        "5. **Red flags for immediate escalation**: loss of consciousness, new arrhythmia, BP drop below 90 systolic, or worsening dyspnea"
    ),
}


# ---------------------------------------------------------------------------
# Main workflow function
# ---------------------------------------------------------------------------

def _run_workflow_inner(chief_complaint, symptoms, age, sex, hr, bp, temp, rr, spo2,
                        history, medications, allergies, progress=gr.Progress()):
    if not chief_complaint or not chief_complaint.strip():
        return ("", "", "", "Please enter a chief complaint.", "", "")

    context = _format_context(
        chief_complaint, symptoms, age, sex, hr, bp, temp, rr, spo2,
        history, medications, allergies,
    )

    # Decide: live inference or demo results
    using_demo = False
    if not LIVE_MODE:
        # Check if this matches the demo case closely enough
        if "chest pain" in chief_complaint.lower() and "left arm" in chief_complaint.lower():
            using_demo = True
            results = dict(DEMO_RESULTS)
            # Simulate progress for demo
            for i, (title, _) in enumerate(STEPS):
                progress((i + 1) / len(STEPS), desc=f"Step {i + 1}/5: {title}")
                time.sleep(0.3)
        else:
            return (
                "",
                "",
                "",
                (
                    "### GPU Required for Custom Cases\n\n"
                    "This Space is running in **demo mode** (no GPU available). "
                    "Live MedGemma inference requires GPU hardware.\n\n"
                    "**To try the demo**: Click **Load Demo Case** then **Run Analysis** "
                    "to see pre-computed MedGemma results for a STEMI case.\n\n"
                    "**For live inference**: The [native macOS app](https://github.com/magnetarai-founder/MedStation-MedGemma_Impact) "
                    "runs MedGemma on-device via Apple Silicon."
                ),
                "",
                "",
            )
    else:
        # LIVE MODE — run actual inference
        results = {}
        cumulative = context

        for i, (title, prompt) in enumerate(STEPS):
            progress((i + 1) / len(STEPS), desc=f"Step {i + 1}/5: {title}")

            full_prompt = f"Patient Context:\n{cumulative}\n\nTask:\n{prompt}"
            response = _generate(full_prompt, max_tokens=512, temperature=0.3)
            results[title] = response

            if title == "Symptom Analysis":
                cumulative = context + f"\n\nSymptom Analysis:\n{response}"
            elif title == "Triage Assessment":
                triage = _extract_triage(response)
                cumulative = context + f"\n\nTriage: {triage}\n\nSymptom Analysis:\n{results['Symptom Analysis'][:500]}"
            elif title == "Differential Diagnosis":
                dx_summary = response[:300]
                cumulative = context + f"\n\nDifferential: {dx_summary}"
            elif title == "Risk Stratification":
                cumulative = context + f"\n\nTriage: {triage}\n\nRisk Factors:\n{response[:300]}"

    # Extract triage level
    triage = _extract_triage(results["Triage Assessment"])
    color = TRIAGE_COLORS.get(triage, "gray")

    # Safety guard (always runs live — no model needed)
    safety_alerts = _run_safety_guard(context, triage, medications, hr, spo2, temp)

    # Format outputs
    mode_label = " (demo)" if using_demo else ""
    triage_badge = (
        f'<div style="display:inline-block;padding:8px 20px;border-radius:20px;'
        f'background:{color};color:white;font-weight:bold;font-size:18px;">'
        f'{triage}{mode_label}</div>'
    )

    if safety_alerts:
        safety_md = "### Safety Alerts\n\n" + "\n\n".join(safety_alerts)
    else:
        safety_md = "*No safety alerts triggered.*"

    step_details = ""
    for title, content in results.items():
        step_details += f"### {title}\n\n{content}\n\n---\n\n"

    if using_demo:
        step_details += (
            "\n\n> *These results were generated by MedGemma 1.5 4B running on Apple M4 Max. "
            "The safety guard ran live on this input. "
            "For live inference on custom cases, GPU hardware is required.*"
        )

    disclaimer = (
        "> **MEDICAL DISCLAIMER:** This analysis is generated by an AI system (MedGemma) "
        "for educational and informational purposes only. It is NOT a substitute for "
        "professional medical advice, diagnosis, or treatment. Always seek the advice of "
        "a qualified healthcare provider."
    )

    return (
        triage_badge,
        results.get("Differential Diagnosis", ""),
        results.get("Recommended Actions", ""),
        safety_md,
        step_details,
        disclaimer,
    )


def _chat_followup_inner(message, history, chief_complaint, triage_html):
    if not message or not message.strip():
        return history, ""

    history = history or []

    if not LIVE_MODE:
        history.append({"role": "user", "content": message})
        history.append({
            "role": "assistant",
            "content": (
                "Follow-up chat requires GPU for live MedGemma inference. "
                "In the native macOS app, this runs on-device via Apple Silicon. "
                "Try the [desktop app](https://github.com/magnetarai-founder/MedStation-MedGemma_Impact) "
                "for full interactive chat."
            ),
        })
        return history, ""

    ctx = ""
    if chief_complaint:
        ctx = f"Prior case: {chief_complaint}."

    prompt = f"Patient Context:\n{ctx}\n\nClinician question: {message}"
    response = _generate(prompt, max_tokens=512, temperature=0.3)

    history.append({"role": "user", "content": message})
    history.append({"role": "assistant", "content": response})
    return history, ""


# Apply @spaces.GPU decorator for ZeroGPU when available.
if ON_SPACES:
    run_workflow = spaces.GPU(duration=300)(_run_workflow_inner)
    chat_followup = spaces.GPU(duration=120)(_chat_followup_inner)
else:
    run_workflow = _run_workflow_inner
    chat_followup = _chat_followup_inner


# ---------------------------------------------------------------------------
# Demo case pre-fill
# ---------------------------------------------------------------------------

DEMO = {
    "chief_complaint": "Severe chest pain radiating to left arm, onset 20 minutes ago",
    "symptoms": "chest pain, shortness of breath, nausea, diaphoresis",
    "age": "58",
    "sex": "Male",
    "hr": "110",
    "bp": "150/95",
    "temp": "98.6",
    "rr": "22",
    "spo2": "94",
    "history": "Hypertension, Type 2 Diabetes",
    "medications": "Metformin, Lisinopril",
    "allergies": "Penicillin",
}


def load_demo():
    return (
        DEMO["chief_complaint"], DEMO["symptoms"], DEMO["age"], DEMO["sex"],
        DEMO["hr"], DEMO["bp"], DEMO["temp"], DEMO["rr"], DEMO["spo2"],
        DEMO["history"], DEMO["medications"], DEMO["allergies"],
    )


# ---------------------------------------------------------------------------
# Gradio UI
# ---------------------------------------------------------------------------

MODE_BADGE = (
    '<span style="background:#22c55e;color:white;padding:2px 8px;border-radius:10px;font-size:11px;">LIVE</span>'
    if LIVE_MODE else
    '<span style="background:#eab308;color:white;padding:2px 8px;border-radius:10px;font-size:11px;">DEMO</span>'
)

HEADER_HTML = f"""
<div style="text-align:center;padding:16px 0 8px 0;">
    <h1 style="margin:0;font-size:28px;">MedStation {MODE_BADGE}</h1>
    <p style="margin:4px 0 0 0;color:#888;font-size:14px;">
        Privacy-First Medical Triage &middot; MedGemma 1.5 4B &middot;
        5-Step Agentic Workflow &middot; 9-Category Safety Guard
    </p>
    <p style="margin:2px 0 0 0;color:#666;font-size:11px;">
        Built for the <a href="https://www.kaggle.com/competitions/med-gemma-impact-challenge" target="_blank">
        Kaggle MedGemma Impact Challenge</a>
        &middot; <a href="https://github.com/magnetarai-founder/MedStation-MedGemma_Impact" target="_blank">Source Code</a>
    </p>
</div>
"""

with gr.Blocks(
    title="MedStation \u2014 MedGemma Triage",
    theme=gr.themes.Soft(primary_hue="purple"),
) as demo:

    gr.HTML(HEADER_HTML)

    if not LIVE_MODE:
        gr.Markdown(
            "> **Demo Mode**: GPU not available. Click **Load Demo Case** then **Run Analysis** "
            "to see pre-computed MedGemma results (STEMI case). The safety guard runs live on all inputs. "
            "For full inference on custom cases, see the "
            "[native macOS app](https://github.com/magnetarai-founder/MedStation-MedGemma_Impact)."
        )

    with gr.Row():
        # ---- Left column: intake form ----
        with gr.Column(scale=1):
            gr.Markdown("### Patient Intake")

            chief_complaint = gr.Textbox(label="Chief Complaint", lines=2,
                                         placeholder="e.g. Severe chest pain radiating to left arm")
            symptoms = gr.Textbox(label="Symptoms (comma-separated)",
                                  placeholder="e.g. chest pain, shortness of breath, nausea")

            with gr.Row():
                age = gr.Textbox(label="Age", placeholder="58")
                sex = gr.Dropdown(label="Sex", choices=["Male", "Female"], value=None)

            gr.Markdown("**Vital Signs**")
            with gr.Row():
                hr = gr.Textbox(label="HR (bpm)", placeholder="110")
                bp = gr.Textbox(label="BP", placeholder="150/95")
                temp = gr.Textbox(label="Temp (\u00b0F)", placeholder="98.6")
            with gr.Row():
                rr = gr.Textbox(label="RR (/min)", placeholder="22")
                spo2 = gr.Textbox(label="SpO2 (%)", placeholder="94")

            history = gr.Textbox(label="Medical History", placeholder="e.g. Hypertension, Diabetes")
            medications = gr.Textbox(label="Current Medications", placeholder="e.g. Metformin, Lisinopril")
            allergies = gr.Textbox(label="Allergies", placeholder="e.g. Penicillin")

            with gr.Row():
                demo_btn = gr.Button("Load Demo Case", variant="secondary", size="sm")
                run_btn = gr.Button("Run Analysis", variant="primary", size="lg")

        # ---- Right column: results ----
        with gr.Column(scale=1):
            gr.Markdown("### Results")

            triage_html = gr.HTML(label="Triage Level",
                                  value="<div style='color:#888;'>Run analysis to see triage level</div>")
            differential_md = gr.Markdown(label="Differential Diagnosis")
            actions_md = gr.Markdown(label="Recommended Actions")
            safety_md = gr.Markdown(label="Safety Alerts")

            with gr.Accordion("Full Reasoning Steps", open=False):
                steps_md = gr.Markdown()

            disclaimer_md = gr.Markdown()

    # ---- Follow-up chat ----
    gr.Markdown("---")
    gr.Markdown("### Follow-Up Chat")

    chatbot = gr.Chatbot(label="Ask MedGemma follow-up questions", height=250, type="messages")
    with gr.Row():
        chat_input = gr.Textbox(
            label="Question",
            placeholder="Ask about the diagnosis, treatment options, or next steps...",
            scale=4, show_label=False,
        )
        chat_send = gr.Button("Send", variant="primary", scale=1)

    # ---- Wiring ----
    intake_inputs = [
        chief_complaint, symptoms, age, sex, hr, bp, temp, rr, spo2,
        history, medications, allergies,
    ]
    result_outputs = [
        triage_html, differential_md, actions_md, safety_md, steps_md, disclaimer_md,
    ]

    run_btn.click(fn=run_workflow, inputs=intake_inputs, outputs=result_outputs)
    demo_btn.click(fn=load_demo, outputs=intake_inputs)

    chat_send.click(
        fn=chat_followup,
        inputs=[chat_input, chatbot, chief_complaint, triage_html],
        outputs=[chatbot, chat_input],
    )
    chat_input.submit(
        fn=chat_followup,
        inputs=[chat_input, chatbot, chief_complaint, triage_html],
        outputs=[chatbot, chat_input],
    )


if __name__ == "__main__":
    demo.launch()
