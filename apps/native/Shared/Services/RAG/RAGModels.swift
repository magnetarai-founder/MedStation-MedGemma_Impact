//
//  RAGModels.swift
//  MagnetarStudio
//
//  Data models for Retrieval-Augmented Generation (RAG) system.
//  Supports multiple content sources with unified retrieval interface.
//

import Foundation

// MARK: - RAG Document

/// A document that can be indexed and retrieved via RAG
struct RAGDocument: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    let content: String
    let embedding: [Float]
    let source: RAGSource
    let metadata: RAGDocumentMetadata
    let createdAt: Date
    var lastAccessedAt: Date

    init(
        id: UUID = UUID(),
        content: String,
        embedding: [Float],
        source: RAGSource,
        metadata: RAGDocumentMetadata,
        createdAt: Date = Date(),
        lastAccessedAt: Date = Date()
    ) {
        self.id = id
        self.content = content
        self.embedding = embedding
        self.source = source
        self.metadata = metadata
        self.createdAt = createdAt
        self.lastAccessedAt = lastAccessedAt
    }

    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }

    static func == (lhs: RAGDocument, rhs: RAGDocument) -> Bool {
        lhs.id == rhs.id
    }
}

// MARK: - RAG Source

/// The source type for a RAG document
enum RAGSource: String, Codable, CaseIterable, Sendable {
    case chatMessage = "chat_message"
    case theme = "theme"
    case semanticNode = "semantic_node"
    case file = "file"
    case vaultFile = "vault_file"
    case workflow = "workflow"
    case kanbanTask = "kanban_task"
    case document = "document"
    case spreadsheet = "spreadsheet"
    case codeFile = "code_file"
    case datasetColumn = "dataset_column"
    case teamMessage = "team_message"

    var displayName: String {
        switch self {
        case .chatMessage: return "Chat Message"
        case .theme: return "Theme"
        case .semanticNode: return "Context"
        case .file: return "File"
        case .vaultFile: return "Vault File"
        case .workflow: return "Workflow"
        case .kanbanTask: return "Task"
        case .document: return "Document"
        case .spreadsheet: return "Spreadsheet"
        case .codeFile: return "Code"
        case .datasetColumn: return "Dataset"
        case .teamMessage: return "Team"
        }
    }

    var icon: String {
        switch self {
        case .chatMessage: return "bubble.left"
        case .theme: return "tag"
        case .semanticNode: return "brain"
        case .file: return "doc"
        case .vaultFile: return "lock.doc"
        case .workflow: return "gearshape.2"
        case .kanbanTask: return "checklist"
        case .document: return "doc.richtext"
        case .spreadsheet: return "tablecells"
        case .codeFile: return "chevron.left.forwardslash.chevron.right"
        case .datasetColumn: return "chart.bar"
        case .teamMessage: return "person.2"
        }
    }

    /// Priority for ranking (higher = more important)
    var priority: Int {
        switch self {
        case .chatMessage: return 10
        case .theme: return 9
        case .semanticNode: return 8
        case .file, .vaultFile: return 7
        case .codeFile: return 7
        case .workflow: return 6
        case .kanbanTask: return 6
        case .document: return 5
        case .spreadsheet: return 5
        case .datasetColumn: return 4
        case .teamMessage: return 3
        }
    }
}

// MARK: - RAG Document Metadata

/// Metadata for a RAG document
struct RAGDocumentMetadata: Codable, Sendable {
    var conversationId: UUID?
    var sessionId: UUID?
    var messageId: UUID?
    var fileId: UUID?
    var workflowId: UUID?
    var taskId: UUID?
    var documentId: UUID?
    var teamId: UUID?

    /// Original filename or title
    var title: String?

    /// File type or content type
    var contentType: String?

    /// Chunk information for large documents
    var chunkIndex: Int?
    var totalChunks: Int?

    /// Additional searchable tags
    var tags: [String]?

    /// Is this from a protected vault file
    var isVaultProtected: Bool

    init(
        conversationId: UUID? = nil,
        sessionId: UUID? = nil,
        messageId: UUID? = nil,
        fileId: UUID? = nil,
        workflowId: UUID? = nil,
        taskId: UUID? = nil,
        documentId: UUID? = nil,
        teamId: UUID? = nil,
        title: String? = nil,
        contentType: String? = nil,
        chunkIndex: Int? = nil,
        totalChunks: Int? = nil,
        tags: [String]? = nil,
        isVaultProtected: Bool = false
    ) {
        self.conversationId = conversationId
        self.sessionId = sessionId
        self.messageId = messageId
        self.fileId = fileId
        self.workflowId = workflowId
        self.taskId = taskId
        self.documentId = documentId
        self.teamId = teamId
        self.title = title
        self.contentType = contentType
        self.chunkIndex = chunkIndex
        self.totalChunks = totalChunks
        self.tags = tags
        self.isVaultProtected = isVaultProtected
    }
}

// MARK: - RAG Search Query

/// Query for RAG search
struct RAGSearchQuery {
    let text: String
    let embedding: [Float]?
    let sources: [RAGSource]?
    let conversationId: UUID?
    let limit: Int
    let minSimilarity: Float

