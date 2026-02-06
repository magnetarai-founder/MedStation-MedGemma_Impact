//
//  AppleFMOrchestrator.swift
//  MagnetarStudio
//
//  Apple Foundation Models orchestrator for intelligent model routing
//  Uses on-device 3B LLM to analyze queries and route to best model
//
//  Part of Noah's Ark for the Digital Age - Intelligent routing
//  Foundation: Matthew 7:24-25 - Built on the rock, not sand
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "AppleFMOrchestrator")

// MARK: - Apple FM Orchestrator

/// Orchestrator using Apple's Foundation Models (macOS 26 Tahoe)
/// Routes queries to best model based on complexity, specialty, and resources
@MainActor
class AppleFMOrchestrator: ModelOrchestrator {
    let id = "apple-fm"
    let displayName = "Apple Foundation Models"

    // Check if backend orchestrator is available
    var isAvailable: Bool {
        get async {
            // Check if backend is available by attempting health check
            do {
                struct HealthResponse: Codable, Sendable {
                    let status: String
                }

                let response: HealthResponse = try await ApiClient.shared.request(
                    "/health",
                    method: .get,
                    authenticated: false
                )
                return response.status == "healthy" || response.status == "ok"
            } catch {
                logger.warning("Backend orchestrator unavailable: \(error)")
                return false
            }
        }
    }

    func healthCheck() async -> Bool {
        await isAvailable
    }

    // MARK: - Routing Logic

    func route(bundle: ContextBundle) async throws -> ModelRoutingDecision {
        // Analyze query with Foundation Models
        let analysis = await analyzeQuery(bundle.userQuery, context: bundle)

        // Get available models
        let availableModels = bundle.availableModels.filter { $0.isHealthy }

        guard !availableModels.isEmpty else {
            throw OrchestratorError.modelNotAvailable("No healthy models available")
        }

        // Find best model based on analysis
        let selectedModel = selectBestModel(
            analysis: analysis,
            availableModels: availableModels,
            systemResources: bundle.systemResources
        )

        // Check if we need to load model into hot slot
        let (requiresHotSlot, evictionCandidate) = checkHotSlotRequirement(
            modelId: selectedModel.id,
            availableModels: availableModels,
            systemResources: bundle.systemResources
        )

        // Determine which context is relevant
        let relevantContext = determineRelevantContext(
            analysis: analysis,
            bundle: bundle
        )

        // Build decision factors
        let factors = buildDecisionFactors(
            analysis: analysis,
            selectedModel: selectedModel,
            systemResources: bundle.systemResources
        )

        // Build fallback list
        let fallbackModels = buildFallbackList(
            primaryModel: selectedModel,
            availableModels: availableModels,
            analysis: analysis
        )

        return ModelRoutingDecision(
            selectedModelId: selectedModel.id,
            selectedModelName: selectedModel.displayName,
            confidence: analysis.confidence,
            reasoning: analysis.reasoning,
            decisionFactors: factors,
            fallbackModels: fallbackModels,
            requiresHotSlot: requiresHotSlot,
            estimatedMemoryGB: selectedModel.memoryUsageGB,
            estimatedTokens: bundle.conversationHistory.reduce(0) { $0 + ($1.tokenCount ?? 0) },
            wouldCauseEviction: evictionCandidate != nil,
            evictionCandidate: evictionCandidate,
            relevantContext: relevantContext,
            shouldIncludeVault: analysis.needsVaultContext,
            shouldIncludeData: analysis.needsDataContext,
            shouldIncludeKanban: analysis.needsKanbanContext,
            shouldIncludeWorkflows: analysis.needsWorkflowContext,
            shouldIncludeTeam: analysis.needsTeamContext,
            shouldIncludeCode: analysis.needsCodeContext,
            decidedAt: Date(),
            orchestratorModel: "apple-fm"
        )
    }

    // MARK: - Query Analysis (Backend-Powered)

    private func analyzeQuery(_ query: String, context: ContextBundle) async -> QueryAnalysis {
        // Use backend's intelligent routing via Phi-3 intent classification
        do {
            // Call backend route endpoint
            let routeRequest = AgentRouteRequest(input: query)
            let response: AgentRouteResponse = try await ApiClient.shared.request(
                "/v1/agent/route",
                method: .post,
                body: routeRequest
            )

            // Map backend response to QueryAnalysis
            return mapBackendRouteToAnalysis(response, originalQuery: query, context: context)

        } catch {
            logger.warning("Backend routing failed, falling back to rule-based analysis: \(error)")
            // Fallback to rule-based analysis if backend unavailable
            return fallbackAnalyzeQuery(query, context: context)
        }
    }

