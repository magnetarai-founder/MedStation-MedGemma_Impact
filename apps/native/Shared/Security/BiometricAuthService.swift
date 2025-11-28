//
//  BiometricAuthService.swift
//  MagnetarStudio
//
//  Handles Touch ID / Face ID authentication
//

import Foundation
import LocalAuthentication

/// Service for biometric authentication (Touch ID/Face ID)
final class BiometricAuthService {
    static let shared = BiometricAuthService()

    private init() {}

    // MARK: - Biometric Availability

    /// Check if biometric authentication is available
    func biometricType() -> BiometricType {
        let context = LAContext()
        var error: NSError?

        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) else {
            return .none
        }

        switch context.biometryType {
        case .none:
            return .none
        case .touchID:
            return .touchID
        case .faceID:
            return .faceID
        case .opticID:
            return .opticID
        @unknown default:
            return .none
        }
    }

    /// Check if biometrics are available
    var isBiometricAvailable: Bool {
        biometricType() != .none
    }

    // MARK: - Authentication

    /// Authenticate using biometrics
    /// - Parameter reason: Reason to display to the user
    /// - Returns: True if authentication succeeded
    func authenticate(reason: String) async throws -> Bool {
        let context = LAContext()
        var error: NSError?

        guard context.canEvaluatePolicy(.deviceOwnerAuthenticationWithBiometrics, error: &error) else {
            if let error = error {
                throw BiometricError.notAvailable(error.localizedDescription)
            }
            throw BiometricError.notAvailable("Biometric authentication not available")
        }

        do {
            return try await context.evaluatePolicy(
                .deviceOwnerAuthenticationWithBiometrics,
                localizedReason: reason
            )
        } catch let error as LAError {
            switch error.code {
            case .userCancel:
                throw BiometricError.userCancel
            case .userFallback:
                throw BiometricError.userFallback
            case .biometryNotAvailable:
                throw BiometricError.notAvailable("Biometric authentication not available")
            case .biometryNotEnrolled:
                throw BiometricError.notEnrolled
            case .biometryLockout:
                throw BiometricError.lockout
            default:
                throw BiometricError.failed(error.localizedDescription)
            }
        } catch {
            throw BiometricError.failed(error.localizedDescription)
        }
    }
}

// MARK: - Models

enum BiometricType {
    case none
    case touchID
    case faceID
    case opticID

    var displayName: String {
        switch self {
        case .none: return "None"
        case .touchID: return "Touch ID"
        case .faceID: return "Face ID"
        case .opticID: return "Optic ID"
        }
    }

    var icon: String {
        switch self {
        case .none: return "lock.fill"
        case .touchID: return "touchid"
        case .faceID: return "faceid"
        case .opticID: return "opticid"
        }
    }
}

enum BiometricError: LocalizedError {
    case notAvailable(String)
    case notEnrolled
    case lockout
    case userCancel
    case userFallback
    case failed(String)

    var errorDescription: String? {
        switch self {
        case .notAvailable(let reason):
            return "Biometric authentication not available: \(reason)"
        case .notEnrolled:
            return "No biometric authentication enrolled. Please set up Touch ID or Face ID in System Preferences."
        case .lockout:
            return "Biometric authentication is locked. Please try again later or use your password."
        case .userCancel:
            return "Authentication cancelled"
        case .userFallback:
            return "User chose to enter password"
        case .failed(let reason):
            return "Authentication failed: \(reason)"
        }
    }
}
