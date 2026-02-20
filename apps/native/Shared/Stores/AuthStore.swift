import Foundation
import Observation
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "AuthStore")

// MARK: - AuthStore

/// Auth state — demo mode (auto-authenticates as Clinician).
@MainActor
@Observable
final class AuthStore {
    static let shared = AuthStore()

    // MARK: - Observable State

    private(set) var authState: AuthState = .checking
    private(set) var user: ApiUser?

    private init() {}

    // MARK: - Bootstrap Flow

    /// Call on app launch or resume from lock — auto-authenticates
    func bootstrap() async {
        // Demo mode: auto-authenticate locally (no backend needed)
        self.user = ApiUser(
            userId: "demo-clinician",
            username: "Clinician",
            deviceId: "demo-device",
            role: "clinician"
        )
        authState = .authenticated
        logger.info("MedStation demo mode — authenticated as Clinician")
    }

    // MARK: - Auth Actions

    /// Lock and re-authenticate (demo mode — immediately re-bootstraps)
    func lock() {
        authState = .checking
        Task { await bootstrap() }
    }

}

// MARK: - Auth State

enum AuthState: Equatable {
    case checking       // Loading / bootstrapping
    case authenticated  // Ready
}
