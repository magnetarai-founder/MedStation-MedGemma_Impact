//
//  CodeTextView.swift
//  MagnetarStudio (macOS)
//
//  NSViewRepresentable wrapping NSScrollView + NSTextView for the code editor.
//  Provides syntax highlighting, integrated line number gutter (NSRulerView),
//  line-level cursor positioning, scroll-to-line, and live cursor tracking.
//

import SwiftUI
import AppKit

struct CodeTextView: NSViewRepresentable {
    @Binding var text: String
    let fontSize: CGFloat
    var language: CodeLanguage = .unknown
    var showLineNumbers: Bool = true
    var targetLine: Int?
    let onCursorMove: (Int, Int) -> Void  // (line, column)
    var onCoordinatorReady: ((Coordinator) -> Void)?
    var onExplainSelection: ((String) -> Void)?       // D1: selected code
    var onAIRename: ((String, String) -> Void)?        // D2: (word, context)

    func makeNSView(context: Context) -> NSScrollView {
        let scrollView = NSScrollView()
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = true
        scrollView.autohidesScrollers = true
        scrollView.borderType = .noBorder

        let textView = CodeNSTextView()
        textView.isRichText = false
        textView.allowsUndo = true
        textView.isEditable = true
        textView.isSelectable = true
        textView.font = NSFont.monospacedSystemFont(ofSize: fontSize, weight: .regular)
        textView.textColor = NSColor.labelColor
        textView.backgroundColor = NSColor.textBackgroundColor
        textView.drawsBackground = true
        textView.isVerticallyResizable = true
        textView.isHorizontallyResizable = true
        textView.autoresizingMask = [.width]
        textView.textContainer?.containerSize = NSSize(
            width: scrollView.contentSize.width,
            height: CGFloat.greatestFiniteMagnitude
        )
        textView.textContainer?.widthTracksTextView = true
        textView.textContainer?.lineFragmentPadding = 8
        textView.delegate = context.coordinator

        // Set initial text
        textView.string = text
        textView.coordinator = context.coordinator
        context.coordinator.textView = textView
        context.coordinator.lastSyncedText = text
        context.coordinator.inlineCompletion.textView = textView
        context.coordinator.inlineCompletion.language = language.rawValue

        scrollView.documentView = textView

        // Set up line number ruler
        let rulerView = LineNumberRulerView(textView: textView)
        rulerView.coordinator = context.coordinator
        scrollView.verticalRulerView = rulerView
        scrollView.hasVerticalRuler = true
        scrollView.rulersVisible = showLineNumbers

        context.coordinator.rulerView = rulerView

        // Expose coordinator to parent SwiftUI views
        DispatchQueue.main.async {
            self.onCoordinatorReady?(context.coordinator)
        }

        // Apply initial syntax highlighting
        context.coordinator.applySyntaxHighlighting()

        // Observe text layout changes to update ruler
        NotificationCenter.default.addObserver(
            context.coordinator,
            selector: #selector(Coordinator.handleTextStorageEdit(_:)),
            name: NSTextStorage.didProcessEditingNotification,
            object: textView.textStorage
        )

        return scrollView
    }

    func updateNSView(_ scrollView: NSScrollView, context: Context) {
        guard let textView = context.coordinator.textView else { return }

        // Update font if changed
        let newFont = NSFont.monospacedSystemFont(ofSize: fontSize, weight: .regular)
        if textView.font != newFont {
            textView.font = newFont
            context.coordinator.rulerView?.ruleThickness = max(36, fontSize * 3.2)
            context.coordinator.rulerView?.needsDisplay = true
        }

        // Update language if changed
        if context.coordinator.currentLanguage != language {
            context.coordinator.currentLanguage = language
            context.coordinator.applySyntaxHighlighting()
        }

        // Toggle line numbers
        scrollView.rulersVisible = showLineNumbers

        // Sync text from binding (only when not actively editing)
        if !context.coordinator.isEditing && text != textView.string {
            textView.string = text
            context.coordinator.lastSyncedText = text
            context.coordinator.applySyntaxHighlighting()
        }

        // Scroll to target line if set
        if let line = targetLine, line != context.coordinator.lastTargetLine {
            context.coordinator.lastTargetLine = line
            context.coordinator.scrollToLine(line)
        }
    }

