//
//  ModelRecommendationService.swift
//  MagnetarStudio
//
//  Service for fetching curated model recommendations from backend
//

import Foundation

class ModelRecommendationService {
    static let shared = ModelRecommendationService()

    private let apiClient = ApiClient.shared

    init() {}

    // MARK: - Get Recommendations

    func getRecommendations(
        totalMemoryGB: Double,
        cpuCores: Int,
        hasMetal: Bool,
        installedModels: [String]
    ) async throws -> RecommendationsResponse {
        // Build query parameters
        var path = "/v1/models/recommendations?total_memory_gb=\(totalMemoryGB)&cpu_cores=\(cpuCores)&has_metal=\(hasMetal)"

        // Add installed models as comma-separated list
        if !installedModels.isEmpty {
            let modelsParam = installedModels.joined(separator: ",")
            path += "&installed_models=\(modelsParam)"
        }

        // Backend returns SuccessResponse<Dict> with data.recommendations
        struct RecommendationsData: Codable {
            let task: String
            let recommendations: [BackendRecommendedModel]
            let count: Int
        }

        // This endpoint uses new API standard with SuccessResponse envelope
        let data: RecommendationsData = try await apiClient.request(path, method: .get, unwrapEnvelope: true)

        return RecommendationsResponse(
            recommendations: data.recommendations,
            totalCount: data.count,
            filteredByHardware: true,
            learningEnabled: true,
            personalizationActive: false
        )
    }

    // MARK: - Health Check

    func checkHealth() async throws -> RecommendationHealthResponse {
        // Health endpoint doesn't use SuccessResponse envelope
        struct HealthResponse: Codable {
            let status: String
            let timestamp: String?
        }

        // Use the /health endpoint which returns plain JSON (no envelope)
        let healthResponse: HealthResponse = try await apiClient.request(
            "/health",
            method: .get,
            authenticated: false,
            unwrapEnvelope: false
        )

        return RecommendationHealthResponse(
            status: healthResponse.status == "ok" ? "healthy" : healthResponse.status,
            version: "1.0",
            lastUpdated: healthResponse.timestamp ?? "",
            totalModels: 0,
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
