//
//  ModelTagService.swift
//  MagnetarStudio
//
//  Service for managing model tags (auto-detected + manual overrides)
//

import Foundation

class ModelTagService {
    static let shared = ModelTagService()

    private let baseURL: String
    private let session = URLSession.shared

    init() {
        self.baseURL = UserDefaults.standard.string(forKey: "apiBaseURL") ?? "http://localhost:8000"
    }

    // MARK: - Get Available Tags

    func getAvailableTags() async throws -> [ModelTag] {
        let url = URL(string: "\(baseURL)/api/v1/chat/tags/available")!
        var request = URLRequest(url: url)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Add auth token
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw TagServiceError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw TagServiceError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode([ModelTag].self, from: data)
    }

    // MARK: - Get Model Tags

    func getModelTags(modelName: String) async throws -> ModelTagsResponse {
        // URL encode model name
        guard let encodedName = modelName.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) else {
            throw TagServiceError.invalidModelName
        }

        let url = URL(string: "\(baseURL)/api/v1/chat/models/\(encodedName)/tags")!
        var request = URLRequest(url: url)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Add auth token
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw TagServiceError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw TagServiceError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(ModelTagsResponse.self, from: data)
    }

    // MARK: - Update Model Tags

    func updateModelTags(modelName: String, tags: [String]) async throws -> ModelTagsResponse {
        // URL encode model name
        guard let encodedName = modelName.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) else {
            throw TagServiceError.invalidModelName
        }

        let url = URL(string: "\(baseURL)/api/v1/chat/models/\(encodedName)/tags")!
        var request = URLRequest(url: url)
        request.httpMethod = "PUT"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Add auth token
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        // Encode request body
        let requestBody = UpdateTagsRequest(tags: tags)
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        request.httpBody = try encoder.encode(requestBody)

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw TagServiceError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw TagServiceError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(ModelTagsResponse.self, from: data)
    }

    // MARK: - Delete Tag Overrides (Revert to Auto)

    func deleteTagOverrides(modelName: String) async throws -> ModelTagsResponse {
        // URL encode model name
        guard let encodedName = modelName.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed) else {
            throw TagServiceError.invalidModelName
        }

        let url = URL(string: "\(baseURL)/api/v1/chat/models/\(encodedName)/tags")!
        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Add auth token
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw TagServiceError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw TagServiceError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(ModelTagsResponse.self, from: data)
    }
}

// MARK: - Errors

enum TagServiceError: LocalizedError {
    case invalidResponse
    case httpError(Int)
    case invalidModelName

    var errorDescription: String? {
        switch self {
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let code):
            return "HTTP error: \(code)"
        case .invalidModelName:
            return "Invalid model name"
        }
    }
}
