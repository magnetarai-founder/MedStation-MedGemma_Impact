//
//  EnhancedContextBridge.swift
//  MagnetarStudio
//
//  Bridges the context optimization system with chat and other workspaces.
//  Wires up CompactService, ContextOptimizer, and RAG for seamless integration.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "EnhancedContextBridge")

// MARK: - Enhanced Context Bridge

/// Bridges all context systems together for unified context management
@MainActor
final class EnhancedContextBridge: ObservableObject {

    // MARK: - Published State

    @Published private(set) var lastContextBuildTime: TimeInterval = 0
    @Published private(set) var lastCompactionTime: Date?
    @Published private(set) var activeSessionId: UUID?
    @Published private(set) var contextUtilization: Float = 0

    // MARK: - Dependencies

    private let contextOptimizer: ContextOptimizer
    private let compactService: CompactService
    private let semanticSearch: SemanticSearchService
    private let graphBuilder: SessionGraphBuilder
    private let fileIndex: CrossConversationFileIndex
    private let tierManager: ContextTierManager
    private let storageService: ConversationStorageService
    private let embedder: HashEmbedder

    // MARK: - Configuration

    var autoCompactThreshold: Int = 50  // Messages before auto-compaction
    var enableCrossConversationContext: Bool = true
    var enableRAGAugmentation: Bool = true

    // MARK: - Singleton

    static let shared = EnhancedContextBridge()

    // MARK: - Initialization

    init(
        contextOptimizer: ContextOptimizer? = nil,
        compactService: CompactService? = nil,
        semanticSearch: SemanticSearchService? = nil,
        graphBuilder: SessionGraphBuilder? = nil,
        fileIndex: CrossConversationFileIndex? = nil,
        tierManager: ContextTierManager? = nil,
        storageService: ConversationStorageService? = nil,
        embedder: HashEmbedder? = nil
    ) {
        self.contextOptimizer = contextOptimizer ?? .shared
        self.compactService = compactService ?? .shared
        self.semanticSearch = semanticSearch ?? .shared
        self.graphBuilder = graphBuilder ?? .shared
        self.fileIndex = fileIndex ?? .shared
        self.tierManager = tierManager ?? .shared
        self.storageService = storageService ?? .shared
        self.embedder = embedder ?? .shared
    }

    // MARK: - Context Building

    /// Build optimized context for a chat message
    func buildOptimizedChatContext(
        sessionId: UUID,
        messages: [ChatMessage],
        query: String,
        model: String
    ) async -> EnhancedChatContext {
        let startTime = Date()
        activeSessionId = sessionId

        // 1. Get appropriate token budget for model
        let budget = TokenBudget.forModel(model)

        // 2. Check if compaction is needed
        let compactionResult = await checkAndCompact(
            sessionId: sessionId,
            messages: messages
        )

        // 3. Get conversation themes from storage and filter by relevance
        let themes = getRelevantThemes(for: query, sessionId: sessionId, limit: 5)

        // 4. Get semantic nodes from graph
        let semanticNodes = await getRelevantSemanticNodes(query: query, limit: 5)

        // 5. Get RAG results if enabled
        var ragResults: [RAGSearchResult] = []
        if enableRAGAugmentation {
            do {
                ragResults = try await semanticSearch.search(
                    query: query,
                    conversationId: sessionId,
                    limit: 10,
                    minSimilarity: 0.3
                )
            } catch {
                logger.warning("[Bridge] RAG search failed, continuing without augmentation: \(error.localizedDescription)")
            }
        }

        // 6. Get cross-conversation files if enabled
        var relevantFiles: [CrossConversationFileResult] = []
        if enableCrossConversationContext {
            relevantFiles = await fileIndex.findRelevantFiles(
                query: query,
                limit: 5,
                excludeConversation: sessionId
            )
        }

        // 7. Build system prompt
        let systemPrompt = buildSystemPrompt(
            themes: themes,
            relevantFiles: relevantFiles
        )

        // 8. Optimize context
        let optimizedContext = contextOptimizer.buildOptimizedContext(
            messages: messages,
            themes: themes,
            semanticNodes: semanticNodes,
            historyBridge: compactionResult?.bridge,
            ragResults: ragResults,
            systemPrompt: systemPrompt,
            query: query,
            budget: budget
        )

        lastContextBuildTime = Date().timeIntervalSince(startTime)
        contextUtilization = optimizedContext.budgetUtilization

        logger.info("[Bridge] Built context: \(optimizedContext.totalTokens) tokens (\(String(format: "%.1f", optimizedContext.budgetUtilization))%), \(String(format: "%.3f", self.lastContextBuildTime))s")

        return EnhancedChatContext(
            optimizedContext: optimizedContext,
            compactionResult: compactionResult,
            relevantFiles: relevantFiles,
            budget: budget,
            buildDuration: lastContextBuildTime
        )
    }

