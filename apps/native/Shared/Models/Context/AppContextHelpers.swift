//
//  AppContextHelpers.swift
//  MagnetarStudio
//
//  Helper types and extensions for AppContext.
//  Extracted from AppContext.swift for maintainability.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "AppContextHelpers")

// MARK: - Model Interaction History

/// Record of a model interaction for learning patterns
struct ModelInteraction: Codable {
    let id: UUID
    let modelId: String
    let queryType: String
    let queryLength: Int
    let responseQuality: Float?
    let latencyMs: Int
    let timestamp: Date
    let workspace: String

    init(
        modelId: String,
        queryType: String,
        queryLength: Int,
        responseQuality: Float? = nil,
        latencyMs: Int,
        workspace: String
    ) {
        self.id = UUID()
        self.modelId = modelId
        self.queryType = queryType
        self.queryLength = queryLength
        self.responseQuality = responseQuality
        self.latencyMs = latencyMs
        self.timestamp = Date()
        self.workspace = workspace
    }

    /// Store interaction to history
    static func record(_ interaction: ModelInteraction) {
        var history = loadHistory()
        history.insert(interaction, at: 0)

        // Keep only recent interactions
        if history.count > 500 {
            history = Array(history.prefix(500))
        }

        saveHistory(history)
    }

    /// Load interaction history
    static func loadHistory() -> [ModelInteraction] {
        guard let data = UserDefaults.standard.data(forKey: "modelInteractionHistory") else {
            return []
        }
        do {
            let decoder = JSONDecoder()
            decoder.dateDecodingStrategy = .iso8601
            return try decoder.decode([ModelInteraction].self, from: data)
        } catch {
            logger.warning("Failed to decode model interactions: \(error)")
            return []
        }
    }

    /// Save interaction history
    static func saveHistory(_ interactions: [ModelInteraction]) {
        do {
            let encoder = JSONEncoder()
            encoder.dateEncodingStrategy = .iso8601
            let data = try encoder.encode(interactions)
            UserDefaults.standard.set(data, forKey: "modelInteractionHistory")
        } catch {
            logger.warning("Failed to encode model interactions: \(error)")
        }
    }
}

// MARK: - Loaded Model Info

/// Information about a model currently loaded in memory
struct LoadedModel: Codable {
    let modelId: String
    let slotNumber: Int
    let memoryUsageGB: Float
    let loadedAt: Date
    let isPinned: Bool
    let lastUsed: Date

    /// Time since model was last used
    var idleTime: TimeInterval {
        Date().timeIntervalSince(lastUsed)
    }

    /// Time model has been loaded
    var loadedDuration: TimeInterval {
        Date().timeIntervalSince(loadedAt)
    }
}

// MARK: - ANE Context State

/// State from ANE Context Engine for cross-workspace memory
struct ANEContextState: Codable {
    let activeTopics: [String]
    let recentEntities: [String]
    let conversationTrends: [String: Float]
    let predictedNeeds: [String]
    let lastUpdated: Date

    static func current() async -> ANEContextState {
        // Get from ANEPredictor if available
        // For now return defaults
        return ANEContextState(
            activeTopics: [],
            recentEntities: [],
            conversationTrends: [:],
            predictedNeeds: [],
            lastUpdated: Date()
        )
    }

    static let empty = ANEContextState(
        activeTopics: [],
        recentEntities: [],
        conversationTrends: [:],
        predictedNeeds: [],
        lastUpdated: Date()
    )
}

// MARK: - Workspace-Specific Context Types

/// Vault context snapshot
struct VaultContext {
    let unlocked: Bool
    let vaultType: String
    let unlockedVaultType: String?
    let fileCount: Int
    let recentFiles: [VaultFileMetadata]
    let activePermissions: [FilePermission]

    init(from snapshot: MainActorSnapshot) {
        self.unlocked = snapshot.vaultUnlocked
        self.vaultType = snapshot.vaultType
        self.unlockedVaultType = snapshot.vaultUnlocked ? snapshot.vaultType : nil
        self.fileCount = snapshot.vaultFiles.count
        self.recentFiles = snapshot.vaultFiles.prefix(5).map { file in
            VaultFileMetadata(
                id: file.id.uuidString,
                name: file.name,
                path: file.path ?? "",
                lastAccessed: file.createdAt
            )
        }
        self.activePermissions = snapshot.activePermissions.map { perm in
            FilePermission(
                id: perm.id,
                fileId: perm.fileId.uuidString,
                grantedAt: perm.grantedAt,
                expiresAt: perm.expiresAt,
                accessLevel: perm.accessLevel.rawValue
            )
        }
    }

