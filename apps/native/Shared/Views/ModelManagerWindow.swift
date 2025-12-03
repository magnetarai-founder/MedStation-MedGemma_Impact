//
//  ModelManagerWindow.swift
//  MagnetarStudio
//
//  Global model loading/unloading management
//  Separate floating window accessible from anywhere
//

import SwiftUI

struct ModelManagerWindow: View {
    @StateObject private var hotSlotManager = HotSlotManager.shared
    @StateObject private var memoryTracker = ModelMemoryTracker.shared
    @State private var availableModels: [String] = []
    @State private var isLoading = false
    @State private var searchText = ""
    @State private var showingEvictionPrompt = false
    @State private var modelToLoad: String?

    var body: some View {
        VStack(spacing: 0) {
            // Header
            header

            Divider()

            // Hot Slots Section
            ScrollView {
                VStack(alignment: .leading, spacing: 20) {
                    hotSlotsSection

                    Divider()
                        .padding(.vertical, 8)

                    availableModelsSection
                }
                .padding(20)
            }
        }
        .frame(width: 600, height: 700)
        .background(Color.surfacePrimary)
        .task {
            await loadData()
        }
        .alert("All Slots Full", isPresented: $showingEvictionPrompt) {
            evictionPromptButtons
        } message: {
            evictionPromptMessage
        }
    }

    // MARK: - Header

    private var header: some View {
        HStack {
            VStack(alignment: .leading, spacing: 4) {
                Text("Model Manager")
                    .font(.title2)
                    .fontWeight(.semibold)

                HStack(spacing: 12) {
                    // Total memory usage
                    Label("\(formattedMemory) in use", systemImage: "memorychip")
                        .font(.caption)
                        .foregroundColor(.textSecondary)

                    // Loaded count
                    Label("\(loadedModelsCount) loaded", systemImage: "bolt.fill")
                        .font(.caption)
                        .foregroundColor(.accentColor)
                }
            }

            Spacer()

            // Refresh button
            Button(action: { Task { await loadData() } }) {
                Image(systemName: "arrow.clockwise")
                    .foregroundColor(.textSecondary)
            }
            .buttonStyle(.plain)
            .disabled(isLoading)
        }
        .padding(20)
    }

    // MARK: - Hot Slots Section

    private var hotSlotsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Hot Slots")
                    .font(.headline)

                Spacer()

