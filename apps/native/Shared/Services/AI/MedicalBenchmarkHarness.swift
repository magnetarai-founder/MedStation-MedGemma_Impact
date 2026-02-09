//
//  MedicalBenchmarkHarness.swift
//  MagnetarStudio
//
//  Automated evaluation harness for MedGemma medical triage accuracy.
//  Runs clinically validated vignettes through the full 5-step workflow
//  and scores against expected outcomes across three dimensions:
//  triage accuracy, diagnosis recall, and safety alert coverage.
//
//  MedGemma Impact Challenge (Kaggle 2026) — Evaluation & Benchmarking.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "MedicalBenchmark")

// MARK: - Benchmark Vignette

struct BenchmarkVignette: Identifiable, Sendable {
    let id: UUID
    let name: String
    let category: String
    let intake: PatientIntake
    let expectedTriage: MedicalWorkflowResult.TriageLevel
    let expectedDiagnosisKeywords: [String]
    let expectedSafetyCategories: Set<SafetyAlert.Category>

    init(
        id: UUID = UUID(),
        name: String,
        category: String,
        intake: PatientIntake,
        expectedTriage: MedicalWorkflowResult.TriageLevel,
        expectedDiagnosisKeywords: [String],
        expectedSafetyCategories: Set<SafetyAlert.Category>
    ) {
        self.id = id
        self.name = name
        self.category = category
        self.intake = intake
        self.expectedTriage = expectedTriage
        self.expectedDiagnosisKeywords = expectedDiagnosisKeywords
        self.expectedSafetyCategories = expectedSafetyCategories
    }
}

// MARK: - Benchmark Result (per-vignette)

struct BenchmarkVignetteResult: Identifiable, Codable, Sendable {
    let id: UUID
    let vignetteName: String
    let vignetteCategory: String

    // Triage scoring
    let expectedTriage: String
    let actualTriage: String
    let triageScore: Double           // 1.0 = exact, 0.5 = adjacent, 0.0 = wrong

    // Diagnosis scoring
    let expectedKeywords: [String]
    let matchedKeywords: [String]
    let diagnosisRecall: Double       // matched / expected

    // Safety scoring
    let expectedSafetyCategories: [String]
    let triggeredSafetyCategories: [String]
    let safetyCoverage: Double        // matched / expected

    // Performance
    let workflowDurationMs: Double
    let stepCount: Int
    let diagnosisCount: Int
    let safetyAlertCount: Int

    // Overall
    var compositeScore: Double {
        // Weighted: triage 40%, diagnosis 35%, safety 25%
        triageScore * 0.40 + diagnosisRecall * 0.35 + safetyCoverage * 0.25
    }

    var passed: Bool { compositeScore >= 0.5 }

    init(
        id: UUID = UUID(),
        vignetteName: String,
        vignetteCategory: String,
        expectedTriage: String,
        actualTriage: String,
        triageScore: Double,
        expectedKeywords: [String],
        matchedKeywords: [String],
        diagnosisRecall: Double,
        expectedSafetyCategories: [String],
        triggeredSafetyCategories: [String],
        safetyCoverage: Double,
        workflowDurationMs: Double,
        stepCount: Int,
        diagnosisCount: Int,
        safetyAlertCount: Int
    ) {
        self.id = id
        self.vignetteName = vignetteName
        self.vignetteCategory = vignetteCategory
        self.expectedTriage = expectedTriage
        self.actualTriage = actualTriage
        self.triageScore = triageScore
        self.expectedKeywords = expectedKeywords
        self.matchedKeywords = matchedKeywords
        self.diagnosisRecall = diagnosisRecall
        self.expectedSafetyCategories = expectedSafetyCategories
        self.triggeredSafetyCategories = triggeredSafetyCategories
        self.safetyCoverage = safetyCoverage
        self.workflowDurationMs = workflowDurationMs
        self.stepCount = stepCount
        self.diagnosisCount = diagnosisCount
        self.safetyAlertCount = safetyAlertCount
    }
}

// MARK: - Benchmark Report (aggregate)

