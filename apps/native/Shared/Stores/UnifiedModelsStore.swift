//
//  UnifiedModelsStore.swift
//  MagnetarStudio
//
//  SPDX-License-Identifier: Proprietary
//

import Foundation
import Observation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "UnifiedModelsStore")

// MARK: - UnifiedModelsStore

/// Unified model management across Ollama and HuggingFace/llama.cpp backends.
///
/// ## Overview
/// UnifiedModelsStore provides a single source of truth for all models available
/// in the system, combining models from Ollama and HuggingFace GGUF formats.
/// It tracks the active inference backend and handles model selection.
///
/// ## Architecture
/// - **Thread Safety**: `@MainActor` isolated - all UI updates happen on main thread
/// - **Observation**: Uses `@Observable` macro for SwiftUI reactivity
/// - **Singleton**: Access via `UnifiedModelsStore.shared`
///
/// ## Backend Management
/// - Tracks which backend is active (Ollama or llama.cpp)
/// - Manages model switching between backends
/// - Provides status for both Ollama and llama.cpp servers
///
/// ## Usage
/// ```swift
/// let store = UnifiedModelsStore.shared
/// await store.fetchAllModels()
/// try await store.selectModel(model)
/// ```
@MainActor
@Observable
final class UnifiedModelsStore {
    static let shared = UnifiedModelsStore()

    // MARK: - Published State

    /// All available models (Ollama + HuggingFace)
    var models: [UnifiedModel] = []

    /// Currently selected model
    var selectedModel: UnifiedModel?

    /// Active inference backend
    var activeBackend: ModelBackend = .ollama

    /// Backend status
    var ollamaRunning: Bool = false
    var llamacppRunning: Bool = false
    var llamacppLoadedModel: String?

    /// Loading states
    var isLoading: Bool = false
    var isDownloading: Bool = false
    var downloadProgress: Double = 0
    var downloadMessage: String = ""

    /// Error state
    var error: Error?

    // MARK: - Services

    private let huggingFaceService = HuggingFaceService.shared
    private let llamacppService = LlamaCppService.shared
    private let modelsStore = ModelsStore.shared

    private init() {}

    // MARK: - Model Fetching

    /// Fetch all models from all backends
    func fetchAllModels() async {
        isLoading = true
        error = nil
        models = []

        do {
            // Fetch from unified endpoint
            let response = try await fetchUnifiedModels()
            models = response.models
            ollamaRunning = response.ollamaRunning
            llamacppRunning = response.llamacppRunning
            llamacppLoadedModel = response.llamacppModel

            // Determine active backend based on what's running
            if llamacppRunning && llamacppLoadedModel != nil {
                activeBackend = .llamacpp
            } else if ollamaRunning {
                activeBackend = .ollama
            }

            logger.info("Fetched \(self.models.count) models (Ollama: \(response.ollamaCount), HF: \(response.huggingfaceCount))")

        } catch {
            self.error = error
            logger.error("Failed to fetch models: \(error)")
        }

        isLoading = false
    }

