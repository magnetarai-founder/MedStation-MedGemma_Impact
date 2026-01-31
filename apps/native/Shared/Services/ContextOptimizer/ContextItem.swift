//
//  ContextItem.swift
//  MagnetarStudio
//
//  Unified context item model for optimization.
//  Wraps different content types with common scoring interface.
//

import Foundation

// MARK: - Context Item

/// A unified wrapper for different types of context content
struct ContextItem: Identifiable {
    let id: UUID
    let type: ContextItemType
    let content: String
    let tokens: Int
    let relevanceScore: Float
    let recencyScore: Float
    let sourceId: UUID?
    let metadata: ContextItemMetadata

    /// Combined score for ranking
    var combinedScore: Float {
        let typeWeight = type.priorityWeight
        return (relevanceScore * 0.5) + (recencyScore * 0.2) + (typeWeight * 0.3)
    }

    /// Priority for inclusion (higher = include first)
    var priority: Float {
        return combinedScore * (metadata.isRequired ? 2.0 : 1.0)
    }

    init(
        id: UUID = UUID(),
        type: ContextItemType,
        content: String,
        tokens: Int? = nil,
        relevanceScore: Float = 0.5,
        recencyScore: Float = 0.5,
        sourceId: UUID? = nil,
        metadata: ContextItemMetadata = ContextItemMetadata()
    ) {
        self.id = id
        self.type = type
        self.content = content
        self.tokens = tokens ?? TokenCounter.count(content)
        self.relevanceScore = relevanceScore
        self.recencyScore = recencyScore
        self.sourceId = sourceId
        self.metadata = metadata
    }
}

// MARK: - Context Item Type

/// Types of context items
enum ContextItemType: String, CaseIterable {
    case systemPrompt
    case historyBridge
    case recentMessage
    case theme
    case semanticNode
    case ragResult
    case fileContext
    case codeContext
    case workflowContext
    case kanbanContext
    case teamContext

    var displayName: String {
        switch self {
        case .systemPrompt: return "System"
        case .historyBridge: return "History"
        case .recentMessage: return "Message"
        case .theme: return "Theme"
        case .semanticNode: return "Context"
        case .ragResult: return "Search"
        case .fileContext: return "File"
        case .codeContext: return "Code"
        case .workflowContext: return "Workflow"
        case .kanbanContext: return "Task"
        case .teamContext: return "Team"
        }
    }

    /// Priority weight for scoring (0-1)
    var priorityWeight: Float {
        switch self {
        case .systemPrompt: return 1.0
        case .historyBridge: return 0.9
        case .recentMessage: return 0.95
        case .theme: return 0.8
        case .semanticNode: return 0.75
        case .ragResult: return 0.7
        case .fileContext: return 0.7
        case .codeContext: return 0.75
        case .workflowContext: return 0.6
        case .kanbanContext: return 0.6
        case .teamContext: return 0.5
        }
    }

    /// Whether this type should be compressed if space is tight
    var canCompress: Bool {
        switch self {
        case .systemPrompt, .recentMessage:
            return false
        default:
            return true
        }
    }

    /// Minimum allocation percentage
    var minAllocationPercent: Float {
        switch self {
        case .systemPrompt: return 0.05
        case .historyBridge: return 0.0
        case .recentMessage: return 0.2
        case .theme: return 0.0
        case .semanticNode: return 0.0
        case .ragResult: return 0.0
        case .fileContext: return 0.0
        case .codeContext: return 0.0
        case .workflowContext: return 0.0
        case .kanbanContext: return 0.0
        case .teamContext: return 0.0
        }
    }
}

// MARK: - Context Item Metadata

/// Metadata for a context item
struct ContextItemMetadata {
    var isRequired: Bool = false
    var canTruncate: Bool = true
    var minTokens: Int = 0
    var maxTokens: Int = Int.max
    var category: String?
    var tags: [String] = []
    var conversationId: UUID?
    var timestamp: Date?

    init(
        isRequired: Bool = false,
        canTruncate: Bool = true,
        minTokens: Int = 0,
        maxTokens: Int = Int.max,
        category: String? = nil,
        tags: [String] = [],
        conversationId: UUID? = nil,
        timestamp: Date? = nil
    ) {
        self.isRequired = isRequired
        self.canTruncate = canTruncate
        self.minTokens = minTokens
        self.maxTokens = maxTokens
        self.category = category
        self.tags = tags
        self.conversationId = conversationId
        self.timestamp = timestamp
    }
}

// MARK: - Context Item Builders

extension ContextItem {

    /// Create from a chat message
    static func fromMessage(
        _ message: ChatMessage,
        relevanceScore: Float = 0.5,
        recencyScore: Float = 0.5
    ) -> ContextItem {
        let tokens = TokenEstimation.forMessage(message)
        return ContextItem(
            type: .recentMessage,
            content: message.content,
            tokens: tokens,
            relevanceScore: relevanceScore,
            recencyScore: recencyScore,
            sourceId: message.id,
            metadata: ContextItemMetadata(
                isRequired: false,
                canTruncate: false,  // Don't truncate messages
                timestamp: message.timestamp
            )
        )
    }

    /// Create from a conversation theme
    static func fromTheme(
        _ theme: ConversationTheme,
        relevanceScore: Float
    ) -> ContextItem {
        let tokens = TokenEstimation.forTheme(theme)
        let recencyScore = calculateRecencyScore(theme.lastAccessed)

        return ContextItem(
            type: .theme,
            content: formatTheme(theme),
            tokens: tokens,
            relevanceScore: relevanceScore,
            recencyScore: recencyScore,
            sourceId: theme.id,
            metadata: ContextItemMetadata(
                canTruncate: true,
                category: theme.topic,
                timestamp: theme.lastAccessed
            )
        )
    }