    func makeCoordinator() -> Coordinator {
        Coordinator(self)
    }

    // MARK: - Coordinator

    class Coordinator: NSObject, NSTextViewDelegate {
        var parent: CodeTextView
        weak var textView: NSTextView?
        weak var rulerView: LineNumberRulerView?
        var isEditing = false
        var lastSyncedText = ""
        var lastTargetLine: Int?
        var currentLanguage: CodeLanguage = .unknown
        private var highlightTask: Task<Void, Never>?

        // A2: Bracket matching
        private var previousBracketRanges: [NSRange] = []

        // A5: Breakpoints
        var breakpoints: Set<Int> = []

        // A3: Code folding
        var foldedRegions: [Int: (range: NSRange, original: String)] = [:]

        // D3: Inline completion
        let inlineCompletion = InlineCompletionManager()

        // D1/D2: AI popover state
        var showExplainPopover = false
        var showRenameSheet = false
        var selectedCodeForAI = ""
        var selectedWordForRename = ""

        init(_ parent: CodeTextView) {
            self.parent = parent
            self.currentLanguage = parent.language
        }

        // MARK: - Text Change

        func textDidBeginEditing(_ notification: Notification) {
            isEditing = true
        }

        func textDidEndEditing(_ notification: Notification) {
            isEditing = false
        }

        func textDidChange(_ notification: Notification) {
            guard let textView = textView else { return }
            let newText = textView.string
            if newText != parent.text {
                parent.text = newText
                lastSyncedText = newText
            }
            // D3: Notify inline completion
            inlineCompletion.onTextChange()
            // Debounced re-highlight (300ms)
            scheduleHighlight()
        }

        @objc func handleTextStorageEdit(_ notification: Notification) {
            rulerView?.needsDisplay = true
        }

        // MARK: - A1: Tab Indent & Auto-Indent

        func textView(_ textView: NSTextView, shouldChangeTextIn affectedCharRange: NSRange, replacementString: String?) -> Bool {
            guard let replacement = replacementString else { return true }
            let nsText = textView.string as NSString

            // Tab key — indent
            if replacement == "\t" {
                let selectedRange = textView.selectedRange()
                let lineRange = nsText.lineRange(for: selectedRange)
                let selectedText = nsText.substring(with: lineRange)
                let lines = selectedText.components(separatedBy: "\n")

                // Multi-line selection: indent all lines
                if lines.count > 1 || selectedRange.length > 0 {
                    let indented = lines.map { $0.isEmpty ? $0 : "    " + $0 }.joined(separator: "\n")
                    textView.insertText(indented, replacementRange: lineRange)
                    return false
                }

                // Single cursor: insert 4 spaces
                textView.insertText("    ", replacementRange: affectedCharRange)
                return false
            }

            // Enter key — auto-indent
            if replacement == "\n" {
                let cursorPos = affectedCharRange.location
                let lineStart = nsText.lineRange(for: NSRange(location: cursorPos, length: 0)).location
                let currentLine = nsText.substring(with: NSRange(location: lineStart, length: cursorPos - lineStart))

                // Copy leading whitespace
                var indent = ""
                for ch in currentLine {
                    if ch == " " || ch == "\t" { indent.append(ch) }
                    else { break }
                }

                // Extra indent after {
                let trimmed = currentLine.trimmingCharacters(in: .whitespaces)
                if trimmed.hasSuffix("{") {
                    indent += "    "
                }

                textView.insertText("\n" + indent, replacementRange: affectedCharRange)
                return false
            }

            return true
        }

