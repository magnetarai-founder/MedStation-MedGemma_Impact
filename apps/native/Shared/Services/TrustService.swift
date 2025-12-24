//
//  TrustService.swift
//  MagnetarStudio
//
//  MagnetarTrust - Swift service layer for trust network
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

// MARK: - Cryptographic Key Management

public enum TrustKeyError: Error, LocalizedError {
    case keyGenerationFailed(OSStatus)
    case keyNotFound
    case keychainError(OSStatus)
    case signingFailed
    case invalidPublicKey
    case encodingFailed

    public var errorDescription: String? {
        switch self {
        case .keyGenerationFailed(let status):
            return "Failed to generate key pair: \(status)"
        case .keyNotFound:
            return "Trust key not found in Keychain"
        case .keychainError(let status):
            return "Keychain error: \(status)"
        case .signingFailed:
            return "Failed to sign data"
        case .invalidPublicKey:
            return "Invalid public key format"
        case .encodingFailed:
            return "Failed to encode key data"
        }
    }
}

public final class TrustKeyManager {
    public static let shared = TrustKeyManager()

    private let keyTag = "com.magnetarstudio.trust.identity"
    private let keychainService = "MagnetarTrust"

    private init() {}

    // MARK: - Key Generation

    public func generateKeyPair() throws -> SecKey {
        // Delete existing key if present
        deleteKeyPair()

        let attributes: [String: Any] = [
            kSecAttrKeyType as String: kSecAttrKeyTypeECSECPrimeRandom,
            kSecAttrKeySizeInBits as String: 256,
            kSecPrivateKeyAttrs as String: [
                kSecAttrIsPermanent as String: true,
                kSecAttrApplicationTag as String: keyTag.data(using: .utf8)!,
                kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
            ]
        ]

        var error: Unmanaged<CFError>?
        guard let privateKey = SecKeyCreateRandomKey(attributes as CFDictionary, &error) else {
            let status = (error?.takeRetainedValue() as? NSError)?.code ?? -1
            throw TrustKeyError.keyGenerationFailed(OSStatus(status))
        }

        return privateKey
    }

    // MARK: - Key Retrieval

    public func getPrivateKey() throws -> SecKey {
        let query: [String: Any] = [
            kSecClass as String: kSecClassKey,
            kSecAttrApplicationTag as String: keyTag.data(using: .utf8)!,
            kSecAttrKeyType as String: kSecAttrKeyTypeECSECPrimeRandom,
            kSecReturnRef as String: true
        ]

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)

        guard status == errSecSuccess, let key = item else {
            if status == errSecItemNotFound {
                throw TrustKeyError.keyNotFound
            }
            throw TrustKeyError.keychainError(status)
        }

