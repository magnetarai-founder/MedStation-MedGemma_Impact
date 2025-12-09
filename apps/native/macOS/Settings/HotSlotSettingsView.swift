//
//  HotSlotSettingsView.swift
//  MagnetarStudio (macOS)
//
//  Hot slot management settings UI
//  Part of Noah's Ark for the Digital Age - Intelligent model routing
//
//  Foundation: Matthew 7:24-25 - Built on the rock, not sand
//  Refactored in Phase 6.24 - extracted card and picker components
//

import SwiftUI

struct HotSlotSettingsView: View {
    @StateObject private var hotSlotManager = HotSlotManager.shared
    @State private var modelsStore = ModelsStore()
    @State private var showModelPicker: Bool = false
    @State private var selectedSlotForAssignment: Int? = nil

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
                                showModelPicker = true
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
            await modelsStore.fetchModels()
        }
        .sheet(isPresented: $showModelPicker) {
            if let slotNumber = selectedSlotForAssignment {
                ModelPickerSheet(
                    slotNumber: slotNumber,
                    availableModels: modelsStore.models,
                    onSelect: { modelName in
                        Task {
                            try? await hotSlotManager.assignToSlot(slotNumber: slotNumber, modelName: modelName)
                            showModelPicker = false
                            selectedSlotForAssignment = nil
                        }
                    },
                    onCancel: {
                        showModelPicker = false
                        selectedSlotForAssignment = nil
                    }
                )
            }
        }
    }
}

// Components extracted to:
// - HotSlots/HotSlotCard.swift (Phase 6.24)
// - HotSlots/HotSlotModelPicker.swift (Phase 6.24)

// MARK: - Preview

#Preview {
    HotSlotSettingsView()
        .frame(width: 700, height: 800)
}
