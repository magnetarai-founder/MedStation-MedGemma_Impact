//
//  CodeWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Code editing workspace with activity bar, file browser, and full-height editor.
//  Terminal access via activity bar buttons (spawn external terminal or terminal bridge).
//  AI assistant available as detached window (⇧⌘P) — no longer embedded.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "CodeWorkspace")

struct CodeWorkspace: View {
    // MARK: - State

    @State private var selectedFile: FileItem? = nil
    @State private var openFiles: [FileItem] = []
    @State private var fileContent: String = ""
    @State private var originalFileContent: String = ""  // For modified detection
    @State private var currentWorkspace: CodeEditorWorkspace? = nil
    @State private var files: [FileItem] = []
    @State private var isLoadingFiles: Bool = false
    @State private var errorMessage: String? = nil
    @State private var isBackendOnline: Bool = true

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

    // Line navigation (set by search/LSP to scroll editor to a line)
    @State private var targetLine: Int?

    // B3: Embedded terminal
    @State private var showTerminal: Bool = false
    @AppStorage("code.terminalHeight") private var terminalHeight: Double = 200

    // C1: Quick open
    @State private var showQuickOpen: Bool = false

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

                // Left: Sidebar panel (switches based on activity bar selection)
                if showSidebar {
                    Group {
                        switch activeActivityItem {
                        case .files:
                            CodeFileBrowser(
                                currentWorkspace: currentWorkspace,
                                files: files,
                                isLoadingFiles: isLoadingFiles,
                                selectedFile: selectedFile,
                                onRefresh: loadFiles,
                                onSelectFile: selectFile
                            )
                        case .search:
                            CodeSearchPanel(
                                workspacePath: currentWorkspace?.diskPath ?? codingStore.workingDirectory,
                                onOpenFile: openFileAtLine
                            )
                        case .sourceControl:
                            CodeSourceControlPanel(
                                workspacePath: currentWorkspace?.diskPath ?? codingStore.workingDirectory,
                                onSelectFile: { path in openLocalFile(path) }
                            )
                        case .gitLog:
                            GitLogPanel(
                                workspacePath: currentWorkspace?.diskPath ?? codingStore.workingDirectory
                            )
                        case .debug:
                            CodeComingSoonPanel(panelName: "Debug", icon: "ladybug")
                        case .extensions:
                            CodeComingSoonPanel(panelName: "Extensions", icon: "square.grid.2x2")
                        }
                    }
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

                // Center: Code Editor + optional Terminal
                VStack(spacing: 0) {
                    CodeEditorArea(
                        openFiles: openFiles,
                        selectedFile: selectedFile,
                        workspaceName: currentWorkspace?.name,
                        fileContent: $fileContent,
                        isModified: isFileModified,
                        targetLine: targetLine,
                        onSelectFile: selectFile,
                        onCloseFile: closeFile,
                        onCursorMove: { line, col in
                            cursorLine = line
                            cursorColumn = col
                        },
                        onDropFile: { url in
                            openLocalFile(url.path)
                        }
                    )
                    .frame(minHeight: 100)
                    .onChange(of: fileContent) { _, newValue in
                        requestDiagnosticsRefresh(content: newValue)
                        codingStore.activeFileContent = newValue
                    }
                    .onChange(of: selectedFile) { _, newFile in
                        codingStore.activeFileName = newFile?.name
                    }
                    // Hidden save button for ⌘S
                    .background {
                        Button("") { saveCurrentFile() }
                            .keyboardShortcut("s", modifiers: .command)
                            .hidden()
                    }

                    // B3: Embedded terminal
                    if showTerminal {
                        ResizableDivider(
                            dimension: $terminalHeight,
                            axis: .vertical,
                            minValue: 100,
                            maxValue: 500,
                            defaultValue: 200
                        )

                        CodeTerminalPanel(
                            showTerminal: $showTerminal,
                            codingStore: codingStore,
                            onSpawnTerminal: { await spawnTerminal() }
                        )
                        .frame(height: CGFloat(terminalHeight))
                    }
                }
            }

