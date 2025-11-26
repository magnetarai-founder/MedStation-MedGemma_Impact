import Foundation
import Security

/// Secure storage for auth tokens using Keychain
final class KeychainService {
    static let shared = KeychainService()

    private let service = "com.magnetarstudio.app"
    private let tokenKey = "auth_token"

    private init() {}

    // MARK: - Token Management

    func saveToken(_ token: String, forKey key: String? = nil) throws {
        let accountKey = key ?? tokenKey

        // DEVELOPMENT BYPASS: Skip keychain to avoid prompts
        #if DEBUG
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
            kSecAttrAccessible as String: kSecAttrAccessibleAfterFirstUnlock
        ]

        let status = SecItemAdd(query as CFDictionary, nil)

        guard status == errSecSuccess else {
            throw KeychainServiceError.saveFailed(status)
        }
        #endif
    }

    func loadToken(forKey key: String? = nil) -> String? {
        let accountKey = key ?? tokenKey

        // DEVELOPMENT BYPASS: Return nil to avoid keychain prompts
        #if DEBUG
        return nil
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

        // DEVELOPMENT BYPASS: Skip keychain to avoid prompts
        #if DEBUG
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
}

// MARK: - Errors

enum KeychainServiceError: LocalizedError {
    case saveFailed(OSStatus)
    case deleteFailed(OSStatus)

    var errorDescription: String? {
        switch self {
        case .saveFailed(let status):
            return "Failed to save token to Keychain (status: \(status))"
        case .deleteFailed(let status):
            return "Failed to delete token from Keychain (status: \(status))"
        }
    }
}
