//
//  TeamService.swift
//  MagnetarStudio
//
//  Service layer for Team workspace endpoints
//

import Foundation

// MARK: - Models

// MARK: - API Response Wrappers

/// Delete response format from backend: { status: "deleted", id: "..." }
private struct DocumentDeleteResponse: Decodable {
    let status: String
    let id: String
}

public struct Team: Identifiable, Codable {
    public let id: String
    public let name: String
    public let description: String?
    public let createdAt: String
    public let memberCount: Int?

    public enum CodingKeys: String, CodingKey {
        case id, name, description
        case createdAt = "created_at"
        case memberCount = "member_count"
    }
}

public struct TeamDocument: Identifiable, Codable {
    public let id: String
    public let title: String
    public let content: AnyCodable?
    public let type: String
    public let createdAt: String
    public let updatedAt: String
    public let createdBy: String
    public let isPrivate: Bool
    public let securityLevel: String?
    public let sharedWith: [String]
    public let teamId: String?

    public init(id: String, title: String, content: AnyCodable? = nil, type: String, createdAt: String, updatedAt: String, createdBy: String, isPrivate: Bool, securityLevel: String? = nil, sharedWith: [String], teamId: String? = nil) {
        self.id = id
        self.title = title
        self.content = content
        self.type = type
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.createdBy = createdBy
        self.isPrivate = isPrivate
        self.securityLevel = securityLevel
        self.sharedWith = sharedWith
        self.teamId = teamId
    }

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

