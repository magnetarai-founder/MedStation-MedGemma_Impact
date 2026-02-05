//
//  SemanticNode.swift
//  MagnetarStudio
//
//  Enhanced semantic node for intelligent context compression.
//  Addresses Gap 2: Full structure with decisions, todos, fileRefs, codeRefs.
//

import Foundation

// MARK: - Semantic Node

/// Compressed context node with full semantic structure.
/// Unlike lossy text summaries, these preserve structured meaning.
struct SemanticNode: Codable, Identifiable {
    let id: UUID

    /// What this node represents (e.g., "Q4 Budget Discussion")
    let concept: String

    /// Compressed but meaningful content
    let content: String

    /// 384-dimensional embedding for retrieval
    let embedding: [Float]

    /// Named entities referenced in this context
    let entities: [String]

    // MARK: - Structured Extractions (Gap 2 requirements)

    /// Decisions made during this conversation segment
    let decisions: [Decision]?

    /// Outstanding items extracted from the conversation
    let todos: [TodoItem]?

    /// Related file references
    let fileRefs: [UUID]?

    /// Code snippets discussed (MagnetarStudio-specific)
    let codeRefs: [CodeReference]?

    /// Related workflow IDs (MagnetarStudio-specific)
    let workflowRefs: [UUID]?

    /// Related Kanban task IDs (MagnetarStudio-specific)
    let kanbanRefs: [UUID]?

    // MARK: - Metadata

    /// Number of original messages compressed into this node
    let originalMessageCount: Int

    /// Relevance score (updated on access)
    var relevanceScore: Float

    /// When this node was created
    let createdAt: Date

    /// Last time this node was accessed/used
    var lastAccessed: Date

    /// Source message IDs that contributed to this node
    let sourceMessageIds: [UUID]

    /// Context tier this node belongs to
    var tier: ContextTier

    init(
        id: UUID = UUID(),
        concept: String,
        content: String,
        embedding: [Float] = [],
        entities: [String] = [],
        decisions: [Decision]? = nil,
        todos: [TodoItem]? = nil,
        fileRefs: [UUID]? = nil,
        codeRefs: [CodeReference]? = nil,
        workflowRefs: [UUID]? = nil,
        kanbanRefs: [UUID]? = nil,
        originalMessageCount: Int = 0,
        relevanceScore: Float = 1.0,
        createdAt: Date = Date(),
        lastAccessed: Date = Date(),
        sourceMessageIds: [UUID] = [],
        tier: ContextTier = .compressed
    ) {
        self.id = id
        self.concept = concept
        self.content = content
        self.embedding = embedding
        self.entities = entities
        self.decisions = decisions
        self.todos = todos
        self.fileRefs = fileRefs
        self.codeRefs = codeRefs
        self.workflowRefs = workflowRefs
        self.kanbanRefs = kanbanRefs
        self.originalMessageCount = originalMessageCount
        self.relevanceScore = relevanceScore
        self.createdAt = createdAt
        self.lastAccessed = lastAccessed
        self.sourceMessageIds = sourceMessageIds
        self.tier = tier
    }

    /// Generate REF token for this node
    var refToken: String {
        let shortId = String(id.uuidString.prefix(8))
        let safeConcept = concept
            .lowercased()
            .replacingOccurrences(of: " ", with: "_")
            .prefix(20)
        return "[REF:\(safeConcept)_\(shortId)]"
    }

    /// Estimated token count for this node's content
    var estimatedTokens: Int {
        // Rough estimate: ~4 characters per token
        return content.count / 4
    }

    /// Check if this node has any structured data
    var hasStructuredData: Bool {
        return (decisions?.isEmpty == false) ||
               (todos?.isEmpty == false) ||
               (fileRefs?.isEmpty == false) ||
               (codeRefs?.isEmpty == false) ||
               (workflowRefs?.isEmpty == false) ||
               (kanbanRefs?.isEmpty == false)
    }
}

// MARK: - Decision

/// A decision extracted from conversation context
struct Decision: Codable, Identifiable {
    let id: UUID
    let summary: String
    let madeAt: Date
    let confidence: Float
    let context: String?
    let relatedEntities: [String]

    init(
        id: UUID = UUID(),
        summary: String,
        madeAt: Date = Date(),
        confidence: Float = 1.0,
        context: String? = nil,
        relatedEntities: [String] = []
    ) {
        self.id = id
        self.summary = summary
        self.madeAt = madeAt
        self.confidence = confidence
        self.context = context
        self.relatedEntities = relatedEntities
    }
}

