//
//  CodingModelOrchestrator.swift
//  MagnetarStudio
//
//  Multi-model orchestration for the Coding workspace.
//  Supports Sequential, Parallel, and Specialist orchestration modes
//  for intelligent model coordination.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "CodingModelOrchestrator")

// MARK: - Orchestration Mode

/// Mode for multi-model orchestration
enum OrchestrationMode: String, CaseIterable, Codable, Sendable {
    /// Single model handles the request
    case single = "Single Model"

    /// Model A reasons → Model B validates/refines
    case sequential = "Sequential"

    /// Multiple models respond in parallel, best selected
    case parallel = "Parallel"

    /// Route based on query type (code → code model, prose → general model)
    case specialist = "Specialist"

    var description: String {
        switch self {
        case .single:
            return "Use a single model for all requests"
        case .sequential:
            return "First model reasons, second model validates"
        case .parallel:
            return "Multiple models respond, best answer selected"
        case .specialist:
            return "Route to specialized models based on query type"
        }
    }

    var iconName: String {
        switch self {
        case .single: return "1.circle"
        case .sequential: return "arrow.right.arrow.left"
        case .parallel: return "square.split.2x1"
        case .specialist: return "target"
        }
    }
}

// MARK: - Model Role

/// Role a model plays in orchestration
enum ModelRole: String, Codable, Sendable {
    case primary      // Main responder
    case validator    // Validates/refines primary response
    case codeSpecialist   // Handles code-related queries
    case reasoningSpecialist  // Handles complex reasoning
    case generalSpecialist    // Handles general prose
}

// MARK: - Model Session

/// Configuration for a model in an orchestration session
struct ModelSession: Codable, Identifiable, Sendable {
    let id: UUID
    let modelId: String
    let modelName: String
    let role: ModelRole
    let provider: ModelProvider

    enum ModelProvider: String, Codable, Sendable {
        case ollama
        case llamaCpp
        case anthropic
        case openai
        case deepseek
        case local  // Generic local model
    }

    init(
        id: UUID = UUID(),
        modelId: String,
        modelName: String,
        role: ModelRole,
        provider: ModelProvider = .ollama
    ) {
        self.id = id
        self.modelId = modelId
        self.modelName = modelName
        self.role = role
        self.provider = provider
    }
}

// MARK: - Orchestrated Request

/// Request for multi-model orchestration
struct OrchestratedRequest: Sendable {
    let query: String
    let context: String?
    let terminalContext: [TerminalContext]
    let codeContext: String?
    let ragCodeContext: String?
    let mode: OrchestrationMode
    let sessions: [ModelSession]
    let temperature: Float
    let maxTokens: Int?

    init(
        query: String,
        context: String? = nil,
        terminalContext: [TerminalContext] = [],
        codeContext: String? = nil,
        ragCodeContext: String? = nil,
        mode: OrchestrationMode = .single,
        sessions: [ModelSession] = [],
        temperature: Float = 0.7,
        maxTokens: Int? = nil
    ) {
        self.query = query
        self.context = context
        self.terminalContext = terminalContext
        self.codeContext = codeContext
        self.ragCodeContext = ragCodeContext
        self.mode = mode
        self.sessions = sessions
        self.temperature = temperature
        self.maxTokens = maxTokens
    }
}

// MARK: - Orchestrated Response

/// Response from multi-model orchestration
struct OrchestratedResponse: Sendable {
    let content: String
    let modelUsed: String
    let mode: OrchestrationMode
    let confidence: Float
    let reasoning: String?
    let modelResponses: [ModelResponse]
    let executionTimeMs: Int
    let timestamp: Date

    struct ModelResponse: Sendable, Identifiable {
        let id: UUID
        let modelId: String
        let modelName: String
        let role: ModelRole
        let content: String
        let confidence: Float
        let executionTimeMs: Int

        init(
            id: UUID = UUID(),
            modelId: String,
            modelName: String,
            role: ModelRole,
            content: String,
            confidence: Float = 0.8,
            executionTimeMs: Int = 0
        ) {
            self.id = id
            self.modelId = modelId
            self.modelName = modelName
            self.role = role
            self.content = content
            self.confidence = confidence
            self.executionTimeMs = executionTimeMs
        }
    }

