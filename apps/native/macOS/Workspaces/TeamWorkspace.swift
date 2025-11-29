//
//  TeamWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Team collaboration workspace matching React TeamWorkspace.tsx specs exactly
//  - Toolbar: NetworkSelector, Diagnostics, View tabs, Join/Create buttons
//  - Content: Switches between TeamChat, Docs, Workflows, Vault sub-workspaces
//

import SwiftUI
import Foundation

// MARK: - Team Service Models & Service (inlined for now)

// Message models (duplicated from TeamService for now - needed due to module visibility)
struct TeamMessage: Identifiable, Codable {
    let id: String
    let channelId: String
    let senderId: String
    let senderName: String
    let type: String
    let content: String
    let timestamp: String
    let encrypted: Bool
    let fileMetadata: AnyCodable?
    let threadId: String?
    let replyTo: String?
    let editedAt: String?

    enum CodingKeys: String, CodingKey {
        case id
        case channelId = "channel_id"
        case senderId = "sender_id"
        case senderName = "sender_name"
        case type, content, timestamp, encrypted
        case fileMetadata = "file_metadata"
        case threadId = "thread_id"
        case replyTo = "reply_to"
        case editedAt = "edited_at"
    }
}

struct MessageListResponse: Codable {
    let channelId: String
    let messages: [TeamMessage]
    let total: Int
    let hasMore: Bool

    enum CodingKeys: String, CodingKey {
        case channelId = "channel_id"
        case messages, total
        case hasMore = "has_more"
    }
}

struct Team: Identifiable, Codable {
    let id: String
    let name: String
    let description: String?
    let createdAt: String
    let memberCount: Int?

    enum CodingKeys: String, CodingKey {
        case id, name, description
        case createdAt = "created_at"
        case memberCount = "member_count"
    }
}

struct TeamDocument: Identifiable, Codable {
    let id: String
    let title: String
    let content: AnyCodable?  // Backend returns Any type (could be JSON object or string)
    let type: String
    let createdAt: String
    let updatedAt: String
    let createdBy: String
    let isPrivate: Bool
    let securityLevel: String?
    let sharedWith: [String]
    let teamId: String?

    enum CodingKeys: String, CodingKey {
        case id, title, content, type
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case createdBy = "created_by"
        case isPrivate = "is_private"
        case securityLevel = "security_level"
        case sharedWith = "shared_with"
        case teamId = "team_id"
    }
}

struct DiagnosticsStatus: Codable {
    let status: String
    let network: NetworkStatus
    let database: DatabaseStatus
    let services: [ServiceStatus]

    struct NetworkStatus: Codable {
        let connected: Bool
        let latency: Int?
        let bandwidth: String?
    }

    struct DatabaseStatus: Codable {
        let connected: Bool
        let queryTime: Int?

        enum CodingKeys: String, CodingKey {
            case connected
            case queryTime = "query_time"
        }
    }

    struct ServiceStatus: Codable {
        let name: String
        let status: String
        let uptime: String?
    }
}

struct NLQueryResponse: Codable {
    let answer: String
    let query: String
    let confidence: Double?
    let sources: [String]?
}

struct PatternDiscoveryResult: Codable {
    let patterns: [Pattern]
    let summary: String?

    struct Pattern: Codable, Identifiable {
        let id: String
        let type: String
        let description: String
        let confidence: Double
        let examples: [String]?
    }
}

struct VaultSetupResponse: Codable {
    let status: String
    let message: String
    let vaultId: String?

    enum CodingKeys: String, CodingKey {
        case status, message
        case vaultId = "vault_id"
    }
}

struct VaultStatusResponse: Codable {
    let initialized: Bool
    let locked: Bool
    let message: String?
}

final class TeamService {
    static let shared = TeamService()
    private let apiClient = ApiClient.shared

    private init() {}

    func createTeam(name: String, description: String?) async throws -> Team {
        try await apiClient.request(
            path: "/v1/teams",
            method: .post,
            jsonBody: [
                "name": name,
                "description": description ?? ""
            ]
        )
    }

    func joinTeam(code: String) async throws -> Team {
        try await apiClient.request(
            path: "/v1/teams/join",
            method: .post,
            jsonBody: ["code": code]
        )
    }

    func listTeams() async throws -> [Team] {
        try await apiClient.request(
            path: "/v1/teams",
            method: .get
        )
    }

    func listDocuments() async throws -> [TeamDocument] {
        try await apiClient.request(
            path: "/v1/docs/documents",
            method: .get
        )
    }

    func createDocument(title: String, content: String, type: String) async throws -> TeamDocument {
        try await apiClient.request(
            path: "/v1/docs/documents",
            method: .post,
            jsonBody: [
                "title": title,
                "content": content,
                "type": type
            ]
        )
    }

    func updateDocument(id: String, title: String?, content: String?) async throws -> TeamDocument {
        var body: [String: Any] = [:]
        if let title = title { body["title"] = title }
        if let content = content { body["content"] = content }

        return try await apiClient.request(
            path: "/v1/docs/documents/\(id)",
            method: .put,
            jsonBody: body
        )
    }

    func getDiagnostics() async throws -> DiagnosticsStatus {
        try await apiClient.request(
            path: "/v1/diagnostics",
            method: .get
        )
    }

    func askNaturalLanguage(query: String) async throws -> NLQueryResponse {
        try await apiClient.request(
            path: "/v1/data/ask",
            method: .post,
            jsonBody: ["query": query]
        )
    }

    func discoverPatterns(query: String, context: String?) async throws -> PatternDiscoveryResult {
        var body: [String: Any] = ["query": query]
        if let context = context { body["context"] = context }

        return try await apiClient.request(
            path: "/v1/data/patterns",
            method: .post,
            jsonBody: body
        )
    }

    func setupVault(password: String) async throws -> VaultSetupResponse {
        try await apiClient.request(
            path: "/v1/vault/setup",
            method: .post,
            jsonBody: ["password": password]
        )
    }

    func getVaultStatus() async throws -> VaultStatusResponse {
        try await apiClient.request(
            path: "/v1/vault/status",
            method: .get
        )
    }

