//
//  HotSlotManager.swift
//  MagnetarStudio
//
//  Manages hot slot assignments for quick model access
//  Part of Noah's Ark for the Digital Age - Intelligent model routing
//
//  Foundation: Matthew 7:24-25 - Built on the rock, not sand
//

import Foundation

// MARK: - Models

/// Hot slot assignment (global, not per-user)
struct HotSlot: Codable, Identifiable {
    let slotNumber: Int
    let modelId: String?  // nil if slot is empty
    let modelName: String?
    let isPinned: Bool
    let loadedAt: Date?
    let memoryUsageGB: Float?

    var id: Int { slotNumber }

    var isEmpty: Bool { modelId == nil }
}

/// Model available for hot slot assignment
struct AssignableModel: Codable, Identifiable {
    let id: String
    let name: String
    let displayName: String
    let size: String  // "3B", "7B", "8B", etc.
    let memoryGB: Float?
    let isLoaded: Bool
    let currentSlot: Int?  // Which slot it's in, if any
}

/// Hot slot response from backend
struct HotSlotsResponse: Codable {
    let hotSlots: [String: String?]  // "1": "model-id" or "1": null

    enum CodingKeys: String, CodingKey {
        case hotSlots = "hot_slots"
    }
}

/// Assign to slot response
struct AssignSlotResponse: Codable {
    let success: Bool
    let model: String
    let slotNumber: Int
    let hotSlots: [String: String?]

    enum CodingKeys: String, CodingKey {
        case success
        case model
        case slotNumber = "slot_number"
        case hotSlots = "hot_slots"
    }
}

/// Remove from slot response
struct RemoveSlotResponse: Codable {
    let success: Bool
    let slotNumber: Int
    let model: String?
    let hotSlots: [String: String?]

    enum CodingKeys: String, CodingKey {
        case success
        case slotNumber = "slot_number"
        case model
        case hotSlots = "hot_slots"
    }
}

// MARK: - Hot Slot Manager

/// Service for managing hot slot assignments
@MainActor
class HotSlotManager: ObservableObject {
    static let shared = HotSlotManager()

    @Published var hotSlots: [HotSlot] = []
    @Published var pinnedSlots: Set<Int> = []  // Which slots are pinned
    @Published var isLoading: Bool = false
    @Published var errorMessage: String?

    private let apiClient = ApiClient.shared

    // User preferences (synced with UserDefaults)
    @Published var immutableModels: Bool = false  // Require confirmation to unpin
    @Published var askBeforeUnpinning: Bool = true

    private init() {
        loadPreferences()
    }

    // MARK: - Hot Slot Operations

    /// Get current hot slot assignments from backend
    func loadHotSlots() async {
        isLoading = true
        errorMessage = nil

        do {
            let response: HotSlotsResponse = try await apiClient.request(
                "/v1/chat/hot-slots",
                method: .get
            )

            // Convert to HotSlot array
            var slots: [HotSlot] = []
            for slotNum in 1...4 {
                let key = String(slotNum)
                let modelId = response.hotSlots[key] ?? nil

                slots.append(HotSlot(
                    slotNumber: slotNum,
                    modelId: modelId,
                    modelName: modelId,  // TODO: Get display name from model registry
                    isPinned: pinnedSlots.contains(slotNum),
                    loadedAt: modelId != nil ? Date() : nil,
                    memoryUsageGB: nil  // TODO: Get from system resources
                ))
            }

            await MainActor.run {
                hotSlots = slots
                isLoading = false
            }
        } catch {
            print("Failed to load hot slots: \(error)")
            await MainActor.run {
                errorMessage = "Failed to load hot slots: \(error.localizedDescription)"
                isLoading = false
            }
        }
    }

    /// Assign a model to a specific hot slot
    func assignToSlot(slotNumber: Int, modelId: String) async throws {
        // Check if slot is pinned and immutable models is enabled
        if immutableModels && pinnedSlots.contains(slotNumber) {
            throw HotSlotError.slotImmutable(slotNumber)
        }

        let response: AssignSlotResponse = try await apiClient.request(
            path: "/v1/chat/hot-slots/\(slotNumber)",
            method: .post,
            jsonBody: ["model_name": modelId]
        )

        if response.success {
            await loadHotSlots()
        } else {
            throw HotSlotError.assignmentFailed(modelId, slotNumber)
        }
    }

    /// Remove a model from a hot slot
    func removeFromSlot(slotNumber: Int) async throws {
        // Check if slot is pinned
        if pinnedSlots.contains(slotNumber) {
            if askBeforeUnpinning {
                throw HotSlotError.slotPinned(slotNumber)
            }
        }

        let response: RemoveSlotResponse = try await apiClient.request(
            path: "/v1/chat/hot-slots/\(slotNumber)",
            method: .delete
        )

        if response.success {
            await loadHotSlots()
        } else {
            throw HotSlotError.removalFailed(slotNumber)
        }
    }

    /// Load all hot slot models into memory
    func loadAllHotSlots(keepAlive: String = "1h") async throws {
        struct LoadResponse: Codable {
            let total: Int
            let results: [LoadResult]
            let keepAlive: String

            enum CodingKeys: String, CodingKey {
                case total
                case results
                case keepAlive = "keep_alive"
            }
        }

        struct LoadResult: Codable {
            let slot: Int
            let model: String
            let loaded: Bool
        }

        let response: LoadResponse = try await apiClient.request(
            path: "/v1/chat/hot-slots/load",
            method: .post,
            jsonBody: ["keep_alive": keepAlive]
        )

        print("✓ Loaded \(response.total) hot slot models")

        // Reload hot slots to get updated state
        await loadHotSlots()
    }

