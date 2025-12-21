//
//  RecordingRow.swift
//  MagnetarStudio
//
//  Recording list item for Insights Lab
//

import SwiftUI

struct RecordingRow: View {
    let recording: InsightsRecording
    let isSelected: Bool

    var body: some View {
        HStack(spacing: 12) {
            // Waveform icon
            Image(systemName: "waveform")
                .font(.title2)
                .foregroundStyle(isSelected ? .white : .indigo)
                .frame(width: 32)

            VStack(alignment: .leading, spacing: 4) {
                Text(recording.title)
                    .font(.headline)
                    .lineLimit(1)
                    .foregroundStyle(isSelected ? .white : .primary)

                HStack(spacing: 8) {
                    Label(recording.formattedDuration, systemImage: "clock")
                        .font(.caption)
                    Text(recording.formattedDate)
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
                                .clipShape(Capsule())
                        }
                    }
                }
            }

            Spacer()

            Image(systemName: "chevron.right")
                .font(.caption)
                .foregroundStyle(isSelected ? .white.opacity(0.6) : Color.secondary.opacity(0.5))
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 10)
        .background(isSelected ? Color.indigo : Color.clear)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .padding(.horizontal, 8)
    }
}