    func getUserPermissions() async throws -> Permissions {
        // MVP: All authenticated users have full access to team features
        // The backend has a comprehensive RBAC system at /api/v1/permissions/*
        // Future enhancement: Query user's actual permission profile for fine-grained access control
        // For production multi-tenant deployment, wire up to backend RBAC:
        //   - GET /api/v1/permissions/users/{user_id}/profiles
        //   - Check specific permissions like "team.access_documents", "team.access_vault", etc.
        return Permissions(
            canAccessDocuments: true,
            canAccessAutomation: true,
            canAccessVault: true
        )
    }

    func listChannels() async throws -> [Channel] {
        struct ChannelListResponse: Codable {
            let channels: [Channel]
            let total: Int
        }

        let response: ChannelListResponse = try await apiClient.request(
            path: "/v1/team/channels",
            method: .get
        )

        return response.channels
    }

    func sendMessage(channelId: String, content: String) async throws -> TeamMessage {
        try await apiClient.request(
            path: "/v1/team/channels/\(channelId)/messages",
            method: .post,
            jsonBody: [
                "channel_id": channelId,
                "content": content,
                "type": "text"
            ]
        )
    }

    func getMessages(channelId: String, limit: Int = 50) async throws -> MessageListResponse {
        try await apiClient.request(
            path: "/v1/team/channels/\(channelId)/messages?limit=\(limit)",
            method: .get
        )
    }

    func getP2PNetworkStatus() async throws -> P2PNetworkStatus {
        try await apiClient.request(
            path: "/v1/team/status",
            method: .get
        )
    }
}

struct P2PNetworkStatus: Codable {
    let peerId: String
    let isConnected: Bool
    let discoveredPeers: Int
    let activeChannels: Int
    let multiaddrs: [String]

    enum CodingKeys: String, CodingKey {
        case peerId = "peer_id"
        case isConnected = "is_connected"
        case discoveredPeers = "discovered_peers"
        case activeChannels = "active_channels"
        case multiaddrs
    }
}

struct Permissions {
    let canAccessDocuments: Bool
    let canAccessAutomation: Bool
    let canAccessVault: Bool
}

struct TeamWorkspace: View {
    @State private var networkMode: NetworkMode = .local
    @State private var workspaceView: TeamView = .chat
    @State private var currentTeam: Team? = nil

    // Modals/Panels
    @State private var showDiagnostics = false
    @State private var showCreateTeam = false
    @State private var showJoinTeam = false
    @State private var showVaultSetup = false

    // Vault status
    @State private var vaultReady: Bool = false
    @State private var checkingVaultStatus: Bool = false
    @State private var vaultError: String? = nil