        /// Shift+Tab dedent — called from key event handler
        func dedentSelectedLines() {
            guard let textView = textView else { return }
            let nsText = textView.string as NSString
            let selectedRange = textView.selectedRange()
            let lineRange = nsText.lineRange(for: selectedRange)
            let selectedText = nsText.substring(with: lineRange)
            let lines = selectedText.components(separatedBy: "\n")

            let dedented = lines.map { line -> String in
                if line.hasPrefix("    ") { return String(line.dropFirst(4)) }
                if line.hasPrefix("\t") { return String(line.dropFirst(1)) }
                // Remove up to 4 leading spaces
                var removed = 0
                var result = line
                while removed < 4 && result.hasPrefix(" ") {
                    result = String(result.dropFirst(1))
                    removed += 1
                }
                return result
            }.joined(separator: "\n")

            textView.insertText(dedented, replacementRange: lineRange)
        }

        // MARK: - Syntax Highlighting

        func applySyntaxHighlighting() {
            guard let textView = textView,
                  currentLanguage != .unknown else { return }

            let highlighter = SyntaxHighlighter(language: currentLanguage)
            let font = textView.font ?? NSFont.monospacedSystemFont(ofSize: 14, weight: .regular)
            let text = textView.string

            // Save cursor position
            let selectedRange = textView.selectedRange()

            let attributed = highlighter.highlight(text, font: font)
            textView.textStorage?.beginEditing()
            textView.textStorage?.setAttributedString(attributed)
            textView.textStorage?.endEditing()

            // Restore cursor position
            let safeRange = NSRange(
                location: min(selectedRange.location, (text as NSString).length),
                length: min(selectedRange.length, max(0, (text as NSString).length - selectedRange.location))
            )
            textView.setSelectedRange(safeRange)
        }

        private func scheduleHighlight() {
            highlightTask?.cancel()
            highlightTask = Task { @MainActor [weak self] in
                try? await Task.sleep(for: .milliseconds(300))
                guard !Task.isCancelled else { return }
                self?.applySyntaxHighlighting()
            }
        }

        // MARK: - A2: Bracket Matching

        private func highlightMatchingBrackets() {
            guard let textView = textView,
                  let layoutManager = textView.layoutManager else { return }

            let fullRange = NSRange(location: 0, length: (textView.string as NSString).length)

            // Clear previous bracket highlights
            for range in previousBracketRanges {
                if range.location + range.length <= fullRange.length {
                    layoutManager.removeTemporaryAttribute(.backgroundColor, forCharacterRange: range)
                }
            }
            previousBracketRanges = []

            let nsText = textView.string as NSString
            guard nsText.length > 0 else { return }

            let cursorPos = textView.selectedRange().location
            guard cursorPos <= nsText.length else { return }

            // Check character at cursor and before cursor
            let bracketPairs: [(Character, Character)] = [("(", ")"), ("[", "]"), ("{", "}")]
            let openBrackets = Set(bracketPairs.map(\.0))
            let closeBrackets = Set(bracketPairs.map(\.1))

            for offset in [0, -1] {
                let pos = cursorPos + offset
                guard pos >= 0, pos < nsText.length else { continue }
                guard let scalar = UnicodeScalar(nsText.character(at: pos)) else { continue }
                let char = Character(scalar)

                if openBrackets.contains(char) {
                    // Find matching close bracket forward
                    guard let pair = bracketPairs.first(where: { $0.0 == char }) else { continue }
                    if let matchPos = findMatchingBracket(in: nsText, from: pos, open: pair.0, close: pair.1, forward: true) {
                        applyBracketHighlight(at: pos, and: matchPos, layoutManager: layoutManager)
                    }
                    return
                } else if closeBrackets.contains(char) {
                    // Find matching open bracket backward
                    guard let pair = bracketPairs.first(where: { $0.1 == char }) else { continue }
                    if let matchPos = findMatchingBracket(in: nsText, from: pos, open: pair.0, close: pair.1, forward: false) {
                        applyBracketHighlight(at: pos, and: matchPos, layoutManager: layoutManager)
                    }
                    return
                }
            }
        }

