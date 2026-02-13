import Foundation
import Testing
@testable import MedStation

// MARK: - Safety Guard Tests

@Suite("Medical Safety Guard")
struct SafetyGuardTests {

    // MARK: - Helpers

    private func makeIntake(
        chiefComplaint: String = "headache",
        symptoms: [String] = [],
        age: Int? = 35,
        sex: BiologicalSex? = .male,
        isPregnant: Bool = false,
        medications: [String] = [],
        vitals: VitalSigns? = nil
    ) -> PatientIntake {
        PatientIntake(
            age: age,
            sex: sex,
            isPregnant: isPregnant,
            chiefComplaint: chiefComplaint,
            symptoms: symptoms,
            severity: .moderate,
            vitalSigns: vitals,
            currentMedications: medications
        )
    }

    private func makeResult(
        triageLevel: MedicalWorkflowResult.TriageLevel = .semiUrgent,
        diagnoses: [Diagnosis] = [],
        reasoning: [ReasoningStep] = []
    ) -> MedicalWorkflowResult {
        MedicalWorkflowResult(
            intakeId: UUID(),
            triageLevel: triageLevel,
            differentialDiagnoses: diagnoses,
            reasoning: reasoning
        )
    }

    // MARK: - 1. Emergency Escalation

    @Test("Emergency triage triggers critical alert with 911 action")
    func emergencyEscalation() {
        let result = makeResult(triageLevel: .emergency)
        let intake = makeIntake()
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let emergency = alerts.filter { $0.category == .emergencyEscalation && $0.severity == .critical }
        #expect(!emergency.isEmpty)
        #expect(emergency[0].actionLabel == "Call 911")
    }

    @Test("Acute keywords in reasoning trigger warning even if not Emergency triage")
    func acuteKeywordsWarning() {
        let reasoning = [ReasoningStep(step: 1, title: "Analysis", content: "Consider stroke as a differential")]
        let result = makeResult(triageLevel: .urgent, reasoning: reasoning)
        let intake = makeIntake()
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let escalation = alerts.filter { $0.category == .emergencyEscalation && $0.severity == .warning }
        #expect(!escalation.isEmpty)
        #expect(escalation[0].message.contains("stroke"))
    }

    // MARK: - 2. Red Flag Symptoms

    @Test("Chest pain triggers red flag alert")
    func chestPainRedFlag() {
        let intake = makeIntake(chiefComplaint: "severe chest pain")
        let result = makeResult()
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let redFlags = alerts.filter { $0.category == .redFlagSymptom }
        #expect(!redFlags.isEmpty)
        #expect(redFlags.contains { $0.title.lowercased().contains("chest pain") })
    }

    @Test("Worst headache triggers red flag")
    func worstHeadacheRedFlag() {
        let intake = makeIntake(chiefComplaint: "worst headache of my life")
        let result = makeResult()
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let redFlags = alerts.filter { $0.category == .redFlagSymptom }
        #expect(!redFlags.isEmpty)
    }

    @Test("No red flags for mild symptoms")
    func noRedFlags() {
        let intake = makeIntake(chiefComplaint: "mild runny nose")
        let result = makeResult()
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let redFlags = alerts.filter { $0.category == .redFlagSymptom }
        #expect(redFlags.isEmpty)
    }

    // MARK: - 3. Critical Vitals

    @Test("SpO2 below 90 triggers critical alert")
    func criticalSpO2() {
        let vitals = VitalSigns(oxygenSaturation: 85)
        let intake = makeIntake(vitals: vitals)
        let result = makeResult()
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let vitalAlerts = alerts.filter { $0.category == .criticalVital && $0.severity == .critical }
        #expect(!vitalAlerts.isEmpty)
        #expect(vitalAlerts.contains { $0.title.contains("SpO2") })
    }

    @Test("Temperature 104+ triggers critical hyperpyrexia alert")
    func criticalTemperature() {
        let vitals = VitalSigns(temperature: 105.0)
        let intake = makeIntake(vitals: vitals)
        let result = makeResult()
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let vitalAlerts = alerts.filter { $0.category == .criticalVital && $0.severity == .critical }
        #expect(vitalAlerts.contains { $0.title.contains("Hyperpyrexia") })
    }

    @Test("Adult tachycardia > 150 triggers critical alert")
    func adultTachycardia() {
        let vitals = VitalSigns(heartRate: 160)
        let intake = makeIntake(age: 40, vitals: vitals)
        let result = makeResult()
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let vitalAlerts = alerts.filter { $0.category == .criticalVital && $0.severity == .critical }
        #expect(!vitalAlerts.isEmpty)
    }

    @Test("Normal vitals produce no vital alerts")
    func normalVitals() {
        let vitals = VitalSigns(heartRate: 72, temperature: 98.6, oxygenSaturation: 98)
        let intake = makeIntake(vitals: vitals)
        let result = makeResult()
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let vitalAlerts = alerts.filter { $0.category == .criticalVital }
        #expect(vitalAlerts.isEmpty)
    }

    // MARK: - 4. Drug Interactions

    @Test("SSRI + tramadol triggers serotonin syndrome warning")
    func serotoninSyndrome() {
        let intake = makeIntake(medications: ["sertraline", "tramadol"])
        let result = makeResult()
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let drugAlerts = alerts.filter { $0.category == .medicationInteraction }
        #expect(!drugAlerts.isEmpty)
        #expect(drugAlerts.contains { $0.message.lowercased().contains("serotonin") })
    }

