//
//  MagnetarCloudSettingsView.swift
//  MagnetarStudio
//
//  Settings panel for MagnetarCloud authentication and sync.
//

import SwiftUI
import AppKit
import Observation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "MagnetarCloudSettings")

// MARK: - MagnetarCloud Settings

struct MagnetarCloudSettingsView: View {
    @State private var authManager = CloudAuthManager.shared
    @State private var syncService = SyncService.shared
    @State private var syncEnabled: Bool = UserDefaults.standard.bool(forKey: "cloudSyncEnabled")
    @State private var isSyncingNow: Bool = false
    @State private var syncError: String?
    private let subscriptionURL = URL(string: "https://billing.magnetar.studio")

    var body: some View {
        Form {
            if !authManager.isAuthenticated {
                // Not authenticated
                Section {
                    VStack(alignment: .leading, spacing: 16) {
                        HStack(spacing: 12) {
                            Image(systemName: "cloud.fill")
                                .font(.system(size: 32))
                                .foregroundStyle(LinearGradient.magnetarGradient)

                            VStack(alignment: .leading, spacing: 4) {
                                Text("MagnetarCloud")
                                    .font(.headline)

                                Text("Sign in to sync across devices and access your models")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }

                        Button {
                            authManager.startAuthFlow()
                        } label: {
                            Label("Login to MagnetarCloud Account", systemImage: "person.circle")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.large)
                        .disabled(authManager.authStatus == .loading)
                    }
                    .padding(.vertical, 8)

                    // Auth status
                    statusLabel(authManager.authStatus)
                }

                Section("Features") {
                    Label("Sync chat sessions across devices", systemImage: "arrow.triangle.2.circlepath")
                    Label("Access your fine-tuned models", systemImage: "cube.box")
                    Label("Download model updates", systemImage: "arrow.down.circle")
                    Label("Priority support", systemImage: "headphones")
                }
                .foregroundStyle(.secondary)
                .font(.caption)
            } else {
                // Authenticated
                Section("Account") {
                    HStack {
                        Text("Email")
                        Spacer()
                        Text(authManager.cloudEmail)
                            .foregroundStyle(.secondary)
                    }

                    HStack {
                        Text("Plan")
                        Spacer()
                        Text(authManager.cloudPlan)
                            .foregroundStyle(Color.magnetarPrimary)
                    }

                    Button("Manage Subscription") {
                        openExternal(subscriptionURL)
                    }
                }

                Section("Sync") {
                    Toggle("Enable Cloud Sync", isOn: $syncEnabled)
                        .onChange(of: syncEnabled) { _, newValue in
                            handleSyncToggle(newValue)
                        }

                    Text("Sync vault, workflows, and team data across all your devices")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    if syncEnabled {
                        // Sync status row
                        HStack {
                            if syncService.isSyncing || isSyncingNow {
                                ProgressView()
                                    .scaleEffect(0.8)
                                    .padding(.trailing, 4)
                                Text("Syncing...")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            } else if let error = syncError {
                                Image(systemName: "exclamationmark.triangle.fill")
                                    .foregroundColor(.orange)
                                Text(error)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(1)
                            } else {
                                Image(systemName: "checkmark.circle.fill")
                                    .foregroundColor(.green)
                                Text(lastSyncText)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }

                            Spacer()

                            // Manual sync button
                            Button {
                                Task { await triggerManualSync() }
                            } label: {
                                Image(systemName: "arrow.triangle.2.circlepath")
                            }
                            .buttonStyle(.borderless)
                            .disabled(syncService.isSyncing || isSyncingNow)
                            .help("Sync now")
                        }

                        // Pending changes indicator
                        if syncService.pendingChanges > 0 {
                            HStack {
                                Image(systemName: "arrow.up.circle")
                                    .foregroundColor(.blue)
                                Text("\(syncService.pendingChanges) pending change\(syncService.pendingChanges == 1 ? "" : "s")")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }

                        // Conflicts indicator
                        if syncService.activeConflicts > 0 {
                            HStack {
                                Image(systemName: "exclamationmark.triangle")
                                    .foregroundColor(.orange)
                                Text("\(syncService.activeConflicts) conflict\(syncService.activeConflicts == 1 ? "" : "s") to resolve")
                                    .font(.caption)
                                    .foregroundStyle(.orange)
                            }
                        }
                    }
                }

                Section("Connected Devices") {
                    Label(Host.current().localizedName ?? "This Mac", systemImage: "laptopcomputer")

                    Text("1 device connected")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Section {
                    Button("Sign Out", role: .destructive) {
                        authManager.signOut()
                    }
                }
            }
        }
        .formStyle(.grouped)
        .padding()
        .onAppear {
            Task {
                await authManager.checkAuthStatus()
                // Start auto-sync if enabled and authenticated
                if syncEnabled && authManager.isAuthenticated {
                    syncService.startAutoSync()
                    await refreshSyncStatus()
                }
            }
        }
    }

    // MARK: - Computed Properties

    private var lastSyncText: String {
        guard let lastSync = syncService.lastSyncAt else {
            return "Not synced yet"
        }

        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return "Synced \(formatter.localizedString(for: lastSync, relativeTo: Date()))"
    }

    // MARK: - Actions

    private func handleSyncToggle(_ enabled: Bool) {
        UserDefaults.standard.set(enabled, forKey: "cloudSyncEnabled")

        if enabled {
            syncService.startAutoSync()
            Task { await refreshSyncStatus() }
        } else {
            syncService.stopAutoSync()
        }

        logger.info("Cloud sync \(enabled ? "enabled" : "disabled")")
    }

    private func triggerManualSync() async {
        isSyncingNow = true
        syncError = nil

        do {
            try await syncService.triggerSync()
            await refreshSyncStatus()
            logger.info("Manual sync completed")
        } catch let error as SyncError {
            syncError = error.localizedDescription
            logger.error("Manual sync failed: \(error.localizedDescription)")
        } catch {
            syncError = error.localizedDescription
            logger.error("Manual sync failed: \(error.localizedDescription)")
        }

        isSyncingNow = false
    }

    private func refreshSyncStatus() async {
        do {
            _ = try await syncService.fetchStatus()
            syncError = nil
        } catch {
            // Don't show error for status fetch - just log it
            logger.warning("Failed to fetch sync status: \(error)")
        }
    }

    private func openExternal(_ url: URL?) {
        guard let url else { return }
        NSWorkspace.shared.open(url)
    }
}

// MARK: - Cloud Auth Manager

/// Manages MagnetarCloud authentication, token storage, and profile
@MainActor
@Observable
final class CloudAuthManager {
    static let shared = CloudAuthManager()

    var isAuthenticated: Bool = false
    var cloudEmail: String = ""
    var cloudPlan: String = "Free"
    var authStatus: SimpleStatus = .idle

    private let authBaseURL = "https://auth.magnetar.studio"
    private let redirectURI = "magnetarstudio://auth/callback"
    private let apiClient = ApiClient.shared
    private let keychain = KeychainService.shared

    // Keychain keys - must match SyncService expectation
    private let cloudTokenKey = "cloud_access_token"

    private init() {}

    // MARK: - Auth Flow

    /// Start OAuth flow by opening browser
    func startAuthFlow() {
        authStatus = .idle

        guard var urlComponents = URLComponents(string: "\(authBaseURL)/login") else {
            authStatus = .failure("Invalid auth URL")
            return
        }

        urlComponents.queryItems = [
            URLQueryItem(name: "redirect_uri", value: redirectURI)
        ]

        guard let authURL = urlComponents.url else {
            authStatus = .failure("Failed to build auth URL")
            return
        }

        NSWorkspace.shared.open(authURL)
        authStatus = .loading
    }

    /// Handle OAuth callback with code
    func handleAuthCallback(url: URL) async {
        authStatus = .loading

        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
              let queryItems = components.queryItems else {
            authStatus = .failure("Invalid callback URL")
            return
        }

        // Extract code from query parameters
        guard let code = queryItems.first(where: { $0.name == "code" })?.value else {
            authStatus = .failure("Missing authorization code")
            return
        }

        // Exchange code for token
        await exchangeCodeForToken(code: code)
    }

    // MARK: - Token Exchange

    private func exchangeCodeForToken(code: String) async {
        do {
            struct TokenResponse: Decodable, Sendable {
                let accessToken: String
                let email: String
                let plan: String
            }

            let response: TokenResponse = try await apiClient.request(
                path: "/v1/auth/exchange",
                method: .post,
                jsonBody: [
                    "code": code,
                    "redirect_uri": redirectURI
                ],
                authenticated: false
            )

            // Store token in keychain
            try keychain.saveToken(response.accessToken, forKey: cloudTokenKey)

            // Update state
            isAuthenticated = true
            cloudEmail = response.email
            cloudPlan = response.plan
            authStatus = .success("Signed in as \(response.email)")

        } catch let error as ApiError {
            authStatus = .failure(error.localizedDescription)
            isAuthenticated = false
        } catch {
            authStatus = .failure("Exchange failed: \(error.localizedDescription)")
            isAuthenticated = false
        }
    }

    // MARK: - Check Auth Status

    /// Check if user has valid token and fetch profile
    func checkAuthStatus() async {
        // Check for existing token
        guard let token = keychain.loadToken(forKey: cloudTokenKey), !token.isEmpty else {
            isAuthenticated = false
            cloudEmail = ""
            cloudPlan = "Free"
            return
        }

        // Token exists - fetch profile to verify it's valid
        await fetchProfile()
    }

    private func fetchProfile() async {
        do {
            struct ProfileResponse: Decodable, Sendable {
                let email: String
                let plan: String
            }

            // Temporarily store token for this request
            let oldToken = keychain.loadToken()
            if let cloudToken = keychain.loadToken(forKey: cloudTokenKey) {
                try keychain.saveToken(cloudToken)
            }

            let profile: ProfileResponse = try await apiClient.request(
                path: "/v1/auth/profile",
                method: .get,
                authenticated: true
            )

            // Restore old token
            if let oldToken = oldToken {
                try keychain.saveToken(oldToken)
            }

            isAuthenticated = true
            cloudEmail = profile.email
            cloudPlan = profile.plan
            authStatus = .idle

        } catch {
            // Token invalid or expired
            isAuthenticated = false
            cloudEmail = ""
            cloudPlan = "Free"
            authStatus = .idle

            // Clear invalid token
            try? keychain.deleteToken(forKey: cloudTokenKey)
        }
    }

    // MARK: - Sign Out

    func signOut() {
        do {
            try keychain.deleteToken(forKey: cloudTokenKey)
            isAuthenticated = false
            cloudEmail = ""
            cloudPlan = "Free"
            authStatus = .idle
        } catch {
            authStatus = .failure("Sign out failed: \(error.localizedDescription)")
        }
    }
}