        private func findMatchingBracket(in text: NSString, from pos: Int, open: Character, close: Character, forward: Bool) -> Int? {
            var depth = 0
            guard let openVal = open.asciiValue, let closeVal = close.asciiValue else { return nil }
            let step = forward ? 1 : -1
            var i = pos

            while i >= 0 && i < text.length {
                let ch = text.character(at: i)
                if ch == UInt16(openVal) { depth += 1 }
                else if ch == UInt16(closeVal) { depth -= 1 }

                if depth == 0 { return i }
                i += step
            }
            return nil
        }

        private func applyBracketHighlight(at pos1: Int, and pos2: Int, layoutManager: NSLayoutManager) {
            let highlightColor = NSColor.systemYellow.withAlphaComponent(0.3)
            let range1 = NSRange(location: pos1, length: 1)
            let range2 = NSRange(location: pos2, length: 1)

            layoutManager.addTemporaryAttribute(.backgroundColor, value: highlightColor, forCharacterRange: range1)
            layoutManager.addTemporaryAttribute(.backgroundColor, value: highlightColor, forCharacterRange: range2)
            previousBracketRanges = [range1, range2]
        }

        // MARK: - A4: Find & Replace Support

        private var findHighlightRanges: [NSRange] = []

        func highlightFindMatches(query: String, caseSensitive: Bool, useRegex: Bool) -> Int {
            clearFindHighlights()
            guard let textView = textView,
                  let layoutManager = textView.layoutManager,
                  !query.isEmpty else { return 0 }

            let text = textView.string
            let nsText = text as NSString
            guard nsText.length > 0 else { return 0 }

            let ranges: [NSRange]
            if useRegex {
                let options: NSRegularExpression.Options = caseSensitive ? [] : [.caseInsensitive]
                guard let regex = try? NSRegularExpression(pattern: query, options: options) else { return 0 }
                let fullRange = NSRange(location: 0, length: nsText.length)
                ranges = regex.matches(in: text, range: fullRange).map(\.range)
            } else {
                var opts: NSString.CompareOptions = []
                if !caseSensitive { opts.insert(.caseInsensitive) }
                var searchRange = NSRange(location: 0, length: nsText.length)
                var found: [NSRange] = []
                while searchRange.location < nsText.length {
                    let r = nsText.range(of: query, options: opts, range: searchRange)
                    guard r.location != NSNotFound else { break }
                    found.append(r)
                    searchRange.location = r.location + r.length
                    searchRange.length = nsText.length - searchRange.location
                }
                ranges = found
            }

            let color = NSColor.findHighlightColor.withAlphaComponent(0.5)
            for range in ranges {
                layoutManager.addTemporaryAttribute(.backgroundColor, value: color, forCharacterRange: range)
            }
            findHighlightRanges = ranges
            return ranges.count
        }

        func clearFindHighlights() {
            guard let textView = textView,
                  let layoutManager = textView.layoutManager else { return }
            for range in findHighlightRanges {
                let nsLength = (textView.string as NSString).length
                if range.location + range.length <= nsLength {
                    layoutManager.removeTemporaryAttribute(.backgroundColor, forCharacterRange: range)
                }
            }
            findHighlightRanges = []
        }

        func scrollToFindMatch(at index: Int) {
            guard let textView = textView, index >= 0, index < findHighlightRanges.count else { return }
            let range = findHighlightRanges[index]
            textView.setSelectedRange(range)
            textView.scrollRangeToVisible(range)
        }

        func replaceCurrentMatch(at index: Int, with replacement: String) {
            guard let textView = textView, index >= 0, index < findHighlightRanges.count else { return }
            let range = findHighlightRanges[index]
            textView.insertText(replacement, replacementRange: range)
        }

        func replaceAllMatches(with replacement: String) {
            guard let textView = textView else { return }
            // Replace in reverse order to preserve indices
            for range in findHighlightRanges.reversed() {
                textView.insertText(replacement, replacementRange: range)
            }
        }

        // MARK: - D1/D2: Context Menu (Explain + AI Rename)