    // Permissions
    @State private var permissions = Permissions(
        canAccessDocuments: true,
        canAccessAutomation: true,
        canAccessVault: true
    )
    @State private var isLoadingPermissions: Bool = false

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
        .task {
            await loadPermissions()
        }
    }

    // MARK: - Data Loading

    private func loadPermissions() async {
        isLoadingPermissions = true
        defer { isLoadingPermissions = false }

        do {
            permissions = try await TeamService.shared.getUserPermissions()
        } catch {
            // Keep default permissions on error
            print("Failed to load permissions: \(error.localizedDescription)")
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
        Task {
            await checkVaultStatus()
        }
    }

    @MainActor
    private func checkVaultStatus() async {
        checkingVaultStatus = true
        vaultError = nil

        do {
            // Try to access vault by checking folders endpoint
            let url = URL(string: "http://localhost:8000/api/v1/vault/folders?vault_type=real")!
            var request = URLRequest(url: url)
            request.httpMethod = "GET"

            // Get token if available (will be nil in DEBUG mode)
            if let token = KeychainService.shared.loadToken() {
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }

            let (_, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw NSError(domain: "VaultError", code: -1, userInfo: [NSLocalizedDescriptionKey: "Invalid response"])
            }

            if httpResponse.statusCode == 200 {
                // Vault is accessible
                vaultReady = true
                workspaceView = .vault
            } else if httpResponse.statusCode == 403 {
                // Vault needs setup or no permissions
                vaultError = "Vault access denied. Setup may be required."
                showVaultSetup = true
            } else {
                vaultError = "Vault returned status \(httpResponse.statusCode)"
            }

        } catch {
            vaultError = "Failed to check vault status: \(error.localizedDescription)"
            print("Vault status check error: \(error)")
        }

        checkingVaultStatus = false
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
// MARK: - Placeholder Sub-Workspaces

struct TeamChatView: View {
    let mode: NetworkMode
    @State private var sidebarWidth: CGFloat = 320
    @State private var activeChannel: Channel?
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
    @State private var messages: [TeamMessage] = []
    @State private var isLoadingMessages = false

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
                    .onChange(of: activeChannel?.id) { _ in
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
                }
            } catch {
                print("Failed to load messages: \(error.localizedDescription)")
                await MainActor.run {
                    messages = []
                    isLoadingMessages = false
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
                }
            } catch {
                print("Failed to send message: \(error.localizedDescription)")
                // TODO: Show error to user
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

                if let editedAt = message.editedAt {
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

struct Channel: Identifiable, Codable {
    let id: String
    let name: String
    let type: String // "public", "private", "direct"
    let createdAt: String
    let createdBy: String
    let members: [String]
    let admins: [String]
    let description: String?
    let topic: String?
    let pinnedMessages: [String]
    let dmParticipants: [String]?

    var isPrivate: Bool {
        type == "private"
    }

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case type
        case createdAt = "created_at"
        case createdBy = "created_by"
        case members
        case admins
        case description
        case topic
        case pinnedMessages = "pinned_messages"
        case dmParticipants = "dm_participants"
    }

    // Mock defaults for preview/testing
    static let defaultPublic = [
        Channel(
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
        Channel(
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
    @State private var activeDocument: TeamDocument? = nil
    @State private var documents: [TeamDocument] = []
    @State private var isLoading: Bool = false
    @State private var errorMessage: String? = nil
    @State private var showNewDocumentModal: Bool = false

    private let teamService = TeamService.shared

    var body: some View {
        HStack(spacing: 0) {
            // Left Sidebar - New Slack-style sidebar
            if sidebarVisible {
                SlackStyleDocsSidebar(
                    activeDocument: $activeDocument,
                    documents: documents,
                    onNewDocument: {
                        showNewDocumentModal = true
                    }
                )
                .frame(width: 256)

                Divider()
            }

            // Main area
            if isLoading {
                loadingView
            } else if let error = errorMessage {
                errorView(error)
            } else if let doc = activeDocument {
                documentEditor(doc: doc)
            } else {
                emptyState
            }
        }
        .task {
            await loadDocuments()
        }
        .sheet(isPresented: $showNewDocumentModal) {
            NewDocumentModal(isPresented: $showNewDocumentModal) { title, type in
                try await createDocument(title: title, type: type)
            }
        }
    }

    @MainActor
    private func loadDocuments() async {
        isLoading = true
        errorMessage = nil

        do {
            documents = try await teamService.listDocuments()
            isLoading = false
        } catch {
            errorMessage = error.localizedDescription
            isLoading = false
        }
    }

    @MainActor
    private func createDocument(title: String, type: NewDocumentType) async throws {
        let newDoc = try await teamService.createDocument(
            title: title,
            content: "",
            type: type.backendType
        )
        documents.append(newDoc)
        activeDocument = newDoc
        await loadDocuments() // Refresh list
    }

    // MARK: - Helper Views

    private var loadingView: some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.5)

            Text("Loading documents...")
                .font(.system(size: 14))
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func errorView(_ message: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 48))
                .foregroundColor(.red)

            Text("Error Loading Documents")
                .font(.system(size: 18, weight: .semibold))

            Text(message)
                .font(.system(size: 14))
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            Button("Retry") {
                Task {
                    await loadDocuments()
                }
            }
            .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }

    private func documentEditor(doc: TeamDocument) -> some View {
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
                    Text(doc.title)
                        .font(.system(size: 16, weight: .semibold))

                    Text("Last edited: \(doc.updatedAt)")
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

            // Editor area - showing content
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    Text(doc.content?.stringValue ?? doc.content?.value as? String ?? "No content")
                        .font(.system(size: 14))
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding()
                }
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
    @Binding var activeDocument: TeamDocument?
    let documents: [TeamDocument]

    var body: some View {
        if documents.isEmpty {
            VStack(spacing: 12) {
                Image(systemName: "doc.text")
                    .font(.system(size: 32))
                    .foregroundColor(.secondary)

                Text("No documents yet")
                    .font(.system(size: 13))
                    .foregroundColor(.secondary)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding()
        } else {
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
    }

    private func documentRow(doc: TeamDocument, isActive: Bool) -> some View {
        HStack(spacing: 10) {
            Image(systemName: iconForType(doc.type))
                .font(.system(size: 16))
                .foregroundColor(isActive ? Color.magnetarPrimary : .secondary)

            VStack(alignment: .leading, spacing: 2) {
                Text(doc.title)
                    .font(.system(size: 13, weight: isActive ? .medium : .regular))
                    .foregroundColor(isActive ? .primary : .secondary)

                Text(doc.updatedAt)
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

    private func iconForType(_ type: String) -> String {
        switch type.lowercased() {
        case "document": return "doc.text"
        case "spreadsheet": return "tablecells"
        case "insight": return "chart.bar.doc.horizontal"
        case "securedocument", "secure_document": return "lock.doc"
        default: return "doc"
        }
    }
}

// MARK: - Document Types

enum DocumentType: String {
    case document = "document"
    case spreadsheet = "spreadsheet"
    case insight = "insight"
    case secureDocument = "secure_document"

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
    @State private var vaultUnlocked: Bool = false
    @State private var password: String = ""
    @State private var showPassword: Bool = false
    @State private var authError: String? = nil
    @State private var isAuthenticating: Bool = false
    @State private var viewMode: VaultViewMode = .grid
    @State private var searchText: String = ""
    @State private var currentPath: [String] = ["/"]
    @State private var selectedFile: VaultFile? = nil
    @State private var showPreview: Bool = false

    // Real backend state
    @State private var files: [VaultFile] = []
    @State private var isLoadingFiles: Bool = false
    @State private var vaultError: String? = nil
    @State private var isUploading: Bool = false
    @State private var isCreatingFolder: Bool = false
    @State private var newFolderName: String = ""
    @State private var showNewFolderDialog: Bool = false
    @State private var fileToDelete: VaultFile? = nil
    @State private var showDeleteConfirmation: Bool = false

    private let vaultService = VaultService.shared

    var body: some View {
        Group {
            if vaultUnlocked {
                unlockedView
            } else {
                lockedView
            }
        }
        .sheet(isPresented: $showPreview) {
            if let file = selectedFile {
                FilePreviewModal(
                    file: file,
                    isPresented: $showPreview,
                    onDownload: {
                        Task {
                            await downloadFile(file)
                        }
                    },
                    onDelete: {
                        fileToDelete = file
                        showDeleteConfirmation = true
                    },
                    vaultPassword: password
                )
            }
        }
        .sheet(isPresented: $showNewFolderDialog) {
            NewFolderDialog(
                folderName: $newFolderName,
                isPresented: $showNewFolderDialog,
                onCreate: {
                    Task {
                        await createFolder()
                    }
                }
            )
        }
        .alert("Delete File", isPresented: $showDeleteConfirmation, presenting: fileToDelete) { file in
            Button("Cancel", role: .cancel) {
                showDeleteConfirmation = false
                fileToDelete = nil
            }
            Button("Delete", role: .destructive) {
                Task {
                    await deleteFile(file)
                }
                showDeleteConfirmation = false
                fileToDelete = nil
            }
        } message: { file in
            Text("Are you sure you want to delete '\(file.name)'? This action cannot be undone.")
        }
        .task {
            if vaultUnlocked {
                await loadFiles()
            }
        }
    }

    // MARK: - Locked View

    private var lockedView: some View {
        VStack(spacing: 24) {
            // Icon
            Image(systemName: "lock.shield")
                .font(.system(size: 32))
                .foregroundColor(.orange)

            // Title
            VStack(spacing: 8) {
                Text("Unlock Vault")
                    .font(.system(size: 24, weight: .bold))

                Text("Enter your password to access secure files")
                    .font(.system(size: 14))
                    .foregroundColor(.secondary)
            }

            // Password field
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 12) {
                    if showPassword {
                        TextField("Password", text: $password)
                            .textFieldStyle(.plain)
                            .font(.system(size: 14))
                    } else {
                        SecureField("Password", text: $password)
                            .textFieldStyle(.plain)
                            .font(.system(size: 14))
                    }

                    Button {
                        showPassword.toggle()
                    } label: {
                        Image(systemName: showPassword ? "eye.slash" : "eye")
                            .font(.system(size: 18))
                            .foregroundColor(.secondary)
                    }
                    .buttonStyle(.plain)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(authError != nil ? Color.red : Color.gray.opacity(0.3), lineWidth: 1)
                )

                if let error = authError {
                    Text(error)
                        .font(.system(size: 12))
                        .foregroundColor(.red)
                }
            }

            // Touch ID button (if available)
            Button {
                // Biometric auth
                authenticateWithBiometrics()
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: "touchid")
                        .font(.system(size: 18))
                    Text("Use Touch ID")
                        .font(.system(size: 14, weight: .medium))
                }
                .foregroundColor(.primary)
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(Color.gray.opacity(0.3), lineWidth: 1)
                )
            }
            .buttonStyle(.plain)

            // Unlock button
            Button {
                unlockVault()
            } label: {
                HStack(spacing: 8) {
                    if isAuthenticating {
                        ProgressView()
                            .scaleEffect(0.8)
                            .tint(.white)
                    } else {
                        Text("Unlock")
                            .font(.system(size: 14, weight: .medium))
                    }
                }
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(password.isEmpty ? Color.gray : Color.magnetarPrimary)
                )
            }
            .buttonStyle(.plain)
            .disabled(password.isEmpty || isAuthenticating)
        }
        .frame(width: 400)
        .padding(28)
        .background(
            RoundedRectangle(cornerRadius: 20)
                .fill(Color(.controlBackgroundColor))
                .shadow(color: Color.black.opacity(0.1), radius: 12, x: 0, y: 4)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 20)
                .strokeBorder(Color.gray.opacity(0.2), lineWidth: 1)
        )
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Unlocked View

    private var unlockedView: some View {
        VStack(spacing: 0) {
            // Top bar
            topBar
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .background(Color(.controlBackgroundColor))
                .overlay(
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 1),
                    alignment: .bottom
                )

            // Content
            if isLoadingFiles {
                loadingView
            } else if let error = vaultError {
                errorView(error: error)
            } else if filteredFiles.isEmpty {
                emptyState
            } else {
                if viewMode == .grid {
                    gridView
                } else {
                    listView
                }
            }
        }
    }

    private var filteredFiles: [VaultFile] {
        if searchText.isEmpty {
            return files
        }
        return files.filter { $0.name.localizedCaseInsensitiveContains(searchText) }
    }

    private var loadingView: some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.2)

            Text("Loading vault...")
                .font(.system(size: 16))
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func errorView(error: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 48))
                .foregroundColor(.orange)

            Text("Error Loading Vault")
                .font(.system(size: 18, weight: .semibold))

            Text(error)
                .font(.system(size: 14))
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)

            Button("Retry") {
                Task {
                    await loadFiles()
                }
            }
            .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var topBar: some View {
        HStack(spacing: 12) {
            // Breadcrumbs
            HStack(spacing: 6) {
                ForEach(Array(currentPath.enumerated()), id: \.offset) { index, folder in
                    if index > 0 {
                        Image(systemName: "chevron.right")
                            .font(.system(size: 10))
                            .foregroundColor(.secondary)
                    }

                    Text(folder)
                        .font(.system(size: 14))
                        .foregroundColor(index == currentPath.count - 1 ? .primary : .secondary)
                }
            }

            Spacer()

            // View toggle
            HStack(spacing: 4) {
                viewToggleButton(icon: "square.grid.3x2", mode: .grid)
                viewToggleButton(icon: "list.bullet", mode: .list)
            }
            .padding(4)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.gray.opacity(0.1))
            )

            // Search
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 14))
                    .foregroundColor(.secondary)

                TextField("Search vault...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 14))
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .frame(width: 240)
            .background(
                RoundedRectangle(cornerRadius: 16)
                    .fill(Color.gray.opacity(0.1))
            )

            // Buttons
            Button {
                showNewFolderDialog = true
            } label: {
                HStack(spacing: 6) {
                    if isCreatingFolder {
                        ProgressView()
                            .scaleEffect(0.7)
                    } else {
                        Image(systemName: "folder.badge.plus")
                            .font(.system(size: 16))
                    }
                    Text("New Folder")
                        .font(.system(size: 14, weight: .medium))
                }
                .foregroundColor(.primary)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(Color.gray.opacity(0.3), lineWidth: 1)
                )
            }
            .buttonStyle(.plain)
            .disabled(isCreatingFolder)

            Button {
                uploadFile()
            } label: {
                HStack(spacing: 6) {
                    if isUploading {
                        ProgressView()
                            .scaleEffect(0.7)
                            .tint(.white)
                    } else {
                        Image(systemName: "arrow.up.doc")
                            .font(.system(size: 16))
                    }
                    Text("Upload")
                        .font(.system(size: 14, weight: .medium))
                }
                .foregroundColor(.white)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(isUploading ? Color.gray : Color.magnetarPrimary)
                )
            }
            .buttonStyle(.plain)
            .disabled(isUploading)
        }
    }

    private func viewToggleButton(icon: String, mode: VaultViewMode) -> some View {
        Button {
            viewMode = mode
        } label: {
            Image(systemName: icon)
                .font(.system(size: 16))
                .foregroundColor(viewMode == mode ? Color.magnetarPrimary : .secondary)
                .frame(width: 32, height: 32)
        }
        .buttonStyle(.plain)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(viewMode == mode ? Color.magnetarPrimary.opacity(0.15) : Color.clear)
        )
    }

    // MARK: - Grid View

    private var gridView: some View {
        ScrollView {
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 180, maximum: 220), spacing: 16)], spacing: 16) {
                ForEach(filteredFiles) { file in
                    fileCard(file: file)
                        .onTapGesture {
                            if file.isFolder {
                                navigateToFolder(file)
                            } else {
                                selectedFile = file
                                showPreview = true
                            }
                        }
                        .contextMenu {
                            if !file.isFolder {
                                Button("Download") {
                                    Task {
                                        await downloadFile(file)
                                    }
                                }

                                Divider()

                                Button("Delete", role: .destructive) {
                                    fileToDelete = file
                                    showDeleteConfirmation = true
                                }
                            }
                        }
                }
            }
            .padding(20)
        }
    }

    private func fileCard(file: VaultFile) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            // Icon chip
            ZStack {
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color(file.mimeColor).opacity(0.15))
                    .frame(height: 80)

                Image(systemName: file.mimeIcon)
                    .font(.system(size: 32))
                    .foregroundColor(Color(file.mimeColor))
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(file.name)
                    .font(.system(size: 13, weight: .medium))
                    .lineLimit(1)
                    .truncationMode(.middle)

                HStack(spacing: 8) {
                    Text(file.sizeFormatted)
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)

                    Text("•")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)

                    Text(file.modifiedFormatted)
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                }
            }
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(Color(.controlBackgroundColor))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(Color.gray.opacity(0.2), lineWidth: 1)
        )
    }

    // MARK: - List View

    private var listView: some View {
        VStack(spacing: 0) {
            // Header
            HStack(spacing: 16) {
                Text("Name")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)

                Text("Size")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(.secondary)
                    .frame(width: 100, alignment: .trailing)

                Text("Modified")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(.secondary)
                    .frame(width: 120, alignment: .trailing)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color.gray.opacity(0.05))

            Divider()

            ScrollView {
                ForEach(filteredFiles) { file in
                    fileRow(file: file)
                        .onTapGesture {
                            if file.isFolder {
                                navigateToFolder(file)
                            } else {
                                selectedFile = file
                                showPreview = true
                            }
                        }
                        .contextMenu {
                            if !file.isFolder {
                                Button("Download") {
                                    Task {
                                        await downloadFile(file)
                                    }
                                }

                                Divider()

                                Button("Delete", role: .destructive) {
                                    fileToDelete = file
                                    showDeleteConfirmation = true
                                }
                            }
                        }
                }
            }
        }
    }

    private func fileRow(file: VaultFile) -> some View {
        HStack(spacing: 16) {
            HStack(spacing: 10) {
                Image(systemName: file.mimeIcon)
                    .font(.system(size: 16))
                    .foregroundColor(Color(file.mimeColor))

                Text(file.name)
                    .font(.system(size: 14))
                    .lineLimit(1)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            Text(file.sizeFormatted)
                .font(.system(size: 14))
                .foregroundColor(.secondary)
                .frame(width: 100, alignment: .trailing)

            Text(file.modifiedFormatted)
                .font(.system(size: 14))
                .foregroundColor(.secondary)
                .frame(width: 120, alignment: .trailing)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(Color.clear)
        .overlay(
            Rectangle()
                .fill(Color.gray.opacity(0.1))
                .frame(height: 1),
            alignment: .bottom
        )
    }

    // MARK: - Empty State

    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "folder.badge.questionmark")
                .font(.system(size: 48))
                .foregroundColor(.secondary)

            Text("No files in this folder")
                .font(.system(size: 18, weight: .semibold))

            Text("Upload files to get started")
                .font(.system(size: 14))
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Actions

    private func unlockVault() {
        isAuthenticating = true
        authError = nil

        // Simulate authentication (real backend integration would verify password)
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            if password == "test" || password.count >= 4 {
                vaultUnlocked = true
                authError = nil
                Task {
                    await loadFiles()
                }
            } else {
                authError = "Invalid password"
            }
            isAuthenticating = false
        }
    }

    private func authenticateWithBiometrics() {
        // Simulate biometric auth
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            vaultUnlocked = true
            Task {
                await loadFiles()
            }
        }
    }

    // MARK: - Vault Operations

    @MainActor
    private func loadFiles() async {
        isLoadingFiles = true
        vaultError = nil

        do {
            let currentFolder = currentPath.last ?? "/"
            files = try await vaultService.listFiles(vaultType: "real", folderPath: currentFolder)
            vaultError = nil
        } catch let error as VaultError {
            if case .unauthorized = error {
                // Show setup modal
                vaultError = error.localizedDescription
                vaultUnlocked = false
            } else {
                vaultError = error.localizedDescription
            }
            files = []
        } catch {
            vaultError = "Failed to load vault: \(error.localizedDescription)"
            files = []
        }

        isLoadingFiles = false
    }

    private func uploadFile() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.canChooseFiles = true

        if panel.runModal() == .OK, let url = panel.url {
            Task {
                await performUpload(fileURL: url)
            }
        }
    }

    @MainActor
    private func performUpload(fileURL: URL) async {
        isUploading = true
        vaultError = nil

        do {
            let currentFolder = currentPath.last ?? "/"
            _ = try await vaultService.upload(
                fileURL: fileURL,
                folderPath: currentFolder,
                vaultType: "real",
                passphrase: password
            )

            // Refresh file list
            await loadFiles()
        } catch let error as VaultError {
            vaultError = "Upload failed: \(error.localizedDescription)"
        } catch {
            vaultError = "Upload failed: \(error.localizedDescription)"
        }

        isUploading = false
    }

    private func createFolder() async {
        guard !newFolderName.isEmpty else { return }

        isCreatingFolder = true
        vaultError = nil

        do {
            _ = try await vaultService.createFolder(
                name: newFolderName,
                folderPath: currentPath.last ?? "/",
                vaultType: "real",
                passphrase: password
            )

            // Refresh file list
            await loadFiles()
            newFolderName = ""
        } catch let error as VaultError {
            vaultError = "Failed to create folder: \(error.localizedDescription)"
        } catch {
            vaultError = "Failed to create folder: \(error.localizedDescription)"
        }

        isCreatingFolder = false
    }

    @MainActor
    private func downloadFile(_ file: VaultFile) async {
        let savePanel = NSSavePanel()
        savePanel.nameFieldStringValue = file.name

        if savePanel.runModal() == .OK, let destinationURL = savePanel.url {
            vaultError = nil

            do {
                let data = try await vaultService.download(
                    fileId: file.id,
                    vaultType: "real",
                    passphrase: password
                )
                try data.write(to: destinationURL)
            } catch let error as VaultError {
                vaultError = "Download failed: \(error.localizedDescription)"
            } catch {
                vaultError = "Download failed: \(error.localizedDescription)"
            }
        }
    }

    @MainActor
    private func deleteFile(_ file: VaultFile) async {
        // Optimistic delete
        let originalFiles = files
        files.removeAll { $0.id == file.id }

        do {
            try await vaultService.deleteFile(fileId: file.id)
            vaultError = nil
        } catch let error as VaultError {
            // Rollback on failure
            files = originalFiles
            vaultError = "Delete failed: \(error.localizedDescription)"
        } catch {
            // Rollback on failure
            files = originalFiles
            vaultError = "Delete failed: \(error.localizedDescription)"
        }
    }

    private func navigateToFolder(_ folder: VaultFile) {
        guard folder.isFolder else { return }

        if let folderPath = folder.folderPath {
            currentPath.append(folderPath)
        } else {
            currentPath.append(folder.name)
        }

        Task {
            await loadFiles()
        }
    }
}

