//
//  TerminalBridgeService.swift
//  MagnetarStudio
//
//  Native terminal integration via AppleScript.
//  Bridges MagnetarStudio to Warp, iTerm2, and Terminal.app.
//

import Foundation
import AppKit
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "TerminalBridge")

// MARK: - Terminal App Enum

/// Supported terminal applications
enum TerminalApp: String, CaseIterable, Sendable {
    case warp = "Warp"
    case iterm = "iTerm"
    case terminal = "Terminal"

    var bundleIdentifier: String {
        switch self {
        case .warp: return "dev.warp.Warp-Stable"
        case .iterm: return "com.googlecode.iterm2"
        case .terminal: return "com.apple.Terminal"
        }
    }

    var displayName: String {
        switch self {
        case .warp: return "Warp"
        case .iterm: return "iTerm2"
        case .terminal: return "Terminal.app"
        }
    }

    var iconName: String {
        switch self {
        case .warp: return "terminal.fill"
        case .iterm: return "terminal"
        case .terminal: return "apple.terminal"
        }
    }
}

// MARK: - Terminal Output Model

/// Represents captured terminal output
struct TerminalOutput: Sendable {
    let content: String
    let source: OutputSource
    let timestamp: Date
    let terminalApp: TerminalApp?

    enum OutputSource: String, Sendable {
        case clipboard      // Captured from clipboard
        case directCapture  // Captured via AppleScript
        case notification   // From terminal notification
    }

    init(content: String, source: OutputSource, terminalApp: TerminalApp? = nil) {
        self.content = content
        self.source = source
        self.timestamp = Date()
        self.terminalApp = terminalApp
    }
}

/// Terminal event for observation
enum TerminalEvent: Sendable {
    case appLaunched(TerminalApp)
    case appTerminated(TerminalApp)
    case commandExecuted(command: String, app: TerminalApp)
    case outputCaptured(TerminalOutput)
    case clipboardChanged(String)
}

// MARK: - TerminalBridgeService