    // Map backend route response to QueryAnalysis
    private func mapBackendRouteToAnalysis(
        _ response: AgentRouteResponse,
        originalQuery: String,
        context: ContextBundle
    ) -> QueryAnalysis {
        // Detect specialty from intent
        var specialty: ModelSpecialty? = nil
        var needsVault = false
        var needsData = false
        var needsKanban = false
        var needsWorkflow = false
        var needsTeam = false
        var needsCode = false

        // Map intent to specialty
        if response.intent == "code_edit" {
            specialty = .code
            needsCode = true
        } else if response.intent == "shell" {
            specialty = .code
            needsCode = true
        } else if response.intent == "question" {
            // Analyze query for context needs
            let lowercased = originalQuery.lowercased()
            if lowercased.contains("sql") || lowercased.contains("query") || lowercased.contains("database") {
                specialty = .data
                needsData = true
            } else if lowercased.contains("file") || lowercased.contains("document") || lowercased.contains("vault") {
                needsVault = true
            } else if lowercased.contains("task") || lowercased.contains("todo") || lowercased.contains("kanban") {
                needsKanban = true
            } else if lowercased.contains("workflow") || lowercased.contains("automation") {
                needsWorkflow = true
            } else if lowercased.contains("team") || lowercased.contains("message") {
                needsTeam = true
            }
        }

        // Determine complexity
        let complexity: QueryComplexity
        if response.next_action.contains("plan") {
            complexity = .high  // Requires planning = complex
        } else if originalQuery.split(separator: " ").count < 5 {
            complexity = .low
        } else {
            complexity = .medium
        }

        // Use backend's model hint as reasoning
        let reasoning = response.model_hint.map { "Backend suggests using \($0) for this task" }
            ?? "General query - using default model selection"

        return QueryAnalysis(
            complexity: complexity,
            specialty: specialty,
            reasoning: reasoning,
            confidence: response.confidence,
            needsVaultContext: needsVault,
            needsDataContext: needsData,
            needsKanbanContext: needsKanban,
            needsWorkflowContext: needsWorkflow,
            needsTeamContext: needsTeam,
            needsCodeContext: needsCode
        )
    }

    // Fallback rule-based analysis (original logic)
    private func fallbackAnalyzeQuery(_ query: String, context: ContextBundle) -> QueryAnalysis {
        let lowercased = query.lowercased()
        var complexity = QueryComplexity.medium
        var specialty: ModelSpecialty? = nil
        var reasoning = ""
        var confidence: Float = 0.7
        var needsVault = false
        var needsData = false
        var needsKanban = false
        var needsWorkflow = false
        var needsTeam = false
        var needsCode = false

        // Detect specialty
        if lowercased.contains("sql") || lowercased.contains("query") || lowercased.contains("database") || lowercased.contains("table") {
            specialty = .data
            needsData = true
            reasoning = "Query requires SQL/data analysis expertise"
            confidence = 0.9
        } else if lowercased.contains("code") || lowercased.contains("function") || lowercased.contains("python") || lowercased.contains("javascript") || lowercased.contains("swift") {
            specialty = .code
            needsCode = true
            reasoning = "Query requires code generation/analysis"
            confidence = 0.9
        } else if lowercased.contains("file") || lowercased.contains("document") || lowercased.contains("vault") {
            needsVault = true
            reasoning = "Query may require access to vault files"
            confidence = 0.8
        } else if lowercased.contains("task") || lowercased.contains("todo") || lowercased.contains("kanban") {
            needsKanban = true
            reasoning = "Query relates to task management"
            confidence = 0.8
        } else if lowercased.contains("workflow") || lowercased.contains("automation") {
            needsWorkflow = true
            reasoning = "Query relates to workflow automation"
            confidence = 0.8
        } else if lowercased.contains("team") || lowercased.contains("message") || lowercased.contains("channel") {
            needsTeam = true
            reasoning = "Query relates to team collaboration"
            confidence = 0.8
        }

        // Detect complexity
        if lowercased.contains("why") || lowercased.contains("explain") || lowercased.contains("reason") || lowercased.contains("analyze") {
            complexity = .high
            if reasoning.isEmpty {
                reasoning = "Complex reasoning query requires deeper analysis (fallback mode)"
            }
        } else if query.split(separator: " ").count < 5 {
            complexity = .low
            confidence = max(0.6, confidence)
        }

        return QueryAnalysis(
            complexity: complexity,
            specialty: specialty,
            reasoning: reasoning.isEmpty ? "General conversational query (fallback mode)" : reasoning,
            confidence: confidence,
            needsVaultContext: needsVault,
            needsDataContext: needsData,
            needsKanbanContext: needsKanban,
            needsWorkflowContext: needsWorkflow,
            needsTeamContext: needsTeam,
            needsCodeContext: needsCode
        )
    }