// MARK: - Supporting Types

enum VaultViewMode {
    case grid
    case list
}

// Legacy mock file model for the UI preview; renamed to avoid clashing with real VaultFile model.
struct LegacyVaultFile: Identifiable {
    let id = UUID()
    let name: String
    let size: String
    let modified: String
    let mimeType: String

    var mimeIcon: String {
        switch mimeType {
        case "image": return "photo"
        case "video": return "video"
        case "audio": return "music.note"
        case "pdf": return "doc.text"
        case "zip": return "archivebox"
        case "code": return "chevron.left.forwardslash.chevron.right"
        default: return "doc"
        }
    }

    var mimeColor: Color {
        switch mimeType {
        case "image": return .purple
        case "video": return .pink
        case "audio": return .green
        case "pdf": return .red
        case "zip": return .yellow
        case "code": return .indigo
        default: return .gray
        }
    }

    static let mockFiles = [
        LegacyVaultFile(name: "Confidential Report.pdf", size: "2.4 MB", modified: "2 hours ago", mimeType: "pdf"),
        LegacyVaultFile(name: "Team Photo.jpg", size: "1.8 MB", modified: "Yesterday", mimeType: "image"),
        LegacyVaultFile(name: "Project Source.zip", size: "15.2 MB", modified: "3 days ago", mimeType: "zip"),
        LegacyVaultFile(name: "Meeting Recording.mp4", size: "45.6 MB", modified: "Last week", mimeType: "video"),
        LegacyVaultFile(name: "Secret Keys.txt", size: "12 KB", modified: "2 weeks ago", mimeType: "code")
    ]
}

