//
//  ChatStore.swift
//  MedStation
//
//  SPDX-License-Identifier: Proprietary
//

import Foundation
import Observation
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "ChatStore")

// MARK: - ChatStore

/// Central state management for the Chat workspace.
///
/// ## Overview
/// ChatStore manages AI chat sessions, messages, streaming responses, and model selection.
/// It coordinates between the local UI state and the backend ChatService for persistence.
///
/// ## Architecture
/// - **Thread Safety**: `@MainActor` isolated - all UI updates happen on main thread
/// - **Observation**: Uses `@Observable` macro for SwiftUI reactivity
/// - **Singleton**: Access via `ChatStore()` injection or direct instantiation
///
/// ## State Persistence (UserDefaults)
/// The following state is automatically persisted and restored on app launch:
/// - `currentSessionId` - Restored after sessions load (deferred pattern)
/// - `selectedMode` - "intelligent" or "manual" model selection
/// - `selectedModelId` - Specific model ID when in manual mode
///
/// ## Key Patterns
/// - **Deferred Restoration**: Session ID is stored in `pendingRestoreSessionId` and
///   restored only after `loadSessions()` completes, ensuring the session object exists.
/// - **Streaming**: Uses async sequences for real-time AI response streaming
/// - **ID Mapping**: Maintains `sessionIdMapping` to translate between local UUIDs
///   and backend string IDs
///
/// ## Dependencies
/// - `ChatService` - Backend API communication
/// - `ApiClient` - HTTP requests and authentication
///
/// ## Usage
/// ```swift
/// // In SwiftUI view
/// @State private var chatStore = ChatStore()
///
/// // Create new session
/// await chatStore.createSession()
///
/// // Send message with streaming
/// await chatStore.sendMessage("Hello", sessionId: session.id)
/// ```
@MainActor
@Observable
final class ChatStore {
    // MARK: - State Persistence Keys
    private static let currentSessionIdKey = "chat.currentSessionId"
    private static let selectedModeKey = "chat.selectedMode"
    private static let selectedModelIdKey = "chat.selectedModelId"
    private static let selectedFilterKey = "chat.selectedFilter"

    // Published state
    var sessions: [ChatSession] = []
    var selectedFilter: ConversationState = .active {
        didSet { UserDefaults.standard.set(selectedFilter.rawValue, forKey: Self.selectedFilterKey) }
    }

    /// Sessions filtered by the current filter selection
    var filteredSessions: [ChatSession] {
        sessions.filter { $0.status == selectedFilter }
    }
    var currentSession: ChatSession? {
        didSet {
            if let sessionId = currentSession?.id.uuidString {
                UserDefaults.standard.set(sessionId, forKey: Self.currentSessionIdKey)
            }
        }
    }
    var messages: [ChatMessage] = []
    var isStreaming: Bool = false
    var isLoading: Bool = false
    var isLoadingSessions: Bool = false  // True while initial sessions are loading
    var error: ChatError?
    var selectedModel: String = ""
    var availableModels: [String] = []

    // Model orchestration (Phase 2)
    var selectedMode: String = "intelligent" {  // "intelligent" or "manual"
        didSet { UserDefaults.standard.set(selectedMode, forKey: Self.selectedModeKey) }
    }
    var selectedModelId: String? = nil {  // Specific model when in manual mode
        didSet { UserDefaults.standard.set(selectedModelId, forKey: Self.selectedModelIdKey) }
    }

    // Context utilization (stub — context bridge removed)
    var contextTokensUsed: Int { 0 }

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

    // Context bridge removed (non-medical feature)

    // MARK: - Per-Session Model Override (transient, resets on app restart)

    struct SessionModelOverride: Codable, Sendable {
        let mode: String       // "intelligent" or "manual"
        let modelId: String?
    }

    @ObservationIgnored
    private var sessionModelOverrides: [UUID: SessionModelOverride] = [:]

    func setSessionModelOverride(sessionId: UUID, mode: String, modelId: String?) {
        sessionModelOverrides[sessionId] = SessionModelOverride(mode: mode, modelId: modelId)
        logger.debug("Set model override for session \(sessionId): mode=\(mode), model=\(modelId ?? "nil")")
    }

