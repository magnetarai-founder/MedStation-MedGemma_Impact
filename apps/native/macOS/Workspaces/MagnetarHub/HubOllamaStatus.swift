//
//  HubOllamaStatus.swift
//  MagnetarStudio (macOS)
//
//  Ollama server status with controls - Extracted from MagnetarHubWorkspace.swift (Phase 6.12)
//  Enhanced with hover effects and status animations
//

import SwiftUI

struct HubOllamaStatus: View {
    let isRunning: Bool
    let isActionInProgress: Bool
    let onToggle: () -> Void
    let onRestart: () -> Void

    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 8) {
            // Status indicator with pulse animation when running
            Circle()
                .fill(isRunning ? Color.green : Color.red)
                .frame(width: 8, height: 8)
                .overlay(
                    Circle()
                        .stroke(isRunning ? Color.green.opacity(0.5) : Color.clear, lineWidth: 2)
                        .scaleEffect(isRunning ? 1.5 : 1.0)
                        .opacity(isRunning ? 0 : 1)
                        .animation(isRunning ? .easeOut(duration: 1.5).repeatForever(autoreverses: false) : .default, value: isRunning)
                )

            VStack(alignment: .leading, spacing: 2) {
                Text("Ollama Server")
                    .font(.caption)
                    .fontWeight(.medium)

                Text(isRunning ? "Running" : "Stopped")
                    .font(.caption2)
                    .foregroundStyle(isRunning ? .green : .secondary)
            }

            Spacer()

            // Control buttons with hover effects
            HStack(spacing: 4) {
                // Power button
                StatusActionButton(
                    icon: "power",
                    color: isRunning ? .green : .red,
                    help: isRunning ? "Stop Ollama" : "Start Ollama",
                    disabled: isActionInProgress,
                    action: onToggle
                )

                // Restart button
                StatusActionButton(
                    icon: "arrow.clockwise",
                    color: .magnetarPrimary,
                    help: "Restart Ollama",
                    disabled: isActionInProgress || !isRunning,
                    action: onRestart
                )

                if isActionInProgress {
                    ProgressView()
                        .scaleEffect(0.6)
                        .frame(width: 12, height: 12)
                }
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

// MARK: - Status Action Button (reusable)

struct StatusActionButton: View {
    let icon: String
    let color: Color
    let help: String
    var disabled: Bool = false
    var isAnimating: Bool = false
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 11))
                .foregroundStyle(disabled ? .gray : (isHovered ? color : color.opacity(0.7)))
                .frame(width: 22, height: 22)
                .background(
                    RoundedRectangle(cornerRadius: 4)
                        .fill(isHovered && !disabled ? color.opacity(0.15) : Color.clear)
                )
                .rotationEffect(.degrees(isAnimating ? 360 : 0))
                .animation(isAnimating ? .linear(duration: 1).repeatForever(autoreverses: false) : .default, value: isAnimating)
        }
        .buttonStyle(.plain)
        .disabled(disabled)
        .help(help)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.1)) {
                isHovered = hovering
            }
        }
    }
}
