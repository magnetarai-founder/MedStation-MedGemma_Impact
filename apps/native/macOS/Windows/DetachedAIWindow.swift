//
//  DetachedAIWindow.swift
//  MagnetarStudio (macOS)
//
//  Floating AI assistant window with workspace context tabs.
//  Global model picker + per-tab model override + per-session override.
//  Accessible via ⇧⌘P or sparkles button in header.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "DetachedAIWindow")

struct DetachedAIWindow: View {
    @Environment(ChatStore.self) private var chatStore
    @State private var inputText = ""
    @State private var activeContext: WorkspaceAIContext = .general
    @FocusState private var isInputFocused: Bool

    var body: some View {
        VStack(spacing: 0) {
            // Global header with app-wide model picker
            globalHeader

            Divider()

            // Workspace context tab bar
            contextTabBar

            Divider()

            // Per-tab sub-header: tab model picker + session switcher
            tabSubHeader

            Divider()

            // Messages
            aiMessagesArea

            Divider()

            // Input
            aiInputArea
        }
        .frame(minWidth: 550, minHeight: 500)
        .background(Color(NSColor.windowBackgroundColor))
        .onAppear {
            isInputFocused = true
        }
        .onChange(of: activeContext) { _, newContext in
            let contextSessions = chatStore.sessionsForContext(newContext)
            // Auto-select most recent session for the new context
            if let currentId = chatStore.currentSession?.id,
               contextSessions.contains(where: { $0.id == currentId }) {
                // Current session already belongs to this context — keep it
                return
            }
            if let mostRecent = contextSessions.first {
                Task { await chatStore.selectSession(mostRecent) }
            }
        }
    }

    // MARK: - Global Header

    private var globalHeader: some View {
        HStack(spacing: 12) {
            Image(systemName: "sparkles")
                .font(.system(size: 18))
                .foregroundStyle(LinearGradient.magnetarGradient)

            Text("AI Assistant")
                .font(.system(size: 16, weight: .semibold))

            Spacer()

            // Global model picker (sets app-wide default)
            Text("Global")
                .font(.system(size: 10))
                .foregroundStyle(.tertiary)

            ModelSelectorMenu(
                selectedMode: Binding(
                    get: { chatStore.selectedMode },
                    set: { chatStore.selectedMode = $0 }
                ),
                selectedModelId: Binding(
                    get: { chatStore.selectedModelId },
                    set: { chatStore.selectedModelId = $0 }
                ),
                availableModels: chatStore.availableModels,
                onRefresh: { await chatStore.fetchModels() }
            )
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color.gray.opacity(0.03))
    }

    // MARK: - Context Tab Bar

    private var contextTabBar: some View {
        HStack(spacing: 0) {
            ForEach(WorkspaceAIContext.allCases) { context in
                Button {
                    withAnimation(.easeInOut(duration: 0.15)) {
                        activeContext = context
                    }
                } label: {
                    VStack(spacing: 3) {
                        Image(systemName: context.icon)
                            .font(.system(size: 13))
                        Text(context.displayName)
                            .font(.system(size: 10, weight: .medium))
                    }
                    .foregroundStyle(activeContext == context ? .primary : .secondary)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 8)
                    .background(
                        activeContext == context
                            ? Color.accentColor.opacity(0.1)
                            : Color.clear
                    )
                    .overlay(alignment: .bottom) {
                        if activeContext == context {
                            Rectangle()
                                .fill(Color.accentColor)
                                .frame(height: 2)
                        }
                    }
                }
                .buttonStyle(.plain)
            }
        }
        .background(Color.gray.opacity(0.02))
    }

    // MARK: - Tab Sub-Header

    private var tabSubHeader: some View {
        HStack(spacing: 12) {
            // Per-tab model picker
            tabModelPicker

            Spacer()

            // Session switcher for this context
            sessionPicker
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .background(Color.gray.opacity(0.02))
    }

    private var tabModelPicker: some View {
        let hasOverride = chatStore.hasWorkspaceModelOverride(for: activeContext)
        let selection = chatStore.workspaceModelSelection(for: activeContext)

        return HStack(spacing: 6) {
            Text(activeContext.displayName)
                .font(.system(size: 11, weight: .medium))
                .foregroundStyle(.secondary)

            ModelSelectorMenu(
                selectedMode: Binding(
                    get: { selection.mode },
                    set: { newMode in
                        chatStore.setWorkspaceModelOverride(
                            context: activeContext,
                            mode: newMode,
                            modelId: selection.modelId
                        )
                    }
                ),
                selectedModelId: Binding(
                    get: { selection.modelId },
                    set: { newModel in
                        chatStore.setWorkspaceModelOverride(
                            context: activeContext,
                            mode: "manual",
                            modelId: newModel
                        )
                    }
                ),
                availableModels: chatStore.availableModels,
                onRefresh: { await chatStore.fetchModels() },
                hasOverride: hasOverride,
                onClearOverride: {
                    chatStore.clearWorkspaceModelOverride(context: activeContext)
                }
            )
        }
    }

    private var sessionPicker: some View {
        let contextSessions = chatStore.sessionsForContext(activeContext)

        return Menu {
            ForEach(contextSessions.prefix(15)) { session in
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

            if !contextSessions.isEmpty {
                Divider()
            }

            Button {
                Task {
                    await chatStore.createSession()
                    if let newSession = chatStore.currentSession {
                        chatStore.tagSession(newSession.id, withContext: activeContext)
                    }
                }
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

    private var currentSessionTitle: String {
        chatStore.currentSession?.title ?? "No Session"
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
            Image(systemName: activeContext.icon)
                .font(.system(size: 40))
                .foregroundStyle(LinearGradient.magnetarGradient)

            Text("\(activeContext.displayName) Assistant")
                .font(.title2.weight(.semibold))

            Text(emptyStateDescription)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(.top, 60)
    }

    private var emptyStateDescription: String {
        switch activeContext {
        case .code:
            return "Ask about code, debugging, architecture,\nor get help writing implementations."
        case .writing:
            return "Get help with writing, editing, formatting,\nor brainstorming content ideas."
        case .sheets:
            return "Ask about formulas, data analysis,\nor get help with spreadsheet tasks."
        case .voice:
            return "Get help with transcriptions, summaries,\nor voice content analysis."
        case .general:
            return "Ask anything — code questions, writing help,\ndata analysis, or general knowledge."
        case .medical:
            return "Ask about symptoms, triage, differential diagnosis,\nor get evidence-based medical information."
        }
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

        // Auto-tag session to current context if not already tagged
        if let sessionId = chatStore.currentSession?.id {
            chatStore.tagSession(sessionId, withContext: activeContext)
        }

        inputText = ""
        Task {
            await chatStore.sendMessage(text, contextPrompt: activeContext.systemPromptPrefix)
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
        .frame(width: 650, height: 750)
}
