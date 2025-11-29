//
//  CodeWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Code editing workspace with file browser, editor, and integrated terminal
//  Layout: Left sidebar (file tree) | Center (code editor) | Bottom (terminal)
//

import SwiftUI

struct CodeWorkspace: View {
    @State private var selectedFile: FileItem? = nil
    @State private var openFiles: [FileItem] = []
    @State private var fileContent: String = ""
    @State private var sidebarWidth: CGFloat = 250
    @State private var terminalHeight: CGFloat = 200
    @State private var showTerminal: Bool = true
    @State private var currentWorkspace: CodeEditorWorkspace? = nil
    @State private var files: [FileItem] = []
    @State private var isLoadingFiles: Bool = false
    @State private var errorMessage: String? = nil

    private let codeEditorService = CodeEditorService.shared

    var body: some View {
        GeometryReader { geometry in
            HStack(spacing: 0) {
                // Left: File Browser
                fileBrowserSidebar
                    .frame(width: sidebarWidth)

                Divider()

                // Right: Editor + Terminal
                VStack(spacing: 0) {
                    // Top: Code Editor
                    editorArea
                        .frame(height: showTerminal ? geometry.size.height - terminalHeight : geometry.size.height)

                    if showTerminal {
                        Divider()

                        // Bottom: Terminal
                        terminalPanel
                            .frame(height: terminalHeight)
                    }
                }
            }
        }
        .task {
            await loadFiles()
        }
    }

    // MARK: - File Browser Sidebar

    private var fileBrowserSidebar: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Image(systemName: "folder")
                    .font(.system(size: 14))
                    .foregroundColor(.magnetarPrimary)

                Text("Files")
                    .font(.system(size: 14, weight: .semibold))

                Spacer()

                Button {
                    Task { await loadFiles() }
                } label: {
                    Image(systemName: "arrow.clockwise")
                        .font(.system(size: 12))
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background(Color.surfaceSecondary.opacity(0.3))

            Divider()

            // Path bar
            HStack {
                Image(systemName: "location")
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)

                Text(currentWorkspace?.name ?? "No workspace")
                    .font(.system(size: 11, design: .monospaced))
                    .foregroundColor(.secondary)
                    .lineLimit(1)

                Spacer()
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Color.surfaceTertiary.opacity(0.2))

