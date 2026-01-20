//
//  WorkspaceEditor.swift
//  MagnetarStudio (macOS)
//
//  Block-based rich text editor (Notion-style)
//  - Each line is a "block" with a type (heading, text, list, etc.)
//  - Visual rendering matches the block type automatically
//  - Slash commands create new blocks with proper styling
//  - No markdown syntax visible - just clean formatted text
//

import SwiftUI
import AppKit

// MARK: - Block Types

enum BlockType: String, CaseIterable, Identifiable, Codable {
    case text
    case heading1
    case heading2
    case heading3
    case bulletList
    case numberedList
    case checkbox
    case code
    case quote
    case divider
    case callout

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .text: return "text.alignleft"
        case .heading1: return "textformat.size.larger"
        case .heading2: return "textformat.size"
        case .heading3: return "textformat.size.smaller"
        case .bulletList: return "list.bullet"
        case .numberedList: return "list.number"
        case .checkbox: return "checkmark.square"
        case .code: return "chevron.left.forwardslash.chevron.right"
        case .quote: return "text.quote"
        case .divider: return "minus"
        case .callout: return "exclamationmark.bubble"
        }
    }

    var title: String {
        switch self {
        case .text: return "Text"
        case .heading1: return "Heading 1"
        case .heading2: return "Heading 2"
        case .heading3: return "Heading 3"
        case .bulletList: return "Bullet List"
        case .numberedList: return "Numbered List"
        case .checkbox: return "Checkbox"
        case .code: return "Code"
        case .quote: return "Quote"
        case .divider: return "Divider"
        case .callout: return "Callout"
        }
    }

    var description: String {
        switch self {
        case .text: return "Plain text paragraph"
        case .heading1: return "Large section heading"
        case .heading2: return "Medium section heading"
        case .heading3: return "Small section heading"
        case .bulletList: return "Simple bullet point"
        case .numberedList: return "Numbered list item"
        case .checkbox: return "Task with checkbox"
        case .code: return "Code snippet"
        case .quote: return "Quote or excerpt"
        case .divider: return "Visual separator"
        case .callout: return "Highlighted info box"
        }
    }

    var placeholder: String {
        switch self {
        case .text: return "Type something..."
        case .heading1: return "Heading 1"
        case .heading2: return "Heading 2"
        case .heading3: return "Heading 3"
        case .bulletList: return "List item"
        case .numberedList: return "List item"
        case .checkbox: return "To-do"
        case .code: return "Code"
        case .quote: return "Quote"
        case .divider: return ""
        case .callout: return "Callout"
        }
    }
}

// MARK: - Document Block

struct DocumentBlock: Identifiable, Equatable, Codable {
    let id: UUID
    var type: BlockType
    var content: String
    var isChecked: Bool  // For checkbox type

    init(id: UUID = UUID(), type: BlockType = .text, content: String = "", isChecked: Bool = false) {
        self.id = id
        self.type = type
        self.content = content
        self.isChecked = isChecked
    }
}

// MARK: - Workspace Editor

struct WorkspaceEditor: View {
    @Binding var content: String
    @State private var blocks: [DocumentBlock] = []
    @State private var focusedBlockId: UUID?
    @State private var showSlashMenu = false
    @State private var slashMenuBlockId: UUID?
    @State private var slashQuery = ""
    @State private var selectedCommandIndex = 0

