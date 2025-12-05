//
//  ModelLibraryService.swift
//  MagnetarStudio
//
//  Service for browsing and discovering models from Ollama library
//

import Foundation

class ModelLibraryService {
    static let shared = ModelLibraryService()

    private let baseURL: String
    private let session = URLSession.shared

    init() {
        self.baseURL = UserDefaults.standard.string(forKey: "apiBaseURL") ?? "http://localhost:8000"
    }

    // MARK: - Browse Library

    func browseLibrary(
        search: String? = nil,
        modelType: String? = nil,
        capability: String? = nil,
        sortBy: String = "pulls",
        order: String = "desc",
        limit: Int = 20,
        skip: Int = 0
    ) async throws -> LibraryResponse {
        var urlComponents = URLComponents(string: "\(baseURL)/api/v1/chat/models/library")!

        var queryItems: [URLQueryItem] = [
            URLQueryItem(name: "sort_by", value: sortBy),
            URLQueryItem(name: "order", value: order),
            URLQueryItem(name: "limit", value: "\(limit)"),
            URLQueryItem(name: "skip", value: "\(skip)")
        ]

        if let search = search, !search.isEmpty {
            queryItems.append(URLQueryItem(name: "search", value: search))
        }
        if let modelType = modelType {
            queryItems.append(URLQueryItem(name: "model_type", value: modelType))
        }
        if let capability = capability {
            queryItems.append(URLQueryItem(name: "capability", value: capability))
        }

        urlComponents.queryItems = queryItems

        guard let url = urlComponents.url else {
            throw ModelLibraryError.invalidURL
        }

        let (data, response) = try await session.data(from: url)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw ModelLibraryError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw ModelLibraryError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(LibraryResponse.self, from: data)
    }
}

// MARK: - Models

struct LibraryResponse: Codable {
    let models: [LibraryModel]
    let totalCount: Int
    let limit: Int
    let skip: Int
    let dataUpdated: String?
}

struct LibraryModel: Codable, Identifiable {
    let modelIdentifier: String
    let modelName: String
    let modelType: String  // "official" or "community"
    let description: String?
    let capability: String?
    let labels: [String]?  // Parameter sizes like ["3B", "7B"]
    let pulls: Int
    let tags: [String]
    let lastUpdated: String
    let url: String

    var id: String { modelIdentifier }

    var isOfficial: Bool {
        modelType == "official"
    }

    var pullsFormatted: String {
        if pulls >= 1_000_000 {
            return String(format: "%.1fM", Double(pulls) / 1_000_000.0)
        } else if pulls >= 1_000 {
            return String(format: "%.1fK", Double(pulls) / 1_000.0)
        } else {
            return "\(pulls)"
        }
    }

    var labelsText: String {
        labels?.joined(separator: ", ") ?? ""
    }
}

// MARK: - Errors

enum ModelLibraryError: LocalizedError {
    case invalidURL
    case invalidResponse
    case httpError(Int)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let code):
            return "HTTP error: \(code)"
        }
    }
}
