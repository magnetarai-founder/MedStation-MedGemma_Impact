//
//  CodingStore.swift
//  MagnetarStudio
//
//  Central state management for the Coding workspace.
//  Manages terminal sessions, code context, and AI assistant state.
//  Enhanced in Phase 4 with ContextBridgeDelegate integration.
//

import Foundation
import Observation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "CodingStore")

// MARK: - Context Bridge Adapter

/// Adapter to bridge MainActor CodingStore with actor-isolated ContextBridgeService
final class CodingStoreContextAdapter: ContextBridgeDelegate, @unchecked Sendable {
    private weak var store: CodingStore?

    init(store: CodingStore) {
        self.store = store
    }

    func contextBridge(_ bridge: ContextBridgeService, didReceiveContext context: ChatReadyContext) async {
        await MainActor.run {
            store?.handleReceivedContext(context)
        }
    }

    func contextBridge(_ bridge: ContextBridgeService, shouldExecuteCommand command: ExecutableCommand) async -> Bool {
        await MainActor.run {
            store?.handleCommandExecutionRequest(command) ?? false
        }
    }
}

// MARK: - Terminal Session Model

/// Represents a native terminal session with context tracking
struct CodingTerminalSession: Identifiable, Sendable {
    let id: UUID
    let terminalApp: TerminalApp
    let workingDirectory: String
    var isActive: Bool
    var lastCommand: String?
    var lastOutput: String?
    var exitCode: Int?
    let createdAt: Date
    var updatedAt: Date

    init(
        id: UUID = UUID(),
        terminalApp: TerminalApp,
        workingDirectory: String,
        isActive: Bool = true,
        lastCommand: String? = nil,
        lastOutput: String? = nil,
        exitCode: Int? = nil,
        createdAt: Date = Date(),
        updatedAt: Date = Date()
    ) {
        self.id = id
        self.terminalApp = terminalApp
        self.workingDirectory = workingDirectory
        self.isActive = isActive
        self.lastCommand = lastCommand
        self.lastOutput = lastOutput
        self.exitCode = exitCode
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }
}

// TerminalApp enum is defined in TerminalBridgeService.swift

// MARK: - Terminal Context

/// Context captured from terminal for AI assistance
struct TerminalContext: Sendable {
    let command: String
    let output: String
    let exitCode: Int
    let workingDirectory: String
    let timestamp: Date

    /// Whether this context indicates an error
    var isError: Bool {
        exitCode != 0
    }

    /// Brief summary for AI context injection
    var summary: String {
        if isError {
            return "Command failed (exit \(exitCode)): `\(command)`\nOutput: \(output.prefix(500))"
        } else {
            return "Command succeeded: `\(command)`\nOutput: \(output.prefix(200))"
        }
    }
}

// MARK: - AI Assistant State

/// State for the integrated AI assistant panel
struct AIAssistantState: Sendable {
    var messages: [AIAssistantMessage] = []
    var isStreaming: Bool = false
    var error: String?
    var pendingContext: [TerminalContext] = []
}

struct AIAssistantMessage: Identifiable, Sendable {
    let id: UUID
    let role: MessageRole
    var content: String
    let timestamp: Date
    var terminalContext: TerminalContext?

    enum MessageRole: String, Sendable {
        case user
        case assistant
        case system
    }

    init(
        id: UUID = UUID(),
        role: MessageRole,
        content: String,
        timestamp: Date = Date(),
        terminalContext: TerminalContext? = nil
    ) {
        self.id = id
        self.role = role
        self.content = content
        self.timestamp = timestamp
        self.terminalContext = terminalContext
    }
}

// MARK: - CodingStore

/// Central state management for Coding workspace
/// Manages terminal sessions, code context, and AI assistant state
@MainActor
@Observable
final class CodingStore {
    // MARK: - Singleton

    static let shared = CodingStore()

    // MARK: - State

    /// Active terminal sessions
    var terminalSessions: [CodingTerminalSession] = []

    /// Currently focused terminal session
    var activeTerminalId: UUID?

    /// Preferred terminal application
    var preferredTerminal: TerminalApp = .warp {
        didSet {
            UserDefaults.standard.set(preferredTerminal.rawValue, forKey: Self.preferredTerminalKey)
        }
    }