    /// Process a sent message for indexing and graph building
    func processMessageForContext(
        message: ChatMessage,
        sessionId: UUID,
        conversationTitle: String?
    ) async {
        // 1. Index message for RAG
        do {
            try await semanticSearch.indexMessage(message, conversationId: sessionId)
        } catch {
            logger.warning("[Bridge] Failed to index message: \(error)")
        }

        // 2. Update session graph with entities
        graphBuilder.processMessage(message.content)

        // 3. Tier manager will handle content organization automatically

        // 4. Index any file references
        await indexFileReferences(from: message.content, sessionId: sessionId)

        logger.debug("[Bridge] Processed message for context: \(message.id)")
    }

    // MARK: - Compaction

    /// Check if compaction is needed and perform if so
    private func checkAndCompact(
        sessionId: UUID,
        messages: [ChatMessage]
    ) async -> CompactionResult? {
        guard messages.count >= autoCompactThreshold else {
            return nil
        }

        // Check when last compacted
        if let lastCompact = lastCompactionTime,
           Date().timeIntervalSince(lastCompact) < 300 {  // 5 minute cooldown
            return nil
        }

        logger.info("[Bridge] Auto-compacting session with \(messages.count) messages")

        do {
            let result = try await compactService.compact(
                sessionId: sessionId,
                messages: messages,
                forceCompact: false
            )
            lastCompactionTime = Date()
            return result
        } catch {
            logger.warning("[Bridge] Auto-compaction failed: \(error.localizedDescription)")
            return nil
        }
    }

    // MARK: - Semantic Nodes

    /// Get relevant semantic nodes for a query
    private func getRelevantSemanticNodes(query: String, limit: Int) async -> [SemanticNode] {
        let graph = graphBuilder.getGraph()

        // Extract entities from query
        let queryEntities = graphBuilder.extractEntities(from: query)

        // Find matching nodes in graph
        var relevantNodes: [SemanticNode] = []

        for (name, _) in queryEntities {
            if let entityNode = graph.findEntity(named: name) {
                // Get related entities
                let related = graph.relatedEntities(to: entityNode.id, limit: 3)

                // Convert to semantic nodes
                let semanticNode = SemanticNode(
                    id: entityNode.id,
                    concept: entityNode.name,
                    content: "Entity: \(entityNode.name) (\(entityNode.type.rawValue))",
                    embedding: entityNode.embedding ?? [],
                    entities: related.map { $0.name },
                    lastAccessed: entityNode.lastMentioned
                )
                relevantNodes.append(semanticNode)
            }
        }

        return Array(relevantNodes.prefix(limit))
    }

    // MARK: - Themes

    /// Get relevant themes for a query from the current session
    private func getRelevantThemes(for query: String, sessionId: UUID, limit: Int) -> [ConversationTheme] {
        let allThemes = storageService.loadThemes(sessionId)
        guard !allThemes.isEmpty else { return [] }

        let queryEmbedding = embedder.embed(query)

        // Score themes by relevance to query
        let scoredThemes = allThemes.map { theme -> (ConversationTheme, Float) in
            let similarity = HashEmbedder.cosineSimilarity(theme.embedding, queryEmbedding)
            return (theme, similarity)
        }

        // Sort by similarity and return top results
        return scoredThemes
            .sorted { $0.1 > $1.1 }
            .prefix(limit)
            .map { $0.0 }
    }

    // MARK: - System Prompt

    /// Build enhanced system prompt with context awareness
    private func buildSystemPrompt(
        themes: [ConversationTheme],
        relevantFiles: [CrossConversationFileResult]
    ) -> String {
        var prompt = """
        You are a helpful AI assistant in MagnetarStudio.

        """

        // Add theme context
        if !themes.isEmpty {
            prompt += "\n## Conversation Context\n"
            for theme in themes.prefix(3) {
                prompt += "- \(theme.topic): \(theme.content.prefix(100))...\n"
            }
        }

        // Add cross-conversation file awareness
        if !relevantFiles.isEmpty {
            prompt += "\n## Relevant Files from Other Conversations\n"
            prompt += "The user has worked with these files in related contexts:\n"
            for file in relevantFiles.prefix(3) {
                prompt += "- \(file.filename) (\(file.description))\n"
            }
        }

        return prompt
    }

    // MARK: - File Indexing

    /// Index file references mentioned in message content
    private func indexFileReferences(from content: String, sessionId: UUID) async {
        // Simple pattern matching for file paths
        let patterns = [
            try? NSRegularExpression(pattern: "[\\w/.-]+\\.[a-zA-Z]{2,4}", options: []),
            try? NSRegularExpression(pattern: "`([^`]+)`", options: [])
        ].compactMap { $0 }

        var filePaths: Set<String> = []

        for pattern in patterns {
            let range = NSRange(content.startIndex..., in: content)
            let matches = pattern.matches(in: content, options: [], range: range)

            for match in matches {
                if let swiftRange = Range(match.range, in: content) {
                    let path = String(content[swiftRange])
                    if looksLikeFilePath(path) {
                        filePaths.insert(path)
                    }
                }
            }
        }

        // Index each file reference
        for path in filePaths {
            let fileRef = FileReference(
                filename: (path as NSString).lastPathComponent,
                originalPath: path,
                fileType: (path as NSString).pathExtension
            )

            await fileIndex.indexFile(fileRef, conversationId: sessionId, query: nil)
        }
    }

