//
//  HubCloudManager.swift
//  MagnetarStudio (macOS)
//
//  Cloud authentication manager - Handles MagnetarCloud sync authentication
//
//  Security (Dec 2025):
//  - Cloud tokens stored in Keychain (separate from local JWT)
//  - Device fingerprint prevents token reuse on different devices
//  - 7-day token expiry with 30-day refresh token
//  - Automatic token refresh before expiry
//

import SwiftUI
import CryptoKit

@MainActor
@Observable
class HubCloudManager {
    // MARK: - Published State

    var cloudModels: [OllamaModel] = []
    var isCloudAuthenticated: Bool = false
    var isLoadingCloud: Bool = false
    var isCloudActionInProgress: Bool = false
    var cloudUsername: String? = nil
    var cloudDeviceId: String? = nil
    var tokenExpiresAt: Date? = nil
    var lastSyncAt: Date? = nil
    var pairedDevices: [CloudDeviceInfo] = []
    var errorMessage: String? = nil

    // Sync status (Tier 15)
    var syncStatus: SyncStatusInfo? = nil
    var isSyncing: Bool = false
    var pendingSyncChanges: Int = 0
    var activeConflicts: Int = 0

    // MARK: - Private Properties

    private let apiClient = ApiClient.shared
    private let keychain = KeychainService.shared

    // Keychain keys for cloud credentials
    private let cloudTokenKey = "magnetar.cloud_token"
    private let cloudRefreshTokenKey = "magnetar.cloud_refresh_token"
    private let cloudDeviceIdKey = "magnetar.cloud_device_id"
    private let cloudExpiryKey = "magnetar.cloud_token_expiry"

    // MARK: - Initialization

    init() {
        // Load cached cloud state from Keychain
        loadCachedCloudState()
    }

    // MARK: - Public Methods

    /// Connect to MagnetarCloud (pair device)
    func connectCloud() async {
        isCloudActionInProgress = true
        errorMessage = nil

        defer { isCloudActionInProgress = false }

        do {
            // Generate device fingerprint from hardware ID
            let deviceFingerprint = generateDeviceFingerprint()
            let deviceId = AuthService.shared.deviceId

            let request = CloudPairRequest(
                deviceId: deviceId,
                deviceName: Host.current().localizedName ?? "Mac",
                devicePlatform: "macos",
                deviceFingerprint: deviceFingerprint
            )

            let response: CloudPairResponseWrapper = try await apiClient.request(
                "/v1/cloud/pair",
                method: .post,
                body: request
            )

            // Store cloud credentials securely
            try keychain.saveToken(response.data.cloudToken, forKey: cloudTokenKey)
            try keychain.saveToken(response.data.cloudRefreshToken, forKey: cloudRefreshTokenKey)
            try keychain.saveToken(response.data.cloudDeviceId, forKey: cloudDeviceIdKey)
            try keychain.saveToken(response.data.expiresAt, forKey: cloudExpiryKey)

            // Update state
            isCloudAuthenticated = true
            cloudUsername = response.data.username
            cloudDeviceId = response.data.cloudDeviceId
            tokenExpiresAt = ISO8601DateFormatter().date(from: response.data.expiresAt)

            print("MagnetarCloud connected: \(response.data.cloudDeviceId)")

            // Fetch paired devices
            await refreshCloudStatus()

        } catch {
            errorMessage = "Failed to connect: \(error.localizedDescription)"
            print("MagnetarCloud connection failed: \(error)")
        }
    }

    /// Disconnect from MagnetarCloud (unpair device)
    func disconnectCloud() async {
        isCloudActionInProgress = true
        errorMessage = nil

        defer { isCloudActionInProgress = false }

        do {
            guard let deviceId = cloudDeviceId else {
                clearCloudState()
                return
            }

            let _: CloudUnpairResponseWrapper = try await apiClient.request(
                "/v1/cloud/unpair?cloud_device_id=\(deviceId)",
                method: .post
            )

            clearCloudState()
            print("MagnetarCloud disconnected")

        } catch {
            // Even if API fails, clear local state
            clearCloudState()
            print("MagnetarCloud disconnect (forced): \(error)")
        }
    }

