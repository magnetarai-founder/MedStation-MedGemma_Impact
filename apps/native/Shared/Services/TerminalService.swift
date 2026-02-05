//
//  TerminalService.swift
//  MagnetarStudio
//
//  Service for connecting to terminal API endpoints
//

import Foundation

// MARK: - Models

struct TerminalSessionsResponse: Codable, Sendable {
    let sessions: [TerminalSession]
    let count: Int
}

struct TerminalSession: Codable, Identifiable, Sendable {
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

    /// Spawn a new system terminal (Warp, iTerm2, or Terminal.app)
    func spawnTerminal(shell: String? = nil, cwd: String? = nil) async throws -> SpawnTerminalResponse {
        // Build request body with optional parameters
        var body: [String: String] = [:]
        if let shell = shell {
            body["shell"] = shell
        }
        if let cwd = cwd {
            body["cwd"] = cwd
        }

        // Use spawn-system endpoint which opens system Terminal/Warp/iTerm2
        return try await apiClient.request(
            path: "/v1/terminal/spawn-system",
            method: .post,
            jsonBody: body.isEmpty ? nil : body
        )
    }
}

// MARK: - Spawn Response

struct SpawnTerminalResponse: Codable, Sendable {
    let terminalId: String
    let terminalApp: String
    let workspaceRoot: String
    let activeCount: Int
    let message: String

    enum CodingKeys: String, CodingKey {
        case terminalId = "terminal_id"
        case terminalApp = "terminal_app"
        case workspaceRoot = "workspace_root"
        case activeCount = "active_count"
        case message
    }
}
