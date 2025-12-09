//
//  TeamWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Team collaboration workspace - matches React app layout exactly
//  Refactored in Phase 6.23 - extracted toolbar, sidebar, detail, data manager, and models
//

import SwiftUI

// MARK: - Models

// TeamView private to avoid conflicts with main TeamWorkspace.swift
private enum TeamView {
    case chat
    case docs
}

// TeamMember defined in TeamWorkspaceModelsV2.swift (Phase 6.23)
// PlaceholderSheet defined inline below

struct PlaceholderSheet: View {
    let title: String
    let message: String
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 20) {
            HStack {
                Text(title)
                    .font(.system(size: 18, weight: .bold))
                Spacer()
                Button("Done") {
                    dismiss()
                }
                .buttonStyle(.bordered)
            }
            .padding(20)

            Divider()

            VStack(spacing: 16) {
                Image(systemName: "wrench.and.screwdriver")
                    .font(.system(size: 48))
                    .foregroundColor(.secondary)

                Text(message)
                    .font(.headline)
                    .foregroundColor(.secondary)
                    .multilineTextAlignment(.center)
                    .padding(.horizontal, 40)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        }
        .frame(width: 500, height: 400)
    }
}

// MARK: - Main View

struct TeamWorkspace: View {
    @State private var selectedView: TeamView = .chat
    @State private var selectedTeamMember: TeamMember? = nil
    @State private var showNetworkStatus: Bool = false
    @State private var showDiagnostics: Bool = false
    @State private var showDataLab: Bool = false
    @State private var showAddMember: Bool = false

    // Manager (Phase 6.23)
    @State private var dataManager = TeamWorkspaceDataManager()

    var body: some View {
        VStack(spacing: 0) {
            // Horizontal Toolbar
            TeamWorkspaceToolbar(
                selectedView: $selectedView,
                onShowNetworkStatus: { showNetworkStatus = true },
                onShowDiagnostics: { showDiagnostics = true },
                onShowDataLab: { showDataLab = true }
            )

            Divider()

            // Two panes below
            HStack(spacing: 0) {
                // Left Sidebar
                TeamMemberSidebar(
                    teamMembers: dataManager.teamMembers,
                    selectedTeamMember: selectedTeamMember,
                    onSelectMember: { member in
                        selectedTeamMember = member
                    },
                    onAddMember: { showAddMember = true }
                )

                Divider()

                // Main Content
                if let member = selectedTeamMember {
                    TeamMemberDetail(member: member)
                } else {
                    VStack(spacing: 16) {
                        Image(systemName: "person.2")
                            .font(.system(size: 48))
                            .foregroundStyle(LinearGradient.magnetarGradient.opacity(0.7))

                        Text("No member selected")
                            .font(.title3)
                            .fontWeight(.semibold)

                        Text("Select a team member to view details")
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                    .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
            }
        }
        .task {
            await dataManager.loadTeamMembers()
        }
        .sheet(isPresented: $showNetworkStatus) {
            PlaceholderSheet(title: "Network Status", message: "Network discovery and P2P mesh status will appear here")
        }
        .sheet(isPresented: $showDiagnostics) {
            PlaceholderSheet(title: "Diagnostics", message: "Team collaboration diagnostics and health metrics will appear here")
        }
        .sheet(isPresented: $showDataLab) {
            PlaceholderSheet(title: "Data Lab", message: "Collaborative data analysis tools will appear here")
        }
        .sheet(isPresented: $showAddMember) {
            PlaceholderSheet(title: "Add Team Member", message: "Invite team members via email or connection code")
        }
    }
}

// Components extracted to:
// - Team/TeamWorkspaceToolbar.swift (Phase 6.23)
// - Team/TeamMemberSidebar.swift (Phase 6.23)
// - Team/TeamMemberDetailView.swift (Phase 6.23)
// - Team/TeamWorkspaceDataManager.swift (Phase 6.23)

#Preview {
    TeamWorkspace()
        .frame(width: 1200, height: 800)
}