    /// Reconnect to MagnetarCloud (refresh token)
    func reconnectCloud() async {
        isCloudActionInProgress = true
        errorMessage = nil

        defer { isCloudActionInProgress = false }

        do {
            // Try to refresh token
            guard let refreshToken = keychain.loadToken(forKey: cloudRefreshTokenKey),
                  let deviceId = keychain.loadToken(forKey: cloudDeviceIdKey) else {
                // No cached credentials, need full reconnect
                await connectCloud()
                return
            }

            let request = CloudTokenRefreshRequest(
                cloudDeviceId: deviceId,
                refreshToken: refreshToken
            )

            let response: CloudTokenRefreshResponseWrapper = try await apiClient.request(
                "/v1/cloud/refresh",
                method: .post,
                body: request,
                authenticated: false  // Refresh uses refresh token, not JWT
            )

            // Update stored token
            try keychain.saveToken(response.data.cloudToken, forKey: cloudTokenKey)
            try keychain.saveToken(response.data.expiresAt, forKey: cloudExpiryKey)

            tokenExpiresAt = ISO8601DateFormatter().date(from: response.data.expiresAt)
            isCloudAuthenticated = true

            print("MagnetarCloud token refreshed")

            // Refresh status
            await refreshCloudStatus()

        } catch {
            errorMessage = "Failed to reconnect: \(error.localizedDescription)"
            print("MagnetarCloud reconnect failed: \(error)")

            // If refresh fails, need full re-auth
            clearCloudState()
        }
    }

    /// Refresh cloud status (paired devices, last sync, etc.)
    func refreshCloudStatus() async {
        do {
            let response: CloudStatusResponseWrapper = try await apiClient.request(
                "/v1/cloud/status",
                method: .get
            )

            isCloudAuthenticated = response.data.isPaired
            cloudDeviceId = response.data.cloudDeviceId
            cloudUsername = response.data.username

            if let expiresStr = response.data.tokenExpiresAt {
                tokenExpiresAt = ISO8601DateFormatter().date(from: expiresStr)
            }

            if let syncStr = response.data.lastSyncAt {
                lastSyncAt = ISO8601DateFormatter().date(from: syncStr)
            }

            pairedDevices = response.data.pairedDevices

        } catch {
            print("Failed to refresh cloud status: \(error)")
        }
    }

    /// Check if token needs refresh (< 1 day until expiry)
    func checkAndRefreshTokenIfNeeded() async {
        guard isCloudAuthenticated,
              let expiry = tokenExpiresAt else { return }

        let oneDayFromNow = Date().addingTimeInterval(86400)

        if expiry < oneDayFromNow {
            print("Cloud token expiring soon, refreshing...")
            await reconnectCloud()
        }
    }

    /// Revoke all cloud sessions (emergency)
    func revokeAllSessions() async {
        isCloudActionInProgress = true

        defer { isCloudActionInProgress = false }

        do {
            let _: CloudRevokeResponseWrapper = try await apiClient.request(
                "/v1/cloud/sessions",
                method: .delete
            )

            clearCloudState()
            print("All cloud sessions revoked")

        } catch {
            errorMessage = "Failed to revoke sessions: \(error.localizedDescription)"
            print("Cloud session revoke failed: \(error)")
        }
    }

    // MARK: - Sync Methods (Tier 15)

    /// Refresh sync status from SyncService
    func refreshSyncStatus() async {
        guard isCloudAuthenticated else { return }

        do {
            let status = try await SyncService.shared.fetchStatus()

            syncStatus = SyncStatusInfo(
                isConnected: status.isConnected,
                lastSyncAt: status.lastSyncAt,
                pendingChanges: status.pendingChanges,
                activeConflicts: status.activeConflicts
            )
            pendingSyncChanges = status.pendingChanges
            activeConflicts = status.activeConflicts

            if let syncTime = status.lastSyncAt {
                lastSyncAt = ISO8601DateFormatter().date(from: syncTime)
            }
        } catch {
            print("Failed to refresh sync status: \(error)")
        }
    }

