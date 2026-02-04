//
//  DiagnosticsStore.swift
//  MagnetarStudio
//
//  Observable store for managing LSP diagnostics (errors, warnings, hints).
//  Provides per-file diagnostic tracking and aggregated statistics.
//

import Foundation
import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "DiagnosticsStore")

// MARK: - Diagnostic Display Model

/// A diagnostic item ready for UI display
struct DiagnosticItem: Identifiable, Sendable {
    let id: String
    let filePath: String
    let fileName: String
    let line: Int
    let character: Int
    let endLine: Int
    let endCharacter: Int
    let severity: LSPDiagnosticSeverity
    let message: String
    let code: String?
    let source: String?
    let timestamp: Date

    init(from diagnostic: LSPDiagnostic, filePath: String) {
        self.id = UUID().uuidString
        self.filePath = filePath
        self.fileName = (filePath as NSString).lastPathComponent
        self.line = diagnostic.range.start.line
        self.character = diagnostic.range.start.character
        self.endLine = diagnostic.range.end.line
        self.endCharacter = diagnostic.range.end.character
        self.severity = diagnostic.severity ?? .information
        self.message = diagnostic.message
        self.code = diagnostic.code
        self.source = diagnostic.source
        self.timestamp = Date()
    }

    /// Human-readable location string
    var locationString: String {
        "\(fileName):\(line + 1):\(character + 1)"
    }
}

// MARK: - Diagnostic Statistics

/// Aggregated diagnostic counts
struct DiagnosticStats: Sendable, Equatable {
    let errorCount: Int
    let warningCount: Int
    let infoCount: Int
    let hintCount: Int

    var totalCount: Int {
        errorCount + warningCount + infoCount + hintCount
    }

    var hasErrors: Bool { errorCount > 0 }
    var hasWarnings: Bool { warningCount > 0 }

    static let zero = DiagnosticStats(errorCount: 0, warningCount: 0, infoCount: 0, hintCount: 0)
}

// MARK: - File Diagnostics

/// Diagnostics for a single file
struct FileDiagnostics: Identifiable, Sendable {
    let filePath: String
    let diagnostics: [DiagnosticItem]
    let lastUpdated: Date

    var id: String { filePath }

    var fileName: String {
        (filePath as NSString).lastPathComponent
    }

    var stats: DiagnosticStats {
        var errors = 0, warnings = 0, infos = 0, hints = 0
        for diag in diagnostics {
            switch diag.severity {
            case .error: errors += 1
            case .warning: warnings += 1
            case .information: infos += 1
            case .hint: hints += 1
            }
        }
        return DiagnosticStats(errorCount: errors, warningCount: warnings, infoCount: infos, hintCount: hints)
    }

    /// Get diagnostics for a specific line
    func diagnostics(forLine line: Int) -> [DiagnosticItem] {
        diagnostics.filter { $0.line == line }
    }

    /// Get diagnostics within a range of lines
    func diagnostics(inRange range: ClosedRange<Int>) -> [DiagnosticItem] {
        diagnostics.filter { range.contains($0.line) }
    }
}

// MARK: - Diagnostics Store

/// Observable store for managing diagnostics across the workspace
@MainActor
@Observable
final class DiagnosticsStore {
    // MARK: - Singleton

    static let shared = DiagnosticsStore()

    // MARK: - State

    /// Diagnostics grouped by file path
    private(set) var filesDiagnostics: [String: FileDiagnostics] = [:]

    /// Currently selected file for filtering
    var selectedFilePath: String?

    /// Whether to auto-refresh diagnostics on file changes
    var autoRefresh: Bool = true

    /// Debounce timer for refresh requests
    private var refreshTask: Task<Void, Never>?
    private let debounceInterval: TimeInterval = 0.5

    // MARK: - Computed Properties

    /// All diagnostics across all files
    var allDiagnostics: [DiagnosticItem] {
        filesDiagnostics.values.flatMap { $0.diagnostics }
    }

    /// Diagnostics for the selected file
    var selectedFileDiagnostics: [DiagnosticItem] {
        guard let path = selectedFilePath else { return [] }
        return filesDiagnostics[path]?.diagnostics ?? []
    }

    /// Aggregated stats across all files
    var totalStats: DiagnosticStats {
        var errors = 0, warnings = 0, infos = 0, hints = 0
        for file in filesDiagnostics.values {
            let stats = file.stats
            errors += stats.errorCount
            warnings += stats.warningCount
            infos += stats.infoCount
            hints += stats.hintCount
        }
        return DiagnosticStats(errorCount: errors, warningCount: warnings, infoCount: infos, hintCount: hints)
    }

