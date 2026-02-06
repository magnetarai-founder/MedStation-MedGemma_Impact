import Foundation
import Observation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "AuthStore")

// MARK: - AuthStore

/// Central authentication state machine and bootstrap logic.
///
/// ## Overview
/// AuthStore manages the complete authentication lifecycle - from initial app launch
/// through login, registration, and session management. Uses a state machine pattern
/// to ensure predictable auth flow.
///
/// ## Architecture
/// - **Thread Safety**: `@MainActor` isolated - all UI updates happen on main thread
/// - **Observation**: Uses `@Observable` macro for SwiftUI reactivity
/// - **Singleton**: Access via `AuthStore.shared`
///
/// ## Auth State Machine
/// ```
/// .welcome ─────┬──► .register ──► .setupWizard ──► .authenticated
///               │                        │                ▲
///               └──► .login ─────────────┴────────────────┘
///                        │
///                        ▼
///                   (Invalid token)
///                        │
///                        ▼
///                    .welcome
/// ```
///
/// ## Token Storage
/// - JWT tokens stored in Keychain via `KeychainService`
/// - Automatic token refresh handled by `ApiClient`
/// - `bootstrap()` validates existing token on app launch
///
/// ## Debug Mode (DEBUG builds only)
/// - Supports auto-login via environment variables:
///   - `DEV_USERNAME` - Username for auto-login
///   - `DEV_PASSWORD` - Password for auto-login
/// - Never hardcoded - only from Xcode scheme environment
///
/// ## Dependencies
/// - `KeychainService` - Secure token storage
/// - `ApiClient` - HTTP requests and token management
///
/// ## Usage
/// ```swift
/// // Bootstrap on app launch
/// await AuthStore.shared.bootstrap()
///
/// // Check auth state
/// switch AuthStore.shared.authState {
/// case .authenticated:
///     // Show main app
/// case .welcome:
///     // Show login/register
/// }
///
/// // Login
/// await AuthStore.shared.login(username: "user", password: "pass")
///
/// // Logout
/// AuthStore.shared.logout()
/// ```
@MainActor
@Observable
final class AuthStore {
    static let shared = AuthStore()

    // MARK: - Observable State

    private(set) var authState: AuthState = .welcome
    private(set) var user: ApiUser?
    private(set) var userSetupComplete: Bool?
    private(set) var loading = false
    private(set) var error: String?

    private let keychain = KeychainService.shared
    private let apiClient = ApiClient.shared

    private init() {}

    // MARK: - Bootstrap Flow

    /// Call on app launch to validate existing token
    func bootstrap() async {
        // Wait for backend to be ready before attempting auth
        logger.debug("Waiting for backend to be ready...")
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
            logger.warning("Backend not ready after 7.5 seconds, will retry auth later")
            authState = .welcome
            loading = false
            return
        }

        logger.info("Backend is ready, proceeding with auth")

        // DEVELOPMENT BYPASS: Auto-login for fast iteration
        // Set DEV_USERNAME and DEV_PASSWORD environment variables in Xcode scheme
        #if DEBUG
        // Check if we already have a valid token
        if keychain.loadToken() != nil {
            do {
                let user: ApiUser = try await apiClient.request("/v1/auth/me")
                self.user = user
                userSetupComplete = true
                authState = .authenticated
                loading = false
                return
            } catch {
                logger.debug("Existing token invalid, will attempt auto-login if env vars set")
            }
        }

        // Auto-login only if environment variables are set (never hardcode credentials)
        if let devUsername = ProcessInfo.processInfo.environment["DEV_USERNAME"],
           let devPassword = ProcessInfo.processInfo.environment["DEV_PASSWORD"],
           !devUsername.isEmpty, !devPassword.isEmpty {

            logger.warning("DEBUG MODE: Auto-login using environment credentials")

            do {
                struct LoginRequest: Codable, Sendable {
                    let username: String
                    let password: String
                }

                struct LoginResponse: Codable, Sendable {
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
                    body: LoginRequest(username: devUsername, password: devPassword),
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
                logger.info("DEBUG: Auto-login successful")
                return

            } catch {
                logger.warning("DEBUG: Auto-login failed: \(error.localizedDescription) - Falling through to normal auth flow")
            }
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

    /// Lock the app without clearing credentials — shows welcome screen for re-authentication
    /// Used by auto-lock idle detection. Biometric auto-login remains available.
    func lock() {
        authState = .welcome
    }

    /// Set error message
    func setError(_ message: String?) {
        self.error = message
    }

    // MARK: - Helpers

    private func clearAuthAndRestart() async {
        do {
            try keychain.deleteToken()
        } catch {
            logger.warning("Failed to delete auth token on logout: \(error)")
        }
        user = nil
        userSetupComplete = nil
        authState = .welcome
        loading = false
        error = nil
    }

    private func checkBackendHealth() async -> Bool {
        guard let url = URL(string: APIConfiguration.shared.healthURL) else { return false }

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