    /// Trigger a manual sync
    func triggerSync() async {
        guard isCloudAuthenticated else {
            errorMessage = "Not connected to MagnetarCloud"
            return
        }

        isSyncing = true
        errorMessage = nil

        do {
            try await SyncService.shared.triggerSync()
            await refreshSyncStatus()
            print("Manual sync completed")
        } catch {
            errorMessage = "Sync failed: \(error.localizedDescription)"
            print("Manual sync failed: \(error)")
        }

        isSyncing = false
    }

    /// Start automatic background sync
    func startAutoSync(intervalSeconds: TimeInterval = 300) {
        guard isCloudAuthenticated else { return }
        SyncService.shared.startAutoSync(intervalSeconds: intervalSeconds)
    }

    /// Stop automatic background sync
    func stopAutoSync() {
        SyncService.shared.stopAutoSync()
    }

    // MARK: - Private Methods

    /// Load cached cloud state from Keychain
    private func loadCachedCloudState() {
        if let token = keychain.loadToken(forKey: cloudTokenKey),
           let deviceId = keychain.loadToken(forKey: cloudDeviceIdKey),
           let expiryStr = keychain.loadToken(forKey: cloudExpiryKey) {

            let expiry = ISO8601DateFormatter().date(from: expiryStr)

            // Check if token is still valid
            if let exp = expiry, exp > Date() {
                isCloudAuthenticated = true
                cloudDeviceId = deviceId
                tokenExpiresAt = expiry

                // Fetch full status in background
                Task {
                    await refreshCloudStatus()
                }
            } else {
                // Token expired, try to refresh
                Task {
                    await reconnectCloud()
                }
            }
        }
    }

    /// Clear all cloud state
    private func clearCloudState() {
        try? keychain.deleteToken(forKey: cloudTokenKey)
        try? keychain.deleteToken(forKey: cloudRefreshTokenKey)
        try? keychain.deleteToken(forKey: cloudDeviceIdKey)
        try? keychain.deleteToken(forKey: cloudExpiryKey)

        isCloudAuthenticated = false
        cloudUsername = nil
        cloudDeviceId = nil
        tokenExpiresAt = nil
        lastSyncAt = nil
        pairedDevices = []
        cloudModels = []
    }

    /// Generate device fingerprint from hardware ID
    private func generateDeviceFingerprint() -> String {
        // Use IOKit to get hardware UUID
        var hardwareUUID = "unknown"

        let platformExpert = IOServiceGetMatchingService(
            kIOMainPortDefault,
            IOServiceMatching("IOPlatformExpertDevice")
        )

        if platformExpert != 0 {
            if let serialNumber = IORegistryEntryCreateCFProperty(
                platformExpert,
                "IOPlatformUUID" as CFString,
                kCFAllocatorDefault,
                0
            )?.takeRetainedValue() as? String {
                hardwareUUID = serialNumber
            }
            IOObjectRelease(platformExpert)
        }

        // Hash the hardware UUID for privacy
        let hash = SHA256.hash(data: Data(hardwareUUID.utf8))
        return hash.map { String(format: "%02x", $0) }.joined()
    }
}

// MARK: - API Models

private struct CloudPairRequest: Codable {
    let deviceId: String
    let deviceName: String?
    let devicePlatform: String?
    let deviceFingerprint: String

    enum CodingKeys: String, CodingKey {
        case deviceId = "device_id"
        case deviceName = "device_name"
        case devicePlatform = "device_platform"
        case deviceFingerprint = "device_fingerprint"
    }
}

private struct CloudPairResponse: Codable {
    let cloudDeviceId: String
    let cloudToken: String
    let cloudRefreshToken: String
    let expiresAt: String
    let username: String

    enum CodingKeys: String, CodingKey {
        case cloudDeviceId = "cloud_device_id"
        case cloudToken = "cloud_token"
        case cloudRefreshToken = "cloud_refresh_token"
        case expiresAt = "expires_at"
        case username
    }
}

