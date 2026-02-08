//
//  ChatMessageRow.swift
//  MagnetarStudio (macOS)
//
//  Chat message row component - Extracted from ChatWorkspace.swift (Phase 6.17)
//  Enhanced with timestamps, hover actions, and code block formatting (Phase 6.18)
//

import SwiftUI

struct ChatMessageRow: View {
    let message: ChatMessage
    var onRetry: (() -> Void)?  // Optional retry callback for incomplete messages
    var isStreaming: Bool = false  // True if this message is currently streaming

    @State private var isHovered: Bool = false
    @State private var showCopied: Bool = false
    @State private var copyResetTask: Task<Void, Never>?

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            HStack(alignment: .top, spacing: 12) {
                // Avatar
                Circle()
                    .fill(message.role == .user ? AnyShapeStyle(LinearGradient.magnetarGradient) : AnyShapeStyle(Color.surfaceSecondary))
                    .frame(width: 32, height: 32)
                    .overlay(
                        Image(systemName: message.role == .user ? "person.fill" : "sparkles")
                            .font(.system(size: 14))
                            .foregroundColor(message.role == .user ? .white : .textSecondary)
                    )

                // Message content
                VStack(alignment: .leading, spacing: 4) {
                    // Header with role and timestamp
                    HStack(spacing: 8) {
                        Text(message.role.displayName)
                            .font(.system(size: 11, weight: .semibold))
                            .foregroundColor(.textSecondary)

                        Text("·")
                            .font(.system(size: 11))
                            .foregroundColor(.textSecondary.opacity(0.5))

                        Text(message.createdAt.relativeFormatted)
                            .font(.system(size: 11))
                            .foregroundColor(.textSecondary.opacity(0.7))

                        // Model indicator for assistant messages
                        if message.role == .assistant, let modelId = message.modelId {
                            Text("·")
                                .font(.system(size: 11))
                                .foregroundColor(.textSecondary.opacity(0.5))

                            Text(modelId.components(separatedBy: ":").first ?? modelId)
                                .font(.system(size: 10, weight: .medium))
                                .foregroundColor(.magnetarPrimary.opacity(0.8))
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(
                                    Capsule()
                                        .fill(Color.magnetarPrimary.opacity(0.1))
                                )
                        }
                    }

                    // Message content with code block handling
                    MessageContentView(content: message.content)
                        .textSelection(.enabled)

                    // Streaming indicator
                    if isStreaming && message.role == .assistant && !message.content.isEmpty {
                        TypingIndicator()
                            .padding(.top, 4)
                    }
                }

                Spacer()

                // Hover actions
                if isHovered && !isStreaming {
                    HStack(spacing: 4) {
                        // Copy button
                        Button {
                            copyToClipboard(message.content)
                        } label: {
                            Image(systemName: showCopied ? "checkmark" : "doc.on.doc")
                                .font(.system(size: 12))
                                .foregroundColor(showCopied ? .green : .textSecondary)
                                .frame(width: 24, height: 24)
                                .background(Color.surfaceSecondary.opacity(0.8))
                                .cornerRadius(4)
                        }
                        .buttonStyle(.plain)
                        .help("Copy message")

                        // Regenerate button (only for last assistant message)
                        if message.role == .assistant, let onRetry {
                            Button(action: onRetry) {
                                Image(systemName: "arrow.clockwise")
                                    .font(.system(size: 12))
                                    .foregroundColor(.textSecondary)
                                    .frame(width: 24, height: 24)
                                    .background(Color.surfaceSecondary.opacity(0.8))
                                    .cornerRadius(4)
                            }
                            .buttonStyle(.plain)
                            .help("Regenerate response")
                        }
                    }
                    .transition(.opacity.combined(with: .scale(scale: 0.9)))
                }
            }

            // Incomplete message indicator
            if message.isIncomplete {
                HStack(spacing: 8) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundColor(.orange)
                        .font(.system(size: 12))

                    Text("Response interrupted")
                        .font(.system(size: 11, weight: .medium))
                        .foregroundColor(.orange)

                    Spacer()

                    if let onRetry {
                        Button(action: onRetry) {
                            HStack(spacing: 4) {
                                Image(systemName: "arrow.clockwise")
                                Text("Retry")
                            }
                            .font(.system(size: 11, weight: .medium))
                            .foregroundColor(.white)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 4)
                            .background(Color.orange)
                            .cornerRadius(4)
                        }
                        .buttonStyle(.plain)
                    }
                }
                .padding(.top, 8)
                .padding(.leading, 44)  // Align with message content
            }
        }
        .padding(12)
        .background(message.role == .user ? Color.magnetarPrimary.opacity(0.06) : Color.surfaceSecondary.opacity(0.4))
        .cornerRadius(10)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
    }

    private func copyToClipboard(_ text: String) {
        #if os(macOS)
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(text, forType: .string)
        #endif

        withAnimation {
            showCopied = true
        }

        // Reset after 2 seconds
        copyResetTask?.cancel()
        copyResetTask = Task {
            try? await Task.sleep(for: .seconds(2))
            guard !Task.isCancelled else { return }
            withAnimation { showCopied = false }
        }
    }
}

