//
//  ResultsTable.swift
//  MagnetarStudio
//
//  Results table with toolbar matching React ResultsTable.tsx specs
//  - Toolbar: Export dropdown, Download, Analyze with AI, Clear
//  - Table with sticky header, truncated cells, null values in italic gray
//

import SwiftUI

struct ResultsTable: View {
    @State private var results: QueryResults?
    @State private var isLoading: Bool = false
    @State private var isExporting: Bool = false
    @State private var exportFormat: ExportFormat = .excel

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
    }

    // MARK: - Toolbar

    private var toolbar: some View {
        HStack(spacing: 12) {
            // Export dropdown + Download
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
                            .font(.system(size: 11))
                        Image(systemName: "chevron.down")
                            .font(.system(size: 8))
                    }
                    .foregroundColor(.primary)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                }
                .buttonStyle(.plain)
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
            }

            // Analyze with AI
            ToolbarButton(action: {
                // Analyze with AI
            }) {
                HStack(spacing: 6) {
                    Image(systemName: "message")
                        .font(.system(size: 16))
                    Text("Analyze with AI")
                        .font(.system(size: 13))
                }
            }
            .disabled(results == nil)
            .opacity(results == nil ? 0.4 : 1.0)
            .help("Analyze with AI")

            Spacer()

            // Clear results
            ToolbarGroup {
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
        }
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

                // Data rows
                ForEach(0..<results.rows.count, id: \.self) { rowIndex in
                    HStack(spacing: 0) {
                        ForEach(0..<results.columns.count, id: \.self) { colIndex in
                            let value = results.rows[rowIndex][colIndex]

                            if value == nil {
                                Text("null")
                                    .font(.system(size: 12))
                                    .italic()
                                    .foregroundColor(.secondary)
                                    .lineLimit(1)
                                    .truncationMode(.tail)
                                    .frame(minWidth: 120, alignment: .leading)
                                    .padding(.horizontal, 16)
                                    .padding(.vertical, 8)
                            } else {
                                Text(value!)
                                    .font(.system(size: 12))
                                    .foregroundColor(.primary)
                                    .lineLimit(1)
                                    .truncationMode(.tail)
                                    .frame(minWidth: 120, alignment: .leading)
                                    .padding(.horizontal, 16)
                                    .padding(.vertical, 8)
                            }
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

// MARK: - Preview

#Preview {
    ResultsTable()
        .frame(height: 400)
}
