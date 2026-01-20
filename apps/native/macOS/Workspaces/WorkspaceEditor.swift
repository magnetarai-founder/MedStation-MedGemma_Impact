//
//  WorkspaceEditor.swift
//  MagnetarStudio (macOS)
//
//  Notion-style editor with:
//  - Slash commands (/) for inserting blocks
//  - Right-click context menu for formatting
//  - No toolbar - everything via keyboard or context menu
//

import SwiftUI
import AppKit

// MARK: - Slash Command Types

enum SlashCommand: String, CaseIterable, Identifiable {
    // Text
    case heading1 = "heading1"
    case heading2 = "heading2"
    case heading3 = "heading3"
    case text = "text"

    // Lists
    case bulletList = "bullet"
    case numberedList = "numbered"
    case checkbox = "checkbox"

    // Media & Code
    case code = "code"
    case quote = "quote"
    case divider = "divider"
    case callout = "callout"

    // Advanced
    case table = "table"
    case toggleList = "toggle"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .heading1: return "textformat.size.larger"
        case .heading2: return "textformat.size"
        case .heading3: return "textformat.size.smaller"
        case .text: return "text.alignleft"
        case .bulletList: return "list.bullet"
        case .numberedList: return "list.number"
        case .checkbox: return "checkmark.square"
        case .code: return "chevron.left.forwardslash.chevron.right"
        case .quote: return "text.quote"
        case .divider: return "minus"
        case .callout: return "exclamationmark.bubble"
        case .table: return "tablecells"
        case .toggleList: return "chevron.right"
        }
    }

    var title: String {
        switch self {
        case .heading1: return "Heading 1"
        case .heading2: return "Heading 2"
        case .heading3: return "Heading 3"
        case .text: return "Text"
        case .bulletList: return "Bullet List"
        case .numberedList: return "Numbered List"
        case .checkbox: return "Checkbox"
        case .code: return "Code Block"
        case .quote: return "Quote"
        case .divider: return "Divider"
        case .callout: return "Callout"
        case .table: return "Table"
        case .toggleList: return "Toggle List"
        }
    }

    var description: String {
        switch self {
        case .heading1: return "Large section heading"
        case .heading2: return "Medium section heading"
        case .heading3: return "Small section heading"
        case .text: return "Plain text paragraph"
        case .bulletList: return "Simple bullet point"
        case .numberedList: return "Numbered list item"
        case .checkbox: return "Task with checkbox"
        case .code: return "Code snippet with syntax highlighting"
        case .quote: return "Quote or excerpt"
        case .divider: return "Visual divider line"
        case .callout: return "Highlighted info box"
        case .table: return "Simple table"
        case .toggleList: return "Collapsible content"
        }
    }

    var shortcut: String {
        switch self {
        case .heading1: return "# "
        case .heading2: return "## "
        case .heading3: return "### "
        case .text: return ""
        case .bulletList: return "- "
        case .numberedList: return "1. "
        case .checkbox: return "[ ] "
        case .code: return "```\n"
        case .quote: return "> "
        case .divider: return "---\n"
        case .callout: return "> 💡 "
        case .table: return "| Column 1 | Column 2 |\n|----------|----------|\n| Cell     | Cell     |\n"
        case .toggleList: return "▶ "
        }
    }

    var category: CommandCategory {
        switch self {
        case .heading1, .heading2, .heading3, .text:
            return .text
        case .bulletList, .numberedList, .checkbox, .toggleList:
            return .lists
        case .code, .quote, .divider, .callout, .table:
            return .blocks
        }
    }

    enum CommandCategory: String, CaseIterable {
        case text = "Text"
        case lists = "Lists"
        case blocks = "Blocks"
    }

    static func filtered(by query: String) -> [SlashCommand] {
        if query.isEmpty {
            return allCases
        }
        return allCases.filter {
            $0.title.localizedCaseInsensitiveContains(query) ||
            $0.rawValue.localizedCaseInsensitiveContains(query)
        }
    }
}

// MARK: - Workspace Editor

struct WorkspaceEditor: View {
    @Binding var content: String
    @State private var showSlashMenu = false
    @State private var slashMenuPosition: CGPoint = .zero
    @State private var slashQuery = ""
    @State private var selectedCommandIndex = 0
    @FocusState private var editorFocused: Bool

