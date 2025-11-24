//
//  KeychainManager.swift
//  MagnetarStudio
//
//  Secure storage for JWT tokens and sensitive data using macOS/iOS Keychain.
//  Supports biometric protection (Face ID / Touch ID).
//

import Foundation
import Security
import LocalAuthentication

final class KeychainManager {
    static let shared = KeychainManager()

    private init() {}

    // MARK: - Public Methods

    /// Store a token in Keychain
    /// Note: Simplified for development - biometric protection disabled
    func store(token: String, for key: String) throws {
        let data = Data(token.utf8)

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecValueData as String: data,
            kSecAttrService as String: "com.magnetar.studio",
            kSecAttrAccessible as String: kSecAttrAccessibleWhenUnlockedThisDeviceOnly
        ]

        // Delete existing item if present
        SecItemDelete(query as CFDictionary)

        // Add new item
        let status = SecItemAdd(query as CFDictionary, nil)

        guard status == errSecSuccess else {
            throw KeychainError.storeFailed(status)
        }
    }

    /// Retrieve a token from Keychain
    /// Note: Simplified for development - no biometric prompt
    func retrieve(for key: String) throws -> String {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecAttrService as String: "com.magnetar.studio",
            kSecReturnData as String: true
        ]

        var result: AnyObject?
        let status = SecItemCopyMatching(query as CFDictionary, &result)

        guard status == errSecSuccess else {
            throw KeychainError.retrieveFailed(status)
        }

        guard let data = result as? Data,
              let token = String(data: data, encoding: .utf8) else {
            throw KeychainError.invalidData
        }

        return token
    }

    /// Delete a token from Keychain
    func delete(for key: String) throws {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrAccount as String: key,
            kSecAttrService as String: "com.magnetar.studio"
        ]

        let status = SecItemDelete(query as CFDictionary)

        // Success if deleted or not found
        guard status == errSecSuccess || status == errSecItemNotFound else {
            throw KeychainError.deleteFailed(status)
        }
    }

    /// Check if biometrics are available
    func biometricsAvailable() -> Bool {
        let context = LAContext()
        var error: NSError?
        return context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error)
    }

    /// Get biometric type (Face ID or Touch ID)
    func biometricType() -> BiometricType {
        let context = LAContext()
        var error: NSError?

        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) else {
            return .none
        }

        switch context.biometryType {
        case .faceID:
            return .faceID
        case .touchID:
            return .touchID
        case .opticID:
            return .opticID
        case .none:
            return .none
        @unknown default:
            return .none
        }
    }
}

// MARK: - Error Types

enum KeychainError: LocalizedError {
    case accessControlCreationFailed
    case storeFailed(OSStatus)
    case retrieveFailed(OSStatus)
    case deleteFailed(OSStatus)
    case invalidData

    var errorDescription: String? {
        switch self {
        case .accessControlCreationFailed:
            return "Failed to create access control for Keychain"
        case .storeFailed(let status):
            return "Failed to store item in Keychain (status: \(status))"
        case .retrieveFailed(let status):
            return "Failed to retrieve item from Keychain (status: \(status))"
        case .deleteFailed(let status):
            return "Failed to delete item from Keychain (status: \(status))"
        case .invalidData:
            return "Invalid data retrieved from Keychain"
        }
    }
}

enum BiometricType {
    case faceID
    case touchID
    case opticID
    case none

    var displayName: String {
        switch self {
        case .faceID: return "Face ID"
        case .touchID: return "Touch ID"
        case .opticID: return "Optic ID"
        case .none: return "None"
        }
    }
}
