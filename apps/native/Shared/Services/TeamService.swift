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
    let content: AnyCodable?
    let type: String
    let createdAt: String
    let updatedAt: String
    let createdBy: String
    let isPrivate: Bool
    let securityLevel: String?
    let sharedWith: [String]
    let teamId: String?

    enum CodingKeys: String, CodingKey {
        case id, title, content, type
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case createdBy = "created_by"
        case isPrivate = "is_private"
        case securityLevel = "security_level"
        case sharedWith = "shared_with"
        case teamId = "team_id"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        title = try container.decode(String.self, forKey: .title)
        content = try? container.decode(AnyCodable.self, forKey: .content)
        type = try container.decode(String.self, forKey: .type)
        createdAt = try container.decode(String.self, forKey: .createdAt)
        updatedAt = try container.decode(String.self, forKey: .updatedAt)
        createdBy = try container.decode(String.self, forKey: .createdBy)
        isPrivate = try container.decode(Bool.self, forKey: .isPrivate)
        securityLevel = try? container.decode(String.self, forKey: .securityLevel)
        sharedWith = (try? container.decode([String].self, forKey: .sharedWith)) ?? []
        teamId = try? container.decode(String.self, forKey: .teamId)
    }
}

// Helper to decode Any type from JSON
struct AnyCodable: Codable {
    let value: Any

    init(_ value: Any) {
        self.value = value
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()

        if let string = try? container.decode(String.self) {
            value = string
        } else if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else if let bool = try? container.decode(Bool.self) {
            value = bool
        } else if let array = try? container.decode([AnyCodable].self) {
            value = array.map { $0.value }
        } else if let dict = try? container.decode([String: AnyCodable].self) {
            value = dict.mapValues { $0.value }
        } else {
            value = NSNull()
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.singleValueContainer()

        switch value {
        case let string as String:
            try container.encode(string)
        case let int as Int:
            try container.encode(int)
        case let double as Double:
            try container.encode(double)
        case let bool as Bool:
            try container.encode(bool)
        case let array as [Any]:
            try container.encode(array.map { AnyCodable($0) })
        case let dict as [String: Any]:
            try container.encode(dict.mapValues { AnyCodable($0) })
        default:
            try container.encodeNil()
        }
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

public final class TeamService {
    public static let shared = TeamService()
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
        do {
            let documents: [TeamDocument] = try await apiClient.request(
                path: "/v1/docs/documents",
                method: .get
            )
            print("✅ Successfully loaded \(documents.count) documents")
            return documents
        } catch {
            print("❌ Failed to load documents: \(error)")
            if let decodingError = error as? DecodingError {
                print("Decoding error details: \(decodingError)")
            }
            throw error
        }
    }

    func createDocument(title: String, content: String, type: String) async throws -> TeamDocument {
        try await apiClient.request(
            path: "/v1/docs/documents",
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
            path: "/v1/docs/documents/\(id)",
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

    // MARK: - Messages

    public func sendMessage(channelId: String, content: String) async throws -> TeamMessage {
        try await apiClient.request(
            path: "/v1/team/channels/\(channelId)/messages",
            method: .post,
            jsonBody: [
                "channel_id": channelId,
                "content": content,
                "type": "text"
            ]
        )
    }

    public func getMessages(channelId: String, limit: Int = 50) async throws -> MessageListResponse {
        try await apiClient.request(
            path: "/v1/team/channels/\(channelId)/messages?limit=\(limit)",
            method: .get
        )
    }
}

// MARK: - Message Models

public struct TeamMessage: Identifiable, Codable {
    public let id: String
    public let channelId: String
    public let senderId: String
    public let senderName: String
    public let type: String
    public let content: String
    public let timestamp: String
    public let encrypted: Bool
    public let fileMetadata: AnyCodable?
    public let threadId: String?
    public let replyTo: String?
    public let editedAt: String?

    public init(id: String, channelId: String, senderId: String, senderName: String, type: String, content: String, timestamp: String, encrypted: Bool, fileMetadata: AnyCodable?, threadId: String?, replyTo: String?, editedAt: String?) {
        self.id = id
        self.channelId = channelId
        self.senderId = senderId
        self.senderName = senderName
        self.type = type
        self.content = content
        self.timestamp = timestamp
        self.encrypted = encrypted
        self.fileMetadata = fileMetadata
        self.threadId = threadId
        self.replyTo = replyTo
        self.editedAt = editedAt
    }

    public enum CodingKeys: String, CodingKey {
        case id
        case channelId = "channel_id"
        case senderId = "sender_id"
        case senderName = "sender_name"
        case type, content, timestamp, encrypted
        case fileMetadata = "file_metadata"
        case threadId = "thread_id"
        case replyTo = "reply_to"
        case editedAt = "edited_at"
    }
}

public struct MessageListResponse: Codable {
    public let channelId: String
    public let messages: [TeamMessage]
    public let total: Int
    public let hasMore: Bool

    public enum CodingKeys: String, CodingKey {
        case channelId = "channel_id"
        case messages, total
        case hasMore = "has_more"
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