    var body: some View {
        ScrollView {
            LazyVStack(alignment: .leading, spacing: 2) {
                ForEach(blocks.indices, id: \.self) { index in
                    let blockId = blocks[index].id
                    BlockView(
                        block: $blocks[index],
                        index: index,
                        isFocused: focusedBlockId == blockId,
                        onFocus: { focusedBlockId = blockId },
                        onSlashTyped: {
                            slashMenuBlockId = blockId
                            slashQuery = ""
                            selectedCommandIndex = 0
                            showSlashMenu = true
                        },
                        onEnter: { insertBlockAfter(blockId) },
                        onDelete: { deleteBlockIfEmpty(blockId) },
                        onArrowUp: { focusPreviousBlock(from: blockId) },
                        onArrowDown: { focusNextBlock(from: blockId) }
                    )
                    .id(blockId)
                }
            }
            .padding(16)
        }
        .overlay(alignment: .topLeading) {
            if showSlashMenu {
                SlashCommandMenu(
                    query: slashQuery,
                    selectedIndex: selectedCommandIndex,
                    onSelect: { blockType in
                        convertBlock(slashMenuBlockId, to: blockType)
                        showSlashMenu = false
                    },
                    onDismiss: {
                        showSlashMenu = false
                    },
                    onQueryChanged: { query in
                        slashQuery = query
                        selectedCommandIndex = 0
                    },
                    onArrowUp: {
                        let count = filteredBlockTypes.count
                        if count > 0 {
                            selectedCommandIndex = (selectedCommandIndex - 1 + count) % count
                        }
                    },
                    onArrowDown: {
                        let count = filteredBlockTypes.count
                        if count > 0 {
                            selectedCommandIndex = (selectedCommandIndex + 1) % count
                        }
                    },
                    onConfirm: {
                        if selectedCommandIndex < filteredBlockTypes.count {
                            convertBlock(slashMenuBlockId, to: filteredBlockTypes[selectedCommandIndex])
                        }
                        showSlashMenu = false
                    }
                )
                .padding(.leading, 40)
                .padding(.top, 60)
            }
        }
        .onAppear {
            loadFromContent()
        }
        .onChange(of: blocks) { _, _ in
            saveToContent()
        }
    }

    private var filteredBlockTypes: [BlockType] {
        if slashQuery.isEmpty {
            return BlockType.allCases
        }
        return BlockType.allCases.filter {
            $0.title.localizedCaseInsensitiveContains(slashQuery) ||
            $0.rawValue.localizedCaseInsensitiveContains(slashQuery)
        }
    }

    // MARK: - Block Operations

    private func insertBlockAfter(_ id: UUID) {
        guard let index = blocks.firstIndex(where: { $0.id == id }) else { return }
        let newBlock = DocumentBlock()
        blocks.insert(newBlock, at: index + 1)
        focusedBlockId = newBlock.id
    }

    private func deleteBlockIfEmpty(_ id: UUID) {
        guard let index = blocks.firstIndex(where: { $0.id == id }),
              blocks[index].content.isEmpty,
              blocks.count > 1 else { return }

        let previousIndex = max(0, index - 1)
        blocks.remove(at: index)
        focusedBlockId = blocks[previousIndex].id
    }

    private func convertBlock(_ id: UUID?, to type: BlockType) {
        guard let id = id,
              let index = blocks.firstIndex(where: { $0.id == id }) else { return }

        // Clear the "/" if it was typed
        if blocks[index].content == "/" {
            blocks[index].content = ""
        }
        blocks[index].type = type
    }

    private func focusPreviousBlock(from id: UUID) {
        guard let index = blocks.firstIndex(where: { $0.id == id }),
              index > 0 else { return }
        focusedBlockId = blocks[index - 1].id
    }

    private func focusNextBlock(from id: UUID) {
        guard let index = blocks.firstIndex(where: { $0.id == id }),
              index < blocks.count - 1 else { return }
        focusedBlockId = blocks[index + 1].id
    }

    // MARK: - Serialization

    private func loadFromContent() {
        // Parse content into blocks (simple: one block per line for now)
        let lines = content.components(separatedBy: "\n")
        if lines.isEmpty || (lines.count == 1 && lines[0].isEmpty) {
            blocks = [DocumentBlock(type: .text, content: "")]
        } else {
            blocks = lines.map { DocumentBlock(type: .text, content: $0) }
        }
        focusedBlockId = blocks.first?.id
    }

    private func saveToContent() {
        content = blocks.map { $0.content }.joined(separator: "\n")
    }
}

// MARK: - Block View

