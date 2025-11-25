//
//  TeamWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Team collaboration workspace - matches React app layout exactly
//

import SwiftUI

struct TeamWorkspace: View {
    @State private var selectedView: TeamView = .chat
    @State private var selectedTeamMember: TeamMember? = nil

    var body: some View {
        VStack(spacing: 0) {
            // Horizontal Toolbar
            HStack(spacing: 12) {
                // Network status indicator
                Button(action: {}) {
                    HStack(spacing: 6) {
                        Image(systemName: "globe")
                            .font(.system(size: 14))
                        Text("Local Network")
                            .font(.system(size: 13))
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(Color.surfaceSecondary)
                    .cornerRadius(6)
                }
                .buttonStyle(.plain)

                // Diagnostics
                Button(action: {}) {
                    HStack(spacing: 6) {
                        Image(systemName: "waveform.path.ecg")
                            .font(.system(size: 14))
                        Text("Diagnostics")
                            .font(.system(size: 13))
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(Color.surfaceSecondary)
                    .cornerRadius(6)
                }
                .buttonStyle(.plain)

                // Divider
                Rectangle()
                    .fill(Color.gray.opacity(0.3))
                    .frame(width: 1, height: 24)

                // View tabs
                Button(action: { selectedView = .chat }) {
                    HStack(spacing: 6) {
                        Image(systemName: "bubble.left")
                            .font(.system(size: 14))
                        Text("Chat")
                            .font(.system(size: 13, weight: .medium))
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(selectedView == .chat ? Color.magnetarPrimary.opacity(0.15) : Color.clear)
                    .foregroundColor(selectedView == .chat ? .magnetarPrimary : .textSecondary)
                    .cornerRadius(6)
                }
                .buttonStyle(.plain)

                Button(action: { selectedView = .docs }) {
                    HStack(spacing: 6) {
                        Image(systemName: "doc.text")
                            .font(.system(size: 14))
                        Text("Docs")
                            .font(.system(size: 13, weight: .medium))
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(selectedView == .docs ? Color.magnetarPrimary.opacity(0.15) : Color.clear)
                    .foregroundColor(selectedView == .docs ? .magnetarPrimary : .textSecondary)
                    .cornerRadius(6)
                }
                .buttonStyle(.plain)

                Button(action: {}) {
                    HStack(spacing: 6) {
                        Image(systemName: "cylinder")
                            .font(.system(size: 14))
                        Text("Data Lab")
                            .font(.system(size: 13))
                    }
                    .padding(.horizontal, 12)
                    .padding(.vertical, 6)
                    .background(Color.surfaceSecondary)
                    .cornerRadius(6)
                }
                .buttonStyle(.plain)

                Spacer()
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color.surfaceTertiary.opacity(0.3))

            Divider()

            // Two panes below
            HStack(spacing: 0) {
                // Left Sidebar
                VStack(spacing: 0) {
                    // Sidebar header
                    HStack {
                        Text("Team Members")
                            .font(.system(size: 13, weight: .semibold))
                            .foregroundColor(.textPrimary)

                        Spacer()

                        Button(action: {}) {
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
                            ForEach(TeamMember.mockMembers) { member in
                                TeamMemberRow(
                                    member: member,
                                    isSelected: selectedTeamMember?.id == member.id
                                )
                                .onTapGesture {
                                    selectedTeamMember = member
                                }
                            }
                        }
                    }
                }
                .frame(width: 260)
                .background(Color.surfaceSecondary.opacity(0.5))

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
    }
}

// MARK: - Supporting Views

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

struct TeamMemberDetail: View {
    let member: TeamMember

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                // Header
                HStack(spacing: 16) {
                    Circle()
                        .fill(LinearGradient.magnetarGradient)
                        .frame(width: 72, height: 72)
                        .overlay(
                            Text(member.initials)
                                .font(.title2)
                                .fontWeight(.bold)
                                .foregroundColor(.white)
                        )

                    VStack(alignment: .leading, spacing: 4) {
                        Text(member.name)
                            .font(.title2)
                            .fontWeight(.bold)

                        Text(member.role)
                            .font(.subheadline)
                            .foregroundColor(.secondary)

                        HStack(spacing: 4) {
                            Circle()
                                .fill(member.isOnline ? Color.green : Color.gray)
                                .frame(width: 8, height: 8)
                            Text(member.isOnline ? "Online" : "Offline")
                                .font(.caption)
                                .foregroundColor(.secondary)
                        }
                    }

                    Spacer()
                }

                Divider()

                // Contact info
                VStack(alignment: .leading, spacing: 16) {
                    Text("Contact Information")
                        .font(.headline)

                    VStack(alignment: .leading, spacing: 12) {
                        HStack(spacing: 12) {
                            Image(systemName: "envelope")
                                .foregroundColor(.secondary)
                                .frame(width: 20)
                            VStack(alignment: .leading, spacing: 2) {
                                Text("Email")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                Text(member.email)
                                    .font(.body)
                            }
                        }

                        HStack(spacing: 12) {
                            Image(systemName: "phone")
                                .foregroundColor(.secondary)
                                .frame(width: 20)
                            VStack(alignment: .leading, spacing: 2) {
                                Text("Phone")
                                    .font(.caption)
                                    .foregroundColor(.secondary)
                                Text(member.phone)
                                    .font(.body)
                            }
                        }
                    }
                }

                Divider()

                // Activity
                VStack(alignment: .leading, spacing: 12) {
                    Text("Recent Activity")
                        .font(.headline)

                    Text("Last active: \(member.lastActive)")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }

                Spacer()
            }
            .padding(24)
        }
    }
}

// MARK: - Models

enum TeamView {
    case chat
    case docs
}

struct TeamMember: Identifiable {
    let id = UUID()
    let name: String
    let role: String
    let email: String
    let phone: String
    let isOnline: Bool
    let lastActive: String

    var initials: String {
        let parts = name.split(separator: " ")
        return parts.compactMap { $0.first }.prefix(2).map { String($0) }.joined()
    }

    static let mockMembers = [
        TeamMember(name: "Alice Johnson", role: "Engineering Lead", email: "alice@magnetar.studio", phone: "+1 (555) 123-4567", isOnline: true, lastActive: "Just now"),
        TeamMember(name: "Bob Smith", role: "Senior Engineer", email: "bob@magnetar.studio", phone: "+1 (555) 234-5678", isOnline: true, lastActive: "2 minutes ago"),
        TeamMember(name: "Carol Davis", role: "Engineer", email: "carol@magnetar.studio", phone: "+1 (555) 345-6789", isOnline: false, lastActive: "1 hour ago"),
        TeamMember(name: "David Wilson", role: "Engineer", email: "david@magnetar.studio", phone: "+1 (555) 456-7890", isOnline: true, lastActive: "Just now"),
        TeamMember(name: "Eve Martinez", role: "Junior Engineer", email: "eve@magnetar.studio", phone: "+1 (555) 567-8901", isOnline: false, lastActive: "Yesterday")
    ]
}

#Preview {
    TeamWorkspace()
        .frame(width: 1200, height: 800)
}
