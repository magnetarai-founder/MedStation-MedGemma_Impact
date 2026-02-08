//
//  HubCloudStatus.swift
//  MagnetarStudio (macOS)
//
//  MagnetarCloud connection status with controls - Extracted from MagnetarHubWorkspace.swift (Phase 6.12)
//  Enhanced with hover effects and improved status indicators
//

import SwiftUI

struct HubCloudStatus: View {
    let isAuthenticated: Bool
    let isActionInProgress: Bool
    let username: String?
    let onConnect: () -> Void
    let onDisconnect: () -> Void
    let onReconnect: () -> Void

    // Sync status (Tier 15)
    var isSyncing: Bool = false
    var pendingChanges: Int = 0
    var activeConflicts: Int = 0
    var onSync: (() -> Void)? = nil

    @State private var isHovered = false

    var body: some View {
        if isAuthenticated {
            authenticatedView
        } else {
            unauthenticatedView
        }
    }

    private var authenticatedView: some View {
        VStack(spacing: 6) {
            HStack(spacing: 8) {
                // Status indicator
                statusIndicator

                VStack(alignment: .leading, spacing: 2) {
                    Text("MagnetarCloud")
                        .font(.caption)
                        .fontWeight(.medium)

                    Text("\(username ?? "User") Connected")
                        .font(.caption2)
                        .foregroundStyle(.secondary)
                }

                Spacer()

                // Control buttons with hover effects
                HStack(spacing: 4) {
                    // Sync button
                    if onSync != nil {
                        StatusActionButton(
                            icon: "arrow.triangle.2.circlepath",
                            color: .magnetarPrimary,
                            help: "Sync now",
                            disabled: isActionInProgress || isSyncing,
                            isAnimating: isSyncing
                        ) {
                            onSync?()
                        }
                    }

                    // Disconnect button
                    StatusActionButton(
                        icon: "power",
                        color: .green,
                        help: "Disconnect",
                        disabled: isActionInProgress,
                        action: onDisconnect
                    )

                    // Refresh button
                    StatusActionButton(
                        icon: "arrow.clockwise",
                        color: .magnetarPrimary,
                        help: "Reconnect",
                        disabled: isActionInProgress,
                        action: onReconnect
                    )

                    if isActionInProgress {
                        ProgressView()
                            .scaleEffect(0.6)
                            .frame(width: 12, height: 12)
                    }
                }
            }

            // Sync status row (only show if there are pending/conflicts)
            if pendingChanges > 0 || activeConflicts > 0 {
                HStack(spacing: 8) {
                    if pendingChanges > 0 {
                        HStack(spacing: 4) {
                            Image(systemName: "arrow.up.circle")
                                .font(.system(size: 10))
                            Text("\(pendingChanges) pending")
                                .font(.caption2)
                        }
                        .foregroundStyle(.orange)
                    }

                    if activeConflicts > 0 {
                        HStack(spacing: 4) {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .font(.system(size: 10))
                            Text("\(activeConflicts) conflict\(activeConflicts == 1 ? "" : "s")")
                                .font(.caption2)
                        }
                        .foregroundStyle(.red)
                    }

                    Spacer()
                }
                .padding(.leading, 16)
            }
        }
        .padding(8)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(isHovered ? Color.surfaceTertiary.opacity(0.5) : Color.surfaceTertiary.opacity(0.3))
        )
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
    }

    private var statusIndicator: some View {
        Circle()
            .fill(statusColor)
            .frame(width: 8, height: 8)
    }

    private var statusColor: Color {
        if activeConflicts > 0 {
            return .red
        } else if pendingChanges > 0 {
            return .orange
        } else if isSyncing {
            return .blue
        } else {
            return .green
        }
    }

    private var unauthenticatedView: some View {
        HStack(spacing: 8) {
            Circle()
                .fill(Color.orange)
                .frame(width: 8, height: 8)

            VStack(alignment: .leading, spacing: 2) {
                Text("MagnetarCloud")
                    .font(.caption)
                    .fontWeight(.medium)

                Text("Not Connected")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Button {
                onConnect()
            } label: {
                Text("Sign In")
                    .font(.caption2)
                    .fontWeight(.semibold)
            }
            .buttonStyle(.borderedProminent)
            .controlSize(.mini)
            .disabled(isActionInProgress)

            if isActionInProgress {
                ProgressView()
                    .scaleEffect(0.6)
                    .frame(width: 12, height: 12)
            }
        }
        .padding(8)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(isHovered ? Color.surfaceTertiary.opacity(0.5) : Color.surfaceTertiary.opacity(0.3))
        )
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
    }
}
