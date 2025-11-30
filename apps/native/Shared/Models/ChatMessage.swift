//
//  ChatMessage.swift
//  MagnetarStudio
//
//  Chat message model for AI conversations.
//

import Foundation
import SwiftData

@Model
final class ChatMessage {
    @Attribute(.unique) var id: UUID
    var role: MessageRole
    var content: String
    var createdAt: Date
    var sessionId: UUID
    var modelId: String?  // Track which model generated this response

    init(
        id: UUID = UUID(),
        role: MessageRole,
        content: String,
        sessionId: UUID,
        createdAt: Date = Date(),
        modelId: String? = nil
    ) {
        self.id = id
        self.role = role
        self.content = content
        self.sessionId = sessionId
        self.createdAt = createdAt
        self.modelId = modelId
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

@Model
final class ChatSession {
    @Attribute(.unique) var id: UUID
    var title: String
    var model: String
    var createdAt: Date
    var updatedAt: Date

    @Relationship(deleteRule: .cascade)
    var messages: [ChatMessage] = []

    init(
        id: UUID = UUID(),
        title: String = "New Chat",
        model: String = "mistral",
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
    let model: String
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
