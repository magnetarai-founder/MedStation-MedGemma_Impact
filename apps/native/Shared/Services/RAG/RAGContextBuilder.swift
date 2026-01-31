//
//  RAGContextBuilder.swift
//  MagnetarStudio
//
//  Assembles RAG context for AI prompts.
//  Combines search results, history bridge, and conversation context.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "RAGContextBuilder")

// MARK: - RAG Context Builder

@MainActor
final class RAGContextBuilder: ObservableObject {

    // MARK: - Published State

    @Published private(set) var lastBuildAt: Date?
    @Published private(set) var lastContextTokens: Int = 0

    // MARK: - Dependencies

    private let searchService: SemanticSearchService
    private let compactService: CompactService
    private let tierManager: ContextTierManager
    private let predictor: ANEPredictor

    // MARK: - Singleton

    static let shared = RAGContextBuilder()

    // MARK: - Initialization

    init(
        searchService: SemanticSearchService? = nil,
        compactService: CompactService? = nil,
        tierManager: ContextTierManager? = nil,
        predictor: ANEPredictor? = nil
    ) {
        self.searchService = searchService ?? .shared
        self.compactService = compactService ?? .shared
        self.tierManager = tierManager ?? .shared
        self.predictor = predictor ?? .shared
    }

    // MARK: - Context Building

    /// Build complete RAG context for an AI prompt
    func buildContext(
        query: String,
        sessionId: UUID,
        recentMessages: [ChatMessage],
        budget: ContextBudget
    ) async throws -> BuiltRAGContext {
        let startTime = Date()

        // 1. Get ANE predictions
        let prediction = predictor.predictContextNeeds(
            currentWorkspace: .chat,
            recentQuery: query,
            activeFileId: nil
        )

        // 2. Perform semantic search
        let searchResults = try await searchService.hybridSearch(
            query: query,
            conversationId: sessionId,
            limit: 20
        )

        // 3. Get history bridge if available
        let historyBridge = compactService.getHistoryBridge(for: sessionId)

        // 4. Allocate budget across components
        let allocation = allocateBudget(
            budget: budget,
            hasHistoryBridge: historyBridge != nil,
            searchResultCount: searchResults.count,
            recentMessageCount: recentMessages.count
        )

        // 5. Build each context section
        let systemSection = buildSystemSection(allocation: allocation)
        let historySection = buildHistorySection(
            bridge: historyBridge,
            allocation: allocation
        )
        let ragSection = buildRAGSection(
            results: searchResults,
            allocation: allocation
        )
        let messagesSection = buildMessagesSection(
            messages: recentMessages,
            allocation: allocation
        )

        // 6. Combine sections
        let combinedContext = combineContext(
            system: systemSection,
            history: historySection,
            rag: ragSection,
            messages: messagesSection
        )

        // 7. Calculate final token count
        let totalTokens = estimateTokens(combinedContext)

        // Update state
        lastBuildAt = Date()
        lastContextTokens = totalTokens

        let duration = Date().timeIntervalSince(startTime)
        logger.info("[RAGContextBuilder] Built context: \(totalTokens) tokens in \(String(format: "%.2f", duration * 1000))ms")

        return BuiltRAGContext(
            fullContext: combinedContext,
            systemPrompt: systemSection,
            historyContext: historySection,
            ragContext: ragSection,
            messagesContext: messagesSection,
            searchResults: searchResults,
            historyBridge: historyBridge,
            prediction: prediction,
            totalTokens: totalTokens,
            budget: budget,
            buildDuration: duration
        )
    }

    /// Build minimal context (for quick queries)
    func buildMinimalContext(
        query: String,
        sessionId: UUID,
        recentMessages: [ChatMessage]
    ) async throws -> BuiltRAGContext {
        return try await buildContext(
            query: query,
            sessionId: sessionId,
            recentMessages: recentMessages,
            budget: .minimal
        )
    }

    /// Build context optimized for a specific model
    func buildContextForModel(
        query: String,
        sessionId: UUID,
        recentMessages: [ChatMessage],
        model: AIModelType
    ) async throws -> BuiltRAGContext {
        let budget = ContextBudget.forModel(model)
        return try await buildContext(
            query: query,
            sessionId: sessionId,
            recentMessages: recentMessages,
            budget: budget
        )
    }

    // MARK: - Section Builders

    /// Build system prompt section
    private func buildSystemSection(allocation: BudgetAllocation) -> String {
        // Base system prompt - can be customized
        return """
        You are a helpful AI assistant with access to conversation history and relevant context.
        When referencing previous context, be specific about what you're referring to.
        If you need more details from a [REF:...] reference, let the user know.
        """
    }

