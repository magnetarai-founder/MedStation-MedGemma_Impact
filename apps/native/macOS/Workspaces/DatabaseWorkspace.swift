//
//  DatabaseWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Database workspace matching React specs exactly:
//  - Left: 320pt resizable sidebar (FileUpload + icon row + SidebarTabs)
//  - Right: Vertical split (CodeEditor top + ResultsTable bottom)
//

import SwiftUI

struct DatabaseWorkspace: View {
    @EnvironmentObject private var databaseStore: DatabaseStore
    @State private var sidebarWidth: CGFloat = 320
    @State private var topPaneHeight: CGFloat = 0.33 // 33% default
    @State private var showLibrary = false
    @State private var showQueryHistory = false
    @State private var showJsonConverter = false

    var body: some View {
        GeometryReader { geometry in
            HStack(spacing: 0) {
                // Left Sidebar (resizable, 320pt default)
                leftSidebar
                    .frame(width: max(320, min(sidebarWidth, geometry.size.width * 0.4)))

                Divider()

                // Right Content (vertical split)
                rightContent(geometry: geometry)
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
        .sheet(isPresented: $showLibrary) {
            QueryLibraryModal(isPresented: $showLibrary, databaseStore: databaseStore)
        }
        .sheet(isPresented: $showQueryHistory) {
            QueryHistoryModal(isPresented: $showQueryHistory, databaseStore: databaseStore)
        }
        .sheet(isPresented: $showJsonConverter) {
            JsonConverterModal(isPresented: $showJsonConverter, databaseStore: databaseStore)
        }
    }

    // MARK: - Left Sidebar

    private var leftSidebar: some View {
        VStack(spacing: 0) {
            // Top: File Upload
            FileUpload()

            // Icon toolbar row
            iconToolbarRow
                .padding(.vertical, 8)
                .overlay(
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 1),
                    alignment: .bottom
                )

            // Tabs: Columns | Logs
            SidebarTabs()
        }
        .background(Color(.controlBackgroundColor).opacity(0.3))
    }

    private var iconToolbarRow: some View {
        HStack(spacing: 8) {
            Spacer()

            // Query Library
            IconToolbarButton(icon: "folder", action: {
                showLibrary = true
            })
            .help("Query Library")

            // Query History
            IconToolbarButton(icon: "clock", action: {
                showQueryHistory = true
            })
            .help("Query History")

            // JSON Converter
            IconToolbarButton(icon: "doc.text", action: {
                showJsonConverter = true
            })
            .help("JSON Converter")

            // Clear workspace
            IconToolbarButton(icon: "trash", action: {
                NotificationCenter.default.post(name: .clearWorkspace, object: nil)
            })
            .help("Clear Workspace")

            Spacer()
        }
    }

    // MARK: - Right Content (Vertical Split)

    private func rightContent(geometry: GeometryProxy) -> some View {
        let totalHeight = geometry.size.height
        let topHeight = totalHeight * topPaneHeight

        return VStack(spacing: 0) {
            // Top: Code Editor
            CodeEditor()
                .frame(height: max(150, topHeight))

            // Drag handle
            DragHandle()
                .frame(height: 6)
                .gesture(
                    DragGesture()
                        .onChanged { value in
                            let newHeight = topHeight + value.translation.height
                            let ratio = newHeight / totalHeight
                            topPaneHeight = max(0.2, min(0.8, ratio))
                        }
                )

            // Bottom: Results Table
            ResultsTable()
                .frame(maxHeight: .infinity)
        }
    }
}

// MARK: - Icon Toolbar Button

struct IconToolbarButton: View {
    let icon: String
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 18))
                .foregroundColor(isHovered ? Color.magnetarPrimary : .secondary)
                .frame(width: 32, height: 32)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(isHovered ? Color.white.opacity(0.6) : Color.clear)
                )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.2)) {
                isHovered = hovering
            }
        }
    }
}

// MARK: - Drag Handle

