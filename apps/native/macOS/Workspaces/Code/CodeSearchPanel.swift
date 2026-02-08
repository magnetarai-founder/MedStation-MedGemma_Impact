//
//  CodeSearchPanel.swift
//  MagnetarStudio (macOS)
//
//  Sidebar panel for workspace-wide text search.
//  Uses local `grep` via Process — works offline without backend.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "CodeSearch")

struct CodeSearchPanel: View {
    let workspacePath: String?
    let onOpenFile: (String, Int) -> Void

    @State private var searchQuery: String = ""
    @State private var replaceQuery: String = ""
    @State private var showReplace: Bool = false
    @State private var useRegex: Bool = false
    @State private var fileTypeFilter: FileTypeFilter = .all
    @State private var results: [SearchResultGroup] = []
    @State private var isSearching: Bool = false
    @State private var totalMatchCount: Int = 0
    @State private var errorMessage: String?
    @State private var searchTask: Task<Void, Never>?

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Search")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(.secondary)
                Spacer()

                // Regex toggle
                Toggle(isOn: $useRegex) {
                    Text(".*")
                        .font(.system(size: 10, weight: .semibold, design: .monospaced))
                }
                .toggleStyle(.button)
                .controlSize(.mini)
                .help("Regular Expression")
                .onChange(of: useRegex) { _, _ in debounceSearch() }

                // Replace toggle
                Button {
                    withAnimation(.easeInOut(duration: 0.15)) {
                        showReplace.toggle()
                    }
                } label: {
                    Image(systemName: showReplace ? "arrow.up.arrow.down.square.fill" : "arrow.up.arrow.down.square")
                        .font(.system(size: 12))
                        .foregroundStyle(showReplace ? .accentColor : .secondary)
                }
                .buttonStyle(.plain)
                .help("Toggle Replace")

                if isSearching {
                    ProgressView()
                        .scaleEffect(0.6)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)