    init(
        content: String,
        modelUsed: String,
        mode: OrchestrationMode,
        confidence: Float = 0.8,
        reasoning: String? = nil,
        modelResponses: [ModelResponse] = [],
        executionTimeMs: Int = 0,
        timestamp: Date = Date()
    ) {
        self.content = content
        self.modelUsed = modelUsed
        self.mode = mode
        self.confidence = confidence
        self.reasoning = reasoning
        self.modelResponses = modelResponses
        self.executionTimeMs = executionTimeMs
        self.timestamp = timestamp
    }
}

// MARK: - Query Classification

/// Classification of query type for specialist routing
enum QueryType: String, Sendable {
    case codeGeneration = "code_generation"
    case codeExplanation = "code_explanation"
    case codeReview = "code_review"
    case debugging = "debugging"
    case terminalHelp = "terminal_help"
    case reasoning = "reasoning"
    case general = "general"

    /// Preferred model role for this query type
    var preferredRole: ModelRole {
        switch self {
        case .codeGeneration, .codeExplanation, .codeReview, .debugging, .terminalHelp:
            return .codeSpecialist
        case .reasoning:
            return .reasoningSpecialist
        case .general:
            return .generalSpecialist
        }
    }
}

// MARK: - Coding Model Orchestrator

/// Orchestrates multiple models for the coding workspace
@MainActor
final class CodingModelOrchestrator {
    // MARK: - Singleton

    static let shared = CodingModelOrchestrator()

    // MARK: - Properties

    /// Current orchestration mode
    var currentMode: OrchestrationMode = .single {
        didSet {
            UserDefaults.standard.set(currentMode.rawValue, forKey: "coding.orchestrationMode")
        }
    }

    /// Configured model sessions
    var modelSessions: [ModelSession] = []

    /// Default model for single mode
    var defaultModelId: String?

    /// Response merger for combining outputs
    private let responseMerger = ResponseMerger()

    // MARK: - Init

    private init() {
        // Restore saved mode
        if let savedMode = UserDefaults.standard.string(forKey: "coding.orchestrationMode"),
           let mode = OrchestrationMode(rawValue: savedMode) {
            self.currentMode = mode
        }

        setupDefaultSessions()
    }

    private func setupDefaultSessions() {
        // Default sessions can be configured based on available models
        // This will be populated dynamically based on OrchestratorManager
    }

    // MARK: - Orchestration

    /// Orchestrate a request based on current mode
    func orchestrate(_ request: OrchestratedRequest) async throws -> OrchestratedResponse {
        let startTime = Date()

        // Auto-enrich with code RAG context if not already provided
        let enrichedRequest = (request.ragCodeContext == nil && request.codeContext == nil)
            ? await enrichWithCodeContext(request)
            : request

        let response: OrchestratedResponse

        switch enrichedRequest.mode {
        case .single:
            response = try await orchestrateSingle(enrichedRequest)

        case .sequential:
            response = try await orchestrateSequential(enrichedRequest)

        case .parallel:
            response = try await orchestrateParallel(enrichedRequest)

        case .specialist:
            response = try await orchestrateSpecialist(enrichedRequest)
        }

        let executionTime = Int(Date().timeIntervalSince(startTime) * 1000)
        logger.info("[Orchestrator] Completed \(enrichedRequest.mode.rawValue) in \(executionTime)ms")

        return response
    }

    // MARK: - Single Mode

    private func orchestrateSingle(_ request: OrchestratedRequest) async throws -> OrchestratedResponse {
        let session = request.sessions.first ?? getDefaultSession()

        let content = try await callModel(
            session: session,
            prompt: buildPrompt(request),
            temperature: request.temperature
        )

        return OrchestratedResponse(
            content: content,
            modelUsed: session.modelName,
            mode: .single,
            confidence: 0.8,
            modelResponses: [
                OrchestratedResponse.ModelResponse(
                    modelId: session.modelId,
                    modelName: session.modelName,
                    role: session.role,
                    content: content
                )
            ]
        )
    }

    // MARK: - Sequential Mode

