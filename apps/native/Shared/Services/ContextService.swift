//
//  ContextService.swift
//  MagnetarStudio
//
//  Phase 5: ANE Context Engine Integration
//  Semantic search and RAG document retrieval for intelligent routing
//

import Foundation

// MARK: - Request/Response Models

struct ContextSearchRequest: Codable {
    let query: String
    let sessionId: String?
    let workspaceTypes: [String]?
    let limit: Int

    enum CodingKeys: String, CodingKey {
        case query
        case sessionId = "session_id"
        case workspaceTypes = "workspace_types"
        case limit
    }
}

struct ContextSearchResult: Codable {
    let source: String  // "vault", "chat", "data", etc.
    let content: String
    let relevanceScore: Float
    let metadata: [String: AnyCodable]

    enum CodingKeys: String, CodingKey {
        case source
        case content
        case relevanceScore = "relevance_score"
        case metadata
    }
}

struct ContextSearchResponse: Codable {
    let results: [ContextSearchResult]
    let totalFound: Int
    let queryEmbeddingDims: Int

    enum CodingKeys: String, CodingKey {
        case results
        case totalFound = "total_found"
        case queryEmbeddingDims = "query_embedding_dims"
    }
}

struct StoreContextRequest: Codable {
    let sessionId: String
    let workspaceType: String
    let content: String
    let metadata: [String: AnyCodable]

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case workspaceType = "workspace_type"
        case content
        case metadata
    }
}

struct ContextStatusResponse: Codable {
    let available: Bool
    let backend: String
    let vectorCount: Int
    let queueDepth: Int
    let processedCount: Int
    let errorCount: Int
    let workers: Int
    let retentionDays: Float
    let features: ContextFeatures

    enum CodingKeys: String, CodingKey {
        case available
        case backend
        case vectorCount = "vector_count"
        case queueDepth = "queue_depth"
        case processedCount = "processed_count"
        case errorCount = "error_count"
        case workers
        case retentionDays = "retention_days"
        case features
    }
}

struct ContextFeatures: Codable {
    let semanticSearch: Bool
    let aneAcceleration: Bool
    let backgroundVectorization: Bool

    enum CodingKeys: String, CodingKey {
        case semanticSearch = "semantic_search"
        case aneAcceleration = "ane_acceleration"
        case backgroundVectorization = "background_vectorization"
    }
}

// MARK: - Context Service

@MainActor
class ContextService {
    static let shared = ContextService()

    private let apiClient: ApiClient
    private let baseURL = "http://localhost:8000/api/v1/context"

    private init(apiClient: ApiClient = .shared) {
        self.apiClient = apiClient
    }

    // MARK: - Search

    /// Search for relevant context across all workspaces
    func searchContext(
        query: String,
        sessionId: String? = nil,
        workspaceTypes: [String]? = nil,
        limit: Int = 10
    ) async throws -> ContextSearchResponse {
        let request = ContextSearchRequest(
            query: query,
            sessionId: sessionId,
            workspaceTypes: workspaceTypes,
            limit: limit
        )

        let response: ContextSearchResponse = try await apiClient.request(
            "/api/v1/context/search",
            method: .post,
            body: request
        )

        return response
    }

    // MARK: - Store

    /// Store context for future semantic search
    func storeContext(
        sessionId: String,
        workspaceType: String,
        content: String,
        metadata: [String: Any] = [:]
    ) async throws {
        let request = StoreContextRequest(
            sessionId: sessionId,
            workspaceType: workspaceType,
            content: content,
            metadata: metadata.mapValues { AnyCodable($0) }
        )

        struct EmptyResponse: Codable {}
        let _: EmptyResponse = try await apiClient.request(
            "/api/v1/context/store",
            method: .post,
            body: request
        )
    }

    // MARK: - Status

    /// Get ANE Context Engine status
    func getStatus() async throws -> ContextStatusResponse {
        let response: ContextStatusResponse = try await apiClient.request(
            "/api/v1/context/status",
            method: .get
        )

        return response
    }

    // MARK: - Convenience Methods

    /// Get RAG documents for a query (convenience wrapper)
    func getRAGDocuments(
        for query: String,
        limit: Int = 5
    ) async -> [RAGDocument] {
        do {
            let response = try await searchContext(
                query: query,
                limit: limit
            )

            return response.results.map { result in
                RAGDocument(
                    id: UUID().uuidString,
                    content: result.content,
                    source: result.source,
                    sourceId: result.metadata["session_id"]?.value as? String,
                    relevanceScore: result.relevanceScore,
                    metadata: result.metadata.mapValues { value in
                        if let str = value.value as? String {
                            return str
                        } else if let num = value.value as? CustomStringConvertible {
                            return String(describing: num)
                        }
                        return ""
                    }
                )
            }
        } catch {
            print("Failed to get RAG documents: \(error)")
            return []
        }
    }
}
