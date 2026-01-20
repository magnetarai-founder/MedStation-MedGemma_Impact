//
//  ResultsTable.swift
//  MagnetarStudio
//
//  Results table with toolbar matching React ResultsTable.tsx specs
//  - Toolbar: Export dropdown, Download, Analyze with AI, Clear
//  - Table with sticky header, truncated cells, null values in italic gray
//  Enhanced with row count display, copy feedback, and visual polish
//

import SwiftUI
import AppKit
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "ResultsTable")

struct ResultsTable: View {
    @Environment(ChatStore.self) private var chatStore
    @Environment(DatabaseStore.self) private var databaseStore
    @State private var results: QueryResults?
    @State private var isLoading: Bool = false
    @State private var isExporting: Bool = false
    @State private var exportFormat: ExportFormat = .excel
    @State private var isAnalyzing: Bool = false
    @State private var showCopied: Bool = false
    @State private var copiedText: String = ""

    var body: some View {
        VStack(spacing: 0) {
            // Toolbar
            toolbar
                .padding(.horizontal, 8)
                .padding(.vertical, 8)
                .background(Color(.controlBackgroundColor).opacity(0.5))
                .overlay(
                    Rectangle()
                        .fill(Color.gray.opacity(0.6))
                        .frame(height: 2),
                    alignment: .bottom
                )

            // Table or empty state
            if isLoading {
                loadingView
            } else if let results = results {
                resultsTableView(results)
            } else {
                emptyStateView
            }
        }
        .onChange(of: databaseStore.currentQuery == nil) { _, isNil in
            if isNil { results = nil }
        }
    }

    // MARK: - Toolbar

    private var toolbar: some View {
        HStack(spacing: 12) {
            // Row count badge
            if let results = results {
                HStack(spacing: 6) {
                    Image(systemName: "tablecells")
                        .font(.system(size: 12))
                    Text(results.formattedRowCount)
                        .font(.system(size: 12, weight: .medium))
                    Text("×")
                        .font(.system(size: 10))
                        .foregroundStyle(.tertiary)
                    Text("\(results.columns.count) cols")
                        .font(.system(size: 12))
                }
                .foregroundStyle(.secondary)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(Color.blue.opacity(0.1))
                .clipShape(Capsule())
            }

            // Copy all button
            Button(action: copyAllResults) {
                HStack(spacing: 4) {
                    Image(systemName: showCopied ? "checkmark" : "doc.on.doc")
                        .font(.system(size: 12))
                    Text(showCopied ? "Copied!" : "Copy All")
                        .font(.system(size: 11, weight: .medium))
                }
                .foregroundColor(showCopied ? .green : .secondary)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(
                    Capsule()
                        .fill(showCopied ? Color.green.opacity(0.1) : Color.gray.opacity(0.1))
                )
            }
            .buttonStyle(.plain)
            .disabled(results == nil)
            .help("Copy all results to clipboard")

            Divider()
                .frame(height: 20)

            // Analyze with AI - first button
            ToolbarIconButton(
                icon: "message",
                isDisabled: results == nil || isAnalyzing,
                action: {
                    guard let results = results else { return }
                    Task {
                        await analyzeWithAI(results)
                    }
                }
            ) {
                HStack(spacing: 6) {
                    if isAnalyzing {
                        ProgressView()
                            .scaleEffect(0.7)
                    } else {
                        Image(systemName: "message")
                            .font(.system(size: 16))
                    }
                    Text(isAnalyzing ? "Analyzing..." : "Analyze with AI")
                        .font(.system(size: 11, weight: .medium))
                }
            }
            .help("Analyze query results with AI")

            // Export dropdown + Download + Trash
            ToolbarGroup {
                // Export format picker
                Menu {
                    Button("Excel (.xlsx)") { exportFormat = .excel }
                    Button("CSV") { exportFormat = .csv }
                    Button("Parquet") { exportFormat = .parquet }
                    Button("JSON") { exportFormat = .json }
                } label: {
                    HStack(spacing: 4) {
                        Text(exportFormat.rawValue)
                            .font(.system(size: 11, weight: .medium))
                        Image(systemName: "chevron.down")
                            .font(.system(size: 10, weight: .semibold))
                    }
                    .foregroundColor(.primary)
                    .frame(height: 28)
                }
                .help("Export Format")

                ToolbarIconButton(
                    icon: isExporting ? "arrow.triangle.2.circlepath" : "arrow.down.circle",
                    isDisabled: results == nil,
                    action: {
                        isExporting.toggle()
                    }
                ) {
                    if isExporting {
                        ProgressView()
                            .scaleEffect(0.7)
                    } else {
                        Image(systemName: "arrow.down.circle")
                            .font(.system(size: 16))
                    }
                }
                .help("Download")

                // Clear results
                ToolbarIconButton(
                    icon: "trash",
                    isDisabled: results == nil,
                    action: {
                        results = nil
                    }
                ) {
                    Image(systemName: "trash")
                        .font(.system(size: 16))
                }
                .help("Clear Results")
            }

            Spacer()
        }
    }

    // MARK: - Copy Results