    private func orchestrateSequential(_ request: OrchestratedRequest) async throws -> OrchestratedResponse {
        let sessions = request.sessions.isEmpty ? getSequentialSessions() : request.sessions

        guard sessions.count >= 2 else {
            // Fall back to single if not enough models
            return try await orchestrateSingle(request)
        }

        let primarySession = sessions[0]
        let validatorSession = sessions[1]
        var modelResponses: [OrchestratedResponse.ModelResponse] = []

        // Step 1: Primary model reasons
        logger.debug("[Orchestrator] Sequential Step 1: Primary model reasoning")
        let primaryStart = Date()
        let primaryResponse = try await callModel(
            session: primarySession,
            prompt: buildPrompt(request),
            temperature: request.temperature
        )
        let primaryTime = Int(Date().timeIntervalSince(primaryStart) * 1000)

        modelResponses.append(OrchestratedResponse.ModelResponse(
            modelId: primarySession.modelId,
            modelName: primarySession.modelName,
            role: .primary,
            content: primaryResponse,
            executionTimeMs: primaryTime
        ))

        // Step 2: Validator refines/validates
        logger.debug("[Orchestrator] Sequential Step 2: Validator refining")
        let validatorStart = Date()
        let validationPrompt = """
        Review and refine this response. Fix any errors, improve clarity, and ensure correctness.

        Original query: \(request.query)

        Initial response:
        \(primaryResponse)

        Provide an improved response:
        """

        let validatorResponse = try await callModel(
            session: validatorSession,
            prompt: validationPrompt,
            temperature: max(0.3, request.temperature - 0.2)  // Lower temp for validation
        )
        let validatorTime = Int(Date().timeIntervalSince(validatorStart) * 1000)

        modelResponses.append(OrchestratedResponse.ModelResponse(
            modelId: validatorSession.modelId,
            modelName: validatorSession.modelName,
            role: .validator,
            content: validatorResponse,
            executionTimeMs: validatorTime
        ))

        return OrchestratedResponse(
            content: validatorResponse,
            modelUsed: "\(primarySession.modelName) → \(validatorSession.modelName)",
            mode: .sequential,
            confidence: 0.85,
            reasoning: "Primary model generated initial response, validator refined it",
            modelResponses: modelResponses
        )
    }

    // MARK: - Parallel Mode

    private func orchestrateParallel(_ request: OrchestratedRequest) async throws -> OrchestratedResponse {
        let sessions = request.sessions.isEmpty ? getParallelSessions() : request.sessions

        guard sessions.count >= 2 else {
            return try await orchestrateSingle(request)
        }

        logger.debug("[Orchestrator] Parallel: Querying \(sessions.count) models")

        // Query all models in parallel
        let prompt = buildPrompt(request)
        var modelResponses: [OrchestratedResponse.ModelResponse] = []

        await withTaskGroup(of: OrchestratedResponse.ModelResponse?.self) { group in
            for session in sessions {
                group.addTask { [self] in
                    let start = Date()
                    do {
                        let content = try await self.callModel(
                            session: session,
                            prompt: prompt,
                            temperature: request.temperature
                        )
                        let time = Int(Date().timeIntervalSince(start) * 1000)

                        return OrchestratedResponse.ModelResponse(
                            modelId: session.modelId,
                            modelName: session.modelName,
                            role: session.role,
                            content: content,
                            confidence: 0.8,
                            executionTimeMs: time
                        )
                    } catch {
                        logger.error("[Orchestrator] Model \(session.modelName) failed: \(error)")
                        return nil
                    }
                }
            }

            for await response in group {
                if let response = response {
                    modelResponses.append(response)
                }
            }
        }

        guard !modelResponses.isEmpty else {
            throw OrchestratorError.allModelsFailed
        }

        // Select best response
        let selected = responseMerger.selectBest(from: modelResponses, query: request.query)

        return OrchestratedResponse(
            content: selected.content,
            modelUsed: selected.modelName,
            mode: .parallel,
            confidence: selected.confidence,
            reasoning: "Selected from \(modelResponses.count) parallel responses based on quality scoring",
            modelResponses: modelResponses
        )
    }

    // MARK: - Specialist Mode

