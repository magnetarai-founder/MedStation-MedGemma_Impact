//
//  SmartModelPicker.swift
//  MagnetarStudio
//
//  Smart model dropdown that shows:
//  1. Intelligent routing
//  2. Loaded models (from hot slots)
//  3. Available models (can be loaded)
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "SmartModelPicker")

struct SmartModelPicker: View {
    @Binding var selectedMode: String  // "intelligent" or specific model
    @Binding var selectedModelId: String?
    @State private var hotSlotManager = HotSlotManager.shared
    @State private var availableModels: [String] = []
    @State private var isExpanded = false

    var body: some View {
        Menu {
            // Intelligent routing (always first)
            Button(action: {
                selectedMode = "intelligent"
                selectedModelId = nil
            }) {
                HStack {
                    Image(systemName: "sparkles")
                    Text("Intelligent (Apple FM)")

                    if selectedMode == "intelligent" {
                        Spacer()
                        Image(systemName: "checkmark")
                            .foregroundColor(.accentColor)
                    }
                }
            }

            Divider()

            // Loaded Models section
            if !loadedModels.isEmpty {
                Section("Loaded Models") {
                    ForEach(loadedModels, id: \.self) { modelName in
                        Button(action: {
                            selectedMode = "manual"
                            selectedModelId = modelName
                        }) {
                            HStack {
                                Circle()
                                    .fill(Color.green)
                                    .frame(width: 6, height: 6)
                                Text(modelName)

                                if selectedMode == "manual" && selectedModelId == modelName {
                                    Spacer()
                                    Image(systemName: "checkmark")
                                        .foregroundColor(.accentColor)
                                }
                            }
                        }
                    }
                }

                Divider()
            }

            // Available Models section
            if !unloadedModels.isEmpty {
                Section("Available Models") {
                    ForEach(unloadedModels.prefix(5), id: \.self) { modelName in
                        Button(action: {
                            // Prompt to load model
                            Task {
                                await loadModelAndSelect(modelName)
                            }
                        }) {
                            HStack {
                                Circle()
                                    .stroke(Color.gray, lineWidth: 1)
                                    .frame(width: 6, height: 6)
                                Text(modelName)
                                Spacer()
                                Image(systemName: "arrow.down.circle")
                                    .foregroundColor(.gray)
                                    .font(.caption)
                            }
                        }
                    }

                    if unloadedModels.count > 5 {
                        Button("Show all models...") {
                            openModelManager()
                        }
                    }
                }
            }
        } label: {
            HStack(spacing: 6) {
                if selectedMode == "intelligent" {
                    Image(systemName: "sparkles")
                        .font(.caption)
                    Text("Intelligent (Apple FM)")
                        .font(.caption)
                } else if let modelId = selectedModelId {
                    Circle()
                        .fill(Color.green)
                        .frame(width: 6, height: 6)
                    Text(modelId)
                        .font(.caption)
                }

                Image(systemName: "chevron.down")
                    .font(.caption2)
            }
            .foregroundColor(.textSecondary)
            .padding(.horizontal, 10)
            .padding(.vertical, 6)
            .background(Color.surfaceSecondary)
            .cornerRadius(6)
        }
        .task {
            await loadData()
        }
    }

    // MARK: - Computed Properties

    private var loadedModels: [String] {
        hotSlotManager.hotSlots
            .compactMap { $0.modelName }
            .sorted()
    }

    private var unloadedModels: [String] {
        let loaded = Set(loadedModels)
        return availableModels
            .filter { !loaded.contains($0) }
            .sorted()
    }

    // MARK: - Actions

    private func loadData() async {
        // Load hot slots
        await hotSlotManager.loadHotSlots()

        // Fetch available models
        do {
            let url = URL(string: APIConfiguration.shared.chatModelsURL)!
            let (data, _) = try await URLSession.shared.data(from: url)

            struct ModelResponse: Codable {
                let name: String
            }

            let models = try JSONDecoder().decode([ModelResponse].self, from: data)
            availableModels = models.map { $0.name }
        } catch {
            logger.error("Failed to fetch available models: \(error)")
        }
    }

    private func loadModelAndSelect(_ modelName: String) async {
        // Check if all slots are full
        if hotSlotManager.areAllSlotsFull {
            // Show prompt: auto-evict or manual
            // For now, auto-evict LRU
            if let evictSlot = hotSlotManager.findEvictionCandidate() {
                do {
                    try await hotSlotManager.removeFromSlot(slotNumber: evictSlot)
                    try await hotSlotManager.assignToSlot(slotNumber: evictSlot, modelId: modelName)

                    // Select the model
                    selectedMode = "manual"
                    selectedModelId = modelName

                    await loadData()
                } catch {
                    logger.error("Failed to load model: \(error)")
                }
            }
        } else {
            // Find empty slot
            if let emptySlot = hotSlotManager.hotSlots.first(where: { $0.isEmpty }) {
                do {
                    try await hotSlotManager.assignToSlot(slotNumber: emptySlot.slotNumber, modelId: modelName)

                    // Select the model
                    selectedMode = "manual"
                    selectedModelId = modelName

                    await loadData()
                } catch {
                    logger.error("Failed to load model: \(error)")
                }
            }
        }
    }

    private func openModelManager() {
        #if os(macOS)
        NSApp.sendAction(#selector(NSResponder.newWindowForTab(_:)), to: nil, from: nil)
        #endif
    }
}