    // MARK: - Model Selection

    private func selectBestModel(
        analysis: QueryAnalysis,
        availableModels: [AvailableModel],
        systemResources: SystemResourceState
    ) -> AvailableModel {
        // Defense-in-depth: caller already guards !availableModels.isEmpty
        guard let fallbackModel = availableModels.first else {
            assertionFailure("selectBestModel called with empty availableModels array")
            return AvailableModel(
                id: "none", name: "none", displayName: "None",
                slotNumber: nil, isPinned: false, memoryUsageGB: nil,
                capabilities: .basic, isHealthy: false
            )
        }

        var scoredModels: [(model: AvailableModel, score: Float)] = []

        for model in availableModels {
            var score: Float = 0.5  // Base score

            // Specialty matching (high weight)
            if let specialty = analysis.specialty {
                switch specialty {
                case .data:
                    if model.capabilities.dataAnalysis {
                        score += 0.4
                    }
                    // Prefer phi-3.5 for data
                    if model.name.lowercased().contains("phi") {
                        score += 0.1
                    }

                case .code:
                    if model.capabilities.codeGeneration {
                        score += 0.4
                    }
                    // Prefer qwen-coder for code
                    if model.name.lowercased().contains("qwen") && model.name.lowercased().contains("coder") {
                        score += 0.1
                    }

                case .reasoning:
                    if model.capabilities.reasoning {
                        score += 0.4
                    }
                    // Prefer deepseek-r1 for reasoning
                    if model.name.lowercased().contains("deepseek") {
                        score += 0.1
                    }
                }
            }

            // Complexity matching
            switch analysis.complexity {
            case .low:
                // Prefer smaller, faster models
                if model.memoryUsageGB ?? 10 < 5 {
                    score += 0.2
                }
            case .medium:
                // No preference
                break
            case .high:
                // Prefer larger, more capable models
                if model.memoryUsageGB ?? 0 > 6 {
                    score += 0.2
                }
            }

            // Hot slot bonus (already loaded = faster)
            if model.slotNumber != nil {
                score += 0.15
            }

            // Resource availability check
            if let memoryGB = model.memoryUsageGB {
                if memoryGB > systemResources.availableMemoryGB {
                    score -= 0.5  // Heavy penalty if insufficient memory
                }
            }

            // Thermal state penalty
            if systemResources.thermalState == .serious || systemResources.thermalState == .critical {
                // Prefer smaller models when thermal is high
                if model.memoryUsageGB ?? 0 > 5 {
                    score -= 0.3
                }
            }

            // CPU usage penalty (avoid heavy models when CPU is maxed)
            if systemResources.cpuUsage > 0.8 {
                // High CPU load - prefer smaller/faster models
                if model.memoryUsageGB ?? 0 > 5 {
                    score -= 0.2
                }
            } else if systemResources.cpuUsage > 0.95 {
                // Critical CPU load - heavily penalize large models
                if model.memoryUsageGB ?? 0 > 3 {
                    score -= 0.4
                }
            }

            scoredModels.append((model, score))
        }

        // Sort by score descending
        scoredModels.sort { $0.score > $1.score }

        // Return highest scoring model
        return scoredModels.first?.model ?? fallbackModel
    }

    // MARK: - Hot Slot Management