    private func orchestrateSpecialist(_ request: OrchestratedRequest) async throws -> OrchestratedResponse {
        // Classify the query
        let queryType = classifyQuery(request.query)
        logger.debug("[Orchestrator] Specialist: Query classified as \(queryType.rawValue)")

        // Find specialist for this query type
        let sessions = request.sessions.isEmpty ? getSpecialistSessions() : request.sessions
        let specialist = sessions.first { $0.role == queryType.preferredRole }
            ?? sessions.first
            ?? getDefaultSession()

        let content = try await callModel(
            session: specialist,
            prompt: buildPrompt(request),
            temperature: request.temperature
        )

        return OrchestratedResponse(
            content: content,
            modelUsed: specialist.modelName,
            mode: .specialist,
            confidence: 0.85,
            reasoning: "Routed to \(specialist.role.rawValue) for \(queryType.rawValue) query",
            modelResponses: [
                OrchestratedResponse.ModelResponse(
                    modelId: specialist.modelId,
                    modelName: specialist.modelName,
                    role: specialist.role,
                    content: content
                )
            ]
        )
    }

    // MARK: - Query Classification

    private func classifyQuery(_ query: String) -> QueryType {
        let lowercased = query.lowercased()

        // Code generation patterns
        if lowercased.contains("write") || lowercased.contains("create") ||
           lowercased.contains("implement") || lowercased.contains("generate code") {
            return .codeGeneration
        }

        // Code explanation patterns
        if lowercased.contains("explain") || lowercased.contains("what does") ||
           lowercased.contains("how does") {
            return .codeExplanation
        }

        // Code review patterns
        if lowercased.contains("review") || lowercased.contains("improve") ||
           lowercased.contains("refactor") {
            return .codeReview
        }

        // Debugging patterns
        if lowercased.contains("debug") || lowercased.contains("error") ||
           lowercased.contains("fix") || lowercased.contains("bug") {
            return .debugging
        }

        // Terminal patterns
        if lowercased.contains("terminal") || lowercased.contains("command") ||
           lowercased.contains("shell") || lowercased.contains("bash") {
            return .terminalHelp
        }

        // Reasoning patterns
        if lowercased.contains("why") || lowercased.contains("analyze") ||
           lowercased.contains("compare") || lowercased.contains("think") {
            return .reasoning
        }

        return .general
    }

    // MARK: - Prompt Building

    private func buildPrompt(_ request: OrchestratedRequest) -> String {
        var parts: [String] = []

        // System context
        parts.append("You are an AI assistant helping with coding tasks.")

        // Code context (explicitly provided)
        if let codeContext = request.codeContext, !codeContext.isEmpty {
            parts.append("Current code context:\n```\n\(codeContext)\n```")
        }

        // RAG-retrieved code context (automatically searched)
        if let ragContext = request.ragCodeContext, !ragContext.isEmpty {
            parts.append(ragContext)
        }

        // Terminal context
        if !request.terminalContext.isEmpty {
            let terminalStr = request.terminalContext.map { ctx in
                "$ \(ctx.command)\n\(ctx.output.prefix(500))"
            }.joined(separator: "\n\n")
            parts.append("Recent terminal output:\n\(terminalStr)")
        }

        // Additional context
        if let context = request.context, !context.isEmpty {
            parts.append("Additional context:\n\(context)")
        }

        // User query
        parts.append("User query: \(request.query)")

        return parts.joined(separator: "\n\n")
    }

    /// Enrich a request with RAG-retrieved code context before sending to models
    func enrichWithCodeContext(_ request: OrchestratedRequest) async -> OrchestratedRequest {
        do {
            let codeContext = try await CodeRAGService.shared.buildContext(
                for: request.query,
                maxTokens: 4000
            )

            guard codeContext.hasContent else { return request }

            logger.debug("[Orchestrator] Enriched with \(codeContext.results.count) code snippets (\(codeContext.tokenEstimate) tokens)")

            return OrchestratedRequest(
                query: request.query,
                context: request.context,
                terminalContext: request.terminalContext,
                codeContext: request.codeContext,
                ragCodeContext: codeContext.formattedContext,
                mode: request.mode,
                sessions: request.sessions,
                temperature: request.temperature,
                maxTokens: request.maxTokens
            )
        } catch {
            logger.error("[Orchestrator] Code RAG enrichment failed: \(error)")
            return request
        }
    }