/// Actor-based service for native terminal integration
/// Uses AppleScript to control Warp, iTerm2, and Terminal.app
actor TerminalBridgeService {
    // MARK: - Singleton

    static let shared = TerminalBridgeService()

    // MARK: - Properties

    /// Detected available terminal apps
    private var availableTerminals: [TerminalApp] = []

    /// Has checked for available terminals
    private var hasDetectedTerminals = false

    /// Running terminal apps
    private var runningTerminals: Set<TerminalApp> = []

    /// Clipboard monitoring state
    private var isMonitoringClipboard = false
    private var lastClipboardContent: String = ""
    private var clipboardCheckTimer: Timer?

    /// Output stream continuations
    private var outputContinuations: [UUID: AsyncStream<TerminalOutput>.Continuation] = [:]

    /// Event stream continuations
    private var eventContinuations: [UUID: AsyncStream<TerminalEvent>.Continuation] = [:]

    // MARK: - Init

    init() {
        Task {
            await detectAvailableTerminals()
            await detectRunningTerminals()
        }
    }

    // MARK: - Output Streaming

    /// Observe terminal output as an async stream
    func observeOutput() -> AsyncStream<TerminalOutput> {
        AsyncStream { continuation in
            let id = UUID()
            Task {
                self.addOutputContinuation(id: id, continuation: continuation)
            }

            continuation.onTermination = { _ in
                Task {
                    await self.removeOutputContinuation(id: id)
                }
            }
        }
    }

    /// Observe terminal events as an async stream
    func observeEvents() -> AsyncStream<TerminalEvent> {
        AsyncStream { continuation in
            let id = UUID()
            Task {
                self.addEventContinuation(id: id, continuation: continuation)
            }

            continuation.onTermination = { _ in
                Task {
                    await self.removeEventContinuation(id: id)
                }
            }
        }
    }

    private func addOutputContinuation(id: UUID, continuation: AsyncStream<TerminalOutput>.Continuation) {
        outputContinuations[id] = continuation

        // Start clipboard monitoring if first observer
        if outputContinuations.count == 1 {
            startClipboardMonitoring()
        }
    }

    private func removeOutputContinuation(id: UUID) {
        outputContinuations.removeValue(forKey: id)

        // Stop clipboard monitoring if no observers
        if outputContinuations.isEmpty {
            stopClipboardMonitoring()
        }
    }

    private func addEventContinuation(id: UUID, continuation: AsyncStream<TerminalEvent>.Continuation) {
        eventContinuations[id] = continuation
    }

    private func removeEventContinuation(id: UUID) {
        eventContinuations.removeValue(forKey: id)
    }

    /// Emit output to all observers
    private func emitOutput(_ output: TerminalOutput) {
        for continuation in outputContinuations.values {
            continuation.yield(output)
        }
    }

    /// Emit event to all observers
    private func emitEvent(_ event: TerminalEvent) {
        for continuation in eventContinuations.values {
            continuation.yield(event)
        }
    }

    // MARK: - Clipboard Monitoring

    /// Start monitoring clipboard for terminal output
    private func startClipboardMonitoring() {
        guard !isMonitoringClipboard else { return }
        isMonitoringClipboard = true

        // Store initial clipboard content
        lastClipboardContent = NSPasteboard.general.string(forType: .string) ?? ""

        // Start periodic check (every 0.5 seconds)
        Task { @MainActor [weak self] in
            let timer = Timer.scheduledTimer(withTimeInterval: 0.5, repeats: true) { [weak self] timer in
                Task {
                    await self?.checkClipboard()
                }
            }
            await self?.setClipboardCheckTimer(timer)
        }

        logger.debug("[TerminalBridge] Started clipboard monitoring")
    }

    /// Store timer reference (actor-isolated setter for cross-actor timer creation)
    private func setClipboardCheckTimer(_ timer: Timer) {
        clipboardCheckTimer = timer
    }

    /// Stop monitoring clipboard
    private func stopClipboardMonitoring() {
        isMonitoringClipboard = false
        clipboardCheckTimer?.invalidate()
        clipboardCheckTimer = nil
        logger.debug("[TerminalBridge] Stopped clipboard monitoring")
    }

    /// Check clipboard for changes
    private func checkClipboard() {
        guard isMonitoringClipboard else { return }

        let currentContent = NSPasteboard.general.string(forType: .string) ?? ""

        if currentContent != lastClipboardContent && !currentContent.isEmpty {
            lastClipboardContent = currentContent

            // Check if it looks like terminal output
            if looksLikeTerminalOutput(currentContent) {
                let output = TerminalOutput(
                    content: currentContent,
                    source: .clipboard,
                    terminalApp: detectActiveTerminal()
                )
                emitOutput(output)
                emitEvent(.clipboardChanged(currentContent))
                logger.debug("[TerminalBridge] Captured clipboard content (\(currentContent.count) chars)")
            }
        }
    }

    /// Heuristic to detect if clipboard content looks like terminal output
    private func looksLikeTerminalOutput(_ content: String) -> Bool {
        // Check for common terminal patterns
        let terminalPatterns = [
            "^\\$\\s",           // Shell prompt
            "^>\\s",             // PowerShell/fish prompt
            "^\\[.*\\]\\$",      // Bracketed prompt
            "error:",           // Error output
            "warning:",         // Warning output
            "^\\s*\\d+:\\s",     // Line numbers
            "^fatal:",          // Git errors
            "^npm ERR!",        // npm errors
            "^\\s*at\\s+.*\\(",  // Stack traces
        ]

        for pattern in terminalPatterns {
            if let regex = try? NSRegularExpression(pattern: pattern, options: [.anchorsMatchLines, .caseInsensitive]) {
                let range = NSRange(content.startIndex..., in: content)
                if regex.firstMatch(in: content, options: [], range: range) != nil {
                    return true
                }
            }
        }

        // Also check if content has multiple lines (likely terminal output)
        let lineCount = content.components(separatedBy: .newlines).count
        return lineCount >= 3
    }

    /// Detect which terminal app is currently active
    private func detectActiveTerminal() -> TerminalApp? {
        let activeApp = NSWorkspace.shared.frontmostApplication
        guard let bundleId = activeApp?.bundleIdentifier else { return nil }

        for app in TerminalApp.allCases {
            if app.bundleIdentifier == bundleId {
                return app
            }
        }
        return nil
    }

    // MARK: - Running Terminal Detection

    /// Detect which terminal apps are currently running
    private func detectRunningTerminals() async {
        let workspace = NSWorkspace.shared
        var running: Set<TerminalApp> = []

        for app in TerminalApp.allCases {
            let runningApps = workspace.runningApplications.filter {
                $0.bundleIdentifier == app.bundleIdentifier
            }
            if !runningApps.isEmpty {
                running.insert(app)
            }
        }

        runningTerminals = running
        logger.debug("[TerminalBridge] Running terminals: \(running.map { $0.displayName })")
    }

    /// Check if a terminal app is running
    func isTerminalRunning(_ app: TerminalApp) -> Bool {
        return runningTerminals.contains(app)
    }

    /// Get all running terminal apps
    func getRunningTerminals() -> [TerminalApp] {
        return Array(runningTerminals)
    }

    // MARK: - Terminal Detection

    /// Detect which terminal apps are installed
    func detectAvailableTerminals() async {
        var available: [TerminalApp] = []

        for app in TerminalApp.allCases {
            if isTerminalInstalled(app) {
                available.append(app)
                logger.debug("[TerminalBridge] Found: \(app.displayName)")
            }
        }

        availableTerminals = available
        hasDetectedTerminals = true

        logger.info("[TerminalBridge] Detected \(available.count) terminal app(s)")
    }

    /// Check if a terminal app is installed
    private func isTerminalInstalled(_ app: TerminalApp) -> Bool {
        let workspace = NSWorkspace.shared
        return workspace.urlForApplication(withBundleIdentifier: app.bundleIdentifier) != nil
    }

    /// Get list of available terminal apps
    func getAvailableTerminals() async -> [TerminalApp] {
        if !hasDetectedTerminals {
            await detectAvailableTerminals()
        }
        return availableTerminals
    }

    /// Get the best available terminal app
    func getBestTerminal() async -> TerminalApp {
        let available = await getAvailableTerminals()

        // Prefer Warp > iTerm > Terminal.app
        if available.contains(.warp) {
            return .warp
        } else if available.contains(.iterm) {
            return .iterm
        } else {
            return .terminal  // Always available on macOS
        }
    }

    // MARK: - Terminal Operations

    /// Spawn a new terminal window/tab
    func spawnTerminal(app: TerminalApp, cwd: String? = nil) async throws {
        let script: String

        switch app {
        case .warp:
            script = warpSpawnScript(cwd: cwd)
        case .iterm:
            script = itermSpawnScript(cwd: cwd)
        case .terminal:
            script = terminalAppSpawnScript(cwd: cwd)
        }

        try await executeAppleScript(script)
        logger.info("[TerminalBridge] Spawned \(app.displayName)")
    }

    /// Execute a command in the terminal
    func executeCommand(_ command: String, in app: TerminalApp) async throws {
        let script: String

        switch app {
        case .warp:
            script = warpExecuteScript(command: command)
        case .iterm:
            script = itermExecuteScript(command: command)
        case .terminal:
            script = terminalAppExecuteScript(command: command)
        }

        try await executeAppleScript(script)

        // Emit command executed event
        emitEvent(.commandExecuted(command: command, app: app))

        logger.debug("[TerminalBridge] Executed in \(app.displayName): \(command.prefix(50))")
    }

    /// Execute a command and wait for output (with timeout)
    /// Uses clipboard capture since direct output capture is limited
    func executeAndCapture(_ command: String, in app: TerminalApp, timeout: TimeInterval = 5.0) async throws -> String {
        // Clear clipboard first
        NSPasteboard.general.clearContents()

        // Execute the command with output piped to clipboard
        let wrappedCommand: String
        switch app {
        case .warp, .iterm, .terminal:
            // Wrap command to copy output to clipboard
            wrappedCommand = "(\(command)) 2>&1 | pbcopy"
        }

        try await executeCommand(wrappedCommand, in: app)

        // Wait for clipboard to be populated
        let startTime = Date()
        while Date().timeIntervalSince(startTime) < timeout {
            try await Task.sleep(nanoseconds: 100_000_000) // 100ms

            if let content = NSPasteboard.general.string(forType: .string), !content.isEmpty {
                let output = TerminalOutput(content: content, source: .clipboard, terminalApp: app)
                emitOutput(output)
                return content
            }
        }

        throw TerminalBridgeError.captureTimeout
    }

    /// Request user to copy terminal output (for Warp which has limited AppleScript support)
    func requestOutputCapture(in app: TerminalApp) async throws {
        // Send Cmd+A (select all) then Cmd+C (copy) via System Events
        let script = """
        tell application "\(app.rawValue)"
            activate
        end tell
        delay 0.2
        tell application "System Events"
            tell process "\(app.rawValue)"
                keystroke "a" using command down
                delay 0.1
                keystroke "c" using command down
            end tell
        end tell
        """

        try await executeAppleScript(script)
        logger.debug("[TerminalBridge] Requested output capture from \(app.displayName)")

        // Give clipboard time to update
        try await Task.sleep(nanoseconds: 300_000_000) // 300ms

        // Check clipboard
        if let content = NSPasteboard.general.string(forType: .string), !content.isEmpty {
            let output = TerminalOutput(content: content, source: .directCapture, terminalApp: app)
            emitOutput(output)
        }
    }

    /// Capture output from terminal (limited support)
    func captureOutput(from app: TerminalApp) async throws -> String {
        // Note: Terminal output capture is limited by macOS security
        // Best we can do is get the visible text from the terminal window

        let script: String

        switch app {
        case .warp:
            // Warp doesn't support AppleScript content extraction well
            return "Output capture not supported for Warp. Use clipboard integration."
        case .iterm:
            script = itermCaptureScript()
        case .terminal:
            script = terminalAppCaptureScript()
        }

        let output = try await executeAppleScriptWithResult(script)
        return output ?? ""
    }

    /// Focus the terminal window
    func focusTerminal(_ app: TerminalApp) async throws {
        let script = """
        tell application "\(app.rawValue)"
            activate
        end tell
        """

        try await executeAppleScript(script)
    }

    // MARK: - AppleScript Execution

    /// Execute AppleScript without expecting a return value
    private func executeAppleScript(_ source: String) async throws {
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<Void, Error>) in
            DispatchQueue.global(qos: .userInitiated).async {
                var error: NSDictionary?
                let script = NSAppleScript(source: source)
                script?.executeAndReturnError(&error)

                if let error = error {
                    let message = error[NSAppleScript.errorMessage] as? String ?? "Unknown AppleScript error"
                    logger.error("[TerminalBridge] AppleScript error: \(message)")
                    continuation.resume(throwing: TerminalBridgeError.appleScriptError(message))
                } else {
                    continuation.resume()
                }
            }
        }
    }

    /// Execute AppleScript and return the result
    private func executeAppleScriptWithResult(_ source: String) async throws -> String? {
        try await withCheckedThrowingContinuation { (continuation: CheckedContinuation<String?, Error>) in
            DispatchQueue.global(qos: .userInitiated).async {
                var error: NSDictionary?
                let script = NSAppleScript(source: source)
                let result = script?.executeAndReturnError(&error)

                if let error = error {
                    let message = error[NSAppleScript.errorMessage] as? String ?? "Unknown AppleScript error"
                    logger.error("[TerminalBridge] AppleScript error: \(message)")
                    continuation.resume(throwing: TerminalBridgeError.appleScriptError(message))
                } else {
                    continuation.resume(returning: result?.stringValue)
                }
            }
        }
    }

    // MARK: - AppleScript Escaping

    /// Escape a string for safe interpolation into AppleScript.
    /// Replaces backslashes, double quotes, and strips control characters.
    private func escapeForAppleScript(_ string: String) -> String {
        string
            .replacingOccurrences(of: "\\", with: "\\\\")
            .replacingOccurrences(of: "\"", with: "\\\"")
            .filter { !$0.isNewline && $0 != "\r" }
    }

    /// Escape a path for safe use inside single-quoted shell arguments in AppleScript.
    /// Replaces single quotes with the shell escape sequence '\'' and strips control characters.
    private func escapePathForShell(_ path: String) -> String {
        path
            .replacingOccurrences(of: "'", with: "'\\''")
            .filter { !$0.isNewline && $0 != "\r" }
    }

    // MARK: - Warp Scripts

    private func warpSpawnScript(cwd: String?) -> String {
        if let cwd = cwd {
            return """
            tell application "Warp"
                activate
                delay 0.3
                tell application "System Events"
                    tell process "Warp"
                        keystroke "t" using command down
                        delay 0.2
                    end tell
                end tell
            end tell
            do shell script "open -a Warp '\(escapePathForShell(cwd))'"
            """
        } else {
            return """
            tell application "Warp"
                activate
                delay 0.3
                tell application "System Events"
                    tell process "Warp"
                        keystroke "t" using command down
                    end tell
                end tell
            end tell
            """
        }
    }

    private func warpExecuteScript(command: String) -> String {
        let escapedCommand = escapeForAppleScript(command)
        return """
        tell application "Warp"
            activate
            delay 0.1
            tell application "System Events"
                tell process "Warp"
                    keystroke "\(escapedCommand)"
                    keystroke return
                end tell
            end tell
        end tell
        """
    }

    // MARK: - iTerm Scripts

    private func itermSpawnScript(cwd: String?) -> String {
        if let cwd = cwd {
            return """
            tell application "iTerm"
                activate
                create window with default profile
                tell current session of current window
                    write text "cd '\(escapePathForShell(cwd))'"
                end tell
            end tell
            """
        } else {
            return """
            tell application "iTerm"
                activate
                create window with default profile
            end tell
            """
        }
    }

    private func itermExecuteScript(command: String) -> String {
        let escapedCommand = escapeForAppleScript(command)
        return """
        tell application "iTerm"
            tell current session of current window
                write text "\(escapedCommand)"
            end tell
        end tell
        """
    }

    private func itermCaptureScript() -> String {
        return """
        tell application "iTerm"
            tell current session of current window
                return contents
            end tell
        end tell
        """
    }

    // MARK: - Terminal.app Scripts

    private func terminalAppSpawnScript(cwd: String?) -> String {
        if let cwd = cwd {
            return """
            tell application "Terminal"
                activate
                do script "cd '\(escapePathForShell(cwd))'"
            end tell
            """
        } else {
            return """
            tell application "Terminal"
                activate
                do script ""
            end tell
            """
        }
    }

    private func terminalAppExecuteScript(command: String) -> String {
        let escapedCommand = escapeForAppleScript(command)
        return """
        tell application "Terminal"
            tell front window
                do script "\(escapedCommand)" in selected tab
            end tell
        end tell
        """
    }

    private func terminalAppCaptureScript() -> String {
        return """
        tell application "Terminal"
            tell front window
                return contents of selected tab
            end tell
        end tell
        """
    }
}

// MARK: - Errors

enum TerminalBridgeError: LocalizedError {
    case terminalNotInstalled(TerminalApp)
    case appleScriptError(String)
    case captureNotSupported(TerminalApp)
    case captureTimeout

    var errorDescription: String? {
        switch self {
        case .terminalNotInstalled(let app):
            return "\(app.displayName) is not installed."
        case .appleScriptError(let message):
            return "AppleScript error: \(message)"
        case .captureNotSupported(let app):
            return "Output capture is not supported for \(app.displayName)."
        case .captureTimeout:
            return "Timed out waiting for terminal output."
        }
    }
}