    /// Files with errors, sorted by error count
    var filesWithErrors: [FileDiagnostics] {
        filesDiagnostics.values
            .filter { $0.stats.hasErrors }
            .sorted { $0.stats.errorCount > $1.stats.errorCount }
    }

    /// Files with warnings (but no errors)
    var filesWithWarnings: [FileDiagnostics] {
        filesDiagnostics.values
            .filter { !$0.stats.hasErrors && $0.stats.hasWarnings }
            .sorted { $0.stats.warningCount > $1.stats.warningCount }
    }

    // MARK: - Update Methods

    /// Update diagnostics for a file
    func updateDiagnostics(_ diagnostics: [LSPDiagnostic], for filePath: String) {
        let items = diagnostics.map { DiagnosticItem(from: $0, filePath: filePath) }
        filesDiagnostics[filePath] = FileDiagnostics(
            filePath: filePath,
            diagnostics: items,
            lastUpdated: Date()
        )

        logger.debug("[Diagnostics] Updated \(filePath): \(items.count) diagnostics")
    }

    /// Clear diagnostics for a file
    func clearDiagnostics(for filePath: String) {
        filesDiagnostics.removeValue(forKey: filePath)
    }

    /// Clear all diagnostics
    func clearAll() {
        filesDiagnostics.removeAll()
    }

    // MARK: - Refresh Methods

    /// Request diagnostics refresh for a file (debounced)
    func requestRefresh(for filePath: String, workspacePath: String, content: String) {
        guard autoRefresh else { return }

        // Cancel previous refresh task
        refreshTask?.cancel()

        // Create debounced task
        refreshTask = Task {
            try? await Task.sleep(nanoseconds: UInt64(debounceInterval * 1_000_000_000))

            guard !Task.isCancelled else { return }

            await refreshDiagnostics(for: filePath, workspacePath: workspacePath, content: content)
        }
    }

    /// Immediately refresh diagnostics for a file
    func refreshDiagnostics(for filePath: String, workspacePath: String, content: String) async {
        do {
            let diagnostics = try await LSPBridgeService.shared.diagnostics(
                filePath: filePath,
                workspacePath: workspacePath,
                text: content
            )

            await MainActor.run {
                updateDiagnostics(diagnostics, for: filePath)
            }
        } catch {
            logger.error("[Diagnostics] Failed to refresh for \(filePath): \(error)")
        }
    }

    // MARK: - Query Methods

    /// Get diagnostics for a specific line in a file
    func diagnostics(for filePath: String, line: Int) -> [DiagnosticItem] {
        filesDiagnostics[filePath]?.diagnostics(forLine: line) ?? []
    }

    /// Check if a line has errors
    func hasErrors(in filePath: String, at line: Int) -> Bool {
        diagnostics(for: filePath, line: line).contains { $0.severity == .error }
    }

    /// Check if a line has warnings
    func hasWarnings(in filePath: String, at line: Int) -> Bool {
        diagnostics(for: filePath, line: line).contains { $0.severity == .warning }
    }

    /// Get the most severe diagnostic for a line
    func mostSevereDiagnostic(in filePath: String, at line: Int) -> DiagnosticItem? {
        diagnostics(for: filePath, line: line)
            .min { ($0.severity.rawValue) < ($1.severity.rawValue) }
    }
}

// MARK: - SwiftUI Extensions

extension DiagnosticItem {
    /// Color for this diagnostic's severity
    var severityColor: Color {
        switch severity {
        case .error: return .red
        case .warning: return .orange
        case .information: return .blue
        case .hint: return .gray
        }
    }

    /// Icon name for this diagnostic's severity
    var severityIcon: String {
        severity.iconName
    }
}

// MARK: - Preview Support

extension DiagnosticsStore {
    /// Create a store with sample data for previews
    static var preview: DiagnosticsStore {
        let store = DiagnosticsStore()

        let sampleDiagnostics: [LSPDiagnostic] = [
            LSPDiagnostic(
                range: LSPRange(
                    start: LSPPosition(line: 10, character: 4),
                    end: LSPPosition(line: 10, character: 20)
                ),
                severity: .error,
                code: "E001",
                source: "pyright",
                message: "Cannot find name 'undefined_variable'"
            ),
            LSPDiagnostic(
                range: LSPRange(
                    start: LSPPosition(line: 15, character: 0),
                    end: LSPPosition(line: 15, character: 50)
                ),
                severity: .warning,
                code: "W002",
                source: "pyright",
                message: "Unused import 'os'"
            )
        ]

        store.updateDiagnostics(sampleDiagnostics, for: "/example/file.py")
        return store
    }
}
