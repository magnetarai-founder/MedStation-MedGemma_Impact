//
//  ContextOptimizer.swift
//  MagnetarStudio
//
//  Optimizes context selection within token budgets.
//  Uses relevance scoring, ANE predictions, and smart truncation.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "ContextOptimizer")

// MARK: - Context Optimizer

@MainActor
final class ContextOptimizer: ObservableObject {

    // MARK: - Published State

    @Published private(set) var lastOptimizationAt: Date?
    @Published private(set) var lastBudgetUtilization: Float = 0
    @Published private(set) var optimizationCount: Int = 0

    // MARK: - Dependencies

    private let predictor: ANEPredictor
    private let smartForgetting: SmartForgetting
    private let embedder: HashEmbedder

    // MARK: - Configuration

    var configuration: OptimizerConfiguration = .default

    // MARK: - Singleton

    static let shared = ContextOptimizer()

    // MARK: - Initialization

    init(
        predictor: ANEPredictor? = nil,
        smartForgetting: SmartForgetting? = nil,
        embedder: HashEmbedder? = nil
    ) {
        self.predictor = predictor ?? .shared
        self.smartForgetting = smartForgetting ?? .shared
        self.embedder = embedder ?? .shared
    }

    // MARK: - Optimization

    /// Optimize a collection of context items to fit within budget
    func optimize(
        items: ContextItemCollection,
        budget: TokenBudget,
        query: String?
    ) -> OptimizationResult {
        let startTime = Date()

        // 1. Separate required and optional items
        let (required, optional) = separateItems(items)

        // 2. Check if required items alone exceed budget
        let requiredTokens = required.reduce(0) { $0 + $1.tokens }
        if requiredTokens > budget.total {
            logger.warning("[Optimizer] Required items (\(requiredTokens)) exceed budget (\(budget.total))")
            return truncateRequired(required, budget: budget)
        }

        // 3. Score optional items
        let scored = scoreItems(optional, query: query)

        // 4. Select items that fit
        var selected = required
        var usedTokens = requiredTokens
        let reserve = Int(Float(budget.total) * configuration.reservePercent)
        // Budget available for optional items (used for logging/debugging if needed)
        _ = budget.total - requiredTokens - reserve

        for item in scored {
            if usedTokens + item.tokens <= budget.total - reserve {
                selected.append(item)
                usedTokens += item.tokens
            } else if configuration.allowTruncation && item.metadata.canTruncate {
                // Try to fit a truncated version
                let remainingBudget = budget.total - reserve - usedTokens
                if remainingBudget > item.metadata.minTokens {
                    if let truncated = truncateItem(item, toTokens: remainingBudget) {
                        selected.append(truncated)
                        usedTokens += truncated.tokens
                    }
                }
            }
        }

        // 5. Apply type-based allocation limits
        selected = applyTypeLimits(selected, budget: budget)
        usedTokens = selected.reduce(0) { $0 + $1.tokens }

        // 6. Build result
        let excluded = items.items.filter { item in
            !selected.contains { $0.id == item.id }
        }

        let duration = Date().timeIntervalSince(startTime)
        lastOptimizationAt = Date()
        lastBudgetUtilization = Float(usedTokens) / Float(budget.total) * 100
        optimizationCount += 1

        logger.info("[Optimizer] Selected \(selected.count)/\(items.items.count) items, \(usedTokens)/\(budget.total) tokens (\(String(format: "%.1f", self.lastBudgetUtilization))%)")

        return OptimizationResult(
            included: selected,
            excluded: excluded,
            totalBudget: budget.total,
            usedBudget: usedTokens,
            duration: duration
        )
    }

    /// Optimize with automatic budget detection from model
    func optimizeForModel(
        items: ContextItemCollection,
        modelName: String,
        query: String?
    ) -> OptimizationResult {
        let budget = TokenBudget.forModel(modelName)
        return optimize(items: items, budget: budget, query: query)
    }

