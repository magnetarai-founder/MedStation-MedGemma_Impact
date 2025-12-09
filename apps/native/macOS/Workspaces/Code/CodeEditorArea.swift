//
//  CodeEditorArea.swift
//  MagnetarStudio (macOS)
//
//  Editor area with tabs and content - Extracted from CodeWorkspace.swift (Phase 6.18)
//

import SwiftUI

struct CodeEditorArea: View {
    let openFiles: [FileItem]
    let selectedFile: FileItem?
    @Binding var fileContent: String
    let onSelectFile: (FileItem) -> Void
    let onCloseFile: (FileItem) -> Void

    var body: some View {
        VStack(spacing: 0) {
            // Tab bar
            if !openFiles.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 0) {
                        ForEach(openFiles) { file in
                            CodeFileTab(
                                file: file,
                                isSelected: selectedFile?.id == file.id,
                                onSelect: { onSelectFile(file) },
                                onClose: { onCloseFile(file) }
                            )
                        }
                    }
                }
                .frame(height: 36)
                .background(Color.surfaceTertiary.opacity(0.3))

                Divider()
            }

            // Editor content
            if selectedFile != nil {
                TextEditor(text: $fileContent)
                    .font(.system(size: 13, design: .monospaced))
                    .scrollContentBackground(.hidden)
                    .background(Color(nsColor: .textBackgroundColor))
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                CodeEditorWelcome()
            }
        }
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
