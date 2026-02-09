//
//  MedicalSafetyGuard.swift
//  MagnetarStudio
//
//  Post-processing safety layer for medical AI outputs.
//  Validates workflow results for clinical safety signals:
//  emergency escalation, red flag symptoms, medication interactions,
//  and confidence calibration.
//
//  HAI-DEF (Health AI Developer Foundation) compliance: responsible
//  health AI requires output validation before presentation to users.
//
//  MedGemma Impact Challenge (Kaggle 2026).
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "MedicalSafetyGuard")

// MARK: - Safety Guard

struct MedicalSafetyGuard {

    // MARK: - Validate Workflow Result

    static func validate(_ result: MedicalWorkflowResult, intake: PatientIntake) -> [SafetyAlert] {
        var alerts: [SafetyAlert] = []

        // 1. Emergency escalation check
        alerts.append(contentsOf: checkEmergencySignals(result, intake: intake))

        // 2. Red flag symptoms
        alerts.append(contentsOf: checkRedFlagSymptoms(intake))

        // 3. Vital sign critical values (age-contextualized)
        if let vitals = intake.vitalSigns {
            alerts.append(contentsOf: checkCriticalVitals(vitals, age: intake.age))
        }

        // 4. High-risk medication interactions
        if !intake.currentMedications.isEmpty {
            alerts.append(contentsOf: checkMedicationRisks(intake.currentMedications, diagnoses: result.differentialDiagnoses))
        }

        // 5. Confidence calibration warnings
        alerts.append(contentsOf: checkConfidenceCalibration(result))

        // 6. Demographic bias detection (HAI-DEF fairness)
        alerts.append(contentsOf: checkDemographicBias(result, intake: intake))

        // 7. Pregnancy-specific risk checks
        if intake.isPregnant {
            alerts.append(contentsOf: checkPregnancyRisks(intake))
        }

        // 8. Input robustness validation
        alerts.append(contentsOf: checkInputRobustness(intake))

        if !alerts.isEmpty {
            logger.info("Safety guard generated \(alerts.count) alerts for case \(result.intakeId)")
        }

        return alerts.sorted { $0.severity.sortOrder < $1.severity.sortOrder }
    }

    // MARK: - Emergency Signals

    private static func checkEmergencySignals(_ result: MedicalWorkflowResult, intake: PatientIntake) -> [SafetyAlert] {
        var alerts: [SafetyAlert] = []

        if result.triageLevel == .emergency {
            alerts.append(SafetyAlert(
                severity: .critical,
                category: .emergencyEscalation,
                title: "Emergency — Seek Immediate Medical Care",
                message: "This analysis indicates a potentially life-threatening condition. Call 911 or go to the nearest emergency room immediately. Do NOT rely on this AI assessment.",
                actionLabel: "Call 911"
            ))
        }

        // Check for acute high-risk keywords in reasoning
        let reasoningText = result.reasoning.map(\.content).joined(separator: " ").lowercased()
        let acuteKeywords = ["stroke", "heart attack", "myocardial infarction", "pulmonary embolism",
                            "anaphylaxis", "sepsis", "meningitis", "aortic dissection",
                            "tension pneumothorax", "status epilepticus"]

        let foundAcute = acuteKeywords.filter { reasoningText.contains($0) }
        if !foundAcute.isEmpty && result.triageLevel != .emergency {
            alerts.append(SafetyAlert(
                severity: .warning,
                category: .emergencyEscalation,
                title: "Potentially Serious Conditions Detected",
                message: "The analysis mentions \(foundAcute.joined(separator: ", ")). Even if triage is not Emergency, consider seeking urgent medical evaluation.",
                actionLabel: "Seek Urgent Care"
            ))
        }

        return alerts
    }

    // MARK: - Red Flag Symptoms

