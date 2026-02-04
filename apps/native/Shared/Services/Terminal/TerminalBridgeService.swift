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

    // MARK: - Init

    init() {
        Task {
            await detectAvailableTerminals()
        }
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
        logger.debug("[TerminalBridge] Executed in \(app.displayName): \(command.prefix(50))")
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
            do shell script "open -a Warp '\(cwd)'"
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
        let escapedCommand = command.replacingOccurrences(of: "\"", with: "\\\"")
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
                    write text "cd '\(cwd)'"
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
        let escapedCommand = command.replacingOccurrences(of: "\"", with: "\\\"")
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
                do script "cd '\(cwd)'"
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
        let escapedCommand = command.replacingOccurrences(of: "\"", with: "\\\"")
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

    var errorDescription: String? {
        switch self {
        case .terminalNotInstalled(let app):
            return "\(app.displayName) is not installed."
        case .appleScriptError(let message):
            return "AppleScript error: \(message)"
        case .captureNotSupported(let app):
            return "Output capture is not supported for \(app.displayName)."
        }
    }
}
