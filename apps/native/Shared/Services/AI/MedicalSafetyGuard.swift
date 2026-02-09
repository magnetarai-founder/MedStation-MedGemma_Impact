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

        // 3. Vital sign critical values
        if let vitals = intake.vitalSigns {
            alerts.append(contentsOf: checkCriticalVitals(vitals))
        }

        // 4. High-risk medication interactions
        if !intake.currentMedications.isEmpty {
            alerts.append(contentsOf: checkMedicationRisks(intake.currentMedications, diagnoses: result.differentialDiagnoses))
        }

        // 5. Confidence calibration warnings
        alerts.append(contentsOf: checkConfidenceCalibration(result))

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
                actionLabel: nil
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

    private static func checkCriticalVitals(_ vitals: VitalSigns) -> [SafetyAlert] {
        var alerts: [SafetyAlert] = []

        if let hr = vitals.heartRate {
            if hr > 150 || hr < 40 {
                alerts.append(SafetyAlert(
                    severity: .critical,
                    category: .criticalVital,
                    title: "Critical Heart Rate: \(hr) bpm",
                    message: hr > 150 ? "Tachycardia >150 bpm may indicate cardiac emergency" : "Bradycardia <40 bpm may indicate heart block",
                    actionLabel: nil
                ))
            } else if hr > 120 || hr < 50 {
                alerts.append(SafetyAlert(
                    severity: .warning,
                    category: .criticalVital,
                    title: "Abnormal Heart Rate: \(hr) bpm",
                    message: "Heart rate outside normal range (60-100 bpm). Clinical correlation recommended.",
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
                    actionLabel: nil
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
                    actionLabel: nil
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
                    actionLabel: nil
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