    // MARK: - Scoring

    /// Score items by relevance to query and user patterns
    private func scoreItems(_ items: [ContextItem], query: String?) -> [ContextItem] {
        guard !items.isEmpty else { return [] }

        // Get ANE predictions
        let prediction = predictor.predictContextNeeds(
            currentWorkspace: .chat,
            recentQuery: query,
            activeFileId: nil
        )

        // Query embedding for similarity
        let queryEmbedding = query.map { embedder.embed($0) }

        var scoredItems: [(ContextItem, Float)] = []

        for item in items {
            var score = item.combinedScore

            // Boost based on predicted topics
            if query != nil {
                for topic in prediction.likelyTopics {
                    if item.content.lowercased().contains(topic.lowercased()) {
                        score += 0.1
                    }
                }
            }

            // Boost based on semantic similarity
            if let queryEmbed = queryEmbedding {
                let itemEmbedding = embedder.embed(item.content)
                let similarity = HashEmbedder.cosineSimilarity(queryEmbed, itemEmbedding)
                score += similarity * 0.2
            }

            // Apply compression aggressiveness from ANE
            if prediction.compressionAggressiveness > 0.7 && item.type.canCompress {
                score *= (1.0 - prediction.compressionAggressiveness * 0.3)
            }

            scoredItems.append((item, min(1.0, score)))
        }

        // Sort by score and return
        return scoredItems
            .sorted { $0.1 > $1.1 }
            .map { item, score in
                ContextItem(
                    id: item.id,
                    type: item.type,
                    content: item.content,
                    tokens: item.tokens,
                    relevanceScore: score,
                    recencyScore: item.recencyScore,
                    sourceId: item.sourceId,
                    metadata: item.metadata
                )
            }
    }

    // MARK: - Item Management

    /// Separate required and optional items
    private func separateItems(_ collection: ContextItemCollection) -> ([ContextItem], [ContextItem]) {
        var required: [ContextItem] = []
        var optional: [ContextItem] = []

        for item in collection.items {
            if item.metadata.isRequired || item.type == .systemPrompt {
                required.append(item)
            } else {
                optional.append(item)
            }
        }

        return (required, optional)
    }

    /// Truncate required items to fit in budget (emergency only)
    private func truncateRequired(_ items: [ContextItem], budget: TokenBudget) -> OptimizationResult {
        var truncated: [ContextItem] = []
        var usedTokens = 0
        let perItemBudget = budget.total / max(1, items.count)

        for item in items {
            if item.tokens <= perItemBudget {
                truncated.append(item)
                usedTokens += item.tokens
            } else if item.metadata.canTruncate {
                if let truncatedItem = truncateItem(item, toTokens: perItemBudget) {
                    truncated.append(truncatedItem)
                    usedTokens += truncatedItem.tokens
                }
            } else {
                // Can't truncate, include anyway (will exceed budget)
                truncated.append(item)
                usedTokens += item.tokens
            }
        }

        return OptimizationResult(
            included: truncated,
            excluded: [],
            totalBudget: budget.total,
            usedBudget: usedTokens,
            duration: 0
        )
    }

    /// Truncate an item to fit within token limit
    private func truncateItem(_ item: ContextItem, toTokens maxTokens: Int) -> ContextItem? {
        guard maxTokens >= item.metadata.minTokens else { return nil }

        let truncatedContent = TokenCounter.truncateToFit(
            item.content,
            budget: maxTokens,
            addEllipsis: true
        )

        let newTokens = TokenCounter.count(truncatedContent)
        guard newTokens <= maxTokens else { return nil }

        return ContextItem(
            id: item.id,
            type: item.type,
            content: truncatedContent,
            tokens: newTokens,
            relevanceScore: item.relevanceScore * 0.9,  // Slight penalty for truncation
            recencyScore: item.recencyScore,
            sourceId: item.sourceId,
            metadata: item.metadata
        )
    }

