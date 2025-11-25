import Foundation
import SwiftUI

/// Auth state machine and bootstrap logic
@MainActor
final class AuthStore: ObservableObject {
    static let shared = AuthStore()

    // MARK: - Published State

    @Published private(set) var authState: AuthState = .welcome
    @Published private(set) var user: ApiUser?
    @Published private(set) var userSetupComplete: Bool?
    @Published private(set) var loading = false
    @Published private(set) var error: String?

    private let keychain = KeychainService.shared
    private let apiClient = ApiClient.shared

    private init() {}

    // MARK: - Bootstrap Flow

    /// Call on app launch to validate existing token
    func bootstrap() async {
        loading = true
        error = nil

        // Load token from keychain
        guard let token = keychain.loadToken() else {
            authState = .welcome
            loading = false
            return
        }

        // Token exists, validate it
        authState = .checking

        do {
            // Step 1: Validate user
            let user: ApiUser = try await apiClient.request("/v1/users/me")
            self.user = user

            // Step 2: Check setup status
            let status: SetupStatus = try await apiClient.request("/v1/users/me/setup/status")

            if status.userSetupCompleted {
                userSetupComplete = true
                authState = .authenticated
            } else {
                userSetupComplete = false
                authState = .setupNeeded
            }

            loading = false

        } catch ApiError.unauthorized {
            // Token invalid, clear and restart
            await clearAuthAndRestart()
        } catch {
            self.error = error.localizedDescription
            authState = .welcome
            loading = false
        }
    }

    // MARK: - Auth Actions

    /// Save token after login and bootstrap
    func saveToken(_ token: String) async {
        do {
            try keychain.saveToken(token)
            await bootstrap()
        } catch {
            self.error = error.localizedDescription
        }
    }

    /// Mark setup as completed and move to authenticated state
    func completeSetup() {
        userSetupComplete = true
        authState = .authenticated
    }

    /// Logout: clear token and reset state
    func logout() async {
        await clearAuthAndRestart()
    }

    // MARK: - Helpers

    private func clearAuthAndRestart() async {
        try? keychain.deleteToken()
        user = nil
        userSetupComplete = nil
        authState = .welcome
        loading = false
        error = nil
    }
}

// MARK: - Auth State

enum AuthState: Equatable {
    case welcome        // No token, show login
    case checking       // Validating existing token
    case setupNeeded    // Token valid but setup incomplete
    case authenticated  // Fully authenticated and setup complete
}