    private static func checkRedFlagSymptoms(_ intake: PatientIntake) -> [SafetyAlert] {
        var alerts: [SafetyAlert] = []

        let symptoms = (intake.symptoms + [intake.chiefComplaint]).joined(separator: " ").lowercased()

        let redFlags: [(pattern: String, description: String)] = [
            ("worst headache", "Thunderclap headache may indicate subarachnoid hemorrhage"),
            ("sudden vision loss", "Acute vision loss requires urgent ophthalmological evaluation"),
            ("chest pain", "Chest pain warrants cardiac evaluation to rule out acute coronary syndrome"),
            ("difficulty breathing", "Acute dyspnea may indicate pulmonary embolism, pneumothorax, or cardiac failure"),
            ("coughing blood", "Hemoptysis requires evaluation for pulmonary embolism or malignancy"),
            ("blood in stool", "GI bleeding may indicate serious underlying pathology"),
            ("sudden weakness", "Acute neurological deficit may indicate stroke (time-critical)"),
            ("slurred speech", "Speech changes may indicate stroke — FAST protocol applies"),
            ("severe abdominal pain", "Acute abdomen may require surgical evaluation"),
            ("high fever", "High fever with other symptoms may indicate sepsis"),
            ("neck stiffness", "Meningeal signs (neck stiffness + fever) require urgent evaluation"),
            ("seizure", "New-onset seizures require neurological evaluation"),
        ]

        for flag in redFlags {
            if symptoms.contains(flag.pattern) {
                alerts.append(SafetyAlert(
                    severity: .warning,
                    category: .redFlagSymptom,
                    title: "Red Flag: \(flag.pattern.capitalized)",
                    message: flag.description,
                    actionLabel: nil
                ))
            }
        }

        return alerts
    }

    // MARK: - Critical Vitals

    private static func checkCriticalVitals(_ vitals: VitalSigns, age: Int? = nil) -> [SafetyAlert] {
        var alerts: [SafetyAlert] = []

        // Age-banded heart rate ranges (clinical reference ranges)
        let patientAge = age ?? 30
        let hrCriticalHigh: Int
        let hrCriticalLow: Int
        let hrWarningHigh: Int
        let hrWarningLow: Int
        let hrContext: String

        switch patientAge {
        case ..<1:    // Neonate/Infant
            hrCriticalHigh = 190; hrCriticalLow = 80
            hrWarningHigh = 160; hrWarningLow = 100
            hrContext = "neonate/infant"
        case 1..<6:  // Toddler/Preschool
            hrCriticalHigh = 170; hrCriticalLow = 60
            hrWarningHigh = 140; hrWarningLow = 80
            hrContext = "toddler"
        case 6..<12: // Child
            hrCriticalHigh = 150; hrCriticalLow = 50
            hrWarningHigh = 120; hrWarningLow = 70
            hrContext = "child"
        case 12..<18: // Adolescent
            hrCriticalHigh = 140; hrCriticalLow = 40
            hrWarningHigh = 110; hrWarningLow = 60
            hrContext = "adolescent"
        case 18..<65: // Adult
            hrCriticalHigh = 150; hrCriticalLow = 40
            hrWarningHigh = 120; hrWarningLow = 50
            hrContext = "adult"
        default:      // Geriatric (65+)
            hrCriticalHigh = 140; hrCriticalLow = 40
            hrWarningHigh = 110; hrWarningLow = 50
            hrContext = "geriatric"
        }

        if let hr = vitals.heartRate {
            if hr > hrCriticalHigh || hr < hrCriticalLow {
                alerts.append(SafetyAlert(
                    severity: .critical,
                    category: .criticalVital,
                    title: "Critical Heart Rate: \(hr) bpm",
                    message: hr > hrCriticalHigh ? "Tachycardia >\(hrCriticalHigh) bpm (\(hrContext)) may indicate cardiac emergency" : "Bradycardia <\(hrCriticalLow) bpm (\(hrContext)) may indicate heart block",
                    actionLabel: "Seek Emergency Care"
                ))
            } else if hr > hrWarningHigh || hr < hrWarningLow {
                alerts.append(SafetyAlert(
                    severity: .warning,
                    category: .criticalVital,
                    title: "Abnormal Heart Rate: \(hr) bpm",
                    message: "Heart rate outside normal \(hrContext) range. Clinical correlation recommended.",
                    actionLabel: nil
                ))
            }
        }

        if let temp = vitals.temperature {
            if temp >= 104.0 {
                alerts.append(SafetyAlert(
                    severity: .critical,
                    category: .criticalVital,
                    title: "Hyperpyrexia: \(String(format: "%.1f", temp))°F",
                    message: "Temperature ≥104°F is a medical emergency requiring immediate cooling measures.",
                    actionLabel: "Seek Emergency Care"
                ))
            } else if temp >= 102.0 {
                alerts.append(SafetyAlert(
                    severity: .warning,
                    category: .criticalVital,
                    title: "High Fever: \(String(format: "%.1f", temp))°F",
                    message: "Consider antipyretics and evaluate for underlying infection or inflammatory process.",
                    actionLabel: nil
                ))
            }
        }

        if let spo2 = vitals.oxygenSaturation {
            if spo2 < 90 {
                alerts.append(SafetyAlert(
                    severity: .critical,
                    category: .criticalVital,
                    title: "Critical SpO2: \(spo2)%",
                    message: "Oxygen saturation <90% indicates hypoxemia requiring supplemental oxygen.",
                    actionLabel: "Seek Emergency Care"
                ))
            } else if spo2 < 94 {
                alerts.append(SafetyAlert(
                    severity: .warning,
                    category: .criticalVital,
                    title: "Low SpO2: \(spo2)%",
                    message: "Oxygen saturation below normal (94-100%). Monitor closely.",
                    actionLabel: nil
                ))
            }
        }

        if let rr = vitals.respiratoryRate {
            if rr > 30 || rr < 8 {
                alerts.append(SafetyAlert(
                    severity: .critical,
                    category: .criticalVital,
                    title: "Critical Respiratory Rate: \(rr)/min",
                    message: rr > 30 ? "Tachypnea >30/min suggests respiratory distress" : "Bradypnea <8/min may indicate respiratory failure",
                    actionLabel: "Seek Emergency Care"
                ))
            }
        }

        return alerts
    }

