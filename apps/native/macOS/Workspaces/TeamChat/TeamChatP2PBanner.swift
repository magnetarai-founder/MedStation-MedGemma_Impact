//
//  TeamChatP2PBanner.swift
//  MagnetarStudio (macOS)
//
//  P2P status banner with controls - Extracted from TeamChatComponents.swift (Phase 6.13)
//

import SwiftUI

struct TeamChatP2PBanner: View {
    let p2pStatus: P2PStatus
    let p2pNetworkStatus: P2PNetworkStatus?
    let onShowPeerDiscovery: () -> Void
    let onShowFileSharing: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            // Left: Status
            HStack(spacing: 8) {
                statusIcon
                    .font(.system(size: 12))

                Text(statusText)
                    .font(.system(size: 14))
                    .foregroundColor(statusColor)
            }

            Spacer()

            // Right: Peer ID + Buttons
            HStack(spacing: 8) {
                if let networkStatus = p2pNetworkStatus, p2pStatus == .connected {
                    Text(String(networkStatus.peerId.prefix(12)) + "...")
                        .font(.system(size: 12, design: .monospaced))
                        .foregroundColor(.blue)
                }

                Button {
                    onShowPeerDiscovery()
                } label: {
                    HStack(spacing: 6) {
                        Image(systemName: "person.2")
                            .font(.system(size: 12))
                        Text("Peers")
                            .font(.system(size: 12, weight: .medium))
                    }
                    .foregroundColor(.white)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(Color.blue)
                    )
                }
                .buttonStyle(.plain)

                Button {
                    onShowFileSharing()
                } label: {
                    HStack(spacing: 6) {
                        Image(systemName: "arrow.up.doc")
                            .font(.system(size: 12))
                        Text("Files")
                            .font(.system(size: 12, weight: .medium))
                    }
                    .foregroundColor(.white)
                    .padding(.horizontal, 10)
                    .padding(.vertical, 5)
                    .background(
                        RoundedRectangle(cornerRadius: 12)
                            .fill(Color.green)
                    )
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 8)
        .background(Color.blue.opacity(0.1))
        .overlay(
            Rectangle()
                .fill(Color.blue.opacity(0.3))
                .frame(height: 1),
            alignment: .bottom
        )
    }

    private var statusIcon: some View {
        Group {
            switch p2pStatus {
            case .connecting:
                ProgressView()
                    .scaleEffect(0.6)
                    .tint(.blue)
            case .disconnected:
                Image(systemName: "wifi.slash")
                    .foregroundColor(.red)
            case .connected:
                Image(systemName: "wifi")
                    .foregroundColor(.green)
            }
        }
    }

    private var statusText: String {
        switch p2pStatus {
        case .connecting: return "Connecting to P2P mesh..."
        case .disconnected: return "Disconnected from mesh"
        case .connected:
            let peerCount = p2pNetworkStatus?.discoveredPeers ?? 0
            return "Connected • \(peerCount) peers"
        }
    }

    private var statusColor: Color {
        switch p2pStatus {
        case .connecting: return .blue
        case .disconnected: return .red
        case .connected: return .green
        }
    }
}