struct BlockView: View {
    @Binding var block: DocumentBlock
    let index: Int
    let isFocused: Bool
    let onFocus: () -> Void
    let onSlashTyped: () -> Void
    let onEnter: () -> Void
    let onDelete: () -> Void
    let onArrowUp: () -> Void
    let onArrowDown: () -> Void

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            // Block prefix/indicator
            blockPrefix

            // Content
            blockContent
        }
        .padding(.vertical, verticalPadding)
        .contentShape(Rectangle())
        .onTapGesture { onFocus() }
        .contextMenu { contextMenuContent }
    }

    private var verticalPadding: CGFloat {
        switch block.type {
        case .heading1: return 12
        case .heading2: return 8
        case .heading3: return 6
        case .divider: return 8
        default: return 2
        }
    }

    // MARK: - Block Prefix

    @ViewBuilder
    private var blockPrefix: some View {
        switch block.type {
        case .bulletList:
            Circle()
                .fill(Color.primary.opacity(0.6))
                .frame(width: 6, height: 6)
                .padding(.top, 7)
                .frame(width: 20)

        case .numberedList:
            Text("\(index + 1).")
                .font(.system(size: 14))
                .foregroundColor(.secondary)
                .frame(width: 20, alignment: .trailing)

        case .checkbox:
            Button {
                block.isChecked.toggle()
            } label: {
                Image(systemName: block.isChecked ? "checkmark.square.fill" : "square")
                    .font(.system(size: 16))
                    .foregroundColor(block.isChecked ? .accentColor : .secondary)
            }
            .buttonStyle(.plain)
            .frame(width: 20)

        case .quote:
            Rectangle()
                .fill(Color.accentColor.opacity(0.6))
                .frame(width: 3)
                .padding(.vertical, 2)

        case .callout:
            Text("💡")
                .font(.system(size: 14))
                .frame(width: 20)

        default:
            Color.clear.frame(width: 20)
        }
    }

    // MARK: - Block Content

    @ViewBuilder
    private var blockContent: some View {
        switch block.type {
        case .divider:
            Divider()
                .padding(.vertical, 8)

        case .code:
            BlockTextField(
                text: $block.content,
                placeholder: block.type.placeholder,
                font: .monospacedSystemFont(ofSize: 13, weight: .regular),
                isFocused: isFocused,
                onFocus: onFocus,
                onSlashTyped: onSlashTyped,
                onEnter: onEnter,
                onDelete: onDelete,
                onArrowUp: onArrowUp,
                onArrowDown: onArrowDown
            )
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .fill(Color.gray.opacity(0.1))
            )

        case .callout:
            BlockTextField(
                text: $block.content,
                placeholder: block.type.placeholder,
                font: .systemFont(ofSize: 14),
                isFocused: isFocused,
                onFocus: onFocus,
                onSlashTyped: onSlashTyped,
                onEnter: onEnter,
                onDelete: onDelete,
                onArrowUp: onArrowUp,
                onArrowDown: onArrowDown
            )
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .fill(Color.yellow.opacity(0.1))
            )

        default:
            BlockTextField(
                text: $block.content,
                placeholder: block.type.placeholder,
                font: fontForType(block.type),
                textColor: textColorForType(block.type),
                isFocused: isFocused,
                onFocus: onFocus,
                onSlashTyped: onSlashTyped,
                onEnter: onEnter,
                onDelete: onDelete,
                onArrowUp: onArrowUp,
                onArrowDown: onArrowDown
            )
        }
    }

    private func fontForType(_ type: BlockType) -> NSFont {
        switch type {
        case .heading1:
            return .systemFont(ofSize: 28, weight: .bold)
        case .heading2:
            return .systemFont(ofSize: 22, weight: .semibold)
        case .heading3:
            return .systemFont(ofSize: 18, weight: .semibold)
        case .quote:
            return .systemFont(ofSize: 14, weight: .regular).withTraits(.italic)
        default:
            return .systemFont(ofSize: 14)
        }
    }

    private func textColorForType(_ type: BlockType) -> NSColor {
        switch type {
        case .quote:
            return .secondaryLabelColor
        default:
            return .labelColor
        }
    }

    // MARK: - Context Menu

    @ViewBuilder
    private var contextMenuContent: some View {
        Menu("Turn into") {
            ForEach(BlockType.allCases) { type in
                Button {
                    block.type = type
                } label: {
                    Label(type.title, systemImage: type.icon)
                }
            }
        }

        Divider()

        Button {
            // Duplicate would need parent access
        } label: {
            Label("Duplicate", systemImage: "plus.square.on.square")
        }

        Button(role: .destructive) {
            onDelete()
        } label: {
            Label("Delete", systemImage: "trash")
        }
    }
}