    private func copyAllResults() {
        guard let results = results else { return }

        // Build TSV format for easy pasting
        var text = results.columns.joined(separator: "\t") + "\n"
        for row in results.rows {
            text += row.map { $0 ?? "null" }.joined(separator: "\t") + "\n"
        }

        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(text, forType: .string)

        withAnimation { showCopied = true }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
            withAnimation { showCopied = false }
        }
    }

    // MARK: - AI Analysis

    private func analyzeWithAI(_ results: QueryResults) async {
        isAnalyzing = true
        defer { isAnalyzing = false }

        // Build a summary of the results for AI analysis
        let rowCount = results.rows.count
        let columnList = results.columns.joined(separator: ", ")

        // Sample first few rows for context (limit to prevent token overload)
        let sampleRows = results.rows.prefix(5).map { row in
            row.map { $0 ?? "null" }.joined(separator: " | ")
        }.joined(separator: "\n")

        let prompt = """
        Please analyze these query results and provide insights:

        **Columns**: \(columnList)
        **Row count**: \(rowCount)\(results.isLimited ? " (limited preview)" : "")

        **Sample data**:
        \(sampleRows)

        What patterns, anomalies, or insights do you see? Are there any data quality issues?
        """

        logger.info("Sending results to AI for analysis: \(rowCount) rows, \(results.columns.count) columns")
        await chatStore.sendMessage(prompt)
    }

    // MARK: - Results Table View

    private func resultsTableView(_ results: QueryResults) -> some View {
        ScrollView([.horizontal, .vertical]) {
            VStack(spacing: 0) {
                // Header row (sticky)
                HStack(spacing: 0) {
                    ForEach(results.columns, id: \.self) { column in
                        Text(column)
                            .font(.system(size: 13, weight: .semibold))
                            .foregroundColor(.primary)
                            .lineLimit(1)
                            .truncationMode(.tail)
                            .frame(minWidth: 120, alignment: .leading)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 8)
                            .background(Color(.controlBackgroundColor))
                    }
                }
                .overlay(
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 1),
                    alignment: .bottom
                )

                // Data rows - LazyVStack for better performance with large datasets
                LazyVStack(spacing: 0) {
                    ForEach(0..<results.rows.count, id: \.self) { rowIndex in
                        HStack(spacing: 0) {
                            ForEach(0..<results.columns.count, id: \.self) { colIndex in
                                TableCell(value: results.rows[rowIndex][colIndex])
                            }
                        }
                        .overlay(
                            Rectangle()
                                .fill(Color.gray.opacity(0.1))
                                .frame(height: 1),
                            alignment: .bottom
                        )
                    }
                }
            }
        }
        .overlay(
            // Footer message if limited
            VStack {
                Spacer()
                if results.isLimited {
                    Text("Showing first \(results.rows.count) rows...")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                        .padding(8)
                        .background(Color(.controlBackgroundColor).opacity(0.9))
                        .cornerRadius(6)
                        .padding(.bottom, 8)
                }
            }
        )
    }

    // MARK: - Empty State

    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Image(systemName: "tablecells")
                .font(.system(size: 48))
                .foregroundColor(.secondary)

            Text("Execute a query to view results")
                .font(.system(size: 14))
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Loading View

    private var loadingView: some View {
        ZStack {
            Color.black.opacity(0.1)

            VStack(spacing: 12) {
                ProgressView()
                    .scaleEffect(1.2)

                Text("Loading preview...")
                    .font(.system(size: 13))
                    .foregroundColor(.secondary)
            }
            .padding(24)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(Color(.controlBackgroundColor))
                    .shadow(radius: 8)
            )
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: - Models

enum ExportFormat: String {
    case excel = "Excel"
    case csv = "CSV"
    case parquet = "Parquet"
    case json = "JSON"
}

struct QueryResults {
    let columns: [String]
    let rows: [[String?]]
    let isLimited: Bool

    /// Formatted row count string
    var formattedRowCount: String {
        let count = rows.count
        if count >= 1000 {
            return String(format: "%.1fk rows", Double(count) / 1000)
        }
        return "\(count) rows"
    }

    static let mock = QueryResults(
        columns: ["id", "name", "email", "created_at"],
        rows: [
            ["1", "Alice Johnson", "alice@example.com", "2024-01-15"],
            ["2", "Bob Smith", nil, "2024-01-16"],
            ["3", "Carol Davis", "carol@example.com", "2024-01-17"]
        ],
        isLimited: false
    )
}

// MARK: - Table Cell Component

struct TableCell: View {
    let value: String?

    @State private var isHovered = false
    @State private var showCopied = false

    var body: some View {
        HStack(spacing: 4) {
            if let value = value {
                Text(value)
                    .font(.system(size: 12))
                    .foregroundColor(.primary)
                    .lineLimit(1)
                    .truncationMode(.tail)
            } else {
                Text("null")
                    .font(.system(size: 12))
                    .italic()
                    .foregroundColor(.secondary)
                    .lineLimit(1)
                    .truncationMode(.tail)
            }

            Spacer(minLength: 4)

            // Copy button on hover
            if isHovered && value != nil {
                Button(action: copyValue) {
                    Image(systemName: showCopied ? "checkmark" : "doc.on.doc")
                        .font(.system(size: 10))
                        .foregroundColor(showCopied ? .green : .secondary)
                }
                .buttonStyle(.plain)
                .transition(.opacity)
            }
        }
        .frame(minWidth: 120, alignment: .leading)
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(isHovered ? Color.blue.opacity(0.03) : Color.clear)
        .contentShape(Rectangle())
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.1)) {
                isHovered = hovering
            }
        }
    }

    private func copyValue() {
        guard let value = value else { return }
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(value, forType: .string)

        withAnimation { showCopied = true }
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            withAnimation { showCopied = false }
        }
    }
}

// MARK: - Preview

#Preview {
    ResultsTable()
        .environment(ChatStore())
        .environment(DatabaseStore.shared)
        .frame(height: 400)
}
