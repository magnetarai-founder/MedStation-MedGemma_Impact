//
//  DetachedAIWindow.swift
//  MagnetarStudio (macOS)
//
//  Floating AI assistant window accessible from any workspace via ⌘⇧A.
//  Shares ChatStore with the main app. Supports per-session model override.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "DetachedAIWindow")

struct DetachedAIWindow: View {
    @Environment(ChatStore.self) private var chatStore
    @State private var inputText = ""
    @FocusState private var isInputFocused: Bool

    var body: some View {
        VStack(spacing: 0) {
            // Header
            aiHeader

            Divider()

            // Messages
            aiMessagesArea

            Divider()

            // Input
            aiInputArea
        }
        .frame(minWidth: 500, minHeight: 400)
        .background(Color(NSColor.windowBackgroundColor))
        .onAppear {
            isInputFocused = true
        }
    }

    // MARK: - Header

    private var aiHeader: some View {
        HStack(spacing: 12) {
            Image(systemName: "sparkles")
                .font(.system(size: 18))
                .foregroundStyle(LinearGradient.magnetarGradient)

            Text("AI Assistant")
                .font(.system(size: 16, weight: .semibold))

            Spacer()

            // Session picker
            if !chatStore.sessions.isEmpty {
                Menu {
                    ForEach(chatStore.sessions.prefix(10)) { session in
                        Button {
                            Task { await chatStore.selectSession(session) }
                        } label: {
                            HStack {
                                Text(session.title)
                                if chatStore.currentSession?.id == session.id {
                                    Image(systemName: "checkmark")
                                }
                            }
                        }
                    }

                    Divider()

                    Button {
                        Task { await chatStore.createSession() }
                    } label: {
                        Label("New Session", systemImage: "plus")
                    }
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: "bubble.left.and.bubble.right")
                            .font(.system(size: 10))
                        Text(currentSessionTitle)
                            .font(.system(size: 11))
                            .lineLimit(1)
                        Image(systemName: "chevron.down")
                            .font(.system(size: 8))
                    }
                    .foregroundStyle(.secondary)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(
                        RoundedRectangle(cornerRadius: 6)
                            .fill(Color.primary.opacity(0.05))
                    )
                }
                .menuStyle(.borderlessButton)
            }

            // Model picker
            modelPicker
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color.gray.opacity(0.03))
    }

    private var currentSessionTitle: String {
        chatStore.currentSession?.title ?? "No Session"
    }

    // MARK: - Model Picker (per-session override)

    private var sessionId: UUID? {
        chatStore.currentSession?.id
    }

    private var effectiveMode: String {
        guard let id = sessionId else { return chatStore.selectedMode }
        return chatStore.effectiveModelSelection(for: id).mode
    }

    private var effectiveModelId: String? {
        guard let id = sessionId else { return chatStore.selectedModelId }
        return chatStore.effectiveModelSelection(for: id).modelId
    }

    private var modelPicker: some View {
        let hasOverride = sessionId.map { chatStore.hasModelOverride(for: $0) } ?? false

        return ModelSelectorMenu(
            selectedMode: Binding(
                get: { effectiveMode },
                set: { newMode in
                    guard let id = sessionId else {
                        chatStore.selectedMode = newMode
                        return
                    }
                    chatStore.setSessionModelOverride(sessionId: id, mode: newMode, modelId: effectiveModelId)
                }
            ),
            selectedModelId: Binding(
                get: { effectiveModelId },
                set: { newModel in
                    guard let id = sessionId else {
                        chatStore.selectedModelId = newModel
                        return
                    }
                    chatStore.setSessionModelOverride(sessionId: id, mode: "manual", modelId: newModel)
                }
            ),
            availableModels: chatStore.availableModels,
            onRefresh: {
                await chatStore.fetchModels()
            },
            hasOverride: hasOverride,
            onClearOverride: {
                guard let id = sessionId else { return }
                chatStore.clearSessionModelOverride(sessionId: id)
            }
        )
    }

    // MARK: - Messages

    private var aiMessagesArea: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 12) {
                    if chatStore.messages.isEmpty {
                        emptyStateView
                    } else {
                        ForEach(chatStore.messages) { message in
                            AIMessageRow(message: message)
                                .id(message.id)
                        }
                    }

                    if chatStore.isStreaming {
                        HStack(spacing: 8) {
                            ProgressView()
                                .scaleEffect(0.8)
                            Text("Thinking...")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .padding()
                        .id("streaming-indicator")
                    }
                }
                .padding(16)
            }
            .onChange(of: chatStore.messages.count) { _, _ in
                if let last = chatStore.messages.last {
                    withAnimation {
                        proxy.scrollTo(last.id, anchor: .bottom)
                    }
                }
            }
            .onChange(of: chatStore.isStreaming) { _, streaming in
                if streaming {
                    withAnimation {
                        proxy.scrollTo("streaming-indicator", anchor: .bottom)
                    }
                }
            }
        }
    }

    private var emptyStateView: some View {
        VStack(spacing: 16) {
            Image(systemName: "sparkles")
                .font(.system(size: 40))
                .foregroundStyle(LinearGradient.magnetarGradient)

            Text("AI Assistant")
                .font(.title2.weight(.semibold))

            Text("Ask anything — code questions, writing help,\ndata analysis, or general knowledge.")
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(.top, 60)
    }

    // MARK: - Input

    private var aiInputArea: some View {
        HStack(spacing: 12) {
            TextField("Ask anything...", text: $inputText, axis: .vertical)
                .textFieldStyle(.plain)
                .lineLimit(1...5)
                .focused($isInputFocused)
                .onSubmit {
                    if !inputText.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                        sendMessage()
                    }
                }

            Button {
                sendMessage()
            } label: {
                Image(systemName: "paperplane.fill")
                    .font(.system(size: 14))
                    .foregroundStyle(inputText.isEmpty ? .secondary : Color.accentColor)
            }
            .buttonStyle(.plain)
            .disabled(inputText.isEmpty || chatStore.isStreaming)
            .keyboardShortcut(.return, modifiers: .command)
        }
        .padding(12)
        .background(Color.gray.opacity(0.05))
    }

    // MARK: - Actions

    private func sendMessage() {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        inputText = ""
        Task {
            await chatStore.sendMessage(text)
        }
    }
}

// MARK: - AI Message Row

private struct AIMessageRow: View {
    let message: ChatMessage

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Avatar
            Circle()
                .fill(message.role == .user ? Color.accentColor.opacity(0.2) : Color.purple.opacity(0.15))
                .frame(width: 32, height: 32)
                .overlay(
                    Image(systemName: message.role == .user ? "person.fill" : "sparkles")
                        .font(.system(size: 14))
                        .foregroundStyle(message.role == .user ? Color.accentColor : .purple)
                )

            VStack(alignment: .leading, spacing: 4) {
                // Role label
                Text(message.role == .user ? "You" : "AI")
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundStyle(.secondary)

                // Content
                Text(message.content)
                    .font(.system(size: 14))
                    .textSelection(.enabled)
            }

            Spacer()
        }
        .padding(.vertical, 4)
    }
}

// MARK: - Preview

#Preview {
    DetachedAIWindow()
        .environment(ChatStore())
        .frame(width: 600, height: 700)
}
