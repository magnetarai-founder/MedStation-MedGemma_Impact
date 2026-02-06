//
//  CodeWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Code editing workspace with activity bar, file browser, and full-height editor.
//  Terminal access via activity bar buttons (spawn external terminal or terminal bridge).
//  AI assistant available as detached window (⌘⇧A) — no longer embedded.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "CodeWorkspace")

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
    @AppStorage("enableBlurEffects") private var enableBlurEffects = true
    @AppStorage("reduceTransparency") private var reduceTransparency = false
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
    }

    // Activity bar selection
    @State private var activeActivityItem: ActivityBarItem = .files

    var body: some View {
        VStack(spacing: 0) {
            // Main workspace area
            HStack(spacing: 0) {
                // Far left: Activity Bar
                activityBar

                // Thin separator
                Rectangle()
                    .fill(Color(nsColor: .separatorColor))
                    .frame(width: 1)

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

                // Center: Full-height Code Editor
                CodeEditorArea(
                    openFiles: openFiles,
                    selectedFile: selectedFile,
                    workspaceName: currentWorkspace?.name,
                    fileContent: $fileContent,
                    onSelectFile: selectFile,
                    onCloseFile: closeFile
                )
                .frame(minHeight: 100)
                .onChange(of: fileContent) { _, newValue in
                    requestDiagnosticsRefresh(content: newValue)
                }
            }

            // Status Bar
            statusBar
        }
        .task {
            await loadFiles()
            if let path = currentWorkspace?.diskPath {
                codingStore.workingDirectory = path
            }
        }
    }

    // MARK: - Activity Bar

    private var activityBar: some View {
        VStack(spacing: 0) {
            ForEach(ActivityBarItem.allCases) { item in
                ActivityBarButton(
                    item: item,
                    isActive: activeActivityItem == item && (item == .files ? showSidebar : false)
                ) {
                    if item == .files {
                        if activeActivityItem == .files {
                            withAnimation(.magnetarQuick) { showSidebar.toggle() }
                        } else {
                            activeActivityItem = .files
                            if !showSidebar {
                                withAnimation(.magnetarQuick) { showSidebar = true }
                            }
                        }
                    } else {
                        activeActivityItem = item
                    }
                }
            }

            Spacer()

            // AI Assistant — opens floating window
            Button {
                WindowOpener.shared.openAIAssistant()
            } label: {
                Image(systemName: "sparkles")
                    .font(.system(size: 16))
                    .foregroundStyle(.secondary)
                    .frame(width: 36, height: 36)
            }
            .buttonStyle(.plain)
            .help("AI Assistant (⌘⇧A)")

            // Open Terminal — spawn user's preferred terminal app
            Button {
                Task { await spawnTerminal() }
            } label: {
                Image(systemName: "terminal")
                    .font(.system(size: 16))
                    .foregroundStyle(.secondary)
                    .frame(width: 36, height: 36)
            }
            .buttonStyle(.plain)
            .help("Open Terminal (\(codingStore.preferredTerminal.displayName))")
            .contextMenu {
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
            }
        }
        .frame(width: 36)
        .padding(.top, 8)
        .padding(.bottom, 8)
        .background {
            if enableBlurEffects && !reduceTransparency {
                AnyView(Rectangle().fill(.thinMaterial))
            } else {
                AnyView(Color(nsColor: .controlBackgroundColor))
            }
        }
    }

    // MARK: - Status Bar

    // MARK: - Code Toolbar Buttons (relocated from .toolbar)

    private var codeToolbarButtons: some View {
        HStack(spacing: 2) {
            // Sidebar toggle
            Button {
                withAnimation(.magnetarQuick) { showSidebar.toggle() }
            } label: {
                Image(systemName: "sidebar.leading")
                    .font(.system(size: 10))
                    .foregroundStyle(showSidebar ? .primary : .secondary)
            }
            .buttonStyle(.plain)
            .help("Toggle Sidebar (⌘B)")
            .keyboardShortcut("b", modifiers: .command)
            .padding(.horizontal, 6)

            Color(nsColor: .separatorColor).frame(width: 1, height: 12)

            // Refresh code index
            Button {
                codingStore.refreshCodeIndex()
            } label: {
                if codingStore.isCodeIndexing {
                    ProgressView().scaleEffect(0.5)
                } else {
                    Image(systemName: "arrow.triangle.2.circlepath")
                        .font(.system(size: 10))
                }
            }
            .buttonStyle(.plain)
            .help("Refresh Code Index")
            .disabled(codingStore.isCodeIndexing)
            .padding(.horizontal, 6)
        }
        .padding(.leading, 8)
    }

    private var statusBar: some View {
        HStack(spacing: 0) {
            // Code-specific layout toggles
            codeToolbarButtons

            Color(nsColor: .separatorColor).frame(width: 1, height: 12)

            // Line/Column indicator
            HStack(spacing: 4) {
                Text("Ln \(cursorLine), Col \(cursorColumn)")
                    .font(.system(size: 11, design: .monospaced))
                    .foregroundStyle(.secondary)
            }
            .padding(.horizontal, 12)

            Color(nsColor: .separatorColor)
                .frame(width: 1, height: 12)

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

            Color(nsColor: .separatorColor)
                .frame(width: 1, height: 12)

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

            Color(nsColor: .separatorColor)
                .frame(width: 1, height: 12)

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
        .background(Color(nsColor: .controlBackgroundColor).opacity(0.5))
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

}

// MARK: - Activity Bar Item

enum ActivityBarItem: String, CaseIterable, Identifiable {
    case files
    case search
    case sourceControl
    case debug
    case extensions

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .files: return "doc.on.doc"
        case .search: return "magnifyingglass"
        case .sourceControl: return "arrow.triangle.branch"
        case .debug: return "ladybug"
        case .extensions: return "square.grid.2x2"
        }
    }

    var label: String {
        switch self {
        case .files: return "Explorer"
        case .search: return "Search"
        case .sourceControl: return "Source Control"
        case .debug: return "Debug"
        case .extensions: return "Extensions"
        }
    }

    var isImplemented: Bool {
        self == .files
    }
}

// MARK: - Activity Bar Button

private struct ActivityBarButton: View {
    let item: ActivityBarItem
    let isActive: Bool
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            ZStack(alignment: .leading) {
                // Active indicator — 2pt accent bar on left edge
                if isActive {
                    RoundedRectangle(cornerRadius: 1)
                        .fill(Color.accentColor)
                        .frame(width: 2, height: 16)
                        .offset(x: -8)
                }

                Image(systemName: item.icon)
                    .font(.system(size: 16))
                    .foregroundStyle(isActive ? .primary : (isHovered ? .secondary : Color(nsColor: .tertiaryLabelColor)))
                    .frame(width: 36, height: 36)
            }
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.1)) {
                isHovered = hovering
            }
        }
        .help(item.isImplemented ? item.label : "\(item.label) — Coming soon")
    }
}

// MARK: - Preview

#Preview {
    CodeWorkspace()
        .frame(width: 1200, height: 800)
}