            // Search input
            HStack(spacing: 6) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 11))
                    .foregroundStyle(.tertiary)

                TextField("Search files...", text: $searchQuery)
                    .textFieldStyle(.plain)
                    .font(.system(size: 12))
                    .onSubmit { executeSearch() }

                if !searchQuery.isEmpty {
                    Button {
                        searchQuery = ""
                        results = []
                        totalMatchCount = 0
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 10))
                            .foregroundStyle(.tertiary)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(8)
            .background(RoundedRectangle(cornerRadius: 6).fill(Color.primary.opacity(0.04)))
            .padding(.horizontal, 12)

            // Replace input
            if showReplace {
                HStack(spacing: 6) {
                    Image(systemName: "arrow.2.squarepath")
                        .font(.system(size: 11))
                        .foregroundStyle(.tertiary)

                    TextField("Replace...", text: $replaceQuery)
                        .textFieldStyle(.plain)
                        .font(.system(size: 12))
                }
                .padding(8)
                .background(RoundedRectangle(cornerRadius: 6).fill(Color.primary.opacity(0.04)))
                .padding(.horizontal, 12)
                .padding(.top, 4)
            }

            // File type filter
            HStack {
                Picker("", selection: $fileTypeFilter) {
                    ForEach(FileTypeFilter.allCases) { filter in
                        Text(filter.label).tag(filter)
                    }
                }
                .pickerStyle(.menu)
                .labelsHidden()
                .font(.system(size: 11))
                .frame(maxWidth: 120)

                Spacer()

                if totalMatchCount > 0 {
                    Text("\(totalMatchCount) result\(totalMatchCount == 1 ? "" : "s")")
                        .font(.system(size: 10))
                        .foregroundStyle(.tertiary)
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 4)

            Divider()

            // Results
            if let error = errorMessage {
                VStack(spacing: 8) {
                    Spacer()
                    Image(systemName: "exclamationmark.triangle")
                        .font(.system(size: 24))
                        .foregroundStyle(.orange)
                    Text(error)
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                    Spacer()
                }
                .padding()
            } else if results.isEmpty && !searchQuery.isEmpty && !isSearching {
                VStack(spacing: 8) {
                    Spacer()
                    Image(systemName: "magnifyingglass")
                        .font(.system(size: 24))
                        .foregroundStyle(.tertiary)
                    Text("No results found")
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                    Spacer()
                }
            } else if results.isEmpty {
                VStack(spacing: 8) {
                    Spacer()
                    Image(systemName: "magnifyingglass")
                        .font(.system(size: 24))
                        .foregroundStyle(.tertiary)
                    Text("Enter a search term")
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                    Spacer()
                }
            } else {
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 0) {
                        ForEach(results) { group in
                            SearchFileGroup(
                                group: group,
                                onOpenFile: onOpenFile,
                                showReplace: showReplace,
                                onReplaceInFile: {
                                    replaceInFile(group: group)
                                }
                            )
                        }
                    }
                    .padding(.vertical, 4)
                }
            }
        }
        .onChange(of: searchQuery) { _, _ in
            debounceSearch()
        }
    }

    // MARK: - Search Logic

    private func debounceSearch() {
        searchTask?.cancel()
        searchTask = Task {
            try? await Task.sleep(for: .milliseconds(500))
            guard !Task.isCancelled else { return }
            executeSearch()
        }
    }

    private func executeSearch() {
        let query = searchQuery.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !query.isEmpty else {
            results = []
            totalMatchCount = 0
            return
        }

        guard let cwd = workspacePath else {
            errorMessage = "No workspace folder open"
            return
        }

        isSearching = true
        errorMessage = nil

        Task {
            do {
                var args = ["grep", "-rn", "--max-count=500", "--binary-files=without-match"]

                if let includePattern = fileTypeFilter.grepInclude {
                    args.append("--include=\(includePattern)")
                }

                args.append(query)
                args.append(".")

                let output = try await runCommand(args, cwd: cwd)
                let parsed = parseGrepOutput(output, basePath: cwd)

                await MainActor.run {
                    results = parsed.groups
                    totalMatchCount = parsed.totalCount
                    isSearching = false
                }
            } catch {
                logger.error("Search failed: \(error)")
                await MainActor.run {
                    errorMessage = "Search failed: \(error.localizedDescription)"
                    isSearching = false
                }
            }
        }
    }

    private func parseGrepOutput(_ output: String, basePath: String) -> (groups: [SearchResultGroup], totalCount: Int) {
        let lines = output.components(separatedBy: "\n").filter { !$0.isEmpty }
        var itemsByFile: [String: [SearchResultItem]] = [:]

        for line in lines {
            // grep output format: ./path/to/file:lineNumber:content
            guard let firstColon = line.firstIndex(of: ":") else { continue }
            let rawPath = String(line[line.startIndex..<firstColon])

            let rest = String(line[line.index(after: firstColon)...])
            guard let secondColon = rest.firstIndex(of: ":") else { continue }

            let lineNumStr = String(rest[rest.startIndex..<secondColon])
            guard let lineNumber = Int(lineNumStr) else { continue }

            let content = String(rest[rest.index(after: secondColon)...]).trimmingCharacters(in: .whitespaces)

            // Normalize path: remove leading "./"
            let cleanPath: String
            if rawPath.hasPrefix("./") {
                cleanPath = String(rawPath.dropFirst(2))
            } else {
                cleanPath = rawPath
            }

            let fullPath = (basePath as NSString).appendingPathComponent(cleanPath)

            let item = SearchResultItem(
                filePath: fullPath,
                lineNumber: lineNumber,
                lineContent: String(content.prefix(200))
            )

            itemsByFile[cleanPath, default: []].append(item)
        }

        let groups = itemsByFile.map { path, items in
            let fileName = (path as NSString).lastPathComponent
            return SearchResultGroup(relativePath: path, fileName: fileName, items: items)
        }
        .sorted { $0.relativePath < $1.relativePath }

        return (groups, lines.count)
    }

    private func replaceInFile(group: SearchResultGroup) {
        guard let first = group.items.first else { return }
        let filePath = first.filePath

        do {
            var content = try String(contentsOfFile: filePath, encoding: .utf8)
            if useRegex {
                guard let regex = try? NSRegularExpression(pattern: searchQuery) else { return }
                content = regex.stringByReplacingMatches(
                    in: content,
                    range: NSRange(content.startIndex..., in: content),
                    withTemplate: replaceQuery
                )
            } else {
                content = content.replacingOccurrences(of: searchQuery, with: replaceQuery)
            }
            try content.write(toFile: filePath, atomically: true, encoding: .utf8)
            // Re-run search to update results
            executeSearch()
        } catch {
            logger.error("Replace in file failed: \(error)")
        }
    }

    private func runCommand(_ args: [String], cwd: String) async throws -> String {
        let process = Process()
        process.executableURL = URL(fileURLWithPath: "/usr/bin/env")
        process.arguments = args
        process.currentDirectoryURL = URL(fileURLWithPath: cwd)

        let outPipe = Pipe()
        let errPipe = Pipe()
        process.standardOutput = outPipe
        process.standardError = errPipe

        try process.run()
        let data = outPipe.fileHandleForReading.readDataToEndOfFile()
        process.waitUntilExit()

        // grep returns exit code 1 for no matches — not an error
        if process.terminationStatus > 1 {
            let errData = errPipe.fileHandleForReading.readDataToEndOfFile()
            let errStr = String(data: errData, encoding: .utf8) ?? "Unknown error"
            throw SearchError.commandFailed(errStr)
        }

        return String(data: data, encoding: .utf8) ?? ""
    }
}

