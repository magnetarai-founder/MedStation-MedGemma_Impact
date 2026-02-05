import Foundation

// MARK: - API Chat Session (DTO for network responses)

struct ApiChatSession: Codable, Identifiable, Sendable {
    let id: String
    let title: String?
    let model: String?
    let createdAt: String
    let updatedAt: String
    let messageCount: Int?

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case model
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case messageCount = "message_count"
    }
}

// MARK: - API Chat Message (for network responses)

struct ApiChatMessage: Codable, Identifiable, Sendable {
    let id: String
    let role: String  // "user" | "assistant"
    let content: String
    let timestamp: String
    let model: String?
    let tokens: Int?
    let files: [ChatFile]?

    // Convenience initializer for local messages
    init(
        id: String = UUID().uuidString,
        role: String,
        content: String,
        timestamp: String,
        model: String? = nil,
        tokens: Int? = nil,
        files: [ChatFile]? = nil
    ) {
        self.id = id
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.model = model
        self.tokens = tokens
        self.files = files
    }
}

// MARK: - Chat File

struct ChatFile: Codable, Identifiable, Sendable {
    let id: String
    let originalName: String
    let size: Int
    let type: String

    enum CodingKeys: String, CodingKey {
        case id
        case originalName = "original_name"
        case size
        case type
    }
}

// MARK: - Send Message Request

struct SendMessageRequest: Codable, Sendable {
    let content: String
    let model: String?
    let temperature: Double?
    let topP: Double?
    let topK: Int?
    let repeatPenalty: Double?
    let systemPrompt: String?

    enum CodingKeys: String, CodingKey {
        case content
        case model
        case temperature
        case topP = "top_p"
        case topK = "top_k"
        case repeatPenalty = "repeat_penalty"
        case systemPrompt = "system_prompt"
    }
}

// MARK: - Token Response

struct TokenResponse: Codable, Sendable {
    let tokensUsed: Int
    let tokensLimit: Int?

    enum CodingKeys: String, CodingKey {
        case tokensUsed = "tokens_used"
        case tokensLimit = "tokens_limit"
    }
}
