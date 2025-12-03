//
//  ChatWorkspace.swift
//  MagnetarStudio (macOS)
//
//  AI Chat workspace - matches React app layout EXACTLY
//

import SwiftUI

struct ChatWorkspace: View {
    @Environment(ChatStore.self) private var chatStore
    @State private var messageInput: String = ""
    @State private var showTimeline: Bool = false

    var body: some View {
        HStack(spacing: 0) {
            // Left: Chat Sidebar (~280-320px)
            chatSidebar
                .frame(width: 300)
                .background(Color.surfaceSecondary.opacity(0.5))

            Divider()

            // Right: Chat Window
            chatWindow
        }
    }

    // MARK: - Chat Sidebar

    private var chatSidebar: some View {
        VStack(spacing: 0) {
            // Header with New Chat button
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Sessions")
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundColor(.textPrimary)

                    Text("\(chatStore.sessions.count) sessions")
                        .font(.system(size: 11))
                        .foregroundColor(.textSecondary)
                }

                Spacer()

                Button(action: {
                    Task {
                        await chatStore.createSession()
                    }
                }) {
                    Image(systemName: "plus.circle.fill")
                        .font(.system(size: 16))
                        .foregroundStyle(LinearGradient.magnetarGradient)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 12)
            .background(Color.surfaceSecondary.opacity(0.3))

            Divider()

            // Sessions list
            if chatStore.sessions.isEmpty {
                VStack(spacing: 16) {
                    Image(systemName: "bubble.left.and.bubble.right")
                        .font(.system(size: 42))
                        .foregroundColor(.secondary)

                    Text("No chat sessions")
                        .font(.headline)
                        .foregroundColor(.secondary)

                    Button(action: {
                        Task {
                            await chatStore.createSession()
                        }
                    }) {
                        HStack(spacing: 6) {
                            Image(systemName: "plus")
                            Text("Start New Chat")
                        }
                        .font(.system(size: 13, weight: .medium))
                        .padding(.horizontal, 16)
                        .padding(.vertical, 8)
                        .background(LinearGradient.magnetarGradient)
                        .foregroundColor(.white)
                        .cornerRadius(8)
                    }
                    .buttonStyle(.plain)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(spacing: 4) {
                        ForEach(chatStore.sessions) { session in
                            SessionRow(
                                session: session,
                                isSelected: chatStore.currentSession?.id == session.id
                            )
                            .onTapGesture {
                                Task {
                                    await chatStore.selectSession(session)
                                }
                            }
                            .contextMenu {
                                Button("Delete", role: .destructive) {
                                    chatStore.deleteSession(session)
                                }
                            }
                        }
                    }
                    .padding(8)
                }
            }
        }
    }

    // MARK: - Chat Window

    @ViewBuilder
    private var chatWindow: some View {
        @Bindable var store = chatStore

        VStack(spacing: 0) {
            // Header toolbar
            HStack {
                // Left: Title and message count
                VStack(alignment: .leading, spacing: 2) {
                    Text(chatStore.currentSession?.title ?? "Chat")
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundColor(.textPrimary)

                    Text("\(chatStore.messages.count) messages")
                        .font(.system(size: 11))
                        .foregroundColor(.textSecondary)
                }

                Spacer()

                // Right: Timeline button + Model selector
                HStack(spacing: 12) {
                    Button(action: {
                        showTimeline.toggle()
                    }) {
                        Image(systemName: "clock.arrow.circlepath")
                            .font(.system(size: 14))
                            .foregroundColor(showTimeline ? .magnetarPrimary : .textSecondary)
                    }
                    .buttonStyle(.plain)
                    .help("Session Timeline")

                    // Model Selector (Phase 2: Intelligent routing)
                    ModelSelectorMenu(
                        selectedMode: $store.selectedMode,
                        selectedModelId: $store.selectedModelId,
                        availableModels: chatStore.availableModels,
                        onRefresh: {
                            await chatStore.fetchModels()
                        }
                    )
                    .onChange(of: chatStore.selectedMode) { oldValue, newValue in
                        Task {
                            await chatStore.saveModelPreferences()
                        }
                    }
                    .onChange(of: chatStore.selectedModelId) { oldValue, newValue in
                        Task {
                            await chatStore.saveModelPreferences()
                        }
                    }
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color.surfaceTertiary.opacity(0.3))

            Divider()

            // Error Banner
            if let error = chatStore.error {
                HStack(spacing: 12) {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundColor(.orange)

                    VStack(alignment: .leading, spacing: 2) {
                        Text("Error")
                            .font(.system(size: 12, weight: .semibold))
                        Text(error.localizedDescription)
                            .font(.system(size: 11))
                            .foregroundColor(.secondary)
                    }

                    Spacer()

                    Button("Dismiss") {
                        chatStore.error = nil
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                }
                .padding(12)
                .background(Color.orange.opacity(0.1))
                .cornerRadius(8)
                .padding(.horizontal, 16)
                .padding(.top, 8)
            }

            // Messages area
            if chatStore.currentSession == nil {
                welcomeView
            } else if chatStore.messages.isEmpty {
                emptyMessagesView
            } else {
                messageList
            }

            Divider()

            // Input area
            inputArea
                .padding(16)
        }
        .sheet(isPresented: $showTimeline) {
            TimelineSheet(session: chatStore.currentSession)
        }
    }

    // MARK: - Welcome View

    private var welcomeView: some View {
        VStack(spacing: 20) {
            Image(systemName: "sparkles")
                .font(.system(size: 56))
                .foregroundStyle(LinearGradient.magnetarGradient)

            VStack(spacing: 8) {
                Text("Welcome to MagnetarStudio")
                    .font(.title2)
                    .fontWeight(.bold)

                Text("Click 'Start New Chat' in the sidebar or press ⌘N")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Empty Messages View

    private var emptyMessagesView: some View {
        VStack(spacing: 16) {
            Image(systemName: "text.bubble")
                .font(.system(size: 48))
                .foregroundColor(.secondary)

            VStack(spacing: 4) {
                Text("Start a conversation")
                    .font(.headline)

                Text("Ask me anything! I can help with code, answer questions, or just chat.")
                    .font(.caption)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .frame(maxWidth: 400)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Message List

    private var messageList: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 16) {
                    ForEach(chatStore.messages) { message in
                        MessageRow(message: message)
                            .id(message.id)
                    }
                }
                .padding(16)
            }
            .onChange(of: chatStore.messages.count) { _, _ in
                if let lastMessage = chatStore.messages.last {
                    withAnimation {
                        proxy.scrollTo(lastMessage.id, anchor: .bottom)
                    }
                }
            }
        }
    }

    // MARK: - Input Area

    private var inputArea: some View {
        HStack(alignment: .bottom, spacing: 12) {
            TextField("Message...", text: $messageInput, axis: .vertical)
                .textFieldStyle(.plain)
                .padding(10)
                .background(Color.surfaceSecondary)
                .cornerRadius(10)
                .lineLimit(1...8)
                .onSubmit {
                    sendMessage()
                }

            Button(action: sendMessage) {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.system(size: 28))
                    .foregroundStyle(messageInput.isEmpty ? AnyShapeStyle(Color.secondary) : AnyShapeStyle(LinearGradient.magnetarGradient))
            }
            .buttonStyle(.plain)
            .disabled(messageInput.isEmpty || chatStore.isLoading)
        }
    }

    // MARK: - Actions

    private func sendMessage() {
        let text = messageInput.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        Task {
            messageInput = ""
            await chatStore.sendMessage(text)
        }
    }
}

// MARK: - Session Row

struct SessionRow: View {
    let session: ChatSession
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 10) {
            VStack(alignment: .leading, spacing: 3) {
                Text(session.title)
                    .font(.system(size: 13, weight: .medium))
                    .lineLimit(1)
                    .foregroundColor(.textPrimary)

                // Sessions don't have fixed models - show "Multi-model" or "Intelligent"
                Text("Multi-model")
                    .font(.system(size: 11))
                    .foregroundColor(.textSecondary)
            }

            Spacer()

            if isSelected {
                Image(systemName: "checkmark.circle.fill")
                    .font(.system(size: 14))
                    .foregroundStyle(LinearGradient.magnetarGradient)
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(isSelected ? Color.magnetarPrimary.opacity(0.12) : Color.clear)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 6)
                .strokeBorder(isSelected ? Color.magnetarPrimary.opacity(0.3) : Color.clear, lineWidth: 1)
        )
    }
}