private struct CloudPairResponseWrapper: Codable {
    let success: Bool
    let data: CloudPairResponse
    let message: String
}

private struct CloudTokenRefreshRequest: Codable {
    let cloudDeviceId: String
    let refreshToken: String

    enum CodingKeys: String, CodingKey {
        case cloudDeviceId = "cloud_device_id"
        case refreshToken = "refresh_token"
    }
}

private struct CloudTokenRefreshResponse: Codable {
    let cloudToken: String
    let expiresAt: String

    enum CodingKeys: String, CodingKey {
        case cloudToken = "cloud_token"
        case expiresAt = "expires_at"
    }
}

private struct CloudTokenRefreshResponseWrapper: Codable {
    let success: Bool
    let data: CloudTokenRefreshResponse
    let message: String
}

struct CloudDeviceInfo: Codable, Identifiable {
    let cloudDeviceId: String
    let deviceName: String?
    let devicePlatform: String?
    let createdAt: String
    let lastSyncAt: String?
    let isActive: Bool

    var id: String { cloudDeviceId }

    enum CodingKeys: String, CodingKey {
        case cloudDeviceId = "cloud_device_id"
        case deviceName = "device_name"
        case devicePlatform = "device_platform"
        case createdAt = "created_at"
        case lastSyncAt = "last_sync_at"
        case isActive = "is_active"
    }
}

private struct CloudStatusResponse: Codable {
    let isPaired: Bool
    let cloudDeviceId: String?
    let username: String?
    let tokenExpiresAt: String?
    let lastSyncAt: String?
    let pairedDevices: [CloudDeviceInfo]

    enum CodingKeys: String, CodingKey {
        case isPaired = "is_paired"
        case cloudDeviceId = "cloud_device_id"
        case username
        case tokenExpiresAt = "token_expires_at"
        case lastSyncAt = "last_sync_at"
        case pairedDevices = "paired_devices"
    }
}

private struct CloudStatusResponseWrapper: Codable {
    let success: Bool
    let data: CloudStatusResponse
    let message: String
}

private struct CloudUnpairResponse: Codable {
    let unpaired: Bool
    let cloudDeviceId: String

    enum CodingKeys: String, CodingKey {
        case unpaired
        case cloudDeviceId = "cloud_device_id"
    }
}

private struct CloudUnpairResponseWrapper: Codable {
    let success: Bool
    let data: CloudUnpairResponse
    let message: String
}

private struct CloudRevokeResponse: Codable {
    let revoked: Bool
    let devicesAffected: Int

    enum CodingKeys: String, CodingKey {
        case revoked
        case devicesAffected = "devices_affected"
    }
}

private struct CloudRevokeResponseWrapper: Codable {
    let success: Bool
    let data: CloudRevokeResponse
    let message: String
}

// MARK: - Sync Status Model (Tier 15)

struct SyncStatusInfo {
    let isConnected: Bool
    let lastSyncAt: String?
    let pendingChanges: Int
    let activeConflicts: Int

    var formattedLastSync: String {
        guard let syncStr = lastSyncAt,
              let date = ISO8601DateFormatter().date(from: syncStr) else {
            return "Never"
        }

        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: date, relativeTo: Date())
    }

    var statusColor: NSColor {
        if activeConflicts > 0 {
            return .systemOrange
        } else if pendingChanges > 0 {
            return .systemYellow
        } else if isConnected {
            return .systemGreen
        } else {
            return .systemGray
        }
    }

    var statusText: String {
        if activeConflicts > 0 {
            return "\(activeConflicts) conflict\(activeConflicts == 1 ? "" : "s")"
        } else if pendingChanges > 0 {
            return "\(pendingChanges) pending"
        } else if isConnected {
            return "Synced"
        } else {
            return "Disconnected"
        }
    }
}

// MARK: - Extension for AuthService access

extension AuthService {
    var deviceId: String {
        // Access the private deviceId via Keychain
        KeychainService.shared.loadToken(forKey: "magnetar.device_id") ?? UUID().uuidString
    }
}
