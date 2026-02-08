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
                .foregroundStyle(.primary)

            Spacer()

            // Network status indicator
            HStack(spacing: 4) {
                Circle()
                    .fill(isNetworkConnected ? Color.green : Color.red)
                    .frame(width: 6, height: 6)
                Text(isNetworkConnected ? "Online" : "Offline")
                    .font(.caption2)
                    .foregroundStyle(.secondary)
            }

            // Browse Models button - Opens ollama.com/library
            Button {
                onBrowseModels()
            } label: {
                Label("Browse Library", systemImage: "safari")
                    .font(.caption)
            }
            .buttonStyle(.borderedProminent)
            .disabled(!isNetworkConnected)
            .help(isNetworkConnected ? "Browse Ollama model library in browser" : "No internet connection")
        }
        .padding(.horizontal, 20)
        .padding(.vertical, 12)
    }
}