    /// Get current vault context
    static func current() async -> VaultContext {
        let snapshot = await MainActor.run { MainActorSnapshot.capture() }
        return VaultContext(from: snapshot)
    }
}

/// Data workspace context
struct DataContext {
    let hasActiveFile: Bool
    let currentFileName: String?
    let hasExecutedQuery: Bool
    let lastQueryPreview: String?
    let tableCount: Int

    init(from snapshot: MainActorSnapshot) {
        self.hasActiveFile = snapshot.currentFile != nil
        self.currentFileName = snapshot.currentFile?.name
        self.hasExecutedQuery = snapshot.hasExecuted
        self.lastQueryPreview = snapshot.currentQuery?.preview
        self.tableCount = 0  // Would need table tracking
    }
}

/// Kanban workspace context
struct KanbanContext: Codable {
    let activeBoard: String?
    let taskCount: Int
    let urgentCount: Int
    let recentActivity: [KanbanActivitySummary]

    static func current() async -> KanbanContext {
        // Load from KanbanStore
        return KanbanContext(
            activeBoard: nil,
            taskCount: 0,
            urgentCount: 0,
            recentActivity: []
        )
    }
}

/// Summary of kanban activity
struct KanbanActivitySummary: Codable {
    let type: String
    let taskName: String?
    let timestamp: Date
}

/// Workflow context
struct WorkflowContext {
    let activeWorkflows: [WorkflowSummary]
    let recentExecutions: [WorkflowExecutionSummary]

    init(from snapshot: MainActorSnapshot) {
        self.activeWorkflows = snapshot.workflows.prefix(5).map { workflow in
            WorkflowSummary(
                id: workflow.id.uuidString,
                name: workflow.name,
                status: workflow.status.rawValue,
                lastRun: workflow.lastRun,
                stepCount: workflow.steps.count
            )
        }
        self.recentExecutions = snapshot.workflowExecutions.prefix(5).map { exec in
            WorkflowExecutionSummary(
                workflowId: exec.workflowId.uuidString,
                status: exec.status.rawValue,
                startedAt: exec.startedAt
            )
        }
    }
}

/// Summary of workflow execution
struct WorkflowExecutionSummary: Codable {
    let workflowId: String
    let status: String
    let startedAt: Date
}

/// Team workspace context
struct TeamContext: Codable {
    let activeChannel: String?
    let onlineCount: Int
    let unreadCount: Int
    let recentMentions: [String]

    static func current() async -> TeamContext {
        return TeamContext(
            activeChannel: nil,
            onlineCount: 0,
            unreadCount: 0,
            recentMentions: []
        )
    }
}

/// Code workspace context
struct CodeContext: Codable {
    let openFiles: [String]
    let currentFile: String?
    let gitBranch: String?
    let hasUncommittedChanges: Bool
    let language: String?

    static func current() async -> CodeContext {
        return CodeContext(
            openFiles: [],
            currentFile: nil,
            gitBranch: nil,
            hasUncommittedChanges: false,
            language: nil
        )
    }
}

// MARK: - Metadata Types

/// Minimal vault file metadata for context
struct VaultFileMetadata: Codable {
    let id: String
    let name: String
    let path: String
    let lastAccessed: Date
}

/// File permission record for context
struct FilePermission: Codable, Identifiable {
    let id: UUID
    let fileId: String
    let grantedAt: Date
    let expiresAt: Date?
    let accessLevel: String

    var isExpired: Bool {
        if let expires = expiresAt {
            return Date() > expires
        }
        return false
    }
}

// MARK: - Query Types

/// Query response preview
struct QueryResponse: Codable {
    let id: UUID
    let preview: String
    let rowCount: Int
    let executedAt: Date
}

// MARK: - Supporting Types

/// Table metadata for data context
struct TableMetadata: Codable {
    let name: String
    let rowCount: Int
    let columnCount: Int
    let lastAccessed: Date
}

/// Recent query for data context
struct RecentQuery: Codable {
    let id: String
    let sql: String
    let executedAt: Date
    let rowCount: Int?
}

/// Database connection info
struct DatabaseConnection: Codable {
    let id: String
    let name: String
    let type: String
    let isConnected: Bool
}

/// Task summary for kanban
struct TaskSummary: Codable {
    let id: String
    let title: String
    let status: String
    let priority: String
    let dueDate: Date?
}

/// Kanban activity record
struct KanbanActivity: Codable {
    let id: String
    let type: String
    let description: String
    let timestamp: Date
}
