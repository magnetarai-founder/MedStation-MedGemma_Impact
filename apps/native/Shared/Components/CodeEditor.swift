//
//  CodeEditor.swift
//  MagnetarStudio
//
//  Code editor with toolbar matching React CodeEditor.tsx specs
//  - Toolbar with pill groups: Upload/Download, Library/Save, Preview/Run/Stop, Trash
//  - Monaco-style editor with syntax highlighting
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "CodeEditor")

struct CodeEditor: View {
    @EnvironmentObject private var databaseStore: DatabaseStore
    @State private var code: String = ""
    @State private var isExecuting: Bool = false
    @State private var hasFile: Bool = false
    @State private var showLibrary: Bool = false
    @State private var showSaveModal: Bool = false
    @State private var isUploading: Bool = false
    @State private var showRecentQueries: Bool = false
    @State private var debounceTask: Task<Void, Never>?

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

            // Editor
            TextEditor(text: $code)
                .font(.system(size: 14, design: .monospaced))
                .scrollContentBackground(.hidden)
                .background(Color(nsColor: .textBackgroundColor))
                .frame(maxWidth: .infinity, maxHeight: .infinity)
                .onChange(of: code) { _, newValue in
                    // Cancel previous debounce task
                    debounceTask?.cancel()

                    // Create new debounced task (300ms delay)
                    debounceTask = Task {
                        try? await Task.sleep(nanoseconds: 300_000_000) // 300ms

                        guard !Task.isCancelled else { return }

                        await MainActor.run {
                            databaseStore.editorText = newValue
                        }
                    }
                }
        }
        .onReceive(NotificationCenter.default.publisher(for: .clearWorkspace)) { _ in
            code = ""
            hasFile = false
            isExecuting = false
        }
        .onAppear {
            code = databaseStore.editorText
        }
        .sheet(isPresented: $showSaveModal) {
            SaveQueryDialog(
                isPresented: $showSaveModal,
                queryText: code,
                databaseStore: databaseStore
            )
        }
        .sheet(isPresented: $showRecentQueries) {
            RecentQueriesSheet(
                isPresented: $showRecentQueries,
                onSelectQuery: { query in
                    code = query
                    showRecentQueries = false
                }
            )
        }
    }

    // MARK: - Toolbar

    private var toolbar: some View {
        HStack(spacing: 12) {
            // Library/Save group - first
            if code.isEmpty {
                Menu {
                    Button("Load from Library") {
                        showLibrary = true
                    }
                    Button("Recent Queries") {
                        showRecentQueries = true
                    }
                    Divider()
                    Button("Upload .sql File") {
                        uploadSQLFile()
                    }
                } label: {
                    HStack(spacing: 6) {
                        Image(systemName: "book")
                            .font(.system(size: 16))
                        Text("Library")
                            .font(.system(size: 13))
                        Image(systemName: "chevron.down")
                            .font(.system(size: 10))
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 6)
                }
                .buttonStyle(.plain)
                .background(
                    RoundedRectangle(cornerRadius: 6)
                        .fill(Color.gray.opacity(0.1))
                )
                .help("Browse Library")
            } else {
                CodeEditorToolbarButton(action: {
                    showSaveModal = true
                }) {
                    HStack(spacing: 6) {
                        Image(systemName: "square.and.arrow.down")
                            .font(.system(size: 16))
                        Text("Save to Library")
                            .font(.system(size: 13))
                    }
                }
                .help("Save to Library")
            }

            // Upload/Download group
            ToolbarGroup {
                ToolbarIconButton(
                    icon: "arrow.up.doc",
                    isDisabled: isUploading,
                    action: {
                        uploadSQLFile()
                    }
                ) {
                    if isUploading {
                        ProgressView()
                            .scaleEffect(0.7)
                    } else {
                        Image(systemName: "arrow.up.doc")
                            .font(.system(size: 16))
                    }
                }
                .help("Upload .sql File")

                ToolbarIconButton(
                    icon: "arrow.down.doc",
                    isDisabled: code.isEmpty,
                    action: {
                        downloadSQL()
                    }
                ) {
                    Image(systemName: "arrow.down.doc")
                        .font(.system(size: 16))
                }
                .help("Download as .sql")
            }

            // Preview/Run/Stop/Trash group
            ToolbarGroup {
                ToolbarIconButton(
                    icon: "bolt",
                    isDisabled: code.isEmpty || isExecuting,
                    action: {
                        previewQuery()
                    }
                ) {
                    Image(systemName: "bolt")
                        .font(.system(size: 16))
                }
                .help("Preview Query (first 100 rows)")

                // Run button (primary)
                ToolbarIconButton(
                    icon: isExecuting ? "arrow.triangle.2.circlepath" : "play.fill",
                    isPrimary: true,
                    isDisabled: code.isEmpty,
                    action: {
                        isExecuting.toggle()
                    }
                ) {
                    if isExecuting {
                        ProgressView()
                            .scaleEffect(0.7)
                            .tint(.white)
                    } else {
                        Image(systemName: "play.fill")
                            .font(.system(size: 16))
                    }
                }
                .help("Run Query (⌘↵)")

                if isExecuting {
                    ToolbarIconButton(
                        icon: "stop.fill",
                        isDestructive: true,
                        action: {
                            isExecuting = false
                        }
                    ) {
                        Image(systemName: "stop.fill")
                            .font(.system(size: 16))
                    }
                    .help("Stop")
                }

                // Trash - Clear editor
                ToolbarIconButton(
                    icon: "trash",
                    isDisabled: code.isEmpty,
                    action: {
                        code = ""
                    }
                ) {
                    Image(systemName: "trash")
                        .font(.system(size: 16))
                }
                .help("Clear Editor")
            }

            Spacer()
        }
    }

    // MARK: - Actions

    private func downloadSQL() {
        let panel = NSSavePanel()
        panel.allowedContentTypes = [.init(filenameExtension: "sql") ?? .plainText]
        panel.nameFieldStringValue = "query.sql"
        panel.canCreateDirectories = true

        panel.begin { response in
            guard response == .OK, let url = panel.url else { return }

            let sqlContent = code // Capture on main actor
            Task.detached {
                do {
                    try sqlContent.write(to: url, atomically: true, encoding: .utf8)
                } catch {
                    logger.error("Failed to save SQL file: \(error)")
                }
            }
        }
    }

    private func previewQuery() {
        Task {
            isExecuting = true
            await databaseStore.runQuery(sql: code, limit: 100, isPreview: true)
            isExecuting = false
        }
    }

    // MARK: - SQL Upload

    private func uploadSQLFile() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [.init(filenameExtension: "sql") ?? .plainText]
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false

        panel.begin { response in
            guard response == .OK, let url = panel.url else { return }

            isUploading = true
            Task {
                do {
                    let contents = try await Task.detached {
                        try String(contentsOf: url, encoding: .utf8)
                    }.value

                    await MainActor.run {
                        code = contents
                        isUploading = false
                    }
                } catch {
                    await MainActor.run {
                        isUploading = false
                    }
                }
            }
        }
    }
}