        // SecItemCopyMatching with kSecReturnRef for kSecClassKey returns SecKey
        // Swift can't introspect CoreFoundation types at runtime, so we use unsafeBitCast
        // This is safe because the query specifically requests a key reference
        return unsafeBitCast(key, to: SecKey.self)
    }

    public func getPublicKey() throws -> SecKey {
        let privateKey = try getPrivateKey()
        guard let publicKey = SecKeyCopyPublicKey(privateKey) else {
            throw TrustKeyError.invalidPublicKey
        }
        return publicKey
    }

    public func getPublicKeyBase64() throws -> String {
        let publicKey = try getPublicKey()

        var error: Unmanaged<CFError>?
        guard let publicKeyData = SecKeyCopyExternalRepresentation(publicKey, &error) as Data? else {
            throw TrustKeyError.encodingFailed
        }

        return publicKeyData.base64EncodedString()
    }

    public func hasKeyPair() -> Bool {
        do {
            _ = try getPrivateKey()
            return true
        } catch {
            return false
        }
    }

    // MARK: - Key Deletion

    @discardableResult
    public func deleteKeyPair() -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassKey,
            kSecAttrApplicationTag as String: keyTag.data(using: .utf8)!
        ]

        let status = SecItemDelete(query as CFDictionary)
        return status == errSecSuccess || status == errSecItemNotFound
    }

    // MARK: - Signing

    public func sign(data: Data) throws -> Data {
        let privateKey = try getPrivateKey()

        var error: Unmanaged<CFError>?
        guard let signature = SecKeyCreateSignature(
            privateKey,
            .ecdsaSignatureMessageX962SHA256,
            data as CFData,
            &error
        ) as Data? else {
            throw TrustKeyError.signingFailed
        }

        return signature
    }

    public func sign(message: String) throws -> String {
        guard let data = message.data(using: .utf8) else {
            throw TrustKeyError.encodingFailed
        }
        let signature = try sign(data: data)
        return signature.base64EncodedString()
    }

    // MARK: - Verification

    public func verify(signature: Data, for data: Data, publicKey: SecKey) -> Bool {
        var error: Unmanaged<CFError>?
        return SecKeyVerifySignature(
            publicKey,
            .ecdsaSignatureMessageX962SHA256,
            data as CFData,
            signature as CFData,
            &error
        )
    }

    public func publicKey(fromBase64 base64String: String) throws -> SecKey {
        guard let keyData = Data(base64Encoded: base64String) else {
            throw TrustKeyError.invalidPublicKey
        }

        let attributes: [String: Any] = [
            kSecAttrKeyType as String: kSecAttrKeyTypeECSECPrimeRandom,
            kSecAttrKeyClass as String: kSecAttrKeyClassPublic,
            kSecAttrKeySizeInBits as String: 256
        ]

        var error: Unmanaged<CFError>?
        guard let publicKey = SecKeyCreateWithData(keyData as CFData, attributes as CFDictionary, &error) else {
            throw TrustKeyError.invalidPublicKey
        }

        return publicKey
    }

    // MARK: - Attestation

    public func createAttestation(targetNodeId: String, level: TrustLevel, note: String?) throws -> SignedAttestation {
        let timestamp = ISO8601DateFormatter().string(from: Date())
        let payload = AttestationPayload(
            targetNodeId: targetNodeId,
            level: level,
            note: note,
            timestamp: timestamp
        )

        let encoder = JSONEncoder()
        encoder.outputFormatting = .sortedKeys
        let payloadData = try encoder.encode(payload)
        let payloadBase64 = payloadData.base64EncodedString()

        let signature = try sign(data: payloadData)
        let publicKey = try getPublicKeyBase64()

        return SignedAttestation(
            payload: payloadBase64,
            signature: signature.base64EncodedString(),
            signerPublicKey: publicKey
        )
    }
}

// MARK: - Attestation Models

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

// MARK: - Trust Service

public final class TrustService {
    private let keyManager = TrustKeyManager.shared
    public static let shared = TrustService()
    private let apiClient = ApiClient.shared

    private init() {}

    // MARK: - Health

    public func getHealth() async throws -> TrustHealthResponse {
        // Trust endpoints return raw responses (not wrapped in SuccessResponse)
        try await apiClient.request(
            "/v1/trust/health",
            method: .get,
            unwrapEnvelope: false
        )
    }

    // MARK: - Nodes

    public func registerNode(_ request: RegisterNodeRequest) async throws -> TrustNode {
        // Trust endpoints return raw responses (not wrapped in SuccessResponse)
        let body: [String: Any] = [
            "public_key": request.publicKey,
            "public_name": request.publicName,
            "type": request.type.rawValue,
            "alias": request.alias as Any,
            "bio": request.bio as Any,
            "location": request.location as Any,
            "display_mode": request.displayMode.rawValue
        ]
        let jsonData = try JSONSerialization.data(withJSONObject: body)
        return try await apiClient.request(
            "/v1/trust/nodes",
            method: .post,
            body: jsonData,
            unwrapEnvelope: false
        )
    }

    public func getNode(id: String) async throws -> TrustNode {
        // Trust endpoints return raw responses (not wrapped in SuccessResponse)
        try await apiClient.request(
            "/v1/trust/nodes/\(id)",
            method: .get,
            unwrapEnvelope: false
        )
    }

