//
//  ContextBridgeService.swift
//  MagnetarStudio
//
//  Bidirectional context sharing between Terminal and Chat.
//  Enables zero copy-paste workflow with intelligent context injection.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "ContextBridge")

// MARK: - Context Types

/// Terminal context ready for chat injection
struct ChatReadyContext: Sendable {
    let source: ContextSource
    let content: String
    let summary: String
    let timestamp: Date
    let metadata: [String: String]

    public enum ContextSource: String, Sendable {
        case terminal
        case codeEditor
        case fileSystem
        case aiAssistant
    }

    init(
        source: ContextSource,
        content: String,
        summary: String,
        timestamp: Date = Date(),
        metadata: [String: String] = [:]
    ) {
        self.source = source
        self.content = content
        self.summary = summary
        self.timestamp = timestamp
        self.metadata = metadata
    }
}

/// AI command ready for terminal execution
struct ExecutableCommand: Sendable {
    let command: String
    let explanation: String
    let confidence: Float
    let requiresConfirmation: Bool
    let workingDirectory: String?

    init(
        command: String,
        explanation: String,
        confidence: Float = 1.0,
        requiresConfirmation: Bool = false,
        workingDirectory: String? = nil
    ) {
        self.command = command
        self.explanation = explanation
        self.confidence = confidence
        self.requiresConfirmation = requiresConfirmation
        self.workingDirectory = workingDirectory
    }
}

// MARK: - Context Bridge Delegate

/// Protocol for receiving context updates
protocol ContextBridgeDelegate: AnyObject, Sendable {
    /// Called when terminal context should be injected to chat
    func contextBridge(_ bridge: ContextBridgeService, didReceiveContext context: ChatReadyContext) async

    /// Called when AI suggests a command for terminal execution
    func contextBridge(_ bridge: ContextBridgeService, shouldExecuteCommand command: ExecutableCommand) async -> Bool
}

// MARK: - ContextBridgeService

