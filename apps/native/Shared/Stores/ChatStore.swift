//
//  ChatStore.swift
//  MagnetarStudio
//
//  Chat state management - sessions, messages, AI responses.
//

import Foundation
import Observation

@MainActor
@Observable
final class ChatStore {
    // Published state
    var sessions: [ChatSession] = []
    var currentSession: ChatSession?
    var messages: [ChatMessage] = []
    var isStreaming: Bool = false
    var isLoading: Bool = false
    var error: ChatError?
    var selectedModel: String = ""
    var availableModels: [String] = []

    // Dependencies
    @ObservationIgnored
    private let apiClient: ApiClient

    @ObservationIgnored
    private let chatService = ChatService.shared

    init(apiClient: ApiClient = .shared) {
        self.apiClient = apiClient

        // Load models and sessions on init
        Task {
            await fetchModels()
            await loadSessions()
        }
    }

    // MARK: - Model Management

    func fetchModels() async {
        do {
            let url = URL(string: "http://localhost:8000/api/v1/chat/models")!
            let (data, _) = try await URLSession.shared.data(from: url)

            let models = try JSONDecoder().decode([ModelResponse].self, from: data)
            availableModels = models.map { $0.name }

            // Set default model if none selected
            if selectedModel.isEmpty, let first = availableModels.first {
                selectedModel = first
            }

            // Clear any previous errors
            error = nil
        } catch {
            // Show error to user instead of silent print
            self.error = .loadFailed("Could not load AI models. Backend may be offline.")
            print("Failed to fetch models: \(error)")
        }
    }

    // MARK: - Session Management

    func loadSessions() async {
        do {
            let apiSessions = try await chatService.listSessions()

            // Convert API sessions to local ChatSession models
            sessions = apiSessions.map { apiSession in
                ChatSession(
                    id: UUID(uuidString: apiSession.id) ?? UUID(),
                    title: apiSession.title ?? "Untitled Chat",
                    model: apiSession.model ?? selectedModel,
                    createdAt: ISO8601DateFormatter().date(from: apiSession.createdAt) ?? Date(),
                    updatedAt: ISO8601DateFormatter().date(from: apiSession.updatedAt) ?? Date()
                )
            }

            // Select first session if available
            if currentSession == nil, let first = sessions.first {
                await selectSession(first)
            }
        } catch {
            print("Failed to load sessions: \(error)")
            self.error = .loadFailed("Could not load chat sessions")
        }
    }

    func createSession(title: String = "New Chat", model: String? = nil) async {
        isLoading = true
        error = nil

        do {
            let useModel = model ?? selectedModel
            let apiSession = try await chatService.createSession(title: title, model: useModel)

            // Create local session from API response
            let session = ChatSession(
                id: UUID(uuidString: apiSession.id) ?? UUID(),
                title: apiSession.title ?? title,
                model: apiSession.model ?? useModel,
                createdAt: ISO8601DateFormatter().date(from: apiSession.createdAt) ?? Date(),
                updatedAt: ISO8601DateFormatter().date(from: apiSession.updatedAt) ?? Date()
            )

            sessions.insert(session, at: 0)
            currentSession = session
            messages = []
        } catch {
            print("Failed to create session: \(error)")
            self.error = .sendFailed("Could not create new session")
        }

        isLoading = false
    }

    func selectSession(_ session: ChatSession) async {
        currentSession = session

        // Load messages from backend
        isLoading = true
        do {
            // Convert UUID to string for API call
            let sessionId = session.id.uuidString
            let apiMessages = try await chatService.loadMessages(sessionId: sessionId)

            // Convert API messages to local ChatMessage models
            messages = apiMessages.map { apiMsg in
                ChatMessage(
                    id: UUID(uuidString: apiMsg.id) ?? UUID(),
                    role: apiMsg.role == "user" ? .user : .assistant,
                    content: apiMsg.content,
                    sessionId: session.id,
                    createdAt: ISO8601DateFormatter().date(from: apiMsg.timestamp) ?? Date()
                )
            }
        } catch {
            print("Failed to load messages: \(error)")
            messages = []
        }
        isLoading = false
    }

    func deleteSession(_ session: ChatSession) {
        sessions.removeAll { $0.id == session.id }
        if currentSession?.id == session.id {
            currentSession = sessions.first
            if let newCurrent = currentSession {
                Task {
                    await selectSession(newCurrent)
                }
            } else {
                messages = []
            }
        }

        // TODO: Call backend delete endpoint when available
    }

    // MARK: - Messaging

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

        // Send to backend with streaming
        isLoading = true
        isStreaming = true
        error = nil

        do {
            // Create assistant message placeholder
            let assistantMessage = ChatMessage(
                role: .assistant,
                content: "",
                sessionId: session.id
            )
            messages.append(assistantMessage)

            // Build request
            let url = URL(string: "http://localhost:8000/api/v1/chat/sessions/\(session.id.uuidString)/messages")!
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")

            // Get token if available (will be nil in DEBUG mode)
            if let token = KeychainService.shared.loadToken() {
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }

            let requestBody: [String: Any] = [
                "content": text,
                "model": selectedModel.isEmpty ? "mistral" : selectedModel
            ]
            request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)

            // Stream response
            let (bytes, response) = try await URLSession.shared.bytes(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw ChatError.sendFailed("Invalid response")
            }

            if httpResponse.statusCode != 200 {
                throw ChatError.sendFailed("Server returned status \(httpResponse.statusCode)")
            }

            // Parse SSE stream
            var fullContent = ""
            for try await line in bytes.lines {
                // SSE format: "data: {...}\n\n"
                if line.hasPrefix("data: ") {
                    let jsonString = String(line.dropFirst(6)) // Remove "data: "

                    // Skip [START] marker
                    if jsonString == "[START]" {
                        continue
                    }

                    // Parse JSON
                    if let jsonData = jsonString.data(using: .utf8) {
                        if let dict = try? JSONSerialization.jsonObject(with: jsonData) as? [String: Any] {
                            // Check for error
                            if let errorMsg = dict["error"] as? String {
                                throw ChatError.sendFailed(errorMsg)
                            }

                            // Check for content chunk
                            if let chunk = dict["content"] as? String {
                                fullContent += chunk
                                // Update last message (assistant)
                                if let lastIndex = messages.indices.last {
                                    messages[lastIndex] = ChatMessage(
                                        id: messages[lastIndex].id,
                                        role: .assistant,
                                        content: fullContent,
                                        sessionId: session.id
                                    )
                                }
                            }

                            // Check for done
                            if let done = dict["done"] as? Bool, done {
                                break
                            }
                        }
                    }
                }
            }

        } catch {
            self.error = .sendFailed(error.localizedDescription)
            print("Chat error: \(error)")
        }

        isLoading = false
        isStreaming = false
    }

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

// MARK: - Model Response

struct ModelResponse: Codable {
    let name: String
    let size: String
    let modifiedAt: String

    enum CodingKeys: String, CodingKey {
        case name
        case size
        case modifiedAt = "modified_at"
    }
}
