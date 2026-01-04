//
//  ChatMessage.swift
//  MagnetarStudio
//
//  Chat message model for AI conversations.
//

import Foundation

/// Chat message model - in-memory only (no SwiftData persistence)
final class ChatMessage: Identifiable {
    let id: UUID
    var role: MessageRole
    var content: String
    var createdAt: Date
    var sessionId: UUID
    var modelId: String?  // Track which model generated this response
    var isIncomplete: Bool  // True if streaming was interrupted before completion

    init(
        id: UUID = UUID(),
        role: MessageRole,
        content: String,
        sessionId: UUID,
        createdAt: Date = Date(),
        modelId: String? = nil,
        isIncomplete: Bool = false
    ) {
        self.id = id
        self.role = role
        self.content = content
        self.sessionId = sessionId
        self.createdAt = createdAt
        self.modelId = modelId
        self.isIncomplete = isIncomplete
    }
}

// MARK: - Message Role

enum MessageRole: String, Codable {
    case user
    case assistant
    case system

    var displayName: String {
        switch self {
        case .user: return "You"
        case .assistant: return "AI"
        case .system: return "System"
        }
    }
}

// MARK: - Chat Session

/// Chat session model - in-memory only (no SwiftData persistence)
/// Messages are managed separately in ChatStore.messages, not via this relationship
final class ChatSession: Identifiable {
    let id: UUID
    var title: String
    var model: String?  // Sessions are model-agnostic; orchestrator chooses model per query
    var createdAt: Date
    var updatedAt: Date

    // Note: Messages are loaded separately into ChatStore.messages
    // This property exists for potential future use but is not actively populated
    var messages: [ChatMessage] = []

    init(
        id: UUID = UUID(),
        title: String = "New Chat",
        model: String? = nil,  // No default model; use orchestrator or manual selection
        createdAt: Date = Date(),
        updatedAt: Date = Date()
    ) {
        self.id = id
        self.title = title
        self.model = model
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }
}

// MARK: - API DTOs (Data Transfer Objects)

/// Codable representation of ChatMessage for API
struct ChatMessageDTO: Codable {
    let id: UUID
    let role: MessageRole
    let content: String
    let createdAt: Date
    let sessionId: UUID

    enum CodingKeys: String, CodingKey {
        case id, role, content
        case createdAt = "created_at"
        case sessionId = "session_id"
    }

    func toModel() -> ChatMessage {
        return ChatMessage(
            id: id,
            role: role,
            content: content,
            sessionId: sessionId,
            createdAt: createdAt
        )
    }
}

/// Codable representation of ChatSession for API
struct ChatSessionDTO: Codable {
    let id: UUID
    let title: String
    let model: String?  // Optional - sessions don't require a fixed model
    let createdAt: Date
    let updatedAt: Date

    enum CodingKeys: String, CodingKey {
        case id, title, model
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }

    func toModel() -> ChatSession {
        return ChatSession(
            id: id,
            title: title,
            model: model,
            createdAt: createdAt,
            updatedAt: updatedAt
        )
    }
}

extension ChatMessage {
    func toDTO() -> ChatMessageDTO {
        return ChatMessageDTO(
            id: id,
            role: role,
            content: content,
            createdAt: createdAt,
            sessionId: sessionId
        )
    }
}

extension ChatSession {
    func toDTO() -> ChatSessionDTO {
        return ChatSessionDTO(
            id: id,
            title: title,
            model: model,
            createdAt: createdAt,
            updatedAt: updatedAt
        )
    }
}