// MARK: - Message Row

struct MessageRow: View {
    let message: ChatMessage

    var body: some View {
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
                Text(message.role.displayName)
                    .font(.system(size: 11, weight: .semibold))
                    .foregroundColor(.textSecondary)

                Text(message.content)
                    .font(.system(size: 14))
                    .textSelection(.enabled)
            }

            Spacer()
        }
        .padding(12)
        .background(message.role == .user ? Color.magnetarPrimary.opacity(0.06) : Color.surfaceSecondary.opacity(0.4))
        .cornerRadius(10)
    }
}

// MARK: - Timeline Sheet

struct TimelineSheet: View {
    let session: ChatSession?
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 0) {
            timelineHeader
            Divider()
            timelineContent
        }
        .frame(width: 500, height: 600)
    }

    private var timelineHeader: some View {
        HStack {
            Text("Session Timeline")
                .font(.system(size: 18, weight: .bold))
            Spacer()
            Button("Done") {
                dismiss()
            }
            .buttonStyle(.bordered)
        }
        .padding(20)
    }

    @ViewBuilder
    private var timelineContent: some View {
        if let session = session {
            SessionTimelineDetails(session: session)
        } else {
            emptyTimelineView
        }
    }

    private var emptyTimelineView: some View {
        VStack(spacing: 16) {
            Image(systemName: "clock")
                .font(.system(size: 48))
                .foregroundColor(.secondary)
            Text("No session selected")
                .font(.headline)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

private struct SessionTimelineDetails: View {
    let session: ChatSession

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                sessionInfoCard
                if !session.messages.isEmpty {
                    messageHistoryList
                }
            }
            .padding(20)
        }
    }

    private var sessionInfoCard: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Session Details", systemImage: "info.circle")
                .font(.system(size: 14, weight: .semibold))

            InfoRow(label: "Title:", value: session.title)
            InfoRow(label: "Mode:", value: "Multi-model")  // Sessions use orchestrator per-query

            HStack {
                Text("Created:")
                    .foregroundColor(.secondary)
                Text(session.createdAt, style: .date)
                Text(session.createdAt, style: .time)
            }
            .font(.system(size: 13))

            InfoRow(label: "Messages:", value: "\(session.messages.count)")
        }
        .padding(16)
        .background(Color.surfaceSecondary.opacity(0.3))
        .cornerRadius(10)
    }

    private var messageHistoryList: some View {
        VStack(alignment: .leading, spacing: 8) {
            Label("Message History", systemImage: "clock.arrow.circlepath")
                .font(.system(size: 14, weight: .semibold))

            ForEach(Array(session.messages.enumerated()), id: \.element.id) { index, message in
                TimelineMessageRow(index: index, message: message)
            }
        }
    }
}

private struct InfoRow: View {
    let label: String
    let value: String

    var body: some View {
        HStack {
            Text(label)
                .foregroundColor(.secondary)
            Text(value)
        }
        .font(.system(size: 13))
    }
}

private struct TimelineMessageRow: View {
    let index: Int
    let message: ChatMessage

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Text("#\(index + 1)")
                .font(.system(size: 11, weight: .medium))
                .foregroundColor(.secondary)
                .frame(width: 30, alignment: .leading)

            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(message.role.displayName)
                        .font(.system(size: 12, weight: .semibold))
                    Spacer()
                    Text(message.createdAt, style: .time)
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                }

                Text(message.content)
                    .font(.system(size: 12))
                    .lineLimit(3)
                    .foregroundColor(.secondary)
            }
        }
        .padding(12)
        .background(Color.surfaceSecondary.opacity(0.2))
        .cornerRadius(8)
    }
}

// MARK: - Preview

#Preview {
    ChatWorkspace()
        .environment(ChatStore())
        .frame(width: 1200, height: 800)
}
