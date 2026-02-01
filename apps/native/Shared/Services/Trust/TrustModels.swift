//
//  TrustModels.swift
//  MagnetarStudio
//
//  MagnetarTrust data models - Extracted from TrustService.swift
//  Part of MagnetarMission: Decentralized trust for churches, missions, and humanitarian teams
//

import Foundation
import Security
import CryptoKit

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

// MARK: - Core Models

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

/// Request to register a new trust node.
/// SECURITY: Registration requires an Ed25519 signature proving ownership of the private key.
/// REPLAY PROTECTION (Dec 2025): Includes nonce for replay attack prevention.
public struct RegisterNodeRequest: Codable {
    public let publicKey: String
    public let publicName: String
    public let type: NodeType
    public let alias: String?
    public let bio: String?
    public let location: String?
    public let displayMode: DisplayMode

    // Security fields (required for authenticated registration)
    public let timestamp: String
    public let nonce: String
    public let signature: String

    /// Create a signed registration request with replay protection
    /// - Parameters:
    ///   - privateKey: Ed25519 private key for signing
    ///   - publicName: Display name for the node
    ///   - type: Node type (individual, church, etc.)
    ///   - alias: Optional alias/pseudonym
    ///   - bio: Optional biography
    ///   - location: Optional location
    ///   - displayMode: Peacetime or underground mode
    public init(
        privateKey: Curve25519.Signing.PrivateKey,
        publicName: String,
        type: NodeType,
        alias: String? = nil,
        bio: String? = nil,
        location: String? = nil,
        displayMode: DisplayMode = .peacetime
    ) throws {
        let publicKeyBase64 = privateKey.publicKey.rawRepresentation.base64EncodedString()
        let timestamp = ISO8601DateFormatter().string(from: Date())

        // Generate 16-byte random nonce for replay protection
        var nonceBytes = [UInt8](repeating: 0, count: 16)
        _ = SecRandomCopyBytes(kSecRandomDefault, nonceBytes.count, &nonceBytes)
        let nonce = nonceBytes.map { String(format: "%02x", $0) }.joined()

        // Create canonical payload: nonce|timestamp|public_key|public_name|type
        let canonicalPayload = "\(nonce)|\(timestamp)|\(publicKeyBase64)|\(publicName)|\(type.rawValue)"

        // Sign the payload with Ed25519
        guard let payloadData = canonicalPayload.data(using: .utf8) else {
            throw TrustKeyError.encodingFailed
        }
        let signatureData = try privateKey.signature(for: payloadData)
        let signatureBase64 = signatureData.base64EncodedString()

        self.publicKey = publicKeyBase64
        self.publicName = publicName
        self.type = type
        self.alias = alias
        self.bio = bio
        self.location = location
        self.displayMode = displayMode
        self.timestamp = timestamp
        self.nonce = nonce
        self.signature = signatureBase64
    }

    public enum CodingKeys: String, CodingKey {
        case publicKey = "public_key"
        case publicName = "public_name"
        case type
        case alias
        case bio
        case location
        case displayMode = "display_mode"
        case timestamp
        case nonce
        case signature
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

// MARK: - Error Types

public enum TrustKeyError: Error, LocalizedError {
    case keyGenerationFailed(String)
    case keyNotFound
    case keychainError(OSStatus)
    case signingFailed
    case invalidPublicKey
    case encodingFailed

    public var errorDescription: String? {
        switch self {
        case .keyGenerationFailed(let reason):
            return "Failed to generate key: \(reason)"
        case .keyNotFound:
            return "Trust key not found in keychain"
        case .keychainError(let status):
            return "Keychain error: \(status)"
        case .signingFailed:
            return "Failed to sign message"
        case .invalidPublicKey:
            return "Invalid public key format"
        case .encodingFailed:
            return "Failed to encode message"
        }
    }
}

// MARK: - Attestation Models

public struct AttestationRequest: Codable {
    public let publicKey: String
    public let claimType: String
    public let claimValue: String

    public init(publicKey: String, claimType: String, claimValue: String) {
        self.publicKey = publicKey
        self.claimType = claimType
        self.claimValue = claimValue
    }

    public enum CodingKeys: String, CodingKey {
        case publicKey = "public_key"
        case claimType = "claim_type"
        case claimValue = "claim_value"
    }
}

public struct AttestationResponse: Codable {
    public let attestationId: String
    public let status: String
    public let claimType: String
    public let issuedAt: String

    public enum CodingKeys: String, CodingKey {
        case attestationId = "attestation_id"
        case status
        case claimType = "claim_type"
        case issuedAt = "issued_at"
    }
}

// MARK: - Signed Attestation Models

public struct AttestationPayload: Codable {
    public let targetNodeId: String
    public let level: TrustLevel
    public let note: String?
    public let timestamp: String

    public enum CodingKeys: String, CodingKey {
        case targetNodeId = "target_node_id"
        case level
        case note
        case timestamp
    }
}

public struct SignedAttestation: Codable {
    public let payload: String
    public let signature: String
    public let signerPublicKey: String

    public enum CodingKeys: String, CodingKey {
        case payload
        case signature
        case signerPublicKey = "signer_public_key"
    }
}
