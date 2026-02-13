import Testing
@testable import MedStation

// MARK: - Triage Level Parser Tests

@Suite("Triage Level Parser")
struct TriageParserTests {

    // MARK: - Structured "TRIAGE: <level>" format

    @Test("Parses TRIAGE: Emergency")
    func triageEmergency() {
        let result = MedicalWorkflowEngine.extractTriageLevel(from: "TRIAGE: Emergency\nPatient needs immediate care.")
        #expect(result == .emergency)
    }

    @Test("Parses TRIAGE: Urgent")
    func triageUrgent() {
        let result = MedicalWorkflowEngine.extractTriageLevel(from: "TRIAGE: Urgent\nSeek care within 2-4 hours.")
        #expect(result == .urgent)
    }

    @Test("Parses TRIAGE: Semi-Urgent")
    func triageSemiUrgent() {
        let result = MedicalWorkflowEngine.extractTriageLevel(from: "TRIAGE: Semi-Urgent\nSee doctor within 24 hours.")
        #expect(result == .semiUrgent)
    }

    @Test("Parses TRIAGE: Non-Urgent")
    func triageNonUrgent() {
        let result = MedicalWorkflowEngine.extractTriageLevel(from: "TRIAGE: Non-Urgent\nSchedule appointment.")
        #expect(result == .nonUrgent)
    }

    @Test("Parses TRIAGE: Self-Care")
    func triageSelfCare() {
        let result = MedicalWorkflowEngine.extractTriageLevel(from: "TRIAGE: Self-Care\nMonitor at home.")
        #expect(result == .selfCare)
    }

    // MARK: - Case insensitivity

    @Test("Handles lowercase triage prefix")
    func triageLowercase() {
        let result = MedicalWorkflowEngine.extractTriageLevel(from: "triage: emergency\nDetails...")
        #expect(result == .emergency)
    }

    @Test("Handles mixed case")
    func triageMixedCase() {
        let result = MedicalWorkflowEngine.extractTriageLevel(from: "Triage: URGENT\nDetails...")
        #expect(result == .urgent)
    }

    // MARK: - Alternative format: "Triage Level:"

    @Test("Parses 'Triage Level:' format")
    func triageLevelPrefix() {
        let result = MedicalWorkflowEngine.extractTriageLevel(from: "Triage Level: Non-Urgent\nPatient stable.")
        #expect(result == .nonUrgent)
    }

    // MARK: - Fallback: line starts with level name

    @Test("Fallback parses line starting with Emergency")
    func fallbackEmergency() {
        let result = MedicalWorkflowEngine.extractTriageLevel(from: "Emergency — life-threatening presentation")
        #expect(result == .emergency)
    }

    @Test("Fallback parses Self Care (no hyphen)")
    func fallbackSelfCareNoHyphen() {
        let result = MedicalWorkflowEngine.extractTriageLevel(from: "Self Care recommended for this patient")
        #expect(result == .selfCare)
    }

    // MARK: - Default behavior

    @Test("Defaults to Semi-Urgent when unparseable")
    func defaultsSemiUrgent() {
        let result = MedicalWorkflowEngine.extractTriageLevel(from: "The patient presents with mild symptoms and should monitor.")
        #expect(result == .semiUrgent)
    }

    @Test("Defaults on empty input")
    func defaultsOnEmpty() {
        let result = MedicalWorkflowEngine.extractTriageLevel(from: "")
        #expect(result == .semiUrgent)
    }

    // MARK: - Only parses first 3 lines

    @Test("Ignores triage level after line 3")
    func ignoresAfterLine3() {
        let text = """
        Some intro text
        More analysis
        Additional context
        TRIAGE: Emergency
        """
        let result = MedicalWorkflowEngine.extractTriageLevel(from: text)
        // Emergency is on line 4, should be ignored → defaults to semiUrgent
        #expect(result == .semiUrgent)
    }

    // MARK: - Urgent vs Semi-Urgent ordering

    @Test("Semi-Urgent matched before Urgent when both substrings present")
    func semiUrgentBeforeUrgent() {
        // "Semi-Urgent" contains "Urgent" as a substring — verify correct matching
        let result = MedicalWorkflowEngine.extractTriageLevel(from: "TRIAGE: Semi-Urgent")
        #expect(result == .semiUrgent)
    }
}