// MARK: - New Folder Dialog

struct NewFolderDialog: View {
    @Binding var folderName: String
    @Binding var isPresented: Bool
    let onCreate: () -> Void

    var body: some View {
        VStack(spacing: 24) {
            // Header
            HStack {
                Text("New Folder")
                    .font(.system(size: 20, weight: .semibold))

                Spacer()

                Button {
                    isPresented = false
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 16))
                        .foregroundColor(.secondary)
                        .frame(width: 28, height: 28)
                }
                .buttonStyle(.plain)
            }

            Divider()

            // Form
            VStack(alignment: .leading, spacing: 12) {
                Text("Folder Name")
                    .font(.headline)

                TextField("Enter folder name", text: $folderName)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit {
                        onCreate()
                        isPresented = false
                    }
            }

            Spacer()

            // Footer buttons
            HStack {
                Spacer()

                Button("Cancel") {
                    isPresented = false
                }
                .keyboardShortcut(.cancelAction)

                Button("Create") {
                    onCreate()
                    isPresented = false
                }
                .keyboardShortcut(.defaultAction)
                .disabled(folderName.isEmpty)
            }
        }
        .padding(24)
        .frame(width: 400, height: 250)
        .background(Color(nsColor: .windowBackgroundColor))
    }
}

// MARK: - File Preview Modal