    func clearSessionModelOverride(sessionId: UUID) {
        sessionModelOverrides.removeValue(forKey: sessionId)
        logger.debug("Cleared model override for session \(sessionId)")
    }

    func hasModelOverride(for sessionId: UUID) -> Bool {
        sessionModelOverrides[sessionId] != nil
    }

    func effectiveModelSelection(for sessionId: UUID) -> (mode: String, modelId: String?) {
        // Tier 1: per-session override
        if let override = sessionModelOverrides[sessionId] {
            return (override.mode, override.modelId)
        }
        // Tier 2: per-workspace-context override
        if let context = sessionWorkspaceContext[sessionId],
           let workspaceOverride = workspaceModelOverrides[context] {
            return (workspaceOverride.mode, workspaceOverride.modelId)
        }
        // Tier 3: global default
        return (selectedMode, selectedModelId)
    }

    // MARK: - Per-Workspace Model Override (persisted to UserDefaults)

    private static let workspaceModelOverridesKey = "chat.workspaceModelOverrides"
    private static let sessionWorkspaceContextKey = "chat.sessionWorkspaceContext"

    @ObservationIgnored
    private var workspaceModelOverrides: [WorkspaceAIContext: SessionModelOverride] = [:]

    @ObservationIgnored
    private var sessionWorkspaceContext: [UUID: WorkspaceAIContext] = [:]

    func setWorkspaceModelOverride(context: WorkspaceAIContext, mode: String, modelId: String?) {
        workspaceModelOverrides[context] = SessionModelOverride(mode: mode, modelId: modelId)
        saveWorkspaceModelOverrides()
        logger.debug("Set workspace model override for \(context.rawValue): mode=\(mode), model=\(modelId ?? "nil")")
    }

    func clearWorkspaceModelOverride(context: WorkspaceAIContext) {
        workspaceModelOverrides.removeValue(forKey: context)
        saveWorkspaceModelOverrides()
        logger.debug("Cleared workspace model override for \(context.rawValue)")
    }

    func hasWorkspaceModelOverride(for context: WorkspaceAIContext) -> Bool {
        workspaceModelOverrides[context] != nil
    }

    func workspaceModelSelection(for context: WorkspaceAIContext) -> (mode: String, modelId: String?) {
        if let override = workspaceModelOverrides[context] {
            return (override.mode, override.modelId)
        }
        return (selectedMode, selectedModelId)
    }

    func tagSession(_ sessionId: UUID, withContext context: WorkspaceAIContext) {
        sessionWorkspaceContext[sessionId] = context
        saveSessionWorkspaceContext()
    }

    func sessionsForContext(_ context: WorkspaceAIContext) -> [ChatSession] {
        sessions.filter { session in
            let mapped = sessionWorkspaceContext[session.id]
            if context == .general {
                return mapped == nil || mapped == .general
            }
            return mapped == context
        }
    }

    // MARK: - Workspace Override Persistence

    private func saveWorkspaceModelOverrides() {
        do {
            let mapped = Dictionary(uniqueKeysWithValues: workspaceModelOverrides.map { ($0.key.rawValue, $0.value) })
            let data = try JSONEncoder().encode(mapped)
            UserDefaults.standard.set(data, forKey: Self.workspaceModelOverridesKey)
        } catch {
            logger.warning("Failed to save workspace model overrides: \(error)")
        }
    }

    private func loadWorkspaceModelOverrides() {
        guard let data = UserDefaults.standard.data(forKey: Self.workspaceModelOverridesKey) else { return }
        do {
            let decoded = try JSONDecoder().decode([String: SessionModelOverride].self, from: data)
            workspaceModelOverrides = Dictionary(uniqueKeysWithValues: decoded.compactMap { key, value in
                guard let context = WorkspaceAIContext(rawValue: key) else { return nil }
                return (context, value)
            })
        } catch {
            logger.warning("Failed to load workspace model overrides: \(error)")
        }
    }

