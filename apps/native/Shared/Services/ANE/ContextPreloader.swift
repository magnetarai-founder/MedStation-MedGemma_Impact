//
//  ContextPreloader.swift
//  MagnetarStudio
//
//  Pre-loads context based on ANE predictions for faster responses.
//  Ported from MagnetarAI-iPad.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "ContextPreloader")

// MARK: - Context Preloader

@MainActor
final class ContextPreloader: ObservableObject {

    // MARK: - Published State

    @Published private(set) var isPreloading: Bool = false
    @Published private(set) var preloadedThemeIds: Set<UUID> = []
    @Published private(set) var preloadedFileIds: Set<UUID> = []
    @Published private(set) var lastPreloadAt: Date?

    // MARK: - Dependencies

    private let predictor: ANEPredictor
    private let storageService: ConversationStorageService
    private let embedder: HashEmbedder

    // MARK: - Cache

    private var embeddingCache: [UUID: [Float]] = [:]
    private var themeCache: [UUID: ConversationTheme] = [:]
    private var fileCache: [UUID: FileReference] = [:]

    // MARK: - Configuration

    /// Staleness threshold for preloaded content (5 minutes)
    let stalenessThreshold: TimeInterval = 300

    /// Maximum items to preload
    let maxPreloadThemes = 10
    let maxPreloadFiles = 5

    // MARK: - Singleton

    static let shared = ContextPreloader()

    // MARK: - Initialization

    init(
        predictor: ANEPredictor? = nil,
        storageService: ConversationStorageService? = nil,
        embedder: HashEmbedder? = nil
    ) {
        self.predictor = predictor ?? .shared
        self.storageService = storageService ?? .shared
        self.embedder = embedder ?? .shared
    }

    // MARK: - Session Lifecycle

    /// Called when a session starts or becomes active
    func onSessionStart(sessionId: UUID) async {
        logger.info("[Preloader] Session started: \(sessionId)")
        await preloadForSession(sessionId)
    }

    /// Called when workspace changes
    func onWorkspaceChange(to workspace: WorkspaceType, sessionId: UUID?) async {
        logger.info("[Preloader] Workspace changed to: \(workspace.rawValue)")

        guard let sessionId = sessionId else { return }

        // Get predictions for new workspace
        let prediction = predictor.predictContextNeeds(
            currentWorkspace: workspace,
            recentQuery: nil,
            activeFileId: nil
        )

        // Preload based on predictions
        await preloadBasedOnPrediction(prediction, sessionId: sessionId)
    }

    // MARK: - Preloading

    /// Preload context for a session
    func preloadForSession(_ sessionId: UUID) async {
        guard !isPreloading else { return }
        isPreloading = true
        defer { isPreloading = false }

        logger.debug("[Preloader] Preloading for session \(sessionId)")

        // Load and cache themes
        let themes = storageService.loadThemes(sessionId)
        for theme in themes.prefix(maxPreloadThemes) {
            themeCache[theme.id] = theme
            preloadedThemeIds.insert(theme.id)

            // Pre-compute embeddings if not present
            if theme.embedding.isEmpty {
                embeddingCache[theme.id] = embedder.embed(theme.content)
            }
        }

        // Load and cache file references
        let files = storageService.loadFileReferences(sessionId)
        for file in files.prefix(maxPreloadFiles) {
            fileCache[file.id] = file
            preloadedFileIds.insert(file.id)

            // Pre-compute embeddings for file content
            if let content = file.processedContent {
                embeddingCache[file.id] = embedder.embed(content)
            }
        }

        lastPreloadAt = Date()
        logger.info("[Preloader] Preloaded \(themes.count) themes, \(files.count) files")
    }

    /// Preload based on ANE prediction
    private func preloadBasedOnPrediction(_ prediction: ContextPrediction, sessionId: UUID) async {
        // Preload suggested items
        for fileId in prediction.preloadSuggestions.prefix(maxPreloadFiles) {
            if fileCache[fileId] == nil {
                // Load file from storage
                let files = storageService.loadFileReferences(sessionId)
                if let file = files.first(where: { $0.id == fileId }) {
                    fileCache[fileId] = file
                    preloadedFileIds.insert(fileId)
                }
            }
        }

        // Preload themes matching predicted topics
        let themes = storageService.loadThemes(sessionId)
        for topic in prediction.likelyTopics {
            let matchingThemes = themes.filter {
                $0.topic.lowercased().contains(topic.lowercased())
            }
            for theme in matchingThemes.prefix(3) {
                if themeCache[theme.id] == nil {
                    themeCache[theme.id] = theme
                    preloadedThemeIds.insert(theme.id)
                }
            }
        }
    }

