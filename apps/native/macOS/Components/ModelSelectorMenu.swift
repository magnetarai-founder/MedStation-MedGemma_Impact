//
//  ModelSelectorMenu.swift
//  MedStation
//
//  Model selector with hot slots and intelligent routing.
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "ModelSelectorMenu")

struct ModelSelectorMenu: View {
    @Binding var selectedMode: String
    @Binding var selectedModelId: String?
    let availableModels: [String]
    let onRefresh: () async -> Void

    var hasOverride: Bool = false
    var onClearOverride: (() -> Void)? = nil

    @State private var hotSlotManager = HotSlotManager.shared
    @State private var showPinConfirmation: Bool = false
    @State private var modelToPinToggle: String? = nil
    @State private var showEvictionDialog: Bool = false
    @State private var evictionModelId: String = ""

    var body: some View {
        Menu {
            menuContent
        } label: {
            menuLabel
        }
        .buttonStyle(.plain)
        .task {
            await hotSlotManager.loadHotSlots()
        }
        .alert("Unpin Model?", isPresented: $showPinConfirmation) {
            unpinAlertButtons
        } message: {
            Text("Are you sure you want to unpin this model? It may be automatically evicted when loading other models.")
        }
        .sheet(isPresented: $showEvictionDialog) {
            evictionSheet
        }
    }

    // MARK: - Menu Content

    @ViewBuilder
    private var menuContent: some View {
        if hasOverride, let clearAction = onClearOverride {
            Button {
                clearAction()
            } label: {
                Label("Use Default", systemImage: "arrow.uturn.backward")
            }

            Divider()
        }

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

        hotSlotsSection

        allModelsSection

        Divider()

        Button {
            Task { await onRefresh() }
        } label: {
            Label("Refresh Models", systemImage: "arrow.clockwise")
        }
    }

    // MARK: - Hot Slots Section

    @ViewBuilder
    private var hotSlotsSection: some View {
        let loadedSlots = hotSlotManager.hotSlots.filter { !$0.isEmpty }
        if !loadedSlots.isEmpty {
            Section("Hot Slots (Preloaded)") {
                ForEach(loadedSlots) { slot in
                    hotSlotButton(for: slot)
                }
            }

            Divider()
        }
    }

