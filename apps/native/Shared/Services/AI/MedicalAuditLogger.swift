//
//  MedicalAuditLogger.swift
//  MagnetarStudio
//
//  HAI-DEF compliant audit logging for medical AI decisions.
//  Records model inputs, outputs, safety checks, and performance
//  for regulatory traceability and quality improvement.
//
//  MedGemma Impact Challenge (Kaggle 2026) — HAI-DEF Compliance.
//

import Foundation
import CryptoKit
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "MedicalAuditLogger")

// MARK: - Audit Logger

struct MedicalAuditLogger {

    // MARK: - Log Workflow Execution

    static func logWorkflowExecution(
        intake: PatientIntake,
        result: MedicalWorkflowResult,
        imageAnalysisPerformed: Bool,
        disclaimerConfirmed: Bool = true
    ) {
        let entry = AuditEntry(
            caseId: result.intakeId,
            modelId: result.performanceMetrics?.modelName ?? "medgemma:4b",
            modelVersion: result.performanceMetrics?.modelParameterCount ?? "4B",
            workflowSteps: result.reasoning.map { step in
                AuditEntry.StepRecord(
                    stepNumber: step.step,
                    title: step.title,
                    inputHash: hashString(step.title),
                    outputHash: hashString(step.content),
                    outputLengthChars: step.content.count,
                    durationMs: step.durationMs
                )
            },
            triageResult: result.triageLevel.rawValue,
            diagnosisCount: result.differentialDiagnoses.count,
            safetyAlertsGenerated: result.safetyAlerts.count,
            safetyAlertSummary: result.safetyAlerts.map { "\($0.severity.rawValue): \($0.category.rawValue)" },
            performanceMetrics: AuditEntry.PerformanceRecord(
                totalWorkflowMs: result.performanceMetrics?.totalWorkflowMs ?? 0,
                averageStepMs: result.performanceMetrics?.averageStepMs ?? 0,
                thermalState: result.performanceMetrics?.deviceThermalState.rawValue ?? "Unknown",
                imageAnalysisMs: result.performanceMetrics?.imageAnalysisMs,
                imageAnalysisPerformed: imageAnalysisPerformed,
                onDeviceInference: true
            ),
            patientDataHash: hashPatientData(intake),
            disclaimerPresented: disclaimerConfirmed,
            consentConfirmed: disclaimerConfirmed
        )

        saveAuditEntry(entry, caseId: result.intakeId)
    }

    // MARK: - Persistence

    private static func saveAuditEntry(_ entry: AuditEntry, caseId: UUID) {
        let dir = auditDirectory
        PersistenceHelpers.ensureDirectory(at: dir, label: "medical audit logs")
        let file = dir.appendingPathComponent("\(caseId.uuidString)-audit.json")
        PersistenceHelpers.save(entry, to: file, label: "medical audit entry")
        logger.info("Audit log saved for case \(caseId.uuidString.prefix(8))")
    }

    static func loadAuditEntry(for caseId: UUID) -> AuditEntry? {
        let file = auditDirectory.appendingPathComponent("\(caseId.uuidString)-audit.json")
        return PersistenceHelpers.load(AuditEntry.self, from: file, label: "medical audit entry")
    }

    static func loadAllAuditEntries() -> [AuditEntry] {
        let dir = auditDirectory
        let files: [URL]
        do {
            files = try FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)
                .filter { $0.pathExtension == "json" }
        } catch {
            logger.debug("No audit logs found: \(error.localizedDescription)")
            return []
        }

        return files.compactMap { PersistenceHelpers.load(AuditEntry.self, from: $0, label: "audit entry") }
            .sorted { $0.timestamp > $1.timestamp }
    }

    private static var auditDirectory: URL {
        (FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory)
            .appendingPathComponent("MagnetarStudio/workspace/medical/audit", isDirectory: true)
    }

    // MARK: - Hashing (privacy-preserving)

    private static func hashString(_ input: String) -> String {
        let data = Data(input.utf8)
        let hash = SHA256.hash(data: data)
        return hash.prefix(8).map { String(format: "%02x", $0) }.joined()
    }

    private static func hashPatientData(_ intake: PatientIntake) -> String {
        let combined = "\(intake.patientId)-\(intake.chiefComplaint)-\(intake.symptoms.joined())"
        return hashString(combined)
    }
}

// MARK: - Audit Entry Model

struct AuditEntry: Codable, Identifiable, Sendable {
    let id: UUID
    let caseId: UUID
    let timestamp: Date

    // Model information
    let modelId: String
    let modelVersion: String

    // Workflow trace
    let workflowSteps: [StepRecord]
    let triageResult: String
    let diagnosisCount: Int

    // Safety compliance
    let safetyAlertsGenerated: Int
    let safetyAlertSummary: [String]

    // Performance
    let performanceMetrics: PerformanceRecord

    // Privacy
    let patientDataHash: String

    // Consent
    let disclaimerPresented: Bool
    let consentConfirmed: Bool

    struct StepRecord: Codable, Sendable {
        let stepNumber: Int
        let title: String
        let inputHash: String
        let outputHash: String
        let outputLengthChars: Int
        let durationMs: Double
    }

    struct PerformanceRecord: Codable, Sendable {
        let totalWorkflowMs: Double
        let averageStepMs: Double
        let thermalState: String
        let imageAnalysisMs: Double?
        let imageAnalysisPerformed: Bool
        let onDeviceInference: Bool
    }

    init(
        id: UUID = UUID(),
        caseId: UUID,
        timestamp: Date = Date(),
        modelId: String,
        modelVersion: String,
        workflowSteps: [StepRecord],
        triageResult: String,
        diagnosisCount: Int,
        safetyAlertsGenerated: Int,
        safetyAlertSummary: [String],
        performanceMetrics: PerformanceRecord,
        patientDataHash: String,
        disclaimerPresented: Bool,
        consentConfirmed: Bool
    ) {
        self.id = id
        self.caseId = caseId
        self.timestamp = timestamp
        self.modelId = modelId
        self.modelVersion = modelVersion
        self.workflowSteps = workflowSteps
        self.triageResult = triageResult
        self.diagnosisCount = diagnosisCount
        self.safetyAlertsGenerated = safetyAlertsGenerated
        self.safetyAlertSummary = safetyAlertSummary
        self.performanceMetrics = performanceMetrics
        self.patientDataHash = patientDataHash
        self.disclaimerPresented = disclaimerPresented
        self.consentConfirmed = consentConfirmed
    }
}
