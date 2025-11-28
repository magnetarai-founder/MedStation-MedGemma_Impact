//
//  DatabaseWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Database workspace matching React specs exactly:
//  - Left: 320pt resizable sidebar (FileUpload + icon row + SidebarTabs)
//  - Right: Vertical split (CodeEditor top + ResultsTable bottom)
//

import SwiftUI

// MARK: - Database View Tab
enum DatabaseViewTab: String, CaseIterable {
    case dataLab = "Data Lab"
    case sqlEditor = "SQL Editor"

    var icon: String {
        switch self {
        case .dataLab: return "sparkles"
        case .sqlEditor: return "terminal"
        }
    }
}

struct DatabaseWorkspace: View {
    @EnvironmentObject private var databaseStore: DatabaseStore
    @State private var sidebarWidth: CGFloat = 320
    @State private var topPaneHeight: CGFloat = 0.33 // 33% default
    @State private var showLibrary = false
    @State private var showQueryHistory = false
    @State private var showJsonConverter = false
    @State private var activeTab: DatabaseViewTab = .dataLab

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

    // MARK: - Right Content (Tab Toolbar + Content)

    private func rightContent(geometry: GeometryProxy) -> some View {
        VStack(spacing: 0) {
            // Tab toolbar
            tabToolbar

            Divider()

            // Tab content
            Group {
                switch activeTab {
                case .dataLab:
                    CombinedDataLabView()
                case .sqlEditor:
                    sqlEditorView(geometry: geometry)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    // MARK: - Tab Toolbar

    private var tabToolbar: some View {
        HStack(spacing: 0) {
            ForEach(DatabaseViewTab.allCases, id: \.self) { tab in
                Button(action: {
                    withAnimation(.magnetarStandard) {
                        activeTab = tab
                    }
                }) {
                    HStack(spacing: 8) {
                        Image(systemName: tab.icon)
                            .font(.system(size: 14))
                        Text(tab.rawValue)
                            .font(.system(size: 13, weight: .medium))
                    }
                    .foregroundColor(activeTab == tab ? .magnetarPrimary : .secondary)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .background(
                        Rectangle()
                            .fill(activeTab == tab ? Color.magnetarPrimary.opacity(0.1) : Color.clear)
                    )
                    .overlay(
                        Rectangle()
                            .fill(activeTab == tab ? Color.magnetarPrimary : Color.clear)
                            .frame(height: 2),
                        alignment: .bottom
                    )
                }
                .buttonStyle(.plain)
            }

            Spacer()
        }
        .background(Color.surfaceTertiary.opacity(0.3))
    }

    // MARK: - SQL Editor View (original content)

    private func sqlEditorView(geometry: GeometryProxy) -> some View {
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
            withAnimation(.magnetarStandard) {
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
            print("DEBUG: Failed to load queries - \(error)")
            if let decodingError = error as? DecodingError {
                print("DEBUG: Decoding error details - \(decodingError)")
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
                    // Pencil - Edit
                    Button(action: {
                        showEditDialog = true
                    }) {
                        Image(systemName: "pencil")
                            .font(.system(size: 14))
                            .foregroundColor(.secondary)
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

// MARK: - Edit Query Dialog

struct EditQueryDialog: View {
    @Binding var isPresented: Bool
    let query: SavedQuery
    let onUpdate: (String, String, String) -> Void  // name, description, sql

    @State private var editedName: String = ""
    @State private var editedDescription: String = ""
    @State private var editedSQL: String = ""

    var body: some View {
        VStack(spacing: 20) {
            // Header
            HStack {
                Text("Edit Query")
                    .font(.title2)
                    .fontWeight(.semibold)
                Spacer()
                Button(action: { isPresented = false }) {
                    Image(systemName: "xmark.circle.fill")
                        .font(.system(size: 20))
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }

            // Name field
            VStack(alignment: .leading, spacing: 8) {
                Text("Name")
                    .font(.system(size: 13, weight: .medium))
                TextField("Query name", text: $editedName)
                    .textFieldStyle(.roundedBorder)
            }

            // Description field
            VStack(alignment: .leading, spacing: 8) {
                Text("Description (optional)")
                    .font(.system(size: 13, weight: .medium))
                TextField("Description", text: $editedDescription)
                    .textFieldStyle(.roundedBorder)
            }

            // SQL Editor
            VStack(alignment: .leading, spacing: 8) {
                Text("SQL Query")
                    .font(.system(size: 13, weight: .medium))

                TextEditor(text: $editedSQL)
                    .font(.system(size: 13, design: .monospaced))
                    .frame(height: 300)
                    .overlay(
                        RoundedRectangle(cornerRadius: 6)
                            .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                    )
            }

            // Action buttons
            HStack(spacing: 12) {
                Button("Cancel") {
                    isPresented = false
                }
                .buttonStyle(.bordered)

                Button("Save Changes") {
                    onUpdate(editedName, editedDescription, editedSQL)
                    isPresented = false
                }
                .buttonStyle(.borderedProminent)
                .disabled(editedName.isEmpty || editedSQL.isEmpty)
            }
        }
        .padding(24)
        .frame(width: 600)
        .onAppear {
            editedName = query.name
            editedDescription = query.description ?? ""
            editedSQL = query.query
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

// MARK: - Combined Data Lab View

enum DataLabMode: String, CaseIterable {
    case naturalLanguage = "Ask Questions"
    case patterns = "Find Patterns"

    var icon: String {
        switch self {
        case .naturalLanguage: return "text.bubble"
        case .patterns: return "chart.bar"
        }
    }
}

struct CombinedDataLabView: View {
    @State private var mode: DataLabMode = .naturalLanguage
    @State private var query: String = ""
    @State private var context: String = ""
    @State private var isLoading: Bool = false
    @State private var errorMessage: String? = nil
    @State private var nlResponse: NLQueryResponse? = nil
    @State private var patternResults: PatternDiscoveryResult? = nil

    private let teamService = TeamService.shared

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                // Header with mode switcher
                VStack(spacing: 16) {
                    Image(systemName: "sparkles")
                        .font(.system(size: 48))
                        .foregroundStyle(LinearGradient.magnetarGradient)

                    Text("Data Lab")
                        .font(.title.weight(.bold))

                    Text("AI-powered data analysis and insights")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    // Mode Switcher
                    HStack(spacing: 0) {
                        ForEach(DataLabMode.allCases, id: \.self) { labMode in
                            Button(action: {
                                withAnimation(.magnetarStandard) {
                                    mode = labMode
                                    // Clear results when switching modes
                                    query = ""
                                    context = ""
                                    errorMessage = nil
                                    nlResponse = nil
                                    patternResults = nil
                                }
                            }) {
                                HStack(spacing: 6) {
                                    Image(systemName: labMode.icon)
                                        .font(.system(size: 13))
                                    Text(labMode.rawValue)
                                        .font(.system(size: 13, weight: .medium))
                                }
                                .foregroundColor(mode == labMode ? .white : .secondary)
                                .padding(.horizontal, 20)
                                .padding(.vertical, 10)
                                .background(
                                    mode == labMode
                                        ? AnyShapeStyle(LinearGradient.magnetarGradient)
                                        : AnyShapeStyle(Color.gray.opacity(0.1))
                                )
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .clipShape(Capsule())
                    .overlay(
                        Capsule()
                            .stroke(Color.gray.opacity(0.2), lineWidth: 1)
                    )
                }
                .padding(.top, 32)

                // Mode-specific content
                if mode == .naturalLanguage {
                    naturalLanguageSection
                } else {
                    patternDiscoverySection
                }

                // Error message
                if let error = errorMessage {
                    HStack(spacing: 12) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(.orange)
                        Text(error)
                            .font(.caption)
                            .foregroundColor(.red)
                    }
                    .padding(.horizontal, 32)
                }

                Spacer()
            }
            .frame(maxWidth: 800)
            .frame(maxWidth: .infinity)
        }
    }

    // MARK: - Natural Language Section

    private var naturalLanguageSection: some View {
        VStack(spacing: 24) {
            // Query input
            VStack(alignment: .leading, spacing: 8) {
                Text("Your Question")
                    .font(.system(size: 13, weight: .medium))
                TextEditor(text: $query)
                    .frame(height: 100)
                    .font(.system(size: 14))
                    .padding(8)
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                    )
                    .disabled(isLoading)

                Text("Example: \"What are the top 5 customers by revenue?\"")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }
            .padding(.horizontal, 32)

            // Submit button
            Button(action: { Task { await askQuestion() } }) {
                HStack(spacing: 8) {
                    if isLoading {
                        ProgressView()
                            .scaleEffect(0.8)
                    }
                    Text(isLoading ? "Asking..." : "Ask AI")
                }
                .frame(maxWidth: 300)
            }
            .buttonStyle(.borderedProminent)
            .disabled(query.isEmpty || isLoading)

            // Response area
            if let answer = nlResponse {
                VStack(alignment: .leading, spacing: 16) {
                    Divider()
                        .padding(.horizontal, 32)

                    VStack(alignment: .leading, spacing: 12) {
                        HStack {
                            Text("Answer")
                                .font(.system(size: 15, weight: .semibold))
                            Spacer()
                            if let confidence = answer.confidence {
                                Text("\(Int(confidence * 100))% confident")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 4)
                                    .background(Color.gray.opacity(0.1))
                                    .cornerRadius(4)
                            }
                        }

                        Text(answer.answer)
                            .font(.system(size: 14))
                            .textSelection(.enabled)
                            .padding(16)
                            .background(Color.surfaceSecondary.opacity(0.5))
                            .cornerRadius(8)

                        if let sources = answer.sources, !sources.isEmpty {
                            VStack(alignment: .leading, spacing: 6) {
                                Text("Sources:")
                                    .font(.caption.weight(.medium))
                                    .foregroundColor(.secondary)
                                ForEach(sources, id: \.self) { source in
                                    HStack(spacing: 6) {
                                        Image(systemName: "link")
                                            .font(.caption)
                                        Text(source)
                                            .font(.caption)
                                    }
                                    .foregroundColor(.secondary)
                                }
                            }
                        }
                    }
                    .padding(.horizontal, 32)
                }
            }
        }
    }

    // MARK: - Pattern Discovery Section

    private var patternDiscoverySection: some View {
        VStack(spacing: 24) {
            // Input fields
            VStack(alignment: .leading, spacing: 16) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Query")
                        .font(.system(size: 13, weight: .medium))
                    TextField("Describe what patterns to find", text: $query)
                        .textFieldStyle(.roundedBorder)
                        .disabled(isLoading)
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text("Context (Optional)")
                        .font(.system(size: 13, weight: .medium))
                    TextEditor(text: $context)
                        .frame(height: 80)
                        .font(.system(size: 14))
                        .padding(8)
                        .overlay(
                            RoundedRectangle(cornerRadius: 8)
                                .stroke(Color.gray.opacity(0.3), lineWidth: 1)
                        )
                        .disabled(isLoading)

                    Text("Additional context to help with pattern detection")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
            .padding(.horizontal, 32)

            // Submit button
            Button(action: { Task { await discoverPatterns() } }) {
                HStack(spacing: 8) {
                    if isLoading {
                        ProgressView()
                            .scaleEffect(0.8)
                    }
                    Text(isLoading ? "Analyzing..." : "Discover Patterns")
                }
                .frame(maxWidth: 300)
            }
            .buttonStyle(.borderedProminent)
            .disabled(query.isEmpty || isLoading)

            // Results area
            if let result = patternResults {
                VStack(alignment: .leading, spacing: 16) {
                    Divider()
                        .padding(.horizontal, 32)

                    VStack(alignment: .leading, spacing: 12) {
                        if let summary = result.summary {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Summary")
                                    .font(.system(size: 15, weight: .semibold))
                                Text(summary)
                                    .font(.system(size: 13))
                                    .foregroundColor(.secondary)
                                    .padding(16)
                                    .background(Color.surfaceSecondary.opacity(0.5))
                                    .cornerRadius(8)
                            }
                        }

                        if !result.patterns.isEmpty {
                            VStack(alignment: .leading, spacing: 12) {
                                Text("Patterns Found (\(result.patterns.count))")
                                    .font(.system(size: 15, weight: .semibold))

                                ForEach(result.patterns) { pattern in
                                    patternRow(pattern)
                                }
                            }
                        } else {
                            Text("No patterns found")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }
                    .padding(.horizontal, 32)
                }
            }
        }
    }

    @ViewBuilder
    private func patternRow(_ pattern: PatternDiscoveryResult.Pattern) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Text(pattern.type)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(.white)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 4)
                    .background(Capsule().fill(Color.blue))

                Spacer()

                Text("\(Int(pattern.confidence * 100))%")
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Text(pattern.description)
                .font(.system(size: 13))

            if let examples = pattern.examples, !examples.isEmpty {
                VStack(alignment: .leading, spacing: 4) {
                    ForEach(examples.prefix(3), id: \.self) { example in
                        HStack(spacing: 6) {
                            Text("•")
                            Text(example)
                        }
                        .font(.caption)
                        .foregroundColor(.secondary)
                    }
                }
            }
        }
        .padding(16)
        .background(Color.gray.opacity(0.08))
        .cornerRadius(10)
    }

    // MARK: - Actions

    @MainActor
    private func askQuestion() async {
        isLoading = true
        errorMessage = nil
        nlResponse = nil

        do {
            nlResponse = try await teamService.askNaturalLanguage(query: query)
        } catch {
            errorMessage = "Failed to get answer: \(error.localizedDescription)"
        }

        isLoading = false
    }

    @MainActor
    private func discoverPatterns() async {
        isLoading = true
        errorMessage = nil
        patternResults = nil

        do {
            patternResults = try await teamService.discoverPatterns(
                query: query,
                context: context.isEmpty ? nil : context
            )
        } catch {
            errorMessage = "Failed to discover patterns: \(error.localizedDescription)"
        }

        isLoading = false
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
