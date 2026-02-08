//
//  CodeDiagnosticsPanel.swift
//  MagnetarStudio (macOS)
//
//  Panel displaying LSP diagnostics (errors, warnings) for the current file.
//  Integrates with DiagnosticsStore for real-time updates.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "CodeDiagnosticsPanel")

struct CodeDiagnosticsPanel: View {
    @Bindable var diagnosticsStore: DiagnosticsStore
    let currentFilePath: String?
    let workspacePath: String?
    let onNavigateTo: ((String, Int, Int) -> Void)?

    @State private var filterSeverity: LSPDiagnosticSeverity? = nil
    @State private var showAllFiles: Bool = false

    var body: some View {
        VStack(spacing: 0) {
            // Header
            header

            Divider()

            // Content
            if filteredDiagnostics.isEmpty {
                emptyState
            } else {
                diagnosticsList
            }
        }
        .background(Color.surfaceTertiary.opacity(0.2))
    }

    // MARK: - Header

    private var header: some View {
        HStack(spacing: 8) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 12))
                .foregroundStyle(.orange)

            Text("Problems")
                .font(.system(size: 12, weight: .semibold))

            // Stats badges
            if diagnosticsStore.totalStats.errorCount > 0 {
                StatBadge(count: diagnosticsStore.totalStats.errorCount, color: .red, icon: "xmark.circle.fill")
            }

            if diagnosticsStore.totalStats.warningCount > 0 {
                StatBadge(count: diagnosticsStore.totalStats.warningCount, color: .orange, icon: "exclamationmark.triangle.fill")
            }

            Spacer()

            // Filter toggle
            Toggle(isOn: $showAllFiles) {
                Text("All Files")
                    .font(.system(size: 10))
            }
            .toggleStyle(.checkbox)
            .controlSize(.small)

            // Severity filter menu
            Menu {
                Button("All") { filterSeverity = nil }
                Divider()
                Button("Errors") { filterSeverity = .error }
                Button("Warnings") { filterSeverity = .warning }
                Button("Info") { filterSeverity = .information }
            } label: {
                Image(systemName: "line.3.horizontal.decrease.circle")
                    .font(.system(size: 12))
                    .foregroundStyle(filterSeverity != nil ? Color.magnetarPrimary : .secondary)
            }
            .menuStyle(.borderlessButton)
            .frame(width: 24)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(Color.surfaceTertiary.opacity(0.3))
    }

    // MARK: - Diagnostics List

    private var diagnosticsList: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 2) {
                ForEach(filteredDiagnostics) { diagnostic in
                    DiagnosticRow(
                        diagnostic: diagnostic,
                        showFileName: showAllFiles,
                        onTap: {
                            onNavigateTo?(diagnostic.filePath, diagnostic.line, diagnostic.character)
                        }
                    )
                }
            }
            .padding(.vertical, 4)
        }
    }

    // MARK: - Empty State

    private var emptyState: some View {
        VStack(spacing: 8) {
            Image(systemName: "checkmark.circle")
                .font(.system(size: 24))
                .foregroundStyle(.green)

            Text("No Problems")
                .font(.system(size: 12, weight: .medium))

            Text(showAllFiles ? "All files are clean" : "Current file has no issues")
                .font(.system(size: 11))
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }

    // MARK: - Computed Properties

    private var filteredDiagnostics: [DiagnosticItem] {
        var diagnostics: [DiagnosticItem]

        if showAllFiles {
            diagnostics = diagnosticsStore.allDiagnostics
        } else if let path = currentFilePath {
            diagnostics = diagnosticsStore.filesDiagnostics[path]?.diagnostics ?? []
        } else {
            diagnostics = []
        }

        // Apply severity filter
        if let severity = filterSeverity {
            diagnostics = diagnostics.filter { $0.severity == severity }
        }

        // Sort by severity (errors first) then by line
        return diagnostics.sorted { lhs, rhs in
            if lhs.severity.rawValue != rhs.severity.rawValue {
                return lhs.severity.rawValue < rhs.severity.rawValue
            }
            if lhs.filePath != rhs.filePath {
                return lhs.filePath < rhs.filePath
            }
            return lhs.line < rhs.line
        }
    }
}

// MARK: - Stat Badge

private struct StatBadge: View {
    let count: Int
    let color: Color
    let icon: String

    var body: some View {
        HStack(spacing: 3) {
            Image(systemName: icon)
                .font(.system(size: 9))
            Text("\(count)")
                .font(.system(size: 10, weight: .medium))
        }
        .foregroundStyle(color)
        .padding(.horizontal, 6)
        .padding(.vertical, 2)
        .background(color.opacity(0.15))
        .cornerRadius(4)
    }
}

// MARK: - Diagnostic Row

