//
//  VaultPermissionManager.swift
//  MagnetarStudio
//
//  CRITICAL: Vault file permission management - LIFE OR DEATH for persecuted church
//  Models see METADATA ONLY. File contents require EXPLICIT permission EVERY TIME.
//
//  Part of Noah's Ark for the Digital Age - Protecting God's people
//  Foundation: Matthew 7:24-25 - Built on the rock, not sand
//

import Foundation
import LocalAuthentication

// MARK: - File Permission

/// Active file permission granted to a model
struct VaultFilePermission: Identifiable, Codable {
    let id: UUID
    let fileId: String
    let fileName: String
    let filePath: String
    let vaultType: String  // "real" or "decoy"
    let modelId: String
    let modelName: String
    let sessionId: String
    let grantedAt: Date
    let expiresAt: Date?  // nil = "just this time", Date = "for this session"

    var isExpired: Bool {
        guard let expires = expiresAt else {
            return true  // "Just this time" permissions expire immediately
        }
        return Date() > expires
    }

    var scope: String {
        expiresAt == nil ? "Just this time" : "For this session"
    }
}

// MARK: - Permission Request

/// Request from model to access a file
struct FileAccessRequest: Identifiable {
    let id = UUID()
    let fileId: String
    let fileName: String
    let filePath: String
    let vaultType: String
    let modelId: String
    let modelName: String
    let sessionId: String
    let requestedAt: Date
    let reason: String?  // Why does the model want access?
}

// MARK: - Permission Response

enum PermissionResponse {
    case justThisTime  // Single-use permission (expires immediately)
    case forThisSession  // Session-scoped permission (expires when session ends)
    case denied  // Access denied
    case cancelled  // User cancelled the dialog
}

// MARK: - Vault Permission Manager

/// CRITICAL: Manages file permissions for vault files
/// SECURITY: Models see metadata ONLY. File contents require explicit permission.
@MainActor
class VaultPermissionManager: ObservableObject {
    static let shared = VaultPermissionManager()

    @Published var activePermissions: [VaultFilePermission] = []
    @Published var auditLog: [FileAccessAudit] = []
    @Published var showPermissionModal: Bool = false
    @Published var pendingRequest: FileAccessRequest? = nil

    // Authentication
    private let context = LAContext()

    // Callbacks
    private var permissionCallback: ((PermissionResponse) -> Void)?

    private init() {
        loadActivePermissions()
        loadAuditLog()

        // Cleanup expired permissions every minute
        Timer.scheduledTimer(withTimeInterval: 60, repeats: true) { [weak self] _ in
            Task { @MainActor in
                self?.cleanupExpiredPermissions()
            }
        }
    }

    // MARK: - Permission Request Flow

    /// Request access to a vault file (BLOCKING - shows modal)
    /// Returns permission response after user decision
    func requestFileAccess(
        fileId: String,
        fileName: String,
        filePath: String,
        vaultType: String,
        modelId: String,
        modelName: String,
        sessionId: String,
        reason: String? = nil
    ) async -> PermissionResponse {
        // Check if permission already exists
        if let existing = activePermissions.first(where: {
            $0.fileId == fileId &&
            $0.modelId == modelId &&
            $0.sessionId == sessionId &&
            !$0.isExpired
        }) {
            print("✓ Using existing permission for \(fileName) (scope: \(existing.scope))")
            return existing.expiresAt == nil ? .justThisTime : .forThisSession
        }

        // Create request
        let request = FileAccessRequest(
            fileId: fileId,
            fileName: fileName,
            filePath: filePath,
            vaultType: vaultType,
            modelId: modelId,
            modelName: modelName,
            sessionId: sessionId,
            requestedAt: Date(),
            reason: reason
        )

        // Show blocking modal
        return await withCheckedContinuation { continuation in
            pendingRequest = request
            showPermissionModal = true

            permissionCallback = { [weak self] response in
                self?.showPermissionModal = false
                self?.pendingRequest = nil
                self?.permissionCallback = nil
                continuation.resume(returning: response)
            }
        }
    }

    /// Grant permission (called from modal)
    func grantPermission(scope: PermissionResponse, requireAuth: Bool = true) async {
        guard let request = pendingRequest else { return }

        // Authenticate if required
        if requireAuth {
            let authenticated = await authenticateUser()
            if !authenticated {
                permissionCallback?(.denied)
                recordAudit(request: request, granted: false, reason: "Authentication failed")
                return
            }
        }

        // Create permission
        let permission = VaultFilePermission(
            id: UUID(),
            fileId: request.fileId,
            fileName: request.fileName,
            filePath: request.filePath,
            vaultType: request.vaultType,
            modelId: request.modelId,
            modelName: request.modelName,
            sessionId: request.sessionId,
            grantedAt: Date(),
            expiresAt: scope == .forThisSession ? Date().addingTimeInterval(3600) : nil  // 1 hour
        )

        activePermissions.append(permission)
        saveActivePermissions()

        permissionCallback?(scope)
        recordAudit(request: request, granted: true, reason: scope == .justThisTime ? "Just this time" : "For this session")

        print("✓ Permission granted: \(request.fileName) (\(scope == .justThisTime ? "just this time" : "for this session"))")
    }

