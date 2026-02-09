//
//  TeamNotesPanel.swift
//  MagnetarStudio
//
//  Team mode panel — Slack-like channels and DMs within the Workspace Hub.
//  Replaces personal notes when team mode is enabled.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "TeamNotesPanel")

// MARK: - Local Team Models

struct LocalChannel: Identifiable, Codable, Equatable, Sendable {
    let id: UUID
    var name: String
    var topic: String
    var isPrivate: Bool
    var createdAt: Date
    var unreadCount: Int
    var isMuted: Bool

    init(
        id: UUID = UUID(),
        name: String,
        topic: String = "",
        isPrivate: Bool = false,
        createdAt: Date = Date(),
        unreadCount: Int = 0,
        isMuted: Bool = false
    ) {
        self.id = id
        self.name = name
        self.topic = topic
        self.isPrivate = isPrivate
        self.createdAt = createdAt
        self.unreadCount = unreadCount
        self.isMuted = isMuted
    }
}

struct LocalMessage: Identifiable, Codable, Equatable, Sendable {
    let id: UUID
    var channelId: UUID
    var senderName: String
    var content: String
    var timestamp: Date
    var isEdited: Bool
    var threadId: UUID?

    init(
        id: UUID = UUID(),
        channelId: UUID,
        senderName: String,
        content: String,
        timestamp: Date = Date(),
        isEdited: Bool = false,
        threadId: UUID? = nil
    ) {
        self.id = id
        self.channelId = channelId
        self.senderName = senderName
        self.content = content
        self.timestamp = timestamp
        self.isEdited = isEdited
        self.threadId = threadId
    }
}

struct DirectConversation: Identifiable, Codable, Equatable, Sendable {
    let id: UUID
    var participantName: String
    var lastMessage: String
    var lastMessageAt: Date
    var unreadCount: Int

    init(
        id: UUID = UUID(),
        participantName: String,
        lastMessage: String = "",
        lastMessageAt: Date = Date(),
        unreadCount: Int = 0
    ) {
        self.id = id
        self.participantName = participantName
        self.lastMessage = lastMessage
        self.lastMessageAt = lastMessageAt
        self.unreadCount = unreadCount
    }
}

// MARK: - Team Notes Panel

struct TeamNotesPanel: View {
    @State private var channels: [LocalChannel] = []
    @State private var directMessages: [DirectConversation] = []
    @State private var selectedChannelID: UUID?
    @State private var selectedDMID: UUID?
    @State private var messages: [LocalMessage] = []
    @State private var messageText = ""
    @State private var searchText = ""
    @State private var showCreateChannel = false
    @State private var isLoading = true
    @AppStorage("workspace.connectionMode") private var connectionMode = "cloud"

    var body: some View {
        HStack(spacing: 0) {
            // Channel sidebar
            channelSidebar
                .frame(width: 240)

            Divider()

            // Content area
            if let channelID = selectedChannelID,
               let channel = channels.first(where: { $0.id == channelID }) {
                ChannelView(
                    channel: channel,
                    messages: channelMessages(for: channelID),
                    messageText: $messageText,
                    onSend: { sendMessage(to: channelID) }
                )
            } else if let dmID = selectedDMID,
                      let dm = directMessages.first(where: { $0.id == dmID }) {
                dmChatView(dm)
            } else {
                teamEmptyState
            }
        }
        .task {
            await loadTeamData()
        }
        .sheet(isPresented: $showCreateChannel) {
            CreateChannelSheet(onCreate: { name, topic, isPrivate in
                createChannel(name: name, topic: topic, isPrivate: isPrivate)
            })
        }
    }

    // MARK: - Channel Sidebar

    private var channelSidebar: some View {
        VStack(spacing: 0) {
            // Header
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 12))
                    .foregroundStyle(.tertiary)
                TextField("Search channels...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 12))

                connectionBadge
            }
            .padding(.horizontal, 12)
            .frame(height: HubLayout.headerHeight)
            .background(Color.surfaceTertiary.opacity(0.5))

            Divider()

            ScrollView {
                VStack(alignment: .leading, spacing: 0) {
                    // Channels section
                    teamSectionHeader("Channels", showAdd: true) {
                        showCreateChannel = true
                    }

                    ForEach(filteredChannels) { channel in
                        TeamChannelRow(
                            channel: channel,
                            isSelected: selectedChannelID == channel.id,
                            onSelect: {
                                selectedChannelID = channel.id
                                selectedDMID = nil
                            }
                        )
                    }

                    // Direct Messages section
                    teamSectionHeader("Direct Messages", showAdd: false) {}

                    if filteredDirectMessages.isEmpty {
                        Text("No conversations yet")
                            .font(.system(size: 12))
                            .foregroundStyle(.secondary)
                            .padding(.horizontal, 14)
                            .padding(.vertical, 8)
                    } else {
                        ForEach(filteredDirectMessages) { dm in
                            DMRow(
                                conversation: dm,
                                isSelected: selectedDMID == dm.id,
                                onSelect: {
                                    selectedDMID = dm.id
                                    selectedChannelID = nil
                                }
                            )
                        }
                    }
                }
                .padding(.vertical, 4)
            }

