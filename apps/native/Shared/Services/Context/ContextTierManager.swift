//
//  ContextTierManager.swift
//  MagnetarStudio
//
//  Manages multi-tier memory architecture for context management.
//  Orchestrates content flow between immediate, themes, graph, compressed, and archived tiers.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "ContextTierManager")

// MARK: - Context Tier Manager

@MainActor
final class ContextTierManager: ObservableObject {

    // MARK: - Published State

    @Published private(set) var tierStats: TierStatistics = TierStatistics()
    @Published private(set) var lastPromotionAt: Date?
    @Published private(set) var lastDemotionAt: Date?

    // MARK: - Dependencies

    private let storageService: ConversationStorageService
    private let embedder: HashEmbedder
    private let predictor: ANEPredictor

    // MARK: - Configuration

    /// Token limits per tier (for small models like Apple FM)
    var tierBudgets: [ContextTier: Int] = [
        .immediate: 1500,
        .themes: 800,
        .graph: 300,
        .compressed: 200,
        .archived: 0  // Not included in prompt
    ]

    /// Maximum items per tier
    var tierItemLimits: [ContextTier: Int] = [
        .immediate: 15,
        .themes: 5,
        .graph: 20,
        .compressed: 50,
        .archived: 1000
    ]

    /// Age thresholds for automatic demotion (hours)
    var demotionThresholds: [ContextTier: TimeInterval] = [
        .immediate: 2,      // 2 hours → themes
        .themes: 24,        // 1 day → graph
        .graph: 168,        // 1 week → compressed
        .compressed: 720    // 30 days → archived
    ]

    // MARK: - Singleton

    static let shared = ContextTierManager()

    // MARK: - Initialization

    init(
        storageService: ConversationStorageService? = nil,
        embedder: HashEmbedder? = nil,
        predictor: ANEPredictor? = nil
    ) {
        self.storageService = storageService ?? .shared
        self.embedder = embedder ?? .shared
        self.predictor = predictor ?? .shared
    }

    // MARK: - Tier Assignment

    /// Determine appropriate tier for content based on characteristics
    func assignTier(for item: TierableContent) -> ContextTier {
        let age = Date().timeIntervalSince(item.lastAccessed) / 3600  // hours

        // Check age thresholds
        for tier in ContextTier.allCases {
            if let threshold = demotionThresholds[tier], age < threshold {
                return tier
            }
        }

        // Default to archived for very old content
        return .archived
    }

    /// Assign tier with relevance consideration
    func assignTier(
        for item: TierableContent,
        relevanceToQuery: Float,
        userPatternScore: Float
    ) -> ContextTier {
        let baseTier = assignTier(for: item)

        // Boost tier for highly relevant content
        if relevanceToQuery > 0.8 || userPatternScore > 0.7 {
            return promoteTier(baseTier)
        }

        // Demote for low relevance old content
        if relevanceToQuery < 0.3 && item.ageHours > 48 {
            return demoteTier(baseTier)
        }

        return baseTier
    }

    // MARK: - Content Organization