        func textView(_ textView: NSTextView, menu: NSMenu, for event: NSEvent, at charIndex: Int) -> NSMenu? {
            let selectedRange = textView.selectedRange()
            let nsText = textView.string as NSString

            // Add "Explain Selection" if text is selected
            if selectedRange.length > 0 {
                let separator = NSMenuItem.separator()
                let explainItem = NSMenuItem(
                    title: "Explain Selection",
                    action: #selector(explainSelectionAction(_:)),
                    keyEquivalent: ""
                )
                explainItem.target = self
                menu.insertItem(separator, at: 0)
                menu.insertItem(explainItem, at: 0)
            }

            // Add "AI Rename Symbol" for word at cursor
            let wordRange = textView.selectionRange(forProposedRange: NSRange(location: charIndex, length: 0), granularity: .selectByWord)
            if wordRange.length > 0 {
                let word = nsText.substring(with: wordRange)
                // Only offer rename for identifiers (starts with letter/underscore)
                if let first = word.first, (first.isLetter || first == "_") {
                    let renameItem = NSMenuItem(
                        title: "AI Rename '\(word)'",
                        action: #selector(aiRenameAction(_:)),
                        keyEquivalent: ""
                    )
                    renameItem.target = self
                    renameItem.representedObject = word
                    menu.insertItem(renameItem, at: menu.items.isEmpty ? 0 : 1)
                }
            }

            return menu
        }

        @objc func explainSelectionAction(_ sender: Any?) {
            guard let textView = textView else { return }
            let nsText = textView.string as NSString
            let selectedRange = textView.selectedRange()
            guard selectedRange.length > 0 else { return }
            let code = nsText.substring(with: selectedRange)
            selectedCodeForAI = code
            showExplainPopover = true
            parent.onExplainSelection?(code)
        }

        @objc func aiRenameAction(_ sender: Any?) {
            guard let menuItem = sender as? NSMenuItem,
                  let word = menuItem.representedObject as? String else { return }
            selectedWordForRename = word
            // Get surrounding context (200 chars before + after cursor)
            var context = ""
            if let textView = textView {
                let nsText = textView.string as NSString
                let cursor = textView.selectedRange().location
                let start = max(0, cursor - 200)
                let end = min(nsText.length, cursor + 200)
                context = nsText.substring(with: NSRange(location: start, length: end - start))
                selectedCodeForAI = context
            }
            showRenameSheet = true
            parent.onAIRename?(word, context)
        }

        /// Replace all occurrences of a word in the current file
        func replaceAllOccurrences(of oldWord: String, with newWord: String) {
            guard let textView = textView else { return }
            let newText = textView.string.replacingOccurrences(of: oldWord, with: newWord)
            textView.string = newText
            parent.text = newText
            lastSyncedText = newText
            applySyntaxHighlighting()
        }

        // MARK: - A3: Code Folding

        func detectFoldableLines() -> Set<Int> {
            guard let textView = textView else { return [] }
            let text = textView.string as NSString
            var foldable = Set<Int>()
            var lineNumber = 1
            var index = 0
            while index < text.length {
                let lineRange = text.lineRange(for: NSRange(location: index, length: 0))
                let line = text.substring(with: lineRange).trimmingCharacters(in: .whitespacesAndNewlines)
                if line.hasSuffix("{") && !foldedRegions.keys.contains(lineNumber) {
                    foldable.insert(lineNumber)
                }
                lineNumber += 1
                index = NSMaxRange(lineRange)
            }
            return foldable
        }