// MARK: - Toolbar Components

struct ToolbarGroup<Content: View>: View {
    @ViewBuilder let content: Content

    var body: some View {
        HStack(spacing: 4) {
            content
        }
        .padding(.horizontal, 6)
        .padding(.vertical, 2)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(Color.gray.opacity(0.1))
        )
    }
}

struct CodeEditorToolbarButton<Content: View>: View {
    let action: () -> Void
    @ViewBuilder let content: Content

    var body: some View {
        Button(action: action) {
            content
                .foregroundColor(.primary)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
        }
        .buttonStyle(.plain)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(Color.gray.opacity(0.1))
        )
    }
}

struct ToolbarIconButton<Content: View>: View {
    let icon: String
    var isPrimary: Bool = false
    var isDestructive: Bool = false
    var isDisabled: Bool = false
    let action: () -> Void
    @ViewBuilder let content: Content

    var body: some View {
        Button(action: action) {
            content
                .foregroundColor(buttonForegroundColor)
                .frame(width: 28, height: 28)
        }
        .buttonStyle(.plain)
        .background(
            RoundedRectangle(cornerRadius: 4)
                .fill(buttonBackgroundColor)
        )
        .disabled(isDisabled)
        .opacity(isDisabled ? 0.4 : 1.0)
    }

    private var buttonForegroundColor: Color {
        if isPrimary {
            return .white
        } else if isDestructive {
            return .red
        } else {
            return .primary
        }
    }

    private var buttonBackgroundColor: Color {
        if isPrimary {
            return Color.magnetarPrimary
        } else if isDestructive {
            return Color.red.opacity(0.1)
        } else {
            return Color.clear
        }
    }
}

// MARK: - Recent Queries Sheet

struct RecentQueriesSheet: View {
    @Binding var isPresented: Bool
    let onSelectQuery: (String) -> Void
    @AppStorage("recentQueries") private var recentQueriesData: Data = Data()

    private var recentQueries: [String] {
        (try? JSONDecoder().decode([String].self, from: recentQueriesData)) ?? []
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Recent Queries")
                    .font(.system(size: 18, weight: .bold))
                Spacer()
                Button("Done") {
                    isPresented = false
                }
                .buttonStyle(.bordered)
            }
            .padding(20)

            Divider()

            // Content
            if recentQueries.isEmpty {
                VStack(spacing: 16) {
                    Image(systemName: "clock")
                        .font(.system(size: 48))
                        .foregroundColor(.secondary)
                    Text("No recent queries")
                        .font(.headline)
                        .foregroundColor(.secondary)
                    Text("Queries you run will appear here")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(spacing: 8) {
                        ForEach(Array(recentQueries.enumerated()), id: \.offset) { index, query in
                            Button(action: {
                                onSelectQuery(query)
                            }) {
                                VStack(alignment: .leading, spacing: 4) {
                                    HStack {
                                        Text("Query #\(recentQueries.count - index)")
                                            .font(.system(size: 12, weight: .semibold))
                                        Spacer()
                                        Image(systemName: "chevron.right")
                                            .font(.system(size: 10))
                                            .foregroundColor(.secondary)
                                    }

                                    Text(query)
                                        .font(.system(size: 12, design: .monospaced))
                                        .lineLimit(2)
                                        .foregroundColor(.secondary)
                                }
                                .padding(12)
                                .frame(maxWidth: .infinity, alignment: .leading)
                                .background(Color.surfaceSecondary.opacity(0.3))
                                .cornerRadius(8)
                            }
                            .buttonStyle(.plain)
                        }
                    }
                    .padding(20)
                }
            }
        }
        .frame(width: 600, height: 500)
    }
}

// MARK: - Preview

#Preview {
    CodeEditor()
        .frame(height: 400)
}