            Spacer(minLength: 0)

            // Bottom status
            teamStatusBar
        }
        .background(Color.surfaceTertiary)
    }

    private var filteredChannels: [LocalChannel] {
        if searchText.isEmpty { return channels }
        let query = searchText.lowercased()
        return channels.filter { $0.name.lowercased().contains(query) || $0.topic.lowercased().contains(query) }
    }

    private var filteredDirectMessages: [DirectConversation] {
        if searchText.isEmpty { return directMessages }
        let query = searchText.lowercased()
        return directMessages.filter { $0.participantName.lowercased().contains(query) }
    }

    private var connectionBadge: some View {
        HStack(spacing: 4) {
            Circle()
                .fill(Color.green)
                .frame(width: 6, height: 6)
            Text(connectionLabel)
                .font(.system(size: 10, weight: .medium))
                .foregroundStyle(.secondary)
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 3)
        .background(
            RoundedRectangle(cornerRadius: 4)
                .fill(Color.green.opacity(0.1))
        )
    }

    private var connectionLabel: String {
        switch connectionMode {
        case "cloud": return "Cloud"
        case "wifi-aware": return "WiFi"
        case "p2p": return "P2P"
        case "lan": return "LAN"
        default: return "Online"
        }
    }

    private var teamStatusBar: some View {
        HStack(spacing: 8) {
            Image(systemName: "person.2.fill")
                .font(.system(size: 11))
                .foregroundStyle(.secondary)
            Text("\(channels.count) channels")
                .font(.system(size: 11))
                .foregroundStyle(.secondary)
            Spacer()
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(Color.surfaceTertiary.opacity(0.8))
    }

    // MARK: - Section Header

    private func teamSectionHeader(
        _ title: String,
        showAdd: Bool,
        action: @escaping () -> Void
    ) -> some View {
        HStack {
            Text(title.uppercased())
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(.tertiary)
            Spacer()
            if showAdd {
                Button(action: action) {
                    Image(systemName: "plus")
                        .font(.system(size: 10, weight: .medium))
                        .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
                .accessibilityLabel("Add \(title.lowercased())")
            }
        }
        .padding(.horizontal, 14)
        .padding(.top, 14)
        .padding(.bottom, 6)
    }

    // MARK: - DM Chat View

    private func dmChatView(_ dm: DirectConversation) -> some View {
        VStack(spacing: 0) {
            // DM header
            HStack(spacing: 10) {
                Circle()
                    .fill(Color.magnetarPrimary.opacity(0.2))
                    .frame(width: 28, height: 28)
                    .overlay(
                        Text(String(dm.participantName.prefix(1)).uppercased())
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(Color.magnetarPrimary)
                    )
                Text(dm.participantName)
                    .font(.system(size: 15, weight: .semibold))
                Spacer()
            }
            .padding(.horizontal, 16)
            .frame(height: HubLayout.headerHeight)
            .background(Color.surfaceTertiary.opacity(0.3))

            Divider()

            // Messages
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    Text("Start of conversation with \(dm.participantName)")
                        .font(.system(size: 12))
                        .foregroundStyle(.tertiary)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 20)
                }
                .padding(16)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)

            Divider()

            // Input
            messageInput(placeholder: "Message \(dm.participantName)...") {
                // DM send logic
                messageText = ""
            }
        }
        .background(Color.surfacePrimary)
    }

    // MARK: - Empty State

    private var teamEmptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "bubble.left.and.bubble.right")
                .font(.system(size: 48))
                .foregroundStyle(.tertiary)
            Text("Select a channel to start chatting")
                .font(.body)
                .foregroundStyle(.secondary)
            Text("Channels are shared spaces for team communication")
                .font(.caption)
                .foregroundStyle(.tertiary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.surfacePrimary)
    }

    // MARK: - Message Input

    private func messageInput(placeholder: String, onSend: @escaping () -> Void) -> some View {
        HStack(spacing: 10) {
            Button {
                // Attach file
            } label: {
                Image(systemName: "plus.circle")
                    .font(.system(size: 18))
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)

            TextField(placeholder, text: $messageText)
                .textFieldStyle(.plain)
                .font(.system(size: 14))
                .onSubmit {
                    if !messageText.isEmpty { onSend() }
                }

            Button {
                if !messageText.isEmpty { onSend() }
            } label: {
                Image(systemName: "paperplane.fill")
                    .font(.system(size: 14))
                    .foregroundStyle(messageText.isEmpty ? .gray : Color.magnetarPrimary)
            }
            .buttonStyle(.plain)
            .disabled(messageText.isEmpty)
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .background(Color.surfaceTertiary.opacity(0.3))
    }

    // MARK: - Helpers

    private func channelMessages(for channelID: UUID) -> [LocalMessage] {
        messages.filter { $0.channelId == channelID }
            .sorted { $0.timestamp < $1.timestamp }
    }

    // MARK: - Actions

    private func sendMessage(to channelID: UUID) {
        guard !messageText.isEmpty else { return }
        let msg = LocalMessage(
            channelId: channelID,
            senderName: "You",
            content: messageText
        )
        messages.append(msg)
        messageText = ""
        saveMessages()
        logger.debug("Sent message to channel \(channelID)")
    }

    private func createChannel(name: String, topic: String, isPrivate: Bool) {
        let channel = LocalChannel(
            name: name,
            topic: topic,
            isPrivate: isPrivate
        )
        channels.append(channel)
        selectedChannelID = channel.id
        selectedDMID = nil
        saveChannels()
        logger.info("Created channel: #\(name)")
    }

    // MARK: - Persistence

    private static var storageDir: URL {
        let dir = (FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory)
            .appendingPathComponent("MagnetarStudio/workspace/team", isDirectory: true)
        PersistenceHelpers.ensureDirectory(at: dir, label: "team storage")
        return dir
    }

    private func loadTeamData() async {
        defer { isLoading = false }

        // Load channels
        let channelsFile = Self.storageDir.appendingPathComponent("channels.json")
        if let loaded = PersistenceHelpers.load([LocalChannel].self, from: channelsFile, label: "team channels") {
            channels = loaded
        } else {
            // Default channels on first launch
            channels = [
                LocalChannel(name: "general", topic: "General discussion"),
                LocalChannel(name: "random", topic: "Off-topic conversations")
            ]
            saveChannels()
        }

        // Load messages
        let messagesFile = Self.storageDir.appendingPathComponent("messages.json")
        if let loaded = PersistenceHelpers.load([LocalMessage].self, from: messagesFile, label: "team messages") {
            messages = loaded
        } else {
            // Welcome messages
            if let general = channels.first {
                messages = [
                    LocalMessage(
                        channelId: general.id,
                        senderName: "MagnetarBot",
                        content: "Welcome to #general! This is the start of your team workspace."
                    )
                ]
                saveMessages()
            }
        }

        // Load DMs
        let dmsFile = Self.storageDir.appendingPathComponent("dms.json")
        if let loaded = PersistenceHelpers.load([DirectConversation].self, from: dmsFile, label: "direct messages") {
            directMessages = loaded
        }

        // Select first channel by default
        if selectedChannelID == nil {
            selectedChannelID = channels.first?.id
        }
    }

    private func saveChannels() {
        let file = Self.storageDir.appendingPathComponent("channels.json")
        PersistenceHelpers.save(channels, to: file, label: "team channels")
    }

    private func saveMessages() {
        let file = Self.storageDir.appendingPathComponent("messages.json")
        PersistenceHelpers.save(messages, to: file, label: "team messages")
    }
}

