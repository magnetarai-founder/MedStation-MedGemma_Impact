//
//  RAGIntegrationBridge.swift
//  MagnetarStudio
//
//  Bridges local Swift RAG with backend FAISS service.
//  Provides unified search across local and server-side indices.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "RAGIntegrationBridge")

// MARK: - RAG Integration Bridge

/// Unified interface for RAG across local and backend systems
@MainActor
final class RAGIntegrationBridge: ObservableObject {

    // MARK: - Published State

    @Published private(set) var isBackendAvailable: Bool = false
    @Published private(set) var lastSearchDuration: TimeInterval = 0
    @Published private(set) var totalDocumentsIndexed: Int = 0

    // MARK: - Dependencies

    private let localSearch: SemanticSearchService
    private let apiClient: ApiClient

    // MARK: - Configuration

    var preferBackend: Bool = true  // Prefer backend FAISS when available
    var localFallback: Bool = true  // Fall back to local if backend fails
    var hybridSearch: Bool = true   // Combine local and backend results

    // MARK: - Singleton

    static let shared = RAGIntegrationBridge()

    // MARK: - Initialization

    init(
        localSearch: SemanticSearchService? = nil,
        apiClient: ApiClient? = nil
    ) {
        self.localSearch = localSearch ?? .shared
        self.apiClient = apiClient ?? .shared

        Task {
            await checkBackendHealth()
        }
    }

    // MARK: - Health Check

    /// Check if backend FAISS service is available
    func checkBackendHealth() async {
        do {
            struct HealthResponse: Codable {
                let status: String
                let indexLoaded: Bool
                let totalDocuments: Int

                enum CodingKeys: String, CodingKey {
                    case status
                    case indexLoaded = "index_loaded"
                    case totalDocuments = "total_documents"
                }
            }

            let response: HealthResponse = try await apiClient.request(
                "/api/v1/faiss/health",
                method: .get
            )

            isBackendAvailable = response.status == "healthy" && response.indexLoaded
            totalDocumentsIndexed = response.totalDocuments

            logger.info("[RAGBridge] Backend health: \(response.status), documents: \(response.totalDocuments)")

        } catch {
            isBackendAvailable = false
            logger.warning("[RAGBridge] Backend unavailable: \(error)")
        }
    }

    // MARK: - Unified Search

    /// Search across all available RAG sources
    func search(_ query: UnifiedRAGQuery) async -> UnifiedRAGResults {
        let startTime = Date()

        var localResults: [RAGSearchResult] = []
        var backendResults: [BackendSearchResult] = []
        var errors: [RAGSearchError] = []

        // Parallel search if hybrid mode
        if hybridSearch {
            async let localTask = searchLocal(query)
            async let backendTask = searchBackend(query)

            let (local, backend) = await (localTask, backendTask)
            localResults = local.results
            backendResults = backend.results
            errors.append(contentsOf: local.errors)
            errors.append(contentsOf: backend.errors)

        } else if preferBackend && isBackendAvailable {
            // Backend only
            let backend = await searchBackend(query)
            backendResults = backend.results
            errors.append(contentsOf: backend.errors)

            // Fallback to local if backend failed
            if backendResults.isEmpty && localFallback {
                let local = await searchLocal(query)
                localResults = local.results
                errors.append(contentsOf: local.errors)
            }

        } else {
            // Local only
            let local = await searchLocal(query)
            localResults = local.results
            errors.append(contentsOf: local.errors)
        }

        // Merge and deduplicate results
        let merged = mergeResults(local: localResults, backend: backendResults, limit: query.limit)

        lastSearchDuration = Date().timeIntervalSince(startTime)

        logger.debug("[RAGBridge] Search complete: \(merged.count) results in \(String(format: "%.3f", self.lastSearchDuration))s")

        return UnifiedRAGResults(
            results: merged,
            localCount: localResults.count,
            backendCount: backendResults.count,
            searchDuration: lastSearchDuration,
            usedBackend: !backendResults.isEmpty,
            usedLocal: !localResults.isEmpty,
            errors: errors
        )
    }

