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
        // Wait for backend to be ready before attempting auth
        print("⏳ Waiting for backend to be ready...")
        var backendReady = false
        var attempts = 0

        while !backendReady && attempts < 15 {
            backendReady = await checkBackendHealth()
            if !backendReady {
                try? await Task.sleep(nanoseconds: 500_000_000) // 0.5 second
                attempts += 1
            }
        }

        if !backendReady {
            print("⚠️ Backend not ready after 7.5 seconds, will retry auth later")
            authState = .welcome
            loading = false
            return
        }

        print("✓ Backend is ready, proceeding with auth")

        // DEVELOPMENT BYPASS: Auto-login for fast iteration
        #if DEBUG
        print("⚠️ DEBUG MODE: Auto-login enabled for fast iteration")

        // Check if we already have a valid token
        if keychain.loadToken() != nil {
            // Try to use existing token
            do {
                let user: ApiUser = try await apiClient.request("/v1/auth/me")
                self.user = user
                userSetupComplete = true
                authState = .authenticated
                loading = false
                return
            } catch {
                // Token invalid, will try to login below
                print("DEBUG: Existing token invalid, will attempt auto-login")
            }
        }

        // Auto-login with founder credentials
        do {
            struct LoginRequest: Codable {
                let username: String
                let password: String
            }

            struct LoginResponse: Codable {
                let token: String
                let refreshToken: String?
                let userId: String
                let username: String
                let deviceId: String
                let role: String
                let expiresIn: Int

                enum CodingKeys: String, CodingKey {
                    case token
                    case refreshToken = "refresh_token"
                    case userId = "user_id"
                    case username
                    case deviceId = "device_id"
                    case role
                    case expiresIn = "expires_in"
                }
            }

            let response: LoginResponse = try await apiClient.request(
                "/v1/auth/login",
                method: .post,
                body: LoginRequest(username: "founder", password: "Jesus33"),
                authenticated: false
            )

            try keychain.saveToken(response.token)
            self.user = ApiUser(
                userId: response.userId,
                username: response.username,
                deviceId: response.deviceId,
                role: response.role
            )
            userSetupComplete = true
            authState = .authenticated
            loading = false
            print("✅ DEBUG: Auto-login successful")
            return

        } catch {
            print("⚠️ DEBUG: Auto-login failed: \(error.localizedDescription)")
            print("   Falling through to normal auth flow...")
        }
        #endif

        loading = true
        error = nil

        // Load token from keychain
        guard keychain.loadToken() != nil else {
            authState = .welcome
            loading = false
            return
        }

        // Token exists, validate it
        authState = .checking

        do {
            // Step 1: Validate user
            let user: ApiUser = try await apiClient.request("/v1/auth/me")
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

    /// Set error message
    func setError(_ message: String?) {
        self.error = message
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

    private func checkBackendHealth() async -> Bool {
        guard let url = URL(string: "http://localhost:8000/health") else { return false }

        do {
            let (_, response) = try await URLSession.shared.data(from: url)
            if let httpResponse = response as? HTTPURLResponse {
                return httpResponse.statusCode == 200
            }
        } catch {
            // Server not responding
            return false
        }

        return false
    }
}

// MARK: - Auth State

enum AuthState: Equatable {
    case welcome        // No token, show login
    case checking       // Validating existing token
    case setupNeeded    // Token valid but setup incomplete
    case authenticated  // Fully authenticated and setup complete
}
