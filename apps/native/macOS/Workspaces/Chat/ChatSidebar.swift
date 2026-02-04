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

    /// Count of sessions in each filter category for badges
    private var activeBadge: Int { chatStore.sessions.filter { $0.status == .active }.count }
    private var archivedBadge: Int { chatStore.sessions.filter { $0.status == .archived }.count }
    private var deletedBadge: Int { chatStore.sessions.filter { $0.status == .deleted }.count }

    var body: some View {
        VStack(spacing: 0) {
            // Header - macOS 26 Messages style
            HStack(spacing: 8) {
                // Title shows current filter
                VStack(alignment: .leading, spacing: 2) {
                    Text(chatStore.selectedFilter.displayName)
                        .font(.system(size: 16, weight: .semibold))
                        .foregroundColor(.textPrimary)

                    if chatStore.isLoadingSessions {
                        Text("Loading...")
                            .font(.system(size: 11))
                            .foregroundColor(.textSecondary)
                    } else {
                        Text("\(chatStore.filteredSessions.count) conversation\(chatStore.filteredSessions.count == 1 ? "" : "s")")
                            .font(.system(size: 11))
                            .foregroundColor(.textSecondary)
                    }
                }

                Spacer()

                // New Chat button (only in active view)
                if chatStore.selectedFilter == .active {
                    Button(action: {
                        Task {
                            await chatStore.createSession()
                        }
                    }) {
                        Image(systemName: "square.and.pencil")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(.textSecondary)
                    }
                    .buttonStyle(.plain)
                    .help("New Chat")
                }

                // Filter dropdown button - macOS 26 Messages style
                Menu {
                    // All Messages / Active
                    Button {
                        chatStore.selectedFilter = .active
                    } label: {
                        HStack {
                            Label("All Messages", systemImage: "bubble.left.and.bubble.right")
                            Spacer()
                            if activeBadge > 0 {
                                Text("\(activeBadge)")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            if chatStore.selectedFilter == .active {
                                Image(systemName: "checkmark")
                            }
                        }
                    }

                    Divider()

                    // Archived
                    Button {
                        chatStore.selectedFilter = .archived
                    } label: {
                        HStack {
                            Label("Archived", systemImage: "archivebox")
                            Spacer()
                            if archivedBadge > 0 {
                                Text("\(archivedBadge)")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            if chatStore.selectedFilter == .archived {
                                Image(systemName: "checkmark")
                            }
                        }
                    }

                    // Recently Deleted
                    Button {
                        chatStore.selectedFilter = .deleted
                    } label: {
                        HStack {
                            Label("Recently Deleted", systemImage: "trash")
                            Spacer()
                            if deletedBadge > 0 {
                                Text("\(deletedBadge)")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                            }
                            if chatStore.selectedFilter == .deleted {
                                Image(systemName: "checkmark")
                            }
                        }
                    }

                    // Empty Trash option when viewing deleted
                    if chatStore.selectedFilter == .deleted && deletedBadge > 0 {
                        Divider()

                        Button(role: .destructive) {
                            chatStore.emptyTrash()
                        } label: {
                            Label("Empty Trash", systemImage: "trash.slash")
                        }
                    }
                } label: {
                    // Filter button with badge indicator
                    ZStack(alignment: .topTrailing) {
                        Image(systemName: "line.3.horizontal.decrease")
                            .font(.system(size: 14, weight: .medium))
                            .foregroundColor(.textSecondary)

                        // Show badge if non-active filters have items
                        if chatStore.selectedFilter == .active && (archivedBadge > 0 || deletedBadge > 0) {
                            Circle()
                                .fill(Color.blue)
                                .frame(width: 6, height: 6)
                                .offset(x: 2, y: -2)
                        }
                    }
                }
                .menuStyle(.borderlessButton)
                .fixedSize()
                .help("Filter Messages")
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 12)
            .background(Color.surfaceTertiary.opacity(0.3))

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
            } else if chatStore.filteredSessions.isEmpty {
                VStack(spacing: 16) {
                    Image(systemName: chatStore.selectedFilter.icon)
                        .font(.system(size: 42))
                        .foregroundColor(.secondary)

                    Text(emptyStateMessage)
                        .font(.headline)
                        .foregroundColor(.secondary)

                    if chatStore.selectedFilter == .active {
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
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(spacing: 4) {
                        ForEach(chatStore.filteredSessions) { session in
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
                                contextMenuItems(for: session)
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

    // MARK: - Helpers

    private var emptyStateMessage: String {
        switch chatStore.selectedFilter {
        case .active:
            return "No Messages"
        case .archived:
            return "No Archived Messages"
        case .deleted:
            return "No Recently Deleted Messages"
        }
    }

    @ViewBuilder
    private func contextMenuItems(for session: ChatSession) -> some View {
        switch chatStore.selectedFilter {
        case .active:
            // Active sessions: Rename, Archive, Delete
            Button {
                renameText = session.title
                sessionToRename = session
            } label: {
                Label("Rename", systemImage: "pencil")
            }

            Button {
                chatStore.archiveSession(session)
            } label: {
                Label("Archive", systemImage: "archivebox")
            }

            Divider()

            Button(role: .destructive) {
                chatStore.moveToTrash(session)
            } label: {
                Label("Delete", systemImage: "trash")
            }

        case .archived:
            // Archived sessions: Restore, Delete
            Button {
                chatStore.restoreSession(session)
            } label: {
                Label("Restore", systemImage: "arrow.uturn.backward")
            }

            Divider()

            Button(role: .destructive) {
                chatStore.moveToTrash(session)
            } label: {
                Label("Delete", systemImage: "trash")
            }

        case .deleted:
            // Deleted sessions: Restore, Permanent Delete
            Button {
                chatStore.restoreSession(session)
            } label: {
                Label("Restore", systemImage: "arrow.uturn.backward")
            }

            Divider()

            Button(role: .destructive) {
                chatStore.permanentlyDeleteSession(session)
            } label: {
                Label("Delete Permanently", systemImage: "trash.slash")
            }
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