    /// Quick semantic search (best-effort, low latency)
    func quickSearch(_ query: String, limit: Int = 5) async -> [UnifiedSearchResult] {
        // Try backend first for fastest results
        if isBackendAvailable && preferBackend {
            let backendResults = await searchBackend(UnifiedRAGQuery(
                query: query,
                limit: limit,
                sources: nil
            ))

            if !backendResults.results.isEmpty {
                return backendResults.results.map { UnifiedSearchResult(from: $0) }
            }
        }

        // Fall back to local
        let localResults = await searchLocal(UnifiedRAGQuery(
            query: query,
            limit: limit,
            sources: nil
        ))

        return localResults.results.map { UnifiedSearchResult(from: $0) }
    }

    // MARK: - Local Search

    private func searchLocal(_ query: UnifiedRAGQuery) async -> (results: [RAGSearchResult], errors: [RAGSearchError]) {
        do {
            let results = try await localSearch.search(
                query: query.query,
                sources: query.sources?.compactMap { RAGSource(rawValue: $0) },
                conversationId: query.conversationId,
                limit: query.limit,
                minSimilarity: query.minSimilarity ?? 0.3
            )
            return (results, [])

        } catch {
            logger.warning("[RAGBridge] Local search failed: \(error)")
            return ([], [RAGSearchError(source: .local, message: error.localizedDescription)])
        }
    }

    // MARK: - Backend Search

    private func searchBackend(_ query: UnifiedRAGQuery) async -> (results: [BackendSearchResult], errors: [RAGSearchError]) {
        guard isBackendAvailable else {
            return ([], [])
        }

        do {
            struct SearchRequest: Codable {
                let query: String
                let limit: Int
                let minSimilarity: Float?
                let sources: [String]?
                let conversationId: String?

                enum CodingKeys: String, CodingKey {
                    case query, limit, sources
                    case minSimilarity = "min_similarity"
                    case conversationId = "conversation_id"
                }
            }

            struct SearchResponse: Codable {
                let results: [BackendSearchResult]
                let totalMatches: Int
                let searchDuration: Double

                enum CodingKeys: String, CodingKey {
                    case results
                    case totalMatches = "total_matches"
                    case searchDuration = "search_duration"
                }
            }

            let request = SearchRequest(
                query: query.query,
                limit: query.limit,
                minSimilarity: query.minSimilarity,
                sources: query.sources,
                conversationId: query.conversationId?.uuidString
            )

            let response: SearchResponse = try await apiClient.request(
                "/api/v1/faiss/search",
                method: .post,
                body: request
            )

            return (response.results, [])

        } catch {
            logger.warning("[RAGBridge] Backend search failed: \(error)")
            return ([], [RAGSearchError(source: .backend, message: error.localizedDescription)])
        }
    }

    // MARK: - Result Merging

    /// Merge and deduplicate results from multiple sources
    private func mergeResults(
        local: [RAGSearchResult],
        backend: [BackendSearchResult],
        limit: Int
    ) -> [UnifiedSearchResult] {
        var merged: [UnifiedSearchResult] = []
        var seenContent: Set<String> = []

        // Convert and deduplicate backend results (higher priority)
        for result in backend {
            let contentHash = hashContent(result.content)
            if !seenContent.contains(contentHash) {
                seenContent.insert(contentHash)
                merged.append(UnifiedSearchResult(from: result))
            }
        }

        // Add local results that aren't duplicates
        for result in local {
            let contentHash = hashContent(result.document.content)
            if !seenContent.contains(contentHash) {
                seenContent.insert(contentHash)
                merged.append(UnifiedSearchResult(from: result))
            }
        }

        // Sort by similarity and limit
        merged.sort { $0.similarity > $1.similarity }
        return Array(merged.prefix(limit))
    }