// MARK: - Differential Diagnosis Parser Tests

@Suite("Differential Diagnosis Parser")
struct DiagnosisParserTests {

    @Test("Parses numbered diagnoses")
    func numberedList() {
        let text = """
        1. Acute Appendicitis (high likelihood) — Right lower quadrant pain with rebound tenderness
        2. Viral Gastroenteritis (medium likelihood) — Recent contact with sick individuals
        3. Urinary Tract Infection (low likelihood) — Mild dysuria reported
        """
        let diagnoses = MedicalWorkflowEngine.parseDifferentialDiagnoses(from: text)
        #expect(diagnoses.count == 3)
        #expect(diagnoses[0].condition.contains("Acute Appendicitis"))
        #expect(diagnoses[0].probability == 0.8) // "high"
        #expect(diagnoses[1].probability == 0.5) // "medium"
        #expect(diagnoses[2].probability == 0.2) // "low"
    }

    @Test("Parses bulleted diagnoses with dashes")
    func bulletedList() {
        let text = """
        - Migraine (most likely) — Unilateral headache with photophobia
        - Tension headache (possible) — Bilateral pressure
        """
        let diagnoses = MedicalWorkflowEngine.parseDifferentialDiagnoses(from: text)
        #expect(diagnoses.count == 2)
        #expect(diagnoses[0].probability == 0.8) // "most likely"
        #expect(diagnoses[1].probability == 0.5) // "possible"
    }

    @Test("Caps at 5 diagnoses")
    func capsAtFive() {
        let text = (1...8).map { "\($0). Condition \($0) (medium)" }.joined(separator: "\n")
        let diagnoses = MedicalWorkflowEngine.parseDifferentialDiagnoses(from: text)
        #expect(diagnoses.count == 5)
    }

    @Test("Extracts rationale after separator")
    func extractsRationale() {
        let text = "1. Pneumonia: Productive cough with fever and consolidation on exam"
        let diagnoses = MedicalWorkflowEngine.parseDifferentialDiagnoses(from: text)
        #expect(diagnoses.count == 1)
        #expect(diagnoses[0].condition == "Pneumonia")
        #expect(diagnoses[0].rationale.contains("Productive cough"))
    }

    @Test("Returns empty for no list items")
    func emptyOnNoList() {
        let text = "The patient likely has a common cold. Monitor symptoms."
        let diagnoses = MedicalWorkflowEngine.parseDifferentialDiagnoses(from: text)
        #expect(diagnoses.isEmpty)
    }
}

// MARK: - Recommended Actions Parser Tests

@Suite("Recommended Actions Parser")
struct ActionParserTests {

    @Test("Parses numbered actions")
    func numberedActions() {
        let text = """
        1. Seek immediate emergency care at the nearest ER
        2. Get a complete blood count today
        3. Monitor temperature every 4 hours
        """
        let actions = MedicalWorkflowEngine.parseRecommendedActions(from: text, triageLevel: .semiUrgent)
        #expect(actions.count == 3)
    }

    @Test("Emergency triage sets all actions to immediate priority")
    func emergencyPriority() {
        let text = "1. Call 911\n2. Start CPR\n3. Use AED"
        let actions = MedicalWorkflowEngine.parseRecommendedActions(from: text, triageLevel: .emergency)
        for action in actions {
            #expect(action.priority == .immediate)
        }
    }

    @Test("Detects urgent keywords")
    func urgentKeywords() {
        let text = "1. Visit urgent care today for evaluation"
        let actions = MedicalWorkflowEngine.parseRecommendedActions(from: text, triageLevel: .nonUrgent)
        #expect(actions[0].priority == .high)
    }

    @Test("Detects monitor/follow-up as low priority")
    func monitorKeywords() {
        let text = "1. Monitor symptoms at home and follow up in one week"
        let actions = MedicalWorkflowEngine.parseRecommendedActions(from: text, triageLevel: .selfCare)
        #expect(actions[0].priority == .low)
    }

    @Test("Skips non-list lines")
    func skipsNonList() {
        let text = """
        Based on the assessment:
        1. Take ibuprofen for pain
        The patient should also rest.
        """
        let actions = MedicalWorkflowEngine.parseRecommendedActions(from: text, triageLevel: .nonUrgent)
        #expect(actions.count == 1)
    }
}
