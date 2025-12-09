//
//  TeamWorkspaceToolbar.swift
//  MagnetarStudio (macOS)
//
//  Horizontal toolbar for TeamWorkspace - Extracted from TeamWorkspace_v2.swift (Phase 6.23)
//

import SwiftUI

struct TeamWorkspaceToolbar: View {
    @Binding var selectedView: TeamView
    let onShowNetworkStatus: () -> Void
    let onShowDiagnostics: () -> Void
    let onShowDataLab: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            // Network status indicator
            Button(action: onShowNetworkStatus) {
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
            Button(action: onShowDiagnostics) {
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

            Button(action: onShowDataLab) {
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
    }
}
