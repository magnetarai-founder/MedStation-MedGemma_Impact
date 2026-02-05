//
//  TeamChatComponents.swift
//  MagnetarStudio (macOS)
//
//  Team chat UI components - Extracted from TeamWorkspace.swift
//  Enhanced with hover actions, copy feedback, and visual polish
//

import SwiftUI
import Foundation
import AppKit
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "TeamChatComponents")

// MARK: - TeamChat Main View

struct TeamChatView: View {
    let mode: NetworkMode
    @State private var sidebarWidth: CGFloat = 320
    @State private var activeChannel: TeamChannel?
    @State private var showNewChannelDialog = false
    @State private var showPeerDiscovery = false
    @State private var showFileSharing = false
    @State private var p2pStatus: P2PStatus = .connecting
    @State private var p2pNetworkStatus: P2PNetworkStatus? = nil

    var body: some View {
        VStack(spacing: 0) {
            // P2P Banner (only in p2p mode)
            if mode == .p2p {
                p2pBanner
            }

            // Resizable split: Sidebar + Chat Window
            GeometryReader { geometry in
                HStack(spacing: 0) {
                    // Left: TeamChat Sidebar
                    TeamChatSidebar(
                        activeChannel: $activeChannel,
                        onNewChannel: { showNewChannelDialog = true }
                    )
                    .frame(width: min(max(sidebarWidth, 280), geometry.size.width * 0.5))

                    Divider()

                    // Right: Chat Window
                    TeamChatWindow(
                        activeChannel: activeChannel,
                        mode: mode
                    )
                }
            }
        }
        .sheet(isPresented: $showNewChannelDialog) {
            NewChannelDialog(isPresented: $showNewChannelDialog)
        }
        .sheet(isPresented: $showPeerDiscovery) {
            PeerDiscoveryPanel()
        }
        .sheet(isPresented: $showFileSharing) {
            FileSharingPanel()
        }
        .task {
            if mode == .p2p {
                await loadP2PStatus()
            }
        }
    }

    // MARK: - Data Loading

    private func loadP2PStatus() async {
        do {
            p2pNetworkStatus = try await TeamService.shared.getP2PNetworkStatus()
            p2pStatus = p2pNetworkStatus?.isConnected == true ? .connected : .disconnected
        } catch {
            p2pStatus = .disconnected
            logger.error("Failed to load P2P status: \(error.localizedDescription)")
        }
    }

    // MARK: - P2P Banner
    // Extracted to TeamChatP2PBanner.swift (Phase 6.13)

    private var p2pBanner: some View {
        TeamChatP2PBanner(
            p2pStatus: p2pStatus,
            p2pNetworkStatus: p2pNetworkStatus,
            onShowPeerDiscovery: { showPeerDiscovery = true },
            onShowFileSharing: { showFileSharing = true }
        )
    }
}

// MARK: - TeamChat Sidebar

struct TeamChatSidebar: View {
    @Binding var activeChannel: TeamChannel?
    let onNewChannel: () -> Void

    @State private var publicChannels: [TeamChannel] = TeamChannel.defaultPublic
    @State private var privateChannels: [TeamChannel] = []
    @State private var directMessages: [TeamChannel] = []

    var body: some View {
        VStack(spacing: 0) {
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    // Public channels section
                    sectionHeader(title: "CHANNELS", onAdd: onNewChannel)

                    ForEach(publicChannels) { channel in
                        channelRow(channel: channel, isActive: activeChannel?.id == channel.id)
                            .onTapGesture {
                                activeChannel = channel
                            }
                    }

                    addChannelRow

                    // Private section
                    sectionHeader(title: "PRIVATE", onAdd: onNewChannel)

                    if privateChannels.isEmpty {
                        emptyState(text: "No private channels")
                    } else {
                        ForEach(privateChannels) { channel in
                            channelRow(channel: channel, isActive: activeChannel?.id == channel.id, isPrivate: true)
                                .onTapGesture {
                                    activeChannel = channel
                                }
                        }
                    }

                    // Direct messages
                    sectionHeader(title: "DIRECT MESSAGES", onAdd: nil)

                    if directMessages.isEmpty {
                        emptyState(text: "No direct messages")
                    }

                    // Team chats
                    sectionHeader(title: "TEAM CHATS", onAdd: nil)

                    emptyState(text: "No team chats yet")
                }
                .padding(.horizontal, 8)
                .padding(.top, 16)
                .padding(.bottom, 8)
            }
        }
        .task {
            await loadChannels()
        }
    }

    private func loadChannels() async {
        do {
            let allChannels = try await TeamService.shared.listChannels()

            // Separate into public, private, and DM channels
            publicChannels = allChannels.filter { $0.type == "public" }
            privateChannels = allChannels.filter { $0.type == "private" }
            directMessages = allChannels.filter { $0.type == "direct" }
        } catch {
            // P2P should be initialized on startup, so log real errors
            logger.error("Error loading channels: \(error.localizedDescription)")
            // Keep default channels on error
        }
    }

    // Extracted to TeamChatSectionHeader.swift and TeamChatChannelRow.swift (Phase 6.13)

    private func sectionHeader(title: String, onAdd: (() -> Void)?) -> some View {
        TeamChatSectionHeader(title: title, onAdd: onAdd)
    }

    private func channelRow(channel: TeamChannel, isActive: Bool, isPrivate: Bool = false) -> some View {
        TeamChatChannelRow(channel: channel, isActive: isActive, isPrivate: isPrivate)
    }

    private var addChannelRow: some View {
        Button(action: onNewChannel) {
            HStack(spacing: 8) {
                Image(systemName: "plus")
                    .font(.system(size: 16))
                    .foregroundColor(.secondary)

                Text("Add channel")
                    .font(.system(size: 14))
                    .foregroundColor(.secondary)

                Spacer()
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
        }
        .buttonStyle(.plain)
    }

    private func emptyState(text: String) -> some View {
        Text(text)
            .font(.system(size: 12))
            .foregroundColor(.secondary)
            .frame(maxWidth: .infinity)
            .padding(.vertical, 8)
    }
}

