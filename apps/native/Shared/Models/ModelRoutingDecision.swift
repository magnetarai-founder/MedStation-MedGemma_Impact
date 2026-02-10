//
//  ModelRoutingDecision.swift
//  MedStation
//
//  Defines orchestrator output when routing a query to a model
//  Part of Noah's Ark for the Digital Age - Intelligent model routing
//
//  Foundation: Matthew 7:24-25 - Built on the rock, not sand
//

import Foundation

// MARK: - Model Routing Decision (Orchestrator Output)

/// Decision made by orchestrator (Apple FM) about which model to route to
/// Includes reasoning, fallback options, and resource constraints
struct ModelRoutingDecision: Codable, Sendable {
    // Primary decision
    let selectedModelId: String
    let selectedModelName: String
    let confidence: Float  // 0.0-1.0 (how confident is the orchestrator?)

    // Reasoning (transparency)
    let reasoning: String  // Human-readable explanation
    let decisionFactors: [DecisionFactor]

    // Fallback strategy
    let fallbackModels: [String]  // Ordered list of fallback model IDs
    let requiresHotSlot: Bool  // Does this model need to be loaded first?

    // Resource management
    let estimatedMemoryGB: Float?
    let estimatedTokens: Int?
    let wouldCauseEviction: Bool  // Would loading this model evict another?
    let evictionCandidate: String?  // Model ID that would be evicted

    // Context filtering
    let relevantContext: [String]  // Which context keys are relevant

    // Metadata
    let decidedAt: Date
    let orchestratorModel: String  // "apple-fm", "llama-3.2-3b", etc.
}

// MARK: - Decision Factor

/// Individual factor that influenced the routing decision
struct DecisionFactor: Codable, Identifiable, Sendable {
    let id: UUID = UUID()
    let factor: String  // "query_complexity", "model_specialty", "resource_constraints", etc.
    let weight: Float  // 0.0-1.0 (how much did this influence the decision?)
    let value: String  // Human-readable description

    enum CodingKeys: String, CodingKey {
        case factor, weight, value
    }
}

// MARK: - Orchestrator Protocol (Swappable)

/// Protocol for orchestrator implementations
/// Allows swapping between Apple FM, Llama, or other orchestrators
@MainActor
protocol ModelOrchestrator {
    /// Unique identifier for this orchestrator
    var id: String { get }

    /// Display name (e.g., "Apple FM", "Llama 3.2 3B Orchestrator")
    var displayName: String { get }

    /// Is this orchestrator available on this system?
    var isAvailable: Bool { get async }

    /// Make a routing decision for a given context bundle
    func route(bundle: ContextBundle) async throws -> ModelRoutingDecision

    /// Check if orchestrator is healthy and ready
    func healthCheck() async -> Bool
}

// MARK: - Orchestrator Manager

/// Manages available orchestrators and selects the best one
@MainActor
class OrchestratorManager {
    static let shared = OrchestratorManager()

    private var orchestrators: [ModelOrchestrator] = []
    private var activeOrchestrator: ModelOrchestrator?

    private init() {}

    /// Register an orchestrator
    func register(_ orchestrator: ModelOrchestrator) {
        orchestrators.append(orchestrator)
    }

    /// Get the active orchestrator (Apple FM preferred, fallback to others)
    func getActiveOrchestrator() async -> ModelOrchestrator? {
        if let active = activeOrchestrator, await active.isAvailable {
            return active
        }

        // Find first available orchestrator
        for orchestrator in orchestrators {
            if await orchestrator.isAvailable {
                activeOrchestrator = orchestrator
                return orchestrator
            }
        }

        return nil
    }

    /// Make a routing decision using active orchestrator
    func route(bundle: ContextBundle) async throws -> ModelRoutingDecision {
        guard let orchestrator = await getActiveOrchestrator() else {
            throw OrchestratorError.noOrchestratorAvailable
        }

        return try await orchestrator.route(bundle: bundle)
    }

    /// Check orchestrator health
    func healthCheck() async -> OrchestratorHealth {
        var available: [String] = []
        var unavailable: [String] = []

        for orchestrator in orchestrators {
            if await orchestrator.isAvailable {
                available.append(orchestrator.displayName)
            } else {
                unavailable.append(orchestrator.displayName)
            }
        }

        return OrchestratorHealth(
            available: available,
            unavailable: unavailable,
            activeOrchestrator: activeOrchestrator?.displayName
        )
    }
}

