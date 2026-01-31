//
//  ContextBundleCore.swift
//  MagnetarStudio
//
//  Core ContextBundle definition with clean interface.
//  Uses extracted models from WorkspaceContextModels.swift.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "ContextBundle")

// MARK: - Context Bundle (What Gets Passed to Models)

/// Complete context bundle for model routing and inference
/// Apple FM uses this to determine which model to route to and what context to provide
struct ContextBundle: Codable {
    // Core query
    let userQuery: String
    let sessionId: String
    let workspaceType: String

    // Conversation history (smart windowing)
    let conversationHistory: [ConversationMessage]
    let totalMessagesInSession: Int

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
    let activeModelId: String?

    // System constraints
    let systemResources: SystemResourceState
    let availableModels: [AvailableModel]

    // Metadata
    let bundledAt: Date
    let ttl: TimeInterval

    // MARK: - Convenience Accessors

    /// Whether bundle has any workspace context beyond the current
    var hasCrossWorkspaceContext: Bool {
        return vaultContext != nil ||
               dataContext != nil ||
               kanbanContext != nil ||
               workflowContext != nil ||
               teamContext != nil ||
               codeContext != nil
    }

    /// Whether bundle has RAG results
    var hasRAGContext: Bool {
        return (ragDocuments?.isEmpty == false) ||
               (vectorSearchResults?.isEmpty == false)
    }

    /// Estimated token count for context
    var estimatedContextTokens: Int {
        var tokens = 0

        // User query
        tokens += userQuery.count / 4

        // Conversation history
        for message in conversationHistory {
            tokens += message.content.count / 4
        }

        // RAG documents
        if let docs = ragDocuments {
            for doc in docs {
                tokens += doc.content.count / 4
            }
        }

        return tokens
    }

    /// Whether system is under resource pressure
    var isResourceConstrained: Bool {
        return systemResources.isResourceConstrained
    }

    // MARK: - Builder

    /// Builder for creating context bundles
    static func builder() -> ContextBundleBuilder {
        return ContextBundleBuilder()
    }
}

// MARK: - Context Bundle Builder

/// Fluent builder for ContextBundle
class ContextBundleBuilder {
    private var userQuery: String = ""
    private var sessionId: String = ""
    private var workspaceType: String = "chat"
    private var conversationHistory: [ConversationMessage] = []
    private var totalMessagesInSession: Int = 0
    private var vaultContext: BundledVaultContext?
    private var dataContext: BundledDataContext?
    private var kanbanContext: BundledKanbanContext?
    private var workflowContext: BundledWorkflowContext?
    private var teamContext: BundledTeamContext?
    private var codeContext: BundledCodeContext?
    private var ragDocuments: [RAGDocument]?
    private var vectorSearchResults: [VectorSearchResult]?
    private var userPreferences: UserPreferences = .default
    private var activeModelId: String?
    private var systemResources: SystemResourceState = .unknown
    private var availableModels: [AvailableModel] = []
    private var ttl: TimeInterval = 60

    func query(_ query: String) -> ContextBundleBuilder {
        self.userQuery = query
        return self
    }

    func session(_ id: String) -> ContextBundleBuilder {
        self.sessionId = id
        return self
    }

    func workspace(_ type: String) -> ContextBundleBuilder {
        self.workspaceType = type
        return self
    }

    func history(_ messages: [ConversationMessage], total: Int) -> ContextBundleBuilder {
        self.conversationHistory = messages
        self.totalMessagesInSession = total
        return self
    }

    func vault(_ context: BundledVaultContext?) -> ContextBundleBuilder {
        self.vaultContext = context
        return self
    }

    func data(_ context: BundledDataContext?) -> ContextBundleBuilder {
        self.dataContext = context
        return self
    }

    func kanban(_ context: BundledKanbanContext?) -> ContextBundleBuilder {
        self.kanbanContext = context
        return self
    }

    func workflow(_ context: BundledWorkflowContext?) -> ContextBundleBuilder {
        self.workflowContext = context
        return self
    }

    func team(_ context: BundledTeamContext?) -> ContextBundleBuilder {
        self.teamContext = context
        return self
    }

    func code(_ context: BundledCodeContext?) -> ContextBundleBuilder {
        self.codeContext = context
        return self
    }

    func rag(documents: [RAGDocument]?, vectors: [VectorSearchResult]?) -> ContextBundleBuilder {
        self.ragDocuments = documents
        self.vectorSearchResults = vectors
        return self
    }