// MARK: - Block Text View (NSViewRepresentable with native undo support)
//
// Key insight: Notion uses Electron/web tech. For native macOS, we must let
// NSTextView manage its own undo stack without SwiftUI interference.
// Based on: https://github.com/shufflingB/swiftui-macos-undoable-texteditor
//

struct BlockTextField: View {
    @Binding var text: String
    let placeholder: String
    let font: NSFont
    var textColor: NSColor = .labelColor
    let isFocused: Bool
    let onFocus: () -> Void
    let onSlashTyped: () -> Void
    let onEnter: () -> Void
    let onDelete: () -> Void
    let onArrowUp: () -> Void
    let onArrowDown: () -> Void

    @State private var textHeight: CGFloat = 24

    var body: some View {
        BlockTextFieldRepresentable(
            text: $text,
            placeholder: placeholder,
            font: font,
            textColor: textColor,
            isFocused: isFocused,
            textHeight: $textHeight,
            onFocus: onFocus,
            onSlashTyped: onSlashTyped,
            onEnter: onEnter,
            onDelete: onDelete,
            onArrowUp: onArrowUp,
            onArrowDown: onArrowDown
        )
        .frame(height: max(textHeight, font.pointSize + 10))
    }
}

struct BlockTextFieldRepresentable: NSViewRepresentable {
    @Binding var text: String
    let placeholder: String
    let font: NSFont
    var textColor: NSColor = .labelColor
    let isFocused: Bool
    @Binding var textHeight: CGFloat
    let onFocus: () -> Void
    let onSlashTyped: () -> Void
    let onEnter: () -> Void
    let onDelete: () -> Void
    let onArrowUp: () -> Void
    let onArrowDown: () -> Void

    func makeNSView(context: Context) -> NSView {
        let containerView = NSView()

        let textView = UndoableTextView()
        textView.isRichText = false
        textView.font = font
        textView.textColor = textColor
        textView.backgroundColor = .clear
        textView.drawsBackground = false
        textView.isVerticallyResizable = false
        textView.isHorizontallyResizable = false
        textView.textContainer?.containerSize = NSSize(width: 0, height: CGFloat.greatestFiniteMagnitude)
        textView.textContainer?.widthTracksTextView = true
        textView.textContainer?.lineFragmentPadding = 0
        textView.allowsUndo = true
        textView.delegate = context.coordinator
        textView.placeholderString = placeholder
        textView.translatesAutoresizingMaskIntoConstraints = false

        containerView.addSubview(textView)

        NSLayoutConstraint.activate([
            textView.leadingAnchor.constraint(equalTo: containerView.leadingAnchor),
            textView.trailingAnchor.constraint(equalTo: containerView.trailingAnchor),
            textView.topAnchor.constraint(equalTo: containerView.topAnchor),
            textView.bottomAnchor.constraint(equalTo: containerView.bottomAnchor)
        ])

        context.coordinator.textView = textView
        context.coordinator.containerView = containerView

        // Set text AFTER coordinator is connected
        textView.string = text
        context.coordinator.lastSyncedText = text
        context.coordinator.previousText = text

        return containerView
    }

