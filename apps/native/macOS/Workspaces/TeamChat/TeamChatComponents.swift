//
//  TeamChatComponents.swift
//  MagnetarStudio (macOS)
//
//  Team chat UI components - Extracted from TeamWorkspace.swift
//

import SwiftUI
import Foundation

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
            print("Failed to load P2P status: \(error.localizedDescription)")
        }
    }

    // MARK: - P2P Banner

    private var p2pBanner: some View {
        HStack(spacing: 12) {
            // Left: Status
            HStack(spacing: 8) {
                statusIcon
                    .font(.system(size: 12))

                Text(statusText)
                    .font(.system(size: 14))
                    .foregroundColor(statusColor)
            }

            Spacer()

            // Right: Peer ID + Buttons
            HStack(spacing: 8) {
                if let networkStatus = p2pNetworkStatus, p2pStatus == .connected {
                    Text(String(networkStatus.peerId.prefix(12)) + "...")
                        .font(.system(size: 12, design: .monospaced))
                        .foregroundColor(.blue)
                }

                Button {
                    showPeerDiscovery = true
                } label: {
                    HStack(spacing: 6) {
                        Image(systemName: "person.2")
                            .font(.system(size: 12))
                        Text("Peers")
                            .font(.system(size: 12, weight: .medium))
                    }
                    .foregroundColor(.white)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(Color.blue)
                    )
                }
                .buttonStyle(.plain)

                Button {
                    showFileSharing = true
                } label: {
                    HStack(spacing: 6) {
                        Image(systemName: "arrow.up.doc")
                            .font(.system(size: 12))
                        Text("Files")
                            .font(.system(size: 12, weight: .medium))
                    }
                    .foregroundColor(.white)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(Color.green)
                    )
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .background(Color.blue.opacity(0.1))
        .overlay(
            Rectangle()
                .fill(Color.blue.opacity(0.3))
                .frame(height: 1),
            alignment: .bottom
        )
    }

    private var statusIcon: some View {
        Group {
            switch p2pStatus {
            case .connecting:
                ProgressView()
                    .scaleEffect(0.6)
                    .tint(.blue)
            case .disconnected:
                Image(systemName: "wifi.slash")
                    .foregroundColor(.red)
            case .connected:
                Image(systemName: "wifi")
                    .foregroundColor(.green)
            }
        }
    }

    private var statusText: String {
        switch p2pStatus {
        case .connecting: return "Connecting to P2P mesh..."
        case .disconnected: return "Disconnected from mesh"
        case .connected:
            let peerCount = p2pNetworkStatus?.discoveredPeers ?? 0
            return "Connected • \(peerCount) peers"
        }
    }

    private var statusColor: Color {
        switch p2pStatus {
        case .connecting: return .blue
        case .disconnected: return .red
        case .connected: return .green
        }
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
            // Silently handle P2P service not initialized (expected in dev without libp2p)
            if error.localizedDescription.contains("P2P service not initialized") {
                print("ℹ️ P2P service not available (libp2p not installed) - using default channels")
            } else {
                print("Failed to load channels: \(error.localizedDescription)")
            }
            // Keep default channels on error
        }
    }

    private func sectionHeader(title: String, onAdd: (() -> Void)?) -> some View {
        HStack {
            Text(title)
                .font(.system(size: 12, weight: .semibold))
                .foregroundColor(.secondary)
                .textCase(.uppercase)

            Spacer()

            if let onAdd = onAdd {
                Button(action: onAdd) {
                    Image(systemName: "plus")
                        .font(.system(size: 14))
                        .foregroundColor(.secondary)
                        .frame(width: 20, height: 20)
                }
                .buttonStyle(.plain)
                .onHover { hovering in
                    // Hover effect handled by buttonStyle
                }
            }
        }
        .padding(.horizontal, 8)
        .padding(.vertical, 4)
    }

    private func channelRow(channel: TeamChannel, isActive: Bool, isPrivate: Bool = false) -> some View {
        HStack(spacing: 8) {
            Image(systemName: isPrivate ? "lock" : "number")
                .font(.system(size: 16))
                .foregroundColor(isActive ? Color.magnetarPrimary : .secondary)

            Text(channel.name)
                .font(.system(size: 14))
                .foregroundColor(isActive ? .primary : .secondary)

            Spacer()
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 16)
                .fill(isActive ? Color.magnetarPrimary.opacity(0.15) : Color.clear)
                .overlay(
                    RoundedRectangle(cornerRadius: 16)
                        .strokeBorder(isActive ? Color.magnetarPrimary.opacity(0.3) : Color.clear, lineWidth: 1)
                )
        )
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
                    // Header
                    HStack(spacing: 12) {
                        Image(systemName: "number")
                            .font(.system(size: 18))
                            .foregroundColor(Color.magnetarPrimary)

                        Text(channel.name)
                            .font(.system(size: 18, weight: .bold))

                        Spacer()

                        Button {
                            // Channel menu
                        } label: {
                            Image(systemName: "ellipsis")
                                .font(.system(size: 16))
                                .foregroundColor(.secondary)
                                .frame(width: 32, height: 32)
                        }
                        .buttonStyle(.plain)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(Color.gray.opacity(0.0))
                        )
                    }
                    .padding(.horizontal, 16)
                    .padding(.vertical, 12)
                    .background(Color(.controlBackgroundColor))
                    .overlay(
                        Rectangle()
                            .fill(Color.gray.opacity(0.2))
                            .frame(height: 1),
                        alignment: .bottom
                    )

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

                    // Message input
                    VStack(spacing: 0) {
                        Divider()

                        HStack(spacing: 12) {
                            TextField("Type a message...", text: $messageInput)
                                .textFieldStyle(.plain)
                                .font(.system(size: 14))

                            HStack(spacing: 8) {
                                Button {
                                    // Attach file
                                } label: {
                                    Image(systemName: "paperclip")
                                        .font(.system(size: 16))
                                        .foregroundColor(.secondary)
                                }
                                .buttonStyle(.plain)

                                Button {
                                    // Emoji picker
                                } label: {
                                    Image(systemName: "face.smiling")
                                        .font(.system(size: 16))
                                        .foregroundColor(.secondary)
                                }
                                .buttonStyle(.plain)

                                Button {
                                    sendMessage()
                                } label: {
                                    Image(systemName: "arrow.up.circle.fill")
                                        .font(.system(size: 24))
                                        .foregroundStyle(messageInput.isEmpty ? AnyShapeStyle(Color.secondary) : AnyShapeStyle(LinearGradient.magnetarGradient))
                                }
                                .buttonStyle(.plain)
                                .disabled(messageInput.isEmpty)
                            }
                        }
                        .padding(.horizontal, 16)
                        .padding(.vertical, 12)
                    }
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
                // Silently handle P2P service not initialized (expected in dev without libp2p)
                if error.localizedDescription.contains("P2P service not initialized") {
                    print("ℹ️ P2P service not available (libp2p not installed) - messages unavailable")
                    await MainActor.run {
                        messages = []
                        isLoadingMessages = false
                        errorMessage = nil  // Don't show error for expected P2P unavailability
                    }
                } else {
                    print("Failed to load messages: \(error.localizedDescription)")
                    await MainActor.run {
                        messages = []
                        isLoadingMessages = false
                        errorMessage = "Failed to load messages: \(error.localizedDescription)"
                    }
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
                print("Failed to send message: \(error.localizedDescription)")
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

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Circle()
                .fill(LinearGradient.magnetarGradient)
                .frame(width: 36, height: 36)
                .overlay(
                    Text(String(message.senderName.prefix(2)).uppercased())
                        .font(.system(size: 12, weight: .bold))
                        .foregroundColor(.white)
                )

            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 8) {
                    Text(message.senderName)
                        .font(.system(size: 14, weight: .semibold))

                    Text(formatTimestamp(message.timestamp))
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)

                    if message.encrypted {
                        Image(systemName: "lock.fill")
                            .font(.system(size: 10))
                            .foregroundColor(.green.opacity(0.7))
                    }
                }

                Text(message.content)
                    .font(.system(size: 14))
                    .foregroundColor(.primary)

                if message.editedAt != nil {
                    Text("(edited)")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary.opacity(0.7))
                        .italic()
                }
            }

            Spacer()
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