struct BenchmarkReport: Identifiable, Codable, Sendable {
    let id: UUID
    let timestamp: Date
    let modelName: String
    let vignetteCount: Int
    let results: [BenchmarkVignetteResult]

    // Aggregate metrics
    let triageAccuracy: Double
    let meanDiagnosisRecall: Double
    let meanSafetyCoverage: Double
    let meanCompositeScore: Double
    let totalDurationMs: Double
    let meanWorkflowMs: Double

    // Confusion matrix (flattened)
    let triageConfusion: [String: [String: Int]]

    var passRate: Double {
        guard vignetteCount > 0 else { return 0 }
        return Double(results.filter(\.passed).count) / Double(vignetteCount)
    }

    init(
        id: UUID = UUID(),
        timestamp: Date = Date(),
        modelName: String = "alibayram/medgemma:4b",
        results: [BenchmarkVignetteResult],
        totalDurationMs: Double,
        triageConfusion: [String: [String: Int]]
    ) {
        self.id = id
        self.timestamp = timestamp
        self.modelName = modelName
        self.vignetteCount = results.count
        self.results = results
        self.totalDurationMs = totalDurationMs
        self.triageConfusion = triageConfusion

        let scores = results.map(\.triageScore)
        self.triageAccuracy = scores.isEmpty ? 0 : scores.reduce(0, +) / Double(scores.count)

        let recalls = results.map(\.diagnosisRecall)
        self.meanDiagnosisRecall = recalls.isEmpty ? 0 : recalls.reduce(0, +) / Double(recalls.count)

        let coverages = results.map(\.safetyCoverage)
        self.meanSafetyCoverage = coverages.isEmpty ? 0 : coverages.reduce(0, +) / Double(coverages.count)

        let composites = results.map(\.compositeScore)
        self.meanCompositeScore = composites.isEmpty ? 0 : composites.reduce(0, +) / Double(composites.count)

        let durations = results.map(\.workflowDurationMs)
        self.meanWorkflowMs = durations.isEmpty ? 0 : durations.reduce(0, +) / Double(durations.count)
    }
}

// MARK: - Benchmark Harness

@MainActor
@Observable
final class MedicalBenchmarkHarness {

    // MARK: - State

    var isRunning = false
    var currentVignetteIndex = 0
    var currentVignetteName = ""
    var report: BenchmarkReport?
    var error: String?

    private var runTask: Task<Void, Never>?

    // MARK: - Run Benchmark

    func run() {
        guard !isRunning else { return }
        isRunning = true
        error = nil
        report = nil
        currentVignetteIndex = 0

        runTask = Task {
            do {
                let benchmarkReport = try await executeBenchmark()
                self.report = benchmarkReport
                saveBenchmarkReport(benchmarkReport)
                logger.info("Benchmark complete: \(benchmarkReport.vignetteCount) vignettes, composite=\(String(format: "%.1f%%", benchmarkReport.meanCompositeScore * 100))")
            } catch is CancellationError {
                logger.info("Benchmark cancelled by user")
            } catch {
                self.error = error.localizedDescription
                logger.error("Benchmark failed: \(error)")
            }
            self.isRunning = false
        }
    }

    func cancel() {
        runTask?.cancel()
        runTask = nil
        isRunning = false
    }

    // MARK: - Core Execution

    private func executeBenchmark() async throws -> BenchmarkReport {
        let vignettes = Self.clinicalVignettes
        var results: [BenchmarkVignetteResult] = []
        var confusion: [String: [String: Int]] = [:]
        let benchmarkStart = ContinuousClock.now

        for (index, vignette) in vignettes.enumerated() {
            try Task.checkCancellation()
            currentVignetteIndex = index
            currentVignetteName = vignette.name
            logger.info("Running vignette \(index + 1)/\(vignettes.count): \(vignette.name)")

            let result = try await runSingleVignette(vignette)
            results.append(result)

            // Update confusion matrix
            let expected = result.expectedTriage
            let actual = result.actualTriage
            if confusion[expected] == nil { confusion[expected] = [:] }
            confusion[expected]?[actual, default: 0] += 1
        }

        let elapsed = benchmarkStart.duration(to: .now)
        let totalMs = Double(elapsed.components.seconds) * 1000
            + Double(elapsed.components.attoseconds) / 1_000_000_000_000_000

        return BenchmarkReport(
            results: results,
            totalDurationMs: totalMs,
            triageConfusion: confusion
        )
    }

