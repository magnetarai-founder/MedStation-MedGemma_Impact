//
//  ChatWorkspace.swift
//  MagnetarStudio (macOS)
//
//  AI chat interface with message list and input.
//

import SwiftUI

struct ChatWorkspace: View {
    @Environment(ChatStore.self) private var chatStore

    @State private var messageInput: String = ""

    var body: some View {
        @Bindable var store = chatStore

        ThreePaneLayout {
            // Left Pane: Session List
            sessionListPane
        } middlePane: {
            // Middle Pane: Message List
            messageListPane
        } rightPane: {
            // Right Pane: Chat Input & Model Selector
            chatDetailPane(selectedModel: $store.selectedModel)
        }
    }

    // MARK: - Left Pane: Session List

    private var sessionListPane: some View {
        VStack(spacing: 0) {
            PaneHeader(
                title: "Sessions",
                icon: "bubble.left.and.bubble.right",
                subtitle: "\(chatStore.sessions.count) conversations",
                action: {
                    Task {
                        await chatStore.createSession()
                    }
                },
                actionIcon: "plus.circle.fill"
            )

            Divider()

            // Session list
            if chatStore.sessions.isEmpty {
                PaneEmptyState(
                    icon: "bubble.left.and.bubble.right",
                    title: "No chat sessions",
                    subtitle: "Start a new conversation",
                    actionTitle: "New Chat",
                    action: {
                        Task {
                            await chatStore.createSession()
                        }
                    }
                )
            } else {
                List(chatStore.sessions, selection: Binding(
                    get: { chatStore.currentSession },
                    set: { if let session = $0 { chatStore.selectSession(session) } }
                )) { session in
                    SessionRow(
                        session: session,
                        isSelected: chatStore.currentSession?.id == session.id
                    )
                    .tag(session)
                    .contextMenu {
                        Button("Delete", role: .destructive) {
                            chatStore.deleteSession(session)
                        }
                    }
                }
                .listStyle(.sidebar)
            }
        }
    }

    // MARK: - Middle Pane: Message List

    private var messageListPane: some View {
        VStack(spacing: 0) {
            PaneHeader(
                title: chatStore.currentSession?.title ?? "Messages",
                icon: "text.bubble",
                subtitle: chatStore.currentSession != nil ? "\(chatStore.messages.count) messages" : nil
            )

            Divider()

            // Messages
            if chatStore.currentSession == nil {
                PaneEmptyState(
                    icon: "bubble.left.and.bubble.right",
                    title: "No session selected",
                    subtitle: "Select a chat session or start a new one"
                )
            } else if chatStore.messages.isEmpty {
                PaneEmptyState(
                    icon: "text.bubble",
                    title: "No messages yet",
                    subtitle: "Start typing in the input area on the right"
                )
            } else {
                messageList
            }
        }
    }

    // MARK: - Right Pane: Chat Detail

    @ViewBuilder
    private func chatDetailPane(selectedModel: Binding<String>) -> some View {
        VStack(spacing: 0) {
            // Model selector header
            modelSelectorView(selectedModel: selectedModel)
                .frame(height: 44)
                .padding(.horizontal, 16)
                .background(Color.surfaceTertiary.opacity(0.3))

            Divider()

            // Selected message detail (or welcome view)
            if chatStore.currentSession == nil {
                welcomeView
            } else {
                // Chat input area
                VStack(spacing: 0) {
                    Spacer()

                    Divider()

                    inputArea
                        .padding()
                }
            }
        }
    }

    // MARK: - Model Selector

