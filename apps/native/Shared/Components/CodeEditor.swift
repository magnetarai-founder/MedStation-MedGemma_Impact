//
//  CodeEditor.swift
//  MagnetarStudio
//
//  Code editor with toolbar matching React CodeEditor.tsx specs
//  - Toolbar with pill groups: Upload/Download, Library/Save, Preview/Run/Stop, Trash
//  - Monaco-style editor with syntax highlighting
//

import SwiftUI

struct CodeEditor: View {
    @EnvironmentObject private var databaseStore: DatabaseStore
    @State private var code: String = ""
    @State private var isExecuting: Bool = false
    @State private var hasFile: Bool = false
    @State private var showLibrary: Bool = false
    @State private var showSaveModal: Bool = false
    @State private var isUploading: Bool = false

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
                .onChange(of: code) {
                    databaseStore.editorText = code
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
    }

    // MARK: - Toolbar

    private var toolbar: some View {
        HStack(spacing: 12) {
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
                        // Download
                    }
                ) {
                    Image(systemName: "arrow.down.doc")
                        .font(.system(size: 16))
                }
                .help("Download")
            }

            // Library/Save group
            if code.isEmpty {
                Menu {
                    Button("Load from Library") {
                        showLibrary = true
                    }
                    Button("Recent Queries") {
                        // Show recent
                    }
                    Divider()
                    Button("Upload .sql File") {
                        // Upload SQL
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
                ToolbarButton(action: {
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

            // Preview/Run/Stop group
            ToolbarGroup {
                ToolbarIconButton(
                    icon: "bolt",
                    isDisabled: !hasFile || isExecuting,
                    action: {
                        // Preview
                    }
                ) {
                    Image(systemName: "bolt")
                        .font(.system(size: 16))
                }
                .help("Preview Query")

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
            }

            Spacer()

            // Trash group
            ToolbarGroup {
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

struct ToolbarButton<Content: View>: View {
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

// MARK: - Preview

#Preview {
    CodeEditor()
        .frame(height: 400)
}