        func toggleFold(at lineNumber: Int) {
            guard let textView = textView else { return }
            let nsText = textView.string as NSString

            // If already folded, unfold
            if let region = foldedRegions[lineNumber] {
                // Verify range is still valid (text may have changed)
                guard region.range.location + region.range.length <= nsText.length else {
                    foldedRegions.removeValue(forKey: lineNumber)
                    return
                }
                textView.insertText(region.original, replacementRange: region.range)
                foldedRegions.removeValue(forKey: lineNumber)
                applySyntaxHighlighting()
                return
            }

            // Find the line's character range
            var currentLine = 1
            var index = 0
            while currentLine < lineNumber && index < nsText.length {
                let lineRange = nsText.lineRange(for: NSRange(location: index, length: 0))
                index = NSMaxRange(lineRange)
                currentLine += 1
            }

            guard index < nsText.length else { return }
            let lineRange = nsText.lineRange(for: NSRange(location: index, length: 0))
            let lineText = nsText.substring(with: lineRange).trimmingCharacters(in: .whitespacesAndNewlines)
            guard lineText.hasSuffix("{") else { return }

            // Find matching closing brace
            let openBracePos = nsText.range(of: "{", options: .backwards, range: lineRange).location
            guard openBracePos != NSNotFound else { return }

            var depth = 0
            var i = openBracePos
            while i < nsText.length {
                let ch = nsText.character(at: i)
                if ch == 0x7B /* { */ { depth += 1 }
                else if ch == 0x7D /* } */ { depth -= 1 }
                if depth == 0 {
                    // Found the matching brace — fold from after { to }
                    let foldStart = openBracePos + 1
                    let foldEnd = i + 1
                    guard foldEnd > foldStart else { return }
                    let foldRange = NSRange(location: foldStart, length: foldEnd - foldStart)
                    let original = nsText.substring(with: foldRange)
                    foldedRegions[lineNumber] = (range: foldRange, original: original)
                    textView.insertText(" ⋯ }", replacementRange: foldRange)
                    applySyntaxHighlighting()
                    return
                }
                i += 1
            }
        }

        // MARK: - Cursor Tracking + Bracket Matching

        func textViewDidChangeSelection(_ notification: Notification) {
            guard let textView = textView else { return }
            let cursorLocation = textView.selectedRange().location
            let text = textView.string
            let (line, column) = lineAndColumn(for: cursorLocation, in: text)
            parent.onCursorMove(line, column)

            // A2: Highlight matching brackets
            highlightMatchingBrackets()
        }

        private func lineAndColumn(for location: Int, in text: String) -> (Int, Int) {
            guard location >= 0, location <= text.count else {
                return (1, 1)
            }

            let nsString = text as NSString
            var line = 1
            var lastLineStart = 0

            for i in 0..<min(location, nsString.length) {
                if nsString.character(at: i) == 0x0A { // newline
                    line += 1
                    lastLineStart = i + 1
                }
            }

            let column = location - lastLineStart + 1
            return (line, column)
        }

        // MARK: - Line Navigation

        func scrollToLine(_ line: Int) {
            guard let textView = textView else { return }
            let text = textView.string
            let lines = text.components(separatedBy: "\n")
            let targetIndex = max(0, min(line - 1, lines.count - 1))

            // Calculate character offset for the start of the target line
            var charOffset = 0
            for i in 0..<targetIndex {
                charOffset += lines[i].count + 1 // +1 for newline
            }

            let lineLength = lines[targetIndex].count
            let range = NSRange(location: charOffset, length: lineLength)

            // Select the line and scroll to it
            textView.setSelectedRange(range)
            textView.scrollRangeToVisible(range)

            // Brief flash highlight on the target line
            if let layoutManager = textView.layoutManager,
               let textContainer = textView.textContainer {
                let glyphRange = layoutManager.glyphRange(forCharacterRange: range, actualCharacterRange: nil)
                let lineRect = layoutManager.boundingRect(forGlyphRange: glyphRange, in: textContainer)
                    .offsetBy(dx: textView.textContainerOrigin.x, dy: textView.textContainerOrigin.y)

                let highlight = NSView(frame: lineRect.insetBy(dx: -4, dy: -1))
                highlight.wantsLayer = true
                highlight.layer?.backgroundColor = NSColor.findHighlightColor.withAlphaComponent(0.4).cgColor
                highlight.layer?.cornerRadius = 2
                textView.addSubview(highlight)

                // Fade out after 1.5 seconds
                DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                    NSAnimationContext.runAnimationGroup { ctx in
                        ctx.duration = 0.5
                        highlight.animator().alphaValue = 0
                    } completionHandler: {
                        highlight.removeFromSuperview()
                    }
                }
            }
        }
    }
}

// MARK: - Custom NSTextView Subclass (Shift+Tab handling)

final class CodeNSTextView: NSTextView {
    weak var coordinator: CodeTextView.Coordinator?