    // MARK: - Medication Risks

    private static func checkMedicationRisks(_ medications: [String], diagnoses: [Diagnosis]) -> [SafetyAlert] {
        var alerts: [SafetyAlert] = []
        let medsLower = medications.map { $0.lowercased() }

        // Blood thinners with bleeding symptoms
        let bloodThinners = ["warfarin", "coumadin", "xarelto", "eliquis", "heparin", "aspirin", "plavix"]
        let bleedingDx = diagnoses.map { $0.condition.lowercased() }

        let onBloodThinner = bloodThinners.first { thinner in medsLower.contains(where: { $0.contains(thinner) }) }
        let hasBleedingRisk = bleedingDx.contains(where: { $0.contains("bleed") || $0.contains("hemorrh") || $0.contains("stroke") })

        if let thinner = onBloodThinner, hasBleedingRisk {
            alerts.append(SafetyAlert(
                severity: .warning,
                category: .medicationInteraction,
                title: "Medication Alert: \(thinner.capitalized) + Bleeding Risk",
                message: "Patient is on anticoagulant therapy. Differential includes conditions with bleeding risk. Inform healthcare provider about current medications.",
                actionLabel: nil
            ))
        }

        // NSAIDs with kidney/GI risk
        let nsaids = ["ibuprofen", "naproxen", "advil", "motrin", "aleve", "aspirin"]
        let onNSAID = nsaids.first { nsaid in medsLower.contains(where: { $0.contains(nsaid) }) }
        let hasGIRisk = bleedingDx.contains(where: { $0.contains("gastritis") || $0.contains("ulcer") || $0.contains("gi bleed") })

        if let nsaid = onNSAID, hasGIRisk {
            alerts.append(SafetyAlert(
                severity: .info,
                category: .medicationInteraction,
                title: "NSAID Caution: \(nsaid.capitalized)",
                message: "Current NSAID use with possible GI condition. Consider discussing alternatives with healthcare provider.",
                actionLabel: nil
            ))
        }

        // Drug-drug interaction database (major interactions)
        let interactionPairs: [(drugs: [String], interacts: [String], severity: SafetyAlert.Severity, warning: String)] = [
            // Serotonin syndrome risk
            (["sertraline", "fluoxetine", "paroxetine", "citalopram", "escitalopram", "venlafaxine", "duloxetine"],
             ["tramadol", "fentanyl", "meperidine", "linezolid", "methylene blue"],
             .critical, "Serotonin syndrome risk — combination of serotonergic agents"),
            (["sertraline", "fluoxetine", "paroxetine", "citalopram", "escitalopram"],
             ["phenelzine", "tranylcypromine", "isocarboxazid", "selegiline"],
             .critical, "SSRI + MAOI — life-threatening serotonin syndrome risk. Contraindicated."),
            // Cardiac rhythm
            (["amiodarone"],
             ["metoprolol", "atenolol", "propranolol", "diltiazem", "verapamil"],
             .warning, "Amiodarone + rate-controlling agent — risk of severe bradycardia or heart block"),
            (["digoxin"],
             ["amiodarone", "verapamil", "quinidine", "spironolactone"],
             .warning, "Digoxin toxicity risk — these drugs increase digoxin levels"),
            // Hyperkalemia
            (["lisinopril", "enalapril", "ramipril", "losartan", "valsartan"],
             ["spironolactone", "eplerenone", "potassium", "triamterene"],
             .warning, "ACE inhibitor/ARB + potassium-sparing agent — hyperkalemia risk"),
            // Renal
            (["metformin"],
             ["contrast", "iodine", "gadolinium"],
             .warning, "Metformin + contrast media — risk of lactic acidosis. Hold metformin before/after contrast."),
            // Bleeding
            (["warfarin", "coumadin"],
             ["metronidazole", "fluconazole", "amiodarone", "sulfamethoxazole", "trimethoprim"],
             .critical, "Warfarin + CYP inhibitor — increased bleeding risk, INR monitoring required"),
            // QT prolongation
            (["azithromycin", "erythromycin", "clarithromycin", "moxifloxacin"],
             ["ondansetron", "haloperidol", "methadone", "amiodarone", "sotalol"],
             .warning, "Dual QT-prolonging agents — risk of torsades de pointes"),
            // Hypotension
            (["sildenafil", "tadalafil", "vardenafil"],
             ["nitroglycerin", "isosorbide", "nitrate"],
             .critical, "PDE5 inhibitor + nitrate — severe hypotension risk. Contraindicated."),
            // Statin myopathy
            (["simvastatin", "atorvastatin", "lovastatin"],
             ["clarithromycin", "erythromycin", "itraconazole", "cyclosporine", "gemfibrozil"],
             .warning, "Statin + CYP3A4 inhibitor — increased risk of rhabdomyolysis"),
            // Lithium toxicity
            (["lithium"],
             ["ibuprofen", "naproxen", "diclofenac", "hydrochlorothiazide", "furosemide", "lisinopril", "enalapril"],
             .warning, "Lithium + NSAIDs/diuretics/ACE inhibitors — lithium toxicity risk"),
            // Hypoglycemia
            (["glipizide", "glyburide", "glimepiride", "insulin"],
             ["fluconazole", "ciprofloxacin", "metoprolol", "propranolol"],
             .warning, "Hypoglycemic agent + masking/potentiating drug — hypoglycemia risk"),
        ]

        for pair in interactionPairs {
            let hasDrug = pair.drugs.first { drug in medsLower.contains(where: { $0.contains(drug) }) }
            let hasInteraction = pair.interacts.first { drug in medsLower.contains(where: { $0.contains(drug) }) }

            if let drug = hasDrug, let interacting = hasInteraction {
                alerts.append(SafetyAlert(
                    severity: pair.severity,
                    category: .medicationInteraction,
                    title: "Drug Interaction: \(drug.capitalized) + \(interacting.capitalized)",
                    message: pair.warning,
                    actionLabel: pair.severity == .critical ? "Consult Pharmacist" : nil
                ))
            }
        }

        return alerts
    }

