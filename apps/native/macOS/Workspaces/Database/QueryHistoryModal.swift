//
//  QueryHistoryModal.swift
//  MagnetarStudio (macOS)
//
//  Query history viewer modal - Extracted from DatabaseModals.swift (Phase 6.14)
//  Enhanced with search, hover actions, and visual polish
//

import SwiftUI
import AppKit

struct QueryHistoryModal: View {
    @Binding var isPresented: Bool
    var databaseStore: DatabaseStore

    @State private var historyItems: [QueryHistoryItem] = []
    @State private var isLoading: Bool = false
    @State private var errorMessage: String? = nil
    @State private var searchText: String = ""

    var filteredItems: [QueryHistoryItem] {
        if searchText.isEmpty {
            return historyItems
        }
        return historyItems.filter {
            $0.query.localizedCaseInsensitiveContains(searchText)
        }
    }

    var body: some View {
        StructuredModal(title: "Query History", isPresented: $isPresented) {
            VStack(spacing: 0) {
                // Search bar
                if !historyItems.isEmpty {
                    HStack(spacing: 8) {
                        Image(systemName: "magnifyingglass")
                            .foregroundStyle(.secondary)
                        TextField("Search queries...", text: $searchText)
                            .textFieldStyle(.plain)
                        if !searchText.isEmpty {
                            Button(action: { searchText = "" }) {
                                Image(systemName: "xmark.circle.fill")
                                    .foregroundStyle(.secondary)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(10)
                    .background(.quaternary.opacity(0.5))
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)

                    Divider()
                }

                if isLoading {
                    ProgressView("Loading history...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if let error = errorMessage {
                    VStack(spacing: 16) {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.system(size: 48))
                            .foregroundColor(.orange)
                        Text("Error")
                            .font(.headline)
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                        Button("Retry") {
                            Task { await loadHistory() }
                        }
                        .buttonStyle(.borderedProminent)
                        .tint(.orange)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if historyItems.isEmpty {
                    VStack(spacing: 16) {
                        Image(systemName: "clock.arrow.circlepath")
                            .font(.system(size: 48))
                            .foregroundStyle(.tertiary)
                        Text("No Query History")
                            .font(.headline)
                            .foregroundStyle(.secondary)
                        Text("Execute some queries to see them here")
                            .font(.subheadline)
                            .foregroundStyle(.tertiary)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if filteredItems.isEmpty {
                    VStack(spacing: 16) {
                        Image(systemName: "magnifyingglass")
                            .font(.system(size: 48))
                            .foregroundStyle(.tertiary)
                        Text("No Matches")
                            .font(.headline)
                            .foregroundStyle(.secondary)
                        Text("Try a different search term")
                            .font(.subheadline)
                            .foregroundStyle(.tertiary)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    ScrollView {
                        LazyVStack(spacing: 2) {
                            ForEach(filteredItems) { item in
                                QueryHistoryRow(
                                    item: item,
                                    onSelect: {
                                        databaseStore.loadEditorText(item.query, contentType: .sql)
                                        isPresented = false
                                    },
                                    onCopy: {
                                        NSPasteboard.general.clearContents()
                                        NSPasteboard.general.setString(item.query, forType: .string)
                                    }
                                )
                            }
                        }
                        .padding(.vertical, 8)
                        .padding(.horizontal, 8)
                    }
                }
            }
        }
        .onAppear {
            Task { await loadHistory() }
        }
    }

    @MainActor
    private func loadHistory() async {
        guard let sessionId = databaseStore.sessionId else { return }

        isLoading = true
        errorMessage = nil

        do {
            let response: QueryHistoryResponse = try await ApiClient.shared.request(
                path: "/v1/sessions/\(sessionId)/query-history",
                method: .get
            )
            historyItems = response.history
            isLoading = false
        } catch {
            errorMessage = error.localizedDescription
            isLoading = false
        }
    }
}

struct QueryHistoryRow: View {
    let item: QueryHistoryItem
    let onSelect: () -> Void
    var onCopy: (() -> Void)? = nil

    @State private var isHovered = false
    @State private var showCopied = false

    var body: some View {
        HStack(spacing: 12) {
            // Status indicator
            Image(systemName: item.statusIcon)
                .font(.system(size: 14))
                .foregroundColor(item.status == "success" ? .green : .red)
                .frame(width: 20)

            // Query content
            VStack(alignment: .leading, spacing: 6) {
                Text(item.query)
                    .font(.system(size: 13, design: .monospaced))
                    .lineLimit(2)
                    .foregroundColor(.primary)
                    .frame(maxWidth: .infinity, alignment: .leading)

                HStack(spacing: 12) {
                    // Relative timestamp
                    Label(item.relativeTimestamp, systemImage: "clock")

                    // Execution time
                    if let execTime = item.formattedExecutionTime {
                        Label(execTime, systemImage: "speedometer")
                    }

                    // Row count
                    if let rowCount = item.formattedRowCount {
                        Label(rowCount, systemImage: "tablecells")
                    }
                }
                .font(.caption)
                .foregroundStyle(.secondary)
            }

            Spacer()

            // Hover actions
            if isHovered {
                HStack(spacing: 4) {
                    // Copy button
                    Button(action: {
                        onCopy?()
                        withAnimation { showCopied = true }
                        DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                            withAnimation { showCopied = false }
                        }
                    }) {
                        Image(systemName: showCopied ? "checkmark" : "doc.on.doc")
                            .font(.system(size: 12))
                            .foregroundColor(showCopied ? .green : .secondary)
                            .frame(width: 28, height: 28)
                            .background(
                                Circle()
                                    .fill(showCopied ? Color.green.opacity(0.1) : Color.gray.opacity(0.1))
                            )
                    }
                    .buttonStyle(.plain)
                    .help("Copy query")

                    // Load button
                    Button(action: onSelect) {
                        Image(systemName: "arrow.right.circle")
                            .font(.system(size: 12))
                            .foregroundColor(.blue)
                            .frame(width: 28, height: 28)
                            .background(
                                Circle()
                                    .fill(Color.blue.opacity(0.1))
                            )
                    }
                    .buttonStyle(.plain)
                    .help("Load in editor")
                }
                .transition(.opacity.combined(with: .scale(scale: 0.9)))
            } else {
                Image(systemName: "chevron.right")
                    .font(.caption)
                    .foregroundStyle(.tertiary)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(isHovered ? Color.blue.opacity(0.05) : Color.clear)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .contentShape(Rectangle())
        .onTapGesture {
            onSelect()
        }
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
    }
}
