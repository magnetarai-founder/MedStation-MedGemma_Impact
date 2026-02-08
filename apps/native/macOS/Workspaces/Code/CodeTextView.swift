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

    func makeNSView(context: Context) -> NSScrollView {
        let scrollView = NSScrollView()
        scrollView.hasVerticalScroller = true
        scrollView.hasHorizontalScroller = true
        scrollView.autohidesScrollers = true
        scrollView.borderType = .noBorder

        let textView = NSTextView()
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
        context.coordinator.textView = textView
        context.coordinator.lastSyncedText = text

        scrollView.documentView = textView

        // Set up line number ruler
        let rulerView = LineNumberRulerView(textView: textView)
        scrollView.verticalRulerView = rulerView
        scrollView.hasVerticalRuler = true
        scrollView.rulersVisible = showLineNumbers

        context.coordinator.rulerView = rulerView

        // Apply initial syntax highlighting
        context.coordinator.applySyntaxHighlighting()

        // Observe text layout changes to update ruler
        NotificationCenter.default.addObserver(
            context.coordinator,
            selector: #selector(Coordinator.textStorageDidProcessEditing(_:)),
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
            // Debounced re-highlight (300ms)
            scheduleHighlight()
        }

        @objc func textStorageDidProcessEditing(_ notification: Notification) {
            rulerView?.needsDisplay = true
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

        // MARK: - Cursor Tracking

        func textViewDidChangeSelection(_ notification: Notification) {
            guard let textView = textView else { return }
            let cursorLocation = textView.selectedRange().location
            let text = textView.string
            let (line, column) = lineAndColumn(for: cursorLocation, in: text)
            parent.onCursorMove(line, column)
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

// MARK: - Line Number Ruler View

final class LineNumberRulerView: NSRulerView {
    private weak var textView: NSTextView?

    init(textView: NSTextView) {
        self.textView = textView
        super.init(scrollView: textView.enclosingScrollView!, orientation: .verticalRuler)
        self.clientView = textView
        self.ruleThickness = max(36, (textView.font?.pointSize ?? 14) * 3.2)
    }

    @available(*, unavailable)
    required init(coder: NSCoder) {
        fatalError("init(coder:) is not supported")
    }

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
        let font = NSFont.monospacedSystemFont(
            ofSize: max((textView.font?.pointSize ?? 14) - 2, 9),
            weight: .regular
        )

        let paragraphStyle = NSMutableParagraphStyle()
        paragraphStyle.alignment = .right

        let attrs: [NSAttributedString.Key: Any] = [
            .font: font,
            .foregroundColor: NSColor.tertiaryLabelColor,
            .paragraphStyle: paragraphStyle
        ]

        // Get the visible rect in text view coordinates
        let visibleRect = scrollView!.contentView.bounds
        let containerOrigin = textView.textContainerOrigin

        // Count lines visible in the rect
        let glyphRange = layoutManager.glyphRange(forBoundingRect: visibleRect, in: textContainer)
        let charRange = layoutManager.characterRange(forGlyphRange: glyphRange, actualGlyphRange: nil)

        // Find the line number of the first visible character
        var lineNumber = 1
        for i in 0..<charRange.location {
            if text.character(at: i) == 0x0A {
                lineNumber += 1
            }
        }

        // Enumerate visible line fragments
        var index = charRange.location
        while index < NSMaxRange(charRange) {
            let lineRange = text.lineRange(for: NSRange(location: index, length: 0))
            let glyphRangeForLine = layoutManager.glyphRange(forCharacterRange: lineRange, actualCharacterRange: nil)
            let lineRect = layoutManager.boundingRect(forGlyphRange: glyphRangeForLine, in: textContainer)

            // Convert to ruler coordinates
            let yPosition = lineRect.minY + containerOrigin.y - visibleRect.origin.y
            let drawRect = NSRect(
                x: 2,
                y: yPosition,
                width: ruleThickness - 10,
                height: lineRect.height
            )

            let lineStr = "\(lineNumber)" as NSString
            lineStr.draw(in: drawRect, withAttributes: attrs)

            lineNumber += 1
            index = NSMaxRange(lineRange)
        }
    }
}
