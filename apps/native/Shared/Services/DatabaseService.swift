import Foundation

/// Service layer for Database workspace endpoints
final class DatabaseService {
    static let shared = DatabaseService()
    private let apiClient = ApiClient.shared

    private init() {}

    // MARK: - Session Management

    func createSession() async throws -> SessionResponse {
        // SQL/JSON sessions are just UUIDs - no backend endpoint needed
        // The session ID is used in subsequent requests like /{session_id}/upload
        let sessionId = UUID().uuidString
        let createdAt = ISO8601DateFormatter().string(from: Date())
        return SessionResponse(sessionId: sessionId, createdAt: createdAt)
    }

    func deleteSession(id: String) async {
        _ = try? await apiClient.request(
            path: "/api/v1/sql-json/sessions/\(id)",
            method: .delete,
            jsonBody: nil
        ) as EmptyResponse
    }

    // MARK: - File Uploads

    func uploadFile(sessionId: String, fileURL: URL) async throws -> FileUploadResponse {
        try await apiClient.multipart(
            path: "/api/v1/sql-json/\(sessionId)/upload",
            fileField: "file",
            fileURL: fileURL
        )
    }

    func uploadJson(sessionId: String, fileURL: URL) async throws -> JsonUploadResponse {
        try await apiClient.multipart(
            path: "/api/v1/sql-json/\(sessionId)/json/upload",
            fileField: "file",
            fileURL: fileURL
        )
    }

    // MARK: - Query Execution

    func executeQuery(
        sessionId: String,
        sql: String,
        limit: Int? = nil,
        isPreview: Bool = false
    ) async throws -> QueryResponse {
        var payload: [String: Any] = ["sql": sql]
        if let limit = limit {
            payload["limit"] = limit
        }
        if isPreview {
            payload["is_preview"] = true
        }

        var response: QueryResponse = try await apiClient.request(
            path: "/api/v1/sql-json/\(sessionId)/query",
            method: .post,
            jsonBody: payload
        )

        // Mark as preview-only if requested
        if isPreview {
            response.isPreviewOnly = true
        }

        return response
    }

    func convertJson(
        sessionId: String,
        json: String,
        options: [String: Any] = [:]
    ) async throws -> JsonConvertResponse {
        try await apiClient.request(
            path: "/api/v1/sql-json/\(sessionId)/json/convert",
            method: .post,
            jsonBody: ["json_data": json, "options": options]
        )
    }

    // MARK: - Export & Download

    func exportResults(
        sessionId: String,
        queryId: String,
        format: String,
        filename: String? = nil
    ) async throws -> Data {
        var payload: [String: Any] = [
            "query_id": queryId,
            "format": format
        ]
        if let filename = filename {
            payload["filename"] = filename
        }

        return try await apiClient.requestRaw(
            path: "/api/v1/sql-json/\(sessionId)/export",
            method: .post,
            jsonBody: payload
        )
    }

    func downloadJsonResult(sessionId: String, format: String) async throws -> Data {
        try await apiClient.requestRaw(
            path: "/api/v1/sql-json/\(sessionId)/json/download?format=\(format)",
            method: .get
        )
    }

    // MARK: - Query History

    func fetchQueryHistory(sessionId: String) async throws -> [QueryHistoryItem] {
        let response: QueryHistoryResponse = try await apiClient.request(
            path: "/api/v1/sql-json/\(sessionId)/query-history",
            method: .get
        )
        return response.history
    }

    func deleteHistoryItem(sessionId: String, historyId: String) async throws {
        _ = try await apiClient.request(
            path: "/api/v1/sql-json/\(sessionId)/query-history/\(historyId)",
            method: .delete,
            jsonBody: nil
        ) as EmptyResponse
    }
}
