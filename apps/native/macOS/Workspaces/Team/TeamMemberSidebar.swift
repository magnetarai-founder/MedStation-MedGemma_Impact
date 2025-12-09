//
//  TeamMemberSidebar.swift
//  MagnetarStudio (macOS)
//
//  Team member sidebar - Extracted from TeamWorkspace_v2.swift (Phase 6.23)
//

import SwiftUI

struct TeamMemberSidebar: View {
    let teamMembers: [TeamMember]
    let selectedTeamMember: TeamMember?
    let onSelectMember: (TeamMember) -> Void
    let onAddMember: () -> Void

    var body: some View {
        VStack(spacing: 0) {
            // Sidebar header
            HStack {
                Text("Team Members")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(.textPrimary)

                Spacer()

                Button(action: onAddMember) {
                    Image(systemName: "person.badge.plus")
                        .font(.system(size: 14))
                        .foregroundStyle(LinearGradient.magnetarGradient)
                }
                .buttonStyle(.plain)
            }
            .padding(12)
            .background(Color.surfaceSecondary.opacity(0.3))

            Divider()

            // Member list
            ScrollView {
                LazyVStack(spacing: 0) {
                    ForEach(teamMembers) { member in
                        TeamMemberRow(
                            member: member,
                            isSelected: selectedTeamMember?.id == member.id
                        )
                        .onTapGesture {
                            onSelectMember(member)
                        }
                    }
                }
            }
        }
        .frame(width: 260)
        .background(Color.surfaceSecondary.opacity(0.5))
    }
}

// MARK: - Team Member Row

struct TeamMemberRow: View {
    let member: TeamMember
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 12) {
            Circle()
                .fill(LinearGradient.magnetarGradient)
                .frame(width: 36, height: 36)
                .overlay(
                    Text(member.initials)
                        .font(.system(size: 12, weight: .semibold))
                        .foregroundColor(.white)
                )

            VStack(alignment: .leading, spacing: 2) {
                Text(member.name)
                    .font(.system(size: 13, weight: .medium))
                    .foregroundColor(.textPrimary)

                Text(member.role)
                    .font(.system(size: 11))
                    .foregroundColor(.textSecondary)
            }

            Spacer()

            Circle()
                .fill(member.isOnline ? Color.green : Color.gray)
                .frame(width: 8, height: 8)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(isSelected ? Color.magnetarPrimary.opacity(0.1) : Color.clear)
    }
}