struct DragHandle: View {
    @State private var isHovered = false
    @State private var isDragging = false

    var body: some View {
        ZStack {
            // Background bar
            Rectangle()
                .fill(isDragging ? Color.magnetarPrimary : Color.gray)
                .opacity(isDragging ? 1.0 : 0.5)

            // Grip icon (on hover)
            if isHovered || isDragging {
                Image(systemName: "line.3.horizontal")
                    .font(.system(size: 12))
                    .foregroundColor(.white)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 4)
                    .background(
                        Capsule()
                            .fill(isDragging ? Color.magnetarPrimary : Color.gray)
                    )
            }
        }
        .frame(maxWidth: .infinity)
        .contentShape(Rectangle()) // Make entire area draggable
        .onHover { hovering in
            isHovered = hovering
        }
        .gesture(
            DragGesture()
                .onChanged { _ in
                    isDragging = true
                }
                .onEnded { _ in
                    isDragging = false
                }
        )
        .cursor(.resizeUpDown)
    }
}

// MARK: - Cursor Extension

extension View {
    func cursor(_ cursor: NSCursor) -> some View {
        self.onContinuousHover { phase in
            switch phase {
            case .active:
                cursor.push()
            case .ended:
                NSCursor.pop()
            }
        }
    }
}

// MARK: - Structured Modal

struct StructuredModal<Content: View>: View {
    let title: String
    @Binding var isPresented: Bool
    @ViewBuilder let content: Content

    var body: some View {
        VStack(spacing: 0) {
            // Header with title + close X
            HStack {
                Text(title)
                    .font(.title2)
                    .fontWeight(.semibold)

                Spacer()

                Button {
                    isPresented = false
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 14))
                        .foregroundColor(.secondary)
                        .frame(width: 28, height: 28)
                        .background(
                            Circle()
                                .fill(Color(nsColor: .controlBackgroundColor))
                        )
                }
                .buttonStyle(.plain)
                .help("Close (Esc)")
                .keyboardShortcut(.cancelAction)
            }
            .padding(.horizontal, 24)
            .padding(.vertical, 16)

            Divider()

            // Content
            content
        }
        .frame(width: 700, height: 500)
        .background(Color(nsColor: .windowBackgroundColor))
        .cornerRadius(12)
        .shadow(radius: 20)
    }
}

// MARK: - Query History Modal

