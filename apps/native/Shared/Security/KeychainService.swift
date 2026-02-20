import Foundation
import Security

/// Secure storage for auth tokens using Keychain
/// Note: Always uses real Keychain - no DEBUG bypass for security
final class KeychainService {
    static let shared = KeychainService()

    private let service = "com.medstation.app"
    private let tokenKey = "auth_token"
    private let credentialsKey = "biometric_credentials"

    private init() {}

    // MARK: - Token Management

    func saveToken(_ token: String, forKey key: String? = nil) throws {
        let accountKey = key ?? tokenKey
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
    }

    func loadToken(forKey key: String? = nil) -> String? {
        let accountKey = key ?? tokenKey

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
    }

    func deleteToken(forKey key: String? = nil) throws {
        let accountKey = key ?? tokenKey

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: accountKey
        ]

        let status = SecItemDelete(query as CFDictionary)

        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainServiceError.deleteFailed(status)
        }
    }

    // MARK: - Biometric Credentials

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

// MARK: - Errors

enum KeychainServiceError: LocalizedError {
    case saveFailed(OSStatus)
    case deleteFailed(OSStatus)
    case loadFailed(OSStatus)

    var errorDescription: String? {
        switch self {
        case .saveFailed(let status):
            return "Failed to save to Keychain (status: \(status))"
        case .deleteFailed(let status):
            return "Failed to delete from Keychain (status: \(status))"
        case .loadFailed(let status):
            return "Failed to load from Keychain (status: \(status))"
        }
    }
}
