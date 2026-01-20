import Foundation

/// Service layer for Chat workspace endpoints
final class ChatService {
    static let shared = ChatService()
    private let apiClient = ApiClient.shared

    private init() {}

    // MARK: - Session Management

    func listSessions() async throws -> [ApiChatSession] {
        // Backend returns SuccessResponse<List<ApiChatSession>>
        // The convenience method auto-unwraps the envelope
        let sessions: [ApiChatSession] = try await apiClient.request(
            path: "/v1/chat/sessions",
            method: .get
        )
        return sessions
    }

    func createSession(title: String? = nil, model: String? = nil) async throws -> ApiChatSession {
        // Build JSON body - always send a valid dictionary (empty dict if no params)
        var jsonBody: [String: Any] = [:]
        if let title = title {
            jsonBody["title"] = title
        }
        if let model = model {
            jsonBody["model"] = model
        }

        // Backend returns SuccessResponse<ApiChatSession>
        // The convenience method auto-unwraps the envelope
        let session: ApiChatSession = try await apiClient.request(
            path: "/v1/chat/sessions",
            method: .post,
            jsonBody: jsonBody
        )
        return session
    }

    func deleteSession(sessionId: String) async throws {
        _ = try await apiClient.request(
            path: "/v1/chat/sessions/\(sessionId)",
            method: .delete
        ) as EmptyResponse
    }

    func renameSession(sessionId: String, title: String) async throws {
        _ = try await apiClient.request(
            path: "/v1/chat/sessions/\(sessionId)",
            method: .patch,
            jsonBody: ["title": title]
        ) as EmptyResponse
    }

    // MARK: - File Upload

    func uploadAttachment(sessionId: String, fileURL: URL) async throws -> ChatFile {
        try await apiClient.multipart(
            path: "/v1/chat/sessions/\(sessionId)/upload",
            fileField: "file",
            fileURL: fileURL
        )
    }

    // MARK: - Model Management

    func changeModel(sessionId: String, model: String) async throws {
        _ = try await apiClient.request(
            path: "/v1/chat/sessions/\(sessionId)/model",
            method: .patch,
            jsonBody: ["model": model]
        ) as EmptyResponse
    }

    // MARK: - Token Tracking

    func fetchTokens(sessionId: String) async throws -> TokenResponse {
        try await apiClient.request(
            path: "/v1/chat/sessions/\(sessionId)/tokens",
            method: .get
        )
    }

    // MARK: - Streaming Messages

    func sendMessageStream(
        sessionId: String,
        request: SendMessageRequest,
        onContent: @escaping (String) -> Void,
        onDone: @escaping () -> Void,
        onError: @escaping (Error) -> Void
    ) throws -> ApiClient.StreamingTask {
        try apiClient.makeStreamingTask(
            path: "/v1/chat/sessions/\(sessionId)/messages",
            method: .post,
            jsonBody: request,
            onContent: onContent,
            onDone: onDone,
            onError: onError
        )
    }

    // MARK: - Message Loading

    /// Result of paginated message loading
    struct PaginatedMessages {
        let messages: [ApiChatMessage]
        let totalCount: Int
        let offset: Int
        let hasMore: Bool
    }

    /// Load messages with pagination support
    /// - Parameters:
    ///   - sessionId: Chat session ID
    ///   - limit: Maximum messages to return (nil for all)
    ///   - offset: Number of messages to skip (for loading older messages)
    /// - Returns: Paginated messages with metadata
    func loadMessages(
        sessionId: String,
        limit: Int? = nil,
        offset: Int = 0
    ) async throws -> PaginatedMessages {
        var queryParams: [String] = []
        if let limit = limit {
            queryParams.append("limit=\(limit)")
        }
        if offset > 0 {
            queryParams.append("offset=\(offset)")
        }

        var path = "/v1/chat/sessions/\(sessionId)/messages"
        if !queryParams.isEmpty {
            path += "?" + queryParams.joined(separator: "&")
        }

        struct MessagesResponse: Codable {
            let messages: [ApiChatMessage]
            let total: Int?
            let totalCount: Int?
            let offset: Int?
            let hasMore: Bool?

            enum CodingKeys: String, CodingKey {
                case messages
                case total
                case totalCount = "total_count"
                case offset
                case hasMore = "has_more"
            }
        }

        let response: MessagesResponse = try await apiClient.request(
            path: path,
            method: .get
        )

        return PaginatedMessages(
            messages: response.messages,
            totalCount: response.totalCount ?? response.total ?? response.messages.count,
            offset: response.offset ?? offset,
            hasMore: response.hasMore ?? false
        )
    }

    /// Load messages (convenience method returning just messages array)
    func loadMessages(sessionId: String, limit: Int? = nil) async throws -> [ApiChatMessage] {
        let result = try await loadMessages(sessionId: sessionId, limit: limit, offset: 0)
        return result.messages
    }

    // MARK: - Health Check

    func checkHealth() async throws -> Bool {
        struct HealthResponse: Codable {
            let status: String
        }

        let response: HealthResponse = try await apiClient.request(
            path: "/v1/chat/health",
            method: .get
        )

        return response.status == "ok"
    }
}