    /// Create from a semantic node
    static func fromSemanticNode(
        _ node: SemanticNode,
        relevanceScore: Float
    ) -> ContextItem {
        let tokens = TokenEstimation.forSemanticNode(node)
        let recencyScore = calculateRecencyScore(node.lastAccessed)

        return ContextItem(
            type: .semanticNode,
            content: formatSemanticNode(node),
            tokens: tokens,
            relevanceScore: relevanceScore,
            recencyScore: recencyScore,
            sourceId: node.id,
            metadata: ContextItemMetadata(
                canTruncate: true,
                category: node.concept,
                timestamp: node.lastAccessed
            )
        )
    }

    /// Create from history bridge
    static func fromHistoryBridge(_ bridge: HistoryBridge) -> ContextItem {
        let tokens = TokenEstimation.forHistoryBridge(bridge)

        return ContextItem(
            type: .historyBridge,
            content: bridge.formatForPrompt(),
            tokens: tokens,
            relevanceScore: 0.9,  // History is always relevant
            recencyScore: 0.8,
            metadata: ContextItemMetadata(
                isRequired: true,
                canTruncate: true,
                minTokens: 50,
                timestamp: bridge.createdAt
            )
        )
    }

    /// Create from RAG search result
    static func fromRAGResult(_ result: RAGSearchResult) -> ContextItem {
        let recencyScore = calculateRecencyScore(result.document.createdAt)

        return ContextItem(
            type: .ragResult,
            content: result.snippet ?? result.document.content,
            tokens: result.document.content.count / 4,
            relevanceScore: result.similarity,
            recencyScore: recencyScore,
            sourceId: result.document.id,
            metadata: ContextItemMetadata(
                canTruncate: true,
                category: result.document.source.rawValue,
                timestamp: result.document.createdAt
            )
        )
    }

    /// Create system prompt item
    static func systemPrompt(_ content: String) -> ContextItem {
        return ContextItem(
            type: .systemPrompt,
            content: content,
            relevanceScore: 1.0,
            recencyScore: 1.0,
            metadata: ContextItemMetadata(
                isRequired: true,
                canTruncate: false
            )
        )
    }

    /// Create file context item
    static func fromFile(
        content: String,
        filename: String,
        fileId: UUID,
        relevanceScore: Float
    ) -> ContextItem {
        return ContextItem(
            type: .fileContext,
            content: "File: \(filename)\n\(content)",
            relevanceScore: relevanceScore,
            recencyScore: 0.5,
            sourceId: fileId,
            metadata: ContextItemMetadata(
                canTruncate: true,
                category: "file"
            )
        )
    }

    // MARK: - Helpers

    private static func calculateRecencyScore(_ date: Date) -> Float {
        let hours = Date().timeIntervalSince(date) / 3600
        return Float(max(0, 1 - (hours / 168)))  // Decay over 1 week
    }

    private static func formatTheme(_ theme: ConversationTheme) -> String {
        var parts: [String] = []
        parts.append("**\(theme.topic)**")
        parts.append(theme.content)

        if !theme.keyPoints.isEmpty {
            parts.append("Key points: " + theme.keyPoints.joined(separator: "; "))
        }

        return parts.joined(separator: "\n")
    }

    private static func formatSemanticNode(_ node: SemanticNode) -> String {
        var parts: [String] = []
        parts.append("**\(node.concept)**")
        parts.append(node.content)

        if let decisions = node.decisions, !decisions.isEmpty {
            parts.append("Decisions: " + decisions.map { $0.summary }.joined(separator: "; "))
        }

        if let todos = node.todos, !todos.isEmpty {
            let pending = todos.filter { !$0.completed }
            if !pending.isEmpty {
                parts.append("Outstanding: " + pending.map { $0.description }.joined(separator: "; "))
            }
        }

        return parts.joined(separator: "\n")
    }
}

// MARK: - Context Item Collection

/// A collection of context items with utilities
struct ContextItemCollection {
    var items: [ContextItem]

    var totalTokens: Int {
        items.reduce(0) { $0 + $1.tokens }
    }

    var requiredTokens: Int {
        items.filter { $0.metadata.isRequired }.reduce(0) { $0 + $1.tokens }
    }

    /// Get items sorted by priority
    func sortedByPriority() -> [ContextItem] {
        items.sorted { $0.priority > $1.priority }
    }

    /// Get items of a specific type
    func items(ofType type: ContextItemType) -> [ContextItem] {
        items.filter { $0.type == type }
    }

    /// Get items that fit within a budget
    func itemsFitting(budget: Int) -> [ContextItem] {
        var result: [ContextItem] = []
        var remaining = budget

        for item in sortedByPriority() {
            if item.tokens <= remaining {
                result.append(item)
                remaining -= item.tokens
            }
        }

        return result
    }

    /// Distribution by type
    var typeDistribution: [ContextItemType: Int] {
        var dist: [ContextItemType: Int] = [:]
        for item in items {
            dist[item.type, default: 0] += 1
        }
        return dist
    }

    /// Token distribution by type
    var tokenDistribution: [ContextItemType: Int] {
        var dist: [ContextItemType: Int] = [:]
        for item in items {
            dist[item.type, default: 0] += item.tokens
        }
        return dist
    }

    init(items: [ContextItem] = []) {
        self.items = items
    }

    mutating func add(_ item: ContextItem) {
        items.append(item)
    }

    mutating func addAll(_ newItems: [ContextItem]) {
        items.append(contentsOf: newItems)
    }

    mutating func remove(id: UUID) {
        items.removeAll { $0.id == id }
    }

    mutating func clear() {
        items.removeAll()
    }
}
