//
//  ModelManagerWindow.swift
//  MagnetarStudio
//
//  Compact model loading/unloading management
//  Slot number buttons [1][2][3][4] for intelligent loading
//  Tag-based filtering from MagnetarHub
//

import SwiftUI

struct ModelManagerWindow: View {
    @StateObject private var hotSlotManager = HotSlotManager.shared
    @StateObject private var memoryTracker = ModelMemoryTracker.shared
    @State private var availableModels: [ModelWithTags] = []
    @State private var isLoading = false
    @State private var searchText = ""
    @State private var selectedTag: String?
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

                    // Tag Filter
                    tagFilterSection

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
                            ForEach(filteredModels, id: \.name) { model in
                                availableModelRow(model: model)
                            }
                        }
                        .padding(.horizontal, 16)
                    }
                    .padding(.bottom, 16)
                }
            }
        }
        .frame(minWidth: 520, idealWidth: 520, maxWidth: .infinity,
               minHeight: 580, idealHeight: 580, maxHeight: .infinity)
        .background(Color.surfacePrimary)
        .task {
            await loadData()
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

    // MARK: - Tag Filter Section

    private var tagFilterSection: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 6) {
                // All models
                tagFilterChip(tag: nil, label: "All")

                ForEach(availableTags, id: \.self) { tag in
                    tagFilterChip(tag: tag, label: tag.capitalized)
                }
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 4)
        }
    }

    private func tagFilterChip(tag: String?, label: String) -> some View {
        Button(action: {
            selectedTag = tag
        }) {
            Text(label)
                .font(.system(size: 11, weight: .medium))
                .foregroundColor(selectedTag == tag ? .white : .textSecondary)
                .padding(.horizontal, 10)
                .padding(.vertical, 4)
                .background(selectedTag == tag ? Color.accentColor : Color.surfaceSecondary)
                .cornerRadius(12)
        }
        .buttonStyle(.plain)
    }

    // MARK: - Hot Slot Row

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

    // MARK: - Available Model Row with Slot Buttons

    private func availableModelRow(model: ModelWithTags) -> some View {
        let isLoaded = hotSlotManager.hotSlots.contains { $0.modelName == model.name }

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

            // Model name + tags
            VStack(alignment: .leading, spacing: 3) {
                Text(model.name)
                    .font(.system(size: 12, weight: .medium))
                    .foregroundColor(isLoaded ? .textPrimary : .textSecondary)

                // Tags
                if !model.tags.isEmpty {
                    HStack(spacing: 4) {
                        ForEach(model.tags.prefix(3), id: \.self) { tag in
                            Text(tag)
                                .font(.system(size: 9))
                                .foregroundColor(.textTertiary)
                                .padding(.horizontal, 4)
                                .padding(.vertical, 1)
                                .background(Color.accentColor.opacity(0.1))
                                .cornerRadius(3)
                        }
                    }
                }
            }

            Spacer()

            // Memory estimate
            if let memory = memoryTracker.getMemoryUsage(for: model.name) {
                Text(String(format: "%.1f GB", memory))
                    .font(.system(size: 10))
                    .foregroundColor(.textTertiary)
            }

            // Slot number buttons [1][2][3][4]
            if isLoaded {
                Text("Loaded")
                    .font(.system(size: 10, weight: .medium))
                    .foregroundColor(.green)
                    .padding(.horizontal, 6)
                    .padding(.vertical, 2)
                    .background(Color.green.opacity(0.1))
                    .cornerRadius(4)
            } else {
                HStack(spacing: 4) {
                    ForEach(1...4, id: \.self) { slotNumber in
                        slotButton(slotNumber: slotNumber, modelName: model.name)
                    }
                }
            }
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(Color.surfaceSecondary.opacity(isLoaded ? 0.3 : 0.5))
        .cornerRadius(6)
    }

    // MARK: - Slot Button [1][2][3][4]

    private func slotButton(slotNumber: Int, modelName: String) -> some View {
        let slot = hotSlotManager.hotSlots.first { $0.slotNumber == slotNumber }
        let isOccupied = !(slot?.isEmpty ?? true)

        return Button(action: {
            Task {
                await loadModelToSlot(modelName: modelName, slotNumber: slotNumber)
            }
        }) {
            Text("\(slotNumber)")
                .font(.system(size: 10, weight: .semibold, design: .monospaced))
                .foregroundColor(isOccupied ? .textTertiary : .accentColor)
                .frame(width: 20, height: 20)
                .background(isOccupied ? Color.gray.opacity(0.2) : Color.accentColor.opacity(0.15))
                .cornerRadius(4)
                .overlay(
                    RoundedRectangle(cornerRadius: 4)
                        .stroke(isOccupied ? Color.clear : Color.accentColor.opacity(0.4), lineWidth: 1)
                )
        }
        .buttonStyle(.plain)
        .disabled(isOccupied)
        .help(isOccupied ? "Slot \(slotNumber) occupied" : "Load to slot \(slotNumber)")
    }

    // MARK: - Actions

    private func loadData() async {
        isLoading = true

        await hotSlotManager.loadHotSlots()

        // Fetch models with tags
        do {
            let url = URL(string: "http://localhost:8000/api/v1/chat/models/with-tags")!
            let (data, _) = try await URLSession.shared.data(from: url)

            struct ModelResponseWithTags: Codable {
                let name: String
                let size: Int
                let tags: [String]
            }

            let models = try JSONDecoder().decode([ModelResponseWithTags].self, from: data)
            availableModels = models.map { ModelWithTags(name: $0.name, tags: $0.tags) }
        } catch {
            print("Failed to fetch models with tags: \(error)")
            // Fallback to basic models endpoint
            do {
                let url = URL(string: "http://localhost:8000/api/v1/chat/models")!
                let (data, _) = try await URLSession.shared.data(from: url)

                struct ModelResponse: Codable {
                    let name: String
                }

                let models = try JSONDecoder().decode([ModelResponse].self, from: data)
                availableModels = models.map { ModelWithTags(name: $0.name, tags: []) }
            } catch {
                print("Failed to fetch basic models: \(error)")
            }
        }

        await memoryTracker.refresh()

        isLoading = false
    }

    private func loadModelToSlot(modelName: String, slotNumber: Int) async {
        do {
            try await hotSlotManager.assignToSlot(slotNumber: slotNumber, modelId: modelName)
            await loadData()
        } catch {
            print("Failed to load model to slot \(slotNumber): \(error)")
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

    // MARK: - Helpers

    private var filteredModels: [ModelWithTags] {
        var models = availableModels

        // Filter by tag
        if let tag = selectedTag {
            models = models.filter { $0.tags.contains(tag) }
        }

        // Filter by search
        if !searchText.isEmpty {
            models = models.filter { $0.name.localizedCaseInsensitiveContains(searchText) }
        }

        return models.sorted { $0.name < $1.name }
    }

    private var availableTags: [String] {
        let allTags = Set(availableModels.flatMap { $0.tags })
        return Array(allTags).sorted()
    }

    private var loadedModelsCount: Int {
        hotSlotManager.hotSlots.filter { !$0.isEmpty }.count
    }

    private var formattedMemory: String {
        let totalGB = hotSlotManager.hotSlots.compactMap { $0.memoryUsageGB }.reduce(0, +)
        return String(format: "%.1f GB", totalGB)
    }
}

// MARK: - Model With Tags

struct ModelWithTags {
    let name: String
    let tags: [String]
}
