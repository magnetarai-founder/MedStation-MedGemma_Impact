//
//  ChatWindow.swift
//  MagnetarStudio (macOS)
//
//  Chat window with messages and input - Extracted from ChatWorkspace.swift (Phase 6.17)
//

import SwiftUI

struct ChatWindow: View {
    @Bindable var chatStore: ChatStore
    @Binding var messageInput: String
    @Binding var showTimeline: Bool

    var body: some View {
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
                ChatWelcomeView()
            } else if chatStore.messages.isEmpty {
                ChatEmptyMessagesView()
            } else {
                ChatMessageList(messages: chatStore.messages)
            }

            Divider()

            // Input area
            ChatInputArea(
                messageInput: $messageInput,
                isLoading: chatStore.isLoading,
                onSend: {
                    sendMessage()
                }
            )
            .padding(16)
        }
        .sheet(isPresented: $showTimeline) {
            ChatTimelineSheet(session: chatStore.currentSession, messages: chatStore.messages)
        }
    }

    private func sendMessage() {
        let text = messageInput.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        Task {
            messageInput = ""
            await chatStore.sendMessage(text)
        }
    }
}

// MARK: - Welcome View

struct ChatWelcomeView: View {
    var body: some View {
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
}

// MARK: - Empty Messages View

struct ChatEmptyMessagesView: View {
    var body: some View {
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
}

// MARK: - Message List

struct ChatMessageList: View {
    let messages: [ChatMessage]

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 16) {
                    ForEach(messages) { message in
                        ChatMessageRow(message: message)
                            .id(message.id)
                    }
                }
                .padding(16)
            }
            .onChange(of: messages.count) { _, _ in
                if let lastMessage = messages.last {
                    withAnimation {
                        proxy.scrollTo(lastMessage.id, anchor: .bottom)
                    }
                }
            }
        }
    }
}

// MARK: - Input Area

struct ChatInputArea: View {
    @Binding var messageInput: String
    let isLoading: Bool
    let onSend: () -> Void

    var body: some View {
        HStack(alignment: .bottom, spacing: 12) {
            TextField("Message...", text: $messageInput, axis: .vertical)
                .textFieldStyle(.plain)
                .padding(10)
                .background(Color.surfaceSecondary)
                .cornerRadius(10)
                .lineLimit(1...8)
                .onSubmit {
                    onSend()
                }

            Button(action: onSend) {
                Image(systemName: "arrow.up.circle.fill")
                    .font(.system(size: 28))
                    .foregroundStyle(messageInput.isEmpty ? AnyShapeStyle(Color.secondary) : AnyShapeStyle(LinearGradient.magnetarGradient))
            }
            .buttonStyle(.plain)
            .disabled(messageInput.isEmpty || isLoading)
        }
    }
}
