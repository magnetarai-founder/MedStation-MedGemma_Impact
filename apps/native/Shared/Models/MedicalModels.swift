//
//  MedicalModels.swift
//  MagnetarStudio
//
//  Data models for the MedGemma-powered agentic medical workflow.
//  Supports patient intake, multi-step reasoning, triage, and case persistence.
//

import Foundation

// MARK: - Patient Intake

struct PatientIntake: Identifiable, Codable, Equatable, Hashable, Sendable {
    let id: UUID
    var patientId: String
    var chiefComplaint: String
    var symptoms: [String]
    var onsetTime: String
    var severity: Severity
    var vitalSigns: VitalSigns?
    var medicalHistory: [String]
    var currentMedications: [String]
    var allergies: [String]
    var attachedImagePaths: [String]
    var createdAt: Date
    var updatedAt: Date

    enum Severity: String, Codable, CaseIterable, Sendable {
        case mild = "Mild"
        case moderate = "Moderate"
        case severe = "Severe"
        case critical = "Critical"
    }

    init(
        id: UUID = UUID(),
        patientId: String = "",
        chiefComplaint: String = "",
        symptoms: [String] = [],
        onsetTime: String = "",
        severity: Severity = .moderate,
        vitalSigns: VitalSigns? = nil,
        medicalHistory: [String] = [],
        currentMedications: [String] = [],
        allergies: [String] = [],
        attachedImagePaths: [String] = [],
        createdAt: Date = Date(),
        updatedAt: Date = Date()
    ) {
        self.id = id
        self.patientId = patientId
        self.chiefComplaint = chiefComplaint
        self.symptoms = symptoms
        self.onsetTime = onsetTime
        self.severity = severity
        self.vitalSigns = vitalSigns
        self.medicalHistory = medicalHistory
        self.currentMedications = currentMedications
        self.allergies = allergies
        self.attachedImagePaths = attachedImagePaths
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }
}

// MARK: - Vital Signs

struct VitalSigns: Codable, Equatable, Hashable, Sendable {
    var heartRate: Int?
    var bloodPressure: String?
    var temperature: Double?
    var respiratoryRate: Int?
    var oxygenSaturation: Int?
}

// MARK: - Workflow Result

struct MedicalWorkflowResult: Identifiable, Codable, Equatable, Sendable {
    let id: UUID
    let intakeId: UUID
    var triageLevel: TriageLevel
    var differentialDiagnoses: [Diagnosis]
    var recommendedActions: [RecommendedAction]
    var reasoning: [ReasoningStep]
    var performanceMetrics: PerformanceMetrics?
    var disclaimer: String
    var generatedAt: Date

    enum TriageLevel: String, Codable, CaseIterable, Sendable {
        case emergency = "Emergency (Call 911)"
        case urgent = "Urgent (Seek care within 2-4 hours)"
        case semiUrgent = "Semi-Urgent (See doctor within 24 hours)"
        case nonUrgent = "Non-Urgent (Schedule appointment)"
        case selfCare = "Self-Care (Monitor at home)"
    }

    init(
        id: UUID = UUID(),
        intakeId: UUID,
        triageLevel: TriageLevel = .semiUrgent,
        differentialDiagnoses: [Diagnosis] = [],
        recommendedActions: [RecommendedAction] = [],
        reasoning: [ReasoningStep] = [],
        performanceMetrics: PerformanceMetrics? = nil,
        disclaimer: String = "",
        generatedAt: Date = Date()
    ) {
        self.id = id
        self.intakeId = intakeId
        self.triageLevel = triageLevel
        self.differentialDiagnoses = differentialDiagnoses
        self.recommendedActions = recommendedActions
        self.reasoning = reasoning
        self.performanceMetrics = performanceMetrics
        self.disclaimer = disclaimer
        self.generatedAt = generatedAt
    }
}

// MARK: - Diagnosis

struct Diagnosis: Codable, Identifiable, Equatable, Sendable {
    let id: UUID
    var condition: String
    var probability: Double
    var rationale: String

