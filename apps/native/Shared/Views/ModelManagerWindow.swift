//
//  ModelManagerWindow.swift
//  MagnetarStudio
//
//  Compact model loading/unloading management (LM Studio style)
//  Rectangular stacked slots with eject buttons
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
    @State private var slotToEvict: Int?

    var body: some View {
        VStack(spacing: 0) {
            // Compact header
            compactHeader

            Divider()

            // Hot Slots - LM Studio style stacked rectangles
            ScrollView {
                VStack(spacing: 12) {
                    // Hot Slots Section
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Hot Slots")
                            .font(.headline)
                            .padding(.horizontal, 16)
                            .padding(.top, 16)

                        VStack(spacing: 6) {
                            ForEach(1...4, id: \.self) { slotNumber in
                                hotSlotRow(slotNumber: slotNumber)
                            }
                        }
                        .padding(.horizontal, 16)
                    }

                    Divider()
                        .padding(.vertical, 8)

                    // Available Models Section
                    VStack(alignment: .leading, spacing: 8) {
                        HStack {
                            Text("Available Models")
                                .font(.headline)

                            Spacer()

                            // Search
                            HStack(spacing: 6) {
                                Image(systemName: "magnifyingglass")
                                    .foregroundColor(.textSecondary)
                                    .font(.caption)

                                TextField("Search", text: $searchText)
                                    .textFieldStyle(.plain)
                                    .font(.caption)
                            }
                            .padding(.horizontal, 8)
                            .padding(.vertical, 4)
                            .background(Color.surfaceSecondary)
                            .cornerRadius(6)
                            .frame(width: 140)
                        }
                        .padding(.horizontal, 16)

                        VStack(spacing: 4) {
                            ForEach(filteredModels, id: \.self) { modelName in
                                availableModelRow(modelName: modelName)
                            }
                        }
                        .padding(.horizontal, 16)
                    }
                    .padding(.bottom, 16)
                }
            }
        }
        .frame(width: 480, height: 520)
        .background(Color.surfacePrimary)
        .task {
            await loadData()
        }
        .alert("All Slots Full", isPresented: $showingEvictionPrompt) {
            Button("Cancel", role: .cancel) {
                modelToLoad = nil
                slotToEvict = nil
            }

            Button("Auto Evict (LRU)") {
                Task { await autoEvictAndLoad() }
            }

            Button("Choose Slot", role: .destructive) {
                showingEvictionPrompt = false
                // Slot picker will show in the UI
            }
        } message: {
            Text("All 4 hot slots are full. Choose which model to unload, or auto-evict the least recently used model.")
        }
    }

    // MARK: - Compact Header

    private var compactHeader: some View {
        HStack(spacing: 12) {
            VStack(alignment: .leading, spacing: 2) {
                Text("Model Manager")
                    .font(.headline)

                HStack(spacing: 8) {
                    HStack(spacing: 4) {
                        Image(systemName: "memorychip")
                            .font(.caption2)
                        Text(formattedMemory)
                            .font(.caption2)
                    }
                    .foregroundColor(.textSecondary)

                    Text("•")
                        .font(.caption2)
                        .foregroundColor(.textTertiary)

                    HStack(spacing: 4) {
                        Image(systemName: "bolt.fill")
                            .font(.caption2)
                        Text("\(loadedModelsCount)/4")
                            .font(.caption2)
                    }
                    .foregroundColor(.accentColor)
                }
            }

            Spacer()

            Button(action: { Task { await loadData() } }) {
                Image(systemName: "arrow.clockwise")
                    .font(.caption)
                    .foregroundColor(.textSecondary)
            }
            .buttonStyle(.plain)
            .disabled(isLoading)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
    }

    // MARK: - Hot Slot Row (LM Studio style)

    private func hotSlotRow(slotNumber: Int) -> some View {
        let slot = hotSlotManager.hotSlots.first { $0.slotNumber == slotNumber }
        let isEmpty = slot?.isEmpty ?? true
        let isPinned = slot?.isPinned ?? false

        return HStack(spacing: 0) {
            // Slot number indicator
            Text("\(slotNumber)")
                .font(.system(size: 11, weight: .semibold, design: .monospaced))
                .foregroundColor(.textTertiary)
                .frame(width: 24)

            if isEmpty {
                // Empty slot
                HStack {
                    Text("Empty Slot")
                        .font(.subheadline)
                        .foregroundColor(.textTertiary)

                    Spacer()

                    Image(systemName: "circle.dashed")
                        .font(.caption)
                        .foregroundColor(.textTertiary)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .background(Color.surfaceSecondary.opacity(0.3))
                .cornerRadius(8)
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(style: StrokeStyle(lineWidth: 1, dash: [4, 2]))
                        .foregroundColor(.textTertiary.opacity(0.3))
                )
            } else if let modelName = slot?.modelName {
                // Loaded model - compact row
                HStack(spacing: 10) {
                    // Status indicator
                    Circle()
                        .fill(Color.green)
                        .frame(width: 6, height: 6)

                    // Model name
                    VStack(alignment: .leading, spacing: 2) {
                        Text(modelName)
                            .font(.system(size: 13, weight: .medium))
                            .lineLimit(1)

                        // Memory usage
                        if let memoryGB = slot?.memoryUsageGB {
                            Text(String(format: "%.1f GB", memoryGB))
                                .font(.system(size: 10))
                                .foregroundColor(.textSecondary)
                        }
                    }

                    Spacer()

                    // Pin button
                    Button(action: { hotSlotManager.togglePin(slotNumber) }) {
                        Image(systemName: isPinned ? "pin.fill" : "pin")
                            .font(.caption)
                            .foregroundColor(isPinned ? .yellow : .textSecondary)
                    }
                    .buttonStyle(.plain)
                    .help(isPinned ? "Unpin" : "Pin")

                    // Eject button
                    Button(action: {
                        Task { await unloadModel(slotNumber: slotNumber) }
                    }) {
                        Image(systemName: "eject.fill")
                            .font(.caption)
                            .foregroundColor(.red.opacity(0.8))
                    }
                    .buttonStyle(.plain)
                    .help("Unload Model")
                    .disabled(isPinned && hotSlotManager.askBeforeUnpinning)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .background(Color.accentColor.opacity(0.08))
                .cornerRadius(8)
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(Color.accentColor.opacity(0.2), lineWidth: 1)
                )
            }
        }
    }

    // MARK: - Available Model Row

    private func availableModelRow(modelName: String) -> some View {
        let isLoaded = hotSlotManager.hotSlots.contains { $0.modelName == modelName }

        return HStack(spacing: 10) {
            // Status indicator
            if isLoaded {
                Circle()
                    .fill(Color.green)
                    .frame(width: 6, height: 6)
            } else {
                Circle()
                    .stroke(Color.gray.opacity(0.4), lineWidth: 1)
                    .frame(width: 6, height: 6)
            }

            // Model name
            Text(modelName)
                .font(.system(size: 12))
                .foregroundColor(isLoaded ? .textPrimary : .textSecondary)

            Spacer()

            // Memory estimate
            if let memory = memoryTracker.getMemoryUsage(for: modelName) {
                Text(String(format: "%.1f GB", memory))
                    .font(.system(size: 10))
                    .foregroundColor(.textTertiary)
            }

            // Load/Loaded indicator
            if isLoaded {
                Text("Loaded")
                    .font(.system(size: 10, weight: .medium))
                    .foregroundColor(.green)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Color.green.opacity(0.1))
                    .cornerRadius(4)
            } else {
                Button(action: {
                    Task { await loadModel(modelName) }
                }) {
                    HStack(spacing: 3) {
                        Image(systemName: "arrow.down.circle.fill")
                            .font(.system(size: 10))
                        Text("Load")
                            .font(.system(size: 10, weight: .medium))
                    }
                    .foregroundColor(.accentColor)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Color.accentColor.opacity(0.1))
                    .cornerRadius(4)
                }
                .buttonStyle(.plain)
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(Color.surfaceSecondary.opacity(isLoaded ? 0.3 : 0.5))
        .cornerRadius(6)
    }

    // MARK: - Actions

    private func loadData() async {
        isLoading = true

        await hotSlotManager.loadHotSlots()

        do {
            let url = URL(string: "http://localhost:8000/api/v1/chat/models")!
            let (data, _) = try await URLSession.shared.data(from: url)

            struct ModelResponse: Codable {
                let name: String
                let size: Int
            }

            let models = try JSONDecoder().decode([ModelResponse].self, from: data)
            availableModels = models.map { $0.name }
        } catch {
            print("Failed to fetch available models: \(error)")
        }

        await memoryTracker.refresh()

        isLoading = false
    }

    private func loadModel(_ modelName: String) async {
        if hotSlotManager.areAllSlotsFull {
            modelToLoad = modelName
            showingEvictionPrompt = true
            return
        }

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

        if let evictSlot = hotSlotManager.findEvictionCandidate() {
            do {
                try await hotSlotManager.removeFromSlot(slotNumber: evictSlot)
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
            return availableModels.sorted()
        }
        return availableModels
            .filter { $0.localizedCaseInsensitiveContains(searchText) }
            .sorted()
    }

    private var loadedModelsCount: Int {
        hotSlotManager.hotSlots.filter { !$0.isEmpty }.count
    }

    private var formattedMemory: String {
        let totalGB = hotSlotManager.hotSlots.compactMap { $0.memoryUsageGB }.reduce(0, +)
        return String(format: "%.1f GB", totalGB)
    }
}
