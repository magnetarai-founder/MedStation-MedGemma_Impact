//
//  DataLabService.swift
//  MagnetarStudio
//
//  Service for Data Lab AI-powered analysis endpoints.
//  Extracted from TeamService (MEDIUM-H2) - these are /v1/data/* endpoints,
//  semantically separate from team operations.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "DataLabService")

// MARK: - Models

public struct NLQueryResponse: Codable, Sendable {
    public let answer: String
    public let query: String
    public let confidence: Double?
    public let sources: [String]?
}

public struct PatternDiscoveryResult: Codable, Sendable {
    public let patterns: [Pattern]
    public let summary: String?

    public struct Pattern: Codable, Identifiable, Sendable {
        public let id: String
        public let type: String
        public let description: String
        public let confidence: Double
        public let examples: [String]?
    }
}

// MARK: - DataLabService

public final class DataLabService {
    public static let shared = DataLabService()
    private let apiClient = ApiClient.shared

    private init() {}

    // MARK: - Natural Language Query

    /// Ask a natural language question about the data
    public func askNaturalLanguage(query: String) async throws -> NLQueryResponse {
        logger.debug("Asking NL query: \(query)")
        return try await apiClient.request(
            path: "/v1/data/ask",
            method: .post,
            jsonBody: ["query": query]
        )
    }

    // MARK: - Pattern Discovery

    /// Discover patterns in the data
    public func discoverPatterns(query: String, context: String?) async throws -> PatternDiscoveryResult {
        logger.debug("Discovering patterns for: \(query)")
        var body: [String: Any] = ["query": query]
        if let context = context { body["context"] = context }

        return try await apiClient.request(
            path: "/v1/data/patterns",
            method: .post,
            jsonBody: body
        )
    }
}
