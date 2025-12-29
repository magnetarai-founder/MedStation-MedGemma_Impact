//
//  QueryHistoryModal.swift
//  MagnetarStudio (macOS)
//
//  Query history viewer modal - Extracted from DatabaseModals.swift (Phase 6.14)
//

import SwiftUI

struct QueryHistoryModal: View {
    @Binding var isPresented: Bool
    var databaseStore: DatabaseStore

    @State private var historyItems: [QueryHistoryItem] = []
    @State private var isLoading: Bool = false
    @State private var errorMessage: String? = nil

    var body: some View {
        StructuredModal(title: "Query History", isPresented: $isPresented) {
            VStack(spacing: 0) {
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
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if historyItems.isEmpty {
                    VStack(spacing: 16) {
                        Image(systemName: "clock")
                            .font(.system(size: 48))
                            .foregroundColor(.secondary)
                        Text("No query history yet")
                            .font(.headline)
                        Text("Execute some queries to see them here")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    ScrollView {
                        LazyVStack(spacing: 0) {
                            ForEach(historyItems) { item in
                                QueryHistoryRow(item: item, onSelect: {
                                    databaseStore.loadEditorText(item.query, contentType: .sql)
                                    isPresented = false
                                })
                                .padding(.horizontal, 16)

                                if item.id != historyItems.last?.id {
                                    Divider()
                                }
                            }
                        }
                        .padding(.vertical, 8)
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

    var body: some View {
        Button(action: onSelect) {
            VStack(alignment: .leading, spacing: 8) {
                Text(item.query)
                    .font(.system(size: 13, design: .monospaced))
                    .lineLimit(2)
                    .foregroundColor(.primary)

                HStack(spacing: 16) {
                    Label(item.timestamp, systemImage: "clock")
                    if let execTime = item.executionTime {
                        Label("\(execTime)ms", systemImage: "speedometer")
                    }
                    if let rowCount = item.rowCount {
                        Label("\(rowCount) rows", systemImage: "tablecells")
                    }
                }
                .font(.caption)
                .foregroundColor(.secondary)
            }
            .padding(.vertical, 8)
        }
        .buttonStyle(.plain)
    }
}