    /// Organize content across tiers for a session
    func organizeContent(
        for sessionId: UUID,
        messages: [ChatMessage],
        themes: [ConversationTheme],
        semanticNodes: [SemanticNode],
        currentQuery: String?
    ) -> TieredContent {
        var tiered = TieredContent()

        // Query embedding for relevance scoring
        let queryEmbedding = currentQuery.map { embedder.embed($0) }

        // 1. Organize messages (immediate tier)
        let recentMessages = messages.suffix(tierItemLimits[.immediate] ?? 15)
        for message in recentMessages {
            tiered.immediate.append(.message(message))
        }

        // 2. Organize themes
        let rankedThemes = rankThemes(themes, queryEmbedding: queryEmbedding)
        for (theme, score) in rankedThemes.prefix(tierItemLimits[.themes] ?? 5) {
            if score > 0.3 {
                tiered.themes.append(.theme(theme))
            } else {
                tiered.compressed.append(.theme(theme))
            }
        }

        // 3. Organize semantic nodes
        let rankedNodes = rankSemanticNodes(semanticNodes, queryEmbedding: queryEmbedding)
        for (node, score) in rankedNodes {
            let tier = determineTierForNode(node, relevanceScore: score)
            switch tier {
            case .immediate:
                tiered.immediate.append(.semanticNode(node))
            case .themes:
                tiered.themes.append(.semanticNode(node))
            case .graph:
                tiered.graph.append(.semanticNode(node))
            case .compressed:
                tiered.compressed.append(.semanticNode(node))
            case .archived:
                tiered.archived.append(.semanticNode(node))
            }
        }

        // 4. Load session graph for graph tier
        if let graph = storageService.loadSessionGraph(sessionId) {
            tiered.graph.append(.graph(graph))
        }

        // Update statistics
        updateStats(tiered)

        return tiered
    }

    // MARK: - Token Budget

    /// Build context within token budget
    func buildContextWithinBudget(
        tiered: TieredContent,
        totalBudget: Int,
        priorityTiers: [ContextTier] = [.immediate, .themes, .graph]
    ) -> BudgetedContext {
        var remaining = totalBudget
        var included: [TieredContentItem] = []
        var excluded: [TieredContentItem] = []

        // Process tiers in priority order
        for tier in priorityTiers {
            let items = tiered.items(for: tier)
            let tierBudget = min(remaining, tierBudgets[tier] ?? 0)

            var tierUsed = 0
            for item in items {
                let itemTokens = item.estimatedTokens
                if tierUsed + itemTokens <= tierBudget {
                    included.append(item)
                    tierUsed += itemTokens
                } else {
                    excluded.append(item)
                }
            }

            remaining -= tierUsed
        }

        return BudgetedContext(
            included: included,
            excluded: excluded,
            totalBudget: totalBudget,
            usedBudget: totalBudget - remaining
        )
    }

    // MARK: - Promotion/Demotion

    /// Promote content to higher tier
    func promoteTier(_ tier: ContextTier) -> ContextTier {
        switch tier {
        case .archived: return .compressed
        case .compressed: return .graph
        case .graph: return .themes
        case .themes: return .immediate
        case .immediate: return .immediate
        }
    }

    /// Demote content to lower tier
    func demoteTier(_ tier: ContextTier) -> ContextTier {
        switch tier {
        case .immediate: return .themes
        case .themes: return .graph
        case .graph: return .compressed
        case .compressed: return .archived
        case .archived: return .archived
        }
    }

    /// Promote an item based on access
    func promoteOnAccess(_ item: TierableContent, sessionId: UUID) {
        let currentTier = item.tier
        let newTier = promoteTier(currentTier)

        if newTier != currentTier {
            logger.debug("[TierManager] Promoting item from \(currentTier.rawValue) to \(newTier.rawValue)")
            lastPromotionAt = Date()
            // Note: Actual tier update would happen in storage layer
        }
    }

    /// Run periodic demotion check
    func runDemotionCheck(for sessionId: UUID) async {
        let themes = storageService.loadThemes(sessionId)
        let nodes = storageService.loadSemanticNodes(sessionId)

        var demotions = 0

        // Check themes for demotion
        for theme in themes {
            let age = Date().timeIntervalSince(theme.lastAccessed) / 3600
            if age > (demotionThresholds[.themes] ?? 24) {
                demotions += 1
                // Would update theme tier in storage
            }
        }

        // Check nodes for demotion
        for node in nodes {
            let age = Date().timeIntervalSince(node.lastAccessed) / 3600
            let threshold = demotionThresholds[node.tier] ?? 168
            if age > threshold {
                demotions += 1
                // Would update node tier in storage
            }
        }

        if demotions > 0 {
            lastDemotionAt = Date()
            logger.info("[TierManager] Demoted \(demotions) items")
        }
    }

