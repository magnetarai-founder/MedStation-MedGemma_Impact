//
//  CodeDiffView.swift
//  MagnetarStudio (macOS)
//
//  Renders unified git diff output with red/green line highlighting.
//  Used by CodeSourceControlPanel to show file changes inline.
//

import SwiftUI

struct CodeDiffView: View {
    let diffOutput: String
    let fileName: String

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            HStack(spacing: 6) {
                Image(systemName: "doc.text.magnifyingglass")
                    .font(.system(size: 10))
                    .foregroundStyle(.secondary)
                Text(fileName)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundStyle(.primary)
                    .lineLimit(1)
                Spacer()
                Text("\(addedCount) added, \(removedCount) removed")
                    .font(.system(size: 10, design: .monospaced))
                    .foregroundStyle(.secondary)
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(Color.primary.opacity(0.04))

            Divider()

            // Diff lines
            if parsedLines.isEmpty {
                VStack(spacing: 8) {
                    Spacer()
                    Text("No diff available")
                        .font(.system(size: 12))
                        .foregroundStyle(.secondary)
                    Spacer()
                }
                .frame(maxWidth: .infinity)
            } else {
                ScrollView(.vertical) {
                    ScrollView(.horizontal, showsIndicators: false) {
                        LazyVStack(alignment: .leading, spacing: 0) {
                            ForEach(parsedLines) { line in
                                DiffLineRow(line: line)
                            }
                        }
                    }
                }
            }
        }
    }

    // MARK: - Parsing

    private var parsedLines: [DiffLine] {
        let lines = diffOutput.components(separatedBy: "\n")
        return lines.enumerated().compactMap { index, content in
            guard !content.isEmpty else { return nil }

            let type: DiffLineType
            if content.hasPrefix("+++") || content.hasPrefix("---") {
                type = .fileHeader
            } else if content.hasPrefix("@@") {
                type = .hunkHeader
            } else if content.hasPrefix("+") {
                type = .added
            } else if content.hasPrefix("-") {
                type = .removed
            } else if content.hasPrefix("diff ") || content.hasPrefix("index ") {
                type = .metaHeader
            } else {
                type = .context
            }

            return DiffLine(id: index, content: content, type: type)
        }
    }

    private var addedCount: Int {
        parsedLines.filter { $0.type == .added }.count
    }

    private var removedCount: Int {
        parsedLines.filter { $0.type == .removed }.count
    }
}

// MARK: - Models

struct DiffLine: Identifiable, Sendable {
    let id: Int
    let content: String
    let type: DiffLineType
}

enum DiffLineType: Sendable {
    case added
    case removed
    case context
    case hunkHeader
    case fileHeader
    case metaHeader
}

// MARK: - Diff Line Row

private struct DiffLineRow: View {
    let line: DiffLine

    var body: some View {
        HStack(spacing: 0) {
            // Gutter symbol
            Text(gutterSymbol)
                .font(.system(size: 11, weight: .medium, design: .monospaced))
                .foregroundStyle(gutterColor)
                .frame(width: 18, alignment: .center)

            // Content
            Text(displayContent)
                .font(.system(size: 11, design: .monospaced))
                .foregroundStyle(textColor)
                .textSelection(.enabled)
        }
        .padding(.horizontal, 4)
        .frame(maxWidth: .infinity, alignment: .leading)
        .frame(height: 18)
        .background(backgroundColor)
    }

    private var displayContent: String {
        // Strip the leading +/- for added/removed lines
        switch line.type {
        case .added, .removed:
            return String(line.content.dropFirst())
        default:
            return line.content
        }
    }

    private var gutterSymbol: String {
        switch line.type {
        case .added: return "+"
        case .removed: return "-"
        default: return " "
        }
    }

    private var gutterColor: Color {
        switch line.type {
        case .added: return .green
        case .removed: return .red
        default: return .clear
        }
    }

    private var textColor: Color {
        switch line.type {
        case .hunkHeader, .fileHeader, .metaHeader: return .secondary
        default: return .primary
        }
    }

    private var backgroundColor: Color {
        switch line.type {
        case .added: return Color.green.opacity(0.1)
        case .removed: return Color.red.opacity(0.1)
        case .hunkHeader: return Color.blue.opacity(0.05)
        case .fileHeader, .metaHeader: return Color.primary.opacity(0.03)
        case .context: return .clear
        }
    }
}
