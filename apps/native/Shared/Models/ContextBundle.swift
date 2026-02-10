//
//  ContextBundle.swift
//  MedStation
//
//  Context passed to models during intelligent routing.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "ContextBundle")

// MARK: - Context Bundle

/// Complete context bundle for model routing and inference
struct ContextBundle: Codable, Sendable {
    // Core query
    let userQuery: String
    let sessionId: String
    let workspaceType: String

    // Conversation history
    let conversationHistory: [ConversationMessage]
    let totalMessagesInSession: Int

    // RAG/Vector search results
    let ragDocuments: [BundledRAGDocument]?
    let vectorSearchResults: [BundledVectorSearchResult]?

    // User preferences and model state
    let userPreferences: UserPreferences
    let activeModelId: String?

    // System constraints
    let systemResources: SystemResourceState
    let availableModels: [AvailableModel]

    // Metadata
    let bundledAt: Date
    let ttl: TimeInterval
}

// MARK: - Bundled RAG Document

/// Simplified RAG document for context bundling (no embeddings)
struct BundledRAGDocument: Codable, Identifiable, Sendable {
    let id: String
    let content: String
    let source: String
    let sourceId: String?
    let relevanceScore: Float
    let metadata: [String: String]?
}

// MARK: - Bundled Vector Search Result

/// Detailed vector search result for context bundling
struct BundledVectorSearchResult: Codable, Identifiable, Sendable {
    let id: String
    let text: String
    let workspaceType: String
    let resourceId: String
    let similarity: Float
    let metadata: BundledVectorMetadata
}

/// Metadata for bundled vector search results
struct BundledVectorMetadata: Codable, Sendable {
    let resourceType: String
    let timestamp: Date
    let author: String?
    let tags: [String]?
}

// MARK: - User Preferences

/// User preferences for model routing
struct UserPreferences: Codable, Sendable {
    let preferredModel: String?
    let enableStreaming: Bool
    let contextWindowSize: Int
    let theme: String

    static let `default` = UserPreferences(
        preferredModel: nil,
        enableStreaming: true,
        contextWindowSize: 8192,
        theme: "system"
    )
}

// MARK: - System Resource State

/// Current system resource state for routing decisions
struct SystemResourceState: Codable, Sendable {
    let availableMemoryGB: Float
    let totalMemoryGB: Float
    let cpuUsagePercent: Float
    let gpuAvailable: Bool
    let activeModels: [LoadedModel]

    static let `default` = SystemResourceState(
        availableMemoryGB: 8.0,
        totalMemoryGB: 16.0,
        cpuUsagePercent: 0.0,
        gpuAvailable: true,
        activeModels: []
    )
}

/// A model currently loaded in memory
struct LoadedModel: Codable, Sendable {
    let id: String
    let name: String
    let slotNumber: Int?
    let isPinned: Bool
    let memoryUsageGB: Float
}