                Text("Quick access • Auto-load on startup")
                    .font(.caption)
                    .foregroundColor(.textSecondary)
            }

            // 4 hot slot cards
            LazyVGrid(columns: [
                GridItem(.flexible()),
                GridItem(.flexible())
            ], spacing: 12) {
                ForEach(1...4, id: \.self) { slotNumber in
                    hotSlotCard(slotNumber: slotNumber)
                }
            }
        }
    }

    private func hotSlotCard(slotNumber: Int) -> some View {
        let slot = hotSlotManager.hotSlots.first { $0.slotNumber == slotNumber }
        let isEmpty = slot?.isEmpty ?? true

        return VStack(alignment: .leading, spacing: 8) {
            // Slot header
            HStack {
                Text("Slot \(slotNumber)")
                    .font(.caption)
                    .foregroundColor(.textSecondary)

                Spacer()

                if let slot = slot, !isEmpty {
                    // Pin button
                    Button(action: { hotSlotManager.togglePin(slotNumber) }) {
                        Image(systemName: slot.isPinned ? "pin.fill" : "pin")
                            .font(.caption)
                            .foregroundColor(slot.isPinned ? .yellow : .textSecondary)
                    }
                    .buttonStyle(.plain)
                    .help(slot.isPinned ? "Unpin" : "Pin (prevent auto-eviction)")
                }
            }

            if isEmpty {
                // Empty slot
                VStack(spacing: 4) {
                    Image(systemName: "cube.transparent")
                        .font(.title2)
                        .foregroundColor(.textTertiary)

                    Text("Empty")
                        .font(.caption)
                        .foregroundColor(.textTertiary)
                }
                .frame(maxWidth: .infinity, minHeight: 80)
                .background(Color.surfaceSecondary.opacity(0.3))
                .cornerRadius(8)
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(style: StrokeStyle(lineWidth: 1, dash: [5]))
                        .foregroundColor(.textTertiary.opacity(0.3))
                )
            } else if let slot = slot, let modelName = slot.modelName {
                // Loaded model
                VStack(alignment: .leading, spacing: 6) {
                    HStack {
                        Text(modelName)
                            .font(.subheadline)
                            .fontWeight(.medium)
                            .lineLimit(1)

                        Spacer()

                        // Status indicator
                        Circle()
                            .fill(Color.green)
                            .frame(width: 6, height: 6)
                    }

                    // Memory usage
                    if let memoryGB = slot.memoryUsageGB {
                        HStack(spacing: 4) {
                            Image(systemName: "memorychip")
                                .font(.caption2)
                            Text(String(format: "%.1f GB", memoryGB))
                                .font(.caption2)
                        }
                        .foregroundColor(.textSecondary)
                    }

                    Spacer()

                    // Unload button
                    Button(action: {
                        Task { await unloadModel(slotNumber: slotNumber) }
                    }) {
                        HStack(spacing: 4) {
                            Image(systemName: "eject")
                                .font(.caption2)
                            Text("Unload")
                                .font(.caption2)
                        }
                        .foregroundColor(.red)
                    }
                    .buttonStyle(.plain)
                    .disabled(slot.isPinned && hotSlotManager.askBeforeUnpinning)
                }
                .padding(10)
                .frame(maxWidth: .infinity, minHeight: 80, alignment: .topLeading)
                .background(Color.accentColor.opacity(0.1))
                .cornerRadius(8)
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(Color.accentColor.opacity(0.3), lineWidth: 1.5)
                )
            }
        }
    }

    // MARK: - Available Models Section

    private var availableModelsSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack {
                Text("Available Models")
                    .font(.headline)

                Spacer()

                // Search
                HStack {
                    Image(systemName: "magnifyingglass")
                        .foregroundColor(.textSecondary)
                        .font(.caption)

                    TextField("Search...", text: $searchText)
                        .textFieldStyle(.plain)
                        .font(.caption)
                }
                .padding(.horizontal, 8)
                .padding(.vertical, 4)
                .background(Color.surfaceSecondary)
                .cornerRadius(6)
                .frame(width: 150)
            }

            // Model list
            LazyVStack(spacing: 8) {
                ForEach(filteredModels, id: \.self) { modelName in
                    availableModelRow(modelName: modelName)
                }
            }
        }
    }

    private func availableModelRow(modelName: String) -> some View {
        let isLoaded = hotSlotManager.hotSlots.contains { $0.modelName == modelName }

        return HStack {
            // Status indicator
            Circle()
                .fill(isLoaded ? Color.green : Color.gray.opacity(0.3))
                .frame(width: 8, height: 8)

            // Model name
            Text(modelName)
                .font(.subheadline)

            Spacer()

            // Memory estimate
            if let memory = memoryTracker.getMemoryUsage(for: modelName) {
                Text(String(format: "%.1f GB", memory))
                    .font(.caption)
                    .foregroundColor(.textSecondary)
            }

            // Load button
            if isLoaded {
                Text("Loaded")
                    .font(.caption)
                    .foregroundColor(.green)
            } else {
                Button(action: {
                    Task { await loadModel(modelName) }
                }) {
                    HStack(spacing: 4) {
                        Image(systemName: "arrow.down.circle")
                            .font(.caption)
                        Text("Load")
                            .font(.caption)
                    }
                    .foregroundColor(.accentColor)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(Color.surfaceSecondary)
        .cornerRadius(6)
    }

    // MARK: - Eviction Prompt

    private var evictionPromptButtons: some View {
        Group {
            Button("Cancel", role: .cancel) {
                modelToLoad = nil
            }

            Button("Auto Evict (LRU)") {
                Task { await autoEvictAndLoad() }
            }

            Button("Manual Selection") {
                showingEvictionPrompt = false
                // Window automatically stays open/comes to front
            }
        }
    }

    private var evictionPromptMessage: some View {
        Text("All 4 hot slots are full. Would you like to automatically evict the least recently used model, or manually select which model to unload?")
    }

    // MARK: - Actions

    private func loadData() async {
        isLoading = true

        // Load hot slots
        await hotSlotManager.loadHotSlots()

        // Fetch available models from backend
        do {
            let url = URL(string: "http://localhost:8000/api/v1/chat/models")!
            let (data, _) = try await URLSession.shared.data(from: url)

            struct ModelResponse: Codable {
                let name: String
            }

            let models = try JSONDecoder().decode([ModelResponse].self, from: data)
            availableModels = models.map { $0.name }
        } catch {
            print("Failed to fetch available models: \(error)")
        }

        // Refresh memory tracker
        await memoryTracker.refresh()

        isLoading = false
    }

    private func loadModel(_ modelName: String) async {
        // Check if all slots are full
        if hotSlotManager.areAllSlotsFull {
            modelToLoad = modelName
            showingEvictionPrompt = true
            return
        }

        // Find first empty slot
        if let emptySlot = hotSlotManager.hotSlots.first(where: { $0.isEmpty }) {
            do {
                try await hotSlotManager.assignToSlot(slotNumber: emptySlot.slotNumber, modelId: modelName)
                await loadData()
            } catch {
                print("Failed to load model: \(error)")
            }
        }
    }

    private func unloadModel(slotNumber: Int) async {
        do {
            try await hotSlotManager.removeFromSlot(slotNumber: slotNumber)
            await loadData()
        } catch {
            print("Failed to unload model: \(error)")
        }
    }

    private func autoEvictAndLoad() async {
        guard let modelName = modelToLoad else { return }

        // Find LRU slot
        if let evictSlot = hotSlotManager.findEvictionCandidate() {
            do {
                // Unload from old slot
                try await hotSlotManager.removeFromSlot(slotNumber: evictSlot)

                // Load new model into that slot
                try await hotSlotManager.assignToSlot(slotNumber: evictSlot, modelId: modelName)

                await loadData()
            } catch {
                print("Failed to auto-evict and load: \(error)")
            }
        }

        modelToLoad = nil
    }

    // MARK: - Helpers

    private var filteredModels: [String] {
        if searchText.isEmpty {
            return availableModels
        }
        return availableModels.filter { $0.localizedCaseInsensitiveContains(searchText) }
    }

    private var loadedModelsCount: Int {
        hotSlotManager.hotSlots.filter { !$0.isEmpty }.count
    }

    private var formattedMemory: String {
        let totalGB = hotSlotManager.hotSlots.compactMap { $0.memoryUsageGB }.reduce(0, +)
        return String(format: "%.1f GB", totalGB)
    }
}
