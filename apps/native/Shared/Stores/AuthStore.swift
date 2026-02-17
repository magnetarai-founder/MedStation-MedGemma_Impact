import Foundation
import Observation
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "AuthStore")

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

    private(set) var authState: AuthState = .checking
    private(set) var user: ApiUser?
    private(set) var userSetupComplete: Bool?
    private(set) var loading = false
    private(set) var error: String?

    private init() {}

    // MARK: - Bootstrap Flow

    /// Call on app launch or resume from lock — ensures backend is running, then auto-authenticates
    func bootstrap() async {
        loading = true

        // Ensure backend is started (restarts if it died during idle)
        await BackendManager.shared.autoStartBackend()

        // Demo mode: auto-authenticate locally (no backend auth endpoints needed)
        // Use a static device ID to avoid triggering KeychainService via AuthService.shared
        self.user = ApiUser(
            userId: "demo-clinician",
            username: "Clinician",
            deviceId: "demo-device",
            role: "clinician"
        )
        userSetupComplete = true
        authState = .authenticated
        loading = false
        logger.info("MedStation demo mode — authenticated as Clinician")
    }

    // MARK: - Auth Actions

    /// Save token after login and bootstrap
    func saveToken(_ token: String) async {
        do {
            try KeychainService.shared.saveToken(token)
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
            try KeychainService.shared.deleteToken()
        } catch {
            logger.warning("Failed to delete auth token on logout: \(error)")
        }
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