    /// Build history bridge section
    private func buildHistorySection(
        bridge: HistoryBridge?,
        allocation: BudgetAllocation
    ) -> String {
        guard let bridge = bridge else { return "" }
        guard allocation.historyTokens > 0 else { return "" }

        var section = "## Previous Conversation Summary\n\n"

        // Add summary (truncate if needed)
        let maxSummaryChars = allocation.historyTokens * 4  // ~4 chars per token
        let summary = String(bridge.summary.prefix(maxSummaryChars))
        section += summary

        // Add key topics if room
        if bridge.keyTopics.count > 0 && summary.count < maxSummaryChars - 100 {
            section += "\n\n**Key Topics:** \(bridge.keyTopics.joined(separator: ", "))"
        }

        return section
    }

    /// Build RAG results section
    private func buildRAGSection(
        results: [RAGSearchResult],
        allocation: BudgetAllocation
    ) -> String {
        guard !results.isEmpty else { return "" }
        guard allocation.ragTokens > 0 else { return "" }

        var section = "## Relevant Context\n\n"
        var usedTokens = 20  // Header overhead

        // Group by source for better organization
        let grouped = Dictionary(grouping: results) { $0.document.source }

        for source in RAGSource.allCases {
            guard let sourceResults = grouped[source], !sourceResults.isEmpty else { continue }

            section += "### \(source.displayName)\n"
            usedTokens += 10

            for result in sourceResults {
                let content = result.snippet ?? String(result.document.content.prefix(300))
                let contentTokens = content.count / 4

                if usedTokens + contentTokens > allocation.ragTokens {
                    break
                }

                if let title = result.document.metadata.title {
                    section += "**\(title)** (relevance: \(Int(result.similarity * 100))%)\n"
                }
                section += "\(content)\n\n"
                usedTokens += contentTokens + 10
            }

            if usedTokens >= allocation.ragTokens {
                break
            }
        }

        return section
    }

    /// Build recent messages section
    private func buildMessagesSection(
        messages: [ChatMessage],
        allocation: BudgetAllocation
    ) -> String {
        guard !messages.isEmpty else { return "" }

        var section = ""
        var usedTokens = 0
        var includedMessages: [ChatMessage] = []

        // Start from most recent
        for message in messages.reversed() {
            let messageTokens = message.content.count / 4 + 10  // +10 for role label
            if usedTokens + messageTokens > allocation.messagesTokens {
                break
            }
            includedMessages.insert(message, at: 0)
            usedTokens += messageTokens
        }

        for message in includedMessages {
            let role = message.role == .user ? "User" : "Assistant"
            section += "\(role): \(message.content)\n\n"
        }

        return section
    }

    /// Combine all context sections
    private func combineContext(
        system: String,
        history: String,
        rag: String,
        messages: String
    ) -> String {
        var combined = system

        if !history.isEmpty {
            combined += "\n\n" + history
        }

        if !rag.isEmpty {
            combined += "\n\n" + rag
        }

        // Messages typically go in the conversation, not combined here
        // But we track them for token counting

        return combined
    }

    // MARK: - Budget Allocation

    /// Allocate token budget across components
    private func allocateBudget(
        budget: ContextBudget,
        hasHistoryBridge: Bool,
        searchResultCount: Int,
        recentMessageCount: Int
    ) -> BudgetAllocation {
        let total = budget.totalTokens

        // Base allocations
        let systemTokens = min(200, Int(Float(total) * 0.05))
        let reserveTokens = Int(Float(total) * 0.1)
        var remaining = total - systemTokens - reserveTokens

        // History bridge gets allocation if present
        let historyTokens: Int
        if hasHistoryBridge {
            historyTokens = min(Int(Float(remaining) * 0.2), 500)
            remaining -= historyTokens
        } else {
            historyTokens = 0
        }

        // Split remaining between RAG and messages
        let ragTokens = Int(Float(remaining) * 0.5)
        let messagesTokens = remaining - ragTokens

        return BudgetAllocation(
            systemTokens: systemTokens,
            historyTokens: historyTokens,
            ragTokens: ragTokens,
            messagesTokens: messagesTokens,
            reserveTokens: reserveTokens
        )
    }

    // MARK: - Utilities

    /// Estimate token count for text
    private func estimateTokens(_ text: String) -> Int {
        return text.count / 4  // Rough estimate: ~4 chars per token
    }
}

// MARK: - Built RAG Context

/// Complete built context ready for AI consumption
struct BuiltRAGContext {
    let fullContext: String
    let systemPrompt: String
    let historyContext: String
    let ragContext: String
    let messagesContext: String
    let searchResults: [RAGSearchResult]
    let historyBridge: HistoryBridge?
    let prediction: ContextPrediction
    let totalTokens: Int
    let budget: ContextBudget
    let buildDuration: TimeInterval

