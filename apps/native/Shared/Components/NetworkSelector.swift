//
//  NetworkSelector.swift
//  MagnetarStudio
//
//  Network mode selector for Team workspace
//  - Toggle between Local/P2P/Cloud modes
//  - Globe icon with mode dropdown
//

import SwiftUI

struct NetworkSelector: View {
    @Binding var mode: NetworkMode

    var body: some View {
        Menu {
            Button {
                mode = .local
            } label: {
                Label("Local Network", systemImage: "wifi")
            }

            Button {
                mode = .p2p
            } label: {
                Label("P2P Mesh", systemImage: "network")
            }

            Button {
                mode = .cloud
            } label: {
                Label("Cloud Relay", systemImage: "cloud")
            }
        } label: {
            HStack(spacing: 8) {
                Image(systemName: "globe")
                    .font(.system(size: 16))

                Text(mode.displayName)
                    .font(.system(size: 14))

                Image(systemName: "chevron.down")
                    .font(.system(size: 10))
            }
            .foregroundColor(.secondary)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.gray.opacity(0.1))
            )
        }
        .buttonStyle(.plain)
        .help("Network Mode")
    }
}

enum NetworkMode: String, CaseIterable {
    case local
    case p2p
    case cloud

    var displayName: String {
        switch self {
        case .local: return "Local Network"
        case .p2p: return "P2P Mesh"
        case .cloud: return "Cloud Relay"
        }
    }
}

// MARK: - Preview

#Preview {
    NetworkSelector(mode: .constant(.local))
        .padding()
}