    // MARK: - Ranking

    /// Rank themes by relevance to current query
    private func rankThemes(
        _ themes: [ConversationTheme],
        queryEmbedding: [Float]?
    ) -> [(ConversationTheme, Float)] {
        guard let queryEmbed = queryEmbedding else {
            // No query - rank by recency
            return themes.map { ($0, $0.relevanceScore) }
        }

        return themes.map { theme in
            let similarity = HashEmbedder.cosineSimilarity(theme.embedding, queryEmbed)
            let recency = recencyScore(theme.lastAccessed)
            let combined = (similarity * 0.6) + (recency * 0.2) + (theme.relevanceScore * 0.2)
            return (theme, combined)
        }.sorted { $0.1 > $1.1 }
    }

    /// Rank semantic nodes by relevance
    private func rankSemanticNodes(
        _ nodes: [SemanticNode],
        queryEmbedding: [Float]?
    ) -> [(SemanticNode, Float)] {
        guard let queryEmbed = queryEmbedding else {
            return nodes.map { ($0, $0.relevanceScore) }
        }

        return nodes.map { node in
            let similarity = HashEmbedder.cosineSimilarity(node.embedding, queryEmbed)
            let recency = recencyScore(node.lastAccessed)

            // Boost for structured content
            var structureBoost: Float = 0
            if node.decisions != nil { structureBoost += 0.1 }
            if node.todos != nil { structureBoost += 0.1 }
            if node.codeRefs != nil { structureBoost += 0.05 }

            let combined = (similarity * 0.5) + (recency * 0.2) + (node.relevanceScore * 0.2) + structureBoost
            return (node, combined)
        }.sorted { $0.1 > $1.1 }
    }

    /// Calculate recency score (0-1)
    private func recencyScore(_ date: Date) -> Float {
        let hours = Date().timeIntervalSince(date) / 3600
        return Float(max(0, 1 - (hours / 168)))  // Decay over 1 week
    }

    /// Determine tier for semantic node based on characteristics
    private func determineTierForNode(_ node: SemanticNode, relevanceScore: Float) -> ContextTier {
        // High relevance = immediate/themes
        if relevanceScore > 0.7 {
            return node.hasStructuredData ? .immediate : .themes
        }

        // Medium relevance = graph/compressed
        if relevanceScore > 0.4 {
            return .graph
        }

        // Low relevance = compressed/archived
        let age = Date().timeIntervalSince(node.lastAccessed) / 3600
        if age > 168 {  // Older than 1 week
            return .archived
        }

        return .compressed
    }

    // MARK: - Statistics

    /// Update tier statistics
    private func updateStats(_ tiered: TieredContent) {
        tierStats = TierStatistics(
            immediateCount: tiered.immediate.count,
            themesCount: tiered.themes.count,
            graphCount: tiered.graph.count,
            compressedCount: tiered.compressed.count,
            archivedCount: tiered.archived.count,
            immediateTokens: tiered.immediate.reduce(0) { $0 + $1.estimatedTokens },
            themesTokens: tiered.themes.reduce(0) { $0 + $1.estimatedTokens },
            graphTokens: tiered.graph.reduce(0) { $0 + $1.estimatedTokens }
        )
    }
}

// MARK: - Tierable Content Protocol

protocol TierableContent {
    var lastAccessed: Date { get }
    var tier: ContextTier { get }
    var ageHours: TimeInterval { get }
}

extension TierableContent {
    var ageHours: TimeInterval {
        return Date().timeIntervalSince(lastAccessed) / 3600
    }
}

// Make existing types conform
extension ConversationTheme: TierableContent {
    var tier: ContextTier { .themes }
}

extension SemanticNode: TierableContent {
    // tier is already a property
}

// MARK: - Tiered Content

