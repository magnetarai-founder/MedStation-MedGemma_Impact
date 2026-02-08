//
//  InlineCompletionOverlay.swift
//  MagnetarStudio (macOS)
//
//  AI-powered inline code completion.
//  After a 1.5s typing pause, requests completion from WorkspaceAIService.
//  Shows ghost text (gray italic) after cursor; Tab to accept, any key to dismiss.
//

import SwiftUI
import AppKit
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "InlineCompletion")

/// Manages inline AI completion state for the code editor Coordinator.
/// Call `onTextChange()` after each edit and `onKeyPress()` before processing keys.
final class InlineCompletionManager {
    weak var textView: NSTextView?

    private var completionTask: Task<Void, Never>?
    private var ghostText: String?
    private var ghostRange: NSRange?
    private var charsSinceLastCompletion = 0
    private let minimumCharsBeforeCompletion = 5
    private let delaySeconds: TimeInterval = 1.5

    var language: String = "code"

    /// Call when text changes (from textDidChange)
    func onTextChange() {
        charsSinceLastCompletion += 1
        dismissGhostText()
        scheduleCompletion()
    }

    /// Returns true if Tab accepted a completion (caller should skip normal Tab handling)
    func handleTab() -> Bool {
        guard let ghost = ghostText, let textView = textView, let range = ghostRange else {
            return false
        }
        // Accept: insert ghost text at cursor
        textView.insertText(ghost, replacementRange: range)
        dismissGhostText()
        return true
    }

    /// Dismiss current ghost text (call on any non-Tab key)
    func dismiss() {
        dismissGhostText()
    }

    // MARK: - Private

    private func scheduleCompletion() {
        completionTask?.cancel()

        guard charsSinceLastCompletion >= minimumCharsBeforeCompletion else { return }

        completionTask = Task { @MainActor [weak self] in
            try? await Task.sleep(for: .milliseconds(1500))
            guard !Task.isCancelled else { return }
            await self?.requestCompletion()
        }
    }

    @MainActor
    private func requestCompletion() async {
        guard let textView = textView else { return }
        let text = textView.string
        let cursorPos = textView.selectedRange().location

        // Get last 20 lines before cursor
        let nsText = text as NSString
        guard cursorPos > 0, cursorPos <= nsText.length else { return }

        let textBeforeCursor = nsText.substring(to: cursorPos)
        let lines = textBeforeCursor.components(separatedBy: "\n")
        let context = lines.suffix(20).joined(separator: "\n")

        let prompt = "Complete the next 1-3 lines of this \(language) code. Return ONLY the code to insert (no markdown, no explanation):\n\n\(context)"

        let aiService = WorkspaceAIService.shared
        let result = await aiService.generateSync(
            action: .generate,
            input: prompt,
            strategy: TextAIStrategy()
        )

        let completion = result.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !completion.isEmpty, !Task.isCancelled else { return }

        // Show ghost text
        showGhostText(completion, at: cursorPos)
        charsSinceLastCompletion = 0
    }

    private func showGhostText(_ text: String, at position: Int) {
        guard let textView = textView,
              let layoutManager = textView.layoutManager else { return }

        let range = NSRange(location: position, length: 0)
        ghostText = text
        ghostRange = range

        // Insert placeholder text with ghost styling
        let attrs: [NSAttributedString.Key: Any] = [
            .foregroundColor: NSColor.tertiaryLabelColor,
            .font: NSFont.monospacedSystemFont(
                ofSize: textView.font?.pointSize ?? 14,
                weight: .regular
            ).withItalic()
        ]

        // Use temporary attributes to show ghost text as inline overlay
        // Note: actual ghost text insertion requires textStorage modification;
        // we insert it but mark it as "ghost" to remove on next keystroke
        textView.textStorage?.beginEditing()
        textView.textStorage?.insert(
            NSAttributedString(string: text, attributes: attrs),
            at: position
        )
        textView.textStorage?.endEditing()

        ghostRange = NSRange(location: position, length: text.count)
    }

    private func dismissGhostText() {
        completionTask?.cancel()
        guard let textView = textView,
              let range = ghostRange,
              ghostText != nil else { return }

        // Remove the ghost text from textStorage
        let nsLength = (textView.string as NSString).length
        if range.location + range.length <= nsLength {
            textView.textStorage?.beginEditing()
            textView.textStorage?.deleteCharacters(in: range)
            textView.textStorage?.endEditing()
        }

        ghostText = nil
        ghostRange = nil
    }
}

// MARK: - NSFont italic helper

private extension NSFont {
    func withItalic() -> NSFont {
        let descriptor = fontDescriptor.withSymbolicTraits(.italic)
        return NSFont(descriptor: descriptor, size: pointSize) ?? self
    }
}