    func preferences(_ prefs: UserPreferences) -> ContextBundleBuilder {
        self.userPreferences = prefs
        return self
    }

    func activeModel(_ modelId: String?) -> ContextBundleBuilder {
        self.activeModelId = modelId
        return self
    }

    func resources(_ state: SystemResourceState) -> ContextBundleBuilder {
        self.systemResources = state
        return self
    }

    func models(_ available: [AvailableModel]) -> ContextBundleBuilder {
        self.availableModels = available
        return self
    }

    func cacheTTL(_ seconds: TimeInterval) -> ContextBundleBuilder {
        self.ttl = seconds
        return self
    }

    func build() -> ContextBundle {
        return ContextBundle(
            userQuery: userQuery,
            sessionId: sessionId,
            workspaceType: workspaceType,
            conversationHistory: conversationHistory,
            totalMessagesInSession: totalMessagesInSession,
            vaultContext: vaultContext,
            dataContext: dataContext,
            kanbanContext: kanbanContext,
            workflowContext: workflowContext,
            teamContext: teamContext,
            codeContext: codeContext,
            ragDocuments: ragDocuments,
            vectorSearchResults: vectorSearchResults,
            userPreferences: userPreferences,
            activeModelId: activeModelId,
            systemResources: systemResources,
            availableModels: availableModels,
            bundledAt: Date(),
            ttl: ttl
        )
    }
}

// MARK: - Context Bundle Extensions

extension ContextBundle {

    /// Create a minimal bundle for quick routing decisions
    static func minimal(query: String, sessionId: String) -> ContextBundle {
        return ContextBundle(
            userQuery: query,
            sessionId: sessionId,
            workspaceType: "chat",
            conversationHistory: [],
            totalMessagesInSession: 0,
            vaultContext: nil,
            dataContext: nil,
            kanbanContext: nil,
            workflowContext: nil,
            teamContext: nil,
            codeContext: nil,
            ragDocuments: nil,
            vectorSearchResults: nil,
            userPreferences: .default,
            activeModelId: nil,
            systemResources: .unknown,
            availableModels: [],
            bundledAt: Date(),
            ttl: 30
        )
    }

    /// Check if bundle is still valid (within TTL)
    var isValid: Bool {
        return Date().timeIntervalSince(bundledAt) < ttl
    }

    /// Create an expired copy (for forcing refresh)
    func expired() -> ContextBundle {
        return ContextBundle(
            userQuery: userQuery,
            sessionId: sessionId,
            workspaceType: workspaceType,
            conversationHistory: conversationHistory,
            totalMessagesInSession: totalMessagesInSession,
            vaultContext: vaultContext,
            dataContext: dataContext,
            kanbanContext: kanbanContext,
            workflowContext: workflowContext,
            teamContext: teamContext,
            codeContext: codeContext,
            ragDocuments: ragDocuments,
            vectorSearchResults: vectorSearchResults,
            userPreferences: userPreferences,
            activeModelId: activeModelId,
            systemResources: systemResources,
            availableModels: availableModels,
            bundledAt: bundledAt.addingTimeInterval(-ttl - 1),  // Force expired
            ttl: ttl
        )
    }
}

// MARK: - Debug / Logging

extension ContextBundle: CustomStringConvertible {
    var description: String {
        var parts: [String] = []

        parts.append("Query: \(userQuery.prefix(50))...")
        parts.append("Session: \(sessionId)")
        parts.append("Workspace: \(workspaceType)")
        parts.append("History: \(conversationHistory.count) messages")

        if hasCrossWorkspaceContext {
            var contexts: [String] = []
            if vaultContext != nil { contexts.append("vault") }
            if dataContext != nil { contexts.append("data") }
            if kanbanContext != nil { contexts.append("kanban") }
            if workflowContext != nil { contexts.append("workflow") }
            if teamContext != nil { contexts.append("team") }
            if codeContext != nil { contexts.append("code") }
            parts.append("Cross-workspace: \(contexts.joined(separator: ", "))")
        }

        if hasRAGContext {
            let ragCount = (ragDocuments?.count ?? 0) + (vectorSearchResults?.count ?? 0)
            parts.append("RAG results: \(ragCount)")
        }

        parts.append("Est. tokens: \(estimatedContextTokens)")
        parts.append("TTL: \(Int(ttl))s")

        return "ContextBundle(\(parts.joined(separator: ", ")))"
    }
}