    /// Simple content hash for deduplication
    private func hashContent(_ content: String) -> String {
        // Use first 200 chars normalized
        let normalized = String(content.prefix(200))
            .lowercased()
            .trimmingCharacters(in: .whitespacesAndNewlines)
        return normalized
    }

    // MARK: - Indexing

    /// Index content to both local and backend (if available)
    func indexContent(_ content: IndexableContent) async -> IndexingResult {
        var localSuccess = false
        var backendSuccess = false
        var errors: [RAGSearchError] = []

        // Index locally
        do {
            switch content.type {
            case .message:
                if let message = content.chatMessage, let convId = content.conversationId {
                    try await localSearch.indexMessage(message, conversationId: convId)
                    localSuccess = true
                }

            case .theme:
                if let theme = content.theme, let convId = content.conversationId {
                    try await localSearch.indexTheme(theme, conversationId: convId)
                    localSuccess = true
                }

            case .file:
                if let file = content.file {
                    let _ = try await localSearch.indexFile(
                        content: file.processedContent ?? file.filename,
                        filename: file.filename,
                        fileId: file.id,
                        conversationId: content.conversationId,
                        isVaultProtected: false
                    )
                    localSuccess = true
                }

            case .generic:
                // Index as generic document using index request
                let request = RAGIndexRequest(
                    content: content.content,
                    source: .chatMessage,
                    metadata: RAGDocumentMetadata(conversationId: content.conversationId),
                    chunkIfNeeded: false
                )
                let _ = try await localSearch.index(request: request)
                localSuccess = true
            }
        } catch {
            errors.append(RAGSearchError(source: .local, message: error.localizedDescription))
        }

        // Index to backend if available
        if isBackendAvailable {
            do {
                struct IndexRequest: Codable {
                    let content: String
                    let source: String
                    let metadata: [String: String]?
                    let conversationId: String?

                    enum CodingKeys: String, CodingKey {
                        case content, source, metadata
                        case conversationId = "conversation_id"
                    }
                }

                struct IndexResponse: Codable {
                    let documentIds: [String]

                    enum CodingKeys: String, CodingKey {
                        case documentIds = "document_ids"
                    }
                }

                let request = IndexRequest(
                    content: content.content,
                    source: content.type.rawValue,
                    metadata: content.metadata,
                    conversationId: content.conversationId?.uuidString
                )

                let _: IndexResponse = try await apiClient.request(
                    "/api/v1/faiss/index",
                    method: .post,
                    body: request
                )

                backendSuccess = true

            } catch {
                errors.append(RAGSearchError(source: .backend, message: error.localizedDescription))
            }
        }

        return IndexingResult(
            localIndexed: localSuccess,
            backendIndexed: backendSuccess,
            errors: errors
        )
    }

    /// Batch index multiple items
    func batchIndex(_ items: [IndexableContent]) async -> BatchIndexingResult {
        var results: [IndexingResult] = []

        for item in items {
            let result = await indexContent(item)
            results.append(result)
        }

        return BatchIndexingResult(
            totalItems: items.count,
            localSuccessCount: results.filter { $0.localIndexed }.count,
            backendSuccessCount: results.filter { $0.backendIndexed }.count,
            errors: results.flatMap { $0.errors }
        )
    }
}

// MARK: - Supporting Types

/// Unified query for RAG search
struct UnifiedRAGQuery {
    let query: String
    let limit: Int
    let minSimilarity: Float?
    let sources: [String]?
    let conversationId: UUID?
    let includeMetadata: Bool

    init(
        query: String,
        limit: Int = 10,
        minSimilarity: Float? = nil,
        sources: [String]? = nil,
        conversationId: UUID? = nil,
        includeMetadata: Bool = true
    ) {
        self.query = query
        self.limit = limit
        self.minSimilarity = minSimilarity
        self.sources = sources
        self.conversationId = conversationId
        self.includeMetadata = includeMetadata
    }
}