    // MARK: - Model Calling

    private func callModel(session: ModelSession, prompt: String, temperature: Float) async throws -> String {
        // This integrates with existing model infrastructure
        // For now, use Ollama via backend API
        switch session.provider {
        case .ollama:
            return try await callOllamaModel(modelId: session.modelId, prompt: prompt, temperature: temperature)
        case .llamaCpp:
            return try await callLlamaCppModel(prompt: prompt, temperature: temperature)
        default:
            // Fallback to Ollama
            return try await callOllamaModel(modelId: session.modelId, prompt: prompt, temperature: temperature)
        }
    }

    private func callOllamaModel(modelId: String, prompt: String, temperature: Float) async throws -> String {
        // Use existing OllamaService or API endpoint
        let body: [String: Any] = [
            "model": modelId,
            "prompt": prompt,
            "stream": false,
            "options": ["temperature": temperature]
        ]

        struct OllamaGenerateResponse: Codable {
            let response: String
        }

        let response: OllamaGenerateResponse = try await ApiClient.shared.request(
            path: "/v1/chat/ollama/generate",
            method: .post,
            jsonBody: body
        )

        return response.response
    }

    private func callLlamaCppModel(prompt: String, temperature: Float) async throws -> String {
        // Use LlamaCppService
        let messages = [["role": "user", "content": prompt]]

        struct LlamaCppResponse: Codable {
            let choices: [Choice]
            struct Choice: Codable {
                let message: Message
                struct Message: Codable {
                    let content: String
                }
            }
        }

        let response: LlamaCppResponse = try await ApiClient.shared.request(
            path: "/v1/chat/llamacpp/chat",
            method: .post,
            jsonBody: [
                "messages": messages,
                "temperature": temperature,
                "stream": false
            ]
        )

        return response.choices.first?.message.content ?? ""
    }

    // MARK: - Session Management

    private func getDefaultSession() -> ModelSession {
        if let id = defaultModelId {
            return ModelSession(modelId: id, modelName: id, role: .primary)
        }
        // Default to a common model
        return ModelSession(modelId: "llama3.2:latest", modelName: "Llama 3.2", role: .primary)
    }

    private func getSequentialSessions() -> [ModelSession] {
        // Default sequential: reasoning model → code model
        return [
            ModelSession(modelId: "deepseek-r1:latest", modelName: "DeepSeek R1", role: .primary, provider: .ollama),
            ModelSession(modelId: "qwen2.5-coder:latest", modelName: "Qwen 2.5 Coder", role: .validator, provider: .ollama)
        ]
    }

    private func getParallelSessions() -> [ModelSession] {
        return [
            ModelSession(modelId: "llama3.2:latest", modelName: "Llama 3.2", role: .primary, provider: .ollama),
            ModelSession(modelId: "qwen2.5-coder:latest", modelName: "Qwen 2.5 Coder", role: .codeSpecialist, provider: .ollama)
        ]
    }

    private func getSpecialistSessions() -> [ModelSession] {
        return [
            ModelSession(modelId: "qwen2.5-coder:latest", modelName: "Qwen 2.5 Coder", role: .codeSpecialist, provider: .ollama),
            ModelSession(modelId: "deepseek-r1:latest", modelName: "DeepSeek R1", role: .reasoningSpecialist, provider: .ollama),
            ModelSession(modelId: "llama3.2:latest", modelName: "Llama 3.2", role: .generalSpecialist, provider: .ollama)
        ]
    }

    // MARK: - Configuration

    /// Configure model sessions
    func configure(sessions: [ModelSession]) {
        self.modelSessions = sessions
    }

    /// Add a model session
    func addSession(_ session: ModelSession) {
        modelSessions.append(session)
    }

    /// Remove a model session
    func removeSession(id: UUID) {
        modelSessions.removeAll { $0.id == id }
    }
}

// OrchestratorError is defined in ModelRoutingDecision.swift
