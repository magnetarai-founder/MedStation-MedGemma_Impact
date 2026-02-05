//
//  ContextService.swift
//  MagnetarStudio
//
//  Phase 5: ANE Context Engine Integration
//  Semantic search and RAG document retrieval for intelligent routing
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "ContextService")

// MARK: - Request/Response Models

struct ContextSearchRequest: Codable, Sendable {
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

struct ContextSearchResult: Codable, Sendable {
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

struct ContextSearchResponse: Codable, Sendable {
    let results: [ContextSearchResult]
    let totalFound: Int
    let queryEmbeddingDims: Int

    enum CodingKeys: String, CodingKey {
        case results
        case totalFound = "total_found"
        case queryEmbeddingDims = "query_embedding_dims"
    }
}

struct StoreContextRequest: Codable, Sendable {
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

struct ContextStatusResponse: Codable, Sendable {
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

struct ContextFeatures: Codable, Sendable {
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
                // Convert source string to RAGSource
                let ragSource: RAGSource
                switch result.source.lowercased() {
                case "vault": ragSource = .vaultFile
                case "chat": ragSource = .chatMessage
                case "data": ragSource = .datasetColumn
                case "code": ragSource = .codeFile
                case "workflow": ragSource = .workflow
                case "kanban": ragSource = .kanbanTask
                case "team": ragSource = .teamMessage
                default: ragSource = .document
                }

                // Build metadata from result
                var metadata = RAGDocumentMetadata()
                if let sessionIdStr = result.metadata["session_id"]?.value as? String,
                   let sessionId = UUID(uuidString: sessionIdStr) {
                    metadata.sessionId = sessionId
                }

                return RAGDocument(
                    content: result.content,
                    embedding: [],  // No embedding from search results
                    source: ragSource,
                    metadata: metadata
                )
            }
        } catch {
            logger.error("Failed to get RAG documents: \(error)")
            return []
        }
    }

    /// Search vault for relevant files based on query
    /// Uses semantic search to find contextually relevant vault content
    func searchVaultFiles(
        for query: String,
        limit: Int = 5
    ) async -> [VaultSearchResult] {
        do {
            let response = try await searchContext(
                query: query,
                workspaceTypes: ["vault"],
                limit: limit
            )

            return response.results.compactMap { result -> VaultSearchResult? in
                guard result.source == "vault" else { return nil }

                return VaultSearchResult(
                    fileId: result.metadata["file_id"]?.value as? String ?? UUID().uuidString,
                    fileName: result.metadata["file_name"]?.value as? String ?? "Unknown",
                    filePath: result.metadata["file_path"]?.value as? String,
                    snippet: result.content,
                    relevanceScore: result.relevanceScore
                )
            }
        } catch {
            logger.error("Failed to search vault files: \(error)")
            return []
        }
    }

    /// Search data queries for relevant context
    func searchDataQueries(
        for query: String,
        limit: Int = 5
    ) async -> [DataQuerySearchResult] {
        do {
            let response = try await searchContext(
                query: query,
                workspaceTypes: ["data"],
                limit: limit
            )

            return response.results.compactMap { result -> DataQuerySearchResult? in
                guard result.source == "data" else { return nil }

                return DataQuerySearchResult(
                    queryId: result.metadata["query_id"]?.value as? String ?? UUID().uuidString,
                    queryText: result.content,
                    tableName: result.metadata["table_name"]?.value as? String,
                    relevanceScore: result.relevanceScore
                )
            }
        } catch {
            logger.error("Failed to search data queries: \(error)")
            return []
        }
    }

    /// Search code context for relevant files and snippets
    /// Uses semantic search to find contextually relevant code
    func searchCodeFiles(
        for query: String,
        limit: Int = 5
    ) async -> [CodeSearchResult] {
        do {
            let response = try await searchContext(
                query: query,
                workspaceTypes: ["code"],
                limit: limit
            )

            return response.results.compactMap { result -> CodeSearchResult? in
                guard result.source == "code" else { return nil }

                return CodeSearchResult(
                    fileId: result.metadata["file_id"]?.value as? String ?? UUID().uuidString,
                    fileName: result.metadata["file_name"]?.value as? String ?? "Unknown",
                    filePath: result.metadata["file_path"]?.value as? String,
                    language: result.metadata["language"]?.value as? String,
                    snippet: result.content,
                    lineNumber: result.metadata["line_number"]?.value as? Int,
                    relevanceScore: result.relevanceScore
                )
            }
        } catch {
            logger.error("Failed to search code files: \(error)")
            return []
        }
    }
}

// MARK: - Search Result Types

struct VaultSearchResult {
    let fileId: String
    let fileName: String
    let filePath: String?
    let snippet: String
    let relevanceScore: Float
}

struct DataQuerySearchResult {
    let queryId: String
    let queryText: String
    let tableName: String?
    let relevanceScore: Float
}

struct CodeSearchResult {
    let fileId: String
    let fileName: String
    let filePath: String?
    let language: String?
    let snippet: String
    let lineNumber: Int?
    let relevanceScore: Float
}
