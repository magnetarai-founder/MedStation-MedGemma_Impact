//
//  TeamWorkspaceDataManager.swift
//  MagnetarStudio (macOS)
//
//  Data manager for TeamWorkspace - Extracted from TeamWorkspace_v2.swift (Phase 6.23)
//

import SwiftUI

@MainActor
@Observable
class TeamWorkspaceDataManager {
    var teamMembers: [TeamMember] = []
    var isLoading: Bool = false

    func loadTeamMembers() async {
        do {
            // Get current user's teams
            guard let userId = AuthStore.shared.user?.id else {
                print("⚠️ No current user, cannot load teams")
                return
            }

            // Call backend to get user's teams
            struct UserTeamsResponse: Codable {
                let user_id: String
                let teams: [TeamInfo]
            }

            struct TeamInfo: Codable {
                let team_id: String
                let name: String
                let description: String?
            }

            let response: UserTeamsResponse = try await ApiClient.shared.request(
                "/v1/teams/user/\(userId)/teams",
                method: .get
            )

            // If user has teams, load members from the first team
            if let firstTeam = response.teams.first {
                try await loadMembersForTeam(teamId: firstTeam.team_id)
            } else {
                // No teams yet, show empty state
                teamMembers = []
            }
        } catch {
            print("⚠️ Failed to load team members: \(error)")
            // Fallback to empty array instead of mock data
            teamMembers = []
        }
    }

    private func loadMembersForTeam(teamId: String) async throws {
        struct TeamMemberResponse: Codable {
            let user_id: String
            let username: String
            let role: String
            let status: String?
        }

        let members: [TeamMemberResponse] = try await ApiClient.shared.request(
            "/v1/teams/\(teamId)/members",
            method: .get
        )

        // Convert to UI model
        teamMembers = members.map { member in
            TeamMember(
                id: member.user_id,
                name: member.username,
                role: member.role,
                status: member.status ?? "offline",
                avatar: nil
            )
        }
    }
}