    /// Apply type-based allocation limits
    private func applyTypeLimits(_ items: [ContextItem], budget: TokenBudget) -> [ContextItem] {
        var result: [ContextItem] = []
        var tokensByType: [ContextItemType: Int] = [:]

        for item in items {
            let typeLimit = configuration.maxTokensForType(item.type, totalBudget: budget.total)
            let currentTypeTokens = tokensByType[item.type, default: 0]

            if currentTypeTokens + item.tokens <= typeLimit {
                result.append(item)
                tokensByType[item.type, default: 0] += item.tokens
            }
        }

        return result
    }

    // MARK: - Context Assembly

    /// Build optimized context string for AI prompt
    func buildOptimizedContext(
        messages: [ChatMessage],
        themes: [ConversationTheme],
        semanticNodes: [SemanticNode],
        historyBridge: HistoryBridge?,
        ragResults: [RAGSearchResult],
        systemPrompt: String,
        query: String,
        budget: TokenBudget
    ) -> OptimizedContext {
        // 1. Convert everything to ContextItems
        var collection = ContextItemCollection()

        // System prompt (required)
        collection.add(.systemPrompt(systemPrompt))

        // History bridge (required if present)
        if let bridge = historyBridge {
            collection.add(.fromHistoryBridge(bridge))
        }

        // Recent messages
        let queryEmbedding = embedder.embed(query)
        for (index, message) in messages.enumerated() {
            let recency = Float(messages.count - index) / Float(messages.count)
            let msgEmbedding = embedder.embed(message.content)
            let relevance = HashEmbedder.cosineSimilarity(queryEmbedding, msgEmbedding)
            collection.add(.fromMessage(message, relevanceScore: relevance, recencyScore: recency))
        }

        // Themes
        for theme in themes {
            let relevance = HashEmbedder.cosineSimilarity(queryEmbedding, theme.embedding)
            collection.add(.fromTheme(theme, relevanceScore: relevance))
        }

        // Semantic nodes
        for node in semanticNodes {
            let relevance = HashEmbedder.cosineSimilarity(queryEmbedding, node.embedding)
            collection.add(.fromSemanticNode(node, relevanceScore: relevance))
        }

        // RAG results
        for result in ragResults {
            collection.add(.fromRAGResult(result))
        }

        // 2. Optimize
        let result = optimize(items: collection, budget: budget, query: query)

        // 3. Assemble context string
        let contextString = assembleContextString(result.included)

        return OptimizedContext(
            contextString: contextString,
            includedItems: result.included,
            excludedItems: result.excluded,
            totalTokens: result.usedBudget,
            budgetUtilization: result.utilizationPercent,
            typeDistribution: ContextItemCollection(items: result.included).tokenDistribution
        )
    }

    /// Assemble items into a formatted context string
    private func assembleContextString(_ items: [ContextItem]) -> String {
        var sections: [String] = []

        // Group by type for cleaner organization
        let grouped = Dictionary(grouping: items) { $0.type }

        // System prompt first
        if let systemItems = grouped[.systemPrompt] {
            sections.append(systemItems.map { $0.content }.joined(separator: "\n"))
        }

        // History bridge
        if let historyItems = grouped[.historyBridge] {
            sections.append("\n## Previous Context\n" + historyItems.map { $0.content }.joined(separator: "\n"))
        }

        // RAG/themes/semantic nodes as background
        let backgroundTypes: [ContextItemType] = [.theme, .semanticNode, .ragResult]
        var backgroundContent: [String] = []
        for type in backgroundTypes {
            if let typeItems = grouped[type], !typeItems.isEmpty {
                backgroundContent.append(contentsOf: typeItems.map { $0.content })
            }
        }
        if !backgroundContent.isEmpty {
            sections.append("\n## Relevant Background\n" + backgroundContent.joined(separator: "\n\n"))
        }

        // File/code context
        let contextTypes: [ContextItemType] = [.fileContext, .codeContext, .workflowContext, .kanbanContext]
        var contextContent: [String] = []
        for type in contextTypes {
            if let typeItems = grouped[type], !typeItems.isEmpty {
                contextContent.append(contentsOf: typeItems.map { $0.content })
            }
        }
        if !contextContent.isEmpty {
            sections.append("\n## Additional Context\n" + contextContent.joined(separator: "\n\n"))
        }

        // Messages handled separately by the caller (they go in the conversation)

        return sections.joined(separator: "\n")
    }
}