// MARK: - Message Content View (handles code blocks)

struct MessageContentView: View {
    let content: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            ForEach(Array(parseContent().enumerated()), id: \.offset) { _, segment in
                switch segment {
                case .text(let text):
                    Text(text)
                        .font(.system(size: 14))

                case .codeBlock(let code, let language):
                    CodeBlockView(code: code, language: language)
                }
            }
        }
    }

    private func parseContent() -> [ContentSegment] {
        var segments: [ContentSegment] = []
        let pattern = "```(\\w*)\\n?([\\s\\S]*?)```"

        guard let regex = try? NSRegularExpression(pattern: pattern, options: []) else {
            return [.text(content)]
        }

        let nsContent = content as NSString
        var lastEnd = 0

        let matches = regex.matches(in: content, options: [], range: NSRange(location: 0, length: nsContent.length))

        for match in matches {
            // Add text before code block
            if match.range.location > lastEnd {
                let textRange = NSRange(location: lastEnd, length: match.range.location - lastEnd)
                let text = nsContent.substring(with: textRange).trimmingCharacters(in: .whitespacesAndNewlines)
                if !text.isEmpty {
                    segments.append(.text(text))
                }
            }

            // Extract language and code
            let language = match.range(at: 1).length > 0 ? nsContent.substring(with: match.range(at: 1)) : nil
            let code = nsContent.substring(with: match.range(at: 2)).trimmingCharacters(in: .whitespacesAndNewlines)

            segments.append(.codeBlock(code: code, language: language))
            lastEnd = match.range.location + match.range.length
        }

        // Add remaining text
        if lastEnd < nsContent.length {
            let text = nsContent.substring(from: lastEnd).trimmingCharacters(in: .whitespacesAndNewlines)
            if !text.isEmpty {
                segments.append(.text(text))
            }
        }

        // If no segments were created, return the whole content as text
        if segments.isEmpty {
            return [.text(content)]
        }

        return segments
    }
}

enum ContentSegment {
    case text(String)
    case codeBlock(code: String, language: String?)
}

// MARK: - Code Block View

struct CodeBlockView: View {
    let code: String
    let language: String?

    @State private var showCopied: Bool = false
    @State private var copyResetTask: Task<Void, Never>?

    var body: some View {
        VStack(alignment: .leading, spacing: 0) {
            // Header with language and copy button
            HStack {
                if let language, !language.isEmpty {
                    Text(language)
                        .font(.system(size: 11, weight: .medium))
                        .foregroundColor(.textSecondary)
                }

                Spacer()

                Button {
                    copyToClipboard(code)
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: showCopied ? "checkmark" : "doc.on.doc")
                        Text(showCopied ? "Copied!" : "Copy")
                    }
                    .font(.system(size: 11))
                    .foregroundColor(showCopied ? .green : .textSecondary)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(Color.black.opacity(0.3))

            // Code content
            ScrollView(.horizontal, showsIndicators: false) {
                Text(code)
                    .font(.system(size: 13, design: .monospaced))
                    .foregroundColor(.white.opacity(0.9))
                    .padding(12)
            }
        }
        .background(Color(.textBackgroundColor).opacity(0.6))
        .cornerRadius(8)
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Color.white.opacity(0.1), lineWidth: 1)
        )
    }

    private func copyToClipboard(_ text: String) {
        #if os(macOS)
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(text, forType: .string)
        #endif

        withAnimation {
            showCopied = true
        }

        copyResetTask?.cancel()
        copyResetTask = Task {
            try? await Task.sleep(for: .seconds(2))
            guard !Task.isCancelled else { return }
            withAnimation { showCopied = false }
        }
    }
}

// MARK: - Typing Indicator

struct TypingIndicator: View {
    @State private var animationPhase: Int = 0
    @State private var animationTimer: Timer?

    var body: some View {
        HStack(spacing: 4) {
            ForEach(0..<3, id: \.self) { index in
                Circle()
                    .fill(Color.magnetarPrimary.opacity(animationPhase == index ? 1.0 : 0.4))
                    .frame(width: 6, height: 6)
            }
        }
        .onAppear {
            animationTimer = Timer.scheduledTimer(withTimeInterval: 0.3, repeats: true) { _ in
                withAnimation(.easeInOut(duration: 0.2)) {
                    animationPhase = (animationPhase + 1) % 3
                }
            }
        }
        .onDisappear {
            animationTimer?.invalidate()
            animationTimer = nil
        }
    }
}

// MARK: - Date Extension for Relative Formatting

extension Date {
    var relativeFormatted: String {
        let now = Date()
        let diff = now.timeIntervalSince(self)

        if diff < 60 {
            return "just now"
        } else if diff < 3600 {
            let minutes = Int(diff / 60)
            return "\(minutes)m ago"
        } else if diff < 86400 {
            let hours = Int(diff / 3600)
            return "\(hours)h ago"
        } else if diff < 604800 {
            let days = Int(diff / 86400)
            return "\(days)d ago"
        } else {
            let formatter = DateFormatter()
            formatter.dateStyle = .short
            formatter.timeStyle = .none
            return formatter.string(from: self)
        }
    }
}
