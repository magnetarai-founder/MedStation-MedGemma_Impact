//
//  CrossWorkspaceIntelligence.swift
//  MagnetarStudio
//
//  Enables intelligence sharing across all workspaces.
//  Connects Chat, Code, Vault, Data, Kanban, and Workflow contexts.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "CrossWorkspaceIntelligence")

// MARK: - Cross Workspace Intelligence

/// Central intelligence hub connecting all workspace contexts
@MainActor
final class CrossWorkspaceIntelligence: ObservableObject {

    // MARK: - Published State

    @Published private(set) var activeWorkspace: WorkspaceType = .chat
    @Published private(set) var workspaceContexts: [WorkspaceType: WorkspaceContext] = [:]
    @Published private(set) var crossWorkspaceInsights: [CrossWorkspaceInsight] = []
    @Published private(set) var lastSyncTime: Date?

    // MARK: - Dependencies

    private let ragBridge: RAGIntegrationBridge
    private let contextBridge: EnhancedContextBridge
    private let predictor: ANEPredictor
    private let embedder: HashEmbedder

    // MARK: - Configuration

    var enableAutoSync: Bool = true
    var syncInterval: TimeInterval = 60  // Seconds between syncs
    var maxInsightsPerWorkspace: Int = 5

    // MARK: - Singleton

    static let shared = CrossWorkspaceIntelligence()

    // MARK: - Background Sync

    private var syncTask: Task<Void, Never>?

    // MARK: - Initialization

    init(
        ragBridge: RAGIntegrationBridge? = nil,
        contextBridge: EnhancedContextBridge? = nil,
        predictor: ANEPredictor? = nil,
        embedder: HashEmbedder? = nil
    ) {
        self.ragBridge = ragBridge ?? .shared
        self.contextBridge = contextBridge ?? .shared
        self.predictor = predictor ?? .shared
        self.embedder = embedder ?? .shared

        // Initialize contexts for all workspaces
        for workspace in WorkspaceType.allCases {
            workspaceContexts[workspace] = WorkspaceContext(workspace: workspace)
        }

        // Start background sync if enabled
        if enableAutoSync {
            startBackgroundSync()
        }
    }

    deinit {
        syncTask?.cancel()
    }

    // MARK: - Workspace Switching

    /// Called when user switches to a workspace
    func onWorkspaceActivated(_ workspace: WorkspaceType, context: WorkspaceActivationContext? = nil) async {
        let previousWorkspace = activeWorkspace
        activeWorkspace = workspace

        // Update context for current workspace
        if let ctx = context {
            await updateWorkspaceContext(workspace, with: ctx)
        }

        // Generate cross-workspace insights
        await generateInsights(
            forWorkspace: workspace,
            fromWorkspace: previousWorkspace
        )

        logger.info("[CrossWorkspace] Activated: \(workspace.rawValue) (from \(previousWorkspace.rawValue))")
    }

    /// Update workspace context with new information
    func updateWorkspaceContext(_ workspace: WorkspaceType, with context: WorkspaceActivationContext) async {
        var workspaceCtx = workspaceContexts[workspace] ?? WorkspaceContext(workspace: workspace)

        workspaceCtx.lastActivated = Date()
        workspaceCtx.activeQuery = context.activeQuery
        workspaceCtx.activeEntities = context.entities
        workspaceCtx.recentTopics = context.topics

        // Generate embedding for current focus
        if let query = context.activeQuery {
            workspaceCtx.focusEmbedding = embedder.embed(query)
        }

        workspaceContexts[workspace] = workspaceCtx
    }

    // MARK: - Cross-Workspace Insights

    /// Generate insights for the activated workspace based on other workspaces
    private func generateInsights(
        forWorkspace target: WorkspaceType,
        fromWorkspace source: WorkspaceType
    ) async {
        var insights: [CrossWorkspaceInsight] = []

        // Get current context
        guard let targetContext = workspaceContexts[target] else { return }

        // Check each other workspace for relevant context
        for (workspace, context) in workspaceContexts where workspace != target {
            // Skip if no recent activity
            guard let lastActive = context.lastActivated,
                  Date().timeIntervalSince(lastActive) < 3600 else {  // Within last hour
                continue
            }

            // Calculate relevance between workspaces
            let relevance = calculateWorkspaceRelevance(
                target: targetContext,
                source: context
            )

            if relevance > 0.3 {
                // Search for relevant content from source workspace
                let relatedContent = await findRelatedContent(
                    from: workspace,
                    forQuery: targetContext.activeQuery ?? ""
                )

                if !relatedContent.isEmpty {
                    let insight = CrossWorkspaceInsight(
                        sourceWorkspace: workspace,
                        targetWorkspace: target,
                        relevance: relevance,
                        summary: buildInsightSummary(workspace: workspace, content: relatedContent),
                        relatedContent: relatedContent,
                        suggestedActions: buildSuggestedActions(
                            source: workspace,
                            target: target,
                            content: relatedContent
                        )
                    )
                    insights.append(insight)
                }
            }
        }

        // Sort by relevance and limit
        crossWorkspaceInsights = insights
            .sorted { $0.relevance > $1.relevance }
            .prefix(maxInsightsPerWorkspace * WorkspaceType.allCases.count)
            .map { $0 }
    }

