//
//  HotSlotManager.swift
//  MedStation
//
//  Manages model hot slots for instant inference.
//  Models assigned to hot slots stay loaded in Ollama for zero-latency responses.
//

import Foundation
import Observation
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "HotSlotManager")

// MARK: - HotSlot

struct HotSlot: Identifiable, Sendable {
    let slotNumber: Int
    var modelId: String?
    var modelName: String?
    var isPinned: Bool
    var isLoaded: Bool
    var loadedAt: Date?
    var memoryUsageGB: Float?

    var id: Int { slotNumber }
    var isEmpty: Bool { modelId == nil }

    static func empty(slot: Int) -> HotSlot {
        HotSlot(slotNumber: slot, modelId: nil, modelName: nil, isPinned: false, isLoaded: false, loadedAt: nil, memoryUsageGB: nil)
    }
}

// MARK: - HotSlotManager

@MainActor
@Observable
final class HotSlotManager {
    static let shared = HotSlotManager()

    var hotSlots: [HotSlot] = (1...4).map { HotSlot.empty(slot: $0) }
    var immutableModels: Bool = false
    var askBeforeUnpinning: Bool = true

    var areAllSlotsFull: Bool {
        hotSlots.allSatisfy { !$0.isEmpty }
    }

    private init() {}

    // MARK: - Loading

    func loadHotSlots() async {
        do {
            let baseURL = APIConfiguration.shared.baseURL
            guard let url = URL(string: "\(baseURL)/v1/models/hot-slots") else { return }
            let (data, _) = try await URLSession.shared.data(from: url)

            struct SlotResponse: Codable {
                let slotNumber: Int
                let modelId: String?
                let modelName: String?
                let isPinned: Bool
                let isLoaded: Bool
            }

            let slots = try JSONDecoder().decode([SlotResponse].self, from: data)
            hotSlots = slots.map { s in
                HotSlot(
                    slotNumber: s.slotNumber,
                    modelId: s.modelId,
                    modelName: s.modelName ?? s.modelId,
                    isPinned: s.isPinned,
                    isLoaded: s.isLoaded
                )
            }
        } catch {
            logger.warning("Failed to load hot slots: \(error.localizedDescription)")
        }
    }

    func loadAllHotSlots() async throws {
        let baseURL = APIConfiguration.shared.baseURL
        guard let url = URL(string: "\(baseURL)/v1/models/hot-slots/load-all") else { return }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        let (_, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }
        await loadHotSlots()
    }

    // MARK: - Slot Management

    func assignToSlot(slotNumber: Int, modelId: String) async throws {
        let baseURL = APIConfiguration.shared.baseURL
        guard let url = URL(string: "\(baseURL)/v1/models/hot-slots/\(slotNumber)") else { return }

        var request = URLRequest(url: url)
        request.httpMethod = "PUT"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        let body = try JSONEncoder().encode(["modelId": modelId])
        request.httpBody = body

        let (_, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }

        if let index = hotSlots.firstIndex(where: { $0.slotNumber == slotNumber }) {
            hotSlots[index].modelId = modelId
            hotSlots[index].modelName = modelId
            hotSlots[index].isLoaded = true
        }
    }

    func removeFromSlot(slotNumber: Int) async throws {
        let baseURL = APIConfiguration.shared.baseURL
        guard let url = URL(string: "\(baseURL)/v1/models/hot-slots/\(slotNumber)") else { return }

        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"

        let (_, response) = try await URLSession.shared.data(for: request)
        guard let httpResponse = response as? HTTPURLResponse, httpResponse.statusCode == 200 else {
            throw URLError(.badServerResponse)
        }

        if let index = hotSlots.firstIndex(where: { $0.slotNumber == slotNumber }) {
            hotSlots[index] = .empty(slot: slotNumber)
        }
    }

    func togglePin(_ slotNumber: Int) async {
        if let index = hotSlots.firstIndex(where: { $0.slotNumber == slotNumber }) {
            hotSlots[index].isPinned.toggle()
        }
    }

    func unpinSlot(_ slotNumber: Int) async {
        if let index = hotSlots.firstIndex(where: { $0.slotNumber == slotNumber }) {
            hotSlots[index].isPinned = false
        }
    }

    func findEvictionCandidate() -> Int? {
        // Prefer unpinned, then least recently used
        hotSlots
            .filter { !$0.isEmpty && !$0.isPinned }
            .first?
            .slotNumber
    }

    // MARK: - Settings

    func updateImmutableModels(_ value: Bool) {
        immutableModels = value
        UserDefaults.standard.set(value, forKey: "hotSlots.immutableModels")
    }

    func updateAskBeforeUnpinning(_ value: Bool) {
        askBeforeUnpinning = value
        UserDefaults.standard.set(value, forKey: "hotSlots.askBeforeUnpinning")
    }
}
