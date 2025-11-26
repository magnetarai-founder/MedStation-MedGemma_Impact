import Foundation
import Combine

/// Network-backed chat store with streaming support
@MainActor
final class NetworkChatStore: ObservableObject {
    static let shared = NetworkChatStore()

    // MARK: - Published State

    @Published var sessions: [ApiChatSession] = []
    @Published var activeSession: ApiChatSession?
    @Published var messages: [ApiChatMessage] = []
    @Published var streamingContent: String = ""
    @Published var isSending = false
    @Published var isLoading = false
    @Published var error: String?
    @Published var selectedModel: String = "mistral"
    @Published var tokensUsed: Int = 0
    @Published var tokensLimit: Int?

    private let service = ChatService.shared
    private var streamingTask: ApiClient.StreamingTask?
    private var pendingFiles: [ChatFile] = []

    private init() {}

    // MARK: - Session Management

    func bootstrapSessions() async {
        isLoading = true
        defer { isLoading = false }

        do {
            sessions = try await service.listSessions()

            // Select most recent session if available
            if activeSession == nil, let latest = sessions.first {
                activeSession = latest
                selectedModel = latest.model ?? "mistral"
            }

            error = nil
        } catch {
            self.error = "Failed to load sessions: \(error.localizedDescription)"
        }
    }

    func createSession(title: String? = nil, model: String? = nil) async {
        isLoading = true
        defer { isLoading = false }

        do {
            let session = try await service.createSession(
                title: title,
                model: model ?? selectedModel
            )

            sessions.insert(session, at: 0)
            activeSession = session
            messages = []
            selectedModel = session.model ?? selectedModel

            error = nil
        } catch {
            self.error = "Failed to create session: \(error.localizedDescription)"
        }
    }

    func selectSession(_ session: ApiChatSession) async {
        activeSession = session
        selectedModel = session.model ?? selectedModel
        messages = []
        streamingContent = ""

        // Load messages from backend
        await loadMessages(sessionId: session.id)
    }

    // MARK: - Message Loading

    func loadMessages(sessionId: String, limit: Int? = nil) async {
        isLoading = true
        error = nil

        do {
            let loadedMessages = try await service.loadMessages(sessionId: sessionId, limit: limit)
            messages = loadedMessages
            error = nil
        } catch {
            self.error = "Failed to load messages: \(error.localizedDescription)"
            messages = []
        }

        isLoading = false
    }

    // MARK: - File Upload

    func uploadFile(url: URL) async -> ChatFile? {
        guard let sessionId = activeSession?.id else {
            error = "No active session"
            return nil
        }

        do {
            let file = try await service.uploadAttachment(sessionId: sessionId, fileURL: url)
            error = nil
            return file
        } catch {
            self.error = "Upload failed: \(error.localizedDescription)"
            return nil
        }
    }

    // MARK: - Send Message

    func sendMessage(
        content: String,
        files: [URL] = [],
        temperature: Double? = 0.7,
        topP: Double? = 0.9,
        topK: Int? = 40,
        repeatPenalty: Double? = 1.1,
        systemPrompt: String? = nil
    ) async {
        guard let sessionId = activeSession?.id else {
            error = "No active session"
            return
        }

        if isSending { return }

        isSending = true
        streamingContent = ""

        do {
            // 1. Upload files first
            var uploadedFiles: [ChatFile] = []
            for fileURL in files {
                if let file = await uploadFile(url: fileURL) {
                    uploadedFiles.append(file)
                }
            }

            // 2. Append user message locally
            let userMessage = ApiChatMessage(
                id: UUID().uuidString,
                role: "user",
                content: content,
                timestamp: ISO8601DateFormatter().string(from: Date()),
                model: selectedModel,
                tokens: nil,
                files: uploadedFiles.isEmpty ? nil : uploadedFiles
            )
            messages.append(userMessage)

            // 3. Create request
            let request = SendMessageRequest(
                content: content,
                model: selectedModel,
                temperature: temperature,
                topP: topP,
                topK: topK,
                repeatPenalty: repeatPenalty,
                systemPrompt: systemPrompt
            )

            // 4. Start streaming
            streamingTask = try service.sendMessageStream(
                sessionId: sessionId,
                request: request,
                onContent: { [weak self] chunk in
                    Task { @MainActor in
                        self?.streamingContent.append(chunk)
                    }
                },
                onDone: { [weak self] in
                    Task { @MainActor in
                        guard let self else { return }

                        // Append final assistant message
                        let assistantMessage = ApiChatMessage(
                            id: UUID().uuidString,
                            role: "assistant",
                            content: self.streamingContent,
                            timestamp: ISO8601DateFormatter().string(from: Date()),
                            model: self.selectedModel,
                            tokens: nil,
                            files: nil
                        )
                        self.messages.append(assistantMessage)

                        // Clear streaming state
                        self.streamingContent = ""
                        self.isSending = false

                        // Fetch token usage
                        await self.fetchTokens()
                    }
                },
                onError: { [weak self] err in
                    Task { @MainActor in
                        self?.error = "Send failed: \(err.localizedDescription)"
                        self?.streamingContent = ""
                        self?.isSending = false
                    }
                }
            )

            streamingTask?.task.resume()
            error = nil

        } catch {
            self.error = "Send failed: \(error.localizedDescription)"
            self.streamingContent = ""
            self.isSending = false
        }
    }

    func cancelStreaming() {
        streamingTask?.cancel()
        streamingTask = nil
        streamingContent = ""
        isSending = false
    }

    // MARK: - Model Management

    func changeModel(_ model: String) async {
        guard let sessionId = activeSession?.id else {
            error = "No active session"
            return
        }

        do {
            try await service.changeModel(sessionId: sessionId, model: model)
            selectedModel = model

            // Update active session model locally
            if sessions.firstIndex(where: { $0.id == sessionId }) != nil {
                // Note: Since ApiChatSession is immutable, we'd need to create a new one
                // For now, just update selectedModel
            }

            error = nil
        } catch {
            self.error = "Failed to change model: \(error.localizedDescription)"
        }
    }

    // MARK: - Token Tracking

    func fetchTokens() async {
        guard let sessionId = activeSession?.id else { return }

        do {
            let response = try await service.fetchTokens(sessionId: sessionId)
            tokensUsed = response.tokensUsed
            tokensLimit = response.tokensLimit
            error = nil
        } catch {
            // Silent fail for token tracking
            print("Failed to fetch tokens: \(error)")
        }
    }

    // MARK: - Health Check

    func checkHealth() async -> Bool {
        do {
            return try await service.checkHealth()
        } catch {
            return false
        }
    }
}