    func updateNSView(_ nsView: NSView, context: Context) {
        guard let textView = context.coordinator.textView else { return }

        // Always update appearance first
        textView.font = font
        textView.textColor = textColor
        textView.placeholderString = placeholder

        // Sync text: update if binding changed externally AND we're not actively editing
        let bindingText = text
        let viewText = textView.string
        let notEditing = !context.coordinator.isEditing

        if notEditing && bindingText != viewText {
            // Text changed externally (switching notes, initial load, etc.)
            textView.string = bindingText
            textView.undoManager?.removeAllActions()
            context.coordinator.lastSyncedText = bindingText
            context.coordinator.previousText = bindingText
            textView.needsDisplay = true
        }

        // Focus handling
        if isFocused && nsView.window?.firstResponder != textView {
            DispatchQueue.main.async {
                nsView.window?.makeFirstResponder(textView)
            }
        }

        // Update height
        context.coordinator.updateHeight()
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    class Coordinator: NSObject, NSTextViewDelegate {
        var parent: BlockTextFieldRepresentable
        weak var textView: UndoableTextView?
        weak var containerView: NSView?
        var isEditing = false
        var previousText = ""
        var lastSyncedText = ""  // Track what SwiftUI binding last knew about

        init(_ parent: BlockTextFieldRepresentable) {
            self.parent = parent
            self.previousText = parent.text
            self.lastSyncedText = parent.text
        }

        func updateHeight() {
            guard let textView = textView else { return }

            let layoutManager = textView.layoutManager!
            let textContainer = textView.textContainer!

            layoutManager.ensureLayout(for: textContainer)
            let usedRect = layoutManager.usedRect(for: textContainer)
            let newHeight = max(usedRect.height + 4, parent.font.pointSize + 10)

            if abs(parent.textHeight - newHeight) > 1 {
                parent.textHeight = newHeight
            }
        }

        func textDidBeginEditing(_ notification: Notification) {
            isEditing = true
            parent.onFocus()
        }

        func textDidEndEditing(_ notification: Notification) {
            isEditing = false
            syncTextToBinding()
        }

        func textDidChange(_ notification: Notification) {
            guard let textView = notification.object as? NSTextView else { return }
            let newText = textView.string

            // Detect "/" typed at start of empty block
            if newText == "/" && previousText.isEmpty {
                parent.onSlashTyped()
            }

            previousText = newText
            updateHeight()

            // NO binding update here - NSTextView manages its own undo stack
            // Undo/redo will work natively with Cmd+Z / Cmd+Shift+Z
        }

        func textView(_ textView: NSTextView, doCommandBy commandSelector: Selector) -> Bool {
            if commandSelector == #selector(NSResponder.insertNewline(_:)) {
                syncTextToBinding()
                parent.onEnter()
                return true
            }

            if commandSelector == #selector(NSResponder.deleteBackward(_:)) {
                if textView.string.isEmpty {
                    parent.onDelete()
                    return true
                }
            }

            if commandSelector == #selector(NSResponder.moveUp(_:)) {
                if isAtFirstLine(textView) {
                    syncTextToBinding()
                    parent.onArrowUp()
                    return true
                }
            }

            if commandSelector == #selector(NSResponder.moveDown(_:)) {
                if isAtLastLine(textView) {
                    syncTextToBinding()
                    parent.onArrowDown()
                    return true
                }
            }

            return false
        }

        func syncTextToBinding() {
            guard let textView = textView else { return }
            let currentText = textView.string
            parent.text = currentText
            lastSyncedText = currentText
        }

        private func isAtFirstLine(_ textView: NSTextView) -> Bool {
            guard let layoutManager = textView.layoutManager,
                  textView.textContainer != nil else { return true }
            let cursorPosition = textView.selectedRange().location
            if layoutManager.numberOfGlyphs == 0 { return true }
            var glyphRange = NSRange()
            layoutManager.lineFragmentRect(forGlyphAt: min(cursorPosition, layoutManager.numberOfGlyphs - 1), effectiveRange: &glyphRange)
            return glyphRange.location == 0
        }

        private func isAtLastLine(_ textView: NSTextView) -> Bool {
            guard let layoutManager = textView.layoutManager,
                  textView.textContainer != nil else { return true }
            let cursorPosition = textView.selectedRange().location
            let totalGlyphs = layoutManager.numberOfGlyphs
            if totalGlyphs == 0 { return true }
            var glyphRange = NSRange()
            layoutManager.lineFragmentRect(forGlyphAt: min(cursorPosition, totalGlyphs - 1), effectiveRange: &glyphRange)
            return NSMaxRange(glyphRange) >= totalGlyphs
        }
    }
}