    init(id: UUID = UUID(), condition: String, probability: Double, rationale: String) {
        self.id = id
        self.condition = condition
        self.probability = probability
        self.rationale = rationale
    }
}

// MARK: - Recommended Action

struct RecommendedAction: Codable, Identifiable, Equatable, Sendable {
    let id: UUID
    var action: String
    var priority: ActionPriority

    enum ActionPriority: String, Codable, Sendable {
        case immediate = "Immediate"
        case high = "High"
        case medium = "Medium"
        case low = "Low"
    }

    init(id: UUID = UUID(), action: String, priority: ActionPriority) {
        self.id = id
        self.action = action
        self.priority = priority
    }
}

// MARK: - Reasoning Step

struct ReasoningStep: Codable, Identifiable, Equatable, Sendable {
    let id: UUID
    var step: Int
    var title: String
    var content: String
    var durationMs: Double
    var timestamp: Date

    init(id: UUID = UUID(), step: Int, title: String, content: String, durationMs: Double = 0, timestamp: Date = Date()) {
        self.id = id
        self.step = step
        self.title = title
        self.content = content
        self.durationMs = durationMs
        self.timestamp = timestamp
    }
}

// MARK: - Medical Case (Persistence Unit)

struct MedicalCase: Identifiable, Codable, Equatable, Sendable {
    let id: UUID
    var intake: PatientIntake
    var result: MedicalWorkflowResult?
    var status: CaseStatus
    var createdAt: Date
    var updatedAt: Date

    enum CaseStatus: String, Codable, Sendable {
        case pending = "Pending"
        case analyzing = "Analyzing"
        case completed = "Completed"
        case archived = "Archived"
    }

    init(
        id: UUID = UUID(),
        intake: PatientIntake,
        result: MedicalWorkflowResult? = nil,
        status: CaseStatus = .pending,
        createdAt: Date = Date(),
        updatedAt: Date = Date()
    ) {
        self.id = id
        self.intake = intake
        self.result = result
        self.status = status
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }
}

// MARK: - Edge AI Performance Metrics

struct PerformanceMetrics: Codable, Equatable, Sendable {
    var totalWorkflowMs: Double
    var stepDurations: [String: Double]
    var modelName: String
    var modelParameterCount: String
    var deviceThermalState: ThermalLabel
    var peakMemoryMB: Int?
    var imageAnalysisMs: Double?

    enum ThermalLabel: String, Codable, Sendable {
        case nominal = "Nominal"
        case fair = "Fair"
        case serious = "Serious"
        case critical = "Critical"

        init(from processInfo: ProcessInfo) {
            switch processInfo.thermalState {
            case .nominal: self = .nominal
            case .fair: self = .fair
            case .serious: self = .serious
            case .critical: self = .critical
            @unknown default: self = .nominal
            }
        }
    }

    var averageStepMs: Double {
        guard !stepDurations.isEmpty else { return 0 }
        return stepDurations.values.reduce(0, +) / Double(stepDurations.count)
    }

    init(
        totalWorkflowMs: Double = 0,
        stepDurations: [String: Double] = [:],
        modelName: String = "medgemma:4b",
        modelParameterCount: String = "4B",
        deviceThermalState: ThermalLabel = .nominal,
        peakMemoryMB: Int? = nil,
        imageAnalysisMs: Double? = nil
    ) {
        self.totalWorkflowMs = totalWorkflowMs
        self.stepDurations = stepDurations
        self.modelName = modelName
        self.modelParameterCount = modelParameterCount
        self.deviceThermalState = deviceThermalState
        self.peakMemoryMB = peakMemoryMB
        self.imageAnalysisMs = imageAnalysisMs
    }
}

// MARK: - Image Analysis Context (for multimodal enrichment)

struct MedicalImageAnalysis: Codable, Equatable, Sendable {
    var imagePath: String
    var ocrText: String
    var detectedObjects: [String]
    var analysisDescription: String
    var layerTimings: [String: Double]
    var totalAnalysisMs: Double
}
