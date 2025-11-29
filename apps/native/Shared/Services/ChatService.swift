import Foundation

/// Service layer for Chat workspace endpoints
final class ChatService {
    static let shared = ChatService()
    private let apiClient = ApiClient.shared

    private init() {}

    // MARK: - Session Management

    func listSessions() async throws -> [ApiChatSession] {
        try await apiClient.request(
            path: "/v1/chat/sessions",
            method: .get
        )
    }

    func createSession(title: String? = nil, model: String? = nil) async throws -> ApiChatSession {
        var payload: [String: Any] = [:]
        if let title = title {
            payload["title"] = title
        }
        if let model = model {
            payload["model"] = model
        }

        return try await apiClient.request(
            path: "/v1/chat/sessions",
            method: .post,
            jsonBody: payload.isEmpty ? nil : payload
        )
    }

    func deleteSession(sessionId: String) async throws {
        _ = try await apiClient.request(
            path: "/v1/chat/sessions/\(sessionId)",
            method: .delete
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

    func loadMessages(sessionId: String, limit: Int? = nil) async throws -> [ApiChatMessage] {
        var path = "/v1/chat/sessions/\(sessionId)/messages"
        if let limit = limit {
            path += "?limit=\(limit)"
        }

        struct MessagesResponse: Codable {
            let messages: [ApiChatMessage]
            let total: Int?
        }

        let response: MessagesResponse = try await apiClient.request(
            path: path,
            method: .get
        )

        return response.messages
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
