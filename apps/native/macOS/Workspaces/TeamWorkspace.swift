//
//  TeamWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Team collaboration workspace matching React TeamWorkspace.tsx specs exactly
//  - Toolbar: NetworkSelector, Diagnostics, View tabs, Join/Create buttons
//  - Content: Switches between TeamChat, Docs, Workflows, Vault sub-workspaces
//

import SwiftUI

struct TeamWorkspace: View {
    @State private var networkMode: NetworkMode = .local
    @State private var workspaceView: TeamView = .chat
    @State private var currentTeam: Team? = nil

    // Modals/Panels
    @State private var showDiagnostics = false
    @State private var showCreateTeam = false
    @State private var showJoinTeam = false
    @State private var showVaultSetup = false
    @State private var showNLQuery = false
    @State private var showPatterns = false

    // Permissions (mock for now)
    private var permissions = Permissions(
        canAccessDocuments: true,
        canAccessAutomation: true,
        canAccessVault: true
    )

    var body: some View {
        VStack(spacing: 0) {
            // Toolbar
            toolbar
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .background(Color.gray.opacity(0.05))
                .overlay(
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 1),
                    alignment: .bottom
                )

            // Content area
            contentArea
        }
        .sheet(isPresented: $showDiagnostics) {
            DiagnosticsPanel()
        }
        .sheet(isPresented: $showCreateTeam) {
            CreateTeamModal()
        }
        .sheet(isPresented: $showJoinTeam) {
            JoinTeamModal()
        }
        .sheet(isPresented: $showVaultSetup) {
            VaultSetupModal()
        }
        .sheet(isPresented: $showNLQuery) {
            NLQueryPanel()
        }
        .sheet(isPresented: $showPatterns) {
            PatternDiscoveryPanel()
        }
    }

    // MARK: - Toolbar

    private var toolbar: some View {
        HStack(spacing: 12) {
            // Left cluster: NetworkSelector + Diagnostics
            NetworkSelector(mode: $networkMode)

            Button {
                showDiagnostics = true
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: "waveform.path.ecg")
                        .font(.system(size: 16))
                    Text("Diagnostics")
                        .font(.system(size: 14))
                }
                .foregroundColor(.secondary)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(Color.gray.opacity(0.1))
                )
            }
            .buttonStyle(.plain)
            .help("Network Diagnostics")

            // Divider
            Rectangle()
                .fill(Color.gray.opacity(0.3))
                .frame(width: 1, height: 24)

            // View tabs
            HStack(spacing: 4) {
                // Chat
                TeamTabButton(
                    title: "Chat",
                    icon: "message",
                    isActive: workspaceView == .chat,
                    tintColor: Color.magnetarPrimary,
                    action: { workspaceView = .chat }
                )

                // Docs
                if permissions.canAccessDocuments {
                    TeamTabButton(
                        title: "Docs",
                        icon: "doc.text",
                        isActive: workspaceView == .docs,
                        tintColor: Color.magnetarPrimary,
                        action: { workspaceView = .docs }
                    )
                }

                // Data Lab (opens panel, not a tab switch)
                Button {
                    showNLQuery = true
                } label: {
                    HStack(spacing: 8) {
                        Image(systemName: "cylinder")
                            .font(.system(size: 16))
                        Text("Data Lab")
                            .font(.system(size: 14))
                    }
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color.clear)
                    )
                }
                .buttonStyle(.plain)
                .help("Ask AI about your data")

                // Patterns (opens panel)
                Button {
                    showPatterns = true
                } label: {
                    HStack(spacing: 8) {
                        Image(systemName: "chart.bar")
                            .font(.system(size: 16))
                        Text("Patterns")
                            .font(.system(size: 14))
                    }
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color.clear)
                    )
                }
                .buttonStyle(.plain)
                .help("Pattern Discovery")

                // Workflows
                if permissions.canAccessAutomation {
                    TeamTabButton(
                        title: "Workflows",
                        icon: "arrow.triangle.branch",
                        isActive: workspaceView == .workflows,
                        tintColor: Color.magnetarPrimary,
                        action: { workspaceView = .workflows }
                    )
                }

                // Divider before Vault
                if permissions.canAccessVault {
                    Rectangle()
                        .fill(Color.gray.opacity(0.3))
                        .frame(width: 1, height: 24)
                        .padding(.horizontal, 8)
                }

                // Vault (amber tint)
                if permissions.canAccessVault {
                    TeamTabButton(
                        title: "Vault",
                        icon: "lock.shield",
                        isActive: workspaceView == .vault,
                        tintColor: .orange,
                        action: { handleVaultClick() }
                    )
                }
            }

            Spacer()

            // Right cluster: Join/Create buttons (only when no team)
            if currentTeam == nil {
                HStack(spacing: 8) {
                    Button {
                        showJoinTeam = true
                    } label: {
                        HStack(spacing: 8) {
                            Image(systemName: "person.badge.plus")
                                .font(.system(size: 16))
                            Text("Join Team")
                                .font(.system(size: 14, weight: .medium))
                        }
                        .foregroundColor(.white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(Color.green)
                        )
                    }
                    .buttonStyle(.plain)

                    Button {
                        showCreateTeam = true
                    } label: {
                        HStack(spacing: 8) {
                            Image(systemName: "plus")
                                .font(.system(size: 16))
                            Text("Create Team")
                                .font(.system(size: 14, weight: .medium))
                        }
                        .foregroundColor(.white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(Color.magnetarPrimary)
                        )
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    // MARK: - Content Area

    @ViewBuilder
    private var contentArea: some View {
        switch workspaceView {
        case .chat:
            TeamChatView(mode: networkMode)
        case .docs:
            DocsWorkspace()
        case .workflows:
            AutomationWorkspaceView()
        case .vault:
            VaultWorkspace()
        }
    }

    // MARK: - Actions

    private func handleVaultClick() {
        // TODO: Check vault setup status
        // For now, just switch to vault
        workspaceView = .vault
    }
}

// MARK: - Team Tab Button Component

struct TeamTabButton: View {
    let title: String
    let icon: String
    let isActive: Bool
    let tintColor: Color
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                Image(systemName: icon)
                    .font(.system(size: 16))
                Text(title)
                    .font(.system(size: 14, weight: isActive ? .medium : .regular))
            }
            .foregroundColor(isActive ? tintColor : (isHovered ? .primary : .secondary))
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isActive ? tintColor.opacity(0.15) : (isHovered ? Color.gray.opacity(0.1) : Color.clear))
            )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            isHovered = hovering
        }
    }
}

