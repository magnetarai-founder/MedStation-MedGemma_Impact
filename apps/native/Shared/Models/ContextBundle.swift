//
//  ContextBundle.swift
//  MagnetarStudio
//
//  Defines what context gets passed to models during intelligent routing
//  Part of Noah's Ark for the Digital Age - Smart context bundling
//
//  Foundation: Matthew 7:24-25 - Built on the rock, not sand
//

import Foundation

// MARK: - Context Bundle (What Gets Passed to Models)

/// Complete context bundle for model routing and inference
/// Apple FM uses this to determine which model to route to and what context to provide
struct ContextBundle: Codable {
    // Core query
    let userQuery: String
    let sessionId: String
    let workspaceType: String  // "chat", "vault", "data", "kanban", etc.

    // Conversation history (smart windowing)
    let conversationHistory: [ConversationMessage]
    let totalMessagesInSession: Int  // For context window management

    // Cross-workspace context (smart relevance filtering)
    let vaultContext: BundledVaultContext?
    let dataContext: BundledDataContext?
    let kanbanContext: BundledKanbanContext?
    let workflowContext: BundledWorkflowContext?
    let teamContext: BundledTeamContext?
    let codeContext: BundledCodeContext?

    // RAG/Vector search results (optional)
    let ragDocuments: [RAGDocument]?
    let vectorSearchResults: [VectorSearchResult]?

    // User preferences and model state
    let userPreferences: UserPreferences
    let activeModelId: String?  // Current model if manual selection

    // System constraints
    let systemResources: SystemResourceState
    let availableModels: [AvailableModel]

    // Metadata
    let bundledAt: Date
    let ttl: TimeInterval  // Cache TTL for this bundle
}

// MARK: - Conversation History

/// Single message in conversation history
struct ConversationMessage: Codable, Identifiable {
    let id: String
    let role: String  // "user", "assistant", "system"
    let content: String
    let modelId: String?  // Which model generated this (if assistant)
    let timestamp: Date
    let tokenCount: Int?  // Optional: for context window management
}

// MARK: - Bundled Vault Context (Metadata Only)

/// Vault context included in bundle - METADATA ONLY, NO FILE CONTENTS
/// File contents require explicit permission via VaultPermissionManager
struct BundledVaultContext: Codable {
    let unlockedVaultType: String?  // "real" or "decoy" (if unlocked)
    let recentlyAccessedFiles: [VaultFileMetadata]  // Last 5 files user opened
    let currentlyGrantedPermissions: [FilePermission]  // Active file permissions
    let relevantFiles: [VaultFileMetadata]?  // Files relevant to query (semantic search)

    // IMPORTANT: File contents are NEVER included in bundle
    // Models must request access via VaultPermissionManager
}

// MARK: - Bundled Data Context

/// Data workspace context - recent queries and loaded tables
struct BundledDataContext: Codable {
    let activeTables: [TableMetadata]  // Currently loaded tables
    let recentQueries: [RecentQuery]  // Last 3 queries
    let relevantQueries: [RecentQuery]?  // Queries similar to current request
    let activeConnections: [DatabaseConnection]
}

// MARK: - Bundled Kanban Context

/// Kanban workspace context - active tasks and boards
struct BundledKanbanContext: Codable {
    let activeBoard: String?
    let relevantTasks: [TaskSummary]  // Tasks relevant to query
    let recentActivity: [KanbanActivity]  // Last 5 activities
    let tasksByPriority: TaskPrioritySummary
}

struct TaskPrioritySummary: Codable {
    let urgent: Int
    let high: Int
    let medium: Int
    let low: Int
}

// MARK: - Bundled Workflow Context

/// Workflow/automation context - active workflows
struct BundledWorkflowContext: Codable {
    let activeWorkflows: [WorkflowSummary]
    let recentExecutions: [WorkflowExecution]
    let relevantWorkflows: [WorkflowSummary]?  // Workflows related to query
}

// MARK: - Bundled Team Context

/// Team workspace context - recent messages and channels
struct BundledTeamContext: Codable {
    let activeChannel: String?
    let recentMessages: [TeamMessageSummary]  // Last 10 messages
    let onlineMembers: Int
    let mentionedUsers: [String]?  // Users @mentioned in query
}

// MARK: - Bundled Code Context (Future)

/// Code workspace context - open files and git state
struct BundledCodeContext: Codable {
    let openFiles: [String]  // File paths
    let recentEdits: [CodeEdit]
    let gitBranch: String?
    let gitStatus: String?  // "clean", "uncommitted changes", etc.
    let relevantFiles: [String]?  // Files semantically related to query
}

// MARK: - RAG Documents

/// Document retrieved from RAG/vector search
struct RAGDocument: Codable, Identifiable {
    let id: String
    let content: String
    let source: String  // "vault", "data", "web", etc.
    let sourceId: String?  // Vault file ID, etc.
    let relevanceScore: Float  // 0.0-1.0
    let metadata: [String: String]?
}

// MARK: - Vector Search Results

