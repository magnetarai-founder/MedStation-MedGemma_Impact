//
//  HotSlotCard.swift
//  MagnetarStudio (macOS)
//
//  Hot slot card component - Extracted from HotSlotSettingsView.swift (Phase 6.24)
//

import SwiftUI

struct HotSlotCard: View {
    let slot: HotSlot
    let onPin: () -> Void
    let onRemove: () -> Void
    let onAssign: () -> Void

    @State private var isHovered: Bool = false

    var body: some View {
        HStack(spacing: 16) {
            // Slot number badge
            ZStack {
                if slot.isEmpty {
                    Circle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(width: 48, height: 48)
                } else {
                    Circle()
                        .fill(LinearGradient.magnetarGradient)
                        .frame(width: 48, height: 48)
                }

                Text("\(slot.slotNumber)")
                    .font(.system(size: 20, weight: .bold))
                    .foregroundColor(slot.isEmpty ? .secondary : .white)
            }

            // Model info
            VStack(alignment: .leading, spacing: 6) {
                if let modelName = slot.modelName {
                    Text(modelName)
                        .font(.system(size: 14, weight: .semibold))

                    HStack(spacing: 8) {
                        // Memory usage
                        if let memoryGB = slot.memoryUsageGB {
                            Label("\(String(format: "%.1f", memoryGB)) GB", systemImage: "memorychip")
                                .font(.system(size: 11))
                                .foregroundColor(.secondary)
                        }

                        // Loaded time
                        if let loadedAt = slot.loadedAt {
                            Label(loadedAt.formatted(.relative(presentation: .named)), systemImage: "clock")
                                .font(.system(size: 11))
                                .foregroundColor(.secondary)
                        }
                    }
                } else {
                    Text("Empty Slot")
                        .font(.system(size: 14))
                        .foregroundColor(.secondary)

                    Text("Click 'Assign Model' to load a model")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                }
            }

            Spacer()

            // Actions
            HStack(spacing: 8) {
                // Pin button
                if !slot.isEmpty {
                    Button {
                        onPin()
                    } label: {
                        Image(systemName: slot.isPinned ? "pin.fill" : "pin")
                            .font(.system(size: 14))
                            .foregroundColor(slot.isPinned ? .orange : .secondary)
                    }
                    .buttonStyle(.plain)
                    .help(slot.isPinned ? "Unpin (allow eviction)" : "Pin (prevent eviction)")
                }

                // Remove button
                if !slot.isEmpty {
                    Button {
                        onRemove()
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 14))
                            .foregroundColor(.red)
                    }
                    .buttonStyle(.plain)
                    .help("Remove from slot")
                }

                // Assign button
                Button {
                    onAssign()
                } label: {
                    HStack(spacing: 4) {
                        Image(systemName: slot.isEmpty ? "plus.circle.fill" : "arrow.triangle.2.circlepath")
                            .font(.system(size: 12))
                        Text(slot.isEmpty ? "Assign Model" : "Replace")
                            .font(.system(size: 11, weight: .medium))
                    }
                    .foregroundColor(.magnetarPrimary)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 12)
                .fill(slot.isEmpty ? Color.surfaceSecondary.opacity(0.2) : Color.surfaceSecondary.opacity(0.4))
                .overlay(
                    RoundedRectangle(cornerRadius: 12)
                        .stroke(slot.isPinned ? Color.orange : Color.clear, lineWidth: 2)
                )
        )
        .onHover { hovering in
            isHovered = hovering
        }
        .scaleEffect(isHovered ? 1.02 : 1.0)
        .animation(.easeInOut(duration: 0.2), value: isHovered)
    }
}