// MARK: - Orchestrator Health

struct OrchestratorHealth: Codable, Sendable {
    let available: [String]
    let unavailable: [String]
    let activeOrchestrator: String?
}

// MARK: - Errors

enum OrchestratorError: LocalizedError {
    case noOrchestratorAvailable
    case routingFailed(String)
    case modelNotAvailable(String)
    case resourceConstraints(String)
    case allModelsFailed
    case invalidConfiguration

    var errorDescription: String? {
        switch self {
        case .noOrchestratorAvailable:
            return "No orchestrator is available. Please check system requirements."
        case .routingFailed(let reason):
            return "Routing failed: \(reason)"
        case .modelNotAvailable(let modelId):
            return "Model '\(modelId)' is not available"
        case .resourceConstraints(let reason):
            return "Resource constraints: \(reason)"
        case .allModelsFailed:
            return "All models failed to respond"
        case .invalidConfiguration:
            return "Invalid orchestration configuration"
        }
    }
}

// MARK: - Mock Orchestrator (Fallback)

/// Simple rule-based orchestrator when Apple FM not available
@MainActor
class MockOrchestrator: ModelOrchestrator {
    let id = "mock-orchestrator"
    let displayName = "Rule-Based Orchestrator"

    var isAvailable: Bool {
        get async { true }  // Always available as fallback
    }

    func route(bundle: ContextBundle) async throws -> ModelRoutingDecision {
        // Simple rule-based routing
        let query = bundle.userQuery.lowercased()

        var selectedModelId = "llama3.2:3b"
        var selectedModelName = "Llama 3.2 3B"
        var reasoning = "Default chat model"
        var factors: [DecisionFactor] = []

        // SQL/Data queries
        if query.contains("sql") || query.contains("query") || query.contains("database") {
            selectedModelId = "phi-3.5:3.8b"
            selectedModelName = "Phi-3.5 3.8B"
            reasoning = "SQL and data analysis specialist"
            factors.append(DecisionFactor(
                factor: "query_type",
                weight: 0.9,
                value: "Data analysis query detected"
            ))
        }

        // Code queries
        if query.contains("code") || query.contains("function") || query.contains("python") || query.contains("javascript") {
            selectedModelId = "qwen2.5-coder:3b"
            selectedModelName = "Qwen2.5-Coder 3B"
            reasoning = "Code generation and analysis specialist"
            factors.append(DecisionFactor(
                factor: "query_type",
                weight: 0.9,
                value: "Code-related query detected"
            ))
        }

        // Reasoning/complex queries
        if query.contains("why") || query.contains("explain") || query.contains("reasoning") {
            selectedModelId = "deepseek-r1:8b"
            selectedModelName = "DeepSeek-R1 8B"
            reasoning = "Complex reasoning and explanation specialist"
            factors.append(DecisionFactor(
                factor: "query_complexity",
                weight: 0.85,
                value: "Complex reasoning required"
            ))
        }

        // Check if model is available
        let isAvailable = bundle.availableModels.contains { $0.id == selectedModelId }
        if !isAvailable {
            // Fallback to first available model
            if let firstModel = bundle.availableModels.first {
                selectedModelId = firstModel.id
                selectedModelName = firstModel.name
                reasoning = "Preferred model not available, using fallback"
            }
        }

        return ModelRoutingDecision(
            selectedModelId: selectedModelId,
            selectedModelName: selectedModelName,
            confidence: 0.7,  // Lower confidence for rule-based
            reasoning: reasoning,
            decisionFactors: factors,
            fallbackModels: ["llama3.2:3b", "phi-3.5:3.8b"],
            requiresHotSlot: true,
            estimatedMemoryGB: 3.0,
            estimatedTokens: bundle.conversationHistory.reduce(0) { $0 + ($1.tokenCount ?? 0) },
            wouldCauseEviction: false,
            evictionCandidate: nil,
            relevantContext: ["conversationHistory"],
            decidedAt: Date(),
            orchestratorModel: "mock-orchestrator"
        )
    }

    func healthCheck() async -> Bool {
        return true
    }
}