    private func checkHotSlotRequirement(
        modelId: String,
        availableModels: [AvailableModel],
        systemResources: SystemResourceState
    ) -> (requiresHotSlot: Bool, evictionCandidate: String?) {
        // Check if model is already in a hot slot
        if let model = availableModels.first(where: { $0.id == modelId }),
           model.slotNumber != nil {
            return (false, nil)  // Already loaded
        }

        // Check if there are empty slots
        let occupiedSlots = systemResources.activeModels.count
        if occupiedSlots < 4 {
            return (true, nil)  // Need to load, but slot available
        }

        // All slots full - find eviction candidate (LRU unpinned)
        let unpinnedModels = systemResources.activeModels
            .filter { !$0.isPinned }
            .sorted { $0.lastUsedAt < $1.lastUsedAt }

        if let candidate = unpinnedModels.first {
            return (true, candidate.id)
        }

        // All slots pinned - cannot load
        return (true, nil)
    }

    // MARK: - Context Relevance

    private func determineRelevantContext(
        analysis: QueryAnalysis,
        bundle: ContextBundle
    ) -> [String] {
        var relevant: [String] = ["conversationHistory"]  // Always include history

        if analysis.needsVaultContext && bundle.vaultContext != nil {
            relevant.append("vault")
        }
        if analysis.needsDataContext && bundle.dataContext != nil {
            relevant.append("data")
        }
        if analysis.needsKanbanContext && bundle.kanbanContext != nil {
            relevant.append("kanban")
        }
        if analysis.needsWorkflowContext && bundle.workflowContext != nil {
            relevant.append("workflow")
        }
        if analysis.needsTeamContext && bundle.teamContext != nil {
            relevant.append("team")
        }
        if analysis.needsCodeContext && bundle.codeContext != nil {
            relevant.append("code")
        }

        return relevant
    }

    // MARK: - Decision Factors

    private func buildDecisionFactors(
        analysis: QueryAnalysis,
        selectedModel: AvailableModel,
        systemResources: SystemResourceState
    ) -> [DecisionFactor] {
        var factors: [DecisionFactor] = []

        // Complexity
        factors.append(DecisionFactor(
            factor: "query_complexity",
            weight: 0.7,
            value: "Complexity: \(analysis.complexity.rawValue)"
        ))

        // Specialty
        if let specialty = analysis.specialty {
            factors.append(DecisionFactor(
                factor: "model_specialty",
                weight: 0.9,
                value: "Specialty: \(specialty.rawValue)"
            ))
        }

        // Resource constraints
        if systemResources.memoryPressure > 0.7 {
            factors.append(DecisionFactor(
                factor: "memory_pressure",
                weight: 0.6,
                value: "High memory pressure (\(Int(systemResources.memoryPressure * 100))%)"
            ))
        }

        // Thermal state
        if systemResources.thermalState == .serious || systemResources.thermalState == .critical {
            factors.append(DecisionFactor(
                factor: "thermal_state",
                weight: 0.8,
                value: "Thermal state: \(systemResources.thermalState.rawValue)"
            ))
        }

        // Hot slot availability
        if selectedModel.slotNumber != nil {
            factors.append(DecisionFactor(
                factor: "hot_slot",
                weight: 0.5,
                value: "Model already loaded in slot \(selectedModel.slotNumber ?? -1)"
            ))
        }

        return factors
    }

    // MARK: - Fallback List

    private func buildFallbackList(
        primaryModel: AvailableModel,
        availableModels: [AvailableModel],
        analysis: QueryAnalysis
    ) -> [String] {
        // Exclude primary model
        let fallbacks = availableModels.filter { $0.id != primaryModel.id }

        // Prefer models in hot slots
        let hotSlotModels = fallbacks.filter { $0.slotNumber != nil }
        let otherModels = fallbacks.filter { $0.slotNumber == nil }

        // Combine and return IDs
        return (hotSlotModels + otherModels).prefix(3).map { $0.id }
    }
}

// MARK: - Query Analysis

struct QueryAnalysis {
    let complexity: QueryComplexity
    let specialty: ModelSpecialty?
    let reasoning: String
    let confidence: Float  // 0.0-1.0
    let needsVaultContext: Bool
    let needsDataContext: Bool
    let needsKanbanContext: Bool
    let needsWorkflowContext: Bool
    let needsTeamContext: Bool
    let needsCodeContext: Bool
}

enum QueryComplexity: String {
    case low = "Low"
    case medium = "Medium"
    case high = "High"
}

enum ModelSpecialty: String {
    case data = "Data/SQL"
    case code = "Code Generation"
    case reasoning = "Deep Reasoning"
}
