//
//  HubDiscoverToolbar.swift
//  MagnetarStudio (macOS)
//
//  Discover toolbar with network status - Extracted from MagnetarHubWorkspace.swift (Phase 6.12)
//

import SwiftUI

struct HubDiscoverToolbar: View {
    let isNetworkConnected: Bool
    let onBrowseModels: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            // Title
            Text("Recommended Models")
                .font(.headline)
                .foregroundColor(.primary)

            Spacer()

            // Network status indicator
            HStack(spacing: 4) {
                Circle()
                    .fill(isNetworkConnected ? Color.green : Color.red)
                    .frame(width: 6, height: 6)
                Text(isNetworkConnected ? "Online" : "Offline")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }

            // Browse Models button - Opens ollama.com
            Button {
                onBrowseModels()
            } label: {
                Label("Browse Models", systemImage: "safari")
                    .font(.caption)
            }
            .buttonStyle(.bordered)
            .disabled(!isNetworkConnected)
            .help(isNetworkConnected ? "Open Ollama library in browser" : "No internet connection")
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 12)
    }
}