// MARK: - Team Channel Row

private struct TeamChannelRow: View {
    let channel: LocalChannel
    let isSelected: Bool
    let onSelect: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: onSelect) {
            HStack(spacing: 8) {
                Image(systemName: channel.isPrivate ? "lock.fill" : "number")
                    .font(.system(size: 12))
                    .foregroundStyle(isSelected ? .white : .secondary)
                    .frame(width: 16)

                Text(channel.name)
                    .font(.system(size: 13, weight: channel.unreadCount > 0 ? .semibold : .regular))
                    .foregroundStyle(isSelected ? .white : .primary)
                    .lineLimit(1)

                Spacer()

                if channel.isMuted {
                    Image(systemName: "speaker.slash.fill")
                        .font(.system(size: 9))
                        .foregroundStyle(isSelected ? .white.opacity(0.5) : .gray)
                }

                if channel.unreadCount > 0 {
                    Text(channel.unreadCount > 99 ? "99+" : "\(channel.unreadCount)")
                        .font(.system(size: 10, weight: .bold))
                        .foregroundStyle(.white)
                        .padding(.horizontal, 5)
                        .padding(.vertical, 2)
                        .background(
                            Capsule().fill(Color.magnetarPrimary)
                        )
                }
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background {
                RoundedRectangle(cornerRadius: 6)
                    .fill(isSelected ? Color.magnetarPrimary : (isHovered ? Color.white.opacity(0.05) : Color.clear))
            }
        }
        .buttonStyle(.plain)
        .padding(.horizontal, 6)
        .onHover { isHovered = $0 }
        .contextMenu {
            if channel.isMuted {
                Button("Unmute") {}
            } else {
                Button("Mute") {}
            }
            Divider()
            Button("Leave Channel", role: .destructive) {}
        }
    }
}

