//
//  SemanticSearchService.swift
//  MagnetarStudio
//
//  High-level semantic search service for RAG.
//  Orchestrates vector store, embedder, and context retrieval.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "SemanticSearch")

// MARK: - Semantic Search Service

@MainActor
final class SemanticSearchService: ObservableObject {

    // MARK: - Published State

    @Published private(set) var isIndexing: Bool = false
    @Published private(set) var lastSearchAt: Date?
    @Published private(set) var searchCount: Int = 0
    @Published private(set) var averageSearchTime: TimeInterval = 0

    // MARK: - Dependencies

    private let vectorStore: VectorStore
    private let embedder: HashEmbedder
    private let conversationStorage: ConversationStorageService
    private let predictor: ANEPredictor

    // MARK: - Configuration

    var configuration: RAGConfiguration = .default

    // MARK: - Singleton

    static let shared = SemanticSearchService()

    // MARK: - Initialization

    init(
        vectorStore: VectorStore? = nil,
        embedder: HashEmbedder? = nil,
        conversationStorage: ConversationStorageService? = nil,
        predictor: ANEPredictor? = nil
    ) {
        self.vectorStore = vectorStore ?? .shared
        self.embedder = embedder ?? .shared
        self.conversationStorage = conversationStorage ?? .shared
        self.predictor = predictor ?? .shared
    }

    // MARK: - Search

    /// Perform semantic search across all indexed content
    func search(
        query: String,
        sources: [RAGSource]? = nil,
        conversationId: UUID? = nil,
        limit: Int? = nil,
        minSimilarity: Float? = nil
    ) async throws -> [RAGSearchResult] {
        let startTime = Date()

        // Embed query
        let queryEmbedding = embedder.embed(query)

        // Use configuration or overrides
        let effectiveLimit = limit ?? configuration.maxResults
        let effectiveMinSimilarity = minSimilarity ?? configuration.minSimilarity
        let effectiveSources = sources ?? (configuration.enabledSources.map { Array($0) })

        // Search vector store
        var results = try await vectorStore.search(
            query: queryEmbedding,
            limit: effectiveLimit,
            minSimilarity: effectiveMinSimilarity,
            sources: effectiveSources,
            conversationId: conversationId
        )

        // Apply recency boost
        results = applyRecencyBoost(to: results)

        // Apply ANE-based relevance boost
        results = applyANEBoost(to: results, query: query)

        // Sort by combined score
        results.sort { $0.combinedScore > $1.combinedScore }

        // Update stats
        let duration = Date().timeIntervalSince(startTime)
        updateStats(duration: duration)

        logger.info("[SemanticSearch] Query '\(query.prefix(30))' returned \(results.count) results in \(String(format: "%.2f", duration * 1000))ms")

        return Array(results.prefix(effectiveLimit))
    }

    /// Search within a specific conversation
    func searchConversation(
        query: String,
        conversationId: UUID,
        includeThemes: Bool = true,
        includeSemanticNodes: Bool = true
    ) async throws -> [RAGSearchResult] {
        var sources: [RAGSource] = [.chatMessage]
        if includeThemes { sources.append(.theme) }
        if includeSemanticNodes { sources.append(.semanticNode) }

        return try await search(
            query: query,
            sources: sources,
            conversationId: conversationId
        )
    }

    /// Search for similar content to a given document
    func findSimilar(
        to document: RAGDocument,
        limit: Int = 5
    ) async throws -> [RAGSearchResult] {
        var results = try await vectorStore.search(
            query: document.embedding,
            limit: limit + 1,  // +1 to exclude self
            minSimilarity: configuration.minSimilarity
        )

        // Remove the document itself from results
        results = results.filter { $0.document.id != document.id }

        return Array(results.prefix(limit))
    }

    /// Hybrid search combining semantic and keyword matching
    func hybridSearch(
        query: String,
        conversationId: UUID? = nil,
        limit: Int? = nil
    ) async throws -> [RAGSearchResult] {
        // Semantic search
        var semanticResults = try await search(
            query: query,
            conversationId: conversationId,
            limit: (limit ?? configuration.maxResults) * 2
        )

        // Keyword boost for exact matches
        let keywords = extractKeywords(from: query)
        for i in 0..<semanticResults.count {
            let matchCount = countKeywordMatches(
                keywords: keywords,
                in: semanticResults[i].document.content
            )
            if matchCount > 0 {
                // Boost similarity for keyword matches
                let boost = Float(min(matchCount, 5)) * 0.05
                semanticResults[i] = RAGSearchResult(
                    document: semanticResults[i].document,
                    similarity: min(1.0, semanticResults[i].similarity + boost),
                    rank: semanticResults[i].rank,
                    matchedTerms: keywords.filter {
                        semanticResults[i].document.content.lowercased().contains($0)
                    },
                    snippet: semanticResults[i].snippet
                )
            }
        }

        // Re-sort by updated similarity
        semanticResults.sort { $0.similarity > $1.similarity }

        return Array(semanticResults.prefix(limit ?? configuration.maxResults))
    }