    private func runSingleVignette(_ vignette: BenchmarkVignette) async throws -> BenchmarkVignetteResult {
        let workflowResult = try await MedicalWorkflowEngine.executeWorkflow(
            intake: vignette.intake,
            disclaimerConfirmed: true,
            onProgress: { _ in }
        )

        // Score triage
        let triageScore = Self.scoreTriage(
            expected: vignette.expectedTriage,
            actual: workflowResult.triageLevel
        )

        // Score diagnoses (keyword recall)
        let diagnosisText = workflowResult.differentialDiagnoses
            .map { $0.condition.lowercased() }
            .joined(separator: " ")
        let reasoningText = workflowResult.reasoning
            .map { $0.content.lowercased() }
            .joined(separator: " ")
        let searchText = diagnosisText + " " + reasoningText

        let matched = vignette.expectedDiagnosisKeywords.filter { keyword in
            searchText.contains(keyword.lowercased())
        }
        let diagnosisRecall = vignette.expectedDiagnosisKeywords.isEmpty
            ? 1.0
            : Double(matched.count) / Double(vignette.expectedDiagnosisKeywords.count)

        // Score safety coverage
        let triggeredCategories = Set(workflowResult.safetyAlerts.map(\.category))
        let expectedHit = vignette.expectedSafetyCategories.filter { triggeredCategories.contains($0) }
        let safetyCoverage = vignette.expectedSafetyCategories.isEmpty
            ? 1.0
            : Double(expectedHit.count) / Double(vignette.expectedSafetyCategories.count)

        return BenchmarkVignetteResult(
            vignetteName: vignette.name,
            vignetteCategory: vignette.category,
            expectedTriage: vignette.expectedTriage.rawValue,
            actualTriage: workflowResult.triageLevel.rawValue,
            triageScore: triageScore,
            expectedKeywords: vignette.expectedDiagnosisKeywords,
            matchedKeywords: matched,
            diagnosisRecall: diagnosisRecall,
            expectedSafetyCategories: vignette.expectedSafetyCategories.map(\.rawValue),
            triggeredSafetyCategories: triggeredCategories.map(\.rawValue),
            safetyCoverage: safetyCoverage,
            workflowDurationMs: workflowResult.performanceMetrics?.totalWorkflowMs ?? 0,
            stepCount: workflowResult.reasoning.count,
            diagnosisCount: workflowResult.differentialDiagnoses.count,
            safetyAlertCount: workflowResult.safetyAlerts.count
        )
    }

    // MARK: - Scoring Helpers

    private static func scoreTriage(
        expected: MedicalWorkflowResult.TriageLevel,
        actual: MedicalWorkflowResult.TriageLevel
    ) -> Double {
        if expected == actual { return 1.0 }

        // Adjacent levels get partial credit
        let ordered: [MedicalWorkflowResult.TriageLevel] = [
            .emergency, .urgent, .semiUrgent, .nonUrgent, .selfCare
        ]
        guard let expectedIdx = ordered.firstIndex(of: expected),
              let actualIdx = ordered.firstIndex(of: actual) else { return 0 }

        let distance = abs(expectedIdx - actualIdx)
        if distance == 1 { return 0.5 }
        return 0
    }

    // MARK: - Persistence

    private func saveBenchmarkReport(_ report: BenchmarkReport) {
        let dir = (FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory)
            .appendingPathComponent("MagnetarStudio/workspace/medical/benchmarks", isDirectory: true)
        PersistenceHelpers.ensureDirectory(at: dir, label: "benchmark reports")
        let file = dir.appendingPathComponent("benchmark-\(report.id.uuidString.prefix(8)).json")
        PersistenceHelpers.save(report, to: file, label: "benchmark report")
    }

