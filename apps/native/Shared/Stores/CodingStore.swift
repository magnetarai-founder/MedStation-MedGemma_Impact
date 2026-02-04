//
//  CodingStore.swift
//  MagnetarStudio
//
//  Central state management for the Coding workspace.
//  Manages terminal sessions, code context, and AI assistant state.
//

import Foundation
import Observation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "CodingStore")

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
    var workingDirectory: String?

    /// Terminal context history (for AI consumption)
    var contextHistory: [TerminalContext] = []

    // MARK: - UserDefaults Keys

    private static let preferredTerminalKey = "coding.preferredTerminal"
    private static let showAIAssistantKey = "coding.showAIAssistant"
    private static let autoInjectContextKey = "coding.autoInjectContext"

    // MARK: - Dependencies

    @ObservationIgnored
    private let terminalBridge: TerminalBridgeService

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

        logger.info("[CodingStore] Initialized with preferred terminal: \(self.preferredTerminal.displayName)")
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

    // MARK: - AI Assistant

    /// Send message to AI assistant
    func sendToAssistant(_ message: String) async {
        // Add user message
        let userMessage = AIAssistantMessage(role: .user, content: message)
        aiAssistant.messages.append(userMessage)
        aiAssistant.isStreaming = true
        aiAssistant.error = nil

        // Include pending terminal context
        let contextMessages = aiAssistant.pendingContext.map { ctx in
            AIAssistantMessage(
                role: .system,
                content: "Terminal context:\n\(ctx.summary)",
                terminalContext: ctx
            )
        }

        // Clear pending context after sending
        clearPendingContext()

        do {
            // Build prompt with context
            var prompt = message
            if !contextMessages.isEmpty {
                let contextStr = contextMessages.map { $0.content }.joined(separator: "\n\n")
                prompt = "Context:\n\(contextStr)\n\nUser query: \(message)"
            }

            // Stream response (integrate with existing chat infrastructure)
            let response = try await streamAIResponse(prompt: prompt)

            let assistantMessage = AIAssistantMessage(role: .assistant, content: response)
            aiAssistant.messages.append(assistantMessage)

        } catch {
            aiAssistant.error = error.localizedDescription
            logger.error("[CodingStore] AI error: \(error)")
        }

        aiAssistant.isStreaming = false
    }

    /// Stream AI response (placeholder - will integrate with ChatStore/OrchestratorManager)
    private func streamAIResponse(prompt: String) async throws -> String {
        // TODO: Integrate with OrchestratorManager for intelligent model routing
        // For now, return placeholder
        try await Task.sleep(nanoseconds: 500_000_000)  // Simulate delay
        return "AI response will be integrated with the orchestrator system."
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