// MARK: - Supporting Types

enum TeamView {
    case chat
    case docs
    case workflows
    case vault
}

struct Team {
    let id: UUID
    let name: String
}

struct Permissions {
    let canAccessDocuments: Bool
    let canAccessAutomation: Bool
    let canAccessVault: Bool
}

// MARK: - Placeholder Sub-Workspaces

struct TeamChatView: View {
    let mode: NetworkMode
    @State private var sidebarWidth: CGFloat = 320
    @State private var activeChannel: Channel?
    @State private var showNewChannelDialog = false
    @State private var showPeerDiscovery = false
    @State private var showFileSharing = false
    @State private var p2pStatus: P2PStatus = .connected
    @State private var peerCount: Int = 3

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
                if let peerId = mockPeerId {
                    Text(peerId)
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
        case .connected: return "Connected • \(peerCount) peers"
        }
    }

    private var statusColor: Color {
        switch p2pStatus {
        case .connecting: return .blue
        case .disconnected: return .red
        case .connected: return .green
        }
    }

    private var mockPeerId: String? {
        p2pStatus == .connected ? "12D3Ko...aB9f" : nil
    }
}

// MARK: - TeamChat Sidebar

struct TeamChatSidebar: View {
    @Binding var activeChannel: Channel?
    let onNewChannel: () -> Void

    @State private var publicChannels: [Channel] = Channel.defaultPublic
    @State private var privateChannels: [Channel] = []
    @State private var directMessages: [Channel] = []

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

