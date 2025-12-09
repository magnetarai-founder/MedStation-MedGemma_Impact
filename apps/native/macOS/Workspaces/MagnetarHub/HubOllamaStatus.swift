//
//  HubOllamaStatus.swift
//  MagnetarStudio (macOS)
//
//  Ollama server status with controls - Extracted from MagnetarHubWorkspace.swift (Phase 6.12)
//

import SwiftUI

struct HubOllamaStatus: View {
    let isRunning: Bool
    let isActionInProgress: Bool
    let onToggle: () -> Void
    let onRestart: () -> Void

    var body: some View {
        HStack(spacing: 8) {
            Circle()
                .fill(isRunning ? Color.green : Color.red)
                .frame(width: 8, height: 8)

            VStack(alignment: .leading, spacing: 2) {
                Text("Ollama Server")
                    .font(.caption)
                    .fontWeight(.medium)

                Text(isRunning ? "Running" : "Stopped")
                    .font(.caption2)
                    .foregroundColor(.secondary)
            }

            Spacer()

            // Control buttons
            HStack(spacing: 6) {
                // Power button
                Button {
                    onToggle()
                } label: {
                    Image(systemName: "power")
                        .font(.system(size: 11))
                        .foregroundColor(isRunning ? .green : .red)
                }
                .buttonStyle(.plain)
                .disabled(isActionInProgress)

                // Restart button
                Button {
                    onRestart()
                } label: {
                    Image(systemName: "arrow.clockwise")
                        .font(.system(size: 11))
                        .foregroundColor(.magnetarPrimary)
                }
                .buttonStyle(.plain)
                .disabled(isActionInProgress || !isRunning)

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
}