    static func loadLatestReport() -> BenchmarkReport? {
        let dir = (FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory)
            .appendingPathComponent("MagnetarStudio/workspace/medical/benchmarks", isDirectory: true)
        let files: [URL]
        do {
            files = try FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: [.contentModificationDateKey])
                .filter { $0.pathExtension == "json" }
                .sorted { a, b in
                    let aDate = (try? a.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
                    let bDate = (try? b.resourceValues(forKeys: [.contentModificationDateKey]).contentModificationDate) ?? .distantPast
                    return aDate > bDate
                }
        } catch {
            logger.debug("No benchmark reports found: \(error.localizedDescription)")
            return nil
        }
        guard let latest = files.first else { return nil }
        return PersistenceHelpers.load(BenchmarkReport.self, from: latest, label: "benchmark report")
    }

    // MARK: - Clinical Vignettes

    static let clinicalVignettes: [BenchmarkVignette] = [
        // 1. STEMI — Emergency, Cardiology
        BenchmarkVignette(
            name: "Acute STEMI",
            category: "Cardiology",
            intake: PatientIntake(
                patientId: "BENCH-001",
                age: 62,
                sex: .male,
                chiefComplaint: "Crushing chest pain radiating to left arm and jaw, sudden onset 30 minutes ago, with diaphoresis",
                symptoms: ["chest pain", "left arm pain", "jaw pain", "diaphoresis", "nausea", "shortness of breath"],
                onsetTime: "30 minutes ago",
                severity: .critical,
                vitalSigns: VitalSigns(heartRate: 115, bloodPressure: "165/100", temperature: 98.4, respiratoryRate: 24, oxygenSaturation: 93),
                medicalHistory: ["Hypertension", "Hyperlipidemia", "Smoking 30 pack-years"],
                currentMedications: ["Lisinopril", "Atorvastatin"],
                allergies: []
            ),
            expectedTriage: .emergency,
            expectedDiagnosisKeywords: ["myocardial infarction", "acute coronary", "stemi", "heart attack", "angina"],
            expectedSafetyCategories: [.emergencyEscalation, .criticalVital, .redFlagSymptom]
        ),

        // 2. Acute Ischemic Stroke — Emergency, Neurology
        BenchmarkVignette(
            name: "Acute Ischemic Stroke",
            category: "Neurology",
            intake: PatientIntake(
                patientId: "BENCH-002",
                age: 71,
                sex: .female,
                chiefComplaint: "Sudden left-sided weakness and facial droop with slurred speech, onset 45 minutes ago",
                symptoms: ["left arm weakness", "left leg weakness", "facial droop", "slurred speech", "confusion"],
                onsetTime: "45 minutes ago",
                severity: .critical,
                vitalSigns: VitalSigns(heartRate: 88, bloodPressure: "185/105", temperature: 98.2, respiratoryRate: 18, oxygenSaturation: 97),
                medicalHistory: ["Atrial fibrillation", "Type 2 Diabetes", "Previous TIA"],
                currentMedications: ["Warfarin", "Metformin", "Metoprolol"],
                allergies: ["Sulfa drugs"]
            ),
            expectedTriage: .emergency,
            expectedDiagnosisKeywords: ["stroke", "cerebrovascular", "ischemic", "tia", "transient ischemic"],
            expectedSafetyCategories: [.emergencyEscalation, .redFlagSymptom, .medicationInteraction]
        ),

        // 3. Anaphylaxis — Emergency, Allergy/Immunology
        BenchmarkVignette(
            name: "Anaphylaxis",
            category: "Allergy",
            intake: PatientIntake(
                patientId: "BENCH-003",
                age: 28,
                sex: .male,
                chiefComplaint: "Severe allergic reaction after eating peanuts — throat swelling, hives, difficulty breathing",
                symptoms: ["throat swelling", "difficulty breathing", "hives", "itching", "lightheadedness", "abdominal cramps"],
                onsetTime: "15 minutes ago",
                severity: .critical,
                vitalSigns: VitalSigns(heartRate: 130, bloodPressure: "85/55", temperature: 98.6, respiratoryRate: 28, oxygenSaturation: 91),
                medicalHistory: ["Peanut allergy", "Asthma"],
                currentMedications: ["Albuterol inhaler"],
                allergies: ["Peanuts"]
            ),
            expectedTriage: .emergency,
            expectedDiagnosisKeywords: ["anaphylaxis", "allergic reaction", "angioedema", "anaphylactic"],
            expectedSafetyCategories: [.emergencyEscalation, .criticalVital, .redFlagSymptom]
        ),

        // 4. Community-Acquired Pneumonia — Urgent, Pulmonology
        BenchmarkVignette(
            name: "Community-Acquired Pneumonia",
            category: "Pulmonology",
            intake: PatientIntake(
                patientId: "BENCH-004",
                age: 52,
                sex: .female,
                chiefComplaint: "Productive cough with rust-colored sputum, fever, and right-sided chest pain for 3 days",
                symptoms: ["productive cough", "fever", "chest pain", "shortness of breath", "fatigue", "chills"],
                onsetTime: "3 days ago",
                severity: .severe,
                vitalSigns: VitalSigns(heartRate: 102, bloodPressure: "128/78", temperature: 102.4, respiratoryRate: 24, oxygenSaturation: 93),
                medicalHistory: ["COPD", "Former smoker"],
                currentMedications: ["Tiotropium", "Albuterol"],
                allergies: ["Penicillin"]
            ),
            expectedTriage: .urgent,
            expectedDiagnosisKeywords: ["pneumonia", "community-acquired", "respiratory infection", "bronchitis"],
            expectedSafetyCategories: [.criticalVital, .redFlagSymptom]
        ),

        // 5. Acute Appendicitis — Urgent, General Surgery
        BenchmarkVignette(
            name: "Acute Appendicitis",
            category: "Surgery",
            intake: PatientIntake(
                patientId: "BENCH-005",
                age: 16,
                sex: .male,
                chiefComplaint: "Right lower quadrant abdominal pain that started around the umbilicus and migrated, with nausea and low-grade fever",
                symptoms: ["abdominal pain", "nausea", "loss of appetite", "low-grade fever", "rebound tenderness"],
                onsetTime: "12 hours ago",
                severity: .severe,
                vitalSigns: VitalSigns(heartRate: 96, bloodPressure: "118/72", temperature: 100.8, respiratoryRate: 18, oxygenSaturation: 99),
                medicalHistory: [],
                currentMedications: [],
                allergies: []
            ),
            expectedTriage: .urgent,
            expectedDiagnosisKeywords: ["appendicitis", "appendix", "peritonitis", "abdominal"],
            expectedSafetyCategories: [.redFlagSymptom]
        ),

        // 6. Diabetic Ketoacidosis (DKA) — Emergency, Endocrinology
        BenchmarkVignette(
            name: "Diabetic Ketoacidosis",
            category: "Endocrinology",
            intake: PatientIntake(
                patientId: "BENCH-006",
                age: 24,
                sex: .female,
                chiefComplaint: "Extreme thirst, frequent urination, nausea/vomiting, and fruity-smelling breath with altered consciousness",
                symptoms: ["polyuria", "polydipsia", "nausea", "vomiting", "fruity breath", "confusion", "abdominal pain", "rapid breathing"],
                onsetTime: "2 days ago, worsening",
                severity: .critical,
                vitalSigns: VitalSigns(heartRate: 120, bloodPressure: "100/60", temperature: 99.0, respiratoryRate: 32, oxygenSaturation: 97),
                medicalHistory: ["Type 1 Diabetes"],
                currentMedications: ["Insulin glargine", "Insulin lispro"],
                allergies: []
            ),
            expectedTriage: .emergency,
            expectedDiagnosisKeywords: ["diabetic ketoacidosis", "dka", "hyperglycemia", "diabetic"],
            expectedSafetyCategories: [.emergencyEscalation, .criticalVital]
        ),

        // 7. Upper Respiratory Infection — Self-Care, General Practice
        BenchmarkVignette(
            name: "Upper Respiratory Infection",
            category: "General",
            intake: PatientIntake(
                patientId: "BENCH-007",
                age: 34,
                sex: .male,
                chiefComplaint: "Runny nose, mild sore throat, and occasional cough for 2 days",
                symptoms: ["runny nose", "sore throat", "cough", "sneezing", "mild fatigue"],
                onsetTime: "2 days ago",
                severity: .mild,
                vitalSigns: VitalSigns(heartRate: 72, bloodPressure: "118/76", temperature: 99.2, respiratoryRate: 16, oxygenSaturation: 99),
                medicalHistory: [],
                currentMedications: [],
                allergies: []
            ),
            expectedTriage: .selfCare,
            expectedDiagnosisKeywords: ["upper respiratory", "common cold", "viral", "pharyngitis", "rhinitis"],
            expectedSafetyCategories: []
        ),

        // 8. Tension Headache — Non-Urgent/Self-Care, Neurology
        BenchmarkVignette(
            name: "Tension Headache",
            category: "Neurology",
            intake: PatientIntake(
                patientId: "BENCH-008",
                age: 29,
                sex: .female,
                chiefComplaint: "Bilateral pressure-like headache that worsens with stress, mild to moderate intensity, no aura or nausea",
                symptoms: ["headache", "neck tension", "stress", "mild light sensitivity"],
                onsetTime: "Since yesterday afternoon",
                severity: .mild,
                vitalSigns: VitalSigns(heartRate: 68, bloodPressure: "112/68", temperature: 98.4, respiratoryRate: 14, oxygenSaturation: 99),
                medicalHistory: ["Occasional headaches"],
                currentMedications: [],
                allergies: ["Aspirin"]
            ),
            expectedTriage: .selfCare,
            expectedDiagnosisKeywords: ["tension headache", "tension-type", "headache", "migraine"],
            expectedSafetyCategories: []
        ),

        // 9. Pediatric Asthma Exacerbation — Urgent, Pediatrics/Pulmonology
        BenchmarkVignette(
            name: "Pediatric Asthma Exacerbation",
            category: "Pediatrics",
            intake: PatientIntake(
                patientId: "BENCH-009",
                age: 7,
                sex: .male,
                chiefComplaint: "Wheezing and difficulty breathing that worsened overnight, not responding to home nebulizer",
                symptoms: ["wheezing", "difficulty breathing", "chest tightness", "cough", "accessory muscle use"],
                onsetTime: "Started yesterday, worsened overnight",
                severity: .severe,
                vitalSigns: VitalSigns(heartRate: 130, bloodPressure: "100/65", temperature: 99.0, respiratoryRate: 32, oxygenSaturation: 92),
                medicalHistory: ["Asthma (moderate persistent)", "Eczema"],
                currentMedications: ["Fluticasone inhaler", "Albuterol nebulizer"],
                allergies: ["Dust mites"]
            ),
            expectedTriage: .urgent,
            expectedDiagnosisKeywords: ["asthma", "asthma exacerbation", "bronchospasm", "reactive airway"],
            expectedSafetyCategories: [.criticalVital, .redFlagSymptom]
        ),

        // 10. Preeclampsia — Emergency, Obstetrics
        BenchmarkVignette(
            name: "Preeclampsia with Severe Features",
            category: "Obstetrics",
            intake: PatientIntake(
                patientId: "BENCH-010",
                age: 30,
                sex: .female,
                isPregnant: true,
                chiefComplaint: "Severe headache with visual changes and upper abdominal pain at 34 weeks pregnant",
                symptoms: ["severe headache", "blurred vision", "right upper quadrant pain", "nausea", "swelling"],
                onsetTime: "Started this morning",
                severity: .severe,
                vitalSigns: VitalSigns(heartRate: 98, bloodPressure: "172/108", temperature: 98.6, respiratoryRate: 20, oxygenSaturation: 98),
                medicalHistory: ["Gestational hypertension"],
                currentMedications: ["Prenatal vitamins", "Labetalol"],
                allergies: []
            ),
            expectedTriage: .emergency,
            expectedDiagnosisKeywords: ["preeclampsia", "eclampsia", "hellp", "hypertensive"],
            expectedSafetyCategories: [.emergencyEscalation, .pregnancyRisk, .redFlagSymptom]
        ),
    ]
}
