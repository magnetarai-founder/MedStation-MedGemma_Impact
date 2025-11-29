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
    @State private var currentPath: String = "~"
    @State private var files: [FileItem] = []
    @State private var isLoadingFiles: Bool = false

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

                Text(currentPath)
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

            // Terminal content (placeholder for now)
            ScrollView {
                VStack(alignment: .leading, spacing: 4) {
                    Text("$ ")
                        .font(.system(size: 12, design: .monospaced))
                        .foregroundColor(.green)
                    + Text("Terminal integration coming soon...")
                        .font(.system(size: 12, design: .monospaced))
                        .foregroundColor(.primary)
                }
                .padding(12)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .background(Color.black.opacity(0.9))
        }
    }

    // MARK: - Actions

    private func loadFiles() async {
        isLoadingFiles = true

        // TODO: Load from backend file system API
        // For now, use mock data
        await MainActor.run {
            files = FileItem.mockFiles
            isLoadingFiles = false
        }
    }

    private func selectFile(_ file: FileItem) {
        selectedFile = file

        // Add to open files if not already open
        if !openFiles.contains(where: { $0.id == file.id }) {
            openFiles.append(file)
        }

        // TODO: Load file content from backend
        fileContent = "// Content of \(file.name)\n// TODO: Load from backend"
    }

    private func closeFile(_ file: FileItem) {
        openFiles.removeAll { $0.id == file.id }

        // If closing the selected file, select another
        if selectedFile?.id == file.id {
            selectedFile = openFiles.first
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

    static let mockFiles = [
        FileItem(name: "README.md", path: "/README.md", isDirectory: false, size: 1024, modifiedAt: Date()),
        FileItem(name: "src", path: "/src", isDirectory: true, size: nil, modifiedAt: Date()),
        FileItem(name: "main.swift", path: "/src/main.swift", isDirectory: false, size: 2048, modifiedAt: Date()),
        FileItem(name: "utils.swift", path: "/src/utils.swift", isDirectory: false, size: 512, modifiedAt: Date()),
        FileItem(name: "package.json", path: "/package.json", isDirectory: false, size: 256, modifiedAt: Date()),
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

// MARK: - Preview

#Preview {
    CodeWorkspace()
        .frame(width: 1200, height: 800)
}