    public func listNodes(type: NodeType? = nil) async throws -> NodeListResponse {
        var path = "/v1/trust/nodes"
        if let type = type {
            path += "?node_type=\(type.rawValue)"
        }

        // Trust endpoints return raw responses (not wrapped in SuccessResponse)
        return try await apiClient.request(
            path,
            method: .get,
            unwrapEnvelope: false
        )
    }

    public func updateNode(id: String, _ request: RegisterNodeRequest) async throws -> TrustNode {
        // Trust endpoints return raw responses (not wrapped in SuccessResponse)
        let body: [String: Any] = [
            "public_key": request.publicKey,
            "public_name": request.publicName,
            "type": request.type.rawValue,
            "alias": request.alias as Any,
            "bio": request.bio as Any,
            "location": request.location as Any,
            "display_mode": request.displayMode.rawValue
        ]
        let jsonData = try JSONSerialization.data(withJSONObject: body)
        return try await apiClient.request(
            "/v1/trust/nodes/\(id)",
            method: .patch,
            body: jsonData,
            unwrapEnvelope: false
        )
    }

    // MARK: - Trust Relationships

    public func vouchForNode(_ request: VouchRequest) async throws -> TrustRelationship {
        // Trust endpoints return raw responses (not wrapped in SuccessResponse)
        let body: [String: Any] = [
            "target_node_id": request.targetNodeId,
            "level": request.level.rawValue,
            "note": request.note as Any
        ]
        let jsonData = try JSONSerialization.data(withJSONObject: body)
        return try await apiClient.request(
            "/v1/trust/vouch",
            method: .post,
            body: jsonData,
            unwrapEnvelope: false
        )
    }

    public func getTrustNetwork(maxDegrees: Int = 3) async throws -> TrustNetworkResponse {
        // Trust endpoints return raw responses (not wrapped in SuccessResponse)
        try await apiClient.request(
            "/v1/trust/network?max_degrees=\(maxDegrees)",
            method: .get,
            unwrapEnvelope: false
        )
    }

    public func getRelationships(level: TrustLevel? = nil) async throws -> TrustRelationshipResponse {
        var path = "/v1/trust/relationships"
        if let level = level {
            path += "?level=\(level.rawValue)"
        }

        // Trust endpoints return raw responses (not wrapped in SuccessResponse)
        return try await apiClient.request(
            path,
            method: .get,
            unwrapEnvelope: false
        )
    }

    // MARK: - Cryptographic Operations

    public func registerNodeWithNewIdentity(
        publicName: String,
        type: NodeType,
        alias: String? = nil,
        bio: String? = nil,
        location: String? = nil,
        displayMode: DisplayMode = .peacetime
    ) async throws -> TrustNode {
        // Generate new cryptographic identity
        _ = try keyManager.generateKeyPair()
        let publicKey = try keyManager.getPublicKeyBase64()

        let request = RegisterNodeRequest(
            publicKey: publicKey,
            publicName: publicName,
            type: type,
            alias: alias,
            bio: bio,
            location: location,
            displayMode: displayMode
        )

        return try await registerNode(request)
    }

    public func vouchWithSignature(
        targetNodeId: String,
        level: TrustLevel = .vouched,
        note: String? = nil
    ) async throws -> TrustRelationship {
        // Create signed attestation
        let attestation = try keyManager.createAttestation(
            targetNodeId: targetNodeId,
            level: level,
            note: note
        )

        // Trust endpoints return raw responses (not wrapped in SuccessResponse)
        let body: [String: Any] = [
            "target_node_id": targetNodeId,
            "level": level.rawValue,
            "note": note as Any,
            "attestation": [
                "payload": attestation.payload,
                "signature": attestation.signature,
                "signer_public_key": attestation.signerPublicKey
            ]
        ]
        let jsonData = try JSONSerialization.data(withJSONObject: body)
        return try await apiClient.request(
            "/v1/trust/vouch",
            method: .post,
            body: jsonData,
            unwrapEnvelope: false
        )
    }

    public func hasIdentity() -> Bool {
        return keyManager.hasKeyPair()
    }

    public func getMyPublicKey() throws -> String {
        return try keyManager.getPublicKeyBase64()
    }
}