    private func channelRow(channel: Channel, isActive: Bool, isPrivate: Bool = false) -> some View {
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
    let activeChannel: Channel?
    let mode: NetworkMode

    @State private var messageInput: String = ""

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

                    // Messages area
                    ScrollView {
                        VStack(spacing: 16) {
                            ForEach(0..<5) { index in
                                TeamMessageRow(index: index)
                            }
                        }
                        .padding(16)
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
                                    // Send message
                                    messageInput = ""
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
    let index: Int

    var body: some View {
        HStack(alignment: .top, spacing: 12) {
            Circle()
                .fill(LinearGradient.magnetarGradient)
                .frame(width: 36, height: 36)
                .overlay(
                    Text("U\(index + 1)")
                        .font(.system(size: 12, weight: .bold))
                        .foregroundColor(.white)
                )

            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 8) {
                    Text("User \(index + 1)")
                        .font(.system(size: 14, weight: .semibold))

                    Text("10:\(30 + index)am")
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                }

                Text("This is a sample message in the team chat. It demonstrates the message layout and styling.")
                    .font(.system(size: 14))
                    .foregroundColor(.primary)
            }

            Spacer()
        }
    }
}

// MARK: - Supporting Types

enum P2PStatus {
    case connecting
    case disconnected
    case connected
}

struct Channel: Identifiable {
    let id = UUID()
    let name: String
    let isPrivate: Bool

    static let defaultPublic = [
        Channel(name: "general", isPrivate: false),
        Channel(name: "files", isPrivate: false)
    ]
}

// MARK: - Modals

struct NewChannelDialog: View {
    @Binding var isPresented: Bool
    @State private var channelName: String = ""
    @State private var description: String = ""
    @State private var isPrivate: Bool = false

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Create Channel")
                    .font(.system(size: 20, weight: .bold))

                Spacer()

                Button {
                    isPresented = false
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 20))
                        .foregroundColor(.secondary)
                        .frame(width: 32, height: 32)
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 24)
            .padding(.vertical, 16)
            .background(Color(.controlBackgroundColor))
            .overlay(
                Rectangle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(height: 1),
                alignment: .bottom
            )

            // Body
            VStack(alignment: .leading, spacing: 24) {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Channel Name")
                        .font(.system(size: 13, weight: .semibold))

                    HStack(spacing: 8) {
                        Text("#")
                            .font(.system(size: 14))
                            .foregroundColor(.secondary)

                        TextField("e.g. project-updates", text: $channelName)
                            .textFieldStyle(.plain)
                            .font(.system(size: 14))
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 10)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .strokeBorder(Color.gray.opacity(0.3), lineWidth: 1)
                    )
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text("Description (optional)")
                        .font(.system(size: 13, weight: .semibold))

                    TextEditor(text: $description)
                        .font(.system(size: 14))
                        .frame(height: 80)
                        .padding(8)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .strokeBorder(Color.gray.opacity(0.3), lineWidth: 1)
                        )
                }

                Toggle(isOn: $isPrivate) {
                    Text("Make private")
                        .font(.system(size: 14))
                }
                .toggleStyle(.switch)
            }
            .padding(24)

            // Footer
            HStack(spacing: 12) {
                Button {
                    isPresented = false
                } label: {
                    Text("Cancel")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(.primary)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .strokeBorder(Color.gray.opacity(0.3), lineWidth: 1)
                        )
                }
                .buttonStyle(.plain)

                Button {
                    // Create channel
                    isPresented = false
                } label: {
                    Text("Create")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(.white)
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 10)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(channelName.isEmpty ? Color.gray : Color.green)
                        )
                }
                .buttonStyle(.plain)
                .disabled(channelName.isEmpty)
            }
            .padding(.horizontal, 24)
            .padding(.vertical, 16)
            .background(Color(.controlBackgroundColor))
            .overlay(
                Rectangle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(height: 1),
                alignment: .top
            )
        }
        .frame(width: 540, height: 480)
        .background(Color(.windowBackgroundColor))
        .cornerRadius(12)
    }
}

struct PeerDiscoveryPanel: View {
    var body: some View {
        VStack(spacing: 16) {
            Text("P2P Peer Discovery")
                .font(.title2)
            Text("Peer list will appear here")
                .foregroundColor(.secondary)
        }
        .frame(width: 600, height: 400)
        .padding()
    }
}

struct FileSharingPanel: View {
    var body: some View {
        VStack(spacing: 16) {
            Text("P2P File Sharing")
                .font(.title2)
            Text("File sharing interface will appear here")
                .foregroundColor(.secondary)
        }
        .frame(width: 600, height: 400)
        .padding()
    }
}

