//
//  ChatMessage.swift
//  MedStation
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

enum MessageRole: String, Codable, Sendable {
    case user
    case assistant

    var displayName: String {
        switch self {
        case .user: return "You"
        case .assistant: return "AI"
        }
    }
}

// MARK: - Conversation State

/// State of a chat session for filtering (matches macOS 26 Messages app)
enum ConversationState: String, Codable, CaseIterable, Sendable {
    case active
    case archived
    case deleted

    var displayName: String {
        switch self {
        case .active: return "All Messages"
        case .archived: return "Archived"
        case .deleted: return "Recently Deleted"
        }
    }

    var icon: String {
        switch self {
        case .active: return "bubble.left.and.bubble.right"
        case .archived: return "archivebox"
        case .deleted: return "trash"
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
    var status: ConversationState

    init(
        id: UUID = UUID(),
        title: String = "New Chat",
        model: String? = nil,  // No default model; use orchestrator or manual selection
        createdAt: Date = Date(),
        updatedAt: Date = Date(),
        status: ConversationState = .active
    ) {
        self.id = id
        self.title = title
        self.model = model
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.status = status
    }
}

