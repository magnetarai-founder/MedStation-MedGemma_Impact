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
            AutomationWorkspace()
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

    var body: some View {
        VStack {
            Text("Team Chat")
                .font(.title)
            Text("Mode: \(mode.displayName)")
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct DocsWorkspace: View {
    var body: some View {
        VStack {
            Image(systemName: "doc.text")
                .font(.system(size: 64))
                .foregroundColor(.secondary)
            Text("Documents Workspace")
                .font(.title)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct AutomationWorkspace: View {
    var body: some View {
        VStack {
            Image(systemName: "arrow.triangle.branch")
                .font(.system(size: 64))
                .foregroundColor(.secondary)
            Text("Workflows & Automation")
                .font(.title)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

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
