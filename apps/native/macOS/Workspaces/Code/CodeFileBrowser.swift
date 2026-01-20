//
//  CodeFileBrowser.swift
//  MagnetarStudio (macOS)
//
//  File browser sidebar - Extracted from CodeWorkspace.swift (Phase 6.18)
//  Enhanced with search, file counts, and visual polish
//

import SwiftUI

struct CodeFileBrowser: View {
    let currentWorkspace: CodeEditorWorkspace?
    let files: [FileItem]
    let isLoadingFiles: Bool
    let selectedFile: FileItem?
    let onRefresh: () async -> Void
    let onSelectFile: (FileItem) -> Void

    @State private var searchText: String = ""
    @State private var isRefreshing = false

    var filteredFiles: [FileItem] {
        if searchText.isEmpty {
            return files
        }
        return files.filter {
            $0.name.localizedCaseInsensitiveContains(searchText)
        }
    }

    var fileCount: Int {
        files.filter { !$0.isDirectory }.count
    }

    var folderCount: Int {
        files.filter { $0.isDirectory }.count
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Image(systemName: "folder")
                    .font(.system(size: 14))
                    .foregroundColor(.magnetarPrimary)

                Text("Files")
                    .font(.system(size: 14, weight: .semibold))

                // File count badge
                if !files.isEmpty {
                    Text("\(fileCount)")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 6)
                        .padding(.vertical, 2)
                        .background(Color.magnetarPrimary.opacity(0.8))
                        .clipShape(Capsule())
                }

                Spacer()

                Button {
                    Task {
                        isRefreshing = true
                        await onRefresh()
                        isRefreshing = false
                    }
                } label: {
                    Image(systemName: "arrow.clockwise")
                        .font(.system(size: 12))
                        .rotationEffect(.degrees(isRefreshing ? 360 : 0))
                        .animation(isRefreshing ? .linear(duration: 1).repeatForever(autoreverses: false) : .default, value: isRefreshing)
                }
                .buttonStyle(.plain)
                .disabled(isRefreshing)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 10)
            .background(Color.surfaceSecondary.opacity(0.3))

            Divider()

            // Search bar
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
                TextField("Search files...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 12))
                if !searchText.isEmpty {
                    Button(action: { searchText = "" }) {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 11))
                            .foregroundStyle(.tertiary)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(Color.gray.opacity(0.1))
            .clipShape(RoundedRectangle(cornerRadius: 6))
            .padding(.horizontal, 8)
            .padding(.vertical, 8)

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

                if folderCount > 0 {
                    Label("\(folderCount)", systemImage: "folder")
                        .font(.system(size: 10))
                        .foregroundStyle(.tertiary)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Color.surfaceTertiary.opacity(0.2))

            Divider()

            // File list
            if isLoadingFiles {
                VStack(spacing: 12) {
                    ProgressView()
                    Text("Loading files...")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if files.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: "folder.badge.questionmark")
                        .font(.system(size: 32))
                        .foregroundStyle(.tertiary)
                    Text("No Files")
                        .font(.headline)
                        .foregroundStyle(.secondary)
                    Text("This workspace is empty")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if filteredFiles.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: "magnifyingglass")
                        .font(.system(size: 32))
                        .foregroundStyle(.tertiary)
                    Text("No Matches")
                        .font(.headline)
                        .foregroundStyle(.secondary)
                    Text("Try a different search term")
                        .font(.caption)
                        .foregroundStyle(.tertiary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 2) {
                        ForEach(filteredFiles) { file in
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
