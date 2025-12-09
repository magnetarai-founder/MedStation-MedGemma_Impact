//
//  CodeWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Code editing workspace with file browser, editor, and integrated terminal
//  Refactored in Phase 6.18 - extracted browser, editor, terminal, and components
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
                CodeFileBrowser(
                    currentWorkspace: currentWorkspace,
                    files: files,
                    isLoadingFiles: isLoadingFiles,
                    selectedFile: selectedFile,
                    onRefresh: loadFiles,
                    onSelectFile: selectFile
                )
                .frame(width: sidebarWidth)

                Divider()

                // Right: Editor + Terminal
                VStack(spacing: 0) {
                    // Top: Code Editor
                    CodeEditorArea(
                        openFiles: openFiles,
                        selectedFile: selectedFile,
                        fileContent: $fileContent,
                        onSelectFile: selectFile,
                        onCloseFile: closeFile
                    )
                    .frame(height: showTerminal ? geometry.size.height - terminalHeight : geometry.size.height)

                    if showTerminal {
                        Divider()

                        // Bottom: Terminal
                        CodeTerminalPanel(
                            showTerminal: $showTerminal,
                            errorMessage: errorMessage,
                            onSpawnTerminal: spawnTerminal
                        )
                        .frame(height: terminalHeight)
                    }
                }
            }
        }
        .task {
            await loadFiles()
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
                // Show empty state if backend unavailable
                files = []
                errorMessage = "Backend connection failed: \(error.localizedDescription)"
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

// MARK: - Preview

#Preview {
    CodeWorkspace()
        .frame(width: 1200, height: 800)
}