private struct DiagnosticRow: View {
    let diagnostic: DiagnosticItem
    let showFileName: Bool
    let onTap: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: onTap) {
            HStack(alignment: .top, spacing: 8) {
                // Severity icon
                Image(systemName: diagnostic.severityIcon)
                    .font(.system(size: 12))
                    .foregroundStyle(diagnostic.severityColor)
                    .frame(width: 16)

                VStack(alignment: .leading, spacing: 2) {
                    // Message
                    Text(diagnostic.message)
                        .font(.system(size: 11))
                        .foregroundStyle(.primary)
                        .lineLimit(2)
                        .multilineTextAlignment(.leading)

                    // Location
                    HStack(spacing: 4) {
                        if showFileName {
                            Text(diagnostic.fileName)
                                .font(.system(size: 10, weight: .medium))
                                .foregroundStyle(.secondary)
                        }

                        Text("Ln \(diagnostic.line + 1), Col \(diagnostic.character + 1)")
                            .font(.system(size: 10, design: .monospaced))
                            .foregroundStyle(.tertiary)

                        if let source = diagnostic.source {
                            Text("[\(source)]")
                                .font(.system(size: 9))
                                .foregroundStyle(.tertiary)
                        }
                    }
                }

                Spacer()
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(isHovered ? Color.surfaceTertiary.opacity(0.5) : Color.clear)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            isHovered = hovering
        }
    }
}

// MARK: - Hover Tooltip View

/// Tooltip view for displaying LSP hover information
struct LSPHoverTooltip: View {
    let content: String
    let range: LSPRange?

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            // Parse markdown-style content
            Text(parseContent(content))
                .font(.system(size: 11, design: .monospaced))
                .foregroundStyle(.primary)
                .textSelection(.enabled)
        }
        .padding(8)
        .background(Color(nsColor: .windowBackgroundColor))
        .cornerRadius(6)
        .shadow(color: .black.opacity(0.2), radius: 4, x: 0, y: 2)
        .frame(maxWidth: 400)
    }

    private func parseContent(_ content: String) -> AttributedString {
        // Simple markdown parsing for code blocks
        var result = AttributedString(content)

        // Strip code fence markers for display
        let stripped = content
            .replacingOccurrences(of: "```\\w*\\n?", with: "", options: .regularExpression)
            .replacingOccurrences(of: "```", with: "")
            .trimmingCharacters(in: .whitespacesAndNewlines)

        result = AttributedString(stripped)
        return result
    }
}

// MARK: - Completion Popup

/// Popup view for displaying LSP completion suggestions
struct LSPCompletionPopup: View {
    let items: [LSPCompletionItem]
    let selectedIndex: Int
    let onSelect: (LSPCompletionItem) -> Void

    var body: some View {
        VStack(spacing: 0) {
            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(spacing: 0) {
                        ForEach(Array(items.enumerated()), id: \.element.id) { index, item in
                            CompletionItemRow(
                                item: item,
                                isSelected: index == selectedIndex,
                                onSelect: { onSelect(item) }
                            )
                            .id(index)
                        }
                    }
                }
                .onChange(of: selectedIndex) { _, newValue in
                    withAnimation {
                        proxy.scrollTo(newValue, anchor: .center)
                    }
                }
            }
        }
        .frame(width: 300, height: min(CGFloat(items.count) * 28, 200))
        .background(Color(nsColor: .windowBackgroundColor))
        .cornerRadius(6)
        .shadow(color: .black.opacity(0.2), radius: 4, x: 0, y: 2)
    }
}

private struct CompletionItemRow: View {
    let item: LSPCompletionItem
    let isSelected: Bool
    let onSelect: () -> Void

    var body: some View {
        Button(action: onSelect) {
            HStack(spacing: 8) {
                // Kind icon
                Image(systemName: item.kind?.iconName ?? "doc.text")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
                    .frame(width: 16)

                // Label
                Text(item.label)
                    .font(.system(size: 12, design: .monospaced))
                    .foregroundStyle(.primary)
                    .lineLimit(1)

                Spacer()

                // Detail (type info)
                if let detail = item.detail {
                    Text(detail)
                        .font(.system(size: 10))
                        .foregroundStyle(.tertiary)
                        .lineLimit(1)
                }
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(isSelected ? Color.magnetarPrimary.opacity(0.2) : Color.clear)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }
}

// MARK: - Preview

#Preview("Diagnostics Panel") {
    CodeDiagnosticsPanel(
        diagnosticsStore: DiagnosticsStore.preview,
        currentFilePath: "/example/file.py",
        workspacePath: "/example",
        onNavigateTo: { _, _, _ in }
    )
    .frame(width: 350, height: 300)
}

#Preview("Hover Tooltip") {
    LSPHoverTooltip(
        content: "```python\ndef example(x: int) -> str\n```\n\nThis function converts an integer to a string.",
        range: nil
    )
    .padding()
}

#Preview("Completion Popup") {
    LSPCompletionPopup(
        items: [
            LSPCompletionItem(label: "print", kind: .function, detail: "(value: Any) -> None", documentation: nil, insertText: nil, sortText: nil),
            LSPCompletionItem(label: "println", kind: .function, detail: "(value: Any) -> None", documentation: nil, insertText: nil, sortText: nil),
            LSPCompletionItem(label: "printf", kind: .function, detail: "(format: str, ...) -> None", documentation: nil, insertText: nil, sortText: nil)
        ],
        selectedIndex: 0,
        onSelect: { _ in }
    )
    .padding()
}
