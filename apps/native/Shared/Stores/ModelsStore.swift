//
//  ModelsStore.swift
//  MagnetarStudio
//
//  SPDX-License-Identifier: Proprietary
//

import Foundation
import Observation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "ModelsStore")

// MARK: - ModelsStore

/// Central state management for Ollama model lifecycle.
///
/// ## Overview
/// ModelsStore manages the local Ollama model registry - fetching available models,
/// pulling new models from Ollama Hub, and deleting models. Used by MagnetarHub
/// and model selection UI across the app.
///
/// ## Architecture
/// - **Thread Safety**: `@MainActor` isolated - all UI updates happen on main thread
/// - **Observation**: Uses `@Observable` macro for SwiftUI reactivity
/// - **Singleton**: Access via `ModelsStore.shared`
///
/// ## No State Persistence
/// Model list is fetched fresh from Ollama on demand.
/// No need to persist - source of truth is Ollama server.
/// Using singleton ensures consistent model list across all views.
///
/// ## Model Operations
/// - `fetchModels()` - Get list of locally installed models
/// - `pullModel()` - Download model from Ollama Hub (streaming progress)
/// - `deleteModel()` - Remove model from local storage
///
/// ## API Integration
/// - `/api/chat/models` - Backend wrapper for Ollama models list
/// - `/api/pull` - Direct to Ollama for model download (streaming)
/// - `/api/delete` - Direct to Ollama for model removal
///
/// ## Usage
/// ```swift
/// // Access the shared instance
/// let modelsStore = ModelsStore.shared
///
/// // Fetch available models
/// await modelsStore.fetchModels()
///
/// // Pull a new model
/// try await modelsStore.pullModel(name: "llama3.2:3b")
///
/// // Delete a model
/// try await modelsStore.deleteModel(name: "old-model:latest")
/// ```
@MainActor
@Observable
final class ModelsStore {
    static let shared = ModelsStore()

    var models: [OllamaModel] = []
    var isLoading: Bool = false
    var error: Error? = nil

    private let apiClient = ApiClient.shared

    private init() {}

    func fetchModels() async {
        isLoading = true
        error = nil

        do {
            // Fetch basic models list (no tags to avoid complexity)
            // SECURITY (CRIT-05): Use guard let instead of force unwrap
            guard let url = URL(string: APIConfiguration.shared.chatModelsURL) else {
                throw ApiError.invalidResponse
            }
            var request = URLRequest(url: url)
            request.httpMethod = "GET"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")

            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw ApiError.invalidResponse
            }

            if httpResponse.statusCode == 200 {
                let decoder = JSONDecoder()
                decoder.keyDecodingStrategy = .convertFromSnakeCase

                // API now returns SuccessResponse wrapper
                struct ModelsResponse: Codable, Sendable {
                    let success: Bool
                    let data: [OllamaModel]
                    let message: String?
                }

                let response = try decoder.decode(ModelsResponse.self, from: data)
                self.models = response.data
            } else {
                throw ApiError.httpError(httpResponse.statusCode, data)
            }
        } catch {
            self.error = error
            logger.error("Failed to fetch models: \(error)")
        }

        isLoading = false
    }

    @MainActor
    func pullModel(name: String) async throws {
        isLoading = true
        error = nil

        do {
            // Build URL to Ollama API (direct to Ollama, not through backend)
            guard let url = URL(string: "\(APIConfiguration.shared.ollamaURL)/api/pull") else {
                throw ApiError.invalidURL("\(APIConfiguration.shared.ollamaURL)/api/pull")
            }
            var request = URLRequest(url: url)
            request.httpMethod = "POST"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")

            let requestBody: [String: Any] = ["name": name]
            request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)

            // Stream the pull progress (Ollama returns JSON-delimited stream)
            let (bytes, response) = try await URLSession.shared.bytes(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw ApiError.invalidResponse
            }

            if httpResponse.statusCode != 200 {
                throw ApiError.httpError(httpResponse.statusCode, Data())
            }

            // Stream progress updates
            for try await line in bytes.lines {
                // Each line is a JSON object with status/progress
                if let jsonData = line.data(using: .utf8) {
                    do {
                        if let dict = try JSONSerialization.jsonObject(with: jsonData) as? [String: Any],
                           let status = dict["status"] as? String {
                            logger.debug("Pull \(name): \(status)")
                        }
                    } catch {
                        logger.debug("Pull \(name): malformed JSON chunk: \(error)")
                    }
                }
            }

            // Refresh models list after successful pull
            await fetchModels()

        } catch {
            self.error = error
            logger.error("Failed to pull model \(name): \(error)")
            throw error
        }

        isLoading = false
    }

    @MainActor
    func deleteModel(name: String) async throws {
        isLoading = true
        error = nil

        do {
            // Build URL to Ollama API (direct to Ollama, not through backend)
            guard let url = URL(string: "\(APIConfiguration.shared.ollamaURL)/api/delete") else {
                throw ApiError.invalidURL("\(APIConfiguration.shared.ollamaURL)/api/delete")
            }
            var request = URLRequest(url: url)
            request.httpMethod = "DELETE"
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")

            let requestBody: [String: Any] = ["name": name]
            request.httpBody = try JSONSerialization.data(withJSONObject: requestBody)

            let (data, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw ApiError.invalidResponse
            }

            if httpResponse.statusCode != 200 {
                throw ApiError.httpError(httpResponse.statusCode, data)
            }

            // Remove from local models array
            models.removeAll { $0.name == name }

            logger.info("Deleted model: \(name)")

        } catch {
            self.error = error
            logger.error("Failed to delete model \(name): \(error)")
            throw error
        }

        isLoading = false
    }
}

// MARK: - Ollama Model

struct OllamaModel: Codable, Identifiable, Sendable {
    let name: String
    let size: Int64
    let digest: String?
    let modifiedAt: String?
    let details: ModelDetails?

    var id: String { name }
    var sizeFormatted: String {
        let gb = Double(size) / 1_073_741_824.0
        return String(format: "%.1f GB", gb)
    }

    enum CodingKeys: String, CodingKey {
        case name, size, digest, details, modifiedAt = "modified_at"
    }

    // Custom decoder to handle optional modified_at gracefully
    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        name = try container.decode(String.self, forKey: .name)
        size = try container.decode(Int64.self, forKey: .size)
        digest = try container.decodeIfPresent(String.self, forKey: .digest)
        modifiedAt = try container.decodeIfPresent(String.self, forKey: .modifiedAt)
        details = try container.decodeIfPresent(ModelDetails.self, forKey: .details)
    }

    struct ModelDetails: Codable, Sendable {
        let format: String?
        let family: String?
        let parameterSize: String?
        let quantizationLevel: String?

        enum CodingKeys: String, CodingKey {
            case format, family
            case parameterSize = "parameter_size"
            case quantizationLevel = "quantization_level"
        }
    }
}

struct ModelTag: Codable, Identifiable, Sendable {
    let id: String
    let name: String
    let description: String
    let icon: String
}
