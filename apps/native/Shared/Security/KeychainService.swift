import Foundation
import Security
import LocalAuthentication

/// Secure storage for auth tokens using Keychain (or in-memory in DEBUG)
final class KeychainService {
    static let shared = KeychainService()

    private let service = "com.magnetarstudio.app"
    private let tokenKey = "auth_token"
    private let credentialsKey = "biometric_credentials"

    // DEBUG: In-memory storage to avoid keychain headaches during development
    #if DEBUG
    private var memoryStorage: [String: String] = [:]
    #endif

    private init() {}

    // MARK: - Token Management

    func saveToken(_ token: String, forKey key: String? = nil) throws {
        let accountKey = key ?? tokenKey

        #if DEBUG
        // DEBUG MODE: Use in-memory storage, skip keychain entirely
        memoryStorage[accountKey] = token
        print("💾 DEBUG: Token saved to memory (keychain bypassed)")
        return
        #else
        let data = Data(token.utf8)

        // Delete existing item first
        try? deleteToken(forKey: accountKey)

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: accountKey,
            kSecValueData as String: data,
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]

        let status = SecItemAdd(query as CFDictionary, nil)

        guard status == errSecSuccess else {
            throw KeychainServiceError.saveFailed(status)
        }
        #endif
    }

    func loadToken(forKey key: String? = nil) -> String? {
        let accountKey = key ?? tokenKey

        #if DEBUG
        // DEBUG MODE: Load from in-memory storage
        return memoryStorage[accountKey]
        #else
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: accountKey,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess,
              let data = result as? Data,
              let token = String(data: data, encoding: .utf8) else {
            return nil
        }

        return token
        #endif
    }

    func deleteToken(forKey key: String? = nil) throws {
        let accountKey = key ?? tokenKey

        #if DEBUG
        // DEBUG MODE: Remove from in-memory storage
        memoryStorage.removeValue(forKey: accountKey)
        print("🗑️ DEBUG: Token deleted from memory")
        return
        #else
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: accountKey
        ]

        let status = SecItemDelete(query as CFDictionary)

        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainServiceError.deleteFailed(status)
        }
        #endif
    }

    // MARK: - Biometric Credentials Storage

    /// Save username/password with biometric protection
    func saveBiometricCredentials(username: String, password: String) throws {
        let credentials = BiometricCredentials(username: username, password: password)
        let data = try JSONEncoder().encode(credentials)

        // Delete existing item first
        try? deleteBiometricCredentials()

        // Create access control for biometric authentication
        var error: Unmanaged<CFError>?
        guard let accessControl = SecAccessControlCreateWithFlags(
            nil,
            kSecAttrAccessibleWhenPasscodeSetThisDeviceOnly,
            .biometryCurrentSet,
            &error
        ) else {
            throw KeychainServiceError.accessControlFailed
        }

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: credentialsKey,
            kSecValueData as String: data,
            kSecAttrAccessControl as String: accessControl
        ]

        let status = SecItemAdd(query as CFDictionary, nil)

        guard status == errSecSuccess else {
            throw KeychainServiceError.saveFailed(status)
        }
    }

    /// Load username/password with biometric authentication
    func loadBiometricCredentials(context: LAContext) throws -> BiometricCredentials {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: credentialsKey,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne,
            kSecUseAuthenticationContext as String: context
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess,
              let data = result as? Data else {
            throw KeychainServiceError.loadFailed(status)
        }

        return try JSONDecoder().decode(BiometricCredentials.self, from: data)
    }

    /// Check if biometric credentials are stored
    func hasBiometricCredentials() -> Bool {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: credentialsKey,
            kSecReturnData as String: false,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]

        let status = SecItemCopyMatching(query as CFDictionary, nil)
        return status == errSecSuccess
    }

    /// Delete biometric credentials
    func deleteBiometricCredentials() throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: credentialsKey
        ]

        let status = SecItemDelete(query as CFDictionary)

        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainServiceError.deleteFailed(status)
        }
    }
}

// MARK: - Models

struct BiometricCredentials: Codable {
    let username: String
    let password: String
}

// MARK: - Errors

enum KeychainServiceError: LocalizedError {
    case saveFailed(OSStatus)
    case deleteFailed(OSStatus)
    case loadFailed(OSStatus)
    case accessControlFailed

    var errorDescription: String? {
        switch self {
        case .saveFailed(let status):
            return "Failed to save to Keychain (status: \(status))"
        case .deleteFailed(let status):
            return "Failed to delete from Keychain (status: \(status))"
        case .loadFailed(let status):
            return "Failed to load from Keychain (status: \(status))"
        case .accessControlFailed:
            return "Failed to create biometric access control"
        }
    }
}