    /// AI Assistant state
    var aiAssistant: AIAssistantState = AIAssistantState()

    /// Show AI assistant panel
    var showAIAssistant: Bool = true {
        didSet {
            UserDefaults.standard.set(showAIAssistant, forKey: Self.showAIAssistantKey)
        }
    }

    /// Auto-inject terminal context to AI
    var autoInjectContext: Bool = true {
        didSet {
            UserDefaults.standard.set(autoInjectContext, forKey: Self.autoInjectContextKey)
        }
    }

    /// Current working directory
    var workingDirectory: String? {
        didSet {
            if let dir = workingDirectory, dir != oldValue {
                triggerCodeIndexing(directory: dir)
            }
        }
    }

    /// Terminal context history (for AI consumption)
    var contextHistory: [TerminalContext] = []

    /// Code indexing state
    var isCodeIndexing: Bool = false
    var indexedFileCount: Int = 0

    // MARK: - UserDefaults Keys

    private static let preferredTerminalKey = "coding.preferredTerminal"
    private static let showAIAssistantKey = "coding.showAIAssistant"
    private static let autoInjectContextKey = "coding.autoInjectContext"

    // MARK: - Dependencies

    @ObservationIgnored
    private let terminalBridge: TerminalBridgeService

    @ObservationIgnored
    private var contextAdapter: CodingStoreContextAdapter?

    /// Pending command awaiting user confirmation
    var pendingCommand: ExecutableCommand?

    /// Show command confirmation dialog
    var showCommandConfirmation: Bool = false

    // MARK: - Init

    init(terminalBridge: TerminalBridgeService = .shared) {
        self.terminalBridge = terminalBridge

        // Restore preferences
        if let savedTerminal = UserDefaults.standard.string(forKey: Self.preferredTerminalKey),
           let terminal = TerminalApp(rawValue: savedTerminal) {
            self.preferredTerminal = terminal
        }

        self.showAIAssistant = UserDefaults.standard.bool(forKey: Self.showAIAssistantKey)

        // Default to true if not set
        if !UserDefaults.standard.contains(key: Self.autoInjectContextKey) {
            self.autoInjectContext = true
        } else {
            self.autoInjectContext = UserDefaults.standard.bool(forKey: Self.autoInjectContextKey)
        }

        // Set up context bridge delegation
        setupContextBridge()

        logger.info("[CodingStore] Initialized with preferred terminal: \(self.preferredTerminal.displayName)")
    }

    private func setupContextBridge() {
        contextAdapter = CodingStoreContextAdapter(store: self)
        Task {
            await ContextBridgeService.shared.setDelegate(contextAdapter)
            await ContextBridgeService.shared.configure(
                autoInjectErrors: autoInjectContext,
                autoInjectSuccess: false
            )
        }
    }

    // MARK: - Terminal Management

    /// Spawn a new terminal session
    func spawnTerminal(in app: TerminalApp? = nil, cwd: String? = nil) async throws -> CodingTerminalSession {
        let terminalApp = app ?? preferredTerminal
        let directory = cwd ?? workingDirectory ?? FileManager.default.currentDirectoryPath

        // Request terminal spawn via bridge
        try await terminalBridge.spawnTerminal(app: terminalApp, cwd: directory)

        // Create session record
        let session = CodingTerminalSession(
            terminalApp: terminalApp,
            workingDirectory: directory
        )

        terminalSessions.append(session)
        activeTerminalId = session.id

        logger.info("[CodingStore] Spawned \(terminalApp.displayName) in \(directory)")
        return session
    }

    /// Execute a command in the active terminal
    func executeCommand(_ command: String) async throws {
        guard let sessionId = activeTerminalId,
              let session = terminalSessions.first(where: { $0.id == sessionId }) else {
            throw CodingError.noActiveTerminal
        }

        try await terminalBridge.executeCommand(command, in: session.terminalApp)

        // Update session
        if let index = terminalSessions.firstIndex(where: { $0.id == sessionId }) {
            terminalSessions[index].lastCommand = command
            terminalSessions[index].updatedAt = Date()
        }

        logger.info("[CodingStore] Executed: \(command)")
    }

