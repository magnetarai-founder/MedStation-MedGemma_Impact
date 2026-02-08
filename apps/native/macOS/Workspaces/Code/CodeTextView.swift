//
//  CodeTextView.swift
//  MagnetarStudio (macOS)
//
//  NSViewRepresentable wrapping NSScrollView + NSTextView for the code editor.
//  Provides line-level cursor positioning, scroll-to-line, and live cursor tracking
//  that SwiftUI's TextEditor cannot offer.
//

import SwiftUI
import AppKit

struct CodeTextView: NSViewRepresentable {
    @Binding var text: String
    let fontSize: CGFloat
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

        return scrollView
    }

    func updateNSView(_ scrollView: NSScrollView, context: Context) {
        guard let textView = context.coordinator.textView else { return }

        // Update font if changed
        let newFont = NSFont.monospacedSystemFont(ofSize: fontSize, weight: .regular)
        if textView.font != newFont {
            textView.font = newFont
        }

        // Sync text from binding (only when not actively editing)
        if !context.coordinator.isEditing && text != textView.string {
            textView.string = text
            context.coordinator.lastSyncedText = text
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
        var isEditing = false
        var lastSyncedText = ""
        var lastTargetLine: Int?

        init(_ parent: CodeTextView) {
            self.parent = parent
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
