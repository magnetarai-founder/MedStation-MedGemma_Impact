//
//  CodeTerminalPanel.swift
//  MagnetarStudio (macOS)
//
//  Terminal panel with info - Extracted from CodeWorkspace.swift (Phase 6.18)
//

import SwiftUI

struct CodeTerminalPanel: View {
    @Binding var showTerminal: Bool
    let errorMessage: String?
    let onSpawnTerminal: () async -> Void

    var body: some View {
        VStack(spacing: 0) {
            // Terminal header
            HStack {
                Image(systemName: "terminal")
                    .font(.system(size: 12))
                    .foregroundColor(.magnetarPrimary)

                Text("Terminal")
                    .font(.system(size: 12, weight: .semibold))

                Spacer()

                // New terminal button
                Button {
                    Task {
                        await onSpawnTerminal()
                    }
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: "plus.circle.fill")
                            .font(.system(size: 12))
                        Text("New")
                            .font(.system(size: 11, weight: .medium))
                    }
                    .foregroundColor(.magnetarPrimary)
                }
                .buttonStyle(.plain)

                Button {
                    showTerminal = false
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 10))
                }
                .buttonStyle(.plain)
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(Color.surfaceTertiary.opacity(0.3))

            Divider()

            // Terminal info
            ScrollView {
                VStack(alignment: .leading, spacing: 12) {
                    HStack(spacing: 8) {
                        Image(systemName: "terminal.fill")
                            .font(.system(size: 24))
                            .foregroundStyle(LinearGradient.magnetarGradient)

                        VStack(alignment: .leading, spacing: 4) {
                            Text("System Terminal Integration")
                                .font(.system(size: 13, weight: .semibold))

                            Text("Click 'New' to spawn a terminal window")
                                .font(.system(size: 11))
                                .foregroundColor(.secondary)
                        }
                    }
                    .padding(.bottom, 8)

                    VStack(alignment: .leading, spacing: 8) {
                        CodeTerminalInfoRow(
                            icon: "checkmark.circle.fill",
                            text: "Opens your default terminal app (Warp, iTerm2, or Terminal)",
                            color: .green
                        )

                        CodeTerminalInfoRow(
                            icon: "checkmark.circle.fill",
                            text: "Automatically starts in your workspace directory",
                            color: .green
                        )

                        CodeTerminalInfoRow(
                            icon: "checkmark.circle.fill",
                            text: "Up to 3 terminals can be active simultaneously",
                            color: .green
                        )
                    }

                    if let error = errorMessage {
                        HStack(spacing: 8) {
                            Image(systemName: "exclamationmark.triangle.fill")
                                .foregroundColor(.orange)
                            Text(error)
                                .font(.system(size: 11))
                                .foregroundColor(.secondary)
                        }
                        .padding(.top, 8)
                    }
                }
                .padding(16)
                .frame(maxWidth: .infinity, alignment: .leading)
            }
            .background(Color.surfaceTertiary.opacity(0.1))
        }
    }
}

// MARK: - Terminal Info Row

struct CodeTerminalInfoRow: View {
    let icon: String
    let text: String
    let color: Color

    var body: some View {
        HStack(alignment: .top, spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 11))
                .foregroundColor(color)
                .frame(width: 16)

            Text(text)
                .font(.system(size: 11))
                .foregroundColor(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
    }
}