            // File list
            if isLoadingFiles {
                ProgressView()
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if files.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: "doc.text")
                        .font(.system(size: 32))
                        .foregroundColor(.secondary)
                    Text("No files")
                        .font(.system(size: 13))
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 0) {
                        ForEach(files) { file in
                            FileRow(
                                file: file,
                                isSelected: selectedFile?.id == file.id,
                                onSelect: { selectFile(file) }
                            )
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
        }
        .background(Color.surfaceSecondary.opacity(0.1))
    }

    // MARK: - Editor Area

    private var editorArea: some View {
        VStack(spacing: 0) {
            // Tab bar
            if !openFiles.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 0) {
                        ForEach(openFiles) { file in
                            FileTab(
                                file: file,
                                isSelected: selectedFile?.id == file.id,
                                onSelect: { selectFile(file) },
                                onClose: { closeFile(file) }
                            )
                        }
                    }
                }
                .frame(height: 36)
                .background(Color.surfaceTertiary.opacity(0.3))

                Divider()
            }

            // Editor content
            if let selected = selectedFile {
                TextEditor(text: $fileContent)
                    .font(.system(size: 13, design: .monospaced))
                    .scrollContentBackground(.hidden)
                    .background(Color(nsColor: .textBackgroundColor))
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                // Welcome screen
                VStack(spacing: 16) {
                    Image(systemName: "chevron.left.forwardslash.chevron.right")
                        .font(.system(size: 48))
                        .foregroundStyle(LinearGradient.magnetarGradient)

                    Text("Code Editor")
                        .font(.title2)
                        .fontWeight(.bold)

                    Text("Select a file from the sidebar to start editing")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }
        }
    }

    // MARK: - Terminal Panel

    private var terminalPanel: some View {
        VStack(spacing: 0) {
            // Terminal header
            HStack {
                Image(systemName: "terminal")
                    .font(.system(size: 12))
                    .foregroundColor(.magnetarPrimary)

                Text("Terminal")
                    .font(.system(size: 12, weight: .semibold))

                Spacer()

                // New terminal button
                Button {
                    Task {
                        await spawnTerminal()
                    }
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: "plus.circle.fill")
                            .font(.system(size: 12))
                        Text("New")
                            .font(.system(size: 11, weight: .medium))
                    }
                    .foregroundColor(.magnetarPrimary)
                }
                .buttonStyle(.plain)

                Button {
                    showTerminal = false
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 10))
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(Color.surfaceTertiary.opacity(0.3))

            Divider()

            // Terminal info
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    HStack(spacing: 8) {
                        Image(systemName: "terminal.fill")
                            .font(.system(size: 24))
                            .foregroundStyle(LinearGradient.magnetarGradient)

                        VStack(alignment: .leading, spacing: 4) {
                            Text("System Terminal Integration")
                                .font(.system(size: 13, weight: .semibold))

                            Text("Click 'New' to spawn a terminal window")
                                .font(.system(size: 11))
                                .foregroundColor(.secondary)
                        }
                    }
                    .padding(.bottom, 8)

                    VStack(alignment: .leading, spacing: 8) {
                        TerminalInfoRow(
                            icon: "checkmark.circle.fill",
                            text: "Opens your default terminal app (Warp, iTerm2, or Terminal)",
                            color: .green
                        )

                        TerminalInfoRow(
                            icon: "checkmark.circle.fill",
                            text: "Automatically starts in your workspace directory",
                            color: .green
                        )

                        TerminalInfoRow(
                            icon: "checkmark.circle.fill",
                            text: "Up to 3 terminals can be active simultaneously",
                            color: .green
                        )
                    }

                    if let error = errorMessage {
                        HStack(spacing: 8) {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .foregroundColor(.orange)
                            Text(error)
                                .font(.system(size: 11))
                                .foregroundColor(.secondary)
                        }
                        .padding(.top, 8)
                    }
                }
                .padding(16)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .background(Color.surfaceTertiary.opacity(0.1))
        }
    }

    // MARK: - Actions

    private func loadFiles() async {
        isLoadingFiles = true
        errorMessage = nil

        do {
            // First, get or create a default workspace
            let workspaces = try await codeEditorService.listWorkspaces()

            let workspace: CodeEditorWorkspace
            if let existing = workspaces.first {
                workspace = existing
            } else {
                // Create default workspace
                workspace = try await codeEditorService.createWorkspace(
                    name: "Default Workspace",
                    sourceType: "database"
                )
            }

            currentWorkspace = workspace

            // Load files for this workspace
            let codeFiles = try await codeEditorService.getWorkspaceFiles(workspaceId: workspace.id)

            // Convert to FileItem
            let fileItems = codeFiles.map { file in
                FileItem(
                    name: file.name,
                    path: file.path,
                    isDirectory: file.isDirectory,
                    size: file.size,
                    modifiedAt: file.modifiedAt != nil ? ISO8601DateFormatter().date(from: file.modifiedAt!) : nil,
                    fileId: file.id
                )
            }

            await MainActor.run {
                files = fileItems
                isLoadingFiles = false
            }
        } catch {
            print("Failed to load files: \(error)")
            await MainActor.run {
                // Fall back to mock data
                files = FileItem.mockFiles
                errorMessage = "Using mock data - backend connection failed"
                isLoadingFiles = false
            }
        }
    }

    private func selectFile(_ file: FileItem) {
        selectedFile = file

        // Add to open files if not already open
        if !openFiles.contains(where: { $0.id == file.id }) {
            openFiles.append(file)
        }

        // Load file content from backend
        Task {
            guard let fileId = file.fileId else {
                fileContent = "// No file ID available"
                return
            }

            do {
                let codeFile = try await codeEditorService.getFile(fileId: fileId)
                await MainActor.run {
                    fileContent = codeFile.content ?? "// Empty file"
                }
            } catch {
                print("Failed to load file content: \(error)")
                await MainActor.run {
                    fileContent = "// Failed to load file content\n// Error: \(error.localizedDescription)"
                }
            }
        }
    }

    private func closeFile(_ file: FileItem) {
        openFiles.removeAll { $0.id == file.id }

        // If closing the selected file, select another
        if selectedFile?.id == file.id {
            selectedFile = openFiles.first
        }
    }

    private func spawnTerminal() async {
        do {
            // Get workspace directory if available
            let cwd = currentWorkspace?.diskPath

            let response = try await TerminalService.shared.spawnTerminal(cwd: cwd)

            await MainActor.run {
                errorMessage = nil
                print("✓ Terminal spawned: \(response.terminalApp) - \(response.message)")
            }
        } catch {
            print("Failed to spawn terminal: \(error)")
            await MainActor.run {
                errorMessage = "Failed to spawn terminal: \(error.localizedDescription)"
            }
        }
    }
}