    @Test("PDE5 inhibitor + nitrate triggers critical contraindication")
    func pde5NitrateContraindication() {
        let intake = makeIntake(medications: ["sildenafil", "nitroglycerin"])
        let result = makeResult()
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let critical = alerts.filter { $0.category == .medicationInteraction && $0.severity == .critical }
        #expect(!critical.isEmpty)
        #expect(critical.contains { $0.message.lowercased().contains("hypotension") })
    }

    @Test("No interactions for safe med combo")
    func safeMedications() {
        let intake = makeIntake(medications: ["acetaminophen", "omeprazole"])
        let result = makeResult()
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let drugAlerts = alerts.filter { $0.category == .medicationInteraction }
        #expect(drugAlerts.isEmpty)
    }

    // MARK: - 5. Confidence Calibration

    @Test("Single diagnosis triggers anchoring risk alert")
    func singleDiagnosisAnchoring() {
        let dx = [Diagnosis(condition: "Appendicitis", probability: 0.9, rationale: "Classic presentation")]
        let result = makeResult(diagnoses: dx)
        let intake = makeIntake()
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let confidence = alerts.filter { $0.category == .confidenceCalibration }
        #expect(confidence.contains { $0.title.contains("Anchoring") })
    }

    @Test("Similar probabilities trigger low confidence alert")
    func lowConfidence() {
        let dx = [
            Diagnosis(condition: "A", probability: 0.4, rationale: ""),
            Diagnosis(condition: "B", probability: 0.35, rationale: ""),
            Diagnosis(condition: "C", probability: 0.38, rationale: ""),
        ]
        let result = makeResult(diagnoses: dx)
        let intake = makeIntake()
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let confidence = alerts.filter { $0.category == .confidenceCalibration }
        #expect(confidence.contains { $0.title.contains("Low Diagnostic Confidence") })
    }

    // MARK: - 6. Demographic Bias Detection

    @Test("Female chest pain triggers bias awareness alert")
    func femaleChestPainBias() {
        let intake = makeIntake(chiefComplaint: "chest pain", sex: .female)
        let result = makeResult(triageLevel: .semiUrgent)
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let bias = alerts.filter { $0.category == .demographicBias }
        #expect(bias.contains { $0.title.contains("Chest Pain in Women") })
    }

    @Test("Male patient with ovarian condition triggers sex mismatch")
    func sexConditionMismatch() {
        let dx = [Diagnosis(condition: "Ovarian cyst", probability: 0.6, rationale: "")]
        let intake = makeIntake(sex: .male)
        let result = makeResult(diagnoses: dx)
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let bias = alerts.filter { $0.category == .demographicBias }
        #expect(bias.contains { $0.title.contains("Sex-Condition Mismatch") })
    }

    // MARK: - 7. Pregnancy Risks

    @Test("Pregnant patient with hypertension triggers preeclampsia alert")
    func preeclampsiaRisk() {
        let vitals = VitalSigns(bloodPressure: "160/95")
        let intake = makeIntake(isPregnant: true, vitals: vitals)
        let result = makeResult()
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let pregnancy = alerts.filter { $0.category == .pregnancyRisk }
        #expect(pregnancy.contains { $0.title.contains("Preeclampsia") })
    }

    @Test("Non-pregnant patient has no pregnancy alerts")
    func noPregnancyAlerts() {
        let intake = makeIntake(isPregnant: false)
        let result = makeResult()
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let pregnancy = alerts.filter { $0.category == .pregnancyRisk }
        #expect(pregnancy.isEmpty)
    }

    // MARK: - 8. Input Robustness

    @Test("20+ symptoms triggers high symptom count warning")
    func highSymptomCount() {
        let symptoms = (1...25).map { "symptom\($0)" }
        let intake = makeIntake(symptoms: symptoms)
        let result = makeResult()
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let input = alerts.filter { $0.category == .inputRobustness }
        #expect(input.contains { $0.title.contains("High Symptom Count") })
    }

    @Test("Brief chief complaint triggers warning")
    func briefComplaint() {
        let intake = makeIntake(chiefComplaint: "ache")
        let result = makeResult()
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let input = alerts.filter { $0.category == .inputRobustness }
        #expect(input.contains { $0.title.contains("Brief Chief Complaint") })
    }

    // MARK: - 9. Clinical Guidelines

    @Test("Chest pain diagnosis triggers AHA guideline reference")
    func guidelineReference() {
        let dx = [Diagnosis(condition: "Acute Coronary Syndrome", probability: 0.7, rationale: "")]
        let result = makeResult(diagnoses: dx)
        let intake = makeIntake()
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        let guidelines = alerts.filter { $0.category == .guidelineReference }
        #expect(guidelines.contains { $0.title.contains("Chest Pain") })
    }

    // MARK: - Alert Ordering

    @Test("Alerts sorted by severity: critical first, info last")
    func alertSorting() {
        // Emergency + critical vitals + guideline = critical, warning, info mix
        let vitals = VitalSigns(oxygenSaturation: 85)
        let dx = [Diagnosis(condition: "Pneumonia", probability: 0.8, rationale: "")]
        let intake = makeIntake(chiefComplaint: "difficulty breathing", vitals: vitals)
        let result = makeResult(triageLevel: .emergency, diagnoses: dx)
        let alerts = MedicalSafetyGuard.validate(result, intake: intake)

        // Verify sorted: all critical before warning, all warning before info
        var seenWarning = false
        var seenInfo = false
        for alert in alerts {
            if alert.severity == .critical {
                #expect(!seenWarning && !seenInfo, "Critical alert appeared after warning/info")
            } else if alert.severity == .warning {
                seenWarning = true
                #expect(!seenInfo, "Warning alert appeared after info")
            } else {
                seenInfo = true
            }
        }
    }
}
