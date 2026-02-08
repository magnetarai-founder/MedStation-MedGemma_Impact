//
//  TeamMemberSidebar.swift
//  MagnetarStudio (macOS)
//
//  Team member sidebar - Extracted from TeamWorkspace_v2.swift (Phase 6.23)
//  Enhanced with search, online counts, and hover effects
//

import SwiftUI

struct TeamMemberSidebar: View {
    let teamMembers: [TeamMember]
    let selectedTeamMember: TeamMember?
    let onSelectMember: (TeamMember) -> Void
    let onAddMember: () -> Void

    @State private var searchText: String = ""

    var filteredMembers: [TeamMember] {
        if searchText.isEmpty {
            return teamMembers
        }
        return teamMembers.filter {
            $0.name.localizedCaseInsensitiveContains(searchText) ||
            $0.role.localizedCaseInsensitiveContains(searchText)
        }
    }

    var onlineCount: Int {
        teamMembers.filter { $0.isOnline }.count
    }

    var body: some View {
        VStack(spacing: 0) {
            // Sidebar header
            HStack {
                Text("Team Members")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(Color.textPrimary)

                // Online count badge
                HStack(spacing: 4) {
                    Circle()
                        .fill(Color.green)
                        .frame(width: 6, height: 6)
                    Text("\(onlineCount)")
                        .font(.system(size: 10, weight: .medium))
                }
                .foregroundStyle(.secondary)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(Color.green.opacity(0.1))
                .clipShape(Capsule())

                Spacer()

                Button(action: onAddMember) {
                    Image(systemName: "person.badge.plus")
                        .font(.system(size: 14))
                        .foregroundStyle(LinearGradient.magnetarGradient)
                }
                .buttonStyle(.plain)
                .help("Add team member")
            }
            .padding(12)
            .background(Color.surfaceSecondary.opacity(0.3))

            // Search bar
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
                TextField("Search members...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 12))
                if !searchText.isEmpty {
                    Button(action: { searchText = "" }) {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 11))
                            .foregroundStyle(.tertiary)
                    }
                    .buttonStyle(.plain)
                }
            }
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(Color.gray.opacity(0.1))
            .clipShape(RoundedRectangle(cornerRadius: 6))
            .padding(.horizontal, 8)
            .padding(.vertical, 8)

            Divider()

            // Member list
            if filteredMembers.isEmpty {
                VStack(spacing: 12) {
                    Image(systemName: searchText.isEmpty ? "person.3" : "magnifyingglass")
                        .font(.system(size: 32))
                        .foregroundStyle(.tertiary)
                    Text(searchText.isEmpty ? "No Members" : "No Matches")
                        .font(.headline)
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    LazyVStack(spacing: 2) {
                        ForEach(filteredMembers) { member in
                            TeamMemberRow(
                                member: member,
                                isSelected: selectedTeamMember?.id == member.id
                            )
                            .onTapGesture {
                                onSelectMember(member)
                            }
                        }
                    }
                    .padding(.vertical, 4)
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
    var onMessage: (() -> Void)? = nil
    var onCall: (() -> Void)? = nil

    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 12) {
            // Avatar with online indicator
            ZStack(alignment: .bottomTrailing) {
                Circle()
                    .fill(LinearGradient.magnetarGradient)
                    .frame(width: 36, height: 36)
                    .overlay(
                        Text(member.initials)
                            .font(.system(size: 12, weight: .semibold))
                            .foregroundStyle(.white)
                    )

                // Online indicator
                Circle()
                    .fill(member.isOnline ? Color.green : Color.gray)
                    .frame(width: 10, height: 10)
                    .overlay(
                        Circle()
                            .stroke(Color(nsColor: .windowBackgroundColor), lineWidth: 2)
                    )
                    .offset(x: 2, y: 2)
            }

            VStack(alignment: .leading, spacing: 2) {
                Text(member.name)
                    .font(.system(size: 13, weight: isSelected ? .semibold : .medium))
                    .foregroundStyle(isSelected ? .primary : Color.textPrimary)

                HStack(spacing: 4) {
                    Text(member.role)
                        .font(.system(size: 11))
                        .foregroundStyle(Color.textSecondary)

                    if isHovered && !member.lastActive.isEmpty {
                        Text("•")
                            .font(.system(size: 8))
                            .foregroundStyle(.tertiary)
                        Text(member.lastActive)
                            .font(.system(size: 10))
                            .foregroundStyle(.tertiary)
                    }
                }
            }

            Spacer()

            // Hover actions
            if isHovered && !isSelected {
                HStack(spacing: 4) {
                    if let onMessage = onMessage {
                        MemberActionButton(icon: "message", color: .blue, action: onMessage)
                    }
                    if let onCall = onCall, member.isOnline {
                        MemberActionButton(icon: "phone", color: .green, action: onCall)
                    }
                }
                .transition(.opacity.combined(with: .scale(scale: 0.9)))
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(isSelected ? Color.magnetarPrimary.opacity(0.15) : (isHovered ? Color.gray.opacity(0.05) : Color.clear))
        )
        .padding(.horizontal, 4)
        .contentShape(Rectangle())
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.1)) {
                isHovered = hovering
            }
        }
    }
}

// MARK: - Member Action Button

private struct MemberActionButton: View {
    let icon: String
    let color: Color
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 11))
                .foregroundStyle(isHovered ? color : .secondary)
                .frame(width: 24, height: 24)
                .background(
                    Circle()
                        .fill(isHovered ? color.opacity(0.1) : Color.gray.opacity(0.1))
                )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            isHovered = hovering
        }
    }
}
