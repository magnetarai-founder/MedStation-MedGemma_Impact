//
//  CodeWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Code editing workspace with file browser, editor, integrated terminal, and AI assistant.
//  Refactored in Phase 6.18 - extracted browser, editor, terminal, and components
//  Enhanced in Phase 7 - added AI assistant panel and bidirectional terminal context
//  Enhanced in Phase 8 - added LSP integration with diagnostics panel
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "CodeWorkspace")

/// Bottom panel mode selection
enum BottomPanelMode: String, CaseIterable {
    case terminal = "Terminal"
    case problems = "Problems"
}

struct CodeWorkspace: View {
    // MARK: - State

    @State private var selectedFile: FileItem? = nil
    @State private var openFiles: [FileItem] = []
    @State private var fileContent: String = ""
    @State private var sidebarWidth: CGFloat = 250
    @State private var terminalHeight: CGFloat = 200
    @State private var showBottomPanel: Bool = true
    @State private var bottomPanelMode: BottomPanelMode = .terminal
    @State private var currentWorkspace: CodeEditorWorkspace? = nil
    @State private var files: [FileItem] = []
    @State private var isLoadingFiles: Bool = false
    @State private var errorMessage: String? = nil

    // AI Assistant state
    @State private var codingStore = CodingStore.shared
    @State private var aiPanelWidth: CGFloat = 320

    // LSP / Diagnostics state
    @State private var diagnosticsStore = DiagnosticsStore.shared
    @State private var previousFileContent: String = ""

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

                // Center: Editor + Bottom Panel
                VStack(spacing: 0) {
                    // Top: Code Editor
                    CodeEditorArea(
                        openFiles: openFiles,
                        selectedFile: selectedFile,
                        fileContent: $fileContent,
                        onSelectFile: selectFile,
                        onCloseFile: closeFile
                    )
                    .frame(height: showBottomPanel ? geometry.size.height - terminalHeight : geometry.size.height)
                    .onChange(of: fileContent) { _, newValue in
                        // Trigger LSP diagnostics refresh on content change
                        requestDiagnosticsRefresh(content: newValue)
                    }

                    if showBottomPanel {
                        Divider()

                        // Bottom Panel with mode tabs
                        VStack(spacing: 0) {
                            // Panel mode tabs
                            bottomPanelTabs

                            Divider()

                            // Panel content
                            switch bottomPanelMode {
                            case .terminal:
                                CodeTerminalPanel(
                                    showTerminal: $showBottomPanel,
                                    codingStore: codingStore,
                                    onSpawnTerminal: spawnTerminal
                                )

                            case .problems:
                                CodeDiagnosticsPanel(
                                    diagnosticsStore: diagnosticsStore,
                                    currentFilePath: selectedFile?.path,
                                    workspacePath: currentWorkspace?.diskPath,
                                    onNavigateTo: navigateToLocation
                                )
                            }
                        }
                        .frame(height: terminalHeight)
                    }
                }