/// Result from ANE Context Engine vector search
struct VectorSearchResult: Codable, Identifiable {
    let id: String
    let text: String
    let workspaceType: String  // Where this came from
    let resourceId: String  // File ID, task ID, message ID, etc.
    let similarity: Float  // 0.0-1.0
    let metadata: VectorMetadata
}

struct VectorMetadata: Codable {
    let resourceType: String  // "vault_file", "kanban_task", "team_message", etc.
    let timestamp: Date
    let author: String?
    let tags: [String]?
}

// MARK: - Available Models

/// Model available for routing
struct AvailableModel: Codable, Identifiable {
    let id: String
    let name: String
    let displayName: String
    let slotNumber: Int?  // nil if not hot-loaded
    let isPinned: Bool
    let memoryUsageGB: Float?  // nil if not loaded
    let capabilities: ModelCapabilities
    let isHealthy: Bool  // Can this model be routed to right now?
}

struct ModelCapabilities: Codable {
    let chat: Bool
    let codeGeneration: Bool
    let dataAnalysis: Bool
    let reasoning: Bool
    let maxContextTokens: Int
    let specialized: String?  // "sql", "python", "scripture", etc.
}

// MARK: - Context Bundler (Smart Relevance Filtering)

/// Service for creating context bundles with smart relevance filtering
@MainActor
class ContextBundler {
    static let shared = ContextBundler()

    private init() {}

    /// Create context bundle for a user query
    /// Apple FM uses this to determine routing and what context to provide
    func createBundle(
        query: String,
        sessionId: String,
        workspaceType: String,
        conversationHistory: [ConversationMessage],
        activeModelId: String? = nil
    ) async -> ContextBundle {
        // Get full app context
        let appContext = await AppContext.current()

        // Smart relevance filtering based on query
        let relevance = analyzeQueryRelevance(query: query, workspaceType: workspaceType)

        // Bundle vault context (metadata only)
        let vaultContext = await bundleVaultContext(
            from: appContext.vault,
            relevance: relevance,
            query: query
        )

        // Bundle data context
        let dataContext = bundleDataContext(
            from: appContext.data,
            relevance: relevance,
            query: query
        )

        // Bundle kanban context
        let kanbanContext = bundleKanbanContext(
            from: appContext.kanban,
            relevance: relevance,
            query: query
        )

        // Bundle workflow context
        let workflowContext = bundleWorkflowContext(
            from: appContext.workflows,
            relevance: relevance,
            query: query
        )

        // Bundle team context
        let teamContext = bundleTeamContext(
            from: appContext.team,
            relevance: relevance,
            query: query
        )

        // Bundle code context
        let codeContext = bundleCodeContext(
            from: appContext.code,
            relevance: relevance,
            query: query
        )

        // Get RAG documents (if ANE Context Engine available)
        let ragDocuments = await fetchRAGDocuments(
            query: query,
            aneState: appContext.vectorMemory
        )

        // Get available models
        let availableModels = await fetchAvailableModels(
            systemResources: appContext.systemResources
        )

        return ContextBundle(
            userQuery: query,
            sessionId: sessionId,
            workspaceType: workspaceType,
            conversationHistory: conversationHistory,
            totalMessagesInSession: conversationHistory.count,
            vaultContext: vaultContext,
            dataContext: dataContext,
            kanbanContext: kanbanContext,
            workflowContext: workflowContext,
            teamContext: teamContext,
            codeContext: codeContext,
            ragDocuments: ragDocuments,
            vectorSearchResults: nil,  // TODO: ANE Context Engine integration
            userPreferences: appContext.userPreferences,
            activeModelId: activeModelId,
            systemResources: appContext.systemResources,
            availableModels: availableModels,
            bundledAt: Date(),
            ttl: 60  // 60 seconds cache
        )
    }

    // MARK: - Private Helpers

    private func analyzeQueryRelevance(query: String, workspaceType: String) -> QueryRelevance {
        // Simple keyword-based relevance (future: use ANE for semantic analysis)
        let lowercased = query.lowercased()

        return QueryRelevance(
            needsVaultFiles: lowercased.contains("file") || lowercased.contains("document") || lowercased.contains("vault"),
            needsDataContext: lowercased.contains("data") || lowercased.contains("query") || lowercased.contains("sql") || lowercased.contains("table"),
            needsKanbanContext: lowercased.contains("task") || lowercased.contains("todo") || lowercased.contains("project") || lowercased.contains("kanban"),
            needsWorkflowContext: lowercased.contains("workflow") || lowercased.contains("automation") || lowercased.contains("automate"),
            needsTeamContext: lowercased.contains("team") || lowercased.contains("message") || lowercased.contains("channel") || lowercased.contains("chat"),
            needsCodeContext: lowercased.contains("code") || lowercased.contains("function") || lowercased.contains("git") || lowercased.contains("repo"),
            currentWorkspaceType: workspaceType
        )
    }