    /// Calculate relevance between two workspace contexts
    private func calculateWorkspaceRelevance(
        target: WorkspaceContext,
        source: WorkspaceContext
    ) -> Float {
        var relevance: Float = 0

        // Embedding similarity
        if let targetEmbed = target.focusEmbedding,
           let sourceEmbed = source.focusEmbedding {
            relevance += HashEmbedder.cosineSimilarity(targetEmbed, sourceEmbed) * 0.4
        }

        // Shared entities
        let sharedEntities = Set(target.activeEntities).intersection(source.activeEntities)
        if !sharedEntities.isEmpty {
            relevance += Float(sharedEntities.count) * 0.1
        }

        // Topic overlap
        let sharedTopics = Set(target.recentTopics).intersection(source.recentTopics)
        if !sharedTopics.isEmpty {
            relevance += Float(sharedTopics.count) * 0.15
        }

        // Recency boost for source
        if let sourceActive = source.lastActivated {
            let minutesSince = Date().timeIntervalSince(sourceActive) / 60
            if minutesSince < 10 {
                relevance += 0.2
            } else if minutesSince < 30 {
                relevance += 0.1
            }
        }

        return min(1.0, relevance)
    }

    /// Find related content from a source workspace
    private func findRelatedContent(
        from workspace: WorkspaceType,
        forQuery query: String
    ) async -> [RelatedWorkspaceContent] {
        guard !query.isEmpty else { return [] }

        // Search RAG for content from that workspace type
        let searchQuery = UnifiedRAGQuery(
            query: query,
            limit: 5,
            sources: [workspace.ragSourceType]
        )

        let results = await ragBridge.search(searchQuery)

        return results.results.map { result in
            RelatedWorkspaceContent(
                id: result.id,
                workspace: workspace,
                content: result.content,
                snippet: result.snippet ?? String(result.content.prefix(200)),
                similarity: result.similarity,
                metadata: result.metadata
            )
        }
    }

    // MARK: - Insight Building

    private func buildInsightSummary(
        workspace: WorkspaceType,
        content: [RelatedWorkspaceContent]
    ) -> String {
        switch workspace {
        case .chat:
            return "Found \(content.count) related conversation\(content.count == 1 ? "" : "s")"
        case .code:
            return "Found \(content.count) related code file\(content.count == 1 ? "" : "s")"
        case .vault:
            return "Found \(content.count) related secure file\(content.count == 1 ? "" : "s")"
        case .data:
            return "Found \(content.count) related quer\(content.count == 1 ? "y" : "ies")"
        case .kanban:
            return "Found \(content.count) related task\(content.count == 1 ? "" : "s")"
        case .workflow:
            return "Found \(content.count) related workflow\(content.count == 1 ? "" : "s")"
        case .team:
            return "Found \(content.count) related team message\(content.count == 1 ? "" : "s")"
        case .magHub:
            return "Found \(content.count) related model\(content.count == 1 ? "" : "s")"
        }
    }

    private func buildSuggestedActions(
        source: WorkspaceType,
        target: WorkspaceType,
        content: [RelatedWorkspaceContent]
    ) -> [SuggestedAction] {
        var actions: [SuggestedAction] = []

        // Always suggest viewing related content
        actions.append(SuggestedAction(
            id: UUID(),
            title: "View in \(source.displayName)",
            icon: source.icon,
            action: .navigateToWorkspace(source)
        ))

        // Workspace-specific actions
        switch (source, target) {
        case (.code, .chat):
            actions.append(SuggestedAction(
                id: UUID(),
                title: "Reference code in chat",
                icon: "doc.text.insert",
                action: .insertReference(content.first?.id)
            ))

        case (.vault, .chat):
            actions.append(SuggestedAction(
                id: UUID(),
                title: "Attach file to chat",
                icon: "paperclip",
                action: .attachFile(content.first?.id)
            ))

        case (.kanban, .chat):
            actions.append(SuggestedAction(
                id: UUID(),
                title: "Link task to conversation",
                icon: "link",
                action: .linkTask(content.first?.id)
            ))

        case (.chat, .code):
            actions.append(SuggestedAction(
                id: UUID(),
                title: "View conversation context",
                icon: "bubble.left.and.bubble.right",
                action: .viewContext(content.first?.id)
            ))

        default:
            break
        }

        return actions
    }

    // MARK: - Background Sync

    private func startBackgroundSync() {
        syncTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: UInt64((self?.syncInterval ?? 60) * 1_000_000_000))

                guard !Task.isCancelled else { break }