    // MARK: - Pinning

    /// Pin a slot (prevent eviction)
    func pinSlot(_ slotNumber: Int) {
        pinnedSlots.insert(slotNumber)
        savePreferences()

        // Update hot slots array
        if let index = hotSlots.firstIndex(where: { $0.slotNumber == slotNumber }) {
            hotSlots[index] = HotSlot(
                slotNumber: slotNumber,
                modelId: hotSlots[index].modelId,
                modelName: hotSlots[index].modelName,
                isPinned: true,
                loadedAt: hotSlots[index].loadedAt,
                memoryUsageGB: hotSlots[index].memoryUsageGB
            )
        }
    }

    /// Unpin a slot (allow eviction)
    func unpinSlot(_ slotNumber: Int) {
        pinnedSlots.remove(slotNumber)
        savePreferences()

        // Update hot slots array
        if let index = hotSlots.firstIndex(where: { $0.slotNumber == slotNumber }) {
            hotSlots[index] = HotSlot(
                slotNumber: slotNumber,
                modelId: hotSlots[index].modelId,
                modelName: hotSlots[index].modelName,
                isPinned: false,
                loadedAt: hotSlots[index].loadedAt,
                memoryUsageGB: hotSlots[index].memoryUsageGB
            )
        }
    }

    /// Toggle pin state for a slot
    func togglePin(_ slotNumber: Int) {
        if pinnedSlots.contains(slotNumber) {
            unpinSlot(slotNumber)
        } else {
            pinSlot(slotNumber)
        }
    }

    // MARK: - Eviction Logic

    /// Find best slot to evict (least recently used, unpinned)
    func findEvictionCandidate() -> Int? {
        // Filter unpinned slots with models
        let candidates = hotSlots.filter { slot in
            !slot.isEmpty && !slot.isPinned
        }

        // Sort by loadedAt (oldest first)
        let sorted = candidates.sorted { a, b in
            guard let aDate = a.loadedAt, let bDate = b.loadedAt else {
                return a.loadedAt != nil  // Slots without loadedAt go last
            }
            return aDate < bDate
        }

        return sorted.first?.slotNumber
    }

    /// Check if all slots are full
    var areAllSlotsFull: Bool {
        hotSlots.allSatisfy { !$0.isEmpty }
    }

    /// Check if any slot is available (empty or unpinned)
    var hasAvailableSlot: Bool {
        hotSlots.contains { $0.isEmpty || !$0.isPinned }
    }

    // MARK: - Loaded Models (for SystemResourceState)

    /// Get loaded models for AppContext
    func loadedModels() -> [LoadedModel] {
        hotSlots.compactMap { slot in
            guard let modelId = slot.modelId else { return nil }

            return LoadedModel(
                id: modelId,
                name: slot.modelName ?? modelId,
                slotNumber: slot.slotNumber,
                memoryUsageGB: slot.memoryUsageGB ?? 3.0,  // Default estimate
                lastUsedAt: slot.loadedAt ?? Date(),
                isPinned: slot.isPinned
            )
        }
    }

    // MARK: - Preferences

    private func loadPreferences() {
        let defaults = UserDefaults.standard

        // Load pinned slots
        if let pinnedArray = defaults.array(forKey: "hotSlot.pinnedSlots") as? [Int] {
            pinnedSlots = Set(pinnedArray)
        }

        // Load immutable models setting
        immutableModels = defaults.bool(forKey: "hotSlot.immutableModels")

        // Load ask before unpinning setting (default true)
        if defaults.object(forKey: "hotSlot.askBeforeUnpinning") != nil {
            askBeforeUnpinning = defaults.bool(forKey: "hotSlot.askBeforeUnpinning")
        } else {
            askBeforeUnpinning = true
        }
    }

    private func savePreferences() {
        let defaults = UserDefaults.standard

        defaults.set(Array(pinnedSlots), forKey: "hotSlot.pinnedSlots")
        defaults.set(immutableModels, forKey: "hotSlot.immutableModels")
        defaults.set(askBeforeUnpinning, forKey: "hotSlot.askBeforeUnpinning")
    }

    func updateImmutableModels(_ enabled: Bool) {
        immutableModels = enabled
        savePreferences()
    }

    func updateAskBeforeUnpinning(_ enabled: Bool) {
        askBeforeUnpinning = enabled
        savePreferences()
    }
}

// MARK: - Errors

enum HotSlotError: LocalizedError {
    case slotImmutable(Int)
    case slotPinned(Int)
    case assignmentFailed(String, Int)
    case removalFailed(Int)
    case noAvailableSlot

    var errorDescription: String? {
        switch self {
        case .slotImmutable(let slot):
            return "Slot \(slot) is pinned and immutable models is enabled. Unpin first."
        case .slotPinned(let slot):
            return "Slot \(slot) is pinned. Unpin first to remove the model."
        case .assignmentFailed(let model, let slot):
            return "Failed to assign '\(model)' to slot \(slot)"
        case .removalFailed(let slot):
            return "Failed to remove model from slot \(slot)"
        case .noAvailableSlot:
            return "All slots are full and pinned. Cannot load new model."
        }
    }
}