    @ViewBuilder
    private func modelSelectorView(selectedModel: Binding<String>) -> some View {
        HStack {
            Image(systemName: "cpu")
                .foregroundColor(.secondary)

            Picker("Model", selection: selectedModel) {
                Text("Mistral").tag("mistral")
                Text("Llama 2").tag("llama2")
                Text("CodeLlama").tag("codellama")
                Text("Neural Chat").tag("neural-chat")
            }
            .pickerStyle(.menu)
            .frame(width: 200)

            Spacer()

            if chatStore.isStreaming {
                HStack(spacing: 8) {
                    ProgressView()
                        .scaleEffect(0.7)
                    Text("Thinking...")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
            }
        }
    }

    // MARK: - Welcome View

    private var welcomeView: some View {
        VStack(spacing: 24) {
            Image(systemName: "sparkles")
                .font(.system(size: 64))
                .foregroundStyle(LinearGradient.magnetarGradient)

            VStack(spacing: 8) {
                Text("Welcome to MagnetarStudio")
                    .font(.largeTitle)
                    .fontWeight(.bold)

                Text("Click 'Start New Chat' in the sidebar or press ⌘N")
                    .font(.title3)
                    .foregroundColor(.secondary)
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Empty State

    private var emptyStateView: some View {
        VStack(spacing: 24) {
            Image(systemName: "text.bubble")
                .font(.system(size: 48))
                .foregroundColor(.secondary)

            Text("No messages yet")
                .font(.headline)
                .foregroundColor(.secondary)

            Text("Type a message below to start the conversation")
                .font(.caption)
                .foregroundColor(.textTertiary)
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
                .padding()
            }
            .onChange(of: chatStore.messages.count) { _, _ in
                // Auto-scroll to bottom on new message
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
            // Text input
            TextField("Message...", text: $messageInput, axis: .vertical)
                .textFieldStyle(.plain)
                .padding(12)
                .background(Color.surfaceSecondary)
                .cornerRadius(12)
                .lineLimit(1...10)
                .onSubmit {
                    sendMessage()
                }

            // Send button
            Button {
                sendMessage()
            } label: {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.system(size: 32))
                    .foregroundStyle(messageInput.isEmpty ? Color.secondary : Color.magnetarPrimary)
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
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text(session.title)
                    .font(.headline)
                    .lineLimit(1)

                Text(session.model)
                    .font(.caption)
                    .foregroundColor(.secondary)
            }

            Spacer()

            if isSelected {
                Image(systemName: "checkmark.circle.fill")
                    .foregroundStyle(LinearGradient.magnetarGradient)
            }
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(isSelected ? Color.magnetarPrimary.opacity(0.1) : Color.clear)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(isSelected ? Color.magnetarPrimary.opacity(0.3) : Color.clear, lineWidth: 1)
        )
    }
}

// MARK: - Message Row

struct MessageRow: View {
    let message: ChatMessage

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Avatar
            avatarView
                .frame(width: 32, height: 32)

            // Message content
            VStack(alignment: .leading, spacing: 4) {
                Text(message.role.displayName)
                    .font(.caption)
                    .fontWeight(.semibold)
                    .foregroundColor(.secondary)

                Text(message.content)
                    .font(.body)
                    .textSelection(.enabled)
            }

            Spacer()
        }
        .padding()
        .background(messageBackground)
        .cornerRadius(12)
    }

    @ViewBuilder
    private var avatarView: some View {
        if message.role == .user {
            Circle()
                .fill(LinearGradient.magnetarGradient)
                .overlay(
                    Image(systemName: "person.fill")
                        .font(.caption)
                        .foregroundColor(.white)
                )
        } else {
            Circle()
                .fill(Color.surfaceTertiary)
                .overlay(
                    Image(systemName: "sparkles")
                        .font(.caption)
                        .foregroundStyle(LinearGradient.magnetarGradient)
                )
        }
    }

    private var messageBackground: some View {
        Group {
            if message.role == .user {
                Color.magnetarPrimary.opacity(0.05)
            } else {
                Color.surfaceSecondary.opacity(0.5)
            }
        }
    }
}

// MARK: - Preview

#Preview {
    ChatWorkspace()
        .environment(ChatStore())
        .frame(width: 1200, height: 800)
}
