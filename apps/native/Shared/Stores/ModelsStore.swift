//
//  ModelsStore.swift
//  MagnetarStudio
//
//  Manages Ollama models - fetching, pulling, deleting.
//

import Foundation
import Observation

@Observable
final class ModelsStore {
    var models: [OllamaModel] = []
    var isLoading: Bool = false
    var error: Error? = nil

    private let apiClient = ApiClient.shared

    init() {}

    @MainActor
    func fetchModels() async {
        isLoading = true
        error = nil

        do {
            // Build URL to fetch models with auto-detected tags
            let url = URL(string: "http://localhost:8000/api/v1/chat/models/with-tags")!
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
                let fetchedModels = try decoder.decode([OllamaModel].self, from: data)
                self.models = fetchedModels
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
        // TODO: Implement model pulling
        print("Pull model: \(name)")
    }

    @MainActor
    func deleteModel(name: String) async throws {
        // TODO: Implement model deletion
        print("Delete model: \(name)")
    }
}

// MARK: - Ollama Model

struct OllamaModel: Codable, Identifiable {
    let name: String
    let size: String  // Already formatted by backend (e.g., "4.4GB")
    let digest: String?
    let modifiedAt: String
    let tags: [String]?
    let tagDetails: [ModelTag]?

    var id: String { name }

    enum CodingKeys: String, CodingKey {
        case name
        case size
        case digest
        case modifiedAt = "modified_at"
        case tags
        case tagDetails = "tag_details"
    }
}

struct ModelTag: Codable, Identifiable {
    let id: String
    let name: String
    let description: String
    let icon: String
}
