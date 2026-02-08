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
    var isModified: Bool = false
    var targetLine: Int?
    let onSelectFile: (FileItem) -> Void
    let onCloseFile: (FileItem) -> Void
    var onCursorMove: ((Int, Int) -> Void)?

    @AppStorage("showLineNumbers") private var showLineNumbers = true
    @AppStorage("editorFontSize") private var editorFontSize = 14

    private var detectedLanguage: CodeLanguage {
        CodeLanguage.detect(from: selectedFile?.path ?? "")
    }

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
                                isModified: isModified && selectedFile?.id == file.id,
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
                CodeTextView(
                    text: $fileContent,
                    fontSize: CGFloat(editorFontSize),
                    language: detectedLanguage,
                    showLineNumbers: showLineNumbers,
                    targetLine: targetLine,
                    onCursorMove: { line, col in
                        onCursorMove?(line, col)
                    }
                )
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
