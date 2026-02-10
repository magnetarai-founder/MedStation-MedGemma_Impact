//
//  ModelMemoryTracker.swift
//  MedStation
//
//  Tracks memory usage of loaded Ollama models.
//

import Foundation
import Observation
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "ModelMemoryTracker")

@MainActor
@Observable
final class ModelMemoryTracker {
    static let shared = ModelMemoryTracker()

    private var memoryMap: [String: Float] = [:]

    private init() {}

    /// Get memory usage in GB for a specific model
    func getMemoryUsage(for modelId: String) -> Float? {
        memoryMap[modelId]
    }

    /// Update memory usage for a model
    func updateMemoryUsage(for modelId: String, gb: Float) {
        memoryMap[modelId] = gb
    }

    /// Start auto-refreshing memory data on a timer
    func startAutoRefresh(intervalMinutes: Int) {
        let interval = TimeInterval(intervalMinutes * 60)
        Task {
            while !Task.isCancelled {
                try? await Task.sleep(nanoseconds: UInt64(interval * 1_000_000_000))
                await refresh()
            }
        }
    }

    /// Refresh memory data from Ollama
    func refresh() async {
        do {
            let ollamaURL = APIConfiguration.shared.ollamaURL
            guard let url = URL(string: "\(ollamaURL)/api/ps") else { return }
            let (data, _) = try await URLSession.shared.data(from: url)

            struct RunningModel: Codable {
                let name: String
                let size: Int64?
            }
            struct PSResponse: Codable {
                let models: [RunningModel]
            }

            let response = try JSONDecoder().decode(PSResponse.self, from: data)
            for model in response.models {
                let gb = Float(model.size ?? 0) / 1_073_741_824
                memoryMap[model.name] = gb
            }
        } catch {
            logger.warning("Failed to refresh model memory: \(error.localizedDescription)")
        }
    }
}
