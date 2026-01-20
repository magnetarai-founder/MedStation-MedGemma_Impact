//
//  ChatSidebar.swift
//  MagnetarStudio (macOS)
//
//  Chat sidebar with sessions list - Extracted from ChatWorkspace.swift (Phase 6.17)
//

import SwiftUI

struct ChatSidebar: View {
    @Bindable var chatStore: ChatStore
    @State private var sessionToRename: ChatSession?
    @State private var renameText = ""

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
                            .contentShape(Rectangle())  // Makes entire row clickable
                            .onTapGesture {
                                Task {
                                    await chatStore.selectSession(session)
                                }
                            }
                            .contextMenu {
                                Button {
                                    renameText = session.title
                                    sessionToRename = session
                                } label: {
                                    Label("Rename", systemImage: "pencil")
                                }

                                Button {
                                    // Archive functionality - placeholder
                                    // Could move to an "archived" state
                                } label: {
                                    Label("Archive", systemImage: "archivebox")
                                }

                                Divider()

                                Button(role: .destructive) {
                                    chatStore.deleteSession(session)
                                } label: {
                                    Label("Delete", systemImage: "trash")
                                }
                            }
                        }
                    }
                    .padding(8)
                }
            }
        }
        .sheet(item: $sessionToRename) { session in
            RenameSessionSheet(
                session: session,
                renameText: $renameText,
                onRename: { newTitle in
                    Task {
                        await chatStore.renameSession(session, to: newTitle)
                    }
                    sessionToRename = nil
                },
                onCancel: {
                    sessionToRename = nil
                }
            )
        }
    }
}

// MARK: - Rename Sheet

struct RenameSessionSheet: View {
    let session: ChatSession
    @Binding var renameText: String
    let onRename: (String) -> Void
    let onCancel: () -> Void

    var body: some View {
        VStack(spacing: 16) {
            Text("Rename Chat")
                .font(.headline)

            TextField("Chat name", text: $renameText)
                .textFieldStyle(.roundedBorder)
                .frame(width: 250)

            HStack(spacing: 12) {
                Button("Cancel") {
                    onCancel()
                }
                .buttonStyle(.bordered)

                Button("Rename") {
                    onRename(renameText)
                }
                .buttonStyle(.borderedProminent)
                .disabled(renameText.trimmingCharacters(in: .whitespaces).isEmpty)
            }
        }
        .padding(20)
        .frame(width: 300)
    }
}