struct QueryHistoryModal: View {
    @Binding var isPresented: Bool
    @ObservedObject var databaseStore: DatabaseStore

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
                    List {
                        ForEach(historyItems) { item in
                            QueryHistoryRow(item: item, onSelect: {
                                databaseStore.loadEditorText(item.query, contentType: .sql)
                                isPresented = false
                            })
                        }
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

// MARK: - Query Library Modal

struct QueryLibraryModal: View {
    @Binding var isPresented: Bool
    @ObservedObject var databaseStore: DatabaseStore

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
                            .foregroundColor(.orange)
                        Text("Error")
                            .font(.headline)
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.secondary)
                        Button("Retry") {
                            Task { await loadQueries() }
                        }
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else if savedQueries.isEmpty {
                    VStack(spacing: 16) {
                        Image(systemName: "folder")
                            .font(.system(size: 48))
                            .foregroundColor(.secondary)
                        Text("No saved queries yet")
                            .font(.headline)
                        Text("Save your frequently used queries for quick access")
                            .font(.caption)
                            .foregroundColor(.secondary)
                            .multilineTextAlignment(.center)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                } else {
                    List {
                        ForEach(savedQueries) { query in
                            SavedQueryRow(
                                query: query,
                                onLoad: {
                                    databaseStore.loadEditorText(query.query, contentType: .sql)
                                    isPresented = false
                                },
                                onRename: { newName in
                                    Task { await renameQuery(id: query.id, newName: newName) }
                                },
                                onDelete: {
                                    Task { await deleteQuery(id: query.id) }
                                }
                            )
                        }
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
            print("DEBUG: Failed to load queries - \(error)")
            if let decodingError = error as? DecodingError {
                print("DEBUG: Decoding error details - \(decodingError)")
            }
            errorMessage = error.localizedDescription
            isLoading = false
        }
    }

    @MainActor
    private func renameQuery(id: Int, newName: String) async {
        do {
            let _: EmptyResponse = try await ApiClient.shared.request(
                path: "/saved-queries/\(id)",
                method: .put,
                jsonBody: ["name": newName]
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
    let onRename: (String) -> Void
    let onDelete: () -> Void

    @State private var isHovering: Bool = false
    @State private var showRenameDialog: Bool = false

    var body: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 8) {
                Text(query.name)
                    .font(.headline)
                    .foregroundColor(.primary)

                Text(query.query)
                    .font(.system(size: 11, design: .monospaced))
                    .lineLimit(2)
                    .foregroundColor(.secondary)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            // Hover action buttons
            if isHovering {
                HStack(spacing: 8) {
                    // Pencil - Rename
                    Button(action: {
                        showRenameDialog = true
                    }) {
                        Image(systemName: "pencil")
                            .font(.system(size: 14))
                            .foregroundColor(.secondary)
                            .frame(width: 28, height: 28)
                            .background(Color.gray.opacity(0.1))
                            .clipShape(Circle())
                    }
                    .buttonStyle(.plain)
                    .help("Rename")

                    // Trash - Delete
                    Button(action: onDelete) {
                        Image(systemName: "trash")
                            .font(.system(size: 14))
                            .foregroundColor(.red)
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
                            .foregroundColor(.blue)
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
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovering = hovering
            }
        }
        .sheet(isPresented: $showRenameDialog) {
            RenameQueryDialog(
                isPresented: $showRenameDialog,
                currentName: query.name,
                onRename: onRename
            )
        }
    }
}

// MARK: - Rename Query Dialog

struct RenameQueryDialog: View {
    @Binding var isPresented: Bool
    let currentName: String
    let onRename: (String) -> Void

    @State private var newName: String = ""

    var body: some View {
        VStack(spacing: 20) {
            Text("Rename Query")
                .font(.title2)
                .fontWeight(.semibold)

            VStack(alignment: .leading, spacing: 8) {
                Text("New Name")
                    .font(.system(size: 13, weight: .medium))
                TextField("Query name", text: $newName)
                    .textFieldStyle(.roundedBorder)
            }

            HStack(spacing: 12) {
                Button("Cancel") {
                    isPresented = false
                }
                .buttonStyle(.bordered)

                Button("Rename") {
                    if !newName.isEmpty {
                        onRename(newName)
                    }
                    isPresented = false
                }
                .buttonStyle(.borderedProminent)
                .disabled(newName.isEmpty || newName == currentName)
            }
        }
        .padding(24)
        .frame(width: 400)
        .onAppear {
            newName = currentName
        }
    }
}


struct SaveQueryDialog: View {
    @Binding var isPresented: Bool
    let queryText: String
    @ObservedObject var databaseStore: DatabaseStore

    @State private var queryName: String = ""
    @State private var queryDescription: String = ""
    @State private var isSaving: Bool = false
    @State private var errorMessage: String? = nil

    var body: some View {
        VStack(spacing: 20) {
            Text("Save Query")
                .font(.title2)
                .fontWeight(.semibold)

            VStack(alignment: .leading, spacing: 8) {
                Text("Name")
                    .font(.system(size: 13, weight: .medium))
                TextField("Query name", text: $queryName)
                    .textFieldStyle(.roundedBorder)
            }

            VStack(alignment: .leading, spacing: 8) {
                Text("Description (optional)")
                    .font(.system(size: 13, weight: .medium))
                TextField("Description", text: $queryDescription)
                    .textFieldStyle(.roundedBorder)
            }

            if let error = errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
            }

            HStack(spacing: 12) {
                Button("Cancel") {
                    isPresented = false
                }
                .buttonStyle(.bordered)

                Button(isSaving ? "Saving..." : "Save") {
                    Task { await saveQuery() }
                }
                .buttonStyle(.borderedProminent)
                .disabled(queryName.isEmpty || isSaving)
            }
        }
        .padding(24)
        .frame(width: 400)
    }

    @MainActor
    private func saveQuery() async {
        isSaving = true
        errorMessage = nil

        do {
            var jsonBody: [String: Any] = [
                "name": queryName,
                "query": queryText,
                "query_type": "sql"
            ]
            if !queryDescription.isEmpty {
                jsonBody["description"] = queryDescription
            }

            let _: SaveQueryResponse = try await ApiClient.shared.request(
                path: "/saved-queries",
                method: .post,
                jsonBody: jsonBody
            )

            isSaving = false
            isPresented = false
        } catch {
            errorMessage = error.localizedDescription
            isSaving = false
        }
    }
}

// MARK: - JSON Converter Modal

struct JsonConverterModal: View {
    @Binding var isPresented: Bool
    @ObservedObject var databaseStore: DatabaseStore

    @State private var jsonInput: String = ""
    @State private var isConverting: Bool = false
    @State private var errorMessage: String? = nil
    @State private var successMessage: String? = nil

    var body: some View {
        StructuredModal(title: "JSON to Excel Converter", isPresented: $isPresented) {
            VStack(spacing: 20) {
                // Instructions
                VStack(alignment: .leading, spacing: 8) {
                    Text("Paste your JSON data below to convert it to Excel format")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    Text("The JSON should be an array of objects with consistent keys")
                        .font(.caption2)
                        .foregroundColor(.secondary)
                }

                // JSON Input
                VStack(alignment: .leading, spacing: 8) {
                    Text("JSON Data")
                        .font(.system(size: 13, weight: .medium))

                    TextEditor(text: $jsonInput)
                        .font(.system(size: 12, design: .monospaced))
                        .frame(height: 300)
                        .overlay(
                            RoundedRectangle(cornerRadius: 4)
                                .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                        )
                }

                // Status Messages
                if let error = errorMessage {
                    HStack(spacing: 8) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(.red)
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.red)
                    }
                }

                if let success = successMessage {
                    HStack(spacing: 8) {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(.green)
                        Text(success)
                            .font(.caption)
                            .foregroundColor(.green)
                    }
                }

                // Convert Button
                Button {
                    Task { await convertJson() }
                } label: {
                    HStack {
                        if isConverting {
                            ProgressView()
                                .scaleEffect(0.8)
                                .frame(width: 16, height: 16)
                        } else {
                            Image(systemName: "arrow.right.doc.on.clipboard")
                        }
                        Text(isConverting ? "Converting..." : "Convert to Excel")
                    }
                    .frame(maxWidth: .infinity)
                }
                .buttonStyle(.borderedProminent)
                .disabled(jsonInput.isEmpty || isConverting)
            }
            .padding(24)
        }
    }

    @MainActor
    private func convertJson() async {
        guard let sessionId = databaseStore.sessionId else {
            errorMessage = "No active session"
            return
        }

        isConverting = true
        errorMessage = nil
        successMessage = nil

        do {
            let response: JsonConvertResponse = try await ApiClient.shared.request(
                path: "/v1/sessions/\(sessionId)/json/convert",
                method: .post,
                jsonBody: ["json_data": jsonInput]
            )

            successMessage = "Converted successfully! File: \(response.filename)"
            isConverting = false

            // Auto-close after 2 seconds
            try? await Task.sleep(for: .seconds(2))
            isPresented = false
        } catch {
            errorMessage = error.localizedDescription
            isConverting = false
        }
    }
}

// MARK: - Preview

#Preview {
    DatabaseWorkspace()
        .frame(width: 1200, height: 800)
}

// MARK: - Notifications

extension Notification.Name {
    static let clearWorkspace = Notification.Name("DatabaseWorkspaceClearWorkspace")
}
