//
//  TeamMemberDetailView.swift
//  MagnetarStudio (macOS)
//
//  Team member detail view - Extracted from TeamWorkspace_v2.swift (Phase 6.23)
//

import SwiftUI

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