            // Status Bar
            statusBar
        }
        // C1: Quick Open overlay
        .overlay {
            if showQuickOpen {
                ZStack {
                    Color.black.opacity(0.2)
                        .ignoresSafeArea()
                        .onTapGesture { showQuickOpen = false }

                    VStack {
                        QuickOpenPanel(
                            files: files,
                            onSelectFile: { file in
                                selectFile(file)
                            },
                            onDismiss: { showQuickOpen = false }
                        )
                        .padding(.top, 60)
                        Spacer()
                    }
                }
            }
        }
        // ⌘P shortcut for Quick Open
        .background {
            Button("") { showQuickOpen.toggle() }
                .keyboardShortcut("p", modifiers: .command)
                .hidden()
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
                    isActive: activeActivityItem == item && showSidebar
                ) {
                    if item == activeActivityItem {
                        withAnimation(.magnetarQuick) { showSidebar.toggle() }
                    } else {
                        activeActivityItem = item
                        if !showSidebar {
                            withAnimation(.magnetarQuick) { showSidebar = true }
                        }
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
            .help("AI Assistant (⇧⌘P)")

            // Toggle embedded terminal (primary), external terminal (context menu)
            Button {
                withAnimation(.magnetarQuick) { showTerminal.toggle() }
            } label: {
                Image(systemName: "terminal")
                    .font(.system(size: 16))
                    .foregroundStyle(showTerminal ? .primary : .secondary)
                    .frame(width: 36, height: 36)
            }
            .buttonStyle(.plain)
            .help("Toggle Terminal")
            .contextMenu {
                Button {
                    Task { await spawnTerminal() }
                } label: {
                    Label("Open External Terminal", systemImage: "rectangle.portrait.and.arrow.right")
                }

                Divider()

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

            // Backend health indicator
            HStack(spacing: 4) {
                Circle()
                    .fill(isBackendOnline ? Color.green : Color.orange)
                    .frame(width: 6, height: 6)
                Text(isBackendOnline ? "Online" : "Local")
                    .font(.system(size: 11))
            }
            .foregroundStyle(.secondary)
            .padding(.horizontal, 8)

            Color(nsColor: .separatorColor)
                .frame(width: 1, height: 12)

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

    // MARK: - File Save

    private var isFileModified: Bool {
        fileContent != originalFileContent && selectedFile != nil
    }

    private func saveCurrentFile() {
        guard isFileModified else { return }
        guard let file = selectedFile else { return }

        if let fileId = file.fileId {
            // Backend-managed file
            Task {
                do {
                    _ = try await codeEditorService.updateFile(fileId: fileId, content: fileContent)
                    await MainActor.run { originalFileContent = fileContent }
                    logger.info("Saved file via backend: \(file.name)")
                } catch {
                    logger.error("Failed to save file via backend: \(error)")
                }
            }
        } else {
            // Local file — write to disk
            do {
                try fileContent.write(toFile: file.path, atomically: true, encoding: .utf8)
                originalFileContent = fileContent
                logger.info("Saved local file: \(file.path)")
            } catch {
                logger.error("Failed to save local file: \(error)")
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
                isBackendOnline = true
            }
        } catch {
            logger.warning("Backend unavailable, falling back to local filesystem: \(error)")
            await MainActor.run { isBackendOnline = false }
            await loadLocalFiles()
        }
    }

    // Directories to skip during recursive scan
    private static let skipDirectories: Set<String> = [
        ".git", "node_modules", "__pycache__", ".build", ".swiftpm",
        "DerivedData", ".hg", ".svn", "Pods", "xcuserdata", ".DS_Store"
    ]

    /// Fallback: recursively scan local workspace directory when backend is unavailable
    private func loadLocalFiles() async {
        guard let workspacePath = codingStore.workingDirectory, !workspacePath.isEmpty else {
            await MainActor.run {
                files = []
                errorMessage = "No workspace folder configured"
                isLoadingFiles = false
            }
            return
        }

        do {
            let items = try scanDirectory(workspacePath, depth: 0)
            await MainActor.run {
                files = items
                isLoadingFiles = false
            }
        } catch {
            logger.error("Failed to scan local directory: \(error)")
            await MainActor.run {
                files = []
                errorMessage = "Failed to scan directory: \(error.localizedDescription)"
                isLoadingFiles = false
            }
        }
    }

    /// Recursively scan a directory, returning sorted FileItems (directories first)
    private func scanDirectory(_ path: String, depth: Int) throws -> [FileItem] {
        guard depth <= 4 else { return [] }

        let fm = FileManager.default
        let contents = try fm.contentsOfDirectory(atPath: path)

        var dirs: [FileItem] = []
        var regularFiles: [FileItem] = []

        for name in contents.sorted(by: { $0.localizedCaseInsensitiveCompare($1) == .orderedAscending }) {
            guard !name.hasPrefix(".") else { continue }
            guard !Self.skipDirectories.contains(name) else { continue }

            let fullPath = (path as NSString).appendingPathComponent(name)
            var isDir: ObjCBool = false
            guard fm.fileExists(atPath: fullPath, isDirectory: &isDir) else { continue }

            if isDir.boolValue {
                let children = (try? scanDirectory(fullPath, depth: depth + 1)) ?? []
                dirs.append(FileItem(
                    name: name,
                    path: fullPath,
                    isDirectory: true,
                    size: nil,
                    modifiedAt: nil,
                    fileId: nil,
                    children: children
                ))
            } else {
                let attrs = try? fm.attributesOfItem(atPath: fullPath)
                regularFiles.append(FileItem(
                    name: name,
                    path: fullPath,
                    isDirectory: false,
                    size: attrs?[.size] as? Int64,
                    modifiedAt: attrs?[.modificationDate] as? Date,
                    fileId: nil
                ))
            }
        }

        return dirs + regularFiles
    }

    private func selectFile(_ file: FileItem) {
        // Skip directory selection — expand/collapse handled by browser
        guard !file.isDirectory else { return }

        // Auto-save previous file if modified
        if isFileModified { saveCurrentFile() }

        selectedFile = file

        // Add to open files if not already open
        if !openFiles.contains(where: { $0.id == file.id }) {
            openFiles.append(file)
        }

        // Load file content
        Task {
            if let fileId = file.fileId {
                // Backend-managed file
                do {
                    let codeFile = try await codeEditorService.getFile(fileId: fileId)
                    await MainActor.run {
                        fileContent = codeFile.content
                        originalFileContent = codeFile.content
                    }
                } catch {
                    logger.error("Failed to load file content: \(error)")
                    await MainActor.run {
                        fileContent = "// Failed to load file content\n// Error: \(error.localizedDescription)"
                        originalFileContent = fileContent
                    }
                }
            } else {
                // Local file (offline fallback)
                do {
                    let content = try String(contentsOfFile: file.path, encoding: .utf8)
                    await MainActor.run {
                        fileContent = content
                        originalFileContent = content
                    }
                } catch {
                    logger.error("Failed to read local file: \(error)")
                    await MainActor.run {
                        fileContent = "// Failed to read file\n// Error: \(error.localizedDescription)"
                        originalFileContent = fileContent
                    }
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

    // MARK: - Local File Opening (for Search & Source Control)

    /// Open a local file at a specific line (from search results)
    private func openFileAtLine(_ path: String, _ line: Int) {
        // Clear previous target so the same line can be re-navigated
        targetLine = nil
        openLocalFile(path)
        // Set target line after a brief delay to ensure content is loaded
        Task {
            try? await Task.sleep(for: .milliseconds(150))
            await MainActor.run { targetLine = line }
        }
    }

    /// Open a local file by path (from source control panel)
    private func openLocalFile(_ path: String) {
        // Auto-save previous file if modified
        if isFileModified { saveCurrentFile() }

        let fileItem = fileItemFromPath(path)

        selectedFile = fileItem
        if !openFiles.contains(where: { $0.path == fileItem.path }) {
            openFiles.append(fileItem)
        }

        // Read content from disk directly (no backend)
        Task {
            do {
                let content = try String(contentsOfFile: path, encoding: .utf8)
                await MainActor.run {
                    fileContent = content
                    originalFileContent = content
                }
            } catch {
                logger.error("Failed to read local file: \(error)")
                await MainActor.run {
                    fileContent = "// Failed to read file\n// Error: \(error.localizedDescription)"
                    originalFileContent = fileContent
                }
            }
        }
    }

    private func fileItemFromPath(_ path: String) -> FileItem {
        let name = (path as NSString).lastPathComponent
        var isDir: ObjCBool = false
        FileManager.default.fileExists(atPath: path, isDirectory: &isDir)
        return FileItem(
            name: name,
            path: path,
            isDirectory: isDir.boolValue,
            size: nil,
            modifiedAt: nil,
            fileId: nil
        )
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

}

// MARK: - Activity Bar Item

enum ActivityBarItem: String, CaseIterable, Identifiable {
    case files
    case search
    case sourceControl
    case gitLog
    case debug
    case extensions

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .files: return "doc.on.doc"
        case .search: return "magnifyingglass"
        case .sourceControl: return "arrow.triangle.branch"
        case .gitLog: return "clock.arrow.circlepath"
        case .debug: return "ladybug"
        case .extensions: return "square.grid.2x2"
        }
    }

    var label: String {
        switch self {
        case .files: return "Explorer"
        case .search: return "Search"
        case .sourceControl: return "Source Control"
        case .gitLog: return "Git Log"
        case .debug: return "Debug"
        case .extensions: return "Extensions"
        }
    }

    var isImplemented: Bool {
        switch self {
        case .files, .search, .sourceControl, .gitLog: return true
        case .debug, .extensions: return false
        }
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
