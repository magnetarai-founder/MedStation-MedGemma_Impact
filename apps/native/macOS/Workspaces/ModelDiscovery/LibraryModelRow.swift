//
//  LibraryModelRow.swift
//  MagnetarStudio (macOS)
//
//  Library model row component - Extracted from ModelDiscoveryWorkspace.swift
//

import SwiftUI

struct LibraryModelRow: View {
    let model: LibraryModel
    let isSelected: Bool
    let isDownloading: Bool
    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: model.isOfficial ? "checkmark.seal.fill" : "cube.box.fill")
                .font(.title3)
                .foregroundStyle(
                    model.isOfficial
                        ? LinearGradient(colors: [.blue, .cyan], startPoint: .topLeading, endPoint: .bottomTrailing)
                        : LinearGradient.magnetarGradient
                )

            VStack(alignment: .leading, spacing: 4) {
                HStack(spacing: 6) {
                    Text(model.modelName)
                        .font(.headline)
                        .foregroundColor(.textPrimary)

                    if model.isOfficial {
                        Image(systemName: "checkmark.seal.fill")
                            .font(.caption)
                            .foregroundColor(.blue)
                    }
                }

                HStack(spacing: 6) {
                    Text("\(model.pullsFormatted) pulls")
                        .font(.caption)
                        .foregroundColor(.secondary)

                    if !model.labelsText.isEmpty {
                        Text("•")
                            .font(.caption)
                            .foregroundColor(.secondary)

                        Text(model.labelsText)
                            .font(.caption)
                            .foregroundColor(.secondary)
                    }
                }
            }

            Spacer()

            if isDownloading {
                ProgressView()
                    .scaleEffect(0.7)
            }
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(backgroundColor)
        )
        .contentShape(Rectangle())
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
    }

    private var backgroundColor: Color {
        if isSelected {
            return Color.magnetarPrimary.opacity(0.15)
        } else if isHovered {
            return Color.magnetarPrimary.opacity(0.06)
        } else {
            return Color.clear
        }
    }
}