/// Content organized by tier
struct TieredContent {
    var immediate: [TieredContentItem] = []
    var themes: [TieredContentItem] = []
    var graph: [TieredContentItem] = []
    var compressed: [TieredContentItem] = []
    var archived: [TieredContentItem] = []

    func items(for tier: ContextTier) -> [TieredContentItem] {
        switch tier {
        case .immediate: return immediate
        case .themes: return themes
        case .graph: return graph
        case .compressed: return compressed
        case .archived: return archived
        }
    }

    var totalItems: Int {
        immediate.count + themes.count + graph.count + compressed.count + archived.count
    }

    var totalTokens: Int {
        [immediate, themes, graph, compressed]
            .flatMap { $0 }
            .reduce(0) { $0 + $1.estimatedTokens }
    }
}

// MARK: - Tiered Content Item

enum TieredContentItem {
    case message(ChatMessage)
    case theme(ConversationTheme)
    case semanticNode(SemanticNode)
    case graph(SessionGraph)
    case file(FileReference)

    var estimatedTokens: Int {
        switch self {
        case .message(let msg):
            return msg.content.count / 4
        case .theme(let theme):
            return theme.content.count / 4
        case .semanticNode(let node):
            return node.content.count / 4
        case .graph(let graph):
            // Estimate based on node count
            return graph.nodes.count * 20
        case .file(let file):
            return (file.processedContent?.count ?? 0) / 4
        }
    }

    var contentPreview: String {
        switch self {
        case .message(let msg):
            return String(msg.content.prefix(100))
        case .theme(let theme):
            return theme.topic
        case .semanticNode(let node):
            return node.concept
        case .graph:
            return "Session Graph"
        case .file(let file):
            return file.filename
        }
    }
}

// MARK: - Budgeted Context

struct BudgetedContext {
    let included: [TieredContentItem]
    let excluded: [TieredContentItem]
    let totalBudget: Int
    let usedBudget: Int

    var remainingBudget: Int { totalBudget - usedBudget }
    var utilizationPercent: Float { Float(usedBudget) / Float(totalBudget) * 100 }

    /// Format included content for AI prompt
    func formatForPrompt() -> String {
        var sections: [String] = []

        // Group by type
        let messages = included.compactMap { if case .message(let m) = $0 { return m } else { return nil } }
        let themes = included.compactMap { if case .theme(let t) = $0 { return t } else { return nil } }
        let nodes = included.compactMap { if case .semanticNode(let n) = $0 { return n } else { return nil } }

        // Format messages
        if !messages.isEmpty {
            sections.append("## Recent Conversation")
            for msg in messages {
                let role = msg.role == .user ? "User" : "Assistant"
                sections.append("\(role): \(msg.content)")
            }
        }

        // Format themes
        if !themes.isEmpty {
            sections.append("\n## Background Context")
            for theme in themes {
                sections.append("**\(theme.topic)**: \(theme.content)")
            }
        }

        // Format semantic nodes
        if !nodes.isEmpty {
            sections.append("\n## Relevant History")
            for node in nodes {
                sections.append("- \(node.concept): \(String(node.content.prefix(200)))")
            }
        }

        return sections.joined(separator: "\n")
    }
}

// MARK: - Tier Statistics

struct TierStatistics {
    var immediateCount: Int = 0
    var themesCount: Int = 0
    var graphCount: Int = 0
    var compressedCount: Int = 0
    var archivedCount: Int = 0

    var immediateTokens: Int = 0
    var themesTokens: Int = 0
    var graphTokens: Int = 0

    var totalActiveCount: Int {
        immediateCount + themesCount + graphCount
    }

    var totalActiveTokens: Int {
        immediateTokens + themesTokens + graphTokens
    }

    var distribution: [ContextTier: Int] {
        [
            .immediate: immediateCount,
            .themes: themesCount,
            .graph: graphCount,
            .compressed: compressedCount,
            .archived: archivedCount
        ]
    }
}