    /// Capture current terminal output
    func captureTerminalOutput() async throws -> String {
        guard let sessionId = activeTerminalId,
              let session = terminalSessions.first(where: { $0.id == sessionId }) else {
            throw CodingError.noActiveTerminal
        }

        let output = try await terminalBridge.captureOutput(from: session.terminalApp)

        // Update session
        if let index = terminalSessions.firstIndex(where: { $0.id == sessionId }) {
            terminalSessions[index].lastOutput = output
            terminalSessions[index].updatedAt = Date()
        }

        return output
    }

    // MARK: - Context Management

    /// Record terminal context for AI consumption
    func recordTerminalContext(_ context: TerminalContext) {
        contextHistory.append(context)

        // Keep last 50 contexts
        if contextHistory.count > 50 {
            contextHistory.removeFirst()
        }

        // Auto-inject to AI if enabled
        if autoInjectContext {
            aiAssistant.pendingContext.append(context)
            logger.debug("[CodingStore] Context queued for AI: \(context.command)")
        }

        // Notify context bridge
        Task {
            await ContextBridgeService.shared.onTerminalContext(context)
        }
    }

    /// Get relevant context for AI query
    func getRelevantContext(for query: String, limit: Int = 5) -> [TerminalContext] {
        // Return most recent contexts (could be enhanced with semantic matching)
        return Array(contextHistory.suffix(limit))
    }

    /// Clear pending AI context
    func clearPendingContext() {
        aiAssistant.pendingContext.removeAll()
    }

    // MARK: - Code Indexing

    /// Trigger background code indexing for a workspace directory
    private func triggerCodeIndexing(directory: String) {
        Task {
            isCodeIndexing = true
            do {
                let stats = try await CodeRAGService.shared.indexWorkspace(at: directory)
                indexedFileCount = CodeRAGService.shared.indexedFileCount
                logger.info("[CodingStore] Indexed \(stats.filesIndexed) files (\(stats.totalDocuments) chunks)")
            } catch {
                logger.error("[CodingStore] Code indexing failed: \(error)")
            }
            isCodeIndexing = false
        }
    }

    /// Manually refresh the code index
    func refreshCodeIndex() {
        guard let dir = workingDirectory else { return }
        triggerCodeIndexing(directory: dir)
    }

    // MARK: - AI Assistant

    /// Send message to AI assistant using orchestrated model routing
    func sendToAssistant(_ message: String) async {
        // Add user message
        let userMessage = AIAssistantMessage(role: .user, content: message)
        aiAssistant.messages.append(userMessage)
        aiAssistant.isStreaming = true
        aiAssistant.error = nil

        // Capture pending terminal context before clearing
        let terminalContexts = aiAssistant.pendingContext
        clearPendingContext()

        do {
            let orchestrator = CodingModelOrchestrator.shared

            // Build orchestrated request with structured context
            let request = OrchestratedRequest(
                query: message,
                terminalContext: terminalContexts,
                codeContext: nil,  // TODO: Inject from active editor
                mode: orchestrator.currentMode
            )

            let response = try await orchestrator.orchestrate(request)

            // Build assistant message with model attribution
            var content = response.content
            if response.mode != .single {
                content += "\n\n---\n*\\(response.modelUsed) via \\(response.mode.rawValue)*"
            }

            let assistantMessage = AIAssistantMessage(role: .assistant, content: content)
            aiAssistant.messages.append(assistantMessage)

            logger.info("[CodingStore] AI response via \(response.mode.rawValue) in \(response.executionTimeMs)ms")

        } catch {
            aiAssistant.error = error.localizedDescription
            logger.error("[CodingStore] AI error: \(error)")
        }

        aiAssistant.isStreaming = false
    }

    /// Clear AI assistant messages
    func clearAssistant() {
        aiAssistant.messages.removeAll()
        aiAssistant.error = nil
    }

    /// Execute AI-suggested command
    func executeAICommand(_ command: String) async throws {
        // Log to assistant
        let commandMessage = AIAssistantMessage(
            role: .system,
            content: "Executing: `\(command)`"
        )
        aiAssistant.messages.append(commandMessage)

        // Execute
        try await executeCommand(command)
    }

    // MARK: - Context Bridge Handlers

