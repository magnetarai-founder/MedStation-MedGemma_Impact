//
//  ChatStore.swift
//  MagnetarStudio
//
//  Chat state management - sessions, messages, AI responses.
//

import Foundation
import Observation

@Observable
final class ChatStore {
    // Published state
    var sessions: [ChatSession] = []
    var currentSession: ChatSession?
    var messages: [ChatMessage] = []
    var isStreaming: Bool = false
    var isLoading: Bool = false
    var error: ChatError?
    var selectedModel: String = "mistral"

    // Dependencies
    @ObservationIgnored
    private let apiClient: APIClient

    init(apiClient: APIClient = .shared) {
        self.apiClient = apiClient
    }

    // MARK: - Session Management

    @MainActor
    func createSession(title: String = "New Chat", model: String = "mistral") async {
        let session = ChatSession(title: title, model: model)
        sessions.insert(session, at: 0)
        currentSession = session
        messages = []
    }

    @MainActor
    func selectSession(_ session: ChatSession) {
        currentSession = session
        // Load messages for this session (from SwiftData or API)
        // For now, just clear
        messages = []
    }

    @MainActor
    func deleteSession(_ session: ChatSession) {
        sessions.removeAll { $0.id == session.id }
        if currentSession?.id == session.id {
            currentSession = sessions.first
            messages = currentSession?.messages ?? []
        }
    }

    // MARK: - Messaging

    @MainActor
    func sendMessage(_ text: String) async {
        guard let session = currentSession else {
            error = .noActiveSession
            return
        }

        // Add user message
        let userMessage = ChatMessage(
            role: .user,
            content: text,
            sessionId: session.id
        )
        messages.append(userMessage)

        // Send to backend
        isLoading = true
        error = nil

        do {
            // TODO: Implement actual API call
            // For now, simulate response
            try await Task.sleep(for: .seconds(1))

            let assistantMessage = ChatMessage(
                role: .assistant,
                content: "This is a simulated AI response. Backend integration coming soon!",
                sessionId: session.id
            )
            messages.append(assistantMessage)

        } catch {
            self.error = .sendFailed(error.localizedDescription)
        }

        isLoading = false
    }

    @MainActor
    func regenerateLastResponse() async {
        // Remove last assistant message
        if let lastIndex = messages.lastIndex(where: { $0.role == .assistant }) {
            messages.remove(at: lastIndex)
        }

        // Resend last user message
        if let lastUserMessage = messages.last(where: { $0.role == .user }) {
            await sendMessage(lastUserMessage.content)
        }
    }

    @MainActor
    func clearMessages() {
        messages.removeAll()
    }
}

// MARK: - Error Types

enum ChatError: LocalizedError {
    case noActiveSession
    case sendFailed(String)
    case loadFailed(String)

    var errorDescription: String? {
        switch self {
        case .noActiveSession:
            return "No active chat session. Please create a new session."
        case .sendFailed(let message):
            return "Failed to send message: \(message)"
        case .loadFailed(let message):
            return "Failed to load chat history: \(message)"
        }
    }
}