    // MARK: - Confidence Calibration

    private static func checkConfidenceCalibration(_ result: MedicalWorkflowResult) -> [SafetyAlert] {
        var alerts: [SafetyAlert] = []

        // Check if all diagnoses have similar probability (low confidence)
        let probabilities = result.differentialDiagnoses.map(\.probability)
        if probabilities.count >= 3 {
            let maxP = probabilities.max() ?? 0
            let minP = probabilities.min() ?? 0
            if maxP - minP < 0.15 {
                alerts.append(SafetyAlert(
                    severity: .info,
                    category: .confidenceCalibration,
                    title: "Low Diagnostic Confidence",
                    message: "Multiple conditions have similar probability. Additional clinical information (labs, imaging) may help narrow the differential. Consult a healthcare provider for definitive diagnosis.",
                    actionLabel: nil
                ))
            }
        }

        // Single diagnosis with high confidence — warn about anchoring bias
        if result.differentialDiagnoses.count == 1 {
            alerts.append(SafetyAlert(
                severity: .info,
                category: .confidenceCalibration,
                title: "Single Diagnosis — Anchoring Risk",
                message: "Only one condition was identified. AI models can exhibit anchoring bias. A healthcare provider may identify additional possibilities.",
                actionLabel: nil
            ))
        }

        return alerts
    }

