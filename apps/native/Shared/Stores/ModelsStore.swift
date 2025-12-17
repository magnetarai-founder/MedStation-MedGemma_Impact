//
//  ModelsStore.swift
//  MagnetarStudio
//
//  Manages Ollama models - fetching, pulling, deleting.
//

import Foundation
import Observation

@MainActor
@Observable
final class ModelsStore {
    var models: [OllamaModel] = []
    var isLoading: Bool = false
    var error: Error? = nil

    private let apiClient = ApiClient.shared

    init() {}

    func fetchModels() async {
        isLoading = true
        error = nil

        do {
            // Fetch basic models list (no tags to avoid complexity)
            let url = URL(string: "http://localhost:8000/api/v1/chat/models")!
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
                struct ModelsResponse: Codable {
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
            print("Failed to fetch models: \(error)")
        }

        isLoading = false
    }

    @MainActor
    func pullModel(name: String) async throws {
        isLoading = true
        error = nil

        do {
            // Build URL to Ollama API (direct to Ollama, not through backend)
            let url = URL(string: "http://localhost:11434/api/pull")!
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
                if let jsonData = line.data(using: .utf8),
                   let dict = try? JSONSerialization.jsonObject(with: jsonData) as? [String: Any] {
                    if let status = dict["status"] as? String {
                        print("Pull \(name): \(status)")
                    }
                }
            }

            // Refresh models list after successful pull
            await fetchModels()

        } catch {
            self.error = error
            print("Failed to pull model \(name): \(error)")
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
            let url = URL(string: "http://localhost:11434/api/delete")!
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

            print("Deleted model: \(name)")

        } catch {
            self.error = error
            print("Failed to delete model \(name): \(error)")
            throw error
        }

        isLoading = false
    }
}

// MARK: - Ollama Model

struct OllamaModel: Codable, Identifiable {
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
        case name, size, digest, details
        case modifiedAt = "modified_at"
    }

    struct ModelDetails: Codable {
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

struct ModelTag: Codable, Identifiable {
    let id: String
    let name: String
    let description: String
    let icon: String
}
