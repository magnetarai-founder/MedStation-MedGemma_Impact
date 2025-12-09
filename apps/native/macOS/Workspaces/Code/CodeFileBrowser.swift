//
//  CodeFileBrowser.swift
//  MagnetarStudio (macOS)
//
//  File browser sidebar - Extracted from CodeWorkspace.swift (Phase 6.18)
//

import SwiftUI

struct CodeFileBrowser: View {
    let currentWorkspace: CodeEditorWorkspace?
    let files: [FileItem]
    let isLoadingFiles: Bool
    let selectedFile: FileItem?
    let onRefresh: () async -> Void
    let onSelectFile: (FileItem) -> Void

    var body: some View {
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
                    Task { await onRefresh() }
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

                Text(currentWorkspace?.name ?? "No workspace")
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
                            CodeFileRow(
                                file: file,
                                isSelected: selectedFile?.id == file.id,
                                onSelect: { onSelectFile(file) }
                            )
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
        }
        .background(Color.surfaceSecondary.opacity(0.1))
    }
}