    // MARK: - Demographic Bias Detection (HAI-DEF Fairness)

    private static func checkDemographicBias(_ result: MedicalWorkflowResult, intake: PatientIntake) -> [SafetyAlert] {
        var alerts: [SafetyAlert] = []
        let conditions = result.differentialDiagnoses.map { $0.condition.lowercased() }

        // Sex-condition mismatch check
        if let sex = intake.sex {
            let femaleOnlyConditions = ["ovarian", "endometriosis", "ectopic pregnancy", "eclampsia", "preeclampsia"]
            let maleOnlyConditions = ["testicular", "prostate"]

            if sex == .male && conditions.contains(where: { cond in femaleOnlyConditions.contains(where: { cond.contains($0) }) }) {
                alerts.append(SafetyAlert(
                    severity: .warning,
                    category: .demographicBias,
                    title: "Potential Sex-Condition Mismatch",
                    message: "Some diagnoses may not apply to this patient's biological sex. Review differential carefully.",
                    actionLabel: nil
                ))
            }
            if sex == .female && conditions.contains(where: { cond in maleOnlyConditions.contains(where: { cond.contains($0) }) }) {
                alerts.append(SafetyAlert(
                    severity: .warning,
                    category: .demographicBias,
                    title: "Potential Sex-Condition Mismatch",
                    message: "Some diagnoses may not apply to this patient's biological sex. Review differential carefully.",
                    actionLabel: nil
                ))
            }

            // Known clinical bias: chest pain in women is often under-triaged for cardiac causes
            if sex == .female && result.triageLevel != .emergency {
                let symptomsLower = (intake.symptoms + [intake.chiefComplaint]).joined(separator: " ").lowercased()
                if symptomsLower.contains("chest pain") {
                    alerts.append(SafetyAlert(
                        severity: .info,
                        category: .demographicBias,
                        title: "Clinical Bias Awareness: Chest Pain in Women",
                        message: "Chest pain in women may present atypically and is historically under-triaged for cardiac causes. Ensure cardiac evaluation is considered.",
                        actionLabel: nil
                    ))
                }
            }
        }

        // Age-condition mismatch check
        if let age = intake.age {
            let geriatricConditions = ["alzheimer", "dementia", "osteoarthritis", "age-related macular"]
            let pediatricConditions = ["croup", "kawasaki", "intussusception"]

            if age < 18 && conditions.contains(where: { cond in geriatricConditions.contains(where: { cond.contains($0) }) }) {
                alerts.append(SafetyAlert(
                    severity: .info,
                    category: .demographicBias,
                    title: "Age-Condition Consideration",
                    message: "Some conditions in the differential are uncommon in pediatric populations. Consider age-appropriate alternatives.",
                    actionLabel: nil
                ))
            }
            if age > 65 && conditions.contains(where: { cond in pediatricConditions.contains(where: { cond.contains($0) }) }) {
                alerts.append(SafetyAlert(
                    severity: .info,
                    category: .demographicBias,
                    title: "Age-Condition Consideration",
                    message: "Some conditions in the differential are typically pediatric. Consider age-appropriate alternatives.",
                    actionLabel: nil
                ))
            }
        }

        return alerts
    }

    // MARK: - Pregnancy-Specific Risk Checks