/// Unified search results
struct UnifiedRAGResults {
    let results: [UnifiedSearchResult]
    let localCount: Int
    let backendCount: Int
    let searchDuration: TimeInterval
    let usedBackend: Bool
    let usedLocal: Bool
    let errors: [RAGSearchError]

    var isEmpty: Bool { results.isEmpty }
    var hasErrors: Bool { !errors.isEmpty }
}

/// Unified search result from any source
struct UnifiedSearchResult: Identifiable {
    let id: String
    let content: String
    let snippet: String?
    let similarity: Float
    let source: String
    let sourceType: UnifiedSourceType
    let metadata: [String: String]?
    let conversationId: UUID?

    init(from local: RAGSearchResult) {
        self.id = local.document.id.uuidString
        self.content = local.document.content
        self.snippet = local.snippet
        self.similarity = local.similarity
        self.source = "local"
        self.sourceType = .local
        self.metadata = nil
        self.conversationId = local.document.metadata.conversationId
    }

    init(from backend: BackendSearchResult) {
        self.id = backend.documentId
        self.content = backend.content
        self.snippet = backend.snippet
        self.similarity = backend.similarity
        self.source = "backend"
        self.sourceType = .backend
        self.metadata = backend.metadata
        self.conversationId = backend.conversationId.flatMap { UUID(uuidString: $0) }
    }
}

/// Source type for search results
enum UnifiedSourceType: String {
    case local
    case backend
}

/// Backend search result model
struct BackendSearchResult: Codable {
    let documentId: String
    let content: String
    let snippet: String?
    let similarity: Float
    let source: String
    let metadata: [String: String]?
    let conversationId: String?

    enum CodingKeys: String, CodingKey {
        case documentId = "document_id"
        case content, snippet, similarity, source, metadata
        case conversationId = "conversation_id"
    }
}

/// Content to be indexed
struct IndexableContent {
    let content: String
    let type: IndexableContentType
    let conversationId: UUID?
    let metadata: [String: String]?

    // Type-specific content
    var chatMessage: ChatMessage?
    var theme: ConversationTheme?
    var file: FileReference?

    enum IndexableContentType: String {
        case message
        case theme
        case file
        case generic
    }

    static func message(_ msg: ChatMessage, conversationId: UUID) -> IndexableContent {
        var content = IndexableContent(
            content: msg.content,
            type: .message,
            conversationId: conversationId,
            metadata: ["role": msg.role.rawValue]
        )
        content.chatMessage = msg
        return content
    }

    static func theme(_ theme: ConversationTheme) -> IndexableContent {
        var content = IndexableContent(
            content: theme.content,
            type: .theme,
            conversationId: nil,
            metadata: ["topic": theme.topic]
        )
        content.theme = theme
        return content
    }

    static func file(_ file: FileReference, conversationId: UUID?) -> IndexableContent {
        var content = IndexableContent(
            content: file.processedContent ?? file.filename,
            type: .file,
            conversationId: conversationId,
            metadata: ["filename": file.filename, "fileType": file.fileType]
        )
        content.file = file
        return content
    }
}

/// Result of indexing operation
struct IndexingResult {
    let localIndexed: Bool
    let backendIndexed: Bool
    let errors: [RAGSearchError]

    var success: Bool { localIndexed || backendIndexed }
}

/// Result of batch indexing
struct BatchIndexingResult {
    let totalItems: Int
    let localSuccessCount: Int
    let backendSuccessCount: Int
    let errors: [RAGSearchError]

    var localSuccessRate: Float {
        Float(localSuccessCount) / Float(max(1, totalItems))
    }

    var backendSuccessRate: Float {
        Float(backendSuccessCount) / Float(max(1, totalItems))
    }
}

/// Error during RAG operation
struct RAGSearchError: Identifiable {
    let id = UUID()
    let source: UnifiedSourceType
    let message: String
}