// MARK: - Optimization Result

struct OptimizationResult {
    let included: [ContextItem]
    let excluded: [ContextItem]
    let totalBudget: Int
    let usedBudget: Int
    let duration: TimeInterval

    var remainingBudget: Int { totalBudget - usedBudget }
    var utilizationPercent: Float { Float(usedBudget) / Float(totalBudget) * 100 }

    var includedCount: Int { included.count }
    var excludedCount: Int { excluded.count }
}

// MARK: - Optimized Context

struct OptimizedContext {
    let contextString: String
    let includedItems: [ContextItem]
    let excludedItems: [ContextItem]
    let totalTokens: Int
    let budgetUtilization: Float
    let typeDistribution: [ContextItemType: Int]

    /// Get messages that were included (for conversation history)
    var includedMessages: [ContextItem] {
        includedItems.filter { $0.type == .recentMessage }
    }

    /// Summary of what was included
    var summary: String {
        let counts = Dictionary(grouping: includedItems) { $0.type }
            .mapValues { $0.count }
            .map { "\($0.value) \($0.key.displayName.lowercased())" }
            .joined(separator: ", ")

        return "\(totalTokens) tokens (\(String(format: "%.0f", budgetUtilization))%): \(counts)"
    }
}

// MARK: - Optimizer Configuration

struct OptimizerConfiguration {
    /// Percentage of budget to reserve for response
    var reservePercent: Float = 0.1

    /// Allow truncating items to fit
    var allowTruncation: Bool = true

    /// Maximum percentage of budget for each type
    var typeLimits: [ContextItemType: Float] = [
        .systemPrompt: 0.1,
        .historyBridge: 0.2,
        .recentMessage: 0.4,
        .theme: 0.15,
        .semanticNode: 0.15,
        .ragResult: 0.2,
        .fileContext: 0.2,
        .codeContext: 0.2,
        .workflowContext: 0.1,
        .kanbanContext: 0.1,
        .teamContext: 0.1
    ]

    /// Get max tokens for a type
    func maxTokensForType(_ type: ContextItemType, totalBudget: Int) -> Int {
        let percent = typeLimits[type] ?? 0.2
        return Int(Float(totalBudget) * percent)
    }

    static let `default` = OptimizerConfiguration()

    static let aggressive = OptimizerConfiguration(
        reservePercent: 0.05,
        allowTruncation: true,
        typeLimits: [
            .systemPrompt: 0.05,
            .historyBridge: 0.1,
            .recentMessage: 0.5,
            .theme: 0.1,
            .semanticNode: 0.1,
            .ragResult: 0.15,
            .fileContext: 0.15,
            .codeContext: 0.15,
            .workflowContext: 0.05,
            .kanbanContext: 0.05,
            .teamContext: 0.05
        ]
    )

    static let conservative = OptimizerConfiguration(
        reservePercent: 0.15,
        allowTruncation: false,
        typeLimits: [
            .systemPrompt: 0.1,
            .historyBridge: 0.25,
            .recentMessage: 0.35,
            .theme: 0.2,
            .semanticNode: 0.2,
            .ragResult: 0.25,
            .fileContext: 0.25,
            .codeContext: 0.25,
            .workflowContext: 0.15,
            .kanbanContext: 0.15,
            .teamContext: 0.15
        ]
    )
}
