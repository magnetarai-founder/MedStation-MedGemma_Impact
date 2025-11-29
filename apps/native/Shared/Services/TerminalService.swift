//
//  TerminalService.swift
//  MagnetarStudio
//
//  Service for connecting to terminal API endpoints
//

import Foundation

// MARK: - Models

struct TerminalSessionsResponse: Codable {
    let sessions: [TerminalSession]
    let count: Int
}

struct TerminalSession: Codable, Identifiable {
    let id: String
    let active: Bool
    let createdAt: String
    let pid: Int?

    enum CodingKeys: String, CodingKey {
        case id
        case active
        case createdAt = "created_at"
        case pid
    }
}

// MARK: - Service

@MainActor
class TerminalService {
    static let shared = TerminalService()
    private let apiClient = ApiClient.shared

    private init() {}

    /// Get list of terminal sessions for current user
    func listSessions() async throws -> TerminalSessionsResponse {
        try await apiClient.request(
            "/v1/terminal/sessions",
            method: .get
        )
    }
}