    // MARK: - Indexing

    /// Index content for search
    func index(request: RAGIndexRequest) async throws -> RAGIndexResult {
        isIndexing = true
        defer { isIndexing = false }

        let startTime = Date()
        var documentIds: [UUID] = []

        // Chunk if needed
        let chunks: [(String, Int?)]
        if request.chunkIfNeeded && request.content.count > configuration.maxChunkSize {
            let chunkedTexts = TextChunker.chunk(
                request.content,
                chunkSize: configuration.maxChunkSize,
                overlap: configuration.chunkOverlap
            )
            chunks = chunkedTexts.enumerated().map { ($1, $0) }
        } else {
            chunks = [(request.content, nil)]
        }

        // Create and index documents
        for (content, chunkIndex) in chunks {
            let embedding = embedder.embed(content)

            var metadata = request.metadata
            if let index = chunkIndex {
                metadata = RAGDocumentMetadata(
                    conversationId: request.metadata.conversationId,
                    sessionId: request.metadata.sessionId,
                    messageId: request.metadata.messageId,
                    fileId: request.metadata.fileId,
                    title: request.metadata.title,
                    contentType: request.metadata.contentType,
                    chunkIndex: index,
                    totalChunks: chunks.count,
                    tags: request.metadata.tags,
                    isVaultProtected: request.metadata.isVaultProtected
                )
            }

            let document = RAGDocument(
                content: content,
                embedding: embedding,
                source: request.source,
                metadata: metadata
            )

            try await vectorStore.insert(document)
            documentIds.append(document.id)
        }

        let duration = Date().timeIntervalSince(startTime)
        let tokensIndexed = chunks.reduce(0) { $0 + $1.0.count / 4 }

        logger.info("[SemanticSearch] Indexed \(documentIds.count) documents (\(tokensIndexed) tokens) in \(String(format: "%.2f", duration))s")

        return RAGIndexResult(
            documentIds: documentIds,
            chunksCreated: chunks.count,
            tokensIndexed: tokensIndexed,
            duration: duration
        )
    }

    /// Index a chat message
    func indexMessage(_ message: ChatMessage, conversationId: UUID) async throws {
        let request = RAGIndexRequest(
            content: message.content,
            source: .chatMessage,
            metadata: RAGDocumentMetadata(
                conversationId: conversationId,
                messageId: message.id
            ),
            chunkIfNeeded: false  // Messages are typically short
        )

        _ = try await index(request: request)
    }

    /// Index a theme
    func indexTheme(_ theme: ConversationTheme, conversationId: UUID) async throws {
        // Theme already has embedding, insert directly
        let document = RAGDocument(
            id: theme.id,
            content: theme.content,
            embedding: theme.embedding,
            source: .theme,
            metadata: RAGDocumentMetadata(
                conversationId: conversationId,
                title: theme.topic
            )
        )

        try await vectorStore.insert(document)
    }

    /// Index a semantic node
    func indexSemanticNode(_ node: SemanticNode, conversationId: UUID) async throws {
        let document = RAGDocument(
            id: node.id,
            content: node.content,
            embedding: node.embedding,
            source: .semanticNode,
            metadata: RAGDocumentMetadata(
                conversationId: conversationId,
                title: node.concept
            )
        )

        try await vectorStore.insert(document)
    }

    /// Index a file
    func indexFile(
        content: String,
        filename: String,
        fileId: UUID,
        conversationId: UUID?,
        isVaultProtected: Bool = false
    ) async throws -> RAGIndexResult {
        let request = RAGIndexRequest(
            content: content,
            source: isVaultProtected ? .vaultFile : .file,
            metadata: RAGDocumentMetadata(
                conversationId: conversationId,
                fileId: fileId,
                title: filename,
                isVaultProtected: isVaultProtected
            ),
            chunkIfNeeded: true
        )

        return try await index(request: request)
    }

    // MARK: - Batch Operations