    /// Get context formatted for API request
    func getMessages(userQuery: String) -> [(role: String, content: String)] {
        var messages: [(String, String)] = []

        // System message with full context
        messages.append(("system", fullContext))

        // Recent conversation messages would be added by the caller

        return messages
    }

    /// Check if context fits within budget
    var isWithinBudget: Bool {
        totalTokens <= budget.totalTokens
    }

    /// Percentage of budget used
    var budgetUtilization: Float {
        Float(totalTokens) / Float(budget.totalTokens) * 100
    }
}

// MARK: - Budget Allocation

/// Internal budget allocation across components
struct BudgetAllocation {
    let systemTokens: Int
    let historyTokens: Int
    let ragTokens: Int
    let messagesTokens: Int
    let reserveTokens: Int

    var total: Int {
        systemTokens + historyTokens + ragTokens + messagesTokens + reserveTokens
    }
}

// MARK: - Context Budget

/// Token budget configuration for different models
struct ContextBudget {
    let totalTokens: Int
    let name: String

    static let minimal = ContextBudget(totalTokens: 2000, name: "Minimal")
    static let appleFM = ContextBudget(totalTokens: 4000, name: "Apple FM")
    static let ollamaSmall = ContextBudget(totalTokens: 8000, name: "Ollama Small")
    static let ollamaMedium = ContextBudget(totalTokens: 16000, name: "Ollama Medium")
    static let ollamaLarge = ContextBudget(totalTokens: 32000, name: "Ollama Large")
    static let huggingFace = ContextBudget(totalTokens: 128000, name: "HuggingFace")
    static let claude = ContextBudget(totalTokens: 200000, name: "Claude")

    static func forModel(_ model: AIModelType) -> ContextBudget {
        switch model {
        case .appleFM:
            return .appleFM
        case .ollamaSmall:
            return .ollamaSmall
        case .ollamaMedium:
            return .ollamaMedium
        case .ollamaLarge:
            return .ollamaLarge
        case .huggingFace:
            return .huggingFace
        case .claude:
            return .claude
        case .custom(let tokens):
            return ContextBudget(totalTokens: tokens, name: "Custom")
        }
    }
}

// MARK: - AI Model Type

/// Supported AI model types
enum AIModelType {
    case appleFM
    case ollamaSmall
    case ollamaMedium
    case ollamaLarge
    case huggingFace
    case claude
    case custom(tokens: Int)
}

// MARK: - Context Builder Extensions

extension RAGContextBuilder {

    /// Build context with automatic model detection
    func buildContextAuto(
        query: String,
        sessionId: UUID,
        recentMessages: [ChatMessage],
        modelName: String?
    ) async throws -> BuiltRAGContext {
        let modelType = detectModelType(from: modelName)
        return try await buildContextForModel(
            query: query,
            sessionId: sessionId,
            recentMessages: recentMessages,
            model: modelType
        )
    }

    /// Detect model type from model name
    private func detectModelType(from name: String?) -> AIModelType {
        guard let name = name?.lowercased() else {
            return .ollamaSmall  // Default
        }

        if name.contains("claude") {
            return .claude
        } else if name.contains("llama") || name.contains("mistral") || name.contains("qwen") {
            // Estimate based on parameter count in name
            if name.contains("70b") || name.contains("72b") || name.contains("65b") {
                return .ollamaLarge
            } else if name.contains("13b") || name.contains("14b") || name.contains("7b") || name.contains("8b") {
                return .ollamaMedium
            } else {
                return .ollamaSmall
            }
        } else if name.contains("gguf") {
            return .huggingFace
        } else if name.contains("apple") || name.contains("fm") {
            return .appleFM
        }

        return .ollamaSmall
    }

    /// Quick context preview (for UI)
    func previewContext(
        query: String,
        sessionId: UUID
    ) async throws -> ContextPreview {
        let searchResults = try await searchService.search(
            query: query,
            conversationId: sessionId,
            limit: 5
        )

        let hasHistory = compactService.getHistoryBridge(for: sessionId) != nil

        return ContextPreview(
            relevantResultCount: searchResults.count,
            topSources: Array(Set(searchResults.map { $0.document.source })),
            hasHistoryBridge: hasHistory,
            estimatedTokens: searchResults.reduce(0) { $0 + $1.document.content.count / 4 }
        )
    }
}

// MARK: - Context Preview

/// Quick preview of available context (for UI)
struct ContextPreview {
    let relevantResultCount: Int
    let topSources: [RAGSource]
    let hasHistoryBridge: Bool
    let estimatedTokens: Int

    var summary: String {
        var parts: [String] = []
        parts.append("\(relevantResultCount) relevant items")
        if hasHistoryBridge {
            parts.append("history available")
        }
        parts.append("~\(estimatedTokens) tokens")
        return parts.joined(separator: ", ")
    }
}
