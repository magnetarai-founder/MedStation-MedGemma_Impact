//
//  HotSlotSettingsView.swift
//  MagnetarStudio (macOS)
//
//  Hot slot management settings UI
//  Part of Noah's Ark for the Digital Age - Intelligent model routing
//
//  Foundation: Matthew 7:24-25 - Built on the rock, not sand
//

import SwiftUI

struct HotSlotSettingsView: View {
    @StateObject private var hotSlotManager = HotSlotManager.shared
    @State private var availableModels: [AssignableModel] = []
    @State private var isLoadingModels: Bool = false
    @State private var showEvictionDialog: Bool = false
    @State private var selectedSlotForAssignment: Int? = nil
    @State private var selectedModelForAssignment: String? = nil

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 24) {
                // Header
                VStack(alignment: .leading, spacing: 8) {
                    HStack(spacing: 12) {
                        Image(systemName: "memorychip.fill")
                            .font(.system(size: 32))
                            .foregroundStyle(LinearGradient.magnetarGradient)

                        VStack(alignment: .leading, spacing: 4) {
                            Text("Hot Slots")
                                .font(.title2)
                                .fontWeight(.bold)

                            Text("Preload models for instant inference")
                                .font(.subheadline)
                                .foregroundColor(.secondary)
                        }

                        Spacer()

                        // Load all button
                        Button {
                            Task {
                                try? await hotSlotManager.loadAllHotSlots()
                            }
                        } label: {
                            HStack(spacing: 6) {
                                Image(systemName: "arrow.clockwise")
                                Text("Load All")
                            }
                            .font(.system(size: 12, weight: .medium))
                        }
                        .buttonStyle(.bordered)
                    }

                    Divider()
                        .padding(.top, 8)
                }

                // Hot Slots (4 cards)
                VStack(spacing: 16) {
                    ForEach(hotSlotManager.hotSlots) { slot in
                        HotSlotCard(
                            slot: slot,
                            onPin: {
                                hotSlotManager.togglePin(slot.slotNumber)
                            },
                            onRemove: {
                                Task {
                                    try? await hotSlotManager.removeFromSlot(slotNumber: slot.slotNumber)
                                }
                            },
                            onAssign: {
                                selectedSlotForAssignment = slot.slotNumber
                                // TODO: Show model picker
                            }
                        )
                    }
                }

                // Global Settings
                VStack(alignment: .leading, spacing: 16) {
                    Text("Global Settings")
                        .font(.headline)
                        .padding(.top, 8)

                    VStack(spacing: 12) {
                        Toggle(isOn: $hotSlotManager.immutableModels) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Immutable Models")
                                    .font(.system(size: 13, weight: .medium))
                                Text("Require confirmation before unpinning models")
                                    .font(.system(size: 11))
                                    .foregroundColor(.secondary)
                            }
                        }
                        .onChange(of: hotSlotManager.immutableModels) { oldValue, newValue in
                            hotSlotManager.updateImmutableModels(newValue)
                        }

                        Divider()

                        Toggle(isOn: $hotSlotManager.askBeforeUnpinning) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text("Ask Before Unpinning")
                                    .font(.system(size: 13, weight: .medium))
                                Text("Show confirmation dialog when unpinning slots")
                                    .font(.system(size: 11))
                                    .foregroundColor(.secondary)
                            }
                        }
                        .onChange(of: hotSlotManager.askBeforeUnpinning) { oldValue, newValue in
                            hotSlotManager.updateAskBeforeUnpinning(newValue)
                        }
                    }
                    .padding(16)
                    .background(Color.surfaceSecondary.opacity(0.3))
                    .cornerRadius(12)
                }

                // Info box
                HStack(spacing: 12) {
                    Image(systemName: "info.circle.fill")
                        .font(.system(size: 20))
                        .foregroundColor(.blue)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Hot slots keep models loaded in memory for instant inference.")
                            .font(.system(size: 12))

                        Text("Pin important models to prevent automatic eviction when loading new models.")
                            .font(.system(size: 11))
                            .foregroundColor(.secondary)
                    }
                }
                .padding(12)
                .background(Color.blue.opacity(0.1))
                .cornerRadius(8)
            }
            .padding(24)
        }
        .task {
            await hotSlotManager.loadHotSlots()
        }
    }
}

// MARK: - Hot Slot Card

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
                Circle()
                    .fill(slot.isEmpty ? Color.gray.opacity(0.2) : LinearGradient.magnetarGradient)
                    .frame(width: 48, height: 48)

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

// MARK: - Preview

#Preview {
    HotSlotSettingsView()
        .frame(width: 700, height: 800)
}