    var body: some View {
        ZStack(alignment: .topLeading) {
            // Main editor
            SlashCommandTextEditor(
                text: $content,
                onSlashTyped: { position in
                    slashMenuPosition = position
                    slashQuery = ""
                    selectedCommandIndex = 0
                    showSlashMenu = true
                },
                onSlashQueryChanged: { query in
                    slashQuery = query
                    selectedCommandIndex = 0
                },
                onSlashCancelled: {
                    showSlashMenu = false
                    slashQuery = ""
                },
                onSlashConfirmed: {
                    insertSelectedCommand()
                },
                onArrowUp: {
                    moveSelection(by: -1)
                },
                onArrowDown: {
                    moveSelection(by: 1)
                },
                showSlashMenu: showSlashMenu
            )
            .focused($editorFocused)
            .contextMenu {
                contextMenuContent
            }

            // Slash command menu
            if showSlashMenu {
                SlashCommandMenu(
                    query: slashQuery,
                    selectedIndex: selectedCommandIndex,
                    onSelect: { command in
                        insertCommand(command)
                    },
                    onDismiss: {
                        showSlashMenu = false
                        slashQuery = ""
                    }
                )
                .offset(x: 20, y: 60)
            }
        }
        .onAppear {
            editorFocused = true
        }
    }

    // MARK: - Context Menu

    @ViewBuilder
    private var contextMenuContent: some View {
        Group {
            Button {
                wrapSelection(with: "**", and: "**")
            } label: {
                Label("Bold", systemImage: "bold")
            }
            .keyboardShortcut("b", modifiers: .command)

            Button {
                wrapSelection(with: "_", and: "_")
            } label: {
                Label("Italic", systemImage: "italic")
            }
            .keyboardShortcut("i", modifiers: .command)

            Button {
                wrapSelection(with: "~~", and: "~~")
            } label: {
                Label("Strikethrough", systemImage: "strikethrough")
            }

            Button {
                wrapSelection(with: "`", and: "`")
            } label: {
                Label("Code", systemImage: "chevron.left.forwardslash.chevron.right")
            }
            .keyboardShortcut("e", modifiers: .command)
        }

        Divider()

        Group {
            Button {
                wrapSelection(with: "[", and: "](url)")
            } label: {
                Label("Link", systemImage: "link")
            }
            .keyboardShortcut("k", modifiers: .command)
        }

        Divider()

        Menu("Turn into") {
            ForEach(SlashCommand.allCases) { command in
                Button {
                    turnLineInto(command)
                } label: {
                    Label(command.title, systemImage: command.icon)
                }
            }
        }

        Divider()

        Group {
            Button {
                duplicateLine()
            } label: {
                Label("Duplicate", systemImage: "plus.square.on.square")
            }
            .keyboardShortcut("d", modifiers: [.command, .shift])

            Button {
                deleteLine()
            } label: {
                Label("Delete", systemImage: "trash")
            }
        }
    }

    // MARK: - Actions

    private var filteredCommands: [SlashCommand] {
        SlashCommand.filtered(by: slashQuery)
    }

    private func moveSelection(by delta: Int) {
        let commands = filteredCommands
        guard !commands.isEmpty else { return }

        selectedCommandIndex = (selectedCommandIndex + delta + commands.count) % commands.count
    }

    private func insertSelectedCommand() {
        let commands = filteredCommands
        guard selectedCommandIndex < commands.count else { return }
        insertCommand(commands[selectedCommandIndex])
    }

    private func insertCommand(_ command: SlashCommand) {
        // Remove the slash and query from content
        if let slashRange = findSlashRange() {
            content.removeSubrange(slashRange)
        }

        // Insert the command shortcut
        content += command.shortcut

        showSlashMenu = false
        slashQuery = ""
    }

    private func findSlashRange() -> Range<String.Index>? {
        // Find the last "/" and everything after it until cursor
        guard let lastSlash = content.lastIndex(of: "/") else { return nil }
        return lastSlash..<content.endIndex
    }

    private func wrapSelection(with prefix: String, and suffix: String) {
        // For now, just append at cursor position
        // In a real implementation, we'd wrap the selected text
        content += prefix + "text" + suffix
    }