    private static func checkPregnancyRisks(_ intake: PatientIntake) -> [SafetyAlert] {
        var alerts: [SafetyAlert] = []
        let symptomsLower = (intake.symptoms + [intake.chiefComplaint]).joined(separator: " ").lowercased()

        // Preeclampsia: hypertension + headache/vision changes
        if let bp = intake.vitalSigns?.bloodPressure {
            let systolic = Int(bp.components(separatedBy: "/").first ?? "") ?? 0
            if systolic >= 140 {
                alerts.append(SafetyAlert(
                    severity: .critical,
                    category: .pregnancyRisk,
                    title: "Pregnancy + Hypertension: Preeclampsia Risk",
                    message: "Elevated blood pressure (\(bp)) during pregnancy may indicate preeclampsia. Seek immediate obstetric evaluation.",
                    actionLabel: "Seek Emergency Care"
                ))

                if symptomsLower.contains("headache") || symptomsLower.contains("vision") || symptomsLower.contains("blurred") {
                    alerts.append(SafetyAlert(
                        severity: .critical,
                        category: .pregnancyRisk,
                        title: "Eclampsia Warning Signs",
                        message: "Hypertension with headache or vision changes during pregnancy is a medical emergency. Risk of seizures (eclampsia).",
                        actionLabel: "Call 911"
                    ))
                }
            }
        }

        // Abdominal pain in pregnancy
        if symptomsLower.contains("abdominal pain") || symptomsLower.contains("pelvic pain") {
            alerts.append(SafetyAlert(
                severity: .warning,
                category: .pregnancyRisk,
                title: "Pregnancy + Abdominal Pain",
                message: "Abdominal or pelvic pain during pregnancy warrants evaluation for ectopic pregnancy, placental abruption, or preterm labor.",
                actionLabel: nil
            ))
        }

        // Vaginal bleeding in pregnancy
        if symptomsLower.contains("bleeding") || symptomsLower.contains("spotting") {
            alerts.append(SafetyAlert(
                severity: .warning,
                category: .pregnancyRisk,
                title: "Pregnancy + Bleeding",
                message: "Vaginal bleeding during pregnancy requires prompt obstetric evaluation to rule out miscarriage, placenta previa, or abruption.",
                actionLabel: nil
            ))
        }

        return alerts
    }

    // MARK: - Input Robustness Validation

    private static func checkInputRobustness(_ intake: PatientIntake) -> [SafetyAlert] {
        var alerts: [SafetyAlert] = []

        // Excessive symptom count — likely noise or spam
        if intake.symptoms.count > 20 {
            alerts.append(SafetyAlert(
                severity: .info,
                category: .inputRobustness,
                title: "High Symptom Count (\(intake.symptoms.count))",
                message: "A large number of symptoms may reduce diagnostic accuracy. Consider listing only primary and most relevant symptoms.",
                actionLabel: nil
            ))
        }

        // Contradictory vitals pattern
        if let vitals = intake.vitalSigns {
            // High HR + normal SpO2 + low RR is physiologically unusual
            if let hr = vitals.heartRate, let spo2 = vitals.oxygenSaturation, let rr = vitals.respiratoryRate {
                if hr > 150 && spo2 > 97 && rr < 12 {
                    alerts.append(SafetyAlert(
                        severity: .info,
                        category: .inputRobustness,
                        title: "Unusual Vital Sign Combination",
                        message: "Severe tachycardia with normal oxygen saturation and low respiratory rate is an uncommon pattern. Verify vital sign accuracy.",
                        actionLabel: nil
                    ))
                }
            }
        }

        // Chief complaint is very short or vague
        if intake.chiefComplaint.count < 5 && !intake.chiefComplaint.isEmpty {
            alerts.append(SafetyAlert(
                severity: .info,
                category: .inputRobustness,
                title: "Brief Chief Complaint",
                message: "A more detailed chief complaint helps improve diagnostic accuracy. Consider adding onset, location, and characteristics.",
                actionLabel: nil
            ))
        }

        return alerts
    }
}

// MARK: - Safety Alert Model

struct SafetyAlert: Identifiable, Codable, Equatable, Sendable {
    let id: UUID
    var severity: Severity
    var category: Category
    var title: String
    var message: String
    var actionLabel: String?

    enum Severity: String, Codable, Sendable, Comparable {
        case critical = "Critical"
        case warning = "Warning"
        case info = "Info"

        var sortOrder: Int {
            switch self {
            case .critical: return 0
            case .warning: return 1
            case .info: return 2
            }
        }

        static func < (lhs: Severity, rhs: Severity) -> Bool {
            lhs.sortOrder < rhs.sortOrder
        }
    }

    enum Category: String, Codable, Sendable {
        case emergencyEscalation = "Emergency"
        case redFlagSymptom = "Red Flag"
        case criticalVital = "Vital Sign"
        case medicationInteraction = "Medication"
        case confidenceCalibration = "Confidence"
        case demographicBias = "Demographic"
        case pregnancyRisk = "Pregnancy"
        case inputRobustness = "Input Quality"
    }

    init(
        id: UUID = UUID(),
        severity: Severity,
        category: Category,
        title: String,
        message: String,
        actionLabel: String? = nil
    ) {
        self.id = id
        self.severity = severity
        self.category = category
        self.title = title
        self.message = message
        self.actionLabel = actionLabel
    }
}