// MARK: - TeamChat Window

struct TeamChatWindow: View {
    let activeChannel: TeamChannel?
    let mode: NetworkMode

    @State private var messageInput: String = ""
    @State private var messages: [TeamMessage] = []
    @State private var isLoadingMessages = false
    @State private var errorMessage: String? = nil

    var body: some View {
        Group {
            if let channel = activeChannel {
                VStack(spacing: 0) {
                    // Header - Extracted to TeamChatWindowHeader.swift (Phase 6.13)
                    TeamChatWindowHeader(channel: channel)

                    // Error banner
                    if let error = errorMessage {
                        HStack(spacing: 12) {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .foregroundColor(.orange)

                            Text(error)
                                .font(.system(size: 13))
                                .foregroundColor(.primary)

                            Spacer()

                            Button {
                                errorMessage = nil
                            } label: {
                                Image(systemName: "xmark.circle.fill")
                                    .foregroundColor(.secondary)
                            }
                            .buttonStyle(.plain)
                        }
                        .padding(.horizontal, 16)
                        .padding(.vertical, 12)
                        .background(Color.orange.opacity(0.1))
                        .overlay(
                            Rectangle()
                                .fill(Color.orange.opacity(0.3))
                                .frame(height: 1),
                            alignment: .bottom
                        )
                    }

                    // Messages area
                    ScrollView {
                        if isLoadingMessages {
                            ProgressView()
                                .padding()
                        } else if messages.isEmpty {
                            VStack(spacing: 12) {
                                Image(systemName: "message")
                                    .font(.system(size: 48))
                                    .foregroundColor(.secondary.opacity(0.5))
                                Text("No messages yet")
                                    .font(.system(size: 16))
                                    .foregroundColor(.secondary)
                                Text("Start the conversation!")
                                    .font(.system(size: 13))
                                    .foregroundColor(.secondary.opacity(0.7))
                            }
                            .frame(maxWidth: .infinity, maxHeight: .infinity)
                        } else {
                            VStack(spacing: 16) {
                                ForEach(messages) { message in
                                    TeamMessageRow(message: message)
                                }
                            }
                            .padding(16)
                        }
                    }
                    .onChange(of: activeChannel?.id) {
                        loadMessages()
                    }
                    .onAppear {
                        loadMessages()
                    }

                    // Message input - Extracted to TeamChatMessageInput.swift (Phase 6.13)
                    TeamChatMessageInput(messageInput: $messageInput, onSend: sendMessage)
                }
            } else {
                emptyState
            }
        }
    }

    private func loadMessages() {
        guard let channel = activeChannel else {
            messages = []
            return
        }

        isLoadingMessages = true

        Task {
            do {
                let response = try await TeamService.shared.getMessages(channelId: channel.id)
                await MainActor.run {
                    messages = response.messages
                    isLoadingMessages = false
                    errorMessage = nil
                }
            } catch {
                // P2P should be initialized on startup, so log real errors
                logger.error("Error loading messages: \(error.localizedDescription)")
                await MainActor.run {
                    messages = []
                    isLoadingMessages = false
                    errorMessage = "Failed to load messages: \(error.localizedDescription)"
                }
            }
        }
    }

    private func sendMessage() {
        guard let channel = activeChannel else { return }
        guard !messageInput.isEmpty else { return }

        let message = messageInput
        messageInput = "" // Clear input immediately

        Task {
            do {
                let sentMessage = try await TeamService.shared.sendMessage(
                    channelId: channel.id,
                    content: message
                )

                await MainActor.run {
                    // Add the new message to the list
                    messages.append(sentMessage)
                    errorMessage = nil
                }
            } catch {
                logger.error("Failed to send message: \(error.localizedDescription)")
                await MainActor.run {
                    errorMessage = "Failed to send message: \(error.localizedDescription)"
                }
            }
        }
    }

