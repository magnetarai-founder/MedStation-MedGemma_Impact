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

// MARK: - Team Service Models & Service
// All models (Team, TeamDocument, TeamMessage, DiagnosticsStatus, P2PNetworkStatus, UserPermissions, etc.)
// are imported from Shared/Services/TeamService.swift

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
    @State private var permissions: UserPermissions? = nil
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
                if permissions?.canAccessDocuments ?? true {
                    TeamTabButton(
                        title: "Docs",
                        icon: "doc.text",
                        isActive: workspaceView == .docs,
                        tintColor: Color.magnetarPrimary,
                        action: { workspaceView = .docs }
                    )
                }

                // Workflows
                if permissions?.canAccessAutomation ?? true {
                    TeamTabButton(
                        title: "Workflows",
                        icon: "arrow.triangle.branch",
                        isActive: workspaceView == .workflows,
                        tintColor: Color.magnetarPrimary,
                        action: { workspaceView = .workflows }
                    )
                }

                // Divider before Vault
                if permissions?.canAccessVault ?? true {
                    Rectangle()
                        .fill(Color.gray.opacity(0.3))
                        .frame(width: 1, height: 24)
                        .padding(.horizontal, 8)
                }

                // Vault (amber tint)
                if permissions?.canAccessVault ?? true {
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

// AutomationWorkspace moved to Shared/Components/AutomationWorkspace.swift



