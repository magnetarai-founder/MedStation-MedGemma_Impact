//
//  UserStore.swift
//  MagnetarStudio
//
//  User authentication and session management.
//  Observable store for SwiftUI integration.
//

import Foundation
import Observation

@Observable
final class UserStore {
    // Published state
    var user: User?
    var isAuthenticated: Bool = false
    var isLoading: Bool = false
    var error: AuthError?

    // Dependencies (not observed)
    @ObservationIgnored
    private let apiClient: APIClient

    @ObservationIgnored
    private let keychain: KeychainManager

    init(
        apiClient: APIClient = .shared,
        keychain: KeychainManager = .shared
    ) {
        self.apiClient = apiClient
        self.keychain = keychain
    }

    // MARK: - Authentication Methods

    @MainActor
    func login(username: String, password: String) async throws {
        isLoading = true
        error = nil
        defer { isLoading = false }

        // Trim whitespace from credentials
        let trimmedUsername = username.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedPassword = password.trimmingCharacters(in: .whitespacesAndNewlines)

        print("🔐 Attempting login with username: '\(trimmedUsername)'")

        do {
            let response = try await apiClient.login(username: trimmedUsername, password: trimmedPassword)

            // Store tokens in Keychain (biometric-protected)
            try keychain.store(token: response.token, for: "jwt_token")
            try keychain.store(token: response.refreshToken, for: "jwt_refresh_token")

            // Update state
            self.user = response.toUserDTO().toModel()
            self.isAuthenticated = true

        } catch {
            self.error = .loginFailed(error.localizedDescription)
            throw error
        }
    }

    @MainActor
    func register(username: String, password: String, email: String?) async throws {
        isLoading = true
        error = nil
        defer { isLoading = false }

        do {
            let response = try await apiClient.register(
                username: username,
                password: password,
                email: email
            )

            // Store tokens
            try keychain.store(token: response.token, for: "jwt_token")
            try keychain.store(token: response.refreshToken, for: "jwt_refresh_token")

            // Update state
            self.user = response.toUserDTO().toModel()
            self.isAuthenticated = true

        } catch {
            self.error = .registrationFailed(error.localizedDescription)
            throw error
        }
    }

    @MainActor
    func logout() async {
        isLoading = true
        defer { isLoading = false }

        // Call backend logout
        try? await apiClient.logout()

        // Clear keychain
        try? keychain.delete(for: "jwt_token")
        try? keychain.delete(for: "jwt_refresh_token")

        // Clear state
        self.user = nil
        self.isAuthenticated = false
        self.error = nil
    }

    @MainActor
    func checkSession() async {
        // Try to load token from keychain
        guard let token = try? keychain.retrieve(for: "jwt_token") else {
            // No token found
            self.isAuthenticated = false
            return
        }

        isLoading = true
        defer { isLoading = false }

        do {
            // Validate token with backend
            let userDTO = try await apiClient.validateToken(token)
            self.user = userDTO.toModel()
            self.isAuthenticated = true
        } catch {
            // Token invalid or expired, try refresh
            await refreshSession()
        }
    }

    @MainActor
    private func refreshSession() async {
        guard let refreshToken = try? keychain.retrieve(for: "jwt_refresh_token") else {
            // No refresh token, user needs to log in again
            self.isAuthenticated = false
            return
        }

        do {
            let response = try await apiClient.refreshToken(refreshToken)

            // Store new tokens
            try keychain.store(token: response.token, for: "jwt_token")
            try keychain.store(token: response.refreshToken, for: "jwt_refresh_token")

            // Re-check session with new token
            await checkSession()

        } catch {
            // Refresh failed, user needs to log in again
            self.isAuthenticated = false
            try? keychain.delete(for: "jwt_token")
            try? keychain.delete(for: "jwt_refresh_token")
        }
    }
}

// MARK: - Error Types

enum AuthError: LocalizedError {
    case loginFailed(String)
    case registrationFailed(String)
    case sessionExpired
    case biometricsUnavailable
    case unknown

    var errorDescription: String? {
        switch self {
        case .loginFailed(let message):
            return "Login failed: \(message)"
        case .registrationFailed(let message):
            return "Registration failed: \(message)"
        case .sessionExpired:
            return "Your session has expired. Please log in again."
        case .biometricsUnavailable:
            return "Biometric authentication is not available on this device"
        case .unknown:
            return "An unknown error occurred"
        }
    }
}