    @ViewBuilder
    private func hotSlotButton(for slot: HotSlot) -> some View {
        Button {
            selectedMode = "manual"
            selectedModelId = slot.modelId
        } label: {
            HStack(spacing: 8) {
                Text("\(slot.slotNumber)")
                    .font(.system(size: 10, weight: .bold))
                    .foregroundStyle(.white)
                    .frame(width: 18, height: 18)
                    .background(Circle().fill(Color.magnetarPrimary))

                Text(slot.modelName ?? slot.modelId ?? "Unknown")

                if slot.isPinned {
                    Image(systemName: "pin.fill")
                        .font(.system(size: 9))
                        .foregroundStyle(.orange)
                }

                if selectedMode == "manual" && selectedModelId == slot.modelId {
                    Spacer()
                    Image(systemName: "checkmark")
                }
            }
        }
        .contextMenu {
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
                    do {
                        try await hotSlotManager.removeFromSlot(slotNumber: slot.slotNumber)
                    } catch {
                        logger.error("Failed to remove from slot \(slot.slotNumber): \(error)")
                    }
                }
            } label: {
                Label("Remove from Slot \(slot.slotNumber)", systemImage: "xmark.circle")
            }
        }
    }

    // MARK: - All Models Section

    @ViewBuilder
    private var allModelsSection: some View {
        Section("All Models") {
            if availableModels.isEmpty {
                Text("Loading models...")
                    .foregroundStyle(.secondary)
            } else {
                ForEach(availableModels, id: \.self) { model in
                    modelButton(for: model)
                }
            }
        }
    }

    @ViewBuilder
    private func modelButton(for model: String) -> some View {
        Button {
            selectedMode = "manual"
            selectedModelId = model
        } label: {
            HStack {
                Text(model)

                if let slot = hotSlotManager.hotSlots.first(where: { $0.modelId == model }) {
                    Text("Slot \(slot.slotNumber)")
                        .font(.system(size: 9))
                        .foregroundStyle(.white)
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
            if hotSlotManager.hotSlots.first(where: { $0.modelId == model }) == nil {
                Button {
                    Task { await loadModelIntoHotSlot(model) }
                } label: {
                    Label("Load into Hot Slot", systemImage: "memorychip")
                }
            }
        }
    }

    // MARK: - Menu Label

    private var menuLabel: some View {
        HStack(spacing: 6) {
            Image(systemName: selectedMode == "intelligent" ? "sparkles" : "cpu")
                .font(.system(size: 13))

            Text(displayText)
                .font(.system(size: 13))
                .lineLimit(1)

            Image(systemName: "chevron.down")
                .font(.system(size: 10))
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(Color.surfaceSecondary)
        .cornerRadius(6)
    }

    // MARK: - Alert & Sheet

    @ViewBuilder
    private var unpinAlertButtons: some View {
        Button("Cancel", role: .cancel) {
            modelToPinToggle = nil
        }
        Button("Unpin", role: .destructive) {
            if let model = modelToPinToggle,
               let slot = hotSlotManager.hotSlots.first(where: { $0.modelId == model }) {
                Task { await hotSlotManager.unpinSlot(slot.slotNumber) }
            }
            modelToPinToggle = nil
        }
    }

    private var evictionSheet: some View {
        ModelEvictionDialog(
            modelToLoad: evictionModelId,
            hotSlots: hotSlotManager.hotSlots,
            onAutoReplace: {
                showEvictionDialog = false
                Task {
                    if let candidate = hotSlotManager.findEvictionCandidate() {
                        try? await hotSlotManager.assignToSlot(slotNumber: candidate, modelId: evictionModelId)
                    }
                }
            },
            onManualSelect: { slotNumber in
                showEvictionDialog = false
                Task {
                    try? await hotSlotManager.assignToSlot(slotNumber: slotNumber, modelId: evictionModelId)
                }
            },
            onCancel: {
                showEvictionDialog = false
            }
        )
    }

    // MARK: - Helpers

    private var displayText: String {
        let prefix = hasOverride ? "● " : ""
        if selectedMode == "intelligent" {
            return "\(prefix)Intelligent (Apple FM)"
        } else if let modelId = selectedModelId {
            if let slot = hotSlotManager.hotSlots.first(where: { $0.modelId == modelId }) {
                return "\(prefix)\(slot.modelName ?? modelId) [Slot \(slot.slotNumber)]"
            }
            return "\(prefix)\(modelId)"
        } else {
            return "Select Model"
        }
    }

    private func togglePinForSlot(_ slotNumber: Int) {
        let slot = hotSlotManager.hotSlots.first { $0.slotNumber == slotNumber }

        if slot?.isPinned == true && hotSlotManager.askBeforeUnpinning {
            modelToPinToggle = slot?.modelId
            showPinConfirmation = true
        } else {
            Task { await hotSlotManager.togglePin(slotNumber) }
        }
    }

    private func loadModelIntoHotSlot(_ modelId: String) async {
        if hotSlotManager.areAllSlotsFull {
            evictionModelId = modelId
            showEvictionDialog = true
        } else {
            if let emptySlot = hotSlotManager.hotSlots.first(where: { $0.isEmpty }) {
                do {
                    try await hotSlotManager.assignToSlot(slotNumber: emptySlot.slotNumber, modelId: modelId)
                } catch {
                    logger.error("Failed to assign model to slot \(emptySlot.slotNumber): \(error)")
                }
            }
        }
    }
}

#Preview {
    @Previewable @State var selectedMode = "intelligent"
    @Previewable @State var selectedModelId: String? = nil

    ModelSelectorMenu(
        selectedMode: $selectedMode,
        selectedModelId: $selectedModelId,
        availableModels: ["llama3.2:3b", "phi-3.5:3.8b", "medgemma:4b"],
        onRefresh: { }
    )
    .padding()
    .frame(width: 400)
}