struct FilePreviewModal: View {
    let file: VaultFile
    @Binding var isPresented: Bool
    let onDownload: () -> Void
    let onDelete: () -> Void
    let vaultPassword: String

    @State private var isDownloading: Bool = false
    @State private var downloadError: String? = nil
    @State private var downloadSuccess: Bool = false

    private let vaultService = VaultService.shared

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(file.name)
                        .font(.system(size: 16, weight: .semibold))

                    HStack(spacing: 8) {
                        Text(file.mimeType?.uppercased() ?? "FILE")
                            .font(.system(size: 12))
                            .foregroundColor(.secondary)

                        Text("•")
                            .font(.system(size: 12))
                            .foregroundColor(.secondary)

                        Text(file.sizeFormatted)
                            .font(.system(size: 12))
                            .foregroundColor(.secondary)
                    }
                }

                Spacer()

                Button {
                    isPresented = false
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 16))
                        .foregroundColor(.secondary)
                        .frame(width: 32, height: 32)
                }
                .buttonStyle(.plain)
            }
            .padding(24)
            .background(Color(.controlBackgroundColor))
            .overlay(
                Rectangle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(height: 1),
                alignment: .bottom
            )

            // Body
            VStack(spacing: 16) {
                Image(systemName: file.mimeIcon)
                    .font(.system(size: 64))
                    .foregroundColor(Color(file.mimeColor))

                Text("Preview for \(file.mimeType ?? "unknown") files")
                    .font(.title2)

                Text("File preview rendering will appear here")
                    .font(.subheadline)
                    .foregroundColor(.secondary)

                // Download status messages
                if downloadSuccess {
                    HStack(spacing: 8) {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(.green)
                        Text("File downloaded successfully")
                            .font(.system(size: 14))
                            .foregroundColor(.green)
                    }
                    .padding(.top, 8)
                }

                if let error = downloadError {
                    HStack(spacing: 8) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(.red)
                        Text(error)
                            .font(.system(size: 14))
                            .foregroundColor(.red)
                    }
                    .padding(.top, 8)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding(24)

            // Footer
            HStack(spacing: 12) {
                Button {
                    onDelete()
                    isPresented = false
                } label: {
                    HStack(spacing: 8) {
                        Image(systemName: "trash")
                            .font(.system(size: 16))
                        Text("Delete")
                            .font(.system(size: 14, weight: .medium))
                    }
                    .foregroundColor(.red)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .strokeBorder(Color.red, lineWidth: 1)
                    )
                }
                .buttonStyle(.plain)
                .disabled(isDownloading)

                Spacer()

                Button {
                    Task {
                        await handleDownload()
                    }
                } label: {
                    HStack(spacing: 8) {
                        if isDownloading {
                            ProgressView()
                                .scaleEffect(0.8)
                                .frame(width: 16, height: 16)
                        } else {
                            Image(systemName: downloadSuccess ? "checkmark.circle" : "arrow.down.circle")
                                .font(.system(size: 16))
                        }
                        Text(isDownloading ? "Downloading..." : (downloadSuccess ? "Downloaded" : "Download"))
                            .font(.system(size: 14, weight: .medium))
                    }
                    .foregroundColor(.white)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(downloadSuccess ? Color.green : Color.magnetarPrimary)
                    )
                }
                .buttonStyle(.plain)
                .disabled(isDownloading || downloadSuccess)
            }
            .padding(24)
            .background(Color(.controlBackgroundColor))
            .overlay(
                Rectangle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(height: 1),
                alignment: .top
            )
        }
        .frame(width: 700, height: 600)
        .background(Color(.windowBackgroundColor))
    }

    // MARK: - Download Handler

    @MainActor
    private func handleDownload() async {
        // Reset states
        downloadError = nil
        downloadSuccess = false

        // Show save panel
        let savePanel = NSSavePanel()
        savePanel.nameFieldStringValue = file.name
        savePanel.canCreateDirectories = true
        savePanel.showsTagField = false

        let response = savePanel.runModal()

        // User cancelled
        guard response == .OK, let destinationURL = savePanel.url else {
            return
        }

        // Start download
        isDownloading = true

        do {
            let data = try await vaultService.download(
                fileId: file.id,
                vaultType: "real",
                passphrase: vaultPassword
            )

            try data.write(to: destinationURL)

            downloadSuccess = true
            isDownloading = false

            // Auto-close after success (optional)
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                isPresented = false
            }
        } catch let error as VaultError {
            downloadError = error.localizedDescription
            isDownloading = false
        } catch {
            downloadError = "Download failed: \(error.localizedDescription)"
            isDownloading = false
        }
    }
}

