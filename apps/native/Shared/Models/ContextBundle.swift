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
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "ContextBundle")

// MARK: - Ollama API Types (for model discovery)

struct OllamaTagsResponse: Codable {
    let models: [OllamaModelInfo]
}

/// Model info from Ollama API (distinct from ModelsStore.OllamaModel for UI state)
struct OllamaModelInfo: Codable {
    let name: String
    let size: Int64  // Size in bytes
    let modifiedAt: String
    let details: OllamaModelInfoDetails?

    enum CodingKeys: String, CodingKey {
        case name, size
        case modifiedAt = "modified_at"
        case details
    }

    /// Size in GB for display
    var sizeGB: Double {
        return Double(size) / 1_073_741_824.0  // 1024^3
    }
}

struct OllamaModelInfoDetails: Codable {
    let parameterSize: String?
    let quantizationLevel: String?
    let format: String?
    let family: String?

    enum CodingKeys: String, CodingKey {
        case parameterSize = "parameter_size"
        case quantizationLevel = "quantization_level"
        case format, family
    }
}

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
    let unlockedVaultType: String?  // "real" or "decoy" (if unlocked)
    let recentlyAccessedFiles: [VaultFileMetadata]  // Last 5 files user opened
    let currentlyGrantedPermissions: [FilePermission]  // Active file permissions
    let relevantFiles: [RelevantVaultFile]?  // Files relevant to query (semantic search)

    // IMPORTANT: File contents are NEVER included in bundle
    // Models must request access via VaultPermissionManager
}

// MARK: - Bundled Data Context

/// Query result from semantic search (includes relevance score)
struct RelevantQuery: Codable {
    let queryId: String
    let queryText: String
    let tableName: String?
    let relevanceScore: Float
}