    public init(from decoder: Decoder) throws {
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

/// Matches the backend /api/v1/diagnostics response structure
public struct DiagnosticsStatus: Codable {
    public let system: SystemStatus
    public let metal: MetalStatus
    public let ollama: OllamaStatus
    public let p2p: P2PStatus
    public let database: DatabaseStatus
    public let timestamp: Double?
    public let partial: Bool?

    public struct SystemStatus: Codable {
        public let os: String?
        public let cpuPercent: Double?
        public let ram: RAMStatus?
        public let disk: DiskStatus?

        public enum CodingKeys: String, CodingKey {
            case os
            case cpuPercent = "cpu_percent"
            case ram, disk
        }

        public struct RAMStatus: Codable {
            public let totalGb: Double?
            public let usedGb: Double?

            public enum CodingKeys: String, CodingKey {
                case totalGb = "total_gb"
                case usedGb = "used_gb"
            }
        }

        public struct DiskStatus: Codable {
            public let totalGb: Double?
            public let usedGb: Double?

            public enum CodingKeys: String, CodingKey {
                case totalGb = "total_gb"
                case usedGb = "used_gb"
            }
        }
    }

    public struct MetalStatus: Codable {
        public let available: Bool
        public let initialized: Bool?
        public let device: String?
        public let recommendedWorkingSetGb: Double?
        public let error: String?

        public enum CodingKeys: String, CodingKey {
            case available, initialized, device
            case recommendedWorkingSetGb = "recommended_working_set_gb"
            case error
        }
    }

    public struct OllamaStatus: Codable {
        public let available: Bool
        public let modelCount: Int?
        public let models: [String]?
        public let status: String?
        public let error: String?

        public enum CodingKeys: String, CodingKey {
            case available
            case modelCount = "model_count"
            case models, status, error
        }
    }

    public struct P2PStatus: Codable {
        public let status: String?
        public let peers: Int?
        public let services: [String]?
        public let error: String?
    }

    public struct DatabaseStatus: Codable {
        public let status: String?
        public let sizeMb: Double?
        public let tableCount: Int?
        public let path: String?
        public let error: String?

        public enum CodingKeys: String, CodingKey {
            case status
            case sizeMb = "size_mb"
            case tableCount = "table_count"
            case path, error
        }
    }
}

public struct NLQueryResponse: Codable {
    public let answer: String
    public let query: String
    public let confidence: Double?
    public let sources: [String]?
}

public struct PatternDiscoveryResult: Codable {
    public let patterns: [Pattern]
    public let summary: String?

    public struct Pattern: Codable, Identifiable {
        public let id: String
        public let type: String
        public let description: String
        public let confidence: Double
        public let examples: [String]?
    }
}

// MARK: - Team Service

public final class TeamService {
    public static let shared = TeamService()
    private let apiClient = ApiClient.shared

    private init() {}

    // MARK: - Teams

    public func createTeam(name: String, description: String?) async throws -> Team {
        try await apiClient.request(
            path: "/v1/teams",
            method: .post,
            jsonBody: [
                "name": name,
                "description": description ?? ""
            ]
        )
    }

    public func joinTeam(code: String) async throws -> Team {
        try await apiClient.request(
            path: "/v1/teams/join",
            method: .post,
            jsonBody: ["code": code]
        )
    }

    public func listTeams() async throws -> [Team] {
        try await apiClient.request(
            path: "/v1/teams",
            method: .get
        )
    }

    // MARK: - Documents

    public func listDocuments() async throws -> [TeamDocument] {
        do {
            // request(path:method:) auto-unwraps SuccessResponse, so expect [TeamDocument] directly
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

    public func createDocument(title: String, content: String, type: String) async throws -> TeamDocument {
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

    public func updateDocument(id: String, title: String?, content: String?) async throws -> TeamDocument {
        var body: [String: Any] = [:]
        if let title = title { body["title"] = title }
        if let content = content { body["content"] = content }

        return try await apiClient.request(
            path: "/v1/docs/documents/\(id)",
            method: .put,
            jsonBody: body
        )
    }

    public func deleteDocument(id: String) async throws {
        // Backend returns: { status: "deleted", id: "..." }
        let _: DocumentDeleteResponse = try await apiClient.request(
            path: "/v1/docs/documents/\(id)",
            method: .delete
        )
    }

    // MARK: - Diagnostics

    public func getDiagnostics() async throws -> DiagnosticsStatus {
        do {
            // request(path:method:) auto-unwraps SuccessResponse, so expect DiagnosticsStatus directly
            let status: DiagnosticsStatus = try await apiClient.request(
                path: "/v1/diagnostics",
                method: .get
            )
            print("✅ Successfully loaded diagnostics")
            return status
        } catch {
            print("❌ Failed to load diagnostics: \(error)")
            if let decodingError = error as? DecodingError {
                print("Decoding error details: \(decodingError)")
            }
            throw error
        }
    }

    // MARK: - NL Query

    public func askNaturalLanguage(query: String) async throws -> NLQueryResponse {
        try await apiClient.request(
            path: "/v1/data/ask",
            method: .post,
            jsonBody: ["query": query]
        )
    }

    // MARK: - Pattern Discovery

    public func discoverPatterns(query: String, context: String?) async throws -> PatternDiscoveryResult {
        var body: [String: Any] = ["query": query]
        if let context = context { body["context"] = context }

        return try await apiClient.request(
            path: "/v1/data/patterns",
            method: .post,
            jsonBody: body
        )
    }

    // MARK: - Vault Setup

    public func setupVault(password: String) async throws -> VaultSetupResponse {
        try await apiClient.request(
            path: "/v1/vault/setup",
            method: .post,
            jsonBody: ["password": password]
        )
    }

    public func getVaultStatus() async throws -> VaultStatusResponse {
        try await apiClient.request(
            path: "/v1/vault/status",
            method: .get
        )
    }

    // MARK: - Messages

    public func sendMessage(channelId: String, content: String) async throws -> TeamMessage {
        // Team endpoints return raw responses (not wrapped in SuccessResponse)
        let body: [String: Any] = [
            "channel_id": channelId,
            "content": content,
            "type": "text"
        ]
        let jsonData = try JSONSerialization.data(withJSONObject: body)
        return try await apiClient.request(
            "/v1/team/channels/\(channelId)/messages",
            method: .post,
            body: jsonData,
            unwrapEnvelope: false
        )
    }

    public func getMessages(channelId: String, limit: Int = 50) async throws -> MessageListResponse {
        // Team endpoints return raw responses (not wrapped in SuccessResponse)
        try await apiClient.request(
            "/v1/team/channels/\(channelId)/messages?limit=\(limit)",
            method: .get,
            unwrapEnvelope: false
        )
    }

    // MARK: - Permissions

    public func getUserPermissions() async throws -> UserPermissions {
        // request(path:method:) auto-unwraps SuccessResponse, so just expect UserPermissions directly
        try await apiClient.request(
            path: "/v1/teams/user/permissions",
            method: .get
        )
    }

    // MARK: - P2P Network

    public func getP2PNetworkStatus() async throws -> P2PNetworkStatus {
        // Team endpoints return raw responses (not wrapped in SuccessResponse)
        try await apiClient.request(
            "/v1/team/p2p/status",
            method: .get,
            unwrapEnvelope: false
        )
    }

    // MARK: - Channels

    public func listChannels() async throws -> [TeamChannel] {
        // Team channels endpoint returns raw ChannelListResponse (not wrapped in SuccessResponse)
        let response: ChannelListResponse = try await apiClient.request(
            "/v1/team/channels",
            method: .get,
            unwrapEnvelope: false
        )
        return response.channels
    }
}

// MARK: - Channel Response Models

private struct ChannelListResponse: Codable {
    let channels: [TeamChannel]
    let total: Int
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
    public let hasMore: Bool?  // Optional - backend may not return this

    public enum CodingKeys: String, CodingKey {
        case channelId = "channel_id"
        case messages, total
        case hasMore = "has_more"
    }
}

// MARK: - Permissions Models

public struct UserPermissions: Codable {
    public let canAccessDocuments: Bool
    public let canAccessAutomation: Bool
    public let canAccessVault: Bool

    public enum CodingKeys: String, CodingKey {
        case canAccessDocuments = "can_access_documents"
        case canAccessAutomation = "can_access_automation"
        case canAccessVault = "can_access_vault"
    }
}

// MARK: - P2P Network Models

public struct P2PNetworkStatus: Codable {
    public let peerId: String
    public let isConnected: Bool
    public let discoveredPeers: Int
    public let activeChannels: Int
    public let multiaddrs: [String]

    public enum CodingKeys: String, CodingKey {
        case peerId = "peer_id"
        case isConnected = "is_connected"
        case discoveredPeers = "discovered_peers"
        case activeChannels = "active_channels"
        case multiaddrs
    }
}

// MARK: - Channel Models

public struct TeamChannel: Identifiable, Codable {
    public let id: String
    public let name: String
    public let type: String  // "public", "private", "direct"
    public let createdAt: String
    public let createdBy: String
    public let members: [String]
    public let admins: [String]
    public let description: String?
    public let topic: String?
    public let pinnedMessages: [String]
    public let dmParticipants: [String]?

    public var isPrivate: Bool {
        type == "private"
    }

    public enum CodingKeys: String, CodingKey {
        case id, name, type
        case createdAt = "created_at"
        case createdBy = "created_by"
        case members, admins, description, topic
        case pinnedMessages = "pinned_messages"
        case dmParticipants = "dm_participants"
    }
}

// MARK: - Vault Models

public struct VaultSetupResponse: Codable {
    public let status: String
    public let message: String
    public let vaultId: String?

    public enum CodingKeys: String, CodingKey {
        case status, message
        case vaultId = "vault_id"
    }
}

public struct VaultStatusResponse: Codable {
    public let initialized: Bool
    public let locked: Bool
    public let message: String?
}
