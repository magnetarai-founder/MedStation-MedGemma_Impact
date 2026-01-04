//
//  ChatStore.swift
//  MagnetarStudio
//
//  Chat state management - sessions, messages, AI responses.
//

import Foundation
import Observation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "ChatStore")

@MainActor
@Observable
final class ChatStore {
    // Published state
    var sessions: [ChatSession] = []
    var currentSession: ChatSession?
    var messages: [ChatMessage] = []
    var isStreaming: Bool = false
    var isLoading: Bool = false
    var isLoadingSessions: Bool = false  // True while initial sessions are loading
    var error: ChatError?
    var selectedModel: String = ""
    var availableModels: [String] = []

    // Model orchestration (Phase 2)
    var selectedMode: String = "intelligent"  // "intelligent" or "manual"
    var selectedModelId: String? = nil  // Specific model when in manual mode

    /// Default model to use when no specific model is selected
    /// Uses first available model from Ollama, or a reasonable fallback
    private var defaultModel: String {
        // Prefer first available model (actually installed on system)
        if let firstModel = availableModels.first {
            return firstModel
        }
        // Fall back to selectedModel if set
        if !selectedModel.isEmpty {
            return selectedModel
        }
        // Last resort fallback - common small model
        return "llama3.2:3b"
    }

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