    /// Deny permission (called from modal)
    func denyPermission() {
        guard let request = pendingRequest else { return }

        permissionCallback?(.denied)
        recordAudit(request: request, granted: false, reason: "User denied")

        print("✗ Permission denied: \(request.fileName)")
    }

    /// Cancel permission request (called from modal)
    func cancelPermission() {
        permissionCallback?(.cancelled)
    }

    // MARK: - Permission Management

    /// Revoke a specific permission
    func revokePermission(_ permission: VaultFilePermission) {
        activePermissions.removeAll { $0.id == permission.id }
        saveActivePermissions()

        recordAudit(
            fileId: permission.fileId,
            fileName: permission.fileName,
            modelId: permission.modelId,
            action: "Permission revoked",
            granted: false,
            reason: "Manual revocation"
        )

        print("✓ Permission revoked: \(permission.fileName) for model \(permission.modelName)")
    }

    /// Revoke ALL permissions (emergency button)
    func revokeAllPermissions() {
        let count = activePermissions.count
        activePermissions.removeAll()
        saveActivePermissions()

        recordAudit(
            fileId: "ALL",
            fileName: "ALL FILES",
            modelId: "ALL",
            action: "EMERGENCY: All permissions revoked",
            granted: false,
            reason: "User revoked all permissions"
        )

        print("🚨 EMERGENCY: All \(count) permissions revoked")
    }

    /// Cleanup expired permissions
    private func cleanupExpiredPermissions() {
        let before = activePermissions.count
        activePermissions.removeAll { $0.isExpired }
        let after = activePermissions.count

        if before != after {
            saveActivePermissions()
            print("✓ Cleaned up \(before - after) expired permissions")
        }
    }

    // MARK: - Authentication

    /// Authenticate user with TouchID or password
    private func authenticateUser() async -> Bool {
        // Check if biometric auth is available
        var error: NSError?
        guard context.canEvaluatePolicy(.deviceOwnerAuthentication, error: &error) else {
            print("✗ Biometric auth not available: \(error?.localizedDescription ?? "Unknown error")")
            return false
        }

        do {
            let reason = "Authenticate to grant file access to AI model"
            let success = try await context.evaluatePolicy(.deviceOwnerAuthentication, localizedReason: reason)
            return success
        } catch {
            print("✗ Authentication failed: \(error.localizedDescription)")
            return false
        }
    }

    // MARK: - Audit Logging

    /// Record file access audit entry
    private func recordAudit(
        request: FileAccessRequest,
        granted: Bool,
        reason: String
    ) {
        recordAudit(
            fileId: request.fileId,
            fileName: request.fileName,
            modelId: request.modelId,
            action: granted ? "Access granted" : "Access denied",
            granted: granted,
            reason: reason
        )
    }

    private func recordAudit(
        fileId: String,
        fileName: String,
        modelId: String,
        action: String,
        granted: Bool,
        reason: String
    ) {
        let audit = FileAccessAudit(
            fileId: fileId,
            fileName: fileName,
            modelId: modelId,
            action: action,
            granted: granted,
            reason: reason,
            timestamp: Date()
        )

        auditLog.insert(audit, at: 0)  // Most recent first

        // Keep only last 1000 entries
        if auditLog.count > 1000 {
            auditLog = Array(auditLog.prefix(1000))
        }

        saveAuditLog()
    }

    // MARK: - Persistence

    private var permissionsURL: URL {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("MagnetarStudio")
            .appendingPathComponent("vault_permissions.json")
    }

    private var auditLogURL: URL {
        FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("MagnetarStudio")
            .appendingPathComponent("vault_audit.json")
    }

    private func loadActivePermissions() {
        guard FileManager.default.fileExists(atPath: permissionsURL.path) else { return }

        do {
            let data = try Data(contentsOf: permissionsURL)
            activePermissions = try JSONDecoder().decode([VaultFilePermission].self, from: data)

            // Remove expired on load
            activePermissions.removeAll { $0.isExpired }
        } catch {
            print("Failed to load permissions: \(error)")
        }
    }

    private func saveActivePermissions() {
        do {
            let dir = permissionsURL.deletingLastPathComponent()
            try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)

            let data = try JSONEncoder().encode(activePermissions)
            try data.write(to: permissionsURL)
        } catch {
            print("Failed to save permissions: \(error)")
        }
    }

    private func loadAuditLog() {
        guard FileManager.default.fileExists(atPath: auditLogURL.path) else { return }

        do {
            let data = try Data(contentsOf: auditLogURL)
            auditLog = try JSONDecoder().decode([FileAccessAudit].self, from: data)
        } catch {
            print("Failed to load audit log: \(error)")
        }
    }

    private func saveAuditLog() {
        do {
            let dir = auditLogURL.deletingLastPathComponent()
            try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)

            let data = try JSONEncoder().encode(auditLog)
            try data.write(to: auditLogURL)
        } catch {
            print("Failed to save audit log: \(error)")
        }
    }
}

// MARK: - Audit Entry

struct FileAccessAudit: Identifiable, Codable {
    var id: UUID = UUID()
    let fileId: String
    let fileName: String
    let modelId: String
    let action: String
    let granted: Bool
    let reason: String
    let timestamp: Date

    enum CodingKeys: String, CodingKey {
        case fileId, fileName, modelId, action, granted, reason, timestamp
    }
}