    // MARK: - RAG Enhancement

    /// Enhance RAG results with preloaded context
    func enhanceRAGResults(
        _ results: [RAGContextResult],
        query: String,
        sessionId: UUID
    ) -> [RAGContextResult] {
        var enhanced = results

        // Check if any preloaded themes are relevant but not in results
        let queryEmbedding = embedder.embed(query)

        for (themeId, theme) in themeCache {
            // Skip if already in results
            if results.contains(where: { $0.sourceId == themeId }) {
                continue
            }

            // Calculate relevance
            let themeEmbedding = embeddingCache[themeId] ?? embedder.embed(theme.content)
            let similarity = HashEmbedder.cosineSimilarity(queryEmbedding, themeEmbedding)

            if similarity > 0.5 {
                // Add to results
                enhanced.append(RAGContextResult(
                    sourceId: themeId,
                    sourceType: .theme,
                    content: theme.content,
                    relevanceScore: similarity,
                    isPreloaded: true
                ))
            }
        }

        // Sort by relevance
        return enhanced.sorted { $0.relevanceScore > $1.relevanceScore }
    }

    // MARK: - Cache Access

    /// Get cached theme
    func getCachedTheme(_ id: UUID) -> ConversationTheme? {
        return themeCache[id]
    }

    /// Get cached file
    func getCachedFile(_ id: UUID) -> FileReference? {
        return fileCache[id]
    }

    /// Get cached embedding
    func getCachedEmbedding(_ id: UUID) -> [Float]? {
        return embeddingCache[id]
    }

    /// Check if preloaded content is stale
    func isStale() -> Bool {
        guard let lastPreload = lastPreloadAt else { return true }
        return Date().timeIntervalSince(lastPreload) > stalenessThreshold
    }

    /// Refresh if stale
    func refreshIfStale(sessionId: UUID) async {
        if isStale() {
            await preloadForSession(sessionId)
        }
    }

    // MARK: - Cache Management

    /// Clear all caches
    func clearCache() {
        embeddingCache.removeAll()
        themeCache.removeAll()
        fileCache.removeAll()
        preloadedThemeIds.removeAll()
        preloadedFileIds.removeAll()
        lastPreloadAt = nil
        logger.info("[Preloader] Cleared all caches")
    }

    /// Evict specific items from cache
    func evict(themeIds: [UUID] = [], fileIds: [UUID] = []) {
        for id in themeIds {
            themeCache.removeValue(forKey: id)
            embeddingCache.removeValue(forKey: id)
            preloadedThemeIds.remove(id)
        }
        for id in fileIds {
            fileCache.removeValue(forKey: id)
            embeddingCache.removeValue(forKey: id)
            preloadedFileIds.remove(id)
        }
    }

    /// Get cache statistics
    var cacheStats: CacheStats {
        return CacheStats(
            themeCount: themeCache.count,
            fileCount: fileCache.count,
            embeddingCount: embeddingCache.count,
            isStale: isStale(),
            lastPreloadAt: lastPreloadAt
        )
    }

    struct CacheStats {
        let themeCount: Int
        let fileCount: Int
        let embeddingCount: Int
        let isStale: Bool
        let lastPreloadAt: Date?
    }
}

// MARK: - RAG Context Result

struct RAGContextResult: Identifiable, Sendable {
    let id = UUID()
    let sourceId: UUID
    let sourceType: RAGSourceType
    let content: String
    let relevanceScore: Float
    let isPreloaded: Bool

    enum RAGSourceType: String, Codable, Sendable {
        case theme
        case message
        case file
        case semanticNode
        case workflow
        case kanbanTask
    }

    init(
        sourceId: UUID,
        sourceType: RAGSourceType,
        content: String,
        relevanceScore: Float,
        isPreloaded: Bool = false
    ) {
        self.sourceId = sourceId
        self.sourceType = sourceType
        self.content = content
        self.relevanceScore = relevanceScore
        self.isPreloaded = isPreloaded
    }
}
