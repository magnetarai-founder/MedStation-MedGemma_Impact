//
//  CodeEditorArea.swift
//  MagnetarStudio (macOS)
//
//  Editor area with tabs, breadcrumbs, find bar, minimap, split editor, and drag-drop.
//  Extracted from CodeWorkspace.swift (Phase 6.18)
//

import SwiftUI
import UniformTypeIdentifiers

struct CodeEditorArea: View {
    let openFiles: [FileItem]
    let selectedFile: FileItem?
    let workspaceName: String?
    @Binding var fileContent: String
    var isModified: Bool = false
    var targetLine: Int?
    let onSelectFile: (FileItem) -> Void
    let onCloseFile: (FileItem) -> Void
    var onCursorMove: ((Int, Int) -> Void)?
    var onDropFile: ((URL) -> Void)?  // C3: file drop

    @AppStorage("showLineNumbers") private var showLineNumbers = true
    @AppStorage("editorFontSize") private var editorFontSize = 14
    @AppStorage("showMinimap") private var showMinimap = true

    @State private var showFindBar = false
    @State private var editorCoordinator: CodeTextView.Coordinator?
    @State private var cursorLine = 1
    @State private var visibleLineCount = 40

    // D1/D2: AI overlays
    @State private var showExplainPopover = false
    @State private var explainCode = ""
    @State private var showRenameSheet = false
    @State private var renameWord = ""
    @State private var renameContext = ""

    // C4: Split editor
    @State private var isSplit = false
    @State private var splitContent: String = ""
    @State private var splitFilePath: String?
    @State private var splitWidth: Double = 0.5 // fraction

    private var detectedLanguage: CodeLanguage {
        CodeLanguage.detect(from: selectedFile?.path ?? "")
    }

    private var splitLanguage: CodeLanguage {
        CodeLanguage.detect(from: splitFilePath ?? "")
    }

    private var totalLines: Int {
        fileContent.components(separatedBy: "\n").count
    }

    private var visibleLineRange: ClosedRange<Int> {
        let lower = max(1, cursorLine - visibleLineCount / 2)
        let upper = min(totalLines, lower + visibleLineCount)
        return lower...upper
    }

    var body: some View {
        VStack(spacing: 0) {
            // Tab bar
            if !openFiles.isEmpty {
                tabBar
                Divider()
            }

            // Breadcrumb bar + split toggle
            if selectedFile != nil {
                HStack(spacing: 0) {
                    breadcrumbBar
                    Spacer()
                    // Split toggle
                    Button {
                        withAnimation(.easeInOut(duration: 0.2)) {
                            if isSplit {
                                isSplit = false
                                splitContent = ""
                                splitFilePath = nil
                            } else if let file = selectedFile {
                                isSplit = true
                                splitContent = fileContent
                                splitFilePath = file.path
                            }
                        }
                    } label: {
                        Image(systemName: isSplit ? "rectangle" : "rectangle.split.2x1")
                            .font(.system(size: 11))
                            .foregroundStyle(isSplit ? Color.accentColor : Color.secondary)
                    }
                    .buttonStyle(.plain)
                    .padding(.trailing, 8)
                    .help(isSplit ? "Close Split" : "Split Editor")
                }
                Divider()
            }

            // Find bar (⌘F)
            if showFindBar && selectedFile != nil {
                FindReplaceBar(
                    isVisible: $showFindBar,
                    coordinator: editorCoordinator
                )
                Divider()
            }

            // Editor content + split + minimap
            if selectedFile != nil {
                HStack(spacing: 0) {
                    // Primary editor
                    primaryEditor
                        .frame(maxWidth: .infinity, maxHeight: .infinity)

                    // C4: Split editor
                    if isSplit {
                        Divider()
                        splitEditor
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                    }

                    // Minimap (right edge)
                    if showMinimap {
                        Divider()
                        EditorMinimap(
                            text: fileContent,
                            language: detectedLanguage,
                            visibleLineRange: visibleLineRange,
                            totalLines: totalLines,
                            onScrollToLine: { line in
                                editorCoordinator?.scrollToLine(line)
                            }
                        )
                    }
                }
                // C3: Drop support
                .onDrop(of: [.fileURL], isTargeted: nil) { providers in
                    handleDrop(providers)
                }
            } else {
                CodeEditorWelcome()
                    // C3: Drop on welcome view too
                    .onDrop(of: [.fileURL], isTargeted: nil) { providers in
                        handleDrop(providers)
                    }
            }
        }
        .background {
            // ⌘F toggles find bar
            Button("") { showFindBar.toggle() }
                .keyboardShortcut("f", modifiers: .command)
                .hidden()

            // Escape dismisses find bar + AI overlays
            Button("") {
                if showExplainPopover { showExplainPopover = false }
                else if showRenameSheet { showRenameSheet = false }
                else if showFindBar {
                    editorCoordinator?.clearFindHighlights()
                    showFindBar = false
                }
            }
            .keyboardShortcut(.escape, modifiers: [])
            .hidden()
        }
        // D1: Explain Selection overlay
        .overlay {
            if showExplainPopover {
                VStack {
                    Spacer()
                    HStack {
                        Spacer()
                        CodeExplainPopover(
                            selectedCode: explainCode,
                            language: detectedLanguage.rawValue,
                            isPresented: $showExplainPopover
                        )
                        .transition(.opacity.combined(with: .scale(scale: 0.95)))
                        Spacer()
                    }
                    Spacer()
                }
                .background(Color.black.opacity(0.15))
                .onTapGesture { showExplainPopover = false }
            }
        }
        .animation(.easeInOut(duration: 0.15), value: showExplainPopover)
        // D2: AI Rename sheet overlay
        .overlay {
            if showRenameSheet {
                VStack {
                    Spacer()
                    HStack {
                        Spacer()
                        AIRenameSheet(
                            originalName: renameWord,
                            codeContext: renameContext,
                            language: detectedLanguage.rawValue,
                            onRename: { newName in
                                editorCoordinator?.replaceAllOccurrences(
                                    of: renameWord, with: newName
                                )
                                showRenameSheet = false
                            },
                            onDismiss: { showRenameSheet = false }
                        )
                        .transition(.opacity.combined(with: .scale(scale: 0.95)))
                        Spacer()
                    }
                    Spacer()
                }
                .background(Color.black.opacity(0.15))
                .onTapGesture { showRenameSheet = false }
            }
        }
        .animation(.easeInOut(duration: 0.15), value: showRenameSheet)
    }

