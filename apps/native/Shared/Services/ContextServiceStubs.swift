//
//  ContextServiceStubs.swift
//  MedStation
//
//  Minimal stubs for deleted context infrastructure.
//  These no-op implementations allow ChatStore to compile while
//  the vector/RAG context engine is removed.
//

import Foundation

// MARK: - Context Summary

struct ContextSummary: Sendable {
    let indexedMessages: Int
    let indexedSessions: Int

    static let empty = ContextSummary(indexedMessages: 0, indexedSessions: 0)
}

// MARK: - Enhanced Context Bridge

@MainActor
final class EnhancedContextBridge {
    static let shared = EnhancedContextBridge()
    private init() {}

    func getContextSummary() -> ContextSummary {
        .empty
    }

    func onSessionSelected(_ sessionId: UUID) async {
        // No-op: vector indexing removed
    }

    func onSessionEnded(_ sessionId: UUID, messages: [ChatMessage]) async {
        // No-op: vector indexing removed
    }

    func processMessageForContext(
        message: ChatMessage,
        sessionId: UUID,
        conversationTitle: String?
    ) async {
        // No-op: vector indexing removed
    }
}

// MARK: - Context Service

@MainActor
final class ContextService {
    static let shared = ContextService()
    private init() {}

    func storeContext(
        sessionId: String,
        workspaceType: String,
        content: String,
        metadata: [String: Any]
    ) async throws {
        // No-op: context engine removed
    }
}
