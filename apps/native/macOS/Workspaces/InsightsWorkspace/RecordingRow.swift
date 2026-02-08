//
//  RecordingRow.swift
//  MagnetarStudio
//
//  Recording list item for Insights Lab
//  Enhanced with hover actions and relative timestamps
//

import SwiftUI
import AppKit

struct RecordingRow: View {
    let recording: InsightsRecording
    let isSelected: Bool
    var onPlay: (() -> Void)? = nil
    var onShare: (() -> Void)? = nil
    var onDelete: (() -> Void)? = nil

    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 12) {
            // Waveform icon with duration indicator
            ZStack {
                // Background circle
                Circle()
                    .fill(isSelected ? .white.opacity(0.2) : .indigo.opacity(0.1))
                    .frame(width: 40, height: 40)

                // Waveform icon
                Image(systemName: "waveform")
                    .font(.system(size: 18))
                    .foregroundStyle(isSelected ? .white : .indigo)
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(recording.title)
                    .font(.headline)
                    .lineLimit(1)
                    .foregroundStyle(isSelected ? .white : .primary)

                HStack(spacing: 8) {
                    // Duration with icon
                    Label(recording.formattedDuration, systemImage: "clock")
                        .font(.caption)

                    // Word count
                    Label(recording.formattedWordCount, systemImage: "text.word.spacing")
                        .font(.caption)

                    // Relative timestamp
                    Text("•")
                        .font(.caption)
                    Text(recording.relativeDate)
                        .font(.caption)
                }
                .foregroundStyle(isSelected ? .white.opacity(0.8) : .secondary)

                if !recording.tags.isEmpty {
                    HStack(spacing: 4) {
                        ForEach(recording.tags.prefix(3), id: \.self) { tag in
                            Text(tag)
                                .font(.caption2)
                                .padding(.horizontal, 6)
                                .padding(.vertical, 2)
                                .background(isSelected ? .white.opacity(0.2) : .indigo.opacity(0.1))
                                .foregroundStyle(isSelected ? .white : .indigo)
                                .clipShape(Capsule())
                        }
                        if recording.tags.count > 3 {
                            Text("+\(recording.tags.count - 3)")
                                .font(.caption2)
                                .foregroundStyle(isSelected ? .white.opacity(0.7) : .secondary)
                        }
                    }
                }
            }

            Spacer()

            // Hover actions
            if isHovered && !isSelected {
                HStack(spacing: 4) {
                    // Play button
                    if let onPlay = onPlay {
                        HoverActionButton(
                            icon: "play.fill",
                            color: .green,
                            action: onPlay,
                            help: "Play Recording"
                        )
                    }

                    // Share button
                    if let onShare = onShare {
                        HoverActionButton(
                            icon: "square.and.arrow.up",
                            color: .blue,
                            action: onShare,
                            help: "Share"
                        )
                    }

                    // Delete button
                    if let onDelete = onDelete {
                        HoverActionButton(
                            icon: "trash",
                            color: .red,
                            action: onDelete,
                            help: "Delete"
                        )
                    }
                }
                .transition(.opacity.combined(with: .scale(scale: 0.9)))
            } else {
                Image(systemName: "chevron.right")
                    .font(.caption)
                    .foregroundStyle(isSelected ? .white.opacity(0.6) : Color.secondary.opacity(0.5))
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(isSelected ? Color.indigo : (isHovered ? Color.indigo.opacity(0.05) : Color.clear))
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .padding(.horizontal, 8)
        .contentShape(Rectangle())
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
    }
}

// MARK: - Hover Action Button

private struct HoverActionButton: View {
    let icon: String
    let color: Color
    let action: () -> Void
    let help: String

    @State private var isPressed = false

    var body: some View {
        Button(action: action) {
            Image(systemName: icon)
                .font(.system(size: 12))
                .foregroundStyle(color)
                .frame(width: 26, height: 26)
                .background(
                    Circle()
                        .fill(color.opacity(isPressed ? 0.2 : 0.1))
                )
        }
        .buttonStyle(.plain)
        .help(help)
        .onHover { hovering in
            isPressed = hovering
        }
    }
}