    // MARK: - Tab Bar

    private var tabBar: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 1) {
                ForEach(openFiles) { file in
                    CodeFileTab(
                        file: file,
                        isSelected: selectedFile?.id == file.id,
                        isModified: isModified && selectedFile?.id == file.id,
                        onSelect: { onSelectFile(file) },
                        onClose: { onCloseFile(file) }
                    )
                    .contextMenu {
                        if isSplit {
                            Button("Show in Split") {
                                openInSplit(file)
                            }
                        } else {
                            Button("Open in Split") {
                                isSplit = true
                                openInSplit(file)
                            }
                        }
                    }
                }
            }
            .padding(.horizontal, 4)
        }
        .frame(height: 30)
        .background(.bar)
    }

    // MARK: - Primary Editor

    private var primaryEditor: some View {
        CodeTextView(
            text: $fileContent,
            fontSize: CGFloat(editorFontSize),
            language: detectedLanguage,
            showLineNumbers: showLineNumbers,
            targetLine: targetLine,
            onCursorMove: { line, col in
                cursorLine = line
                onCursorMove?(line, col)
            },
            onCoordinatorReady: { coord in
                editorCoordinator = coord
            },
            onExplainSelection: { code in
                explainCode = code
                showExplainPopover = true
            },
            onAIRename: { word, context in
                renameWord = word
                renameContext = context
                showRenameSheet = true
            }
        )
    }

    // MARK: - C4: Split Editor

    private var splitEditor: some View {
        CodeTextView(
            text: $splitContent,
            fontSize: CGFloat(editorFontSize),
            language: splitLanguage,
            showLineNumbers: showLineNumbers,
            targetLine: nil,
            onCursorMove: { _, _ in }
        )
    }

    private func openInSplit(_ file: FileItem) {
        splitFilePath = file.path
        do {
            splitContent = try String(contentsOfFile: file.path, encoding: .utf8)
        } catch {
            splitContent = "// Failed to load: \(file.name)"
        }
    }

    // MARK: - C3: Drag & Drop

    private func handleDrop(_ providers: [NSItemProvider]) -> Bool {
        for provider in providers {
            provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier, options: nil) { item, _ in
                guard let data = item as? Data,
                      let url = URL(dataRepresentation: data, relativeTo: nil) else { return }
                DispatchQueue.main.async {
                    onDropFile?(url)
                }
            }
        }
        return true
    }

    // MARK: - Breadcrumb Bar

    private var breadcrumbBar: some View {
        HStack(spacing: 2) {
            breadcrumbSegment(name: workspaceName ?? "Workspace", icon: "folder")

            if let file = selectedFile {
                let segments = file.path.split(separator: "/").dropLast()
                ForEach(Array(segments.enumerated()), id: \.offset) { _, segment in
                    breadcrumbChevron
                    breadcrumbSegment(name: String(segment))
                }
                breadcrumbChevron
                breadcrumbSegment(name: file.name, isCurrent: true)
            }

            Spacer()
        }
        .padding(.horizontal, 12)
        .frame(height: 26)
        .background(Color(nsColor: .controlBackgroundColor).opacity(0.4))
    }

    private func breadcrumbSegment(name: String, icon: String? = nil, isCurrent: Bool = false) -> some View {
        HStack(spacing: 3) {
            if let icon {
                Image(systemName: icon)
                    .font(.system(size: 9))
            }
            Text(name)
                .font(.system(size: 11))
        }
        .foregroundStyle(isCurrent ? .primary : .secondary)
    }

    private var breadcrumbChevron: some View {
        Image(systemName: "chevron.right")
            .font(.system(size: 7, weight: .semibold))
            .foregroundStyle(.tertiary)
    }
}

// MARK: - Welcome View

struct CodeEditorWelcome: View {
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "chevron.left.forwardslash.chevron.right")
                .font(.system(size: 48))
                .foregroundStyle(LinearGradient.magnetarGradient)

            Text("Code Editor")
                .font(.title2)
                .fontWeight(.bold)

            Text("Select a file from the sidebar to start editing\nor drop a file here")
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