    /// Check if a string looks like a file path
    private func looksLikeFilePath(_ path: String) -> Bool {
        // Must have extension
        guard path.contains(".") else { return false }

        // Filter out URLs
        guard !path.hasPrefix("http") else { return false }

        // Common extensions
        let codeExtensions = ["swift", "py", "ts", "js", "tsx", "jsx", "go", "rs", "java", "kt", "cpp", "c", "h"]
        let docExtensions = ["md", "txt", "json", "yaml", "yml", "xml", "html", "css"]
        let allExtensions = codeExtensions + docExtensions

        let ext = (path as NSString).pathExtension.lowercased()
        return allExtensions.contains(ext)
    }

    // MARK: - Session Management

    /// Called when a session is selected
    func onSessionSelected(_ sessionId: UUID) async {
        activeSessionId = sessionId

        // Load graph for this session
        if let savedGraph = await loadSessionGraph(sessionId) {
            graphBuilder.setGraph(savedGraph)
        }

        logger.info("[Bridge] Session selected: \(sessionId)")
    }

    /// Called when a session ends
    func onSessionEnded(_ sessionId: UUID, messages: [ChatMessage]) async {
        // Final compaction
        if messages.count > 20 {
            do {
                let _ = try await compactService.compact(
                    sessionId: sessionId,
                    messages: messages,
                    forceCompact: true
                )
            } catch {
                logger.warning("[Bridge] Session end compaction failed for \(sessionId): \(error.localizedDescription)")
            }
        }

        // Save session graph
        await saveSessionGraph(sessionId)

        // Apply decay to graph
        graphBuilder.applyDecay()

        logger.info("[Bridge] Session ended: \(sessionId)")
    }

    // MARK: - Persistence

    private func loadSessionGraph(_ sessionId: UUID) async -> SessionGraph? {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let graphPath = documentsPath
            .appendingPathComponent(".magnetar_studio/sessions")
            .appendingPathComponent("\(sessionId.uuidString)/graph.json")

        guard FileManager.default.fileExists(atPath: graphPath.path) else {
            return nil
        }

        do {
            let data = try Data(contentsOf: graphPath)
            return try JSONDecoder().decode(SessionGraph.self, from: data)
        } catch {
            logger.warning("[Bridge] Failed to load session graph: \(error)")
            return nil
        }
    }

    private func saveSessionGraph(_ sessionId: UUID) async {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let sessionsPath = documentsPath.appendingPathComponent(".magnetar_studio/sessions/\(sessionId.uuidString)")

        do {
            try FileManager.default.createDirectory(at: sessionsPath, withIntermediateDirectories: true)

            let graphPath = sessionsPath.appendingPathComponent("graph.json")
            let graph = graphBuilder.getGraph()
            let data = try JSONEncoder().encode(graph)
            try data.write(to: graphPath)
        } catch {
            logger.warning("[Bridge] Failed to save session graph: \(error)")
        }
    }
}

// MARK: - Enhanced Chat Context

/// Result of building optimized chat context
struct EnhancedChatContext {
    let optimizedContext: OptimizedContext
    let compactionResult: CompactionResult?
    let relevantFiles: [CrossConversationFileResult]
    let budget: TokenBudget
    let buildDuration: TimeInterval

    /// Format context for API request
    func formatForRequest() -> String {
        return optimizedContext.contextString
    }

    /// Get messages to include in conversation history
    func getMessagesToInclude() -> [ContextItem] {
        return optimizedContext.includedMessages
    }

    /// Summary for debugging
    var debugSummary: String {
        var parts: [String] = []

        parts.append("Tokens: \(optimizedContext.totalTokens)/\(budget.total)")
        parts.append("Utilization: \(String(format: "%.1f", optimizedContext.budgetUtilization))%")

        if compactionResult != nil {
            parts.append("Compacted: Yes")
        }

        if !relevantFiles.isEmpty {
            parts.append("Cross-conv files: \(relevantFiles.count)")
        }

        parts.append("Build time: \(String(format: "%.3f", buildDuration))s")

        return parts.joined(separator: " | ")
    }
}

// MARK: - Context Service Extension

extension EnhancedContextBridge {

    /// Quick context summary for UI display
    func getContextSummary() -> ContextSummary {
        return ContextSummary(
            utilizationPercent: contextUtilization,
            lastBuildTime: lastContextBuildTime,
            hasActiveSession: activeSessionId != nil,
            lastCompaction: lastCompactionTime
        )
    }
}

/// Summary of context state for UI
struct ContextSummary {
    let utilizationPercent: Float
    let lastBuildTime: TimeInterval
    let hasActiveSession: Bool
    let lastCompaction: Date?

    var formattedUtilization: String {
        return String(format: "%.0f%%", utilizationPercent)
    }

    var formattedBuildTime: String {
        return String(format: "%.0fms", lastBuildTime * 1000)
    }
}