    private func turnLineInto(_ command: SlashCommand) {
        // Simple implementation - prepend to current line
        let lines = content.components(separatedBy: "\n")
        guard !lines.isEmpty else { return }

        var newLines = lines
        if let lastIndex = newLines.indices.last {
            // Remove any existing prefix
            var line = newLines[lastIndex]
            line = line.trimmingCharacters(in: .whitespaces)

            // Remove common prefixes
            for prefix in ["# ", "## ", "### ", "- ", "1. ", "[ ] ", "[x] ", "> ", "```"] {
                if line.hasPrefix(prefix) {
                    line = String(line.dropFirst(prefix.count))
                    break
                }
            }

            newLines[lastIndex] = command.shortcut + line
        }
        content = newLines.joined(separator: "\n")
    }

    private func duplicateLine() {
        let lines = content.components(separatedBy: "\n")
        guard let last = lines.last else { return }
        content += "\n" + last
    }

    private func deleteLine() {
        var lines = content.components(separatedBy: "\n")
        if !lines.isEmpty {
            lines.removeLast()
        }
        content = lines.joined(separator: "\n")
    }
}

// MARK: - Slash Command Menu

struct SlashCommandMenu: View {
    let query: String
    let selectedIndex: Int
    let onSelect: (SlashCommand) -> Void
    let onDismiss: () -> Void

    private var filteredCommands: [SlashCommand] {
        SlashCommand.filtered(by: query)
    }

    private var groupedCommands: [(SlashCommand.CommandCategory, [SlashCommand])] {
        let commands = filteredCommands
        return SlashCommand.CommandCategory.allCases.compactMap { category in
            let categoryCommands = commands.filter { $0.category == category }
            return categoryCommands.isEmpty ? nil : (category, categoryCommands)
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header
            HStack {
                Image(systemName: "slash.circle")
                    .foregroundColor(.secondary)
                Text(query.isEmpty ? "Type to filter..." : query)
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)
                Spacer()
                Button {
                    onDismiss()
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 10))
                        .foregroundColor(.secondary)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)

            Divider()

            // Commands list
            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    if filteredCommands.isEmpty {
                        Text("No commands found")
                            .font(.system(size: 12))
                            .foregroundColor(.secondary)
                            .padding(12)
                    } else {
                        ForEach(groupedCommands, id: \.0) { category, commands in
                            // Category header
                            Text(category.rawValue.uppercased())
                                .font(.system(size: 10, weight: .semibold))
                                .foregroundColor(.secondary)
                                .padding(.horizontal, 12)
                                .padding(.top, 8)
                                .padding(.bottom, 4)

                            // Commands in category
                            ForEach(Array(commands.enumerated()), id: \.element.id) { _, command in
                                SlashCommandRow(
                                    command: command,
                                    isSelected: calculateIndex(for: command) == selectedIndex
                                ) {
                                    onSelect(command)
                                }
                            }
                        }
                    }
                }
                .padding(.vertical, 4)
            }
            .frame(maxHeight: 300)
        }
        .frame(width: 280)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(Color(nsColor: .windowBackgroundColor))
                .shadow(color: .black.opacity(0.2), radius: 10, y: 4)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .stroke(Color.gray.opacity(0.2), lineWidth: 1)
        )
    }

    private func calculateIndex(for command: SlashCommand) -> Int {
        filteredCommands.firstIndex(of: command) ?? 0
    }
}

// MARK: - Slash Command Row

struct SlashCommandRow: View {
    let command: SlashCommand
    let isSelected: Bool
    let onSelect: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: onSelect) {
            HStack(spacing: 10) {
                Image(systemName: command.icon)
                    .font(.system(size: 14))
                    .foregroundColor(isSelected ? .white : .secondary)
                    .frame(width: 24)

                VStack(alignment: .leading, spacing: 2) {
                    Text(command.title)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundColor(isSelected ? .white : .primary)

                    Text(command.description)
                        .font(.system(size: 10))
                        .foregroundColor(isSelected ? .white.opacity(0.8) : .secondary)
                }

                Spacer()
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .fill(isSelected ? Color.accentColor : (isHovered ? Color.gray.opacity(0.1) : Color.clear))
            )
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .padding(.horizontal, 4)
        .onHover { hovering in
            isHovered = hovering
        }
    }
}

// MARK: - Custom Text Editor with Slash Detection