// MARK: - Todo Item

/// An outstanding item extracted from conversation
struct TodoItem: Codable, Identifiable {
    let id: UUID
    let description: String
    let priority: Priority
    let extractedAt: Date
    var completed: Bool
    var completedAt: Date?
    let assignee: String?
    let dueDate: Date?

    enum Priority: String, Codable, CaseIterable, Sendable {
        case low
        case medium
        case high
        case critical

        var sortOrder: Int {
            switch self {
            case .critical: return 4
            case .high: return 3
            case .medium: return 2
            case .low: return 1
            }
        }
    }

    init(
        id: UUID = UUID(),
        description: String,
        priority: Priority = .medium,
        extractedAt: Date = Date(),
        completed: Bool = false,
        completedAt: Date? = nil,
        assignee: String? = nil,
        dueDate: Date? = nil
    ) {
        self.id = id
        self.description = description
        self.priority = priority
        self.extractedAt = extractedAt
        self.completed = completed
        self.completedAt = completedAt
        self.assignee = assignee
        self.dueDate = dueDate
    }
}

// MARK: - Code Reference

/// A code snippet referenced in conversation (MagnetarStudio-specific)
struct CodeReference: Codable, Identifiable {
    let id: UUID
    let filePath: String
    let language: String
    let snippet: String
    let lineStart: Int?
    let lineEnd: Int?
    let description: String?
    let createdAt: Date

    init(
        id: UUID = UUID(),
        filePath: String,
        language: String,
        snippet: String,
        lineStart: Int? = nil,
        lineEnd: Int? = nil,
        description: String? = nil,
        createdAt: Date = Date()
    ) {
        self.id = id
        self.filePath = filePath
        self.language = language
        self.snippet = snippet
        self.lineStart = lineStart
        self.lineEnd = lineEnd
        self.description = description
        self.createdAt = createdAt
    }

    var lineRange: String? {
        guard let start = lineStart else { return nil }
        if let end = lineEnd, end != start {
            return "L\(start)-\(end)"
        }
        return "L\(start)"
    }
}

// MARK: - Semantic Node Builder

/// Helper for building SemanticNode from messages
struct SemanticNodeBuilder {
    private var concept: String = ""
    private var content: String = ""
    private var embedding: [Float] = []
    private var entities: [String] = []
    private var decisions: [Decision] = []
    private var todos: [TodoItem] = []
    private var fileRefs: [UUID] = []
    private var codeRefs: [CodeReference] = []
    private var workflowRefs: [UUID] = []
    private var kanbanRefs: [UUID] = []
    private var sourceMessageIds: [UUID] = []

    mutating func setConcept(_ concept: String) -> SemanticNodeBuilder {
        self.concept = concept
        return self
    }

    mutating func setContent(_ content: String) -> SemanticNodeBuilder {
        self.content = content
        return self
    }

    mutating func setEmbedding(_ embedding: [Float]) -> SemanticNodeBuilder {
        self.embedding = embedding
        return self
    }

    mutating func addEntity(_ entity: String) -> SemanticNodeBuilder {
        entities.append(entity)
        return self
    }

    mutating func addDecision(_ decision: Decision) -> SemanticNodeBuilder {
        decisions.append(decision)
        return self
    }

    mutating func addTodo(_ todo: TodoItem) -> SemanticNodeBuilder {
        todos.append(todo)
        return self
    }

    mutating func addFileRef(_ fileId: UUID) -> SemanticNodeBuilder {
        fileRefs.append(fileId)
        return self
    }

    mutating func addCodeRef(_ codeRef: CodeReference) -> SemanticNodeBuilder {
        codeRefs.append(codeRef)
        return self
    }

    mutating func addSourceMessageId(_ messageId: UUID) -> SemanticNodeBuilder {
        sourceMessageIds.append(messageId)
        return self
    }

    func build() -> SemanticNode {
        return SemanticNode(
            concept: concept,
            content: content,
            embedding: embedding,
            entities: entities,
            decisions: decisions.isEmpty ? nil : decisions,
            todos: todos.isEmpty ? nil : todos,
            fileRefs: fileRefs.isEmpty ? nil : fileRefs,
            codeRefs: codeRefs.isEmpty ? nil : codeRefs,
            workflowRefs: workflowRefs.isEmpty ? nil : workflowRefs,
            kanbanRefs: kanbanRefs.isEmpty ? nil : kanbanRefs,
            originalMessageCount: sourceMessageIds.count,
            sourceMessageIds: sourceMessageIds
        )
    }
}
