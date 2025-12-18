//
//  ModelRecommendationService.swift
//  MagnetarStudio
//
//  Service for fetching curated model recommendations from backend
//

import Foundation

class ModelRecommendationService {
    static let shared = ModelRecommendationService()

    private let baseURL: String
    private let session = URLSession.shared

    init() {
        self.baseURL = UserDefaults.standard.string(forKey: "apiBaseURL") ?? "http://localhost:8000"
    }

    // MARK: - Get Recommendations

    func getRecommendations(
        totalMemoryGB: Double,
        cpuCores: Int,
        hasMetal: Bool,
        installedModels: [String]
    ) async throws -> RecommendationsResponse {
        // Build query parameters
        var components = URLComponents(string: "\(baseURL)/api/v1/models/recommended")!

        components.queryItems = [
            URLQueryItem(name: "total_memory_gb", value: String(totalMemoryGB)),
            URLQueryItem(name: "cpu_cores", value: String(cpuCores)),
            URLQueryItem(name: "has_metal", value: String(hasMetal)),
        ]

        // Add installed models as comma-separated list
        if !installedModels.isEmpty {
            components.queryItems?.append(
                URLQueryItem(name: "installed_models", value: installedModels.joined(separator: ","))
            )
        }

        guard let url = components.url else {
            throw RecommendationError.invalidURL
        }

        var request = URLRequest(url: url)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        // Add auth token
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw RecommendationError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw RecommendationError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(RecommendationsResponse.self, from: data)
    }

    // MARK: - Health Check

    func checkHealth() async throws -> RecommendationHealthResponse {
        // Use main health endpoint instead of non-existent recommendations health
        let url = URL(string: "\(baseURL)/health")!
        var request = URLRequest(url: url)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        let (data, response) = try await session.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw RecommendationError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw RecommendationError.httpError(httpResponse.statusCode)
        }

        // Health endpoint returns {"status": "ok", "timestamp": "..."}
        // Map it to RecommendationHealthResponse
        struct HealthResponse: Codable {
            let status: String
            let timestamp: String?
        }

        let healthResponse = try JSONDecoder().decode(HealthResponse.self, from: data)

        // Return a RecommendationHealthResponse with health status
        return RecommendationHealthResponse(
            status: healthResponse.status == "ok" ? "healthy" : healthResponse.status,
            version: "1.0",
            lastUpdated: healthResponse.timestamp ?? "",
            totalModels: 0,  // Not available from health endpoint
            learningEnabled: true
        )
    }
}

// MARK: - Models

struct RecommendationsResponse: Codable {
    let recommendations: [BackendRecommendedModel]
    let totalCount: Int
    let filteredByHardware: Bool
    let learningEnabled: Bool
    let personalizationActive: Bool
}

struct BackendRecommendedModel: Codable, Identifiable {
    let modelName: String
    let displayName: String
    let description: String
    let tags: [String]
    let parameterSize: String
    let estimatedMemoryGb: Double
    let compatibility: ModelCompatibilityInfo
    let badges: [String]
    let isInstalled: Bool
    let isMultiPurpose: Bool
    let primaryUseCases: [String]
    let popularityRank: Int
    let capability: String

    var id: String { modelName }
}

struct ModelCompatibilityInfo: Codable {
    let performance: String  // "excellent", "good", "fair", "insufficient"
    let reason: String
    let estimatedMemoryUsage: Double?
}

struct RecommendationHealthResponse: Codable {
    let status: String
    let version: String
    let lastUpdated: String
    let totalModels: Int
    let learningEnabled: Bool
}

// MARK: - Errors

enum RecommendationError: LocalizedError {
    case invalidURL
    case invalidResponse
    case httpError(Int)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid recommendation URL"
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let code):
            return "HTTP error: \(code)"
        }
    }
}
