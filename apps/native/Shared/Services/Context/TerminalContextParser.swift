//
//  TerminalContextParser.swift
//  MagnetarStudio
//
//  Intelligent parser for terminal output that detects common error patterns
//  and provides structured information for AI assistance.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "TerminalContextParser")

// MARK: - Parsed Error

/// A parsed error with structured information
struct ParsedTerminalError: Sendable, Identifiable {
    let id: UUID
    let category: ErrorCategory
    let summary: String
    let details: String
    let suggestedFixes: [SuggestedFix]
    let severity: ErrorSeverity
    let filePath: String?
    let lineNumber: Int?
    let confidence: Float

    enum ErrorCategory: String, Sendable, CaseIterable {
        case packageManager = "Package Manager"
        case git = "Git"
        case compiler = "Compiler"
        case runtime = "Runtime"
        case permission = "Permission"
        case network = "Network"
        case fileSystem = "File System"
        case unknown = "Unknown"

        var iconName: String {
            switch self {
            case .packageManager: return "shippingbox"
            case .git: return "arrow.triangle.branch"
            case .compiler: return "hammer"
            case .runtime: return "play.slash"
            case .permission: return "lock.shield"
            case .network: return "wifi.exclamationmark"
            case .fileSystem: return "folder.badge.questionmark"
            case .unknown: return "questionmark.circle"
            }
        }
    }

    enum ErrorSeverity: String, Sendable {
        case critical
        case error
        case warning
        case info
    }

    init(
        category: ErrorCategory,
        summary: String,
        details: String,
        suggestedFixes: [SuggestedFix] = [],
        severity: ErrorSeverity = .error,
        filePath: String? = nil,
        lineNumber: Int? = nil,
        confidence: Float = 0.8
    ) {
        self.id = UUID()
        self.category = category
        self.summary = summary
        self.details = details
        self.suggestedFixes = suggestedFixes
        self.severity = severity
        self.filePath = filePath
        self.lineNumber = lineNumber
        self.confidence = confidence
    }
}

/// A suggested fix for an error
struct SuggestedFix: Sendable, Identifiable {
    let id: UUID
    let description: String
    let command: String?
    let isAutomatic: Bool

    init(description: String, command: String? = nil, isAutomatic: Bool = false) {
        self.id = UUID()
        self.description = description
        self.command = command
        self.isAutomatic = isAutomatic
    }
}

// MARK: - Enriched Context

/// Terminal context enriched with parsed error information
struct EnrichedTerminalContext: Sendable {
    let original: TerminalContext
    let parsedErrors: [ParsedTerminalError]
    let detectedLanguage: String?
    let commandType: CommandType
    let enrichedSummary: String

    enum CommandType: String, Sendable {
        case build
        case test
        case install
        case run
        case git
        case navigation
        case fileOperation
        case network
        case other
    }

    /// Whether this context contains actionable errors
    var hasActionableErrors: Bool {
        parsedErrors.contains { $0.severity == .error || $0.severity == .critical }
    }

    /// Best suggested fix if available
    var primarySuggestedFix: SuggestedFix? {
        parsedErrors.flatMap { $0.suggestedFixes }.first
    }
}

// MARK: - Terminal Context Parser

