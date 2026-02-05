//
//  WorkspaceContextModels.swift
//  MagnetarStudio
//
//  Workspace-specific context models extracted from ContextBundle.swift.
//  Part of Phase 7 refactoring for maintainability.
//

import Foundation

// MARK: - Vault Context Models

/// Vault file result from semantic search (includes relevance score and snippet)
struct RelevantVaultFile: Codable, Sendable {
    let fileId: String
    let fileName: String
    let filePath: String
    let snippet: String
    let relevanceScore: Float
}

/// Vault context included in bundle - METADATA ONLY, NO FILE CONTENTS
/// File contents require explicit permission via VaultPermissionManager
struct BundledVaultContext: Codable, Sendable {
    let unlockedVaultType: String?
    let recentlyAccessedFiles: [VaultFileMetadata]
    let currentlyGrantedPermissions: [FilePermission]
    let relevantFiles: [RelevantVaultFile]?
}

// MARK: - Data Context Models

/// Query result from semantic search (includes relevance score)
struct RelevantQuery: Codable, Sendable {
    let queryId: String
    let queryText: String
    let tableName: String?
    let relevanceScore: Float
}

/// Data workspace context - recent queries and loaded tables
struct BundledDataContext: Codable, Sendable {
    let activeTables: [TableMetadata]
    let recentQueries: [RecentQuery]
    let relevantQueries: [RelevantQuery]?
    let activeConnections: [DatabaseConnection]
}

// MARK: - Kanban Context Models

/// Kanban workspace context - active tasks and boards
struct BundledKanbanContext: Codable, Sendable {
    let activeBoard: String?
    let relevantTasks: [TaskSummary]
    let recentActivity: [KanbanActivity]
    let tasksByPriority: TaskPrioritySummary
}

/// Summary of tasks by priority level
struct TaskPrioritySummary: Codable, Sendable {
    let urgent: Int
    let high: Int
    let medium: Int
    let low: Int

    var total: Int { urgent + high + medium + low }

    static let empty = TaskPrioritySummary(urgent: 0, high: 0, medium: 0, low: 0)
}

// MARK: - Workflow Context Models

/// Workflow/automation context - active workflows
struct BundledWorkflowContext: Codable, Sendable {
    let activeWorkflows: [WorkflowSummary]
    let recentExecutions: [WorkflowExecution]
    let relevantWorkflows: [WorkflowSummary]?
}

// Note: WorkflowSummary is defined in AppContext.swift

// MARK: - Team Context Models

/// Team workspace context - recent messages and channels
struct BundledTeamContext: Codable, Sendable {
    let activeChannel: String?
    let recentMessages: [TeamMessageSummary]
    let onlineMembers: Int
    let mentionedUsers: [String]?
}

// Note: TeamMessageSummary is defined in AppContext.swift

// MARK: - Code Context Models

/// Code workspace context - open files and git state
struct BundledCodeContext: Codable, Sendable {
    let openFiles: [String]
    let recentEdits: [CodeEdit]
    let gitBranch: String?
    let gitStatus: String?
    let relevantFiles: [RelevantCodeFile]?
}

/// Code file found via semantic search
struct RelevantCodeFile: Codable, Sendable {
    let fileId: String
    let fileName: String
    let filePath: String?
    let language: String?
    let snippet: String
    let lineNumber: Int?
    let relevanceScore: Float
}

/// A code edit for tracking recent changes
struct CodeEdit: Codable, Sendable {
    let fileId: String
    let fileName: String
    let editType: String  // "insert", "delete", "modify"
    let timestamp: Date
    let preview: String?
}

// MARK: - Conversation Models

/// Single message in conversation history
struct ConversationMessage: Codable, Identifiable, Sendable {
    let id: String
    let role: String
    let content: String
    let modelId: String?
    let timestamp: Date
    let tokenCount: Int?

    /// Create from a ChatMessage
    init(from message: ChatMessage) {
        self.id = message.id.uuidString
        self.role = message.role.rawValue
        self.content = message.content
        self.modelId = message.modelId
        self.timestamp = message.createdAt
        self.tokenCount = nil
    }

    init(
        id: String,
        role: String,
        content: String,
        modelId: String? = nil,
        timestamp: Date = Date(),
        tokenCount: Int? = nil
    ) {
        self.id = id
        self.role = role
        self.content = content
        self.modelId = modelId
        self.timestamp = timestamp
        self.tokenCount = tokenCount
    }
}

// MARK: - Model & System Models
// Note: RAG documents are in Services/RAG/RAGModels.swift (full version with embeddings)
// Note: Bundled versions for context passing are in ContextBundle.swift (BundledRAGDocument, BundledVectorSearchResult)

/// Information about an available model
struct AvailableModel: Codable, Sendable {
    let id: String
    let name: String
    let displayName: String
    let slotNumber: Int?
    let isPinned: Bool
    let memoryUsageGB: Float?
    let capabilities: ModelCapabilities
    let isHealthy: Bool

    /// Whether this model is loaded and ready
    var isLoaded: Bool { slotNumber != nil }
}

/// Model capabilities for routing decisions
struct ModelCapabilities: Codable, Sendable {
    let chat: Bool
    let codeGeneration: Bool
    let dataAnalysis: Bool
    let reasoning: Bool
    let maxContextTokens: Int
    let specialized: String?

    static let basic = ModelCapabilities(
        chat: true,
        codeGeneration: false,
        dataAnalysis: false,
        reasoning: false,
        maxContextTokens: 4096,
        specialized: nil
    )

    static let full = ModelCapabilities(
        chat: true,
        codeGeneration: true,
        dataAnalysis: true,
        reasoning: true,
        maxContextTokens: 32768,
        specialized: nil
    )
}

