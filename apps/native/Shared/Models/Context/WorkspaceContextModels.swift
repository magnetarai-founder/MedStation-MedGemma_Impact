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
struct RelevantVaultFile: Codable {
    let fileId: String
    let fileName: String
    let filePath: String
    let snippet: String
    let relevanceScore: Float
}

/// Vault context included in bundle - METADATA ONLY, NO FILE CONTENTS
/// File contents require explicit permission via VaultPermissionManager
struct BundledVaultContext: Codable {
    let unlockedVaultType: String?
    let recentlyAccessedFiles: [VaultFileMetadata]
    let currentlyGrantedPermissions: [FilePermission]
    let relevantFiles: [RelevantVaultFile]?
}

// MARK: - Data Context Models

/// Query result from semantic search (includes relevance score)
struct RelevantQuery: Codable {
    let queryId: String
    let queryText: String
    let tableName: String?
    let relevanceScore: Float
}

/// Data workspace context - recent queries and loaded tables
struct BundledDataContext: Codable {
    let activeTables: [TableMetadata]
    let recentQueries: [RecentQuery]
    let relevantQueries: [RelevantQuery]?
    let activeConnections: [DatabaseConnection]
}

// MARK: - Kanban Context Models

/// Kanban workspace context - active tasks and boards
struct BundledKanbanContext: Codable {
    let activeBoard: String?
    let relevantTasks: [TaskSummary]
    let recentActivity: [KanbanActivity]
    let tasksByPriority: TaskPrioritySummary
}

/// Summary of tasks by priority level
struct TaskPrioritySummary: Codable {
    let urgent: Int
    let high: Int
    let medium: Int
    let low: Int

    var total: Int { urgent + high + medium + low }

    static let empty = TaskPrioritySummary(urgent: 0, high: 0, medium: 0, low: 0)
}

// MARK: - Workflow Context Models

/// Workflow/automation context - active workflows
struct BundledWorkflowContext: Codable {
    let activeWorkflows: [WorkflowSummary]
    let recentExecutions: [WorkflowExecution]
    let relevantWorkflows: [WorkflowSummary]?
}

/// Summary of a workflow for context bundling
struct WorkflowSummary: Codable {
    let id: String
    let name: String
    let status: String
    let lastRun: Date?
    let stepCount: Int
}

// MARK: - Team Context Models

/// Team workspace context - recent messages and channels
struct BundledTeamContext: Codable {
    let activeChannel: String?
    let recentMessages: [TeamMessageSummary]
    let onlineMembers: Int
    let mentionedUsers: [String]?
}

/// Summary of a team message for context bundling
struct TeamMessageSummary: Codable {
    let id: String
    let sender: String
    let preview: String
    let timestamp: Date
    let channelId: String?
}

// MARK: - Code Context Models

/// Code workspace context - open files and git state
struct BundledCodeContext: Codable {
    let openFiles: [String]
    let recentEdits: [CodeEdit]
    let gitBranch: String?
    let gitStatus: String?
    let relevantFiles: [RelevantCodeFile]?
}

/// Code file found via semantic search
struct RelevantCodeFile: Codable {
    let fileId: String
    let fileName: String
    let filePath: String?
    let language: String?
    let snippet: String
    let lineNumber: Int?
    let relevanceScore: Float
}

/// A code edit for tracking recent changes
struct CodeEdit: Codable {
    let fileId: String
    let fileName: String
    let editType: String  // "insert", "delete", "modify"
    let timestamp: Date
    let preview: String?
}

// MARK: - Conversation Models

/// Single message in conversation history
struct ConversationMessage: Codable, Identifiable {
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

// MARK: - RAG Models (Context-Specific)

/// Document retrieved from RAG/vector search for context bundling
struct RAGDocument: Codable, Identifiable {
    let id: String
    let content: String
    let source: String
    let sourceId: String?
    let relevanceScore: Float
    let metadata: [String: String]?

    init(
        id: String = UUID().uuidString,
        content: String,
        source: String,
        sourceId: String? = nil,
        relevanceScore: Float,
        metadata: [String: String]? = nil
    ) {
        self.id = id
        self.content = content
        self.source = source
        self.sourceId = sourceId
        self.relevanceScore = relevanceScore
        self.metadata = metadata
    }
}

/// Result from ANE Context Engine vector search
struct VectorSearchResult: Codable, Identifiable {
    let id: String
    let content: String
    let similarity: Float
    let source: String
    let metadata: [String: String]?

    /// Formatted for inclusion in prompt
    var formattedForPrompt: String {
        return "[\(source)] \(content)"
    }
}

// MARK: - Model & System Models

/// Information about an available model
struct AvailableModel: Codable {
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
struct ModelCapabilities: Codable {
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

/// System resource state for context-aware routing
struct SystemResourceState: Codable {
    let availableMemoryGB: Float
    let cpuUsage: Float
    let gpuAvailable: Bool
    let loadedModels: [LoadedModelInfo]
    let batteryLevel: Float?
    let isPluggedIn: Bool?

    /// Whether system is under resource pressure
    var isResourceConstrained: Bool {
        availableMemoryGB < 4.0 || cpuUsage > 80.0
    }

    static let unknown = SystemResourceState(
        availableMemoryGB: 0,
        cpuUsage: 0,
        gpuAvailable: false,
        loadedModels: [],
        batteryLevel: nil,
        isPluggedIn: nil
    )
}

/// Info about a loaded model
struct LoadedModelInfo: Codable {
    let modelId: String
    let memoryUsageGB: Float
    let loadedAt: Date
}

// MARK: - User Preferences

/// User preferences affecting model routing and behavior
struct UserPreferences: Codable {
    var preferLocalModels: Bool
    var maxModelSizeGB: Float
    var preferredLanguage: String
    var enableExperimentalFeatures: Bool
    var privacyLevel: PrivacyLevel
    var defaultTemperature: Float

    enum PrivacyLevel: String, Codable {
        case standard
        case high
        case maximum
    }

    static func load() async -> UserPreferences {
        // Load from UserDefaults or return defaults
        guard let data = UserDefaults.standard.data(forKey: "userPreferences"),
              let prefs = try? JSONDecoder().decode(UserPreferences.self, from: data) else {
            return .default
        }
        return prefs
    }

    func save() {
        if let data = try? JSONEncoder().encode(self) {
            UserDefaults.standard.set(data, forKey: "userPreferences")
        }
    }

    static let `default` = UserPreferences(
        preferLocalModels: true,
        maxModelSizeGB: 16.0,
        preferredLanguage: "en",
        enableExperimentalFeatures: false,
        privacyLevel: .standard,
        defaultTemperature: 0.7
    )
}
