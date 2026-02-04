//
//  AIAssistantPanel.swift
//  MagnetarStudio
//
//  Integrated AI assistant panel for the Coding workspace.
//  Provides contextual help with terminal and code context.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "AIAssistantPanel")

// MARK: - AI Assistant Panel

struct AIAssistantPanel: View {
    @Bindable var codingStore: CodingStore
    @State private var inputText: String = ""
    @State private var isExpanded: Bool = true
    @FocusState private var isInputFocused: Bool

    var body: some View {
        VStack(spacing: 0) {
            // Header
            header

            Divider()

            if isExpanded {
                // Messages
                messagesView

                // Pending Commands
                if !codingStore.aiAssistant.pendingContext.isEmpty {
                    pendingContextView
                }

                Divider()

                // Input
                inputView
            }
        }
        .background(Color.surfaceSecondary.opacity(0.5))
    }

    // MARK: - Header

    private var header: some View {
        HStack {
            Image(systemName: "sparkles")
                .foregroundStyle(.purple)

            Text("AI Assistant")
                .font(.system(size: 12, weight: .semibold))

            Spacer()

            // Context indicator
            if !codingStore.contextHistory.isEmpty {
                HStack(spacing: 4) {
                    Circle()
                        .fill(Color.green)
                        .frame(width: 6, height: 6)
                    Text("\(codingStore.contextHistory.count) context")
                        .font(.system(size: 10))
                        .foregroundStyle(.secondary)
                }
            }

            // Expand/collapse button
            Button {
                withAnimation(.easeInOut(duration: 0.2)) {
                    isExpanded.toggle()
                }
            } label: {
                Image(systemName: isExpanded ? "chevron.down" : "chevron.up")
                    .font(.system(size: 10))
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
    }

    // MARK: - Messages View

    private var messagesView: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 12) {
                    if codingStore.aiAssistant.messages.isEmpty {
                        emptyState
                    } else {
                        ForEach(codingStore.aiAssistant.messages) { message in
                            AIMessageView(message: message, onExecuteCommand: executeCommand)
                                .id(message.id)
                        }
                    }

                    // Streaming indicator
                    if codingStore.aiAssistant.isStreaming {
                        HStack(spacing: 8) {
                            ProgressView()
                                .scaleEffect(0.7)
                            Text("Thinking...")
                                .font(.system(size: 12))
                                .foregroundStyle(.secondary)
                        }
                        .padding(.horizontal, 12)
                    }

                    // Error display
                    if let error = codingStore.aiAssistant.error {
                        HStack {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .foregroundStyle(.red)
                            Text(error)
                                .font(.system(size: 11))
                                .foregroundStyle(.red)
                        }
                        .padding(.horizontal, 12)
                    }
                }
                .padding(.vertical, 8)
            }
            .onChange(of: codingStore.aiAssistant.messages.count) { _, _ in
                if let lastMessage = codingStore.aiAssistant.messages.last {
                    withAnimation {
                        proxy.scrollTo(lastMessage.id, anchor: .bottom)
                    }
                }
            }
        }
    }

    // MARK: - Empty State

    private var emptyState: some View {
        VStack(spacing: 8) {
            Image(systemName: "bubble.left.and.bubble.right")
                .font(.system(size: 24))
                .foregroundStyle(.tertiary)

            Text("AI Assistant")
                .font(.system(size: 13, weight: .medium))

            Text("Ask questions about your code or get help with terminal commands")
                .font(.system(size: 11))
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 20)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(.vertical, 40)
    }

    // MARK: - Pending Context View

    private var pendingContextView: some View {
        VStack(alignment: .leading, spacing: 4) {
            HStack {
                Image(systemName: "tray.full")
                    .font(.system(size: 10))
                    .foregroundStyle(.orange)
                Text("Pending Context")
                    .font(.system(size: 10, weight: .medium))
                    .foregroundStyle(.orange)
                Spacer()
                Button("Clear") {
                    codingStore.clearPendingContext()
                }
                .font(.system(size: 10))
                .buttonStyle(.plain)
                .foregroundStyle(.secondary)
            }

            ForEach(codingStore.aiAssistant.pendingContext.indices, id: \.self) { index in
                let context = codingStore.aiAssistant.pendingContext[index]
                HStack {
                    Image(systemName: context.isError ? "xmark.circle.fill" : "checkmark.circle.fill")
                        .font(.system(size: 10))
                        .foregroundStyle(context.isError ? .red : .green)
                    Text(context.command)
                        .font(.system(size: 10, design: .monospaced))
                        .lineLimit(1)
                }
            }
        }
        .padding(8)
        .background(Color.orange.opacity(0.1))
        .cornerRadius(6)
        .padding(.horizontal, 12)
        .padding(.bottom, 8)
    }

    // MARK: - Input View

    private var inputView: some View {
        HStack(spacing: 8) {
            TextField("Ask about code or terminal...", text: $inputText, axis: .vertical)
                .textFieldStyle(.plain)
                .font(.system(size: 12))
                .lineLimit(1...4)
                .focused($isInputFocused)
                .onSubmit {
                    if !inputText.isEmpty {
                        sendMessage()
                    }
                }

            Button {
                sendMessage()
            } label: {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.system(size: 20))
                    .foregroundColor(inputText.isEmpty ? .gray : .purple)
            }
            .buttonStyle(.plain)
            .disabled(inputText.isEmpty || codingStore.aiAssistant.isStreaming)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
    }

    // MARK: - Actions

    private func sendMessage() {
        let message = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !message.isEmpty else { return }

        inputText = ""

        Task {
            await codingStore.sendToAssistant(message)
        }
    }

    private func executeCommand(_ command: String) {
        Task {
            do {
                try await codingStore.executeCommand(command)
            } catch {
                logger.error("Failed to execute command: \(error)")
            }
        }
    }
}