/// Data workspace context - recent queries and loaded tables
struct BundledDataContext: Codable {
    let activeTables: [TableMetadata]  // Currently loaded tables
    let recentQueries: [RecentQuery]  // Last 3 queries
    let relevantQueries: [RelevantQuery]?  // Queries similar to current request (semantic search)
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

// MARK: - Bundled Code Context

/// Code workspace context - open files and git state
struct BundledCodeContext: Codable {
    let openFiles: [String]  // File paths
    let recentEdits: [CodeEdit]
    let gitBranch: String?
    let gitStatus: String?  // "clean", "uncommitted changes", etc.
    let relevantFiles: [RelevantCodeFile]?  // Files semantically related to query
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
        let dataContext = await bundleDataContext(
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
        let workflowContext = await bundleWorkflowContext(
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
        let codeContext = await bundleCodeContext(
            from: appContext.code,
            relevance: relevance,
            query: query
        )

        // Fetch RAG documents and vector search results in parallel
        async let ragDocsTask = fetchRAGDocuments(
            query: query,
            aneState: appContext.vectorMemory
        )
        async let vectorResultsTask = fetchVectorSearchResults(
            query: query,
            aneState: appContext.vectorMemory
        )

        let ragDocuments = await ragDocsTask
        let vectorSearchResults = await vectorResultsTask

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
            vectorSearchResults: vectorSearchResults,
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

        // Semantic search for relevant files
        let relevantFiles = await fetchRelevantVaultFiles(query: query, vaultType: vault.unlockedVaultType ?? "real")

        return BundledVaultContext(
            unlockedVaultType: vault.unlockedVaultType,
            recentlyAccessedFiles: Array(vault.recentFiles.prefix(5)),
            currentlyGrantedPermissions: vault.activePermissions,
            relevantFiles: relevantFiles
        )
    }

    private func bundleDataContext(
        from data: DataContext,
        relevance: QueryRelevance,
        query: String
    ) async -> BundledDataContext? {
        guard relevance.needsDataContext || relevance.currentWorkspaceType == "data" else {
            return nil
        }

        // Search for similar queries using semantic search
        let queryResults = await ContextService.shared.searchDataQueries(for: query, limit: 3)
        let relevantQueries: [RelevantQuery]? = queryResults.isEmpty ? nil : queryResults.map { result in
            RelevantQuery(
                queryId: result.queryId,
                queryText: result.queryText,
                tableName: result.tableName,
                relevanceScore: result.relevanceScore
            )
        }

        return BundledDataContext(
            activeTables: data.loadedTables,
            recentQueries: Array(data.recentQueries.prefix(3)),
            relevantQueries: relevantQueries,
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
    ) async -> BundledWorkflowContext? {
        guard relevance.needsWorkflowContext || relevance.currentWorkspaceType == "workflows" else {
            return nil
        }

        // Semantic search for relevant workflows
        let relevantWorkflows = await fetchRelevantWorkflows(query: query)

        return BundledWorkflowContext(
            activeWorkflows: Array(workflow.activeWorkflows.prefix(5)),
            recentExecutions: Array(workflow.recentExecutions.prefix(5)),
            relevantWorkflows: relevantWorkflows
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

        // Extract @mentions from query using simple regex
        var mentionedUsers: [String]? = nil
        let mentionPattern = "@(\\w+)"
        if let regex = try? NSRegularExpression(pattern: mentionPattern, options: []) {
            let nsString = query as NSString
            let results = regex.matches(in: query, options: [], range: NSRange(location: 0, length: nsString.length))
            let mentions = results.compactMap { result -> String? in
                if result.numberOfRanges > 1 {
                    let range = result.range(at: 1)
                    return nsString.substring(with: range)
                }
                return nil
            }
            mentionedUsers = mentions.isEmpty ? nil : mentions
        }

        return BundledTeamContext(
            activeChannel: team.activeChannel,
            recentMessages: Array(team.recentMessages.prefix(10)),
            onlineMembers: team.onlineMembers,
            mentionedUsers: mentionedUsers
        )
    }

    private func bundleCodeContext(
        from code: CodeContext,
        relevance: QueryRelevance,
        query: String
    ) async -> BundledCodeContext? {
        guard relevance.needsCodeContext || relevance.currentWorkspaceType == "code" else {
            return nil
        }

        // Get git status if in a git repo
        let gitStatus = getGitStatus()

        // Semantic search for relevant code files via Context Engine
        // Returns results when code content is indexed; empty until then
        let codeSearchResults = await ContextService.shared.searchCodeFiles(for: query, limit: 5)
        let relevantFiles: [RelevantCodeFile]? = codeSearchResults.isEmpty ? nil : codeSearchResults.map { result in
            RelevantCodeFile(
                fileId: result.fileId,
                fileName: result.fileName,
                filePath: result.filePath,
                language: result.language,
                snippet: result.snippet,
                lineNumber: result.lineNumber,
                relevanceScore: result.relevanceScore
            )
        }

        return BundledCodeContext(
            openFiles: code.openFiles,
            recentEdits: Array(code.recentEdits.prefix(5)),
            gitBranch: code.gitBranch,
            gitStatus: gitStatus,
            relevantFiles: relevantFiles
        )
    }

    private func getGitStatus() -> String? {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/git")
        process.arguments = ["status", "--porcelain"]

        let pipe = Pipe()
        process.standardOutput = pipe
        process.standardError = Pipe()

        do {
            try process.run()
            process.waitUntilExit()

            guard process.terminationStatus == 0 else {
                // Not a git repo or git error
                return nil
            }

            let data = pipe.fileHandleForReading.readDataToEndOfFile()
            let output = String(data: data, encoding: .utf8) ?? ""

            if output.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                return "clean"
            } else {
                let lines = output.split(separator: "\n")
                let modifiedCount = lines.filter { $0.hasPrefix(" M") || $0.hasPrefix("M ") }.count
                let addedCount = lines.filter { $0.hasPrefix("A ") || $0.hasPrefix("??") }.count
                let deletedCount = lines.filter { $0.hasPrefix(" D") || $0.hasPrefix("D ") }.count

                var statusParts: [String] = []
                if modifiedCount > 0 {
                    statusParts.append("\(modifiedCount) modified")
                }
                if addedCount > 0 {
                    statusParts.append("\(addedCount) added")
                }
                if deletedCount > 0 {
                    statusParts.append("\(deletedCount) deleted")
                }

                return statusParts.isEmpty ? "uncommitted changes" : statusParts.joined(separator: ", ")
            }
        } catch {
            return nil
        }
    }

    private func fetchRAGDocuments(
        query: String,
        aneState: ANEContextState
    ) async -> [RAGDocument]? {
        guard aneState.available else {
            return nil
        }

        // Query ANE Context Engine backend for semantic search
        do {
            let searchRequest = ContextSearchRequest(
                query: query,
                sessionId: nil,
                workspaceTypes: nil,  // Search across all workspaces
                limit: 10
            )

            let response: ContextSearchResponse = try await ApiClient.shared.request(
                "/v1/context/search",
                method: .post,
                body: searchRequest
            )

            // Convert search results to RAGDocuments
            let ragDocs = response.results.map { result in
                // Extract sourceId from metadata if available
                let sourceId = result.metadata["session_id"]?.value as? String

                // Convert AnyCodable metadata to String dictionary
                var stringMetadata: [String: String] = [:]
                for (key, value) in result.metadata {
                    stringMetadata[key] = String(describing: value.value)
                }

                return RAGDocument(
                    id: sourceId ?? UUID().uuidString,
                    content: result.content,
                    source: result.source,
                    sourceId: sourceId,
                    relevanceScore: result.relevanceScore,
                    metadata: stringMetadata
                )
            }

            return ragDocs.isEmpty ? nil : ragDocs
        } catch {
            logger.warning("Failed to fetch RAG documents: \(error)")
            return nil
        }
    }

    /// Fetch vector search results from ANE Context Engine
    /// Returns structured results with workspace type and resource metadata
    private func fetchVectorSearchResults(
        query: String,
        aneState: ANEContextState
    ) async -> [VectorSearchResult]? {
        guard aneState.available else {
            return nil
        }

        do {
            let searchRequest = ContextSearchRequest(
                query: query,
                sessionId: nil,
                workspaceTypes: nil,
                limit: 10
            )

            let response: ContextSearchResponse = try await ApiClient.shared.request(
                "/v1/context/search",
                method: .post,
                body: searchRequest
            )

            let results = response.results.compactMap { result -> VectorSearchResult? in
                // Extract metadata fields
                let sessionId = result.metadata["session_id"]?.value as? String ?? UUID().uuidString
                let resourceType = result.metadata["resource_type"]?.value as? String ?? result.source
                let author = result.metadata["author"]?.value as? String
                let timestampStr = result.metadata["timestamp"]?.value as? String
                let tagsValue = result.metadata["tags"]?.value
                let tags: [String]? = (tagsValue as? [String]) ?? nil

                // Parse timestamp or use current date
                let timestamp: Date
                if let ts = timestampStr, let parsedDate = ISO8601DateFormatter().date(from: ts) {
                    timestamp = parsedDate
                } else {
                    timestamp = Date()
                }

                return VectorSearchResult(
                    id: sessionId,
                    text: result.content,
                    workspaceType: result.source,
                    resourceId: sessionId,
                    similarity: result.relevanceScore,
                    metadata: VectorMetadata(
                        resourceType: resourceType,
                        timestamp: timestamp,
                        author: author,
                        tags: tags
                    )
                )
            }

            return results.isEmpty ? nil : results
        } catch {
            logger.warning("Failed to fetch vector search results: \(error)")
            return nil
        }
    }

    private func fetchAvailableModels(
        systemResources: SystemResourceState
    ) async -> [AvailableModel] {
        // Fetch all available models from Ollama
        var allModels: [AvailableModel] = []

        do {
            let ollamaURL = APIConfiguration.shared.ollamaURL
            guard let url = URL(string: "\(ollamaURL)/api/tags") else {
                return systemResources.activeModels.map { modelFromLoaded($0) }
            }

            let (data, _) = try await URLSession.shared.data(from: url)
            let response = try JSONDecoder().decode(OllamaTagsResponse.self, from: data)

            for model in response.models {
                let loadedModel = systemResources.activeModels.first { $0.id == model.name }

                allModels.append(AvailableModel(
                    id: model.name,
                    name: model.name,
                    displayName: model.name,
                    slotNumber: loadedModel?.slotNumber,
                    isPinned: loadedModel?.isPinned ?? false,
                    memoryUsageGB: loadedModel?.memoryUsageGB ?? Float(model.sizeGB),
                    capabilities: inferCapabilities(from: model),
                    isHealthy: true
                ))
            }
        } catch {
            logger.warning("Failed to fetch models from Ollama: \(error)")
            // Fall back to loaded models only
            return systemResources.activeModels.map { modelFromLoaded($0) }
        }

        return allModels
    }

    private func modelFromLoaded(_ loadedModel: LoadedModel) -> AvailableModel {
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

    private func inferCapabilities(from model: OllamaModelInfo) -> ModelCapabilities {
        let name = model.name.lowercased()
        return ModelCapabilities(
            chat: true,
            codeGeneration: name.contains("code") || name.contains("qwen") || name.contains("deepseek"),
            dataAnalysis: name.contains("phi") || name.contains("llama"),
            reasoning: name.contains("deepseek") || name.contains("r1"),
            maxContextTokens: 8192,
            specialized: nil
        )
    }

    private func fetchRelevantVaultFiles(query: String, vaultType: String) async -> [RelevantVaultFile]? {
        do {
            struct SemanticSearchRequest: Codable {
                let query: String
                let vaultType: String
                let limit: Int
                let minSimilarity: Float
            }

            struct SemanticSearchResult: Codable {
                let fileId: String
                let filename: String
                let similarityScore: Float
                let filePath: String?
                let fileSize: Int?
                let createdAt: String?
                let modifiedAt: String?
                let snippet: String?
            }

            struct SemanticSearchResponse: Codable {
                let results: [SemanticSearchResult]
                let query: String
                let totalResults: Int
            }

            let searchRequest = SemanticSearchRequest(
                query: query,
                vaultType: vaultType,
                limit: 10,
                minSimilarity: 0.4
            )

            let response: SemanticSearchResponse = try await ApiClient.shared.request(
                "/v1/vault/semantic-search",
                method: .post,
                body: searchRequest
            )

            let files = response.results.map { result in
                RelevantVaultFile(
                    fileId: result.fileId,
                    fileName: result.filename,
                    filePath: result.filePath ?? "/",
                    snippet: result.snippet ?? "",
                    relevanceScore: result.similarityScore
                )
            }

            return files.isEmpty ? nil : files
        } catch {
            logger.warning("Failed to fetch relevant vault files: \(error)")
            return nil
        }
    }

    private func fetchRelevantWorkflows(query: String) async -> [WorkflowSummary]? {
        do {
            struct WorkflowSemanticSearchRequest: Codable {
                let query: String
                let limit: Int
                let minSimilarity: Float
            }

            struct WorkflowSearchResult: Codable {
                let workflowId: String
                let workflowName: String
                let description: String?
                let createdAt: String
                let similarityScore: Float
            }

            struct WorkflowSemanticSearchResponse: Codable {
                let results: [WorkflowSearchResult]
                let query: String
                let totalResults: Int
            }

            let searchRequest = WorkflowSemanticSearchRequest(
                query: query,
                limit: 10,
                minSimilarity: 0.4
            )

            let response: WorkflowSemanticSearchResponse = try await ApiClient.shared.request(
                "/v1/automation/workflows/semantic-search",
                method: .post,
                body: searchRequest
            )

            let workflows = response.results.map { result in
                WorkflowSummary(
                    id: result.workflowId,
                    name: result.workflowName,
                    status: "active",  // Default status, adjust as needed
                    lastRun: ISO8601DateFormatter().date(from: result.createdAt)
                )
            }

            return workflows.isEmpty ? nil : workflows
        } catch {
            logger.warning("Failed to fetch relevant workflows: \(error)")
            return nil
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