// MARK: - Custom NSTextView with Undo Support and Placeholder

class UndoableTextView: NSTextView {
    var placeholderString: String = ""
    var onFocus: (() -> Void)?
    var onSlashTyped: (() -> Void)?
    var onEnter: (() -> Void)?
    var onDelete: (() -> Void)?
    var onArrowUp: (() -> Void)?
    var onArrowDown: (() -> Void)?

    override var string: String {
        didSet {
            needsDisplay = true
        }
    }

    override func draw(_ dirtyRect: NSRect) {
        super.draw(dirtyRect)

        // Draw placeholder if empty
        if string.isEmpty && !placeholderString.isEmpty {
            let attributes: [NSAttributedString.Key: Any] = [
                .foregroundColor: NSColor.placeholderTextColor,
                .font: font ?? NSFont.systemFont(ofSize: 14)
            ]
            let rect = NSRect(x: textContainerInset.width + (textContainer?.lineFragmentPadding ?? 0),
                              y: textContainerInset.height,
                              width: bounds.width,
                              height: bounds.height)
            placeholderString.draw(in: rect, withAttributes: attributes)
        }
    }

    override func becomeFirstResponder() -> Bool {
        let result = super.becomeFirstResponder()
        if result {
            needsDisplay = true
        }
        return result
    }

    override func resignFirstResponder() -> Bool {
        let result = super.resignFirstResponder()
        needsDisplay = true
        return result
    }
}

// MARK: - Slash Command Menu

struct SlashCommandMenu: View {
    let query: String
    let selectedIndex: Int
    let onSelect: (BlockType) -> Void
    let onDismiss: () -> Void
    let onQueryChanged: (String) -> Void
    let onArrowUp: () -> Void
    let onArrowDown: () -> Void
    let onConfirm: () -> Void

    private var filteredTypes: [BlockType] {
        if query.isEmpty {
            return BlockType.allCases
        }
        return BlockType.allCases.filter {
            $0.title.localizedCaseInsensitiveContains(query) ||
            $0.rawValue.localizedCaseInsensitiveContains(query)
        }
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header with filter
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
                    if filteredTypes.isEmpty {
                        Text("No commands found")
                            .font(.system(size: 12))
                            .foregroundColor(.secondary)
                            .padding(12)
                    } else {
                        ForEach(Array(filteredTypes.enumerated()), id: \.element.id) { index, type in
                            SlashCommandRow(
                                type: type,
                                isSelected: index == selectedIndex
                            ) {
                                onSelect(type)
                            }
                        }
                    }
                }
                .padding(.vertical, 4)
            }
            .frame(maxHeight: 300)
        }
        .frame(width: 260)
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
}

// MARK: - Slash Command Row

struct SlashCommandRow: View {
    let type: BlockType
    let isSelected: Bool
    let onSelect: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: onSelect) {
            HStack(spacing: 10) {
                Image(systemName: type.icon)
                    .font(.system(size: 14))
                    .foregroundColor(isSelected ? .white : .secondary)
                    .frame(width: 24)

                VStack(alignment: .leading, spacing: 2) {
                    Text(type.title)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundColor(isSelected ? .white : .primary)

                    Text(type.description)
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

// MARK: - NSFont Extension

extension NSFont {
    func withTraits(_ traits: NSFontDescriptor.SymbolicTraits) -> NSFont {
        let descriptor = fontDescriptor.withSymbolicTraits(traits)
        return NSFont(descriptor: descriptor, size: pointSize) ?? self
    }
}

// MARK: - Preview

#Preview {
    WorkspaceEditor(content: .constant("Welcome to the editor\n\nType / to see commands"))
        .frame(width: 600, height: 400)
}