// MARK: - File Item Model

struct FileItem: Identifiable, Hashable {
    let id = UUID()
    let name: String
    let path: String
    let isDirectory: Bool
    let size: Int64?
    let modifiedAt: Date?
    let fileId: String?  // Backend file ID

    static let mockFiles = [
        FileItem(name: "README.md", path: "/README.md", isDirectory: false, size: 1024, modifiedAt: Date(), fileId: nil),
        FileItem(name: "src", path: "/src", isDirectory: true, size: nil, modifiedAt: Date(), fileId: nil),
        FileItem(name: "main.swift", path: "/src/main.swift", isDirectory: false, size: 2048, modifiedAt: Date(), fileId: nil),
        FileItem(name: "utils.swift", path: "/src/utils.swift", isDirectory: false, size: 512, modifiedAt: Date(), fileId: nil),
        FileItem(name: "package.json", path: "/package.json", isDirectory: false, size: 256, modifiedAt: Date(), fileId: nil),
    ]
}

// MARK: - File Row

struct FileRow: View {
    let file: FileItem
    let isSelected: Bool
    let onSelect: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: onSelect) {
            HStack(spacing: 8) {
                Image(systemName: file.isDirectory ? "folder.fill" : "doc.text.fill")
                    .font(.system(size: 12))
                    .foregroundColor(file.isDirectory ? .blue : .secondary)

                Text(file.name)
                    .font(.system(size: 12))
                    .lineLimit(1)

                Spacer()
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                isSelected ? Color.magnetarPrimary.opacity(0.2) :
                isHovered ? Color.gray.opacity(0.1) : Color.clear
            )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            isHovered = hovering
        }
    }
}

// MARK: - File Tab

struct FileTab: View {
    let file: FileItem
    let isSelected: Bool
    let onSelect: () -> Void
    let onClose: () -> Void

    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: "doc.text")
                .font(.system(size: 11))
                .foregroundColor(.secondary)

            Text(file.name)
                .font(.system(size: 12))
                .lineLimit(1)

            Button {
                onClose()
            } label: {
                Image(systemName: "xmark")
                    .font(.system(size: 9))
                    .foregroundColor(.secondary)
            }
            .buttonStyle(.plain)
            .opacity(isHovered || isSelected ? 1 : 0)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(
            isSelected ? Color.surfaceSecondary :
            isHovered ? Color.gray.opacity(0.1) : Color.clear
        )
        .onTapGesture {
            onSelect()
        }
        .onHover { hovering in
            isHovered = hovering
        }
    }
}

// MARK: - Terminal Info Row

struct TerminalInfoRow: View {
    let icon: String
    let text: String
    let color: Color

    var body: some View {
        HStack(spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 11))
                .foregroundColor(color)

            Text(text)
                .font(.system(size: 11))
                .foregroundColor(.secondary)
        }
    }
}

// MARK: - Preview

#Preview {
    CodeWorkspace()
        .frame(width: 1200, height: 800)
}