struct DocsWorkspace: View {
    @State private var sidebarVisible: Bool = true
    @State private var activeDocument: Document? = nil
    @State private var showDocTypeSelector: Bool = false
    @State private var selectedDocType: DocumentType = .document

    var body: some View {
        HStack(spacing: 0) {
            // Left Sidebar
            if sidebarVisible {
                docsSidebar
                    .frame(width: 256)

                Divider()
            }

            // Main area
            if let doc = activeDocument {
                documentEditor(doc: doc)
            } else {
                emptyState
            }
        }
    }

    // MARK: - Sidebar

    private var docsSidebar: some View {
        VStack(spacing: 0) {
            // Header
            VStack(spacing: 12) {
                HStack(spacing: 8) {
                    Text("Documents")
                        .font(.system(size: 14, weight: .semibold))

                    Spacer()

                    HStack(spacing: 4) {
                        Text("Solo")
                            .font(.system(size: 10, weight: .medium))
                            .foregroundColor(.white)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 3)
                            .background(
                                RoundedRectangle(cornerRadius: 4)
                                    .fill(Color.blue)
                            )
                    }
                }

                // New Document button
                Button {
                    // Create new document
                } label: {
                    HStack(spacing: 8) {
                        Image(systemName: "plus")
                            .font(.system(size: 16))
                        Text("New Document")
                            .font(.system(size: 14, weight: .medium))
                    }
                    .foregroundColor(.white)
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 10)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color.magnetarPrimary)
                    )
                }
                .buttonStyle(.plain)

                // Type selector
                Menu {
                    Button("Document") { selectedDocType = .document }
                    Button("Spreadsheet") { selectedDocType = .spreadsheet }
                    Button("Insight") { selectedDocType = .insight }
                    Divider()
                    Button("Secure Document") { selectedDocType = .secureDocument }
                } label: {
                    HStack(spacing: 8) {
                        Image(systemName: selectedDocType.icon)
                            .font(.system(size: 14))

                        Text(selectedDocType.displayName)
                            .font(.system(size: 13))

                        Spacer()

                        Image(systemName: "chevron.down")
                            .font(.system(size: 10))
                    }
                    .foregroundColor(.secondary)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(Color.gray.opacity(0.1))
                    )
                }
                .buttonStyle(.plain)
            }
            .padding(12)
            .background(Color.gray.opacity(0.03))
            .overlay(
                Rectangle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(height: 1),
                alignment: .bottom
            )

            // Document list
            DocumentsSidebar(
                activeDocument: $activeDocument,
                documents: Document.mockDocuments
            )
        }
        .background(Color.gray.opacity(0.05))
    }

    // MARK: - Editor

    private func documentEditor(doc: Document) -> some View {
        VStack(spacing: 0) {
            // Header
            HStack(spacing: 12) {
                Button {
                    sidebarVisible.toggle()
                } label: {
                    Image(systemName: "sidebar.left")
                        .font(.system(size: 16))
                        .foregroundColor(.secondary)
                        .frame(width: 32, height: 32)
                }
                .buttonStyle(.plain)

                VStack(alignment: .leading, spacing: 2) {
                    Text(doc.name)
                        .font(.system(size: 16, weight: .semibold))

                    Text("Last edited: \(doc.lastEdited)")
                        .font(.system(size: 12))
                        .foregroundColor(.secondary)
                }

                Spacer()
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

            // Editor area (placeholder)
            VStack(spacing: 16) {
                Image(systemName: doc.type.icon)
                    .font(.system(size: 64))
                    .foregroundColor(.secondary)

                Text("Document Editor")
                    .font(.title)

                Text("Editor for \(doc.name) will appear here")
                    .font(.subheadline)
                    .foregroundColor(.secondary)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
    }

    // MARK: - Empty State

    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "plus")
                .font(.system(size: 64))
                .foregroundColor(.secondary)

            Text("No document selected")
                .font(.system(size: 18, weight: .semibold))

            Text("Select a document from the sidebar or create a new one")
                .font(.system(size: 14))
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: - Documents Sidebar

struct DocumentsSidebar: View {
    @Binding var activeDocument: Document?
    let documents: [Document]

    var body: some View {
        ScrollView {
            VStack(spacing: 4) {
                ForEach(documents) { doc in
                    documentRow(doc: doc, isActive: activeDocument?.id == doc.id)
                        .onTapGesture {
                            activeDocument = doc
                        }
                }
            }
            .padding(8)
        }
    }

    private func documentRow(doc: Document, isActive: Bool) -> some View {
        HStack(spacing: 10) {
            Image(systemName: doc.type.icon)
                .font(.system(size: 16))
                .foregroundColor(isActive ? Color.magnetarPrimary : .secondary)

            VStack(alignment: .leading, spacing: 2) {
                Text(doc.name)
                    .font(.system(size: 13, weight: isActive ? .medium : .regular))
                    .foregroundColor(isActive ? .primary : .secondary)

                Text(doc.lastEdited)
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)
            }

            Spacer()
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(isActive ? Color.magnetarPrimary.opacity(0.1) : Color.clear)
        )
    }
}

// MARK: - Document Types

enum DocumentType {
    case document
    case spreadsheet
    case insight
    case secureDocument

    var displayName: String {
        switch self {
        case .document: return "Document"
        case .spreadsheet: return "Spreadsheet"
        case .insight: return "Insight"
        case .secureDocument: return "Secure Document"
        }
    }

    var icon: String {
        switch self {
        case .document: return "doc.text"
        case .spreadsheet: return "tablecells"
        case .insight: return "chart.bar.doc.horizontal"
        case .secureDocument: return "lock.doc"
        }
    }
}

struct Document: Identifiable {
    let id = UUID()
    let name: String
    let type: DocumentType
    let lastEdited: String

    static let mockDocuments = [
        Document(name: "Project Proposal", type: .document, lastEdited: "2 hours ago"),
        Document(name: "Q4 Budget", type: .spreadsheet, lastEdited: "Yesterday"),
        Document(name: "Sales Analysis", type: .insight, lastEdited: "3 days ago"),
        Document(name: "Confidential Report", type: .secureDocument, lastEdited: "Last week")
    ]
}

// AutomationWorkspace moved to Shared/Components/AutomationWorkspace.swift

struct VaultWorkspace: View {
    var body: some View {
        VStack {
            Image(systemName: "lock.shield")
                .font(.system(size: 64))
                .foregroundColor(.orange)
            Text("Vault Workspace")
                .font(.title)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

// MARK: - Placeholder Modals

struct DiagnosticsPanel: View {
    var body: some View {
        VStack(spacing: 16) {
            Text("Network Diagnostics")
                .font(.title2)
            Text("Connection metrics and status will appear here")
                .foregroundColor(.secondary)
        }
        .frame(width: 600, height: 400)
        .padding()
    }
}

struct CreateTeamModal: View {
    var body: some View {
        VStack(spacing: 16) {
            Text("Create Team")
                .font(.title2)
            Text("Team creation form will appear here")
                .foregroundColor(.secondary)
        }
        .frame(width: 500, height: 400)
        .padding()
    }
}

struct JoinTeamModal: View {
    var body: some View {
        VStack(spacing: 16) {
            Text("Join Team")
                .font(.title2)
            Text("Team join form will appear here")
                .foregroundColor(.secondary)
        }
        .frame(width: 500, height: 400)
        .padding()
    }
}

struct VaultSetupModal: View {
    var body: some View {
        VStack(spacing: 16) {
            Text("Vault Setup")
                .font(.title2)
            Text("Vault configuration will appear here")
                .foregroundColor(.secondary)
        }
        .frame(width: 500, height: 400)
        .padding()
    }
}

struct NLQueryPanel: View {
    var body: some View {
        VStack(spacing: 16) {
            Text("Ask AI About Your Data")
                .font(.title2)
            Text("Natural language query interface will appear here")
                .foregroundColor(.secondary)
        }
        .frame(width: 600, height: 500)
        .padding()
    }
}

struct PatternDiscoveryPanel: View {
    var body: some View {
        VStack(spacing: 16) {
            Text("Pattern Discovery")
                .font(.title2)
            Text("Data pattern analysis will appear here")
                .foregroundColor(.secondary)
        }
        .frame(width: 700, height: 600)
        .padding()
    }
}

// MARK: - Preview

#Preview {
    TeamWorkspace()
        .frame(width: 1200, height: 800)
}