// MARK: - Models

fileprivate struct SearchResultItem: Identifiable {
    let id = UUID()
    let filePath: String
    let lineNumber: Int
    let lineContent: String
}

fileprivate struct SearchResultGroup: Identifiable {
    let id = UUID()
    let relativePath: String
    let fileName: String
    let items: [SearchResultItem]
}

private enum FileTypeFilter: String, CaseIterable, Identifiable {
    case all
    case swift
    case python
    case javascript
    case typescript
    case json
    case markdown

    var id: String { rawValue }

    var label: String {
        switch self {
        case .all: return "All Files"
        case .swift: return "Swift"
        case .python: return "Python"
        case .javascript: return "JavaScript"
        case .typescript: return "TypeScript"
        case .json: return "JSON"
        case .markdown: return "Markdown"
        }
    }

    var grepInclude: String? {
        switch self {
        case .all: return nil
        case .swift: return "*.swift"
        case .python: return "*.py"
        case .javascript: return "*.js"
        case .typescript: return "*.ts"
        case .json: return "*.json"
        case .markdown: return "*.md"
        }
    }
}

private enum SearchError: LocalizedError {
    case commandFailed(String)

    var errorDescription: String? {
        switch self {
        case .commandFailed(let msg): return msg
        }
    }
}

// MARK: - Result Row Views

private struct SearchFileGroup: View {
    let group: SearchResultGroup
    let onOpenFile: (String, Int) -> Void
    var showReplace: Bool = false
    var onReplaceInFile: (() -> Void)?
    @State private var isExpanded = true

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // File header
            HStack(spacing: 0) {
                Button {
                    withAnimation(.easeInOut(duration: 0.15)) { isExpanded.toggle() }
                } label: {
                    HStack(spacing: 6) {
                        Image(systemName: isExpanded ? "chevron.down" : "chevron.right")
                            .font(.system(size: 8))
                            .foregroundStyle(.tertiary)
                            .frame(width: 10)

                        Image(systemName: "doc")
                            .font(.system(size: 10))
                            .foregroundStyle(.secondary)

                        Text(group.fileName)
                            .font(.system(size: 12, weight: .medium))
                            .foregroundStyle(.primary)
                            .lineLimit(1)

                        Text(group.relativePath)
                            .font(.system(size: 10))
                            .foregroundStyle(.tertiary)
                            .lineLimit(1)
                            .truncationMode(.middle)
                    }
                    .contentShape(Rectangle())
                }
                .buttonStyle(.plain)

                Spacer()

                if showReplace {
                    Button {
                        onReplaceInFile?()
                    } label: {
                        Text("Replace")
                            .font(.system(size: 9, weight: .medium))
                            .foregroundStyle(.accentColor)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(RoundedRectangle(cornerRadius: 3).fill(Color.accentColor.opacity(0.1)))
                    }
                    .buttonStyle(.plain)
                }

                Text("\(group.items.count)")
                    .font(.system(size: 10, design: .monospaced))
                    .foregroundStyle(.tertiary)
                    .padding(.horizontal, 4)
                    .padding(.vertical, 1)
                    .background(RoundedRectangle(cornerRadius: 3).fill(Color.primary.opacity(0.05)))
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 5)

            if isExpanded {
                ForEach(group.items) { item in
                    Button {
                        onOpenFile(item.filePath, item.lineNumber)
                    } label: {
                        HStack(spacing: 6) {
                            Text("\(item.lineNumber)")
                                .font(.system(size: 10, design: .monospaced))
                                .foregroundStyle(.tertiary)
                                .frame(width: 36, alignment: .trailing)

                            Text(item.lineContent)
                                .font(.system(size: 11, design: .monospaced))
                                .foregroundStyle(.secondary)
                                .lineLimit(1)
                                .truncationMode(.tail)

                            Spacer()
                        }
                        .padding(.horizontal, 12)
                        .padding(.leading, 16)
                        .padding(.vertical, 3)
                        .contentShape(Rectangle())
                    }
                    .buttonStyle(.plain)
                    .onHover { hovering in
                        if hovering {
                            NSCursor.pointingHand.push()
                        } else {
                            NSCursor.pop()
                        }
                    }
                }
            }
        }
    }
}