    private var emptyState: some View {
        VStack(spacing: 16) {
            ZStack {
                RoundedRectangle(cornerRadius: 20)
                    .fill(Color.gray.opacity(0.1))
                    .frame(width: 80, height: 80)

                Image(systemName: "number")
                    .font(.system(size: 40))
                    .foregroundColor(.secondary)
            }

            Text("No channel selected")
                .font(.system(size: 20, weight: .semibold))

            Text("Select a channel from the sidebar to start chatting")
                .font(.system(size: 14))
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct TeamMessageRow: View {
    let message: TeamMessage
    var onReply: (() -> Void)? = nil
    var onReact: (() -> Void)? = nil
    var onCopy: (() -> Void)? = nil

    @State private var isHovered = false
    @State private var showCopied = false
    @State private var copyResetTask: Task<Void, Never>?

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            // Avatar
            Circle()
                .fill(LinearGradient.magnetarGradient)
                .frame(width: 36, height: 36)
                .overlay(
                    Text(String(message.senderName.prefix(2)).uppercased())
                        .font(.system(size: 12, weight: .bold))
                        .foregroundColor(.white)
                )

            VStack(alignment: .leading, spacing: 4) {
                // Header: name, timestamp, encryption badge
                HStack(spacing: 8) {
                    Text(message.senderName)
                        .font(.system(size: 14, weight: .semibold))

                    Text(formatTimestamp(message.timestamp))
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)

                    if message.encrypted {
                        HStack(spacing: 2) {
                            Image(systemName: "lock.fill")
                                .font(.system(size: 9))
                            Text("E2E")
                                .font(.system(size: 9, weight: .medium))
                        }
                        .foregroundColor(.green)
                        .padding(.horizontal, 5)
                        .padding(.vertical, 2)
                        .background(Color.green.opacity(0.1))
                        .clipShape(Capsule())
                    }

                    Spacer()

                    // Hover actions
                    if isHovered {
                        HStack(spacing: 4) {
                            MessageActionButton(icon: "face.smiling", help: "Add reaction") {
                                onReact?()
                            }
                            MessageActionButton(icon: "arrowshape.turn.up.left", help: "Reply") {
                                onReply?()
                            }
                            MessageActionButton(icon: showCopied ? "checkmark" : "doc.on.doc", help: "Copy", isSuccess: showCopied) {
                                copyMessage()
                            }
                        }
                        .transition(.opacity.combined(with: .scale(scale: 0.95)))
                    }
                }

                // Message content
                Text(message.content)
                    .font(.system(size: 14))
                    .foregroundColor(.primary)
                    .textSelection(.enabled)

                // Edited indicator
                if message.editedAt != nil {
                    Text("(edited)")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary.opacity(0.7))
                        .italic()
                }
            }
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 6)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(isHovered ? Color.gray.opacity(0.05) : Color.clear)
        )
        .contentShape(Rectangle())
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.1)) {
                isHovered = hovering
            }
        }
    }

    private func copyMessage() {
        NSPasteboard.general.clearContents()
        NSPasteboard.general.setString(message.content, forType: .string)
        onCopy?()

        withAnimation { showCopied = true }
        copyResetTask?.cancel()
        copyResetTask = Task {
            try? await Task.sleep(for: .seconds(1.5))
            guard !Task.isCancelled else { return }
            withAnimation { showCopied = false }
        }
    }

    private func formatTimestamp(_ timestamp: String) -> String {
        let formatter = ISO8601DateFormatter()
        guard let date = formatter.date(from: timestamp) else {
            return timestamp
        }

        let relativeFormatter = RelativeDateTimeFormatter()
        relativeFormatter.unitsStyle = .short
        return relativeFormatter.localizedString(for: date, relativeTo: Date())
    }
}

// MARK: - Message Action Button

private struct MessageActionButton: View {
    let icon: String
    let help: String
    var isSuccess: Bool = false
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 12))
                .foregroundColor(isSuccess ? .green : (isHovered ? .primary : .secondary))
                .frame(width: 26, height: 26)
                .background(
                    RoundedRectangle(cornerRadius: 6)
                        .fill(isSuccess ? Color.green.opacity(0.1) : (isHovered ? Color.gray.opacity(0.15) : Color.gray.opacity(0.08)))
                )
        }
        .buttonStyle(.plain)
        .help(help)
        .onHover { hovering in
            isHovered = hovering
        }
    }
}

// MARK: - Supporting Types

enum P2PStatus {
    case connecting
    case disconnected
    case connected
}

// MARK: - TeamChannel Extension for Defaults

extension TeamChannel {
    // Mock defaults for preview/testing
    static let defaultPublic = [
        TeamChannel(
            id: "ch_general",
            name: "general",
            type: "public",
            createdAt: "",
            createdBy: "",
            members: [],
            admins: [],
            description: nil,
            topic: nil,
            pinnedMessages: [],
            dmParticipants: nil
        ),
        TeamChannel(
            id: "ch_files",
            name: "files",
            type: "public",
            createdAt: "",
            createdBy: "",
            members: [],
            admins: [],
            description: nil,
            topic: nil,
            pinnedMessages: [],
            dmParticipants: nil
        )
    ]
}