    private func saveSessionWorkspaceContext() {
        do {
            let mapped = Dictionary(uniqueKeysWithValues: sessionWorkspaceContext.map { ($0.key.uuidString, $0.value.rawValue) })
            let data = try JSONEncoder().encode(mapped)
            UserDefaults.standard.set(data, forKey: Self.sessionWorkspaceContextKey)
        } catch {
            logger.warning("Failed to save session workspace context: \(error)")
        }
    }

    private func loadSessionWorkspaceContext() {
        guard let data = UserDefaults.standard.data(forKey: Self.sessionWorkspaceContextKey) else { return }
        do {
            let decoded = try JSONDecoder().decode([String: String].self, from: data)
            sessionWorkspaceContext = Dictionary(uniqueKeysWithValues: decoded.compactMap { key, value in
                guard let uuid = UUID(uuidString: key),
                      let context = WorkspaceAIContext(rawValue: value) else { return nil }
                return (uuid, context)
            })
        } catch {
            logger.warning("Failed to load session workspace context: \(error)")
        }
    }

    // Session ID mapping: local UUID -> backend string ID
    @ObservationIgnored
    private var sessionIdMapping: [UUID: String] = [:]

    // Persisted session ID to restore after sessions load
    @ObservationIgnored
    private var pendingRestoreSessionId: UUID?

    init(apiClient: ApiClient = .shared) {
        self.apiClient = apiClient

        // Restore persisted state
        if let savedMode = UserDefaults.standard.string(forKey: Self.selectedModeKey) {
            self.selectedMode = savedMode
        }
        self.selectedModelId = UserDefaults.standard.string(forKey: Self.selectedModelIdKey)

        // Restore filter selection
        if let savedFilter = UserDefaults.standard.string(forKey: Self.selectedFilterKey),
           let filter = ConversationState(rawValue: savedFilter) {
            self.selectedFilter = filter
        }

        // Store session ID to restore after sessions load
        if let savedSessionId = UserDefaults.standard.string(forKey: Self.currentSessionIdKey),
           let uuid = UUID(uuidString: savedSessionId) {
            self.pendingRestoreSessionId = uuid
        }

        // Restore workspace model overrides
        loadWorkspaceModelOverrides()
        loadSessionWorkspaceContext()

        // MedStation uses MedGemma exclusively — no backend model/session endpoints needed
        availableModels = ["google/medgemma-1.5-4b-it"]
        if selectedModel.isEmpty {
            selectedModel = "google/medgemma-1.5-4b-it"
        }
    }