    /// Handle context received from ContextBridgeService
    func handleReceivedContext(_ context: ChatReadyContext) {
        logger.debug("[CodingStore] Received context from bridge: \(context.summary)")

        // Add system message to AI assistant
        let message = AIAssistantMessage(
            role: .system,
            content: formatContextForAssistant(context)
        )
        aiAssistant.messages.append(message)

        // If it's an error context, parse it for suggestions
        if context.source == .terminal,
           let command = context.metadata["command"],
           let exitCodeStr = context.metadata["exitCode"],
           let exitCode = Int(exitCodeStr),
           exitCode != 0 {
            // Parse the terminal context for intelligent suggestions
            Task {
                let terminalContext = TerminalContext(
                    command: command,
                    output: context.content,
                    exitCode: exitCode,
                    workingDirectory: context.metadata["workingDirectory"] ?? "~",
                    timestamp: context.timestamp
                )

                let enriched = await TerminalContextParser.shared.parse(terminalContext)

                await MainActor.run {
                    handleEnrichedContext(enriched)
                }
            }
        }
    }

    /// Handle enriched context with parsed errors
    private func handleEnrichedContext(_ enriched: EnrichedTerminalContext) {
        guard enriched.hasActionableErrors else { return }

        // Add error analysis to assistant
        var analysisMessage = "**Error Analysis:**\n"
        for error in enriched.parsedErrors.prefix(3) {
            analysisMessage += "• [\(error.category.rawValue)] \(error.summary)\n"
            if let fix = error.suggestedFixes.first {
                analysisMessage += "  → Suggested: \(fix.description)"
                if let cmd = fix.command {
                    analysisMessage += " (`\(cmd)`)"
                }
                analysisMessage += "\n"
            }
        }

        let message = AIAssistantMessage(
            role: .assistant,
            content: analysisMessage
        )
        aiAssistant.messages.append(message)

        logger.info("[CodingStore] Added error analysis with \(enriched.parsedErrors.count) detected errors")
    }

    /// Format context for AI assistant display
    private func formatContextForAssistant(_ context: ChatReadyContext) -> String {
        switch context.source {
        case .terminal:
            return "📟 **Terminal Context**\n\(context.summary)"
        case .codeEditor:
            return "📝 **Code Context**\n\(context.summary)"
        case .fileSystem:
            return "📁 **File System Context**\n\(context.summary)"
        case .aiAssistant:
            return context.content
        }
    }

    /// Handle command execution request from AI
    func handleCommandExecutionRequest(_ command: ExecutableCommand) -> Bool {
        logger.info("[CodingStore] Command execution request: \(command.command)")

        if command.requiresConfirmation {
            // Store pending command and show confirmation dialog
            pendingCommand = command
            showCommandConfirmation = true
            return false  // Don't execute yet
        } else {
            // Execute immediately
            Task {
                do {
                    try await executeAICommand(command.command)
                } catch {
                    logger.error("[CodingStore] Command execution failed: \(error)")
                }
            }
            return true
        }
    }

    /// Confirm and execute pending command
    func confirmPendingCommand() async {
        guard let command = pendingCommand else { return }

        showCommandConfirmation = false
        pendingCommand = nil

        do {
            try await executeAICommand(command.command)
        } catch {
            logger.error("[CodingStore] Confirmed command failed: \(error)")
            aiAssistant.error = error.localizedDescription
        }
    }

    /// Cancel pending command
    func cancelPendingCommand() {
        pendingCommand = nil
        showCommandConfirmation = false

        let message = AIAssistantMessage(
            role: .system,
            content: "Command cancelled by user"
        )
        aiAssistant.messages.append(message)
    }
}

// MARK: - Errors

enum CodingError: LocalizedError {
    case noActiveTerminal
    case terminalNotFound(TerminalApp)
    case executionFailed(String)
    case captureFailed(String)

    var errorDescription: String? {
        switch self {
        case .noActiveTerminal:
            return "No active terminal session. Please spawn a terminal first."
        case .terminalNotFound(let app):
            return "\(app.displayName) is not installed or not running."
        case .executionFailed(let message):
            return "Command execution failed: \(message)"
        case .captureFailed(let message):
            return "Failed to capture terminal output: \(message)"
        }
    }
}

// MARK: - UserDefaults Extension

extension UserDefaults {
    func contains(key: String) -> Bool {
        return object(forKey: key) != nil
    }
}
