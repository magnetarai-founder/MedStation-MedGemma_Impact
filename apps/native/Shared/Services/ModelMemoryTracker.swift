//
//  ModelMemoryTracker.swift
//  MagnetarStudio
//
//  Tracks model memory usage by querying Ollama API
//  Enables smart hot slot management and prevents OOM crashes
//

import Foundation
import Observation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "ModelMemoryTracker")

// MARK: - Ollama API Models

struct OllamaTagsResponseMemory: Codable, Sendable {
    let models: [OllamaModelMemory]
}

struct OllamaModelMemory: Codable, Sendable {
    let name: String
    let size: Int64  // Size in bytes
    let modifiedAt: String
    let details: OllamaModelDetailsMemory

    enum CodingKeys: String, CodingKey {
        case name, size
        case modifiedAt = "modified_at"
        case details
    }

    /// Size in GB for display
    var sizeGB: Double {
        return Double(size) / 1_073_741_824.0  // 1024^3
    }
}

struct OllamaModelDetailsMemory: Codable, Sendable {
    let parameterSize: String
    let quantizationLevel: String
    let format: String
    let family: String

    enum CodingKeys: String, CodingKey {
        case parameterSize = "parameter_size"
        case quantizationLevel = "quantization_level"
        case format, family
    }
}

// MARK: - Memory Tracker

@MainActor
@Observable
class ModelMemoryTracker {
    static let shared = ModelMemoryTracker()

    private(set) var modelSizes: [String: Double] = [:]  // modelId -> GB
    private(set) var totalMemoryUsed: Double = 0.0  // Total GB of loaded models
    private(set) var lastUpdated: Date?

    private var ollamaBaseURL: String { APIConfiguration.shared.ollamaURL }
    private var updateTask: Task<Void, Never>?

    private init() {
        // Auto-refresh on init
        Task { [weak self] in
            await self?.refresh()
        }
    }

    // MARK: - Public API

    /// Get memory usage for a specific model in GB
    func getMemoryUsage(for modelId: String) -> Float? {
        return modelSizes[modelId].map { Float($0) }
    }

    /// Get formatted memory string (e.g., "3.8 GB")
    func getFormattedSize(for modelId: String) -> String? {
        guard let sizeGB = modelSizes[modelId] else { return nil }
        return String(format: "%.1f GB", sizeGB)
    }

    /// Refresh model sizes from Ollama
    func refresh() async {
        do {
            guard let url = URL(string: "\(ollamaBaseURL)/api/tags") else {
                logger.error("Invalid Ollama tags URL")
                return
            }
            let (data, _) = try await URLSession.shared.data(from: url)

            let response = try JSONDecoder().decode(OllamaTagsResponseMemory.self, from: data)

            // Update model sizes
            var newSizes: [String: Double] = [:]
            for model in response.models {
                newSizes[model.name] = model.sizeGB
            }

            modelSizes = newSizes
            lastUpdated = Date()

            // Calculate total memory of loaded models (hot slots)
            await calculateTotalMemoryUsed()

            logger.info("Updated model sizes: \(self.modelSizes.count) models")

        } catch {
            logger.warning("Failed to refresh model sizes from Ollama: \(error)")
        }
    }

    // MARK: - Private Helpers

    private func calculateTotalMemoryUsed() async {
        let hotSlotManager = HotSlotManager.shared
        let loadedModels = hotSlotManager.hotSlots.compactMap { $0.modelId }

        let total = loadedModels.reduce(0.0) { sum, modelId in
            return sum + (modelSizes[modelId] ?? 0.0)
        }

        totalMemoryUsed = total
    }

    // MARK: - Auto-refresh

    /// Start auto-refresh every N minutes
    func startAutoRefresh(intervalMinutes: Int = 5) {
        updateTask?.cancel()

        updateTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: UInt64(intervalMinutes) * 60 * 1_000_000_000)

                if !Task.isCancelled {
                    await self?.refresh()
                }
            }
        }
    }

    /// Stop auto-refresh
    func stopAutoRefresh() {
        updateTask?.cancel()
        updateTask = nil
    }
}

