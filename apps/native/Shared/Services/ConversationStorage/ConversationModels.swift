//
//  ConversationModels.swift
//  MagnetarStudio
//
//  Data models for hierarchical conversation storage.
//  Ported from MagnetarAI-iPad with enhancements for MagnetarStudio.
//

import Foundation

// MARK: - Conversation Hierarchy

/// Complete hierarchy for a conversation including all stored context
struct ConversationHierarchy: Codable, Identifiable {
    let id: UUID
    var metadata: ConversationMetadata
    var themes: [ConversationTheme]
    var sessionGraph: SessionGraph?
    var compressedContext: CompressedContext?
    var fileReferences: [FileReference]
    var referenceIndex: [String: ReferencePointer]

    init(
        id: UUID = UUID(),
        metadata: ConversationMetadata? = nil,
        themes: [ConversationTheme] = [],
        sessionGraph: SessionGraph? = nil,
        compressedContext: CompressedContext? = nil,
        fileReferences: [FileReference] = [],
        referenceIndex: [String: ReferencePointer] = [:]
    ) {
        self.id = id
        self.metadata = metadata ?? ConversationMetadata(id: id)
        self.themes = themes
        self.sessionGraph = sessionGraph
        self.compressedContext = compressedContext
        self.fileReferences = fileReferences
        self.referenceIndex = referenceIndex
    }
}

// MARK: - Conversation Metadata

/// Metadata for a conversation
struct ConversationMetadata: Codable, Identifiable {
    let id: UUID
    var title: String
    var createdAt: Date
    var updatedAt: Date
    var messageCount: Int
    var primaryTopics: [String]
    var userIntent: String?
    var isCompacted: Bool
    var compactedAt: Date?

    // MagnetarStudio-specific
    var linkedWorkflowIds: [UUID]
    var linkedKanbanTaskIds: [UUID]
    var linkedVaultFileIds: [UUID]
    var preferredModelId: String?

    init(
        id: UUID = UUID(),
        title: String = "New Conversation",
        createdAt: Date = Date(),
        updatedAt: Date = Date(),
        messageCount: Int = 0,
        primaryTopics: [String] = [],
        userIntent: String? = nil,
        isCompacted: Bool = false,
        compactedAt: Date? = nil,
        linkedWorkflowIds: [UUID] = [],
        linkedKanbanTaskIds: [UUID] = [],
        linkedVaultFileIds: [UUID] = [],
        preferredModelId: String? = nil
    ) {
        self.id = id
        self.title = title
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.messageCount = messageCount
        self.primaryTopics = primaryTopics
        self.userIntent = userIntent
        self.isCompacted = isCompacted
        self.compactedAt = compactedAt
        self.linkedWorkflowIds = linkedWorkflowIds
        self.linkedKanbanTaskIds = linkedKanbanTaskIds
        self.linkedVaultFileIds = linkedVaultFileIds
        self.preferredModelId = preferredModelId
    }
}

// MARK: - Conversation Theme

/// A theme extracted from conversation messages
struct ConversationTheme: Codable, Identifiable {
    let id: UUID
    var topic: String
    var content: String
    var entities: [String]
    var keyPoints: [String]
    var embedding: [Float]
    var messageIds: [UUID]
    var relevanceScore: Float
    var createdAt: Date
    var lastAccessed: Date

    init(
        id: UUID = UUID(),
        topic: String,
        content: String,
        entities: [String] = [],
        keyPoints: [String] = [],
        embedding: [Float] = [],
        messageIds: [UUID] = [],
        relevanceScore: Float = 1.0,
        createdAt: Date = Date(),
        lastAccessed: Date = Date()
    ) {
        self.id = id
        self.topic = topic
        self.content = content
        self.entities = entities
        self.keyPoints = keyPoints
        self.embedding = embedding
        self.messageIds = messageIds
        self.relevanceScore = relevanceScore
        self.createdAt = createdAt
        self.lastAccessed = lastAccessed
    }
}

// MARK: - Compressed Context

