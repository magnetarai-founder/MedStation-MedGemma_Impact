//
//  ChatWorkspace.swift
//  MagnetarStudio (macOS)
//
//  AI Chat workspace - matches React app layout EXACTLY
//  Refactored in Phase 6.17 - extracted sidebar, window, and components
//

import SwiftUI

struct ChatWorkspace: View {
    @Environment(ChatStore.self) private var chatStore
    @State private var messageInput: String = ""
    @State private var showTimeline: Bool = false

    var body: some View {
        HStack(spacing: 0) {
            // Left: Chat Sidebar (~280-320px)
            ChatSidebar(chatStore: chatStore)
                .frame(width: 300)
                .background(Color.surfaceSecondary.opacity(0.5))

            Divider()

            // Right: Chat Window
            ChatWindow(
                chatStore: chatStore,
                messageInput: $messageInput,
                showTimeline: $showTimeline
            )
        }
        .onAppear {
            // Refresh sessions when navigating to chat workspace
            // This handles cases where auth completes after initial load
            if chatStore.sessions.isEmpty {
                Task {
                    await chatStore.loadSessions()
                }
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
