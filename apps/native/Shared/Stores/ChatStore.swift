//
//  ChatStore.swift
//  MedStation
//
//  Chat session state management. Uses MLX Swift for on-device inference.
//  No backend HTTP calls — everything is local.
//

import Foundation
import Observation
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "ChatStore")

@MainActor
@Observable
final class ChatStore {

    // MARK: - State

    var sessions: [ChatSession] = []
    var selectedFilter: ConversationState = .active {
        didSet { UserDefaults.standard.set(selectedFilter.rawValue, forKey: "chat.selectedFilter") }
    }
    var filteredSessions: [ChatSession] {
        sessions.filter { $0.status == selectedFilter }
    }
    var currentSession: ChatSession?
    var messages: [ChatMessage] = []
    var isStreaming: Bool = false
    var isLoading: Bool = false
    var isLoadingSessions: Bool = false
    var error: ChatError?

    // MARK: - Per-Session State

    @ObservationIgnored
    private var sessionMessages: [UUID: [ChatMessage]] = [:]

    @ObservationIgnored
    private var sessionWorkspaceContext: [UUID: WorkspaceAIContext] = [:]

    // MARK: - Init

    init() {
        if let savedFilter = UserDefaults.standard.string(forKey: "chat.selectedFilter"),
           let filter = ConversationState(rawValue: savedFilter) {
            self.selectedFilter = filter
        }
    }

    // MARK: - Session Management

    func createSession(title: String = "New Chat") async {
        let session = ChatSession(
            title: title,
            createdAt: Date(),
            updatedAt: Date()
        )
        sessions.insert(session, at: 0)
        currentSession = session
        messages = []
        sessionMessages[session.id] = []
    }

    func selectSession(_ session: ChatSession) async {
        currentSession = session
        messages = sessionMessages[session.id] ?? []
    }

    func deleteSession(_ session: ChatSession) {
        let wasCurrentSession = currentSession?.id == session.id
        sessions.removeAll { $0.id == session.id }
        sessionMessages.removeValue(forKey: session.id)

        if wasCurrentSession {
            currentSession = sessions.first
            messages = currentSession.flatMap { sessionMessages[$0.id] } ?? []
        }
    }

    func renameSession(_ session: ChatSession, to newTitle: String) async {
        guard let index = sessions.firstIndex(where: { $0.id == session.id }) else { return }
        let trimmed = newTitle.trimmingCharacters(in: .whitespaces)
        guard !trimmed.isEmpty else { return }

        sessions[index].title = trimmed
        if currentSession?.id == session.id {
            currentSession?.title = trimmed
        }
    }

    // MARK: - Archive & Restore

    func archiveSession(_ session: ChatSession) {
        guard let index = sessions.firstIndex(where: { $0.id == session.id }) else { return }
        sessions[index].status = .archived
        sessions[index].updatedAt = Date()
        if currentSession?.id == session.id {
            currentSession = nil
            messages = []
        }
    }

    func restoreSession(_ session: ChatSession) {
        guard let index = sessions.firstIndex(where: { $0.id == session.id }) else { return }
        sessions[index].status = .active
        sessions[index].updatedAt = Date()
    }

    func moveToTrash(_ session: ChatSession) {
        guard let index = sessions.firstIndex(where: { $0.id == session.id }) else { return }
        sessions[index].status = .deleted
        sessions[index].updatedAt = Date()
        if currentSession?.id == session.id {
            currentSession = nil
            messages = []
        }
    }

    func permanentlyDeleteSession(_ session: ChatSession) {
        deleteSession(session)
    }

    func emptyTrash() {
        let deleted = sessions.filter { $0.status == .deleted }
        for session in deleted { deleteSession(session) }
    }

    // MARK: - Workspace Context

    func tagSession(_ sessionId: UUID, withContext context: WorkspaceAIContext) {
        sessionWorkspaceContext[sessionId] = context
    }

    func sessionsForContext(_ context: WorkspaceAIContext) -> [ChatSession] {
        sessions.filter { session in
            let mapped = sessionWorkspaceContext[session.id]
            if context == .general { return mapped == nil || mapped == .general }
            return mapped == context
        }
    }

    // Single model — MedGemma 4B via MLX

    // MARK: - Messaging (MLX native)

    func sendMessage(_ text: String, contextPrompt: String? = nil) async {
        let trimmed = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }

        // Auto-create session if needed
        if currentSession == nil {
            await createSession(title: String(trimmed.prefix(40)))
        }

        guard let session = currentSession else {
            error = .noActiveSession
            return
        }

        // Add user message
        let userMessage = ChatMessage(role: .user, content: trimmed, sessionId: session.id)
        messages.append(userMessage)

        // Add placeholder assistant message
        let assistantMessage = ChatMessage(role: .assistant, content: "", sessionId: session.id)
        messages.append(assistantMessage)

        isStreaming = true
        error = nil

        // Build system prompt
        let systemPrompt = contextPrompt ?? MedicalAIService.chatSystemPrompt

        do {
            try await MLXInferenceEngine.shared.stream(
                prompt: trimmed,
                system: systemPrompt,
                maxTokens: 1024,
                temperature: 0.3,
                onToken: { [weak self] token in
                    Task { @MainActor in
                        guard let self, let lastIndex = self.messages.indices.last else { return }
                        self.messages[lastIndex].content += token
                    }
                }
            )
        } catch {
            if !Task.isCancelled {
                logger.error("Chat inference error: \(error)")
                self.error = .sendFailed(error.localizedDescription)
                if let lastIndex = messages.indices.last,
                   messages[lastIndex].role == .assistant,
                   !messages[lastIndex].content.isEmpty {
                    messages[lastIndex].isIncomplete = true
                }
            }
        }

        isStreaming = false

        // Persist messages to session
        sessionMessages[session.id] = messages

        // Auto-title from first user message
        if session.title == "New Chat", let firstUser = messages.first(where: { $0.role == .user }) {
            await renameSession(session, to: String(firstUser.content.prefix(40)))
        }
    }

    func analyzeImageForContext(_ image: PlatformImage) async -> String? {
        do {
            let result = try await ImageAnalysisService.shared.analyze(image)
            return result.generateAIContext()
        } catch {
            logger.warning("Image analysis failed: \(error.localizedDescription)")
            return nil
        }
    }

    func regenerateLastResponse() async {
        if let lastIndex = messages.lastIndex(where: { $0.role == .assistant }) {
            messages.remove(at: lastIndex)
        }
        if let lastUserMessage = messages.last(where: { $0.role == .user }) {
            await sendMessage(lastUserMessage.content)
        }
    }

    func clearMessages() {
        messages.removeAll()
    }
}

// MARK: - Error Types

enum ChatError: LocalizedError {
    case noActiveSession
    case sendFailed(String)
    case loadFailed(String)
    case deleteFailed(String)

    var errorDescription: String? {
        switch self {
        case .noActiveSession:
            return "No active chat session. Please create a new session."
        case .sendFailed(let message):
            return "Failed to send message: \(message)"
        case .loadFailed(let message):
            return "Failed to load chat history: \(message)"
        case .deleteFailed(let sessionTitle):
            return "Failed to delete '\(sessionTitle)'. Session has been restored."
        }
    }
}
