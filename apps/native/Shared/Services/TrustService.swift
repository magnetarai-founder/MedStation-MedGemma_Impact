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

// MARK: - Cryptographic Key Management

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
            return "Failed to generate key pair: \(reason)"
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

/// Manages Ed25519 cryptographic keys for trust network operations.
/// SECURITY: Uses CryptoKit's Curve25519.Signing (Ed25519) for cross-platform compatibility
/// with the Python backend (NaCl/libsodium).
public final class TrustKeyManager {
    public static let shared = TrustKeyManager()

    private let keychainService = "MagnetarTrust"
    private let privateKeyAccount = "com.magnetarstudio.trust.ed25519.private"

    private init() {}

    // MARK: - Key Generation

    /// Generate a new Ed25519 keypair and store in Keychain
    public func generateKeyPair() throws -> Curve25519.Signing.PrivateKey {
        // Delete existing key if present
        deleteKeyPair()

        // Generate new Ed25519 keypair
        let privateKey = Curve25519.Signing.PrivateKey()

        // Store in Keychain
        let privateKeyData = privateKey.rawRepresentation

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: privateKeyAccount,
            kSecValueData as String: privateKeyData,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]

        let status = SecItemAdd(query as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw TrustKeyError.keychainError(status)
        }

        return privateKey
    }

    // MARK: - Key Retrieval

    /// Retrieve the Ed25519 private key from Keychain
    public func getPrivateKey() throws -> Curve25519.Signing.PrivateKey {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: privateKeyAccount,
            kSecReturnData as String: true
        ]

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)

        guard status == errSecSuccess, let keyData = item as? Data else {
            if status == errSecItemNotFound {
                throw TrustKeyError.keyNotFound
            }
            throw TrustKeyError.keychainError(status)
        }

        return try Curve25519.Signing.PrivateKey(rawRepresentation: keyData)
    }

    /// Get the Ed25519 public key
    public func getPublicKey() throws -> Curve25519.Signing.PublicKey {
        let privateKey = try getPrivateKey()
        return privateKey.publicKey
    }

    /// Get the public key as Base64-encoded string (32 bytes)
    public func getPublicKeyBase64() throws -> String {
        let publicKey = try getPublicKey()
        return publicKey.rawRepresentation.base64EncodedString()
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
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: keychainService,
            kSecAttrAccount as String: privateKeyAccount
        ]

        let status = SecItemDelete(query as CFDictionary)
        return status == errSecSuccess || status == errSecItemNotFound
    }

    // MARK: - Signing (Ed25519)

    /// Sign data with Ed25519 private key
    public func sign(data: Data) throws -> Data {
        let privateKey = try getPrivateKey()
        return try privateKey.signature(for: data)
    }

    /// Sign a message string and return Base64-encoded signature
    public func sign(message: String) throws -> String {
        guard let data = message.data(using: .utf8) else {
            throw TrustKeyError.encodingFailed
        }
        let signature = try sign(data: data)
        return signature.base64EncodedString()
    }

    // MARK: - Verification (Ed25519)

    /// Verify an Ed25519 signature
    public func verify(signature: Data, for data: Data, publicKey: Curve25519.Signing.PublicKey) -> Bool {
        return publicKey.isValidSignature(signature, for: data)
    }

    /// Parse a Base64-encoded Ed25519 public key
    public func publicKey(fromBase64 base64String: String) throws -> Curve25519.Signing.PublicKey {
        guard let keyData = Data(base64Encoded: base64String) else {
            throw TrustKeyError.invalidPublicKey
        }

        guard keyData.count == 32 else {
            throw TrustKeyError.invalidPublicKey
        }

        return try Curve25519.Signing.PublicKey(rawRepresentation: keyData)
    }

    // MARK: - Attestation

    /// Create a signed attestation for vouching
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

    /// Register a node with a signed request
    /// SECURITY: The request includes an Ed25519 signature proving key ownership
    /// REPLAY PROTECTION: Includes nonce for replay attack prevention
    public func registerNode(_ request: RegisterNodeRequest) async throws -> TrustNode {
        // Trust endpoints return raw responses (not wrapped in SuccessResponse)
        // Include all fields including security fields (timestamp, nonce, signature)
        let body: [String: Any] = [
            "public_key": request.publicKey,
            "public_name": request.publicName,
            "type": request.type.rawValue,
            "alias": request.alias as Any,
            "bio": request.bio as Any,
            "location": request.location as Any,
            "display_mode": request.displayMode.rawValue,
            "timestamp": request.timestamp,
            "nonce": request.nonce,
            "signature": request.signature
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

    /// Register a new node with a freshly generated Ed25519 identity
    /// SECURITY: Generates keypair, signs registration, and submits to backend
    public func registerNodeWithNewIdentity(
        publicName: String,
        type: NodeType,
        alias: String? = nil,
        bio: String? = nil,
        location: String? = nil,
        displayMode: DisplayMode = .peacetime
    ) async throws -> TrustNode {
        // Generate new Ed25519 cryptographic identity
        let privateKey = try keyManager.generateKeyPair()

        // Create signed registration request
        let request = try RegisterNodeRequest(
            privateKey: privateKey,
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

    // MARK: - Safety Number Verification

    /// Generate a 60-digit safety number for verifying identity with another node.
    /// SECURITY: Safety numbers change when either party rotates keys, detecting MITM attacks.
    /// Both parties will compute the same safety number (keys are sorted lexicographically).
    ///
    /// - Parameters:
    ///   - localPublicKey: Your Base64-encoded public key
    ///   - remotePublicKey: The other party's Base64-encoded public key
    /// - Returns: 60-digit safety number string
    public func generateSafetyNumber(localPublicKey: String, remotePublicKey: String) -> String {
        // Decode public keys
        guard let localKeyData = Data(base64Encoded: localPublicKey),
              let remoteKeyData = Data(base64Encoded: remotePublicKey) else {
            return "000000000000000000000000000000000000000000000000000000000000"
        }

        // Concatenate keys in lexicographic order (ensures both parties get same result)
        let combined: Data
        if localKeyData.lexicographicallyPrecedes(remoteKeyData) {
            combined = localKeyData + remoteKeyData
        } else {
            combined = remoteKeyData + localKeyData
        }

        // SHA-512 hash and convert to decimal digits
        let hash = SHA512.hash(data: combined)
        let hashData = Data(hash)

        // Convert hash bytes to a large integer, then to decimal string
        // Take first 60 digits for safety number
        let hexString = hashData.map { String(format: "%02x", $0) }.joined()

        // Convert hex to decimal digits (use simple modular arithmetic)
        var digits = ""
        for i in stride(from: 0, to: min(hexString.count, 120), by: 2) {
            let startIndex = hexString.index(hexString.startIndex, offsetBy: i)
            let endIndex = hexString.index(startIndex, offsetBy: 2)
            if let byte = UInt8(String(hexString[startIndex..<endIndex]), radix: 16) {
                digits += String(format: "%03d", Int(byte) % 1000)
            }
        }

        // Return exactly 60 digits
        let result = String(digits.prefix(60))
        if result.count < 60 {
            return result + String(repeating: "0", count: 60 - result.count)
        }
        return result
    }

    /// Generate safety number for verifying another node.
    /// Uses your stored private key to compute the local public key.
    ///
    /// - Parameter remoteNode: The node to verify
    /// - Returns: 60-digit safety number, or nil if no local identity
    public func generateSafetyNumber(forNode remoteNode: TrustNode) -> String? {
        guard let localPublicKey = try? getMyPublicKey() else {
            return nil
        }
        return generateSafetyNumber(localPublicKey: localPublicKey, remotePublicKey: remoteNode.publicKey)
    }

    /// Format a 60-digit safety number into groups of 5 for display (like Signal).
    /// Example: "12345 67890 12345 67890 12345 67890 12345 67890 12345 67890 12345 67890"
    public func formatSafetyNumber(_ safetyNumber: String) -> String {
        var formatted = ""
        for (index, char) in safetyNumber.enumerated() {
            if index > 0 && index % 5 == 0 {
                formatted += " "
            }
            formatted.append(char)
        }
        return formatted
    }

    /// Format a 60-digit safety number into a 3-row grid for QR code style display.
    /// Each row has 4 groups of 5 digits (20 digits per row).
    public func formatSafetyNumberGrid(_ safetyNumber: String) -> [[String]] {
        var grid: [[String]] = []
        var currentRow: [String] = []
        var currentGroup = ""

        for char in safetyNumber {
            currentGroup.append(char)

            if currentGroup.count == 5 {
                currentRow.append(currentGroup)
                currentGroup = ""

                if currentRow.count == 4 {
                    grid.append(currentRow)
                    currentRow = []
                }
            }
        }

        // Handle any remaining digits
        if !currentGroup.isEmpty {
            currentRow.append(currentGroup)
        }
        if !currentRow.isEmpty {
            grid.append(currentRow)
        }

        return grid
    }

    /// Generate fingerprint from a public key (SHA-256, formatted as hex with colons).
    public func generateFingerprint(publicKey: String) -> String {
        guard let keyData = Data(base64Encoded: publicKey) else {
            return "Invalid Key"
        }

        let hash = SHA256.hash(data: keyData)
        let hexString = hash.map { String(format: "%02X", $0) }.joined()

        // Format as colon-separated pairs (like macOS certificate fingerprints)
        var formatted = ""
        for (index, char) in hexString.enumerated() {
            if index > 0 && index % 2 == 0 {
                formatted += ":"
            }
            formatted.append(char)
        }
        return formatted
    }
}

// MARK: - Safety Number Verification State

/// Tracks verification state for a peer's safety number.
public struct SafetyNumberVerification: Codable {
    public let nodeId: String
    public let safetyNumber: String
    public let verifiedAt: Date?
    public let isVerified: Bool

    public init(nodeId: String, safetyNumber: String, verifiedAt: Date? = nil, isVerified: Bool = false) {
        self.nodeId = nodeId
        self.safetyNumber = safetyNumber
        self.verifiedAt = verifiedAt
        self.isVerified = isVerified
    }
}