/// Parses terminal output to detect error patterns and provide intelligent suggestions
actor TerminalContextParser {
    // MARK: - Singleton

    static let shared = TerminalContextParser()

    // MARK: - Error Patterns

    private struct ErrorPattern {
        let regex: NSRegularExpression
        let category: ParsedTerminalError.ErrorCategory
        let severity: ParsedTerminalError.ErrorSeverity
        let summaryExtractor: (NSTextCheckingResult, String) -> String
        let suggestedFixes: [SuggestedFix]
    }

    private var errorPatterns: [ErrorPattern] = []

    // MARK: - Init

    init() {
        setupErrorPatterns()
    }

    private func setupErrorPatterns() {
        // NPM/Yarn/PNPM errors
        addPattern(
            pattern: "npm ERR! ([^\n]+)",
            category: .packageManager,
            severity: .error,
            summaryExtractor: { match, text in
                extractGroup(match: match, group: 1, in: text) ?? "npm error"
            },
            fixes: [
                SuggestedFix(description: "Clear npm cache", command: "npm cache clean --force"),
                SuggestedFix(description: "Delete node_modules and reinstall", command: "rm -rf node_modules && npm install")
            ]
        )

        addPattern(
            pattern: "error: Cannot find module '([^']+)'",
            category: .packageManager,
            severity: .error,
            summaryExtractor: { match, text in
                let module = extractGroup(match: match, group: 1, in: text) ?? "unknown"
                return "Missing module: \(module)"
            },
            fixes: [
                SuggestedFix(description: "Install missing dependency", command: nil, isAutomatic: false)
            ]
        )

        // Git errors
        addPattern(
            pattern: "fatal: ([^\n]+)",
            category: .git,
            severity: .critical,
            summaryExtractor: { match, text in
                extractGroup(match: match, group: 1, in: text) ?? "Git fatal error"
            },
            fixes: []
        )

        addPattern(
            pattern: "error: failed to push some refs",
            category: .git,
            severity: .error,
            summaryExtractor: { _, _ in "Push rejected - remote has changes" },
            fixes: [
                SuggestedFix(description: "Pull and rebase", command: "git pull --rebase"),
                SuggestedFix(description: "Pull with merge", command: "git pull")
            ]
        )

        addPattern(
            pattern: "CONFLICT \\(content\\): Merge conflict in ([^\n]+)",
            category: .git,
            severity: .error,
            summaryExtractor: { match, text in
                let file = extractGroup(match: match, group: 1, in: text) ?? "unknown"
                return "Merge conflict in \(file)"
            },
            fixes: [
                SuggestedFix(description: "Open file to resolve conflicts manually", command: nil),
                SuggestedFix(description: "Accept current (ours)", command: nil),
                SuggestedFix(description: "Accept incoming (theirs)", command: nil)
            ]
        )

        // Python errors
        addPattern(
            pattern: "Traceback \\(most recent call last\\):",
            category: .runtime,
            severity: .error,
            summaryExtractor: { _, _ in "Python traceback" },
            fixes: []
        )

        addPattern(
            pattern: "ModuleNotFoundError: No module named '([^']+)'",
            category: .runtime,
            severity: .error,
            summaryExtractor: { match, text in
                let module = extractGroup(match: match, group: 1, in: text) ?? "unknown"
                return "Python module not found: \(module)"
            },
            fixes: [
                SuggestedFix(description: "Install with pip", command: nil, isAutomatic: false)
            ]
        )

        addPattern(
            pattern: "SyntaxError: ([^\n]+)",
            category: .compiler,
            severity: .error,
            summaryExtractor: { match, text in
                let detail = extractGroup(match: match, group: 1, in: text) ?? "syntax error"
                return "Python syntax error: \(detail)"
            },
            fixes: []
        )

        // Swift/Xcode errors
        addPattern(
            pattern: "error: ([^:]+):(\\d+):(\\d+): error: ([^\n]+)",
            category: .compiler,
            severity: .error,
            summaryExtractor: { match, text in
                let message = extractGroup(match: match, group: 4, in: text) ?? "compile error"
                return "Swift error: \(message)"
            },
            fixes: []
        )

        addPattern(
            pattern: "\\*\\* BUILD FAILED \\*\\*",
            category: .compiler,
            severity: .critical,
            summaryExtractor: { _, _ in "Xcode build failed" },
            fixes: [
                SuggestedFix(description: "Clean build folder", command: "xcodebuild clean"),
                SuggestedFix(description: "Check build logs for details", command: nil)
            ]
        )

        // Rust errors
        addPattern(
            pattern: "error\\[E(\\d+)\\]: ([^\n]+)",
            category: .compiler,
            severity: .error,
            summaryExtractor: { match, text in
                let code = extractGroup(match: match, group: 1, in: text) ?? "?"
                let message = extractGroup(match: match, group: 2, in: text) ?? "error"
                return "Rust E\(code): \(message)"
            },
            fixes: []
        )

        // Permission errors
        addPattern(
            pattern: "Permission denied|EACCES|Operation not permitted",
            category: .permission,
            severity: .error,
            summaryExtractor: { _, _ in "Permission denied" },
            fixes: [
                SuggestedFix(description: "Run with sudo (use caution)", command: nil),
                SuggestedFix(description: "Check file permissions", command: "ls -la")
            ]
        )

        // Network errors
        addPattern(
            pattern: "ECONNREFUSED|Connection refused|ETIMEDOUT|Network is unreachable",
            category: .network,
            severity: .error,
            summaryExtractor: { _, _ in "Network connection error" },
            fixes: [
                SuggestedFix(description: "Check network connection", command: nil),
                SuggestedFix(description: "Verify service is running", command: nil)
            ]
        )

        addPattern(
            pattern: "Could not resolve host|getaddrinfo",
            category: .network,
            severity: .error,
            summaryExtractor: { _, _ in "DNS resolution failed" },
            fixes: [
                SuggestedFix(description: "Check internet connection", command: nil),
                SuggestedFix(description: "Verify hostname is correct", command: nil)
            ]
        )

        // File system errors
        addPattern(
            pattern: "No such file or directory|ENOENT",
            category: .fileSystem,
            severity: .error,
            summaryExtractor: { _, _ in "File or directory not found" },
            fixes: [
                SuggestedFix(description: "Check path exists", command: "ls -la"),
                SuggestedFix(description: "Create missing directory", command: nil)
            ]
        )

        addPattern(
            pattern: "Directory not empty|ENOTEMPTY",
            category: .fileSystem,
            severity: .error,
            summaryExtractor: { _, _ in "Directory not empty" },
            fixes: [
                SuggestedFix(description: "Use recursive delete", command: nil)
            ]
        )
    }

    private func addPattern(
        pattern: String,
        category: ParsedTerminalError.ErrorCategory,
        severity: ParsedTerminalError.ErrorSeverity,
        summaryExtractor: @escaping (NSTextCheckingResult, String) -> String,
        fixes: [SuggestedFix]
    ) {
        guard let regex = try? NSRegularExpression(pattern: pattern, options: [.caseInsensitive]) else {
            logger.warning("[Parser] Failed to compile pattern: \(pattern)")
            return
        }

        errorPatterns.append(ErrorPattern(
            regex: regex,
            category: category,
            severity: severity,
            summaryExtractor: summaryExtractor,
            suggestedFixes: fixes
        ))
    }

    // MARK: - Parsing

    /// Parse terminal context and enrich with error information
    func parse(_ context: TerminalContext) -> EnrichedTerminalContext {
        let output = context.output
        var parsedErrors: [ParsedTerminalError] = []

        // Match against all patterns
        for pattern in errorPatterns {
            let range = NSRange(output.startIndex..., in: output)
            let matches = pattern.regex.matches(in: output, options: [], range: range)

            for match in matches {
                let summary = pattern.summaryExtractor(match, output)
                let error = ParsedTerminalError(
                    category: pattern.category,
                    summary: summary,
                    details: extractContext(around: match, in: output),
                    suggestedFixes: pattern.suggestedFixes,
                    severity: pattern.severity
                )
                parsedErrors.append(error)
            }
        }

        // Detect command type
        let commandType = detectCommandType(context.command)

        // Detect language
        let detectedLanguage = detectLanguage(from: context)

        // Build enriched summary
        let enrichedSummary = buildEnrichedSummary(context: context, errors: parsedErrors)

        logger.debug("[Parser] Parsed \(parsedErrors.count) errors from output")

        return EnrichedTerminalContext(
            original: context,
            parsedErrors: parsedErrors,
            detectedLanguage: detectedLanguage,
            commandType: commandType,
            enrichedSummary: enrichedSummary
        )
    }

    // MARK: - Helpers

    private func detectCommandType(_ command: String) -> EnrichedTerminalContext.CommandType {
        let cmd = command.lowercased()

        if cmd.hasPrefix("npm ") || cmd.hasPrefix("yarn ") || cmd.hasPrefix("pnpm ") ||
           cmd.hasPrefix("pip ") || cmd.hasPrefix("cargo ") || cmd.hasPrefix("brew ") {
            if cmd.contains("install") || cmd.contains("add") {
                return .install
            }
            if cmd.contains("run") || cmd.contains("start") {
                return .run
            }
            if cmd.contains("test") {
                return .test
            }
            if cmd.contains("build") {
                return .build
            }
        }

        if cmd.hasPrefix("git ") {
            return .git
        }

        if cmd.hasPrefix("cd ") || cmd.hasPrefix("ls") || cmd.hasPrefix("pwd") {
            return .navigation
        }

        if cmd.hasPrefix("cp ") || cmd.hasPrefix("mv ") || cmd.hasPrefix("rm ") ||
           cmd.hasPrefix("mkdir ") || cmd.hasPrefix("touch ") {
            return .fileOperation
        }

        if cmd.hasPrefix("curl ") || cmd.hasPrefix("wget ") || cmd.hasPrefix("ssh ") {
            return .network
        }

        if cmd.contains("build") || cmd.contains("compile") || cmd.hasPrefix("make") ||
           cmd.hasPrefix("xcodebuild") || cmd.hasPrefix("swift build") || cmd.hasPrefix("cargo build") {
            return .build
        }

        if cmd.contains("test") || cmd.hasPrefix("pytest") || cmd.hasPrefix("jest") {
            return .test
        }

        return .other
    }

    private func detectLanguage(from context: TerminalContext) -> String? {
        let cmd = context.command.lowercased()
        let output = context.output.lowercased()

        if cmd.hasPrefix("python") || cmd.hasPrefix("pip") || output.contains("traceback") {
            return "Python"
        }
        if cmd.hasPrefix("node") || cmd.hasPrefix("npm") || cmd.hasPrefix("yarn") ||
           output.contains("syntaxerror:") && output.contains("javascript") {
            return "JavaScript"
        }
        if cmd.hasPrefix("swift") || cmd.hasPrefix("xcodebuild") || output.contains(".swift:") {
            return "Swift"
        }
        if cmd.hasPrefix("cargo") || cmd.hasPrefix("rustc") || output.contains("error[e") {
            return "Rust"
        }
        if cmd.hasPrefix("go ") || output.contains(".go:") {
            return "Go"
        }

        return nil
    }

    private func extractContext(around match: NSTextCheckingResult, in text: String, lines: Int = 2) -> String {
        guard let matchRange = Range(match.range, in: text) else {
            return ""
        }

        // Find line boundaries
        let startOfLine = text[..<matchRange.lowerBound].lastIndex(of: "\n").map { text.index(after: $0) } ?? text.startIndex
        let endOfLine = text[matchRange.upperBound...].firstIndex(of: "\n") ?? text.endIndex

        return String(text[startOfLine..<endOfLine])
    }

    private func buildEnrichedSummary(context: TerminalContext, errors: [ParsedTerminalError]) -> String {
        var parts: [String] = []

        parts.append("Command: `\(context.command)`")
        parts.append("Exit code: \(context.exitCode)")

        if !errors.isEmpty {
            let errorSummaries = errors.prefix(3).map { "• \($0.summary)" }
            parts.append("Errors detected:\n" + errorSummaries.joined(separator: "\n"))

            if let fix = errors.first?.suggestedFixes.first {
                parts.append("Suggested fix: \(fix.description)")
            }
        }

        return parts.joined(separator: "\n")
    }
}

// MARK: - Helper Function

private func extractGroup(match: NSTextCheckingResult, group: Int, in text: String) -> String? {
    guard group < match.numberOfRanges,
          let range = Range(match.range(at: group), in: text) else {
        return nil
    }
    return String(text[range])
}