/// Service for bidirectional context sharing between Terminal and Chat
/// Enables zero copy-paste workflow with intelligent context injection
actor ContextBridgeService {
    // MARK: - Singleton

    static let shared = ContextBridgeService()

    // MARK: - Properties

    /// Delegate for receiving context updates
    private weak var delegate: (any ContextBridgeDelegate)?

    /// Context history for retrieval
    private var contextHistory: [ChatReadyContext] = []

    /// Pending commands from AI
    private var pendingCommands: [ExecutableCommand] = []

    /// Maximum context history size
    private let maxHistorySize = 100

    /// Auto-inject terminal errors to chat
    private var autoInjectErrors: Bool = true

    /// Auto-inject successful outputs (when explicitly requested)
    private var autoInjectSuccess: Bool = false

    // MARK: - Configuration

    /// Set the delegate for context updates
    func setDelegate(_ delegate: (any ContextBridgeDelegate)?) {
        self.delegate = delegate
    }

    /// Configure auto-injection settings
    func configure(autoInjectErrors: Bool, autoInjectSuccess: Bool) {
        self.autoInjectErrors = autoInjectErrors
        self.autoInjectSuccess = autoInjectSuccess
    }

    // MARK: - Terminal → Chat

    /// Process terminal context and optionally inject to chat
    func onTerminalContext(_ context: TerminalContext) async {
        // Create chat-ready context
        let chatContext = ChatReadyContext(
            source: .terminal,
            content: formatTerminalContext(context),
            summary: context.summary,
            timestamp: context.timestamp,
            metadata: [
                "command": context.command,
                "exitCode": String(context.exitCode),
                "workingDirectory": context.workingDirectory
            ]
        )

        // Store in history
        addToHistory(chatContext)

        // Auto-inject based on configuration
        let shouldInject = (context.isError && autoInjectErrors) ||
                          (!context.isError && autoInjectSuccess)

        if shouldInject {
            await delegate?.contextBridge(self, didReceiveContext: chatContext)
            logger.debug("[ContextBridge] Auto-injected terminal context to chat")
        }
    }

    /// Format terminal context for chat consumption
    private func formatTerminalContext(_ context: TerminalContext) -> String {
        var formatted = """
        ## Terminal Command
        ```bash
        $ \(context.command)
        ```

        **Working Directory:** `\(context.workingDirectory)`
        **Exit Code:** \(context.exitCode)\(context.isError ? " (Error)" : "")

        """

        if !context.output.isEmpty {
            // Truncate long output
            let maxLength = 2000
            let output = context.output.count > maxLength
                ? String(context.output.prefix(maxLength)) + "\n... (truncated)"
                : context.output

            formatted += """
            ### Output
            ```
            \(output)
            ```
            """
        }

        return formatted
    }

    // MARK: - Chat → Terminal

    /// Parse AI response for executable commands
    func parseCommandsFromResponse(_ response: String) -> [ExecutableCommand] {
        var commands: [ExecutableCommand] = []

        // Look for code blocks with bash/shell/zsh using NSRegularExpression
        let pattern = "```(?:bash|shell|zsh|sh)\\n([\\s\\S]*?)```"
        guard let regex = try? NSRegularExpression(pattern: pattern, options: []) else {
            logger.warning("[ContextBridge] Failed to compile regex for code block extraction")
            return []
        }

        let range = NSRange(response.startIndex..., in: response)
        let matches = regex.matches(in: response, options: [], range: range)

        for match in matches {
            guard match.numberOfRanges > 1,
                  let commandRange = Range(match.range(at: 1), in: response) else {
                continue
            }

            let command = String(response[commandRange]).trimmingCharacters(in: .whitespacesAndNewlines)

            // Skip if empty or looks like output
            guard !command.isEmpty, !command.hasPrefix("#") else { continue }

            // Check for dangerous commands
            let isDangerous = isDangerousCommand(command)

            commands.append(ExecutableCommand(
                command: command,
                explanation: "AI suggested command",
                confidence: 0.9,
                requiresConfirmation: isDangerous
            ))
        }

        // Store as pending
        pendingCommands.append(contentsOf: commands)

        logger.debug("[ContextBridge] Parsed \(commands.count) commands from AI response")
        return commands
    }

    /// Execute a pending command
    func executeCommand(_ command: ExecutableCommand) async -> Bool {
        guard let delegate = delegate else {
            logger.warning("[ContextBridge] No delegate to execute command")
            return false
        }

        let approved = await delegate.contextBridge(self, shouldExecuteCommand: command)

        if approved {
            // Remove from pending
            pendingCommands.removeAll { $0.command == command.command }
            logger.info("[ContextBridge] Command executed: \(command.command.prefix(50))")
        }

        return approved
    }

    /// Get pending commands
    func getPendingCommands() -> [ExecutableCommand] {
        return pendingCommands
    }

    /// Clear pending commands
    func clearPendingCommands() {
        pendingCommands.removeAll()
    }

    // MARK: - Command Safety

    /// Check if a command is potentially dangerous
    private func isDangerousCommand(_ command: String) -> Bool {
        let dangerousPatterns = [
            "rm -rf",
            "rm -r /",
            "sudo rm",
            "> /dev/",
            "mkfs",
            "dd if=",
            ":(){:|:&};:",  // Fork bomb
            "chmod -R 777",
            "chmod 777 /",
            "curl | bash",
            "wget | bash",
            "sudo su",
            "sudo -i"
        ]

        let lowercased = command.lowercased()
        return dangerousPatterns.contains { lowercased.contains($0.lowercased()) }
    }

    // MARK: - Context History

    /// Add context to history
    private func addToHistory(_ context: ChatReadyContext) {
        contextHistory.append(context)

        // Trim if exceeds max size
        if contextHistory.count > maxHistorySize {
            contextHistory.removeFirst(contextHistory.count - maxHistorySize)
        }
    }

    /// Get recent context history
    func getRecentContext(limit: Int = 10) -> [ChatReadyContext] {
        return Array(contextHistory.suffix(limit))
    }

    /// Search context history
    func searchContext(query: String, limit: Int = 10) -> [ChatReadyContext] {
        let lowercasedQuery = query.lowercased()
        return contextHistory
            .filter { $0.content.lowercased().contains(lowercasedQuery) ||
                      $0.summary.lowercased().contains(lowercasedQuery) }
            .suffix(limit)
            .reversed()
            .map { $0 }
    }

    /// Clear context history
    func clearHistory() {
        contextHistory.removeAll()
    }

    // MARK: - Code Editor Context

    /// Add code editor context (selected code, file info)
    func addCodeContext(
        code: String,
        fileName: String,
        language: String,
        lineRange: ClosedRange<Int>? = nil
    ) async {
        let lineInfo = lineRange.map { "lines \($0.lowerBound)-\($0.upperBound)" } ?? ""

        let summary = "Code from \(fileName)\(lineInfo.isEmpty ? "" : " (\(lineInfo))")"

        let context = ChatReadyContext(
            source: .codeEditor,
            content: """
            ## Code Context
            **File:** `\(fileName)` \(lineInfo)
            **Language:** \(language)

            ```\(language)
            \(code)
            ```
            """,
            summary: summary,
            metadata: [
                "fileName": fileName,
                "language": language,
                "lineRange": lineInfo
            ]
        )

        addToHistory(context)
        await delegate?.contextBridge(self, didReceiveContext: context)
    }

    // MARK: - File System Context

    /// Add file system context (directory listing, file info)
    func addFileSystemContext(
        path: String,
        type: String,
        info: String
    ) async {
        let context = ChatReadyContext(
            source: .fileSystem,
            content: """
            ## File System Context
            **Path:** `\(path)`
            **Type:** \(type)

            \(info)
            """,
            summary: "\(type) at \(path)",
            metadata: [
                "path": path,
                "type": type
            ]
        )

        addToHistory(context)
        await delegate?.contextBridge(self, didReceiveContext: context)
    }
}
