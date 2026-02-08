//
//  QuickOpenPanel.swift
//  MagnetarStudio (macOS)
//
//  ⌘P quick-open overlay with fuzzy file search.
//  Shows recent files when query is empty, fuzzy-matched results when typing.
//

import SwiftUI

struct QuickOpenPanel: View {
    let files: [FileItem]
    let onSelectFile: (FileItem) -> Void
    let onDismiss: () -> Void

    @State private var query = ""
    @State private var selectedIndex = 0
    @FocusState private var searchFocused: Bool

    private var flatFiles: [FileItem] {
        flattenFiles(files)
    }

    private var filteredFiles: [FileItem] {
        if query.isEmpty {
            return Array(flatFiles.prefix(20))
        }
        return flatFiles
            .filter { fuzzyMatch(query: query.lowercased(), target: $0.name.lowercased()) }
            .prefix(30)
            .map { $0 }
    }

    var body: some View {
        VStack(spacing: 0) {
            // Search field
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 14))
                    .foregroundStyle(.tertiary)

                TextField("Go to File...", text: $query)
                    .textFieldStyle(.plain)
                    .font(.system(size: 14))
                    .focused($searchFocused)
                    .onSubmit {
                        selectCurrent()
                    }
            }
            .padding(12)

            Divider()

            // Results
            if filteredFiles.isEmpty {
                VStack(spacing: 8) {
                    Text("No files found")
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity)
                .padding(.vertical, 20)
            } else {
                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 0) {
                            ForEach(Array(filteredFiles.enumerated()), id: \.element.id) { index, file in
                                quickOpenRow(file, isSelected: index == selectedIndex)
                                    .id(index)
                                    .onTapGesture {
                                        onSelectFile(file)
                                        onDismiss()
                                    }
                            }
                        }
                    }
                    .onChange(of: selectedIndex) { _, newIndex in
                        withAnimation {
                            proxy.scrollTo(newIndex, anchor: .center)
                        }
                    }
                }
                .frame(maxHeight: 350)
            }
        }
        .frame(width: 500)
        .background(.regularMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 10))
        .shadow(color: .black.opacity(0.3), radius: 20, y: 10)
        .onAppear { searchFocused = true }
        .onChange(of: query) { _, _ in
            selectedIndex = 0
        }
        .onKeyPress(.upArrow) {
            if selectedIndex > 0 { selectedIndex -= 1 }
            return .handled
        }
        .onKeyPress(.downArrow) {
            if selectedIndex < filteredFiles.count - 1 { selectedIndex += 1 }
            return .handled
        }
        .onKeyPress(.escape) {
            onDismiss()
            return .handled
        }
    }

    // MARK: - Row

    private func quickOpenRow(_ file: FileItem, isSelected: Bool) -> some View {
        HStack(spacing: 8) {
            Image(systemName: file.iconName)
                .font(.system(size: 12))
                .foregroundStyle(file.iconColor)
                .frame(width: 18)

            VStack(alignment: .leading, spacing: 1) {
                Text(file.name)
                    .font(.system(size: 13, weight: isSelected ? .medium : .regular))
                    .foregroundStyle(.primary)
                    .lineLimit(1)

                // Show relative path
                Text(file.path)
                    .font(.system(size: 10))
                    .foregroundStyle(.tertiary)
                    .lineLimit(1)
                    .truncationMode(.head)
            }

            Spacer()
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(
            isSelected ? Color.accentColor.opacity(0.1) : Color.clear
        )
        .contentShape(Rectangle())
    }

    // MARK: - Helpers

    private func selectCurrent() {
        guard selectedIndex < filteredFiles.count else { return }
        onSelectFile(filteredFiles[selectedIndex])
        onDismiss()
    }

    private func flattenFiles(_ items: [FileItem]) -> [FileItem] {
        var result: [FileItem] = []
        for item in items {
            if !item.isDirectory {
                result.append(item)
            }
            if let children = item.children {
                result.append(contentsOf: flattenFiles(children))
            }
        }
        return result
    }

    /// Fuzzy match: each character in query appears in order in target
    private func fuzzyMatch(query: String, target: String) -> Bool {
        var targetIndex = target.startIndex
        for queryChar in query {
            guard let found = target[targetIndex...].firstIndex(of: queryChar) else {
                return false
            }
            targetIndex = target.index(after: found)
        }
        return true
    }
}
