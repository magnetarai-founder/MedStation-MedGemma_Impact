//
//  QueryLibraryModal.swift
//  MagnetarStudio (macOS)
//
//  Saved queries library modal - Extracted from DatabaseModals.swift (Phase 6.14)
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "QueryLibraryModal")

struct QueryLibraryModal: View {
    @Binding var isPresented: Bool
    var databaseStore: DatabaseStore

    @State private var savedQueries: [SavedQuery] = []
    @State private var isLoading: Bool = false
    @State private var errorMessage: String? = nil

    var body: some View {
        StructuredModal(title: "Query Library", isPresented: $isPresented) {
            VStack(spacing: 0) {
                // Content
                if isLoading {
                    ProgressView("Loading library...")
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if let error = errorMessage {
                    VStack(spacing: 16) {
                        Image(systemName: "exclamationmark.triangle")
                            .font(.system(size: 48))
                            .foregroundStyle(.orange)
                        Text("Error")
                            .font(.headline)
                        Text(error)
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Button("Retry") {
                            Task { await loadQueries() }
                        }
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if savedQueries.isEmpty {
                    VStack(spacing: 16) {
                        Image(systemName: "folder")
                            .font(.system(size: 48))
                            .foregroundStyle(.secondary)
                        Text("No saved queries yet")
                            .font(.headline)
                        Text("Save your frequently used queries for quick access")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                            .multilineTextAlignment(.center)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    ScrollView {
                        LazyVStack(spacing: 0) {
                            ForEach(savedQueries) { query in
                                SavedQueryRow(
                                    query: query,
                                    onLoad: {
                                        databaseStore.loadEditorText(query.query, contentType: .sql)
                                        isPresented = false
                                    },
                                    onUpdate: { newName, newDescription, newSQL in
                                        Task { await updateQuery(id: query.id, name: newName, description: newDescription, sql: newSQL) }
                                    },
                                    onDelete: {
                                        Task { await deleteQuery(id: query.id) }
                                    }
                                )
                                .padding(.horizontal, 16)

                                if query.id != savedQueries.last?.id {
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
            Task { await loadQueries() }
        }
    }

    @MainActor
    private func loadQueries() async {
        isLoading = true
        errorMessage = nil

        do {
            let response: SavedQueriesResponse = try await ApiClient.shared.request(
                path: "/saved-queries?query_type=sql",
                method: .get
            )
            savedQueries = response.queries
            isLoading = false
        } catch {
            logger.debug("Failed to load queries: \(error)")
            if let decodingError = error as? DecodingError {
                logger.debug("Decoding error details: \(decodingError)")
            }
            errorMessage = error.localizedDescription
            isLoading = false
        }
    }

    @MainActor
    private func updateQuery(id: Int, name: String, description: String, sql: String) async {
        do {
            var jsonBody: [String: Any] = [
                "name": name,
                "query": sql
            ]
            if !description.isEmpty {
                jsonBody["description"] = description
            }

            let _: EmptyResponse = try await ApiClient.shared.request(
                path: "/saved-queries/\(id)",
                method: .put,
                jsonBody: jsonBody
            )
            await loadQueries()
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    @MainActor
    private func deleteQuery(id: Int) async {
        do {
            let _: EmptyResponse = try await ApiClient.shared.request(
                path: "/saved-queries/\(id)",
                method: .delete
            )
            await loadQueries()
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

struct SavedQueryRow: View {
    let query: SavedQuery
    let onLoad: () -> Void
    let onUpdate: (String, String, String) -> Void  // name, description, sql
    let onDelete: () -> Void

    @State private var isHovering: Bool = false
    @State private var showEditDialog: Bool = false

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 8) {
                Text(query.name)
                    .font(.headline)
                    .foregroundStyle(.primary)

                Text(query.query)
                    .font(.system(size: 11, design: .monospaced))
                    .lineLimit(2)
                    .foregroundStyle(.secondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            // Hover action buttons
            if isHovering {
                HStack(spacing: 8) {
                    // Pencil - Edit
                    Button(action: {
                        showEditDialog = true
                    }) {
                        Image(systemName: "pencil")
                            .font(.system(size: 14))
                            .foregroundStyle(.secondary)
                            .frame(width: 28, height: 28)
                            .background(Color.gray.opacity(0.1))
                            .clipShape(Circle())
                    }
                    .buttonStyle(.plain)
                    .help("Edit query")

                    // Trash - Delete
                    Button(action: onDelete) {
                        Image(systemName: "trash")
                            .font(.system(size: 14))
                            .foregroundStyle(.red)
                            .frame(width: 28, height: 28)
                            .background(Color.red.opacity(0.1))
                            .clipShape(Circle())
                    }
                    .buttonStyle(.plain)
                    .help("Delete")

                    // Arrow - Load
                    Button(action: onLoad) {
                        Image(systemName: "arrow.right")
                            .font(.system(size: 14))
                            .foregroundStyle(.blue)
                            .frame(width: 28, height: 28)
                            .background(Color.blue.opacity(0.1))
                            .clipShape(Circle())
                    }
                    .buttonStyle(.plain)
                    .help("Load into editor")
                }
            }
        }
        .padding(.vertical, 8)
        .padding(.horizontal, 12)
        .background(isHovering ? Color.gray.opacity(0.05) : Color.clear)
        .cornerRadius(8)
        .onHover { hovering in
            isHovering = hovering
        }
        .sheet(isPresented: $showEditDialog) {
            EditQueryDialog(
                isPresented: $showEditDialog,
                query: query,
                onUpdate: onUpdate
            )
        }
    }
}