    /// Re-index all content for a conversation
    func reindexConversation(_ conversationId: UUID) async throws {
        isIndexing = true
        defer { isIndexing = false }

        // Clear existing
        try await vectorStore.deleteForConversation(conversationId)

        // Load and index themes
        let themes = conversationStorage.loadThemes(conversationId)
        for theme in themes {
            try await indexTheme(theme, conversationId: conversationId)
        }

        // Load and index semantic nodes
        let nodes = conversationStorage.loadSemanticNodes(conversationId)
        for node in nodes {
            try await indexSemanticNode(node, conversationId: conversationId)
        }

        logger.info("[SemanticSearch] Re-indexed conversation \(conversationId): \(themes.count) themes, \(nodes.count) nodes")
    }

    // MARK: - Helpers

    /// Apply recency boost to search results
    private func applyRecencyBoost(to results: [RAGSearchResult]) -> [RAGSearchResult] {
        let now = Date()
        let windowSeconds = configuration.recencyWindow * 3600

        return results.map { result in
            let age = now.timeIntervalSince(result.document.createdAt)
            if age < windowSeconds {
                let recencyFactor = 1.0 - (age / windowSeconds)
                let boost = Float(recencyFactor) * configuration.recencyBoost
                return RAGSearchResult(
                    document: result.document,
                    similarity: min(1.0, result.similarity + boost),
                    rank: result.rank,
                    matchedTerms: result.matchedTerms,
                    snippet: result.snippet
                )
            }
            return result
        }
    }

    /// Apply ANE-based user pattern boost
    private func applyANEBoost(to results: [RAGSearchResult], query: String) -> [RAGSearchResult] {
        let prediction = predictor.predictContextNeeds(
            currentWorkspace: .chat,
            recentQuery: query,
            activeFileId: nil
        )

        return results.map { result in
            var boost: Float = 0

            // Boost if topic matches predicted topics
            for topic in prediction.likelyTopics {
                if result.document.content.lowercased().contains(topic.lowercased()) {
                    boost += 0.05
                }
            }

            if boost > 0 {
                return RAGSearchResult(
                    document: result.document,
                    similarity: min(1.0, result.similarity + boost),
                    rank: result.rank,
                    matchedTerms: result.matchedTerms,
                    snippet: result.snippet
                )
            }

            return result
        }
    }

    /// Extract keywords from query
    private func extractKeywords(from query: String) -> [String] {
        let stopWords: Set<String> = ["the", "a", "an", "is", "are", "was", "were", "be", "been",
                                       "being", "have", "has", "had", "do", "does", "did", "will",
                                       "would", "could", "should", "may", "might", "must", "can",
                                       "this", "that", "these", "those", "i", "you", "he", "she",
                                       "it", "we", "they", "what", "which", "who", "when", "where",
                                       "why", "how", "all", "each", "every", "both", "few", "more",
                                       "some", "any", "no", "not", "only", "same", "so", "than",
                                       "too", "very", "just", "also", "now", "here", "there", "then"]

        return query
            .lowercased()
            .components(separatedBy: .whitespacesAndNewlines)
            .map { $0.trimmingCharacters(in: .punctuationCharacters) }
            .filter { $0.count > 2 && !stopWords.contains($0) }
    }

    /// Count keyword matches in content
    private func countKeywordMatches(keywords: [String], in content: String) -> Int {
        let lowercaseContent = content.lowercased()
        return keywords.reduce(0) { count, keyword in
            count + (lowercaseContent.contains(keyword) ? 1 : 0)
        }
    }

    /// Update search statistics
    private func updateStats(duration: TimeInterval) {
        searchCount += 1
        averageSearchTime = (averageSearchTime * Double(searchCount - 1) + duration) / Double(searchCount)
        lastSearchAt = Date()
    }

    // MARK: - Statistics

    /// Get search service statistics
    func getStatistics() async -> SearchStatistics {
        let indexStats = await vectorStore.getStatistics()

        return SearchStatistics(
            totalDocuments: indexStats.totalDocuments,
            documentsBySource: indexStats.documentsBySource,
            searchCount: searchCount,
            averageSearchTime: averageSearchTime,
            lastSearchAt: lastSearchAt,
            isIndexing: isIndexing
        )
    }
}

// MARK: - Search Statistics

struct SearchStatistics {
    let totalDocuments: Int
    let documentsBySource: [String: Int]
    let searchCount: Int
    let averageSearchTime: TimeInterval
    let lastSearchAt: Date?
    let isIndexing: Bool

    var formattedAverageTime: String {
        String(format: "%.1fms", averageSearchTime * 1000)
    }
}