    private func fetchUnifiedModels() async throws -> UnifiedModelsResponse {
        guard let url = URL(string: "\(APIConfiguration.shared.baseURL)/v1/chat/models/unified") else {
            throw UnifiedModelError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw UnifiedModelError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw UnifiedModelError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let envelope = try decoder.decode(SuccessEnvelope<UnifiedModelsResponse>.self, from: data)
        return envelope.data
    }

    // MARK: - Backend Status

    /// Refresh backend status only (without fetching models)
    func refreshBackendStatus() async {
        do {
            let llamacppStatus = try await llamacppService.getStatus()
            llamacppRunning = llamacppStatus.running && llamacppStatus.healthOk
            llamacppLoadedModel = llamacppStatus.modelLoaded
        } catch {
            llamacppRunning = false
            llamacppLoadedModel = nil
        }

        // Ollama status from ModelsStore (it already caches this)
        ollamaRunning = !modelsStore.models.isEmpty || modelsStore.error == nil
    }

    // MARK: - Model Selection

    /// Select a model and switch backend if needed
    func selectModel(_ model: UnifiedModel) async throws {
        selectedModel = model

        switch model.source {
        case "ollama":
            // Ollama models are ready to use immediately
            activeBackend = .ollama
            logger.info("Selected Ollama model: \(model.name)")

        case "huggingface":
            // HuggingFace models need llama.cpp
            if !model.isDownloaded {
                throw UnifiedModelError.modelNotDownloaded
            }

            // Extract model ID from unified ID (format: "hf:model-id")
            let modelId = String(model.id.dropFirst(3))  // Remove "hf:" prefix

            // Start llama.cpp server with this model
            isLoading = true
            defer { isLoading = false }

            let status = try await llamacppService.startServer(modelId: modelId)

            if status.running && status.healthOk {
                activeBackend = .llamacpp
                llamacppRunning = true
                llamacppLoadedModel = status.modelLoaded
                logger.info("Started llama.cpp with: \(model.name)")
            } else {
                throw UnifiedModelError.serverStartFailed(status.error ?? "Unknown error")
            }

        default:
            throw UnifiedModelError.unknownSource
        }
    }

    // MARK: - Download Management

    /// Download a HuggingFace model
    func downloadModel(_ model: UnifiedModel) async throws {
        guard model.source == "huggingface" else {
            throw UnifiedModelError.invalidOperation
        }

        // Extract model ID
        let modelId = String(model.id.dropFirst(3))

        isDownloading = true
        downloadProgress = 0
        downloadMessage = "Starting download..."
        error = nil

        defer {
            isDownloading = false
            downloadProgress = 0
            downloadMessage = ""
        }

        do {
            for try await progress in huggingFaceService.downloadModel(modelId: modelId) {
                downloadProgress = progress.progress
                downloadMessage = progress.message

                if progress.status == "downloading" {
                    downloadMessage = "\(progress.speedFormatted) • \(progress.etaFormatted) remaining"
                }

                if progress.status == "completed" {
                    // Refresh models to update download status
                    await fetchAllModels()
                    logger.info("Download completed: \(modelId)")
                    return
                }

                if progress.status == "failed" {
                    throw UnifiedModelError.downloadFailed(progress.error ?? progress.message)
                }
            }
        } catch {
            self.error = error
            throw error
        }
    }

    /// Delete a downloaded model
    func deleteModel(_ model: UnifiedModel) async throws {
        switch model.source {
        case "ollama":
            try await modelsStore.deleteModel(name: model.ollamaName ?? model.name)
            await fetchAllModels()

        case "huggingface":
            let modelId = String(model.id.dropFirst(3))
            try await huggingFaceService.deleteModel(modelId: modelId)
            await fetchAllModels()

        default:
            throw UnifiedModelError.unknownSource
        }
    }

    // MARK: - Filtering

    /// Filter models by source
    func models(for source: ModelBackend) -> [UnifiedModel] {
        switch source {
        case .ollama:
            return models.filter { $0.source == "ollama" }
        case .llamacpp:
            return models.filter { $0.source == "huggingface" }
        }
    }

    /// Filter models by capability
    func models(with capability: String) -> [UnifiedModel] {
        models.filter { $0.capabilities.contains(capability) }
    }

    /// Get downloaded models only
    var downloadedModels: [UnifiedModel] {
        models.filter { $0.isDownloaded }
    }

    /// Get medical models
    var medicalModels: [UnifiedModel] {
        models(with: "medical")
    }
}

// MARK: - Supporting Types

enum ModelBackend: String, CaseIterable, Identifiable {
    case ollama
    case llamacpp

    var id: String { rawValue }

    var displayName: String {
        switch self {
        case .ollama:
            return "Ollama"
        case .llamacpp:
            return "llama.cpp"
        }
    }

    var icon: String {
        switch self {
        case .ollama:
            return "llama"  // Custom asset or SF Symbol
        case .llamacpp:
            return "cpu"
        }
    }
}

/// Unified model representation
struct UnifiedModel: Codable, Identifiable, Hashable, Sendable {
    let id: String
    let name: String
    let source: String  // "ollama" or "huggingface"
    let sizeBytes: Int?
    let sizeFormatted: String
    let quantization: String?
    let parameterCount: String?
    let isDownloaded: Bool
    let isRunning: Bool
    let capabilities: [String]
    let contextLength: Int?
    let description: String?

    // Source-specific
    let ollamaName: String?
    let repoId: String?
    let filename: String?

    // Hardware info
    let minVramGb: Double?
    let recommendedVramGb: Double?

    // Hashable conformance
    func hash(into hasher: inout Hasher) {
        hasher.combine(id)
    }

    static func == (lhs: UnifiedModel, rhs: UnifiedModel) -> Bool {
        lhs.id == rhs.id
    }
}

/// Response from unified models endpoint
private struct UnifiedModelsResponse: Codable, Sendable {
    let models: [UnifiedModel]
    let ollamaCount: Int
    let huggingfaceCount: Int
    let totalCount: Int
    let ollamaRunning: Bool
    let llamacppRunning: Bool
    let llamacppModel: String?
}

/// Generic success envelope
private struct SuccessEnvelope<T: Decodable & Sendable>: Decodable, Sendable {
    let success: Bool
    let data: T
    let message: String?
}

// MARK: - Errors

enum UnifiedModelError: LocalizedError {
    case invalidURL
    case invalidResponse
    case httpError(Int)
    case modelNotDownloaded
    case serverStartFailed(String)
    case downloadFailed(String)
    case unknownSource
    case invalidOperation

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let code):
            return "HTTP error: \(code)"
        case .modelNotDownloaded:
            return "Model must be downloaded first"
        case .serverStartFailed(let message):
            return "Failed to start inference server: \(message)"
        case .downloadFailed(let message):
            return "Download failed: \(message)"
        case .unknownSource:
            return "Unknown model source"
        case .invalidOperation:
            return "Invalid operation for this model type"
        }
    }
}
