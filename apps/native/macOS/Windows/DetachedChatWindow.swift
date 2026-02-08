//
//  DetachedChatWindow.swift
//  MagnetarStudio (macOS)
//
//  A standalone chat window opened from Quick Action menu
//  Creates a new chat session in a focused interface
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "DetachedChatWindow")

struct DetachedChatWindow: View {
    @Environment(ChatStore.self) private var chatStore
    @State private var sessionId: UUID?
    @State private var isCreating = true

    var body: some View {
        Group {
            if isCreating {
                creatingView
            } else if let id = sessionId,
                      let session = chatStore.sessions.first(where: { $0.id == id }) {
                ChatDetailView(chatStore: chatStore, session: session)
            } else {
                errorView
            }
        }
        .frame(minWidth: 600, minHeight: 500)
        .background(Color(NSColor.windowBackgroundColor))
        .task {
            await createNewSession()
        }
    }

    // MARK: - Creating State

    private var creatingView: some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.2)
            Text("Creating new chat...")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Error State

    private var errorView: some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 40))
                .foregroundStyle(.orange)
            Text("Could not create chat session")
                .font(.headline)
            Button("Try Again") {
                isCreating = true
                Task {
                    await createNewSession()
                }
            }
            .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Create Session

    private func createNewSession() async {
        isCreating = true
        await chatStore.createSession()

        // Get the newly created session (should be first)
        if let newSession = chatStore.sessions.first {
            sessionId = newSession.id
            logger.info("Created new detached chat session: \(newSession.id)")
        }

        isCreating = false
    }
}

// MARK: - Chat Detail View for Detached Window

private struct ChatDetailView: View {
    @Bindable var chatStore: ChatStore
    let session: ChatSession

    @State private var inputText = ""
    @FocusState private var isInputFocused: Bool

    var body: some View {
        VStack(spacing: 0) {
            // Header
            chatHeader

            Divider()

            // Messages
            messagesArea

            Divider()

            // Input
            inputArea
        }
    }

    private var chatHeader: some View {
        HStack(spacing: 12) {
            Image(systemName: "bubble.left.and.bubble.right.fill")
                .font(.system(size: 18))
                .foregroundStyle(LinearGradient.magnetarGradient)

            Text(session.title)
                .font(.system(size: 16, weight: .semibold))

            Spacer()

            // Model indicator
            Text(session.model ?? "Default")
                .font(.system(size: 11))
                .foregroundStyle(.secondary)
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(
                    RoundedRectangle(cornerRadius: 4)
                        .fill(Color.gray.opacity(0.1))
                )
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color.gray.opacity(0.03))
    }

    private var messagesArea: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(spacing: 12) {
                    ForEach(chatStore.messages) { message in
                        MessageRow(message: message)
                            .id(message.id)
                    }

                    if chatStore.isStreaming {
                        HStack {
                            ProgressView()
                                .scaleEffect(0.8)
                            Text("Thinking...")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                        .padding()
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
        }
    }

    private var inputArea: some View {
        HStack(spacing: 12) {
            TextField("Message...", text: $inputText, axis: .vertical)
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
        }
        .padding(12)
        .background(Color.gray.opacity(0.05))
        .onAppear {
            isInputFocused = true
        }
    }

    private func sendMessage() {
        let text = inputText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty else { return }

        inputText = ""
        Task {
            await chatStore.sendMessage(text)
        }
    }
}

// MARK: - Message Row

private struct MessageRow: View {
    let message: ChatMessage

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Avatar
            Circle()
                .fill(message.role == .user ? Color.accentColor.opacity(0.2) : Color.gray.opacity(0.2))
                .frame(width: 32, height: 32)
                .overlay(
                    Image(systemName: message.role == .user ? "person.fill" : "brain")
                        .font(.system(size: 14))
                        .foregroundStyle(message.role == .user ? Color.accentColor : .secondary)
                )

            VStack(alignment: .leading, spacing: 4) {
                // Role label
                Text(message.role == .user ? "You" : "Assistant")
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

#Preview {
    DetachedChatWindow()
        .environment(ChatStore())
        .frame(width: 700, height: 600)
}
