//
//  CodeWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Code editing workspace with file browser, editor, integrated terminal, and AI assistant.
//  Refactored in Phase 6.18 - extracted browser, editor, terminal, and components
//  Enhanced in Phase 7 - added AI assistant panel and bidirectional terminal context
//  Enhanced in Phase 8 - added LSP integration with diagnostics panel
//  Phase 8 Polish - keyboard shortcuts, status bar, persistent layout, pane constraints
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
    @State private var currentWorkspace: CodeEditorWorkspace? = nil
    @State private var files: [FileItem] = []
    @State private var isLoadingFiles: Bool = false
    @State private var errorMessage: String? = nil

    // Layout state — persisted via AppStorage
    @AppStorage("code.sidebarWidth") private var sidebarWidth: Double = 250
    @AppStorage("code.terminalHeight") private var terminalHeight: Double = 200
    @AppStorage("code.aiPanelWidth") private var aiPanelWidth: Double = 320
    @AppStorage("code.showBottomPanel") private var showBottomPanel: Bool = true
    @State private var bottomPanelMode: BottomPanelMode = .terminal
    @State private var showSidebar: Bool = true

    // AI Assistant state
    @State private var codingStore = CodingStore.shared

    // LSP / Diagnostics state
    @State private var diagnosticsStore = DiagnosticsStore.shared
    @State private var previousFileContent: String = ""

    // Cursor position for status bar
    @State private var cursorLine: Int = 1
    @State private var cursorColumn: Int = 1

    private let codeEditorService = CodeEditorService.shared

    // MARK: - Layout Constants

    private enum Layout {
        static let sidebarMin: CGFloat = 180
        static let sidebarMax: CGFloat = 400
        static let sidebarDefault: CGFloat = 250
        static let terminalMin: CGFloat = 100
        static let terminalMax: CGFloat = 500
        static let terminalDefault: CGFloat = 200
        static let aiPanelMin: CGFloat = 260
        static let aiPanelMax: CGFloat = 500
        static let aiPanelDefault: CGFloat = 320
    }

    var body: some View {
        GeometryReader { geometry in
            VStack(spacing: 0) {
                // Main workspace area
                HStack(spacing: 0) {
                    // Left: File Browser
                    if showSidebar {
                        CodeFileBrowser(
                            currentWorkspace: currentWorkspace,
                            files: files,
                            isLoadingFiles: isLoadingFiles,
                            selectedFile: selectedFile,
                            onRefresh: loadFiles,
                            onSelectFile: selectFile
                        )
                        .frame(width: CGFloat(sidebarWidth))

                        // Resizable sidebar divider
                        ResizableDivider(
                            dimension: $sidebarWidth,
                            axis: .horizontal,
                            minValue: Double(Layout.sidebarMin),
                            maxValue: Double(Layout.sidebarMax),
                            defaultValue: Double(Layout.sidebarDefault)
                        )
                    }

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
                        .frame(minHeight: 100)
                        .onChange(of: fileContent) { _, newValue in
                            requestDiagnosticsRefresh(content: newValue)
                        }

                        if showBottomPanel {
                            // Resizable bottom panel divider
                            ResizableDivider(
                                dimension: $terminalHeight,
                                axis: .vertical,
                                minValue: Double(Layout.terminalMin),
                                maxValue: min(Double(Layout.terminalMax), Double(geometry.size.height) * 0.6),
                                defaultValue: Double(Layout.terminalDefault)
                            )

                            // Bottom Panel with mode tabs
                            VStack(spacing: 0) {
                                bottomPanelTabs

                                Divider()

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
                            .frame(height: CGFloat(terminalHeight))
                        }
                    }

                    // Right: AI Assistant Panel
                    if codingStore.showAIAssistant {
                        ResizableDivider(
                            dimension: $aiPanelWidth,
                            axis: .horizontal,
                            minValue: Double(Layout.aiPanelMin),
                            maxValue: Double(Layout.aiPanelMax),
                            defaultValue: Double(Layout.aiPanelDefault),
                            invertDrag: true
                        )

                        AIAssistantPanel(codingStore: codingStore)
                            .frame(width: CGFloat(aiPanelWidth))
                    }
                }

                // Status Bar
                statusBar
            }
            .toolbar {
                ToolbarItemGroup(placement: .automatic) {
                    // Sidebar toggle
                    Button {
                        withAnimation(.magnetarQuick) {
                            showSidebar.toggle()
                        }
                    } label: {
                        Image(systemName: "sidebar.leading")
                    }
                    .help("Toggle Sidebar (⌘B)")
                    .keyboardShortcut("b", modifiers: .command)

                    // Bottom panel toggle
                    Button {
                        withAnimation(.magnetarQuick) {
                            showBottomPanel.toggle()
                        }
                    } label: {
                        Image(systemName: showBottomPanel ? "rectangle.bottomhalf.filled" : "rectangle.bottomhalf.inset.filled")
                    }
                    .help("Toggle Bottom Panel (⌘`)")
                    .keyboardShortcut("`", modifiers: .command)

                    // AI Assistant toggle
                    Button {
                        withAnimation(.magnetarQuick) {
                            codingStore.showAIAssistant.toggle()
                        }
                    } label: {
                        Image(systemName: "sparkles")
                            .foregroundStyle(codingStore.showAIAssistant ? .purple : .secondary)
                    }
                    .help("Toggle AI Assistant (⇧⌘P)")
                    .keyboardShortcut("p", modifiers: [.command, .shift])

                    Spacer()

                    // Refresh code index
                    Button {
                        codingStore.refreshCodeIndex()
                    } label: {
                        if codingStore.isCodeIndexing {
                            ProgressView()
                                .scaleEffect(0.6)
                        } else {
                            Image(systemName: "arrow.triangle.2.circlepath")
                        }
                    }
                    .help("Refresh Code Index")
                    .disabled(codingStore.isCodeIndexing)

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
            if let path = currentWorkspace?.diskPath {
                codingStore.workingDirectory = path
            }
        }
    }

    // MARK: - Status Bar

    private var statusBar: some View {
        HStack(spacing: 0) {
            // Line/Column indicator
            HStack(spacing: 4) {
                Text("Ln \(cursorLine), Col \(cursorColumn)")
                    .font(.system(size: 11, design: .monospaced))
                    .foregroundStyle(.secondary)
            }
            .padding(.horizontal, 12)

            Divider()
                .frame(height: 12)

            // Language indicator
            if let file = selectedFile {
                HStack(spacing: 4) {
                    let lang = CodeLanguage.detect(from: file.path)
                    Image(systemName: "chevron.left.forwardslash.chevron.right")
                        .font(.system(size: 9))
                    Text(lang == .unknown ? file.fileExtension : lang.rawValue.capitalized)
                        .font(.system(size: 11))
                }
                .foregroundStyle(.secondary)
                .padding(.horizontal, 8)

                Divider()
                    .frame(height: 12)
            }

            // Encoding
            Text("UTF-8")
                .font(.system(size: 11))
                .foregroundStyle(.tertiary)
                .padding(.horizontal, 8)

            Divider()
                .frame(height: 12)

            // Diagnostics summary
            if diagnosticsStore.totalStats.totalCount > 0 {
                HStack(spacing: 6) {
                    if diagnosticsStore.totalStats.errorCount > 0 {
                        HStack(spacing: 2) {
                            Image(systemName: "xmark.circle.fill")
                                .font(.system(size: 9))
                            Text("\(diagnosticsStore.totalStats.errorCount)")
                                .font(.system(size: 11))
                        }
                        .foregroundStyle(.red)
                    }

                    if diagnosticsStore.totalStats.warningCount > 0 {
                        HStack(spacing: 2) {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .font(.system(size: 9))
                            Text("\(diagnosticsStore.totalStats.warningCount)")
                                .font(.system(size: 11))
                        }
                        .foregroundStyle(.orange)
                    }
                }
                .padding(.horizontal, 8)

                Divider()
                    .frame(height: 12)
            }

            Spacer()

            // Code index status
            if codingStore.isCodeIndexing {
                HStack(spacing: 4) {
                    ProgressView()
                        .scaleEffect(0.5)
                    Text("Indexing...")
                        .font(.system(size: 11))
                }
                .foregroundStyle(.secondary)
                .padding(.horizontal, 8)
            } else if codingStore.indexedFileCount > 0 {
                HStack(spacing: 4) {
                    Image(systemName: "magnifyingglass")
                        .font(.system(size: 9))
                    Text("\(codingStore.indexedFileCount) files indexed")
                        .font(.system(size: 11))
                }
                .foregroundStyle(.tertiary)
                .padding(.horizontal, 8)
            }

            Divider()
                .frame(height: 12)

            // Orchestration mode indicator
            HStack(spacing: 4) {
                Image(systemName: CodingModelOrchestrator.shared.currentMode.iconName)
                    .font(.system(size: 9))
                Text(CodingModelOrchestrator.shared.currentMode.rawValue)
                    .font(.system(size: 11))
            }
            .foregroundStyle(.purple.opacity(0.7))
            .padding(.horizontal, 12)
        }
        .frame(height: 22)
        .background(Color.surfaceTertiary.opacity(0.5))
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