    private func bundleVaultContext(
        from vault: VaultContext,
        relevance: QueryRelevance,
        query: String
    ) async -> BundledVaultContext? {
        guard relevance.needsVaultFiles || relevance.currentWorkspaceType == "vault" else {
            return nil
        }

        return BundledVaultContext(
            unlockedVaultType: vault.unlockedVaultType,
            recentlyAccessedFiles: Array(vault.recentFiles.prefix(5)),
            currentlyGrantedPermissions: vault.activePermissions,
            relevantFiles: nil  // TODO: Semantic search for relevant files
        )
    }

    private func bundleDataContext(
        from data: DataContext,
        relevance: QueryRelevance,
        query: String
    ) -> BundledDataContext? {
        guard relevance.needsDataContext || relevance.currentWorkspaceType == "data" else {
            return nil
        }

        return BundledDataContext(
            activeTables: data.loadedTables,
            recentQueries: Array(data.recentQueries.prefix(3)),
            relevantQueries: nil,  // TODO: Find similar queries
            activeConnections: data.activeConnections
        )
    }

    private func bundleKanbanContext(
        from kanban: KanbanContext,
        relevance: QueryRelevance,
        query: String
    ) -> BundledKanbanContext? {
        guard relevance.needsKanbanContext || relevance.currentWorkspaceType == "kanban" else {
            return nil
        }

        // Count tasks by priority
        let prioritySummary = TaskPrioritySummary(
            urgent: kanban.activeTasks.filter { $0.priority == "urgent" }.count,
            high: kanban.activeTasks.filter { $0.priority == "high" }.count,
            medium: kanban.activeTasks.filter { $0.priority == "medium" }.count,
            low: kanban.activeTasks.filter { $0.priority == "low" }.count
        )

        return BundledKanbanContext(
            activeBoard: kanban.activeBoard,
            relevantTasks: Array(kanban.activeTasks.prefix(5)),
            recentActivity: Array(kanban.recentActivity.prefix(5)),
            tasksByPriority: prioritySummary
        )
    }

    private func bundleWorkflowContext(
        from workflow: WorkflowContext,
        relevance: QueryRelevance,
        query: String
    ) -> BundledWorkflowContext? {
        guard relevance.needsWorkflowContext || relevance.currentWorkspaceType == "workflows" else {
            return nil
        }

        return BundledWorkflowContext(
            activeWorkflows: Array(workflow.activeWorkflows.prefix(5)),
            recentExecutions: Array(workflow.recentExecutions.prefix(5)),
            relevantWorkflows: nil  // TODO: Find relevant workflows
        )
    }

    private func bundleTeamContext(
        from team: TeamContext,
        relevance: QueryRelevance,
        query: String
    ) -> BundledTeamContext? {
        guard relevance.needsTeamContext || relevance.currentWorkspaceType == "team" else {
            return nil
        }

        return BundledTeamContext(
            activeChannel: team.activeChannel,
            recentMessages: Array(team.recentMessages.prefix(10)),
            onlineMembers: team.onlineMembers,
            mentionedUsers: nil  // TODO: Extract @mentions from query
        )
    }

    private func bundleCodeContext(
        from code: CodeContext,
        relevance: QueryRelevance,
        query: String
    ) -> BundledCodeContext? {
        guard relevance.needsCodeContext || relevance.currentWorkspaceType == "code" else {
            return nil
        }

        return BundledCodeContext(
            openFiles: code.openFiles,
            recentEdits: Array(code.recentEdits.prefix(5)),
            gitBranch: code.gitBranch,
            gitStatus: nil,  // TODO: Get git status
            relevantFiles: nil  // TODO: Semantic search for relevant files
        )
    }

    private func fetchRAGDocuments(
        query: String,
        aneState: ANEContextState
    ) async -> [RAGDocument]? {
        guard aneState.available else {
            return nil
        }

        // TODO: Query ANE Context Engine backend
        // For now, return empty array
        return []
    }

    private func fetchAvailableModels(
        systemResources: SystemResourceState
    ) async -> [AvailableModel] {
        // TODO: Get models from HotSlotManager + Ollama
        // For now, return active models from system resources
        return systemResources.activeModels.map { loadedModel in
            AvailableModel(
                id: loadedModel.id,
                name: loadedModel.name,
                displayName: loadedModel.name,
                slotNumber: loadedModel.slotNumber,
                isPinned: loadedModel.isPinned,
                memoryUsageGB: loadedModel.memoryUsageGB,
                capabilities: ModelCapabilities(
                    chat: true,
                    codeGeneration: false,
                    dataAnalysis: false,
                    reasoning: false,
                    maxContextTokens: 8192,
                    specialized: nil
                ),
                isHealthy: true
            )
        }
    }
}

// MARK: - Query Relevance Analysis

struct QueryRelevance {
    let needsVaultFiles: Bool
    let needsDataContext: Bool
    let needsKanbanContext: Bool
    let needsWorkflowContext: Bool
    let needsTeamContext: Bool
    let needsCodeContext: Bool
    let currentWorkspaceType: String
}
