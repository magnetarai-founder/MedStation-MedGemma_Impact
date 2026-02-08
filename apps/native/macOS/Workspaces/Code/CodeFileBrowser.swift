//
//  CodeFileBrowser.swift
//  MagnetarStudio (macOS)
//
//  File browser sidebar with recursive tree rendering and search.
//  Directories show disclosure triangles; click expands/collapses.
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
    @State private var expandedFolders: Set<String> = []
    @AppStorage("enableBlurEffects") private var enableBlurEffects = true
    @AppStorage("reduceTransparency") private var reduceTransparency = false

    var filteredFiles: [FileItem] {
        if searchText.isEmpty {
            return files
        }
        return flattenAndFilter(files, query: searchText)
    }

    var fileCount: Int {
        countFiles(in: files)
    }

    var folderCount: Int {
        files.filter { $0.isDirectory }.count
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Files")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(.secondary)
                    .textCase(.uppercase)

                if fileCount > 0 {
                    Text("(\(fileCount))")
                        .font(.system(size: 11))
                        .foregroundStyle(.tertiary)
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
                        .font(.system(size: 11))
                        .foregroundStyle(.tertiary)
                        .rotationEffect(.degrees(isRefreshing ? 360 : 0))
                        .animation(isRefreshing ? .linear(duration: 1).repeatForever(autoreverses: false) : .default, value: isRefreshing)
                }
                .buttonStyle(.plain)
                .disabled(isRefreshing)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)

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
            .background(Color(nsColor: .quaternaryLabelColor).opacity(0.5))
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .padding(.horizontal, 8)
            .padding(.vertical, 8)

            // Path bar
            HStack(spacing: 4) {
                Text(currentWorkspace?.name ?? "No workspace")
                    .font(.system(size: 11))
                    .foregroundStyle(.tertiary)
                    .lineLimit(1)

                Spacer()
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 4)

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
                    LazyVStack(alignment: .leading, spacing: 0) {
                        if searchText.isEmpty {
                            // Tree view
                            ForEach(files) { file in
                                FileTreeRow(
                                    file: file,
                                    depth: 0,
                                    selectedFile: selectedFile,
                                    expandedFolders: $expandedFolders,
                                    onSelectFile: onSelectFile
                                )
                            }
                        } else {
                            // Flat filtered results
                            ForEach(filteredFiles) { file in
                                CodeFileRow(
                                    file: file,
                                    isSelected: selectedFile?.id == file.id,
                                    onSelect: { onSelectFile(file) }
                                )
                            }
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
        }
        .background {
            if enableBlurEffects && !reduceTransparency {
                AnyView(Rectangle().fill(.ultraThinMaterial))
            } else {
                AnyView(Color(nsColor: .controlBackgroundColor))
            }
        }
    }

    // MARK: - Helpers

    /// Recursively count all files (non-directory) in the tree
    private func countFiles(in items: [FileItem]) -> Int {
        items.reduce(0) { count, item in
            if item.isDirectory {
                return count + countFiles(in: item.children ?? [])
            }
            return count + 1
        }
    }

    /// Flatten tree and filter by search query (returns files only)
    private func flattenAndFilter(_ items: [FileItem], query: String) -> [FileItem] {
        var result: [FileItem] = []
        for item in items {
            if item.isDirectory {
                result.append(contentsOf: flattenAndFilter(item.children ?? [], query: query))
            } else if item.name.localizedCaseInsensitiveContains(query) {
                result.append(item)
            }
        }
        return result
    }
}

// MARK: - Recursive File Tree Row

private struct FileTreeRow: View {
    let file: FileItem
    let depth: Int
    let selectedFile: FileItem?
    @Binding var expandedFolders: Set<String>
    let onSelectFile: (FileItem) -> Void

    private var isExpanded: Bool {
        expandedFolders.contains(file.path)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // This row
            HStack(spacing: 4) {
                // Indentation
                if depth > 0 {
                    Spacer()
                        .frame(width: CGFloat(depth) * 16)
                }

                // Disclosure triangle for directories
                if file.isDirectory {
                    Image(systemName: isExpanded ? "chevron.down" : "chevron.right")
                        .font(.system(size: 8, weight: .semibold))
                        .foregroundStyle(.tertiary)
                        .frame(width: 12)
                } else {
                    Spacer().frame(width: 12)
                }

                // File icon
                Image(systemName: file.iconName)
                    .font(.system(size: 11))
                    .foregroundColor(selectedFile?.id == file.id ? .white : file.iconColor)
                    .frame(width: 14)

                // File name
                Text(file.name)
                    .font(.system(size: 12))
                    .lineLimit(1)
                    .foregroundStyle(selectedFile?.id == file.id ? .white : .primary)

                Spacer()
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .frame(height: 24)
            .background(
                RoundedRectangle(cornerRadius: 4)
                    .fill(selectedFile?.id == file.id ? Color.accentColor : Color.clear)
                    .padding(.horizontal, 4)
            )
            .contentShape(Rectangle())
            .onTapGesture {
                if file.isDirectory {
                    withAnimation(.magnetarQuick) {
                        if isExpanded {
                            expandedFolders.remove(file.path)
                        } else {
                            expandedFolders.insert(file.path)
                        }
                    }
                } else {
                    onSelectFile(file)
                }
            }

            // Children (if expanded)
            if file.isDirectory && isExpanded, let children = file.children {
                ForEach(children) { child in
                    FileTreeRow(
                        file: child,
                        depth: depth + 1,
                        selectedFile: selectedFile,
                        expandedFolders: $expandedFolders,
                        onSelectFile: onSelectFile
                    )
                }
            }
        }
    }
}
