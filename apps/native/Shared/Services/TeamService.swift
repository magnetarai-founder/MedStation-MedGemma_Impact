//
//  TeamService.swift
//  MagnetarStudio
//
//  Service layer for Team workspace endpoints
//

import Foundation

// MARK: - Models

struct Team: Identifiable, Codable {
    let id: String
    let name: String
    let description: String?
    let createdAt: String
    let memberCount: Int?

    enum CodingKeys: String, CodingKey {
        case id, name, description
        case createdAt = "created_at"
        case memberCount = "member_count"
    }
}

struct TeamDocument: Identifiable, Codable {
    let id: String
    let title: String
    let content: String?
    let type: String
    let updatedAt: String
    let createdBy: String?

    enum CodingKeys: String, CodingKey {
        case id, title, content, type
        case updatedAt = "updated_at"
        case createdBy = "created_by"
    }
}

struct DiagnosticsStatus: Codable {
    let status: String
    let network: NetworkStatus
    let database: DatabaseStatus
    let services: [ServiceStatus]

    struct NetworkStatus: Codable {
        let connected: Bool
        let latency: Int?
        let bandwidth: String?
    }

    struct DatabaseStatus: Codable {
        let connected: Bool
        let queryTime: Int?

        enum CodingKeys: String, CodingKey {
            case connected
            case queryTime = "query_time"
        }
    }

    struct ServiceStatus: Codable {
        let name: String
        let status: String
        let uptime: String?
    }
}

struct NLQueryResponse: Codable {
    let answer: String
    let query: String
    let confidence: Double?
    let sources: [String]?
}

struct PatternDiscoveryResult: Codable {
    let patterns: [Pattern]
    let summary: String?

    struct Pattern: Codable, Identifiable {
        let id: String
        let type: String
        let description: String
        let confidence: Double
        let examples: [String]?
    }
}

// MARK: - Team Service

final class TeamService {
    static let shared = TeamService()
    private let apiClient = ApiClient.shared

    private init() {}

    // MARK: - Teams

    func createTeam(name: String, description: String?) async throws -> Team {
        try await apiClient.request(
            path: "/v1/teams",
            method: .post,
            jsonBody: [
                "name": name,
                "description": description ?? ""
            ]
        )
    }

    func joinTeam(code: String) async throws -> Team {
        try await apiClient.request(
            path: "/v1/teams/join",
            method: .post,
            jsonBody: ["code": code]
        )
    }

    func listTeams() async throws -> [Team] {
        try await apiClient.request(
            path: "/v1/teams",
            method: .get
        )
    }

    // MARK: - Documents

    func listDocuments() async throws -> [TeamDocument] {
        try await apiClient.request(
            path: "/v1/docs",
            method: .get
        )
    }

    func createDocument(title: String, content: String, type: String) async throws -> TeamDocument {
        try await apiClient.request(
            path: "/v1/docs",
            method: .post,
            jsonBody: [
                "title": title,
                "content": content,
                "type": type
            ]
        )
    }

    func updateDocument(id: String, title: String?, content: String?) async throws -> TeamDocument {
        var body: [String: Any] = [:]
        if let title = title { body["title"] = title }
        if let content = content { body["content"] = content }

        return try await apiClient.request(
            path: "/v1/docs/\(id)",
            method: .put,
            jsonBody: body
        )
    }

    // MARK: - Diagnostics

    func getDiagnostics() async throws -> DiagnosticsStatus {
        try await apiClient.request(
            path: "/v1/diagnostics",
            method: .get
        )
    }

    // MARK: - NL Query

    func askNaturalLanguage(query: String) async throws -> NLQueryResponse {
        try await apiClient.request(
            path: "/v1/data/ask",
            method: .post,
            jsonBody: ["query": query]
        )
    }

    // MARK: - Pattern Discovery

    func discoverPatterns(query: String, context: String?) async throws -> PatternDiscoveryResult {
        var body: [String: Any] = ["query": query]
        if let context = context { body["context"] = context }

        return try await apiClient.request(
            path: "/v1/data/patterns",
            method: .post,
            jsonBody: body
        )
    }

    // MARK: - Vault Setup

    func setupVault(password: String) async throws -> VaultSetupResponse {
        try await apiClient.request(
            path: "/v1/vault/setup",
            method: .post,
            jsonBody: ["password": password]
        )
    }

    func getVaultStatus() async throws -> VaultStatusResponse {
        try await apiClient.request(
            path: "/v1/vault/status",
            method: .get
        )
    }
}

// MARK: - Vault Models

struct VaultSetupResponse: Codable {
    let status: String
    let message: String
    let vaultId: String?

    enum CodingKeys: String, CodingKey {
        case status, message
        case vaultId = "vault_id"
    }
}

struct VaultStatusResponse: Codable {
    let initialized: Bool
    let locked: Bool
    let message: String?
}