                // Right: AI Assistant Panel
                if codingStore.showAIAssistant {
                    Divider()

                    AIAssistantPanel(codingStore: codingStore)
                        .frame(width: aiPanelWidth)
                }
            }
            .toolbar {
                ToolbarItemGroup(placement: .automatic) {
                    // Bottom panel toggle
                    Button {
                        withAnimation(.easeInOut(duration: 0.2)) {
                            showBottomPanel.toggle()
                        }
                    } label: {
                        Image(systemName: showBottomPanel ? "rectangle.bottomhalf.filled" : "rectangle.bottomhalf.inset.filled")
                    }
                    .help("Toggle Bottom Panel")

                    // AI Assistant toggle
                    Button {
                        withAnimation(.easeInOut(duration: 0.2)) {
                            codingStore.showAIAssistant.toggle()
                        }
                    } label: {
                        Image(systemName: codingStore.showAIAssistant ? "sparkles" : "sparkles")
                            .foregroundStyle(codingStore.showAIAssistant ? .purple : .secondary)
                    }
                    .help("Toggle AI Assistant")

                    // Terminal app picker
                    Menu {
                        ForEach(TerminalApp.allCases, id: \.self) { app in
                            Button {
                                codingStore.preferredTerminal = app
                            } label: {
                                HStack {
                                    Image(systemName: app.iconName)
                                    Text(app.displayName)
                                    if codingStore.preferredTerminal == app {
                                        Image(systemName: "checkmark")
                                    }
                                }
                            }
                        }
                    } label: {
                        Image(systemName: codingStore.preferredTerminal.iconName)
                    }
                    .help("Terminal App: \(codingStore.preferredTerminal.displayName)")
                }
            }
        }
        .task {
            await loadFiles()
            // Set working directory for CodingStore
            if let path = currentWorkspace?.diskPath {
                codingStore.workingDirectory = path
            }
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

            // Convert to FileItem (tree nodes don't have size/modifiedAt - those come from full file fetch)
            let fileItems = codeFiles.map { file in
                FileItem(
                    name: file.name,
                    path: file.path,
                    isDirectory: file.isDirectory,
                    size: nil,  // Not available in tree listing
                    modifiedAt: nil,  // Not available in tree listing
                    fileId: file.id
                )
            }

            await MainActor.run {
                files = fileItems
                isLoadingFiles = false
            }
        } catch {
            logger.error("Failed to load files: \(error)")
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
                    fileContent = codeFile.content
                }
            } catch {
                logger.error("Failed to load file content: \(error)")
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
            // Use native terminal bridge for direct control
            let cwd = currentWorkspace?.diskPath ?? codingStore.workingDirectory

            // Spawn via CodingStore which tracks sessions
            _ = try await codingStore.spawnTerminal(cwd: cwd)

            await MainActor.run {
                errorMessage = nil
            }
        } catch {
            // Fallback to backend API if native bridge fails
            do {
                let cwd = currentWorkspace?.diskPath
                let response = try await TerminalService.shared.spawnTerminal(cwd: cwd)

                await MainActor.run {
                    errorMessage = nil
                    logger.info("Terminal spawned via backend: \(response.terminalApp) - \(response.message)")
                }
            } catch let fallbackError {
                logger.error("Failed to spawn terminal: \(fallbackError)")
                await MainActor.run {
                    errorMessage = "Failed to spawn terminal: \(fallbackError.localizedDescription)"
                }
            }
        }
    }

    /// Send selected code to AI assistant for explanation/help
    private func sendCodeToAssistant() {
        guard !fileContent.isEmpty else { return }

        let fileName = selectedFile?.name ?? "Unknown"
        let language = selectedFile?.fileExtension ?? "text"

        Task {
            await ContextBridgeService.shared.addCodeContext(
                code: fileContent,
                fileName: fileName,
                language: language
            )
        }
    }

    // MARK: - LSP Integration

    /// Request diagnostics refresh (debounced)
    private func requestDiagnosticsRefresh(content: String) {
        guard let filePath = selectedFile?.path,
              let workspacePath = currentWorkspace?.diskPath,
              content != previousFileContent else {
            return
        }

        previousFileContent = content
        diagnosticsStore.requestRefresh(
            for: filePath,
            workspacePath: workspacePath,
            content: content
        )
    }

    /// Navigate to a specific location in a file
    private func navigateToLocation(filePath: String, line: Int, character: Int) {
        // Find or open the file
        if let file = files.first(where: { $0.path == filePath }) {
            selectFile(file)
            // Note: Full cursor positioning would require NSTextView integration
            logger.info("[LSP] Navigate to \(filePath):\(line):\(character)")
        }
    }

    // MARK: - Bottom Panel Tabs

    private var bottomPanelTabs: some View {
        HStack(spacing: 0) {
            ForEach(BottomPanelMode.allCases, id: \.self) { mode in
                Button {
                    bottomPanelMode = mode
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: mode == .terminal ? "terminal" : "exclamationmark.triangle")
                            .font(.system(size: 10))

                        Text(mode.rawValue)
                            .font(.system(size: 11))

                        // Show problem count badge
                        if mode == .problems && diagnosticsStore.totalStats.totalCount > 0 {
                            problemCountBadge
                        }
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(bottomPanelMode == mode ? Color.magnetarPrimary.opacity(0.15) : Color.clear)
                    .foregroundColor(bottomPanelMode == mode ? .magnetarPrimary : .secondary)
                }
                .buttonStyle(.plain)
            }

            Spacer()

            // Close button
            Button {
                withAnimation(.easeInOut(duration: 0.2)) {
                    showBottomPanel = false
                }
            } label: {
                Image(systemName: "xmark")
                    .font(.system(size: 10))
                    .foregroundColor(.secondary)
            }
            .buttonStyle(.plain)
            .padding(.trailing, 8)
        }
        .background(Color.surfaceTertiary.opacity(0.3))
    }

    private var problemCountBadge: some View {
        HStack(spacing: 2) {
            if diagnosticsStore.totalStats.errorCount > 0 {
                HStack(spacing: 2) {
                    Image(systemName: "xmark.circle.fill")
                        .font(.system(size: 8))
                    Text("\(diagnosticsStore.totalStats.errorCount)")
                        .font(.system(size: 9, weight: .medium))
                }
                .foregroundColor(.red)
            }

            if diagnosticsStore.totalStats.warningCount > 0 {
                HStack(spacing: 2) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .font(.system(size: 8))
                    Text("\(diagnosticsStore.totalStats.warningCount)")
                        .font(.system(size: 9, weight: .medium))
                }
                .foregroundColor(.orange)
            }
        }
        .padding(.horizontal, 4)
    }
}

// MARK: - Preview

#Preview {
    CodeWorkspace()
        .frame(width: 1200, height: 800)
}