// MARK: - Placeholder Modals

struct DiagnosticsPanel: View {
    @Environment(\.dismiss) var dismiss
    @State private var isLoading: Bool = false
    @State private var errorMessage: String? = nil
    @State private var diagnostics: DiagnosticsStatus? = nil

    private let teamService = TeamService.shared

    var body: some View {
        VStack(spacing: 20) {
            // Header
            HStack {
                Text("Network Diagnostics")
                    .font(.title2.weight(.semibold))

                Spacer()

                Button(action: { Task { await loadDiagnostics() } }) {
                    HStack(spacing: 4) {
                        Image(systemName: "arrow.clockwise")
                        Text("Retry")
                    }
                }
                .disabled(isLoading)
            }

            if isLoading {
                VStack(spacing: 12) {
                    ProgressView()
                    Text("Loading diagnostics...")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if let diag = diagnostics {
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        // Overall Status
                        HStack {
                            Image(systemName: diag.status == "ok" ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                                .foregroundColor(diag.status == "ok" ? .green : .orange)
                            Text("Status: \(diag.status.uppercased())")
                                .font(.system(size: 14, weight: .medium))
                        }

                        Divider()

                        // Network Status
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Network")
                                .font(.system(size: 13, weight: .semibold))

                            statusRow("Connected", value: diag.network.connected ? "Yes" : "No", status: diag.network.connected)

                            if let latency = diag.network.latency {
                                statusRow("Latency", value: "\(latency)ms", status: latency < 100)
                            }

                            if let bandwidth = diag.network.bandwidth {
                                statusRow("Bandwidth", value: bandwidth, status: true)
                            }
                        }

                        Divider()

                        // Database Status
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Database")
                                .font(.system(size: 13, weight: .semibold))

                            statusRow("Connected", value: diag.database.connected ? "Yes" : "No", status: diag.database.connected)

                            if let queryTime = diag.database.queryTime {
                                statusRow("Query Time", value: "\(queryTime)ms", status: queryTime < 100)
                            }
                        }

                        Divider()

                        // Services
                        if !diag.services.isEmpty {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Services")
                                    .font(.system(size: 13, weight: .semibold))

                                ForEach(diag.services, id: \.name) { service in
                                    HStack {
                                        Image(systemName: service.status == "running" ? "checkmark.circle.fill" : "xmark.circle.fill")
                                            .foregroundColor(service.status == "running" ? .green : .red)
                                            .font(.system(size: 12))

                                        Text(service.name)
                                            .font(.system(size: 12))

                                        Spacer()

                                        if let uptime = service.uptime {
                                            Text(uptime)
                                                .font(.caption)
                                                .foregroundColor(.secondary)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            } else if let error = errorMessage {
                VStack(spacing: 12) {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.largeTitle)
                        .foregroundColor(.orange)

                    Text(error)
                        .font(.caption)
                        .foregroundColor(.red)
                        .multilineTextAlignment(.center)

                    Button("Retry") {
                        Task { await loadDiagnostics() }
                    }
                    .buttonStyle(.borderedProminent)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }

            // Close button
            Button("Close") {
                dismiss()
            }
            .keyboardShortcut(.escape)
        }
        .frame(width: 600, height: 400)
        .padding(24)
        .onAppear {
            Task { await loadDiagnostics() }
        }
    }

    @ViewBuilder
    private func statusRow(_ label: String, value: String, status: Bool) -> some View {
        HStack {
            Image(systemName: status ? "checkmark.circle.fill" : "xmark.circle.fill")
                .foregroundColor(status ? .green : .red)
                .font(.system(size: 12))

            Text(label)
                .font(.system(size: 12))

            Spacer()

            Text(value)
                .font(.system(size: 12))
                .foregroundColor(.secondary)
        }
    }

    @MainActor
    private func loadDiagnostics() async {
        isLoading = true
        errorMessage = nil

        do {
            diagnostics = try await teamService.getDiagnostics()
        } catch {
            errorMessage = "Failed to load diagnostics: \(error.localizedDescription)"
        }

        isLoading = false
    }
}

struct CreateTeamModal: View {
    @Environment(\.dismiss) var dismiss
    @State private var teamName: String = ""
    @State private var teamDescription: String = ""
    @State private var isLoading: Bool = false
    @State private var errorMessage: String? = nil

    private let teamService = TeamService.shared

    var body: some View {
        VStack(spacing: 20) {
            // Header
            Text("Create Team")
                .font(.title2.weight(.semibold))

            // Form
            VStack(alignment: .leading, spacing: 16) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Team Name")
                        .font(.system(size: 13, weight: .medium))
                    TextField("Enter team name", text: $teamName)
                        .textFieldStyle(.roundedBorder)
                        .disabled(isLoading)
                }

                VStack(alignment: .leading, spacing: 6) {
                    Text("Description (Optional)")
                        .font(.system(size: 13, weight: .medium))
                    TextEditor(text: $teamDescription)
                        .frame(height: 80)
                        .border(Color.gray.opacity(0.3))
                        .disabled(isLoading)
                }
            }

            // Error message
            if let error = errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            // Actions
            HStack(spacing: 12) {
                Button("Cancel") {
                    dismiss()
                }
                .keyboardShortcut(.escape)
                .disabled(isLoading)

                Button("Create Team") {
                    Task { await createTeam() }
                }
                .keyboardShortcut(.return)
                .buttonStyle(.borderedProminent)
                .disabled(teamName.isEmpty || isLoading)
            }

            if isLoading {
                ProgressView()
                    .scaleEffect(0.8)
            }
        }
        .frame(width: 500)
        .padding(24)
    }

    @MainActor
    private func createTeam() async {
        isLoading = true
        errorMessage = nil

        do {
            _ = try await teamService.createTeam(
                name: teamName,
                description: teamDescription.isEmpty ? nil : teamDescription
            )
            dismiss()
        } catch {
            errorMessage = "Failed to create team: \(error.localizedDescription)"
        }

        isLoading = false
    }
}

struct JoinTeamModal: View {
    @Environment(\.dismiss) var dismiss
    @State private var teamCode: String = ""
    @State private var isLoading: Bool = false
    @State private var errorMessage: String? = nil

    private let teamService = TeamService.shared

    var body: some View {
        VStack(spacing: 20) {
            // Header
            Text("Join Team")
                .font(.title2.weight(.semibold))

            Text("Enter the team invitation code to join")
                .font(.system(size: 13))
                .foregroundColor(.secondary)

            // Form
            VStack(alignment: .leading, spacing: 6) {
                Text("Team Code")
                    .font(.system(size: 13, weight: .medium))
                TextField("Enter invitation code", text: $teamCode)
                    .textFieldStyle(.roundedBorder)
                    .disabled(isLoading)
                    .font(.system(.body, design: .monospaced))
            }

            // Error message
            if let error = errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            // Actions
            HStack(spacing: 12) {
                Button("Cancel") {
                    dismiss()
                }
                .keyboardShortcut(.escape)
                .disabled(isLoading)

                Button("Join Team") {
                    Task { await joinTeam() }
                }
                .keyboardShortcut(.return)
                .buttonStyle(.borderedProminent)
                .disabled(teamCode.isEmpty || isLoading)
            }

            if isLoading {
                ProgressView()
                    .scaleEffect(0.8)
            }
        }
        .frame(width: 450)
        .padding(24)
    }

    @MainActor
    private func joinTeam() async {
        isLoading = true
        errorMessage = nil

        do {
            _ = try await teamService.joinTeam(code: teamCode)
            dismiss()
        } catch {
            errorMessage = "Failed to join team: \(error.localizedDescription)"
        }

        isLoading = false
    }
}

struct VaultSetupModal: View {
    @Environment(\.dismiss) var dismiss
    @State private var password: String = ""
    @State private var confirmPassword: String = ""
    @State private var isLoading: Bool = false
    @State private var errorMessage: String? = nil
    @State private var setupStatus: String? = nil

    private let teamService = TeamService.shared

    var body: some View {
        VStack(spacing: 20) {
            // Header
            Text("Vault Setup")
                .font(.title2.weight(.semibold))

            Text("Set up encrypted vault for secure file storage")
                .font(.system(size: 13))
                .foregroundColor(.secondary)

            // Form
            VStack(alignment: .leading, spacing: 16) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Master Password")
                        .font(.system(size: 13, weight: .medium))
                    SecureField("Enter master password", text: $password)
                        .textFieldStyle(.roundedBorder)
                        .disabled(isLoading)
                }

                VStack(alignment: .leading, spacing: 6) {
                    Text("Confirm Password")
                        .font(.system(size: 13, weight: .medium))
                    SecureField("Re-enter password", text: $confirmPassword)
                        .textFieldStyle(.roundedBorder)
                        .disabled(isLoading)
                }

                Text("⚠️ Store this password securely. It cannot be recovered.")
                    .font(.caption)
                    .foregroundColor(.orange)
            }

            // Status/Error message
            if let status = setupStatus {
                Text(status)
                    .font(.caption)
                    .foregroundColor(.green)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            if let error = errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            // Actions
            HStack(spacing: 12) {
                Button("Cancel") {
                    dismiss()
                }
                .keyboardShortcut(.escape)
                .disabled(isLoading)

                Button("Setup Vault") {
                    Task { await setupVault() }
                }
                .keyboardShortcut(.return)
                .buttonStyle(.borderedProminent)
                .disabled(!canSubmit || isLoading)
            }

            if isLoading {
                ProgressView()
                    .scaleEffect(0.8)
            }
        }
        .frame(width: 500)
        .padding(24)
    }

    private var canSubmit: Bool {
        !password.isEmpty && password == confirmPassword && password.count >= 8
    }

    @MainActor
    private func setupVault() async {
        isLoading = true
        errorMessage = nil
        setupStatus = nil

        do {
            let response = try await teamService.setupVault(password: password)
            setupStatus = response.message
            try? await Task.sleep(nanoseconds: 1_500_000_000)
            dismiss()
        } catch {
            errorMessage = "Setup failed: \(error.localizedDescription)"
        }

        isLoading = false
    }
}

// MARK: - Preview

#Preview {
    TeamWorkspace()
        .frame(width: 1200, height: 800)
}
