//
//  ChatSidebar.swift
//  MagnetarStudio (macOS)
//
//  Chat sidebar with sessions list - Extracted from ChatWorkspace.swift (Phase 6.17)
//

import SwiftUI

struct ChatSidebar: View {
    @Bindable var chatStore: ChatStore

    var body: some View {
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
            if chatStore.isLoadingSessions {
                // Show loading indicator while sessions are being fetched
                VStack(spacing: 16) {
                    ProgressView()
                        .scaleEffect(1.2)

                    Text("Loading sessions...")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if chatStore.sessions.isEmpty {
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
                            ChatSessionRow(
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
}
