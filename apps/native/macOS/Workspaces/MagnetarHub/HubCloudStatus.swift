//
//  HubCloudStatus.swift
//  MagnetarStudio (macOS)
//
//  MagnetarCloud connection status with controls - Extracted from MagnetarHubWorkspace.swift (Phase 6.12)
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
                        .foregroundColor(.secondary)
                }

                Spacer()

                // Control buttons
                HStack(spacing: 6) {
                    // Sync button
                    if let onSync = onSync {
                        Button {
                            onSync()
                        } label: {
                            Image(systemName: isSyncing ? "arrow.triangle.2.circlepath" : "arrow.triangle.2.circlepath")
                                .font(.system(size: 11))
                                .foregroundColor(.magnetarPrimary)
                                .rotationEffect(.degrees(isSyncing ? 360 : 0))
                                .animation(isSyncing ? .linear(duration: 1).repeatForever(autoreverses: false) : .default, value: isSyncing)
                        }
                        .buttonStyle(.plain)
                        .disabled(isActionInProgress || isSyncing)
                    }

                    // Disconnect button
                    Button {
                        onDisconnect()
                    } label: {
                        Image(systemName: "power")
                            .font(.system(size: 11))
                            .foregroundColor(.green)
                    }
                    .buttonStyle(.plain)
                    .disabled(isActionInProgress)

                    // Refresh button
                    Button {
                        onReconnect()
                    } label: {
                        Image(systemName: "arrow.clockwise")
                            .font(.system(size: 11))
                            .foregroundColor(.magnetarPrimary)
                    }
                    .buttonStyle(.plain)
                    .disabled(isActionInProgress)

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
                        .foregroundColor(.orange)
                    }

                    if activeConflicts > 0 {
                        HStack(spacing: 4) {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .font(.system(size: 10))
                            Text("\(activeConflicts) conflict\(activeConflicts == 1 ? "" : "s")")
                                .font(.caption2)
                        }
                        .foregroundColor(.red)
                    }

                    Spacer()
                }
                .padding(.leading, 16)
            }
        }
        .padding(8)
        .background(Color.surfaceTertiary.opacity(0.3))
        .cornerRadius(6)
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
                    .foregroundColor(.secondary)
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
        .background(Color.surfaceTertiary.opacity(0.3))
        .cornerRadius(6)
    }
}