    /// Restore the previously selected session after sessions load
    private func restorePersistedSession() async {
        guard let sessionId = pendingRestoreSessionId else { return }
        if let session = sessions.first(where: { $0.id == sessionId }) {
            // Use selectSession which handles loading messages and model preferences
            await selectSession(session)
        }
        pendingRestoreSessionId = nil
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
            struct ModelsResponse: Codable, Sendable {
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
                logger.debug("Retrying session load in \(delay)s (attempt \(attempt)/\(maxRetries))")
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
            var newMapping: [UUID: String] = [:]
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
                newMapping[localId] = apiSession.id

                return session
            }

            // Replace old mapping entirely to prevent memory growth
            // This cleans up stale entries from previous loads
            sessionIdMapping = newMapping

            // Don't auto-select sessions - let user explicitly choose
            // Sessions are only selected when:
            // 1. User clicks a session in sidebar
            // 2. User creates a new session
            // 3. User sends a message (auto-creates session if needed)
        } catch ApiError.unauthorized {
            // Auth token not fully propagated yet during auto-login - this is expected
            // Silently handle by setting empty sessions - they'll load on next refresh
            sessions = []
            sessionIdMapping = [:]  // Clear mapping when no sessions
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
        // Session change (context bridge removed)

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

            // Session selected (context bridge removed)
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
            struct ModelPreferencesResponse: Codable, Sendable {
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
            struct UpdateRequest: Codable, Sendable {
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
        _ = wasCurrentSession ? messages : []

        // Notify context bridge about session ending (archive context)
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

    func renameSession(_ session: ChatSession, to newTitle: String) async {
        // Find and update session locally
        guard let index = sessions.firstIndex(where: { $0.id == session.id }) else {
            logger.warning("Cannot rename: session not found")
            return
        }

        let trimmedTitle = newTitle.trimmingCharacters(in: .whitespaces)
        guard !trimmedTitle.isEmpty else {
            logger.warning("Cannot rename: empty title")
            return
        }

        // Update locally
        sessions[index].title = trimmedTitle
        if currentSession?.id == session.id {
            currentSession?.title = trimmedTitle
        }

        // Update on backend if we have a mapping
        if let backendId = sessionIdMapping[session.id] {
            do {
                try await chatService.renameSession(sessionId: backendId, title: trimmedTitle)
                logger.info("Renamed session \(session.id) to '\(trimmedTitle)'")
            } catch {
                logger.error("Failed to rename session on backend: \(error)")
                // Keep local change anyway - next sync will fix it
            }
        }
    }

    // MARK: - Archive & Restore

    /// Archive a session (soft delete - moves to archived state)
    func archiveSession(_ session: ChatSession) {
        guard let index = sessions.firstIndex(where: { $0.id == session.id }) else {
            logger.warning("Cannot archive: session not found")
            return
        }

        let wasCurrentSession = currentSession?.id == session.id

        // Update status locally
        sessions[index].status = .archived
        sessions[index].updatedAt = Date()

        // If this was the current session, clear selection
        if wasCurrentSession {
            currentSession = nil
            messages = []
        }

        logger.info("Archived session: \(session.title)")

        // Backend API does not support archive status — local only for now.
        // When /v1/chat/sessions/:id/archive endpoint is added, sync here.
    }

    /// Restore a session from archived or deleted state
    func restoreSession(_ session: ChatSession) {
        guard let index = sessions.firstIndex(where: { $0.id == session.id }) else {
            logger.warning("Cannot restore: session not found")
            return
        }

        // Update status locally
        sessions[index].status = .active
        sessions[index].updatedAt = Date()

        logger.info("Restored session: \(session.title)")

        // Backend API does not support restore status — local only for now.
        // When /v1/chat/sessions/:id/restore endpoint is added, sync here.
    }

    /// Move session to deleted state (can still be restored)
    func moveToTrash(_ session: ChatSession) {
        guard let index = sessions.firstIndex(where: { $0.id == session.id }) else {
            logger.warning("Cannot trash: session not found")
            return
        }

        let wasCurrentSession = currentSession?.id == session.id

        // Update status locally
        sessions[index].status = .deleted
        sessions[index].updatedAt = Date()

        // If this was the current session, clear selection
        if wasCurrentSession {
            currentSession = nil
            messages = []
        }

        logger.info("Moved session to trash: \(session.title)")

        // Best-effort backend sync — delete on backend since it has no "trash" state
        if let backendId = sessionIdMapping[session.id] {
            Task {
                do {
                    try await chatService.deleteSession(sessionId: backendId)
                    logger.debug("Backend session \(backendId) deleted (trash sync)")
                } catch {
                    logger.warning("Failed to sync trash to backend: \(error.localizedDescription)")
                }
            }
        }
    }

    /// Permanently delete a session (no recovery)
    func permanentlyDeleteSession(_ session: ChatSession) {
        // Use existing deleteSession for permanent deletion
        deleteSession(session)
    }

    /// Empty the trash (permanently delete all deleted sessions)
    func emptyTrash() {
        let deletedSessions = sessions.filter { $0.status == .deleted }

        for session in deletedSessions {
            deleteSession(session)
        }

        logger.info("Emptied trash: \(deletedSessions.count) sessions permanently deleted")
    }

    // MARK: - Intelligent Routing (Phase 4)

    /// Determine which model to use for a query
    /// Checks per-session override first, then global mode.
    /// Uses orchestrator in "intelligent" mode, manual selection otherwise
    private func determineModelForQuery(_ query: String, sessionId: String) async -> String {
        // Check per-session override first
        let effectiveMode: String
        let effectiveModelId: String?

        if let localId = currentSession?.id, let override = sessionModelOverrides[localId] {
            effectiveMode = override.mode
            effectiveModelId = override.modelId
            logger.debug("Using per-session override: mode=\(effectiveMode)")
        } else {
            effectiveMode = selectedMode
            effectiveModelId = selectedModelId
        }

        // Check mode
        if effectiveMode == "manual" {
            // Manual mode: use specifically selected model
            if let modelId = effectiveModelId {
                logger.debug("Manual mode: Using selected model \(modelId)")
                return modelId
            } else {
                // Fallback to default
                let fallback = defaultModel
                logger.debug("Manual mode but no model selected, using default: \(fallback)")
                return fallback
            }
        }

        // Intelligent mode: check if orchestrator routing is enabled
        let enableAppleFM = UserDefaults.standard.bool(forKey: "enableAppleFM")
        guard enableAppleFM else {
            let model = taskSpecificModel(for: query)
            logger.debug("Intelligent routing disabled, using task-specific model: \(model)")
            return model
        }

        // Use orchestrator
        logger.debug("Intelligent mode: Using orchestrator to determine best model")

        do {
            // Build context bundle
            let bundle = await buildContextBundle(query: query, sessionId: sessionId)

            // Get orchestrator
            let manager = OrchestratorManager.shared
            guard let orchestrator = await manager.getActiveOrchestrator() else {
                let model = taskSpecificModel(for: query)
                logger.warning("No orchestrator available, using task-specific model: \(model)")
                return model
            }

            // Route with orchestrator
            let decision = try await orchestrator.route(bundle: bundle)

            logger.info("Orchestrator decision - Model: \(decision.selectedModelName), Confidence: \(Int(decision.confidence * 100))%, Reasoning: \(decision.reasoning)")

            return decision.selectedModelId

        } catch {
            let model = taskSpecificModel(for: query)
            logger.error("Orchestrator routing failed: \(error), using task-specific model: \(model)")
            return model
        }
    }

    /// Select model based on query task type using Settings → Models configuration
    private func taskSpecificModel(for query: String) -> String {
        let defaults = UserDefaults.standard
        let lowered = query.lowercased()

        // Data/SQL queries
        let dataKeywords = ["sql", "query", "database", "table", "select", "insert", "data"]
        if dataKeywords.contains(where: { lowered.contains($0) }) {
            if let dataModel = defaults.string(forKey: "dataQueryModel"), !dataModel.isEmpty {
                return dataModel
            }
        }

        // Code tasks
        let codeKeywords = ["code", "function", "implement", "debug", "refactor", "fix", "compile", "swift", "python"]
        if codeKeywords.contains(where: { lowered.contains($0) }) {
            if let codeModel = defaults.string(forKey: "codeModel"), !codeModel.isEmpty {
                return codeModel
            }
        }

        // General chat — use chat model or default
        if let chatModel = defaults.string(forKey: "chatModel"), !chatModel.isEmpty {
            return chatModel
        }

        return defaultModel
    }

    /// Build context bundle for orchestrator routing
    private func buildContextBundle(query: String, sessionId: String) async -> ContextBundle {
        // Convert messages to ConversationMessage format
        let conversationHistory = messages.map { msg in
            ConversationMessage(
                id: msg.id.uuidString,
                role: msg.role == .user ? "user" : "assistant",
                content: msg.content,
                modelId: msg.modelId,
                timestamp: msg.createdAt,
                tokenCount: nil
            )
        }

        // MedStation: single model (MedGemma)
        let bundledModels: [AvailableModel] = availableModels.map { modelName in
            AvailableModel(
                id: modelName,
                name: modelName,
                displayName: "MedGemma 1.5 4B",
                slotNumber: nil,
                isPinned: true,
                memoryUsageGB: nil,
                capabilities: ModelCapabilities(
                    chat: true,
                    codeGeneration: false,
                    dataAnalysis: false,
                    reasoning: true,
                    maxContextTokens: 8192,
                    specialized: "medical"
                ),
                isHealthy: true
            )
        }

        return ContextBundle(
            userQuery: query,
            sessionId: sessionId,
            workspaceType: "medical",
            conversationHistory: conversationHistory,
            totalMessagesInSession: messages.count,
            ragDocuments: nil,
            vectorSearchResults: nil,
            userPreferences: .default,
            activeModelId: selectedModelId,
            systemResources: .default,
            availableModels: bundledModels,
            bundledAt: Date(),
            ttl: 60
        )
    }

    // MARK: - Messaging

    /// Maximum allowed message length (characters)
    /// Prevents extremely long messages that could cause memory/API issues
    private static let maxMessageLength = 100_000  // 100KB text is generous

    func sendMessage(_ text: String, contextPrompt: String? = nil) async {
        // Input validation
        let trimmedText = text.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !trimmedText.isEmpty else {
            // Silently ignore empty messages (UI should prevent this)
            return
        }

        guard trimmedText.count <= Self.maxMessageLength else {
            error = .sendFailed("Message too long (max \(Self.maxMessageLength / 1000)K characters)")
            return
        }

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

        // Add user message (use trimmed text)
        let userMessage = ChatMessage(
            role: .user,
            content: trimmedText,
            sessionId: session.id
        )
        messages.append(userMessage)

        // Send to backend with streaming
        isLoading = true
        isStreaming = true
        error = nil

        do {
            // Determine which model to use (intelligent routing or manual)
            let modelToUse = await determineModelForQuery(trimmedText, sessionId: backendSessionId)

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
                content: trimmedText,
                model: modelToUse,
                contextPrompt: contextPrompt
            )

            // Store context for semantic search (fire and forget)
            storeMessageContext(
                sessionId: session.id,
                userQuery: trimmedText,
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
        model: String,
        contextPrompt: String? = nil
    ) async throws -> String {
        // Build request
        let request = try buildMessageRequest(
            sessionId: sessionId,
            content: content,
            model: model,
            contextPrompt: contextPrompt
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
        model: String,
        contextPrompt: String? = nil
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

        var requestBody: [String: Any] = [
            "content": content,
            "model": model
        ]

        // Model generation parameters from Settings → Models
        let defaults = UserDefaults.standard
        let temperature = defaults.double(forKey: "defaultTemperature")
        if temperature > 0 { requestBody["temperature"] = temperature }

        let topP = defaults.double(forKey: "defaultTopP")
        if topP > 0 { requestBody["top_p"] = topP }

        let topK = defaults.integer(forKey: "defaultTopK")
        if topK > 0 { requestBody["top_k"] = topK }

        let repeatPenalty = defaults.double(forKey: "defaultRepeatPenalty")
        if repeatPenalty > 0 { requestBody["repeat_penalty"] = repeatPenalty }

        // System prompt: global + optional workspace context
        var systemPromptParts: [String] = []

        if defaults.bool(forKey: "enableGlobalPrompt") {
            let globalPrompt = defaults.string(forKey: "globalSystemPrompt") ?? ""
            if !globalPrompt.isEmpty {
                systemPromptParts.append(globalPrompt)
            }
        }

        if let contextPrompt, !contextPrompt.isEmpty {
            systemPromptParts.append(contextPrompt)
        }

        if !systemPromptParts.isEmpty {
            requestBody["system_prompt"] = systemPromptParts.joined(separator: "\n\n")
        }

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
            guard let jsonData = jsonString.data(using: .utf8) else { continue }
            let dict: [String: Any]
            do {
                guard let parsed = try JSONSerialization.jsonObject(with: jsonData) as? [String: Any] else { continue }
                dict = parsed
            } catch {
                logger.debug("Failed to parse streaming JSON chunk: \(error.localizedDescription)")
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

    /// Store message context (context bridge removed — no-op)
    private func storeMessageContext(
        sessionId: UUID,
        userQuery: String,
        response: String,
        model: String
    ) {
        // Context indexing removed (non-medical feature)
    }

    /// Analyze an image and return context string for AI prompts.
    /// Call this before sending a message when the user attaches an image.
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

struct ModelResponse: Codable, Sendable {
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