/// Compressed context from older messages
struct CompressedContext: Codable {
    var summary: String
    var entities: [String]
    var decisions: [String]
    var todos: [String]
    var originalMessageCount: Int
    var compressedAt: Date

    // History bridge for AI context
    var historyBridge: HistoryBridge?

    init(
        summary: String,
        entities: [String] = [],
        decisions: [String] = [],
        todos: [String] = [],
        originalMessageCount: Int = 0,
        compressedAt: Date = Date(),
        historyBridge: HistoryBridge? = nil
    ) {
        self.summary = summary
        self.entities = entities
        self.decisions = decisions
        self.todos = todos
        self.originalMessageCount = originalMessageCount
        self.compressedAt = compressedAt
        self.historyBridge = historyBridge
    }
}

/// History bridge for maintaining context across compaction
struct HistoryBridge: Codable {
    let summary: String
    let keyTopics: [String]
    let recentMessageCount: Int
    let createdAt: Date

    init(
        summary: String,
        keyTopics: [String] = [],
        recentMessageCount: Int = 15,
        createdAt: Date = Date()
    ) {
        self.summary = summary
        self.keyTopics = keyTopics
        self.recentMessageCount = recentMessageCount
        self.createdAt = createdAt
    }
}

// MARK: - Reference Pointer

/// Pointer to a reference in the index for REF token expansion
struct ReferencePointer: Codable {
    enum ReferenceType: String, Codable {
        case theme
        case message
        case file
        case semanticNode
        case workflow
        case kanbanTask
    }

    let type: ReferenceType
    let targetId: UUID
    let preview: String
    let createdAt: Date

    init(
        type: ReferenceType,
        targetId: UUID,
        preview: String,
        createdAt: Date = Date()
    ) {
        self.type = type
        self.targetId = targetId
        self.preview = preview
        self.createdAt = createdAt
    }
}

// MARK: - File Reference

/// Reference to a file in the conversation
struct FileReference: Codable, Identifiable {
    let id: UUID
    var filename: String
    var originalPath: String?
    var processedContent: String?
    var embedding: [Float]?
    var fileType: String
    var uploadedAt: Date
    var lastAccessed: Date

    // MagnetarStudio-specific
    var isVaultProtected: Bool
    var vaultFileId: UUID?
    var conversationIds: [UUID]  // Cross-conversation tracking

    init(
        id: UUID = UUID(),
        filename: String,
        originalPath: String? = nil,
        processedContent: String? = nil,
        embedding: [Float]? = nil,
        fileType: String = "unknown",
        uploadedAt: Date = Date(),
        lastAccessed: Date = Date(),
        isVaultProtected: Bool = false,
        vaultFileId: UUID? = nil,
        conversationIds: [UUID] = []
    ) {
        self.id = id
        self.filename = filename
        self.originalPath = originalPath
        self.processedContent = processedContent
        self.embedding = embedding
        self.fileType = fileType
        self.uploadedAt = uploadedAt
        self.lastAccessed = lastAccessed
        self.isVaultProtected = isVaultProtected
        self.vaultFileId = vaultFileId
        self.conversationIds = conversationIds
    }
}

// MARK: - Context Tier

/// Multi-tier memory architecture for context management
enum ContextTier: String, Codable, CaseIterable {
    /// Last 10-15 messages, full fidelity
    case immediate

    /// 3-5 key topics as structured JSON
    case themes

    /// Entity relationships for reference
    case graph

    /// Older messages, heavily compressed
    case compressed

    /// In storage, retrievable via semantic search
    case archived

    var description: String {
        switch self {
        case .immediate: return "Recent messages (full detail)"
        case .themes: return "Key topics and themes"
        case .graph: return "Entity relationships"
        case .compressed: return "Compressed older context"
        case .archived: return "Archived (searchable)"
        }
    }

    var priority: Int {
        switch self {
        case .immediate: return 5
        case .themes: return 4
        case .graph: return 3
        case .compressed: return 2
        case .archived: return 1
        }
    }
}
