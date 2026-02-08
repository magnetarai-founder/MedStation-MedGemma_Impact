//
//  LibraryModelRow.swift
//  MagnetarStudio (macOS)
//
//  Library model row component - Extracted from ModelDiscoveryWorkspace.swift
//  Enhanced with capability badges, size display, and improved hover effects
//

import SwiftUI

struct LibraryModelRow: View {
    let model: LibraryModel
    let isSelected: Bool
    let isDownloading: Bool
    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 12) {
            // Model icon
            ZStack {
                RoundedRectangle(cornerRadius: 10)
                    .fill(model.isOfficial ? Color.blue.opacity(0.1) : Color.magnetarPrimary.opacity(0.1))
                    .frame(width: 44, height: 44)

                Image(systemName: model.isOfficial ? "checkmark.seal.fill" : "cube.box.fill")
                    .font(.system(size: 20))
                    .foregroundStyle(
                        model.isOfficial
                            ? LinearGradient(colors: [.blue, .cyan], startPoint: .topLeading, endPoint: .bottomTrailing)
                            : LinearGradient.magnetarGradient
                    )
            }

            VStack(alignment: .leading, spacing: 4) {
                // Model name with official badge
                HStack(spacing: 6) {
                    Text(model.modelName)
                        .font(.system(size: 14, weight: isSelected ? .semibold : .medium))
                        .foregroundStyle(isSelected ? .primary : Color.textPrimary)

                    if model.isOfficial {
                        Text("Official")
                            .font(.system(size: 9, weight: .medium))
                            .foregroundStyle(.blue)
                            .padding(.horizontal, 5)
                            .padding(.vertical, 2)
                            .background(Color.blue.opacity(0.1))
                            .clipShape(Capsule())
                    }
                }

                // Stats row
                HStack(spacing: 8) {
                    // Pull count
                    HStack(spacing: 3) {
                        Image(systemName: "arrow.down.circle")
                            .font(.system(size: 10))
                        Text(model.pullsFormatted)
                            .font(.system(size: 11))
                    }
                    .foregroundStyle(.secondary)

                    // Capability labels as badges
                    if !model.labelsText.isEmpty {
                        ForEach(model.labelsText.components(separatedBy: ", ").prefix(2), id: \.self) { label in
                            Text(label)
                                .font(.system(size: 9, weight: .medium))
                                .foregroundStyle(capabilityColor(label))
                                .padding(.horizontal, 5)
                                .padding(.vertical, 2)
                                .background(capabilityColor(label).opacity(0.1))
                                .clipShape(Capsule())
                        }
                    }
                }
            }

            Spacer()

            // Right side: downloading indicator or hover chevron
            if isDownloading {
                ProgressView()
                    .scaleEffect(0.7)
            } else if isHovered {
                Image(systemName: "chevron.right")
                    .font(.system(size: 11))
                    .foregroundStyle(.tertiary)
                    .transition(.opacity)
            }
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(backgroundColor)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 10)
                .strokeBorder(isSelected ? Color.magnetarPrimary.opacity(0.3) : Color.clear, lineWidth: 1)
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

    private func capabilityColor(_ label: String) -> Color {
        switch label.lowercased() {
        case "code": return .green
        case "chat": return .blue
        case "vision": return .purple
        case "embedding": return .orange
        default: return .secondary
        }
    }
}
