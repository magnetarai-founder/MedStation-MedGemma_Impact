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

    // Model orchestration (Phase 2)
    var selectedMode: String = "intelligent"  // "intelligent" or "manual"
    var selectedModelId: String? = nil  // Specific model when in manual mode

    // Dependencies
    @ObservationIgnored
    private let apiClient: ApiClient

    @ObservationIgnored
    private let chatService = ChatService.shared

    // Session ID mapping: local UUID -> backend string ID
    @ObservationIgnored
    private var sessionIdMapping: [UUID: String] = [:]

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

            // Convert API sessions to local ChatSession models and build ID mapping
            sessions = apiSessions.map { apiSession in
                let localId = UUID()
                let session = ChatSession(
                    id: localId,
                    title: apiSession.title ?? "Untitled Chat",
                    model: apiSession.model ?? selectedModel,
                    createdAt: ISO8601DateFormatter().date(from: apiSession.createdAt) ?? Date(),
                    updatedAt: ISO8601DateFormatter().date(from: apiSession.updatedAt) ?? Date()
                )

                // Store mapping between local UUID and backend string ID
                sessionIdMapping[localId] = apiSession.id

                return session
            }

            // Select first session if available
            if currentSession == nil, let first = sessions.first {
                await selectSession(first)
            }
        } catch ApiError.unauthorized {
            print("⚠️ Unauthorized when loading sessions - session may not be initialized yet")
            // Don't show error to user for auth issues - they just logged in
            sessions = []
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
            let localId = UUID()
            let session = ChatSession(
                id: localId,
                title: apiSession.title ?? title,
                model: apiSession.model ?? useModel,
                createdAt: ISO8601DateFormatter().date(from: apiSession.createdAt) ?? Date(),
                updatedAt: ISO8601DateFormatter().date(from: apiSession.updatedAt) ?? Date()
            )

            // Store the mapping between local UUID and backend string ID
            sessionIdMapping[localId] = apiSession.id

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
            // Get backend session ID from mapping
            guard let backendSessionId = sessionIdMapping[session.id] else {
                print("Failed to load session: session not found in backend mapping")
                messages = []
                isLoading = false
                return
            }
            let apiMessages = try await chatService.loadMessages(sessionId: backendSessionId)

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

            // Load model preferences for this session
            await loadModelPreferences(sessionId: backendSessionId)
        } catch {
            print("Failed to load messages: \(error)")
            messages = []
        }
        isLoading = false
    }

    // MARK: - Model Preferences (Phase 2)

    /// Load model preferences for the current session
    func loadModelPreferences(sessionId: String) async {
        do {
            struct ModelPreferencesResponse: Codable {
                let selectedMode: String
                let selectedModelId: String?

                enum CodingKeys: String, CodingKey {
                    case selectedMode = "selected_mode"
                    case selectedModelId = "selected_model_id"
                }
            }

            let prefs: ModelPreferencesResponse = try await apiClient.request(
                "/api/v1/chat/sessions/\(sessionId)/model-preferences",
                method: .get
            )

            selectedMode = prefs.selectedMode
            selectedModelId = prefs.selectedModelId
        } catch {
            print("Failed to load model preferences: \(error)")
            // Default to intelligent mode
            selectedMode = "intelligent"
            selectedModelId = nil
        }
    }

    /// Save model preferences for the current session
    func saveModelPreferences() async {
        guard let session = currentSession else { return }
        guard let backendSessionId = sessionIdMapping[session.id] else {
            print("Failed to save model preferences: session not found in backend mapping")
            return
        }

        do {
            struct UpdateRequest: Codable {
                let selectedMode: String
                let selectedModelId: String?

                enum CodingKeys: String, CodingKey {
                    case selectedMode = "selected_mode"
                    case selectedModelId = "selected_model_id"
                }
            }

            let _: EmptyResponse = try await apiClient.request(
                "/api/v1/chat/sessions/\(backendSessionId)/model-preferences",
                method: .put,
                body: UpdateRequest(
                    selectedMode: selectedMode,
                    selectedModelId: selectedModelId
                )
            )
        } catch {
            print("Failed to save model preferences: \(error)")
        }
    }

    private struct EmptyResponse: Codable {}

    func deleteSession(_ session: ChatSession) {
        // Optimistically remove from UI
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

        // Delete from backend
        Task {
            do {
                try await chatService.deleteSession(sessionId: session.id.uuidString)
            } catch {
                print("Failed to delete session from backend: \(error)")
                // Session already removed from UI, just log the error
            }
        }
    }

    // MARK: - Intelligent Routing (Phase 4)

    /// Determine which model to use for a query
    /// Uses orchestrator in "intelligent" mode, manual selection otherwise
    private func determineModelForQuery(_ query: String, sessionId: String) async -> String {
        // Check mode
        if selectedMode == "manual" {
            // Manual mode: use specifically selected model
            if let modelId = selectedModelId {
                print("✓ Manual mode: Using selected model \(modelId)")
                return modelId
            } else {
                // Fallback to default
                print("⚠️ Manual mode but no model selected, using default")
                return selectedModel.isEmpty ? "llama3.2:3b" : selectedModel
            }
        }

        // Intelligent mode: use orchestrator
        print("🧠 Intelligent mode: Using orchestrator to determine best model")

        do {
            // Build context bundle
            let bundle = await buildContextBundle(query: query, sessionId: sessionId)

            // Get orchestrator
            let manager = OrchestratorManager.shared
            guard let orchestrator = await manager.getActiveOrchestrator() else {
                print("✗ No orchestrator available, using default model")
                return selectedModel.isEmpty ? "llama3.2:3b" : selectedModel
            }

            // Route with orchestrator
            let decision = try await orchestrator.route(bundle: bundle)

            print("✓ Orchestrator decision:")
            print("  Model: \(decision.selectedModelName)")
            print("  Confidence: \(Int(decision.confidence * 100))%")
            print("  Reasoning: \(decision.reasoning)")

            return decision.selectedModelId

        } catch {
            print("✗ Orchestrator routing failed: \(error)")
            // Fallback to default
            return selectedModel.isEmpty ? "llama3.2:3b" : selectedModel
        }
    }

    /// Build context bundle for orchestrator routing
    private func buildContextBundle(query: String, sessionId: String) async -> ContextBundle {
        // Get app context
        let appContext = await AppContext.current()

        // Convert messages to ConversationMessage format
        let conversationHistory = messages.map { msg in
            ConversationMessage(
                id: msg.id.uuidString,
                role: msg.role == .user ? "user" : "assistant",
                content: msg.content,
                modelId: msg.modelId,  // Track which model generated each response
                timestamp: msg.createdAt,
                tokenCount: nil
            )
        }

        // Get available models (hot slots + all models)
        let hotSlotManager = HotSlotManager.shared
        let memoryTracker = ModelMemoryTracker.shared

        let availableModels: [AvailableModel] = availableModels.enumerated().map { index, modelName in
            // Check if in hot slot
            let slot = hotSlotManager.hotSlots.first { $0.modelId == modelName }

            return AvailableModel(
                id: modelName,
                name: modelName,
                displayName: modelName,
                slotNumber: slot?.slotNumber,
                isPinned: slot?.isPinned ?? false,
                memoryUsageGB: memoryTracker.getMemoryUsage(for: modelName),
                capabilities: ModelCapabilities(
                    chat: true,
                    codeGeneration: modelName.lowercased().contains("coder"),
                    dataAnalysis: modelName.lowercased().contains("phi"),
                    reasoning: modelName.lowercased().contains("deepseek"),
                    maxContextTokens: 8192,
                    specialized: nil
                ),
                isHealthy: true
            )
        }

        // Phase 5: Get RAG documents from ANE Context Engine
        let ragDocuments = await ContextService.shared.getRAGDocuments(for: query, limit: 5)

        // Phase 3: Get vault context (file permissions and access)
        let vaultContext = await VaultContext.current()

        // Convert VaultContext to BundledVaultContext
        let bundledVaultContext = BundledVaultContext(
            unlockedVaultType: vaultContext.unlockedVaultType,
            recentlyAccessedFiles: vaultContext.recentFiles,
            currentlyGrantedPermissions: vaultContext.activePermissions,
            relevantFiles: nil  // TODO: Add semantic search for relevant vault files
        )

        return ContextBundle(
            userQuery: query,
            sessionId: sessionId,
            workspaceType: "chat",
            conversationHistory: conversationHistory,
            totalMessagesInSession: messages.count,
            vaultContext: bundledVaultContext,
            dataContext: nil,
            kanbanContext: nil,
            workflowContext: nil,
            teamContext: nil,
            codeContext: nil,
            ragDocuments: ragDocuments.isEmpty ? nil : ragDocuments,
            vectorSearchResults: nil,
            userPreferences: appContext.userPreferences,
            activeModelId: selectedModelId,
            systemResources: appContext.systemResources,
            availableModels: availableModels,
            bundledAt: Date(),
            ttl: 60
        )
    }

    // MARK: - Messaging

    func sendMessage(_ text: String) async {
        // Auto-create session if none exists (UX improvement)
        if currentSession == nil {
            await createSession(title: "New Chat")
        }

        guard let session = currentSession else {
            error = .noActiveSession
            return
        }

        // Get backend session ID from mapping
        guard let backendSessionId = sessionIdMapping[session.id] else {
            error = .sendFailed("Session not found in backend mapping")
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
            // Phase 4: Determine which model to use (intelligent routing or manual)
            let modelToUse = await determineModelForQuery(text, sessionId: backendSessionId)

            // Create assistant message placeholder with model tracking
            let assistantMessage = ChatMessage(
                role: .assistant,
                content: "",
                sessionId: session.id,
                modelId: modelToUse
            )
            messages.append(assistantMessage)

            // Build request using backend session ID
            let url = URL(string: "http://localhost:8000/api/v1/chat/sessions/\(backendSessionId)/messages")!
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")

            // Get token if available (will be nil in DEBUG mode)
            if let token = KeychainService.shared.loadToken() {
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }

            let requestBody: [String: Any] = [
                "content": text,
                "model": modelToUse
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
                                // Update last message (assistant) while preserving modelId
                                if let lastIndex = messages.indices.last {
                                    messages[lastIndex] = ChatMessage(
                                        id: messages[lastIndex].id,
                                        role: .assistant,
                                        content: fullContent,
                                        sessionId: session.id,
                                        modelId: modelToUse
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

            // Auto-store context for future semantic search (Phase 5)
            Task {
                do {
                    try await ContextService.shared.storeContext(
                        sessionId: session.id.uuidString,
                        workspaceType: "chat",
                        content: """
                        User: \(text)
                        Assistant: \(fullContent)
                        """,
                        metadata: [
                            "model": modelToUse,
                            "user_query": text,
                            "response_length": fullContent.count
                        ]
                    )
                    print("✅ Stored chat context in ANE for session \(session.id.uuidString)")
                } catch {
                    print("⚠️ Failed to store context in ANE: \(error)")
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
    let size: Int
    let modifiedAt: String

    enum CodingKeys: String, CodingKey {
        case name
        case size
        case modifiedAt = "modified_at"
    }
}
