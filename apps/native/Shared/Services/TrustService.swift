//
//  TrustService.swift
//  MagnetarStudio
//
//  MagnetarTrust - Swift service layer for trust network
//  Part of MagnetarMission: Decentralized trust for churches, missions, and humanitarian teams
//

import Foundation

// MARK: - Enums

public enum NodeType: String, Codable {
    case individual = "individual"
    case church = "church"
    case mission = "mission"
    case family = "family"
    case organization = "organization"
}

public enum TrustLevel: String, Codable {
    case direct = "direct"       // I know you personally
    case vouched = "vouched"     // Someone I trust vouches for you
    case network = "network"     // 2-3 degrees of separation
}

public enum DisplayMode: String, Codable {
    case peacetime = "peacetime"         // Full names, churches visible
    case underground = "underground"     // Pseudonyms, codes only
}

// MARK: - Models

public struct TrustNode: Identifiable, Codable {
    public let id: String
    public let publicKey: String

    // Identity (changes based on display_mode)
    public let publicName: String
    public let alias: String?

    // Node metadata
    public let type: NodeType
    public let displayMode: DisplayMode
    public let bio: String?
    public let location: String?

    // Timestamps
    public let createdAt: String
    public let lastSeen: String

    // Network metadata
    public let isHub: Bool
    public let vouchedBy: String?

    public enum CodingKeys: String, CodingKey {
        case id
        case publicKey = "public_key"
        case publicName = "public_name"
        case alias
        case type
        case displayMode = "display_mode"
        case bio
        case location
        case createdAt = "created_at"
        case lastSeen = "last_seen"
        case isHub = "is_hub"
        case vouchedBy = "vouched_by"
    }
}

public struct TrustRelationship: Identifiable, Codable {
    public let id: String
    public let fromNode: String
    public let toNode: String
    public let level: TrustLevel
    public let vouchedBy: String?
    public let established: String
    public let lastVerified: String
    public let note: String?
    public let isMutual: Bool

    public enum CodingKeys: String, CodingKey {
        case id
        case fromNode = "from_node"
        case toNode = "to_node"
        case level
        case vouchedBy = "vouched_by"
        case established
        case lastVerified = "last_verified"
        case note
        case isMutual = "is_mutual"
    }
}

// MARK: - Request Models

public struct RegisterNodeRequest: Codable {
    public let publicKey: String
    public let publicName: String
    public let type: NodeType
    public let alias: String?
    public let bio: String?
    public let location: String?
    public let displayMode: DisplayMode

    public init(publicKey: String, publicName: String, type: NodeType, alias: String? = nil, bio: String? = nil, location: String? = nil, displayMode: DisplayMode = .peacetime) {
        self.publicKey = publicKey
        self.publicName = publicName
        self.type = type
        self.alias = alias
        self.bio = bio
        self.location = location
        self.displayMode = displayMode
    }

    public enum CodingKeys: String, CodingKey {
        case publicKey = "public_key"
        case publicName = "public_name"
        case type
        case alias
        case bio
        case location
        case displayMode = "display_mode"
    }
}

public struct VouchRequest: Codable {
    public let targetNodeId: String
    public let level: TrustLevel
    public let note: String?

    public init(targetNodeId: String, level: TrustLevel = .vouched, note: String? = nil) {
        self.targetNodeId = targetNodeId
        self.level = level
        self.note = note
    }

    public enum CodingKeys: String, CodingKey {
        case targetNodeId = "target_node_id"
        case level
        case note
    }
}

// MARK: - Response Models

public struct TrustNetworkResponse: Codable {
    public let nodeId: String
    public let directTrusts: [TrustNode]
    public let vouchedTrusts: [TrustNode]
    public let networkTrusts: [TrustNode]
    public let totalNetworkSize: Int

    public enum CodingKeys: String, CodingKey {
        case nodeId = "node_id"
        case directTrusts = "direct_trusts"
        case vouchedTrusts = "vouched_trusts"
        case networkTrusts = "network_trusts"
        case totalNetworkSize = "total_network_size"
    }
}

public struct NodeListResponse: Codable {
    public let nodes: [TrustNode]
    public let total: Int
}

public struct TrustRelationshipResponse: Codable {
    public let relationships: [TrustRelationship]
    public let total: Int
}

public struct TrustHealthResponse: Codable {
    public let status: String
    public let service: String
    public let totalNodes: Int
    public let timestamp: String

    public enum CodingKeys: String, CodingKey {
        case status
        case service
        case totalNodes = "total_nodes"
        case timestamp
    }
}

// MARK: - Trust Service

public final class TrustService {
    public static let shared = TrustService()
    private let apiClient = ApiClient.shared

    private init() {}

    // MARK: - Health

    public func getHealth() async throws -> TrustHealthResponse {
        try await apiClient.request(
            path: "/v1/trust/health",
            method: .get
        )
    }

    // MARK: - Nodes

    public func registerNode(_ request: RegisterNodeRequest) async throws -> TrustNode {
        try await apiClient.request(
            path: "/v1/trust/nodes",
            method: .post,
            jsonBody: [
                "public_key": request.publicKey,
                "public_name": request.publicName,
                "type": request.type.rawValue,
                "alias": request.alias as Any,
                "bio": request.bio as Any,
                "location": request.location as Any,
                "display_mode": request.displayMode.rawValue
            ]
        )
    }

    public func getNode(id: String) async throws -> TrustNode {
        try await apiClient.request(
            path: "/v1/trust/nodes/\(id)",
            method: .get
        )
    }

    public func listNodes(type: NodeType? = nil) async throws -> NodeListResponse {
        var path = "/v1/trust/nodes"
        if let type = type {
            path += "?node_type=\(type.rawValue)"
        }

        return try await apiClient.request(
            path: path,
            method: .get
        )
    }

    public func updateNode(id: String, _ request: RegisterNodeRequest) async throws -> TrustNode {
        try await apiClient.request(
            path: "/v1/trust/nodes/\(id)",
            method: .patch,
            jsonBody: [
                "public_key": request.publicKey,
                "public_name": request.publicName,
                "type": request.type.rawValue,
                "alias": request.alias as Any,
                "bio": request.bio as Any,
                "location": request.location as Any,
                "display_mode": request.displayMode.rawValue
            ]
        )
    }

    // MARK: - Trust Relationships

    public func vouchForNode(_ request: VouchRequest) async throws -> TrustRelationship {
        try await apiClient.request(
            path: "/v1/trust/vouch",
            method: .post,
            jsonBody: [
                "target_node_id": request.targetNodeId,
                "level": request.level.rawValue,
                "note": request.note as Any
            ]
        )
    }

    public func getTrustNetwork(maxDegrees: Int = 3) async throws -> TrustNetworkResponse {
        try await apiClient.request(
            path: "/v1/trust/network?max_degrees=\(maxDegrees)",
            method: .get
        )
    }

    public func getRelationships(level: TrustLevel? = nil) async throws -> TrustRelationshipResponse {
        var path = "/v1/trust/relationships"
        if let level = level {
            path += "?level=\(level.rawValue)"
        }

        return try await apiClient.request(
            path: path,
            method: .get
        )
    }
}