struct SlashCommandTextEditor: NSViewRepresentable {
    @Binding var text: String
    var onSlashTyped: (CGPoint) -> Void
    var onSlashQueryChanged: (String) -> Void
    var onSlashCancelled: () -> Void
    var onSlashConfirmed: () -> Void
    var onArrowUp: () -> Void
    var onArrowDown: () -> Void
    var showSlashMenu: Bool

    func makeNSView(context: Context) -> NSScrollView {
        let scrollView = NSTextView.scrollableTextView()
        let textView = scrollView.documentView as! NSTextView

        textView.delegate = context.coordinator
        textView.font = NSFont.systemFont(ofSize: 14)
        textView.isRichText = false
        textView.allowsUndo = true
        textView.isAutomaticQuoteSubstitutionEnabled = false
        textView.isAutomaticDashSubstitutionEnabled = false
        textView.isAutomaticTextReplacementEnabled = false
        textView.backgroundColor = .clear
        textView.drawsBackground = false
        textView.textContainerInset = NSSize(width: 16, height: 16)

        context.coordinator.textView = textView

        return scrollView
    }

    func updateNSView(_ nsView: NSScrollView, context: Context) {
        let textView = nsView.documentView as! NSTextView

        if textView.string != text {
            let selectedRange = textView.selectedRange()
            textView.string = text
            textView.setSelectedRange(selectedRange)
        }

        context.coordinator.showSlashMenu = showSlashMenu
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    class Coordinator: NSObject, NSTextViewDelegate {
        var parent: SlashCommandTextEditor
        weak var textView: NSTextView?
        var slashPosition: Int?
        var showSlashMenu = false

        init(_ parent: SlashCommandTextEditor) {
            self.parent = parent
        }

        func textDidChange(_ notification: Notification) {
            guard let textView = textView else { return }
            parent.text = textView.string

            // Check for slash command trigger
            let cursorPosition = textView.selectedRange().location
            let text = textView.string

            if cursorPosition > 0 {
                let index = text.index(text.startIndex, offsetBy: cursorPosition - 1)
                let char = text[index]

                // Check if "/" was just typed at start of line or after whitespace
                if char == "/" {
                    let isAtStart = cursorPosition == 1
                    let isAfterWhitespace = cursorPosition >= 2 && {
                        let prevIndex = text.index(text.startIndex, offsetBy: cursorPosition - 2)
                        return text[prevIndex].isWhitespace || text[prevIndex].isNewline
                    }()

                    if isAtStart || isAfterWhitespace {
                        slashPosition = cursorPosition - 1
                        let rect = textView.firstRect(forCharacterRange: NSRange(location: cursorPosition - 1, length: 1), actualRange: nil)
                        parent.onSlashTyped(CGPoint(x: rect.origin.x, y: rect.origin.y))
                        return
                    }
                }
            }

            // Update slash query if menu is showing
            if let slashPos = slashPosition, showSlashMenu {
                if cursorPosition > slashPos {
                    let queryStart = text.index(text.startIndex, offsetBy: slashPos + 1)
                    let queryEnd = text.index(text.startIndex, offsetBy: cursorPosition)
                    let query = String(text[queryStart..<queryEnd])

                    // Cancel if query contains space or newline
                    if query.contains(" ") || query.contains("\n") {
                        slashPosition = nil
                        parent.onSlashCancelled()
                    } else {
                        parent.onSlashQueryChanged(query)
                    }
                } else {
                    slashPosition = nil
                    parent.onSlashCancelled()
                }
            }
        }

        func textView(_ textView: NSTextView, doCommandBy commandSelector: Selector) -> Bool {
            if showSlashMenu {
                if commandSelector == #selector(NSResponder.moveUp(_:)) {
                    parent.onArrowUp()
                    return true
                }
                if commandSelector == #selector(NSResponder.moveDown(_:)) {
                    parent.onArrowDown()
                    return true
                }
                if commandSelector == #selector(NSResponder.insertNewline(_:)) {
                    parent.onSlashConfirmed()
                    return true
                }
                if commandSelector == #selector(NSResponder.cancelOperation(_:)) {
                    slashPosition = nil
                    parent.onSlashCancelled()
                    return true
                }
            }
            return false
        }
    }
}

// MARK: - Preview

#Preview {
    WorkspaceEditor(content: .constant("# Welcome\n\nType / to see commands"))
        .frame(width: 600, height: 400)
}
