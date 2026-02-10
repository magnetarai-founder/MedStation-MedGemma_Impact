//
//  WorkspaceContextModels.swift
//  MedStation
//
//  Context models for AI model routing and inference.
//

import Foundation

// MARK: - Conversation Models

/// Single message in conversation history
struct ConversationMessage: Codable, Identifiable, Sendable {
    let id: String
    let role: String
    let content: String
    let modelId: String?
    let timestamp: Date
    let tokenCount: Int?

    /// Create from a ChatMessage
    init(from message: ChatMessage) {
        self.id = message.id.uuidString
        self.role = message.role.rawValue
        self.content = message.content
        self.modelId = message.modelId
        self.timestamp = message.createdAt
        self.tokenCount = nil
    }

    init(
        id: String,
        role: String,
        content: String,
        modelId: String? = nil,
        timestamp: Date = Date(),
        tokenCount: Int? = nil
    ) {
        self.id = id
        self.role = role
        self.content = content
        self.modelId = modelId
        self.timestamp = timestamp
        self.tokenCount = tokenCount
    }
}

// MARK: - Model & System Models

/// Information about an available model
struct AvailableModel: Codable, Sendable {
    let id: String
    let name: String
    let displayName: String
    let slotNumber: Int?
    let isPinned: Bool
    let memoryUsageGB: Float?
    let capabilities: ModelCapabilities
    let isHealthy: Bool

    /// Whether this model is loaded and ready
    var isLoaded: Bool { slotNumber != nil }
}

/// Model capabilities for routing decisions
struct ModelCapabilities: Codable, Sendable {
    let chat: Bool
    let codeGeneration: Bool
    let dataAnalysis: Bool
    let reasoning: Bool
    let maxContextTokens: Int
    let specialized: String?

    static let basic = ModelCapabilities(
        chat: true,
        codeGeneration: false,
        dataAnalysis: false,
        reasoning: false,
        maxContextTokens: 4096,
        specialized: nil
    )

    static let full = ModelCapabilities(
        chat: true,
        codeGeneration: true,
        dataAnalysis: true,
        reasoning: true,
        maxContextTokens: 32768,
        specialized: nil
    )
}
