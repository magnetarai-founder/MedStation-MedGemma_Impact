//
//  ModelSelectorMenu.swift
//  MagnetarStudio (macOS)
//
//  Enhanced model selector with intelligent routing and hot slots
//  Part of Noah's Ark for the Digital Age - Intelligent model routing
//
//  Foundation: Matthew 7:24-25 - Built on the rock, not sand
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "ModelSelectorMenu")

struct ModelSelectorMenu: View {
    @Binding var selectedMode: String  // "intelligent" or "manual"
    @Binding var selectedModelId: String?
    let availableModels: [String]
    let onRefresh: () async -> Void

    @State private var hotSlotManager = HotSlotManager.shared
    @State private var showPinConfirmation: Bool = false
    @State private var modelToPinToggle: String? = nil

    var body: some View {
        Menu {
            // Intelligent Mode (Apple FM Orchestrator)
            Button {
                selectedMode = "intelligent"
                selectedModelId = nil
            } label: {
                HStack {
                    Image(systemName: "sparkles")
                    Text("Intelligent (Apple FM)")
                    if selectedMode == "intelligent" {
                        Spacer()
                        Image(systemName: "checkmark")
                    }
                }
            }

            Divider()

            // Hot Slot Models Section
            if !hotSlotManager.hotSlots.filter({ !$0.isEmpty }).isEmpty {
                Section("Hot Slots (Preloaded)") {
                    ForEach(hotSlotManager.hotSlots.filter { !$0.isEmpty }) { slot in
                        Button {
                            selectedMode = "manual"
                            selectedModelId = slot.modelId
                        } label: {
                            HStack(spacing: 8) {
                                // Slot badge
                                Text("\(slot.slotNumber)")
                                    .font(.system(size: 10, weight: .bold))
                                    .foregroundColor(.white)
                                    .frame(width: 18, height: 18)
                                    .background(Circle().fill(Color.magnetarPrimary))

                                // Model name
                                Text(slot.modelName ?? slot.modelId ?? "Unknown")

                                // Pin indicator
                                if slot.isPinned {
                                    Image(systemName: "pin.fill")
                                        .font(.system(size: 9))
                                        .foregroundColor(.orange)
                                }

                                // Selection checkmark
                                if selectedMode == "manual" && selectedModelId == slot.modelId {
                                    Spacer()
                                    Image(systemName: "checkmark")
                                }
                            }
                        }
                        .contextMenu {
                            // Right-click pin/unpin
                            Button {
                                togglePinForSlot(slot.slotNumber)
                            } label: {
                                Label(
                                    slot.isPinned ? "Unpin from Slot \(slot.slotNumber)" : "Pin to Slot \(slot.slotNumber)",
                                    systemImage: slot.isPinned ? "pin.slash" : "pin"
                                )
                            }

                            Button(role: .destructive) {
                                Task {
                                    try? await hotSlotManager.removeFromSlot(slotNumber: slot.slotNumber)
                                }
                            } label: {
                                Label("Remove from Slot \(slot.slotNumber)", systemImage: "xmark.circle")
                            }
                        }
                    }
                }

                Divider()
            }

            // All Available Models Section
            Section("All Models") {
                if availableModels.isEmpty {
                    Text("Loading models...")
                        .foregroundColor(.secondary)
                } else {
                    ForEach(availableModels, id: \.self) { model in
                        Button {
                            selectedMode = "manual"
                            selectedModelId = model
                        } label: {
                            HStack {
                                Text(model)

                                // Show if in hot slot
                                if let slot = hotSlotManager.hotSlots.first(where: { $0.modelId == model }) {
                                    Text("Slot \(slot.slotNumber)")
                                        .font(.system(size: 9))
                                        .foregroundColor(.white)
                                        .padding(.horizontal, 6)
                                        .padding(.vertical, 2)
                                        .background(Color.magnetarPrimary)
                                        .cornerRadius(4)
                                }

                                if selectedMode == "manual" && selectedModelId == model {
                                    Spacer()
                                    Image(systemName: "checkmark")
                                }
                            }
                        }
                        .contextMenu {
                            // Right-click to load into hot slot
                            if hotSlotManager.hotSlots.first(where: { $0.modelId == model }) == nil {
                                Button {
                                    Task {
                                        await loadModelIntoHotSlot(model)
                                    }
                                } label: {
                                    Label("Load into Hot Slot", systemImage: "memorychip")
                                }
                            }
                        }
                    }
                }
            }

            Divider()

            // Actions
            Button {
                Task {
                    await onRefresh()
                }
            } label: {
                Label("Refresh Models", systemImage: "arrow.clockwise")
            }

        } label: {
            HStack(spacing: 6) {
                // Icon
                Image(systemName: selectedMode == "intelligent" ? "sparkles" : "cpu")
                    .font(.system(size: 13))

                // Label
                Text(displayText)
                    .font(.system(size: 13))
                    .lineLimit(1)

                // Chevron
                Image(systemName: "chevron.down")
                    .font(.system(size: 10))
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(Color.surfaceSecondary)
            .cornerRadius(6)
        }
        .buttonStyle(.plain)
        .task {
            await hotSlotManager.loadHotSlots()
        }
        .alert("Unpin Model?", isPresented: $showPinConfirmation) {
            Button("Cancel", role: .cancel) {
                modelToPinToggle = nil
            }
            Button("Unpin", role: .destructive) {
                if let model = modelToPinToggle,
                   let slot = hotSlotManager.hotSlots.first(where: { $0.modelId == model }) {
                    hotSlotManager.unpinSlot(slot.slotNumber)
                }
                modelToPinToggle = nil
            }
        } message: {
            Text("Are you sure you want to unpin this model? It may be automatically evicted when loading other models.")
        }
    }

    // MARK: - Helpers

    private var displayText: String {
        if selectedMode == "intelligent" {
            return "Intelligent (Apple FM)"
        } else if let modelId = selectedModelId {
            // Check if it's in a hot slot
            if let slot = hotSlotManager.hotSlots.first(where: { $0.modelId == modelId }) {
                return "\(slot.modelName ?? modelId) [Slot \(slot.slotNumber)]"
            }
            return modelId
        } else {
            return "Select Model"
        }
    }

    private func togglePinForSlot(_ slotNumber: Int) {
        let slot = hotSlotManager.hotSlots.first { $0.slotNumber == slotNumber }

        if slot?.isPinned == true && hotSlotManager.askBeforeUnpinning {
            // Show confirmation
            modelToPinToggle = slot?.modelId
            showPinConfirmation = true
        } else {
            // Toggle directly
            hotSlotManager.togglePin(slotNumber)
        }
    }

    private func loadModelIntoHotSlot(_ modelId: String) async {
        // Check if all slots are full
        if hotSlotManager.areAllSlotsFull {
            // Find eviction candidate
            if let candidateSlot = hotSlotManager.findEvictionCandidate() {
                // Auto-replace least used
                try? await hotSlotManager.assignToSlot(slotNumber: candidateSlot, modelId: modelId)
            } else {
                // All slots pinned - show error
                logger.warning("Cannot load model: All slots are full and pinned")
            }
        } else {
            // Find first empty slot
            if let emptySlot = hotSlotManager.hotSlots.first(where: { $0.isEmpty }) {
                try? await hotSlotManager.assignToSlot(slotNumber: emptySlot.slotNumber, modelId: modelId)
            }
        }
    }
}

// MARK: - Preview

#Preview {
    @Previewable @State var selectedMode = "intelligent"
    @Previewable @State var selectedModelId: String? = nil

    return ModelSelectorMenu(
        selectedMode: $selectedMode,
        selectedModelId: $selectedModelId,
        availableModels: ["llama3.2:3b", "phi-3.5:3.8b", "qwen2.5-coder:3b", "deepseek-r1:8b"],
        onRefresh: { logger.debug("Refresh requested") }
    )
    .padding()
    .frame(width: 400)
}