        // Load models and sessions on init with retry logic
        Task {
            await fetchModelsWithRetry()
            await loadSessionsWithRetry()
        }
    }

    // MARK: - Model Management

    private func fetchModelsWithRetry(maxRetries: Int = 5) async {
        for attempt in 1...maxRetries {
            await fetchModels()

            // If we successfully loaded models, we're done
            if !availableModels.isEmpty {
                return
            }

            // Wait before retrying (exponential backoff: 1s, 2s, 4s, 8s, 16s)
            if attempt < maxRetries {
                let delay = Double(1 << (attempt - 1))  // 2^(attempt-1)
                try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
            }
        }
    }

    func fetchModels() async {
        do {
            // SECURITY (CRIT-05): Use guard let instead of force unwrap
            guard let url = URL(string: APIConfiguration.shared.chatModelsURL) else {
                logger.error("Invalid URL for models endpoint")
                return
            }
            let (data, _) = try await URLSession.shared.data(from: url)

            // API now returns SuccessResponse wrapper
            struct ModelsResponse: Codable {
                let success: Bool
                let data: [ModelResponse]
                let message: String?
            }

            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            let response = try decoder.decode(ModelsResponse.self, from: data)
            availableModels = response.data.map { $0.name }

            // Set default model if none selected
            if selectedModel.isEmpty, let first = availableModels.first {
                selectedModel = first
            }

            // Clear any previous errors
            error = nil
        } catch {
            // Show error to user instead of silent print
            self.error = .loadFailed("Could not load AI models. Backend may be offline.")
            logger.error("Failed to fetch models: \(error)")
        }
    }

    // MARK: - Session Management

    /// Load sessions with retry logic for auth timing issues
    private func loadSessionsWithRetry(maxRetries: Int = 5) async {
        for attempt in 1...maxRetries {
            await loadSessions()

            // If we successfully loaded sessions (or there genuinely are none), we're done
            // Check if sessions is non-empty OR if we didn't get an auth error
            if !sessions.isEmpty || error == nil {
                return
            }

            // Wait before retrying (exponential backoff: 1s, 2s, 4s, 8s, 16s)
            if attempt < maxRetries {
                let delay = Double(1 << (attempt - 1))  // 2^(attempt-1)
                logger.info("Retrying session load in \(delay)s (attempt \(attempt)/\(maxRetries))")
                try? await Task.sleep(nanoseconds: UInt64(delay * 1_000_000_000))
            }
        }
        logger.warning("Failed to load sessions after \(maxRetries) retries")
    }

    func loadSessions() async {
        isLoadingSessions = true
        defer { isLoadingSessions = false }

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

            // Don't auto-select sessions - let user explicitly choose
            // Sessions are only selected when:
            // 1. User clicks a session in sidebar
            // 2. User creates a new session
            // 3. User sends a message (auto-creates session if needed)
        } catch ApiError.unauthorized {
            // Auth token not fully propagated yet during auto-login - this is expected
            // Silently handle by setting empty sessions - they'll load on next refresh
            sessions = []
        } catch {
            logger.error("Failed to load sessions: \(error)")
            self.error = .loadFailed("Could not load chat sessions")
        }
    }

    func createSession(title: String = "New Chat", model: String? = nil) async {
        isLoading = true
        error = nil

        do {
            // Sessions don't have fixed models - orchestrator chooses per query
            let apiSession = try await chatService.createSession(title: title, model: nil)

            // Create local session from API response
            let localId = UUID()
            let session = ChatSession(
                id: localId,
                title: apiSession.title ?? title,
                model: apiSession.model,  // Will be nil - that's correct
                createdAt: ISO8601DateFormatter().date(from: apiSession.createdAt) ?? Date(),
                updatedAt: ISO8601DateFormatter().date(from: apiSession.updatedAt) ?? Date()
            )

            // Store the mapping between local UUID and backend string ID
            sessionIdMapping[localId] = apiSession.id

            sessions.insert(session, at: 0)
            currentSession = session
            messages = []
        } catch {
            logger.error("Failed to create session: \(error)")
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
                logger.warning("Failed to load session: session not found in backend mapping")
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
            logger.error("Failed to load messages: \(error)")
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
            logger.debug("Failed to load model preferences: \(error)")
            // Default to intelligent mode
            selectedMode = "intelligent"
            selectedModelId = nil
        }
    }

    /// Save model preferences for the current session
    func saveModelPreferences() async {
        guard let session = currentSession else { return }
        guard let backendSessionId = sessionIdMapping[session.id] else {
            logger.warning("Failed to save model preferences: session not found in backend mapping")
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
            logger.error("Failed to save model preferences: \(error)")
        }
    }

    func deleteSession(_ session: ChatSession) {
        // Store session state before deletion for potential rollback
        let deletedSessionIndex = sessions.firstIndex { $0.id == session.id }
        let backendId = sessionIdMapping[session.id]
        let wasCurrentSession = currentSession?.id == session.id

        // Optimistically remove from UI
        sessions.removeAll { $0.id == session.id }
        if wasCurrentSession {
            currentSession = sessions.first
            if let newCurrent = currentSession {
                Task { [weak self] in
                    await self?.selectSession(newCurrent)
                }
            } else {
                messages = []
            }
        }

        // Delete from backend using mapped backend ID
        Task { [weak self] in
            guard let self else { return }
            do {
                // Get backend ID from mapping
                guard let backendId else {
                    logger.warning("No backend ID mapping found for session \(session.id)")
                    return
                }

                try await self.chatService.deleteSession(sessionId: backendId)

                // Remove from mapping after successful delete
                self.sessionIdMapping.removeValue(forKey: session.id)
            } catch {
                logger.error("Failed to delete session from backend: \(error)")

                // Rollback: restore session to UI
                if let index = deletedSessionIndex {
                    self.sessions.insert(session, at: min(index, self.sessions.count))
                } else {
                    self.sessions.insert(session, at: 0)
                }

                // Restore mapping if we had one
                if let backendId {
                    self.sessionIdMapping[session.id] = backendId
                }

                // Restore as current session if it was selected
                if wasCurrentSession {
                    self.currentSession = session
                }

                // Show error to user
                self.error = .deleteFailed(session.title)
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
                logger.debug("Manual mode: Using selected model \(modelId)")
                return modelId
            } else {
                // Fallback to default
                let fallback = defaultModel
                logger.debug("Manual mode but no model selected, using default: \(fallback)")
                return fallback
            }
        }

        // Intelligent mode: use orchestrator
        logger.debug("Intelligent mode: Using orchestrator to determine best model")

        do {
            // Build context bundle
            let bundle = await buildContextBundle(query: query, sessionId: sessionId)

            // Get orchestrator
            let manager = OrchestratorManager.shared
            guard let orchestrator = await manager.getActiveOrchestrator() else {
                let fallback = defaultModel
                logger.warning("No orchestrator available, using default model: \(fallback)")
                return fallback
            }

            // Route with orchestrator
            let decision = try await orchestrator.route(bundle: bundle)

            logger.info("Orchestrator decision - Model: \(decision.selectedModelName), Confidence: \(Int(decision.confidence * 100))%, Reasoning: \(decision.reasoning)")

            return decision.selectedModelId

        } catch {
            let fallback = self.defaultModel
            logger.error("Orchestrator routing failed: \(error), using default: \(fallback)")
            // Fallback to default
            return fallback
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

        // Phase 5: Get relevant vault files via semantic search
        let vaultSearchResults = await ContextService.shared.searchVaultFiles(for: query, limit: 5)
        let relevantVaultFiles: [RelevantVaultFile]? = vaultSearchResults.isEmpty ? nil : vaultSearchResults.map { result in
            RelevantVaultFile(
                fileId: result.fileId,
                fileName: result.fileName,
                filePath: result.filePath ?? "",
                snippet: result.snippet,
                relevanceScore: result.relevanceScore
            )
        }

        // Convert VaultContext to BundledVaultContext
        let bundledVaultContext = BundledVaultContext(
            unlockedVaultType: vaultContext.unlockedVaultType,
            recentlyAccessedFiles: vaultContext.recentFiles,
            currentlyGrantedPermissions: vaultContext.activePermissions,
            relevantFiles: relevantVaultFiles
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
            // Determine which model to use (intelligent routing or manual)
            let modelToUse = await determineModelForQuery(text, sessionId: backendSessionId)

            // Create assistant message placeholder with model tracking
            let assistantMessage = ChatMessage(
                role: .assistant,
                content: "",
                sessionId: session.id,
                modelId: modelToUse
            )
            messages.append(assistantMessage)

            // Stream the AI response
            let fullContent = try await streamMessageResponse(
                sessionId: backendSessionId,
                localSessionId: session.id,
                content: text,
                model: modelToUse
            )

            // Store context for semantic search (fire and forget)
            storeMessageContext(
                sessionId: session.id,
                userQuery: text,
                response: fullContent,
                model: modelToUse
            )

        } catch {
            self.error = .sendFailed(error.localizedDescription)
            logger.error("Chat error: \(error)")

            // Mark the last assistant message as incomplete if it exists and has content
            if let lastIndex = messages.indices.last,
               messages[lastIndex].role == .assistant,
               !messages[lastIndex].content.isEmpty {
                messages[lastIndex].isIncomplete = true
            }
        }

        isLoading = false
        isStreaming = false
    }

    // MARK: - Streaming Helpers

    /// Build and send streaming request, returning full response content
    private func streamMessageResponse(
        sessionId: String,
        localSessionId: UUID,
        content: String,
        model: String
    ) async throws -> String {
        // Build request
        let request = try buildMessageRequest(
            sessionId: sessionId,
            content: content,
            model: model
        )

        // Execute streaming request
        let (bytes, response) = try await URLSession.shared.bytes(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw ChatError.sendFailed("Invalid response")
        }

        if httpResponse.statusCode != 200 {
            throw ChatError.sendFailed("Server returned status \(httpResponse.statusCode)")
        }

        // Parse SSE stream and update messages in real-time
        return try await parseSSEStream(
            bytes: bytes,
            localSessionId: localSessionId,
            model: model
        )
    }

    /// Build HTTP request for sending a message
    private func buildMessageRequest(
        sessionId: String,
        content: String,
        model: String
    ) throws -> URLRequest {
        guard let url = URL(string: "\(APIConfiguration.shared.versionedBaseURL)/chat/sessions/\(sessionId)/messages") else {
            throw ChatError.sendFailed("Invalid URL for session messages")
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Get token if available (will be nil in DEBUG mode)
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let requestBody: [String: Any] = [
            "content": content,
            "model": model
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)

        return request
    }

    /// Parse SSE stream and update assistant message in real-time
    private func parseSSEStream(
        bytes: URLSession.AsyncBytes,
        localSessionId: UUID,
        model: String
    ) async throws -> String {
        var fullContent = ""

        for try await line in bytes.lines {
            // SSE format: "data: {...}\n\n"
            guard line.hasPrefix("data: ") else { continue }

            let jsonString = String(line.dropFirst(6)) // Remove "data: "

            // Skip [START] marker
            if jsonString == "[START]" { continue }

            // Parse JSON chunk
            guard let jsonData = jsonString.data(using: .utf8),
                  let dict = try? JSONSerialization.jsonObject(with: jsonData) as? [String: Any] else {
                continue
            }

            // Check for error
            if let errorMsg = dict["error"] as? String {
                throw ChatError.sendFailed(errorMsg)
            }

            // Check for content chunk
            if let chunk = dict["content"] as? String {
                fullContent += chunk
                updateAssistantMessage(content: fullContent, sessionId: localSessionId, model: model)
            }

            // Check for done
            if let done = dict["done"] as? Bool, done {
                break
            }
        }

        return fullContent
    }

    /// Update the last assistant message with streaming content
    private func updateAssistantMessage(content: String, sessionId: UUID, model: String) {
        guard let lastIndex = messages.indices.last else { return }
        messages[lastIndex] = ChatMessage(
            id: messages[lastIndex].id,
            role: .assistant,
            content: content,
            sessionId: sessionId,
            modelId: model
        )
    }

    /// Store message context for semantic search (fire and forget)
    private func storeMessageContext(
        sessionId: UUID,
        userQuery: String,
        response: String,
        model: String
    ) {
        Task {
            do {
                try await ContextService.shared.storeContext(
                    sessionId: sessionId.uuidString,
                    workspaceType: "chat",
                    content: """
                    User: \(userQuery)
                    Assistant: \(response)
                    """,
                    metadata: [
                        "model": model,
                        "user_query": userQuery,
                        "response_length": response.count
                    ]
                )
            } catch {
                // Context storage is optional - silently ignore 404s
                #if DEBUG
                if !"\(error)".contains("404") {
                    logger.debug("Context storage error: \(error)")
                }
                #endif
            }
        }
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

// MARK: - Model Response

struct ModelResponse: Codable {
    let name: String
    let size: Int
    let modifiedAt: String?

    enum CodingKeys: String, CodingKey {
        case name, size, modifiedAt = "modified_at"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        name = try container.decode(String.self, forKey: .name)
        size = try container.decode(Int.self, forKey: .size)
        modifiedAt = try container.decodeIfPresent(String.self, forKey: .modifiedAt)
    }
}
