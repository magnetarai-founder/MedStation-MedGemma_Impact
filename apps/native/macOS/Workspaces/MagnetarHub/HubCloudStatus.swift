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

    var body: some View {
        if isAuthenticated {
            authenticatedView
        } else {
            unauthenticatedView
        }
    }

    private var authenticatedView: some View {
        HStack(spacing: 8) {
            Circle()
                .fill(Color.green)
                .frame(width: 8, height: 8)

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
        .padding(8)
        .background(Color.surfaceTertiary.opacity(0.3))
        .cornerRadius(6)
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