                await self?.syncAllWorkspaces()
            }
        }
    }

    private func syncAllWorkspaces() async {
        // Sync context from each workspace
        for workspace in WorkspaceType.allCases {
            await syncWorkspace(workspace)
        }

        lastSyncTime = Date()
        logger.debug("[CrossWorkspace] Background sync complete")
    }

    private func syncWorkspace(_ workspace: WorkspaceType) async {
        // Get ANE predictions for this workspace
        let prediction = predictor.predictContextNeeds(
            currentWorkspace: workspace,
            recentQuery: workspaceContexts[workspace]?.activeQuery,
            activeFileId: nil
        )

        // Update context with predictions
        var context = workspaceContexts[workspace] ?? WorkspaceContext(workspace: workspace)
        context.predictedTopics = prediction.likelyTopics
        context.predictedCompression = prediction.compressionAggressiveness
        workspaceContexts[workspace] = context
    }

    // MARK: - Query API

    /// Get insights relevant to a specific query
    func getInsightsForQuery(_ query: String, inWorkspace workspace: WorkspaceType) async -> [CrossWorkspaceInsight] {
        // Update current workspace context with query
        await updateWorkspaceContext(workspace, with: WorkspaceActivationContext(
            activeQuery: query,
            entities: [],
            topics: extractTopics(from: query)
        ))

        // Regenerate insights
        await generateInsights(forWorkspace: workspace, fromWorkspace: workspace)

        return crossWorkspaceInsights.filter { $0.targetWorkspace == workspace }
    }

    /// Get all recent insights
    func getRecentInsights(limit: Int = 10) -> [CrossWorkspaceInsight] {
        return Array(crossWorkspaceInsights.prefix(limit))
    }

    /// Get insights from a specific workspace
    func getInsightsFromWorkspace(_ workspace: WorkspaceType) -> [CrossWorkspaceInsight] {
        return crossWorkspaceInsights.filter { $0.sourceWorkspace == workspace }
    }

    // MARK: - Helpers

    private func extractTopics(from query: String) -> [String] {
        // Simple keyword extraction
        let words = query
            .components(separatedBy: .whitespacesAndNewlines)
            .filter { $0.count >= 4 }
            .map { $0.lowercased() }

        // Remove common words
        let stopWords: Set<String> = [
            "what", "where", "when", "which", "that", "this", "have", "with",
            "from", "about", "could", "would", "should", "there", "their"
        ]

        return words.filter { !stopWords.contains($0) }
    }
}

// MARK: - Supporting Types

/// Context for a single workspace
struct WorkspaceContext {
    let workspace: WorkspaceType
    var lastActivated: Date?
    var activeQuery: String?
    var activeEntities: [String] = []
    var recentTopics: [String] = []
    var focusEmbedding: [Float]?
    var predictedTopics: [String] = []
    var predictedCompression: Float = 0.5
}

/// Context passed when activating a workspace
struct WorkspaceActivationContext {
    var activeQuery: String?
    var entities: [String] = []
    var topics: [String] = []
}

/// Insight connecting two workspaces
struct CrossWorkspaceInsight: Identifiable {
    let id = UUID()
    let sourceWorkspace: WorkspaceType
    let targetWorkspace: WorkspaceType
    let relevance: Float
    let summary: String
    let relatedContent: [RelatedWorkspaceContent]
    let suggestedActions: [SuggestedAction]
    let createdAt = Date()
}

/// Content from another workspace
struct RelatedWorkspaceContent: Identifiable {
    let id: String
    let workspace: WorkspaceType
    let content: String
    let snippet: String
    let similarity: Float
    let metadata: [String: String]?
}

/// Action suggested based on cross-workspace insight
struct SuggestedAction: Identifiable {
    let id: UUID
    let title: String
    let icon: String
    let action: ActionType

    enum ActionType {
        case navigateToWorkspace(WorkspaceType)
        case insertReference(String?)
        case attachFile(String?)
        case linkTask(String?)
        case viewContext(String?)
    }
}

// MARK: - Workspace Type Extensions

extension WorkspaceType {
    var displayName: String {
        switch self {
        case .chat: return "Chat"
        case .code: return "Code"
        case .vault: return "Vault"
        case .data: return "Data"
        case .kanban: return "Kanban"
        case .workflow: return "Workflow"
        case .team: return "Team"
        case .magHub: return "MagnetarHub"
        }
    }

    var icon: String {
        switch self {
        case .chat: return "bubble.left.and.bubble.right"
        case .code: return "chevron.left.forwardslash.chevron.right"
        case .vault: return "lock.shield"
        case .data: return "tablecells"
        case .kanban: return "square.grid.2x2"
        case .workflow: return "arrow.triangle.branch"
        case .team: return "person.3"
        case .magHub: return "sparkles"
        }
    }

    var ragSourceType: String {
        switch self {
        case .chat: return "chat_message"
        case .code: return "code_file"
        case .vault: return "vault_file"
        case .data: return "data_query"
        case .kanban: return "kanban_task"
        case .workflow: return "workflow"
        case .team: return "team_message"
        case .magHub: return "model_info"
        }
    }
}