    override func keyDown(with event: NSEvent) {
        // Shift+Tab → dedent
        if event.keyCode == 48 /* Tab */ && event.modifierFlags.contains(.shift) {
            coordinator?.dedentSelectedLines()
            return
        }

        // D3: Tab → accept inline completion if active
        if event.keyCode == 48 /* Tab */ && !event.modifierFlags.contains(.shift) {
            if coordinator?.inlineCompletion.handleTab() == true {
                return
            }
        }

        // D3: Any non-Tab key dismisses inline completion ghost text
        if event.keyCode != 48 {
            coordinator?.inlineCompletion.dismiss()
        }

        super.keyDown(with: event)
    }
}

// MARK: - Line Number Ruler View

final class LineNumberRulerView: NSRulerView {
    private weak var textView: NSTextView?
    weak var coordinator: CodeTextView.Coordinator?

    // A3: fold marker click zone width
    private let foldMarkerWidth: CGFloat = 14

    init(textView: NSTextView) {
        self.textView = textView
        if textView.enclosingScrollView == nil {
            assertionFailure("CodeTextView must have an enclosingScrollView for line numbers")
        }
        super.init(scrollView: textView.enclosingScrollView ?? NSScrollView(), orientation: .verticalRuler)
        self.clientView = textView
        self.ruleThickness = max(44, (textView.font?.pointSize ?? 14) * 3.6)
    }

    @available(*, unavailable)
    required init(coder: NSCoder) {
        fatalError("init(coder:) is not supported")
    }

    // MARK: - A3/A5: Mouse Click Handling (breakpoints + fold toggles)

    override func mouseDown(with event: NSEvent) {
        guard let textView = textView,
              let layoutManager = textView.layoutManager,
              let textContainer = textView.textContainer,
              let coordinator = coordinator else {
            super.mouseDown(with: event)
            return
        }

        let localPoint = convert(event.locationInWindow, from: nil)
        guard let scrollView else { return }
        let visibleRect = scrollView.contentView.bounds
        let containerOrigin = textView.textContainerOrigin

        // Determine which line was clicked
        let text = textView.string as NSString
        guard text.length > 0 else { return }

        let glyphRange = layoutManager.glyphRange(forBoundingRect: visibleRect, in: textContainer)
        let charRange = layoutManager.characterRange(forGlyphRange: glyphRange, actualGlyphRange: nil)

        var lineNumber = 1
        for i in 0..<charRange.location {
            if text.character(at: i) == 0x0A { lineNumber += 1 }
        }

        var index = charRange.location
        while index < NSMaxRange(charRange) {
            let lineRange = text.lineRange(for: NSRange(location: index, length: 0))
            let glyphRangeForLine = layoutManager.glyphRange(forCharacterRange: lineRange, actualCharacterRange: nil)
            let lineRect = layoutManager.boundingRect(forGlyphRange: glyphRangeForLine, in: textContainer)
            let yPosition = lineRect.minY + containerOrigin.y - visibleRect.origin.y

            if localPoint.y >= yPosition && localPoint.y < yPosition + lineRect.height {
                // Clicked on this line
                if localPoint.x < foldMarkerWidth {
                    // A3: Fold marker zone — toggle fold
                    coordinator.toggleFold(at: lineNumber)
                } else {
                    // A5: Line number zone — toggle breakpoint
                    if coordinator.breakpoints.contains(lineNumber) {
                        coordinator.breakpoints.remove(lineNumber)
                    } else {
                        coordinator.breakpoints.insert(lineNumber)
                    }
                }
                needsDisplay = true
                return
            }

            lineNumber += 1
            index = NSMaxRange(lineRange)
        }
    }

    // MARK: - Drawing