    init(
        text: String,
        embedding: [Float]? = nil,
        sources: [RAGSource]? = nil,
        conversationId: UUID? = nil,
        limit: Int = 10,
        minSimilarity: Float = 0.3
    ) {
        self.text = text
        self.embedding = embedding
        self.sources = sources
        self.conversationId = conversationId
        self.limit = limit
        self.minSimilarity = minSimilarity
    }
}

// MARK: - RAG Search Result

/// Result from RAG search
struct RAGSearchResult: Identifiable {
    let id: UUID
    let document: RAGDocument
    let similarity: Float
    let rank: Int
    let matchedTerms: [String]?
    let snippet: String?

    init(
        document: RAGDocument,
        similarity: Float,
        rank: Int,
        matchedTerms: [String]? = nil,
        snippet: String? = nil
    ) {
        self.id = document.id
        self.document = document
        self.similarity = similarity
        self.rank = rank
        self.matchedTerms = matchedTerms
        self.snippet = snippet
    }

    /// Combined score considering similarity and source priority
    var combinedScore: Float {
        let sourcePriorityNormalized = Float(document.source.priority) / 10.0
        return (similarity * 0.7) + (sourcePriorityNormalized * 0.3)
    }
}

// MARK: - RAG Context

/// Assembled RAG context for AI prompt
struct RAGContext {
    let results: [RAGSearchResult]
    let query: RAGSearchQuery
    let totalTokens: Int
    let sourceSummary: [RAGSource: Int]

    /// Format for inclusion in AI prompt
    func formatForPrompt(maxTokens: Int = 2000) -> String {
        var sections: [String] = []
        var usedTokens = 0

        // Group by source for cleaner presentation
        let grouped = Dictionary(grouping: results) { $0.document.source }

        for source in RAGSource.allCases {
            guard let sourceResults = grouped[source], !sourceResults.isEmpty else { continue }

            var sourceSection = "### \(source.displayName)\n"

            for result in sourceResults.prefix(5) {
                let content = result.snippet ?? String(result.document.content.prefix(300))
                let tokenEstimate = content.count / 4

                if usedTokens + tokenEstimate > maxTokens { break }

                if let title = result.document.metadata.title {
                    sourceSection += "**\(title)** (relevance: \(String(format: "%.0f", result.similarity * 100))%)\n"
                }
                sourceSection += "\(content)\n\n"
                usedTokens += tokenEstimate
            }

            sections.append(sourceSection)
        }

        return sections.joined(separator: "\n")
    }

    /// Get the most relevant source
    var primarySource: RAGSource? {
        sourceSummary.max(by: { $0.value < $1.value })?.key
    }
}

// MARK: - Index Statistics

/// Statistics about the RAG index
struct RAGIndexStatistics: Codable, Sendable {
    var totalDocuments: Int
    var documentsBySource: [String: Int]
    var averageEmbeddingDimension: Int
    var indexSizeBytes: Int
    var lastUpdated: Date

    init(
        totalDocuments: Int = 0,
        documentsBySource: [String: Int] = [:],
        averageEmbeddingDimension: Int = 384,
        indexSizeBytes: Int = 0,
        lastUpdated: Date = Date()
    ) {
        self.totalDocuments = totalDocuments
        self.documentsBySource = documentsBySource
        self.averageEmbeddingDimension = averageEmbeddingDimension
        self.indexSizeBytes = indexSizeBytes
        self.lastUpdated = lastUpdated
    }
}

// MARK: - Indexing Request

/// Request to index new content
struct RAGIndexRequest {
    let content: String
    let source: RAGSource
    let metadata: RAGDocumentMetadata
    let chunkIfNeeded: Bool

    init(
        content: String,
        source: RAGSource,
        metadata: RAGDocumentMetadata,
        chunkIfNeeded: Bool = true
    ) {
        self.content = content
        self.source = source
        self.metadata = metadata
        self.chunkIfNeeded = chunkIfNeeded
    }
}

// MARK: - Indexing Result

/// Result of indexing operation
struct RAGIndexResult {
    let documentIds: [UUID]
    let chunksCreated: Int
    let tokensIndexed: Int
    let duration: TimeInterval

    static let empty = RAGIndexResult(
        documentIds: [],
        chunksCreated: 0,
        tokensIndexed: 0,
        duration: 0
    )
}

// MARK: - RAG Configuration

/// Configuration for RAG system
struct RAGConfiguration {
    /// Maximum chunk size for indexing
    var maxChunkSize: Int = 512

    /// Overlap between chunks
    var chunkOverlap: Int = 64

    /// Minimum similarity threshold for results
    var minSimilarity: Float = 0.3

    /// Maximum results to return
    var maxResults: Int = 20

    /// Sources to include (nil = all)
    var enabledSources: Set<RAGSource>?

    /// Boost factor for recent content
    var recencyBoost: Float = 0.1

    /// Maximum age for recency boost (hours)
    var recencyWindow: TimeInterval = 24

    static let `default` = RAGConfiguration()

    static let aggressive = RAGConfiguration(
        minSimilarity: 0.2,
        maxResults: 30,
        recencyBoost: 0.2
    )

    static let conservative = RAGConfiguration(
        minSimilarity: 0.5,
        maxResults: 10,
        recencyBoost: 0.05
    )
}
