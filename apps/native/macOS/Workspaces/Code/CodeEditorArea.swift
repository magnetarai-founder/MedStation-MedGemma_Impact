//
//  CodeEditorArea.swift
//  MagnetarStudio (macOS)
//
//  Editor area with tabs, breadcrumbs, line number gutter, and content.
//  Extracted from CodeWorkspace.swift (Phase 6.18)
//  Enhanced with breadcrumb bar and line number gutter (Native IDE Redesign)
//

import SwiftUI

struct CodeEditorArea: View {
    let openFiles: [FileItem]
    let selectedFile: FileItem?
    let workspaceName: String?
    @Binding var fileContent: String
    var targetLine: Int?
    let onSelectFile: (FileItem) -> Void
    let onCloseFile: (FileItem) -> Void
    var onCursorMove: ((Int, Int) -> Void)?

    @AppStorage("showLineNumbers") private var showLineNumbers = true
    @AppStorage("editorFontSize") private var editorFontSize = 14

    var body: some View {
        VStack(spacing: 0) {
            // Tab bar
            if !openFiles.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 1) {
                        ForEach(openFiles) { file in
                            CodeFileTab(
                                file: file,
                                isSelected: selectedFile?.id == file.id,
                                onSelect: { onSelectFile(file) },
                                onClose: { onCloseFile(file) }
                            )
                        }
                    }
                    .padding(.horizontal, 4)
                }
                .frame(height: 30)
                .background(.bar)

                Divider()
            }

            // Breadcrumb bar
            if selectedFile != nil {
                breadcrumbBar
                Divider()
            }

            // Editor content
            if selectedFile != nil {
                HStack(spacing: 0) {
                    // Line number gutter (respects settings)
                    if showLineNumbers {
                        LineNumberGutter(text: fileContent, fontSize: CGFloat(max(editorFontSize - 2, 9)))

                        // Thin separator
                        Rectangle()
                            .fill(Color(nsColor: .separatorColor))
                            .frame(width: 1)
                    }

                    // Editor (NSTextView for cursor positioning + scroll-to-line)
                    CodeTextView(
                        text: $fileContent,
                        fontSize: CGFloat(editorFontSize),
                        targetLine: targetLine,
                        onCursorMove: { line, col in
                            onCursorMove?(line, col)
                        }
                    )
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                CodeEditorWelcome()
            }
        }
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

// MARK: - Line Number Gutter

private struct LineNumberGutter: View {
    let text: String
    var fontSize: CGFloat = 11

    private var lineCount: Int {
        max(text.components(separatedBy: "\n").count, 1)
    }

    /// Line height matches TextEditor's default line spacing for the given font size
    private var lineHeight: CGFloat {
        max(fontSize * 1.4, 16)
    }

    var body: some View {
        ScrollView(.vertical, showsIndicators: false) {
            VStack(alignment: .trailing, spacing: 0) {
                ForEach(1...lineCount, id: \.self) { lineNumber in
                    Text("\(lineNumber)")
                        .font(.system(size: fontSize, design: .monospaced))
                        .foregroundStyle(.tertiary)
                        .frame(height: lineHeight)
                }
            }
            .padding(.top, 7)
            .padding(.trailing, 8)
            .padding(.leading, 4)
        }
        .frame(width: max(44, fontSize * 4))
        .background(Color(nsColor: .textBackgroundColor).opacity(0.5))
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

            Text("Select a file from the sidebar to start editing")
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}