// MARK: - DM Row

private struct DMRow: View {
    let conversation: DirectConversation
    let isSelected: Bool
    let onSelect: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: onSelect) {
            HStack(spacing: 8) {
                // Avatar
                Circle()
                    .fill(Color.magnetarPrimary.opacity(0.15))
                    .frame(width: 24, height: 24)
                    .overlay(
                        Text(String(conversation.participantName.prefix(1)).uppercased())
                            .font(.system(size: 10, weight: .semibold))
                            .foregroundStyle(Color.magnetarPrimary)
                    )

                VStack(alignment: .leading, spacing: 1) {
                    Text(conversation.participantName)
                        .font(.system(size: 13, weight: conversation.unreadCount > 0 ? .semibold : .regular))
                        .foregroundStyle(isSelected ? .white : .primary)
                        .lineLimit(1)

                    if !conversation.lastMessage.isEmpty {
                        Text(conversation.lastMessage)
                            .font(.system(size: 10))
                            .foregroundStyle(isSelected ? .white.opacity(0.6) : .secondary)
                            .lineLimit(1)
                    }
                }

                Spacer()

                if conversation.unreadCount > 0 {
                    Circle()
                        .fill(Color.magnetarPrimary)
                        .frame(width: 8, height: 8)
                }
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background {
                RoundedRectangle(cornerRadius: 6)
                    .fill(isSelected ? Color.magnetarPrimary : (isHovered ? Color.white.opacity(0.05) : Color.clear))
            }
        }
        .buttonStyle(.plain)
        .padding(.horizontal, 6)
        .onHover { isHovered = $0 }
    }
}

// MARK: - Create Channel Sheet

private struct CreateChannelSheet: View {
    let onCreate: (String, String, Bool) -> Void

    @Environment(\.dismiss) private var dismiss
    @State private var channelName = ""
    @State private var channelTopic = ""
    @State private var isPrivate = false

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Create Channel")
                    .font(.system(size: 15, weight: .semibold))
                Spacer()
                Button("Cancel") { dismiss() }
                    .buttonStyle(.plain)
                    .foregroundStyle(.secondary)
            }
            .padding(16)

            Divider()

            VStack(alignment: .leading, spacing: 16) {
                // Name
                VStack(alignment: .leading, spacing: 6) {
                    Text("Channel name")
                        .font(.system(size: 12, weight: .medium))
                    HStack(spacing: 4) {
                        Text("#")
                            .font(.system(size: 14, weight: .medium, design: .monospaced))
                            .foregroundStyle(.secondary)
                        TextField("e.g. design-reviews", text: $channelName)
                            .textFieldStyle(.plain)
                            .font(.system(size: 14))
                    }
                    .padding(8)
                    .background(
                        RoundedRectangle(cornerRadius: 6)
                            .fill(Color.surfaceTertiary)
                    )
                }

                // Topic
                VStack(alignment: .leading, spacing: 6) {
                    Text("Topic (optional)")
                        .font(.system(size: 12, weight: .medium))
                    TextField("What's this channel about?", text: $channelTopic)
                        .textFieldStyle(.plain)
                        .font(.system(size: 14))
                        .padding(8)
                        .background(
                            RoundedRectangle(cornerRadius: 6)
                                .fill(Color.surfaceTertiary)
                        )
                }

                // Private toggle
                Toggle(isOn: $isPrivate) {
                    VStack(alignment: .leading, spacing: 2) {
                        Text("Make private")
                            .font(.system(size: 13, weight: .medium))
                        Text("Only invited members can see this channel")
                            .font(.system(size: 11))
                            .foregroundStyle(.secondary)
                    }
                }
                .toggleStyle(.switch)
                .controlSize(.small)
            }
            .padding(16)

            Divider()

            // Actions
            HStack {
                Spacer()
                Button("Create") {
                    let name = channelName.trimmingCharacters(in: .whitespaces)
                        .lowercased()
                        .replacingOccurrences(of: " ", with: "-")
                    if !name.isEmpty {
                        onCreate(name, channelTopic, isPrivate)
                        dismiss()
                    }
                }
                .buttonStyle(.borderedProminent)
                .disabled(channelName.trimmingCharacters(in: .whitespaces).isEmpty)
            }
            .padding(16)
        }
        .frame(width: 400)
    }
}