    override func drawHashMarksAndLabels(in rect: NSRect) {
        guard let textView = textView,
              let layoutManager = textView.layoutManager,
              let textContainer = textView.textContainer else { return }

        // Draw background
        NSColor.textBackgroundColor.withAlphaComponent(0.5).setFill()
        rect.fill()

        // Draw separator line on the right edge
        NSColor.separatorColor.setStroke()
        let separatorPath = NSBezierPath()
        separatorPath.move(to: NSPoint(x: ruleThickness - 0.5, y: rect.minY))
        separatorPath.line(to: NSPoint(x: ruleThickness - 0.5, y: rect.maxY))
        separatorPath.lineWidth = 0.5
        separatorPath.stroke()

        let text = textView.string as NSString
        let fontSize = max((textView.font?.pointSize ?? 14) - 2, 9)
        let font = NSFont.monospacedSystemFont(ofSize: fontSize, weight: .regular)

        let paragraphStyle = NSMutableParagraphStyle()
        paragraphStyle.alignment = .right

        let attrs: [NSAttributedString.Key: Any] = [
            .font: font,
            .foregroundColor: NSColor.tertiaryLabelColor,
            .paragraphStyle: paragraphStyle
        ]

        let breakpoints = coordinator?.breakpoints ?? []
        let foldedRegions = coordinator?.foldedRegions ?? [:]
        let foldableLines = coordinator?.detectFoldableLines() ?? []

        // Get the visible rect in text view coordinates
        guard let scrollView else { return }
        let visibleRect = scrollView.contentView.bounds
        let containerOrigin = textView.textContainerOrigin

        let glyphRange = layoutManager.glyphRange(forBoundingRect: visibleRect, in: textContainer)
        let charRange = layoutManager.characterRange(forGlyphRange: glyphRange, actualGlyphRange: nil)

        // Find the line number of the first visible character
        var lineNumber = 1
        for i in 0..<charRange.location {
            if text.character(at: i) == 0x0A { lineNumber += 1 }
        }

        // Enumerate visible line fragments
        var index = charRange.location
        while index < NSMaxRange(charRange) {
            let lineRange = text.lineRange(for: NSRange(location: index, length: 0))
            let glyphRangeForLine = layoutManager.glyphRange(forCharacterRange: lineRange, actualCharacterRange: nil)
            let lineRect = layoutManager.boundingRect(forGlyphRange: glyphRangeForLine, in: textContainer)

            let yPosition = lineRect.minY + containerOrigin.y - visibleRect.origin.y

            // A5: Draw breakpoint marker (red circle)
            if breakpoints.contains(lineNumber) {
                let bpSize: CGFloat = min(lineRect.height - 2, 14)
                let bpRect = NSRect(
                    x: foldMarkerWidth + 2,
                    y: yPosition + (lineRect.height - bpSize) / 2,
                    width: bpSize,
                    height: bpSize
                )
                NSColor.systemRed.withAlphaComponent(0.85).setFill()
                NSBezierPath(ovalIn: bpRect).fill()
            }

            // A3: Draw fold marker
            if foldableLines.contains(lineNumber) || foldedRegions[lineNumber] != nil {
                let isFolded = foldedRegions[lineNumber] != nil
                let marker = isFolded ? "▶" : "▼"
                let markerAttrs: [NSAttributedString.Key: Any] = [
                    .font: NSFont.systemFont(ofSize: fontSize - 1),
                    .foregroundColor: NSColor.tertiaryLabelColor
                ]
                let markerRect = NSRect(x: 1, y: yPosition, width: foldMarkerWidth - 2, height: lineRect.height)
                (marker as NSString).draw(in: markerRect, withAttributes: markerAttrs)
            }

            // Draw line number
            let numberRect = NSRect(
                x: foldMarkerWidth,
                y: yPosition,
                width: ruleThickness - foldMarkerWidth - 8,
                height: lineRect.height
            )

            let lineStr = "\(lineNumber)" as NSString
            // Breakpoint lines: white text on red
            if breakpoints.contains(lineNumber) {
                var bpAttrs = attrs
                bpAttrs[.foregroundColor] = NSColor.white
                lineStr.draw(in: numberRect, withAttributes: bpAttrs)
            } else {
                lineStr.draw(in: numberRect, withAttributes: attrs)
            }

            lineNumber += 1
            index = NSMaxRange(lineRange)
        }
    }
}