// MARK: - AI Message View

struct AIMessageView: View {
    let message: AIAssistantMessage
    var onExecuteCommand: ((String) -> Void)?

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            // Avatar
            Circle()
                .fill(message.role == .user ? Color.blue : Color.purple)
                .frame(width: 24, height: 24)
                .overlay {
                    Image(systemName: message.role == .user ? "person.fill" : "sparkles")
                        .font(.system(size: 12))
                        .foregroundStyle(.white)
                }

            VStack(alignment: .leading, spacing: 4) {
                // Role label
                Text(message.role == .user ? "You" : "Assistant")
                    .font(.system(size: 10, weight: .medium))
                    .foregroundStyle(.secondary)

                // Content
                if message.role == .system {
                    systemMessageContent
                } else {
                    Text(message.content)
                        .font(.system(size: 12))
                        .textSelection(.enabled)
                }

                // Terminal context badge
                if let context = message.terminalContext {
                    terminalContextBadge(context)
                }

                // Extract and show executable commands
                if message.role == .assistant {
                    commandButtons
                }
            }

            Spacer()
        }
        .padding(.horizontal, 12)
    }

    private var systemMessageContent: some View {
        HStack(spacing: 6) {
            Image(systemName: "terminal")
                .font(.system(size: 10))
                .foregroundStyle(.green)
            Text(message.content)
                .font(.system(size: 11, design: .monospaced))
                .foregroundStyle(.secondary)
        }
        .padding(6)
        .background(Color.green.opacity(0.1))
        .cornerRadius(4)
    }

    private func terminalContextBadge(_ context: TerminalContext) -> some View {
        HStack(spacing: 4) {
            Image(systemName: context.isError ? "xmark.circle" : "checkmark.circle")
                .font(.system(size: 10))
            Text(context.command)
                .font(.system(size: 10, design: .monospaced))
                .lineLimit(1)
        }
        .foregroundStyle(context.isError ? .red : .green)
        .padding(.horizontal, 6)
        .padding(.vertical, 3)
        .background(
            RoundedRectangle(cornerRadius: 4)
                .fill(context.isError ? Color.red.opacity(0.1) : Color.green.opacity(0.1))
        )
    }

    @ViewBuilder
    private var commandButtons: some View {
        let commands = parseCommands(from: message.content)
        if !commands.isEmpty {
            VStack(alignment: .leading, spacing: 4) {
                ForEach(commands, id: \.self) { command in
                    Button {
                        onExecuteCommand?(command)
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "play.fill")
                                .font(.system(size: 8))
                            Text("Run: \(command)")
                                .font(.system(size: 10, design: .monospaced))
                                .lineLimit(1)
                        }
                        .padding(.horizontal, 8)
                        .padding(.vertical, 4)
                        .background(Color.green.opacity(0.1))
                        .cornerRadius(4)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.top, 4)
        }
    }

    /// Simple command extraction from message content
    private func parseCommands(from content: String) -> [String] {
        var commands: [String] = []

        // Look for inline code with shell-like commands
        let inlinePattern = "`([^`]+)`"
        if let regex = try? NSRegularExpression(pattern: inlinePattern, options: []) {
            let range = NSRange(content.startIndex..., in: content)
            let matches = regex.matches(in: content, options: [], range: range)

            for match in matches {
                if let commandRange = Range(match.range(at: 1), in: content) {
                    let command = String(content[commandRange])
                    // Only include if it looks like a shell command
                    if looksLikeShellCommand(command) {
                        commands.append(command)
                    }
                }
            }
        }

        return Array(commands.prefix(3))  // Limit to 3 commands
    }

    private func looksLikeShellCommand(_ text: String) -> Bool {
        let shellPrefixes = ["cd ", "ls", "git ", "npm ", "yarn ", "pnpm ", "cargo ", "swift ",
                           "python ", "pip ", "brew ", "make", "mkdir ", "rm ", "cp ", "mv ",
                           "cat ", "echo ", "curl ", "wget ", "./", "xcodebuild"]
        return shellPrefixes.contains { text.hasPrefix($0) }
    }
}

// MARK: - Preview

#Preview {
    AIAssistantPanel(codingStore: CodingStore())
        .frame(width: 350, height: 500)
}
