//
//  ModelEvictionDialog.swift
//  MagnetarStudio (macOS)
//
//  Dialog for handling hot slot eviction when all slots are full
//  Part of Noah's Ark for the Digital Age - Intelligent model routing
//
//  Foundation: Matthew 7:24-25 - Built on the rock, not sand
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "ModelEvictionDialog")

struct ModelEvictionDialog: View {
    let modelToLoad: String
    let hotSlots: [HotSlot]
    let onAutoReplace: () -> Void
    let onManualSelect: (Int) -> Void
    let onCancel: () -> Void

    @State private var selectedSlot: Int? = nil

    var body: some View {
        VStack(spacing: 20) {
            // Header
            HStack(spacing: 12) {
                Image(systemName: "exclamationmark.triangle.fill")
                    .font(.system(size: 32))
                    .foregroundColor(.orange)

                VStack(alignment: .leading, spacing: 4) {
                    Text("All Hot Slots Are Full")
                        .font(.title3)
                        .fontWeight(.bold)

                    Text("Replace a model to load '\(modelToLoad)'")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }

                Spacer()
            }

            Divider()

            // Auto replace option
            VStack(alignment: .leading, spacing: 12) {
                Text("Automatic Replacement")
                    .font(.headline)

                HStack(spacing: 12) {
                    Image(systemName: "wand.and.stars")
                        .font(.system(size: 20))
                        .foregroundColor(.magnetarPrimary)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Auto Replace Least-Used")
                            .font(.system(size: 13, weight: .medium))

                        Text("Automatically replaces the oldest unpinned model")
                            .font(.system(size: 11))
                            .foregroundColor(.secondary)
                    }

                    Spacer()

                    Button {
                        onAutoReplace()
                    } label: {
                        HStack(spacing: 6) {
                            Image(systemName: "sparkles")
                            Text("Auto Replace")
                        }
                        .font(.system(size: 12, weight: .medium))
                        .padding(.horizontal, 12)
                        .padding(.vertical, 8)
                    }
                    .buttonStyle(.borderedProminent)
                    .tint(.magnetarPrimary)
                }
                .padding(12)
                .background(Color.surfaceSecondary.opacity(0.3))
                .cornerRadius(8)
            }

            // Manual selection
            VStack(alignment: .leading, spacing: 12) {
                Text("Manual Selection")
                    .font(.headline)

                Text("Choose which model to replace:")
                    .font(.system(size: 12))
                    .foregroundColor(.secondary)

                // Slot cards
                VStack(spacing: 8) {
                    ForEach(hotSlots.filter { !$0.isEmpty }) { slot in
                        EvictionSlotCard(
                            slot: slot,
                            isSelected: selectedSlot == slot.slotNumber,
                            onSelect: {
                                selectedSlot = slot.slotNumber
                            }
                        )
                    }
                }
            }

            Divider()

            // Actions
            HStack(spacing: 12) {
                Button("Cancel") {
                    onCancel()
                }
                .keyboardShortcut(.cancelAction)

                Spacer()

                Button {
                    if let slot = selectedSlot {
                        onManualSelect(slot)
                    }
                } label: {
                    HStack(spacing: 6) {
                        Image(systemName: "arrow.triangle.2.circlepath")
                        Text("Replace Selected")
                    }
                    .font(.system(size: 12, weight: .medium))
                }
                .disabled(selectedSlot == nil)
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
            }
        }
        .padding(24)
        .frame(width: 500)
    }
}

// MARK: - Eviction Slot Card

struct EvictionSlotCard: View {
    let slot: HotSlot
    let isSelected: Bool
    let onSelect: () -> Void

    @State private var isHovered: Bool = false

    var body: some View {
        Button {
            onSelect()
        } label: {
            HStack(spacing: 12) {
                // Slot badge
                ZStack {
                    if isSelected {
                        Circle()
                            .fill(LinearGradient.magnetarGradient)
                            .frame(width: 40, height: 40)
                    } else {
                        Circle()
                            .fill(Color.gray.opacity(0.2))
                            .frame(width: 40, height: 40)
                    }

                    Text("\(slot.slotNumber)")
                        .font(.system(size: 16, weight: .bold))
                        .foregroundColor(isSelected ? .white : .secondary)
                }

                // Model info
                VStack(alignment: .leading, spacing: 4) {
                    Text(slot.modelName ?? "Unknown")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundColor(.primary)

                    HStack(spacing: 8) {
                        // Memory
                        if let memoryGB = slot.memoryUsageGB {
                            Label("\(String(format: "%.1f", memoryGB)) GB", systemImage: "memorychip")
                                .font(.system(size: 10))
                                .foregroundColor(.secondary)
                        }

                        // Loaded time
                        if let loadedAt = slot.loadedAt {
                            Label("Loaded \(loadedAt.formatted(.relative(presentation: .named)))", systemImage: "clock")
                                .font(.system(size: 10))
                                .foregroundColor(.secondary)
                        }
                    }
                }

                Spacer()

                // Pinned badge
                if slot.isPinned {
                    HStack(spacing: 4) {
                        Image(systemName: "pin.fill")
                            .font(.system(size: 10))
                        Text("PINNED")
                            .font(.system(size: 9, weight: .bold))
                    }
                    .foregroundColor(.orange)
                    .padding(.horizontal, 8)
                    .padding(.vertical, 4)
                    .background(Color.orange.opacity(0.2))
                    .cornerRadius(4)
                }

                // Selection indicator
                if isSelected {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.system(size: 20))
                        .foregroundColor(.magnetarPrimary)
                }
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isSelected ? Color.magnetarPrimary.opacity(0.1) : Color.surfaceSecondary.opacity(0.2))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(
                                isSelected ? Color.magnetarPrimary :
                                slot.isPinned ? Color.orange.opacity(0.5) :
                                Color.clear,
                                lineWidth: 2
                            )
                    )
            )
        }
        .buttonStyle(.plain)
        .disabled(slot.isPinned)  // Can't select pinned slots
        .opacity(slot.isPinned ? 0.5 : 1.0)
        .onHover { hovering in
            isHovered = hovering && !slot.isPinned
        }
        .scaleEffect(isHovered ? 1.02 : 1.0)
        .animation(.easeInOut(duration: 0.15), value: isHovered)
    }
}

// MARK: - Preview

#Preview {
    let mockSlots = [
        HotSlot(slotNumber: 1, modelId: "llama3.2:3b", modelName: "Llama 3.2 3B", isPinned: false, loadedAt: Date().addingTimeInterval(-3600), memoryUsageGB: 3.2),
        HotSlot(slotNumber: 2, modelId: "phi-3.5:3.8b", modelName: "Phi-3.5 3.8B", isPinned: true, loadedAt: Date().addingTimeInterval(-1800), memoryUsageGB: 4.1),
        HotSlot(slotNumber: 3, modelId: "qwen2.5-coder:3b", modelName: "Qwen2.5-Coder 3B", isPinned: false, loadedAt: Date().addingTimeInterval(-7200), memoryUsageGB: 3.5),
        HotSlot(slotNumber: 4, modelId: "deepseek-r1:8b", modelName: "DeepSeek-R1 8B", isPinned: false, loadedAt: Date().addingTimeInterval(-300), memoryUsageGB: 8.2)
    ]

    return ModelEvictionDialog(
        modelToLoad: "llama3.3:70b",
        hotSlots: mockSlots,
        onAutoReplace: { logger.debug("Auto replace") },
        onManualSelect: { slot in logger.debug("Replace slot \(slot)") },
        onCancel: { logger.debug("Cancel") }
    )
    .frame(width: 500, height: 600)
}
