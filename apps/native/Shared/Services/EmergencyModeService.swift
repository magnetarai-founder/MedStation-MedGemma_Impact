//
//  EmergencyModeService.swift
//  MagnetarStudio
//
//  CRITICAL: Emergency mode with DoD 7-pass wipe and self-uninstall
//  FOR PERSECUTION SCENARIOS ONLY
//
//  Safety: Week 1 is SIMULATION MODE ONLY - no actual file deletion
//

import Foundation
import AppKit

// MARK: - Emergency Mode Safety Configuration

/// CRITICAL SAFETY: Debug kill switch for emergency mode
/// Must be manually enabled for testing, disabled by default in debug builds
#if DEBUG
private let EMERGENCY_MODE_ENABLED = false  // ⚠️ SET TO true ONLY FOR VM TESTING
#else
private let EMERGENCY_MODE_ENABLED = true   // Production: Always enabled
#endif

// MARK: - Emergency Mode Service

/// Service for handling emergency panic mode (DoD wipe + self-uninstall)
/// This is the nuclear option for persecution scenarios
@MainActor
final class EmergencyModeService: ObservableObject {
    static let shared = EmergencyModeService()

    // MARK: - Published State

    @Published private(set) var isSimulationMode: Bool = true
    @Published private(set) var emergencyInProgress: Bool = false
    @Published private(set) var lastEmergencyReport: EmergencyWipeReport?

    // MARK: - Private State

    private let apiClient: ApiClient
    private let baseURL: String

    private init() {
        self.apiClient = .shared
        self.baseURL = "\(APIConfiguration.shared.versionedBaseURL)/panic"

        #if DEBUG
        self.isSimulationMode = true  // Always simulate in debug
        print("⚠️ EmergencyModeService: DEBUG MODE - Simulation only")
        #else
        self.isSimulationMode = false  // Real deletion in production
        #endif
    }

    // MARK: - Emergency Trigger

    /// Trigger emergency mode (DoD 7-pass wipe + self-uninstall)
    /// CRITICAL: This is IRREVERSIBLE in production
    func triggerEmergency(reason: String?, confirmationMethod: EmergencyTriggerMethod) async throws -> EmergencyWipeReport {
        // Safety check: Emergency mode must be enabled
        guard EMERGENCY_MODE_ENABLED else {
            throw EmergencyModeError.disabledInDebug
        }

        emergencyInProgress = true
        defer { emergencyInProgress = false }

        // Log emergency trigger BEFORE wiping (critical for audit)
        await logEmergencyTrigger(reason: reason, method: confirmationMethod)

        // Attempt to send emergency log to remote (if network available)
        try? await sendEmergencyLogToRemote(reason: reason)

        // Small delay to ensure log transmission
        try? await Task.sleep(nanoseconds: 1_000_000_000) // 1 second

        // Execute emergency wipe
        let report: EmergencyWipeReport

        if isSimulationMode {
            // SAFE: Simulation mode (Week 1)
            report = try await simulateEmergencyWipe(reason: reason)
        } else {
            // DANGEROUS: Real DoD 7-pass wipe (Production/VM testing)
            report = try await executeEmergencyWipe(reason: reason)
        }

        lastEmergencyReport = report
        return report
    }

    // MARK: - Simulation Mode (Week 1 - SAFE)

    /// Simulate emergency wipe without actually deleting files
    /// Week 1: This logs what WOULD be deleted
    private func simulateEmergencyWipe(reason: String?) async throws -> EmergencyWipeReport {
        print("🧪 SIMULATION MODE: Emergency wipe started")
        print("   Reason: \(reason ?? "User-initiated")")

        var report = EmergencyWipeReport(
            simulated: true,
            filesWiped: 0,
            passes: 7,
            durationSeconds: 0,
            errors: []
        )

        let startTime = Date()

        // 1. Identify vault databases
        let vaultFiles = await identifyVaultFiles()
        print("   📁 Would delete \(vaultFiles.count) vault files:")
        vaultFiles.forEach { print("      - \($0)") }
        report.filesIdentified.append(contentsOf: vaultFiles)

        // 2. Identify backups
        let backupFiles = await identifyBackupFiles()
        print("   📁 Would delete \(backupFiles.count) backup files:")
        backupFiles.forEach { print("      - \($0)") }
        report.filesIdentified.append(contentsOf: backupFiles)

        // 3. Identify models
        let modelFiles = await identifyModelFiles()
        print("   📁 Would delete \(modelFiles.count) model files:")
        modelFiles.forEach { print("      - \($0)") }
        report.filesIdentified.append(contentsOf: modelFiles)

        // 4. Identify cache
        let cacheFiles = await identifyCacheFiles()
        print("   📁 Would delete \(cacheFiles.count) cache files:")
        cacheFiles.forEach { print("      - \($0)") }
        report.filesIdentified.append(contentsOf: cacheFiles)

        // 5. Identify audit logs
        let auditFiles = await identifyAuditFiles()
        print("   📁 Would delete \(auditFiles.count) audit log files:")
        auditFiles.forEach { print("      - \($0)") }
        report.filesIdentified.append(contentsOf: auditFiles)

        // 6. Identify app bundle
        let appBundle = await identifyAppBundle()
        print("   📁 Would delete app bundle: \(appBundle)")
        report.filesIdentified.append(appBundle)

        report.filesWiped = report.filesIdentified.count
        report.durationSeconds = Date().timeIntervalSince(startTime)

        print("✅ SIMULATION COMPLETE: \(report.filesWiped) files identified")
        print("   Duration: \(String(format: "%.2f", report.durationSeconds))s")

        return report
    }

    // MARK: - Real Emergency Wipe (Production/VM - DANGEROUS)

    /// Execute REAL emergency wipe with DoD 7-pass overwrite
    /// ⚠️ THIS IS IRREVERSIBLE - VM TESTING ONLY IN WEEK 2
    private func executeEmergencyWipe(reason: String?) async throws -> EmergencyWipeReport {
        // SAFETY: This should only run in production or VM testing
        #if DEBUG
        fatalError("❌ SAFETY ERROR: Real emergency wipe attempted in debug build")
        #endif

        print("🚨 EMERGENCY MODE: Real DoD 7-pass wipe starting")
        print("   ⚠️ THIS IS IRREVERSIBLE")

        var report = EmergencyWipeReport(
            simulated: false,
            filesWiped: 0,
            passes: 7,
            durationSeconds: 0,
            errors: []
        )

        let startTime = Date()

        // Call backend emergency endpoint
        do {
            let backendResponse = try await callBackendEmergencyWipe(reason: reason)
            report.filesWiped += backendResponse.filesWiped
            report.errors.append(contentsOf: backendResponse.errors)
        } catch {
            report.errors.append("Backend wipe failed: \(error.localizedDescription)")
        }

        // Local emergency actions
        try await performLocalEmergencyWipe(&report)

        // Keychain purge
        try await purgeKeychain(&report)

        // Self-uninstall (must be last action)
        try await performSelfUninstall(&report)

        report.durationSeconds = Date().timeIntervalSince(startTime)

        return report
    }

    // MARK: - File Identification (Simulation Mode)

    private func identifyVaultFiles() async -> [String] {
        let magnetarDir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".magnetar")

        var files: [String] = []

        // Vault databases
        let vaultFiles = [
            "vault_sensitive.db",
            "vault_unsensitive.db",
            "vault.db"
        ]

        for file in vaultFiles {
            let path = magnetarDir.appendingPathComponent(file)
            if FileManager.default.fileExists(atPath: path.path) {
                files.append(path.path)
            }
        }

        return files
    }

    private func identifyBackupFiles() async -> [String] {
        let backupDir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".elohimos_backups")

        guard let enumerator = FileManager.default.enumerator(atPath: backupDir.path) else {
            return []
        }

        var files: [String] = []
        for case let file as String in enumerator {
            let fullPath = backupDir.appendingPathComponent(file).path
            files.append(fullPath)
        }

        return files
    }

    private func identifyModelFiles() async -> [String] {
        let modelsDir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".magnetar/models")

        guard let enumerator = FileManager.default.enumerator(atPath: modelsDir.path) else {
            return []
        }

        var files: [String] = []
        for case let file as String in enumerator {
            let fullPath = modelsDir.appendingPathComponent(file).path
            files.append(fullPath)
        }

        return files
    }

    private func identifyCacheFiles() async -> [String] {
        let cacheDir = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first?
            .appendingPathComponent("com.magnetarstudio.app")

        guard let cacheDir = cacheDir,
              let enumerator = FileManager.default.enumerator(atPath: cacheDir.path) else {
            return []
        }

        var files: [String] = []
        for case let file as String in enumerator {
            let fullPath = cacheDir.appendingPathComponent(file).path
            files.append(fullPath)
        }

        return files
    }

    private func identifyAuditFiles() async -> [String] {
        let magnetarDir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".magnetar")

        let auditDB = magnetarDir.appendingPathComponent("audit.db")

        if FileManager.default.fileExists(atPath: auditDB.path) {
            return [auditDB.path]
        }

        return []
    }

    private func identifyAppBundle() async -> String {
        return "/Applications/MagnetarStudio.app"
    }

    // MARK: - Backend Integration

    private func callBackendEmergencyWipe(reason: String?) async throws -> BackendEmergencyResponse {
        let url = URL(string: "\(baseURL)/emergency")!
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let body: [String: Any] = [
            "confirmation": "CONFIRM",
            "reason": reason ?? "User-initiated emergency mode"
        ]

        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse,
              (200...299).contains(httpResponse.statusCode) else {
            throw EmergencyModeError.backendFailed
        }

        return try JSONDecoder().decode(BackendEmergencyResponse.self, from: data)
    }

    // MARK: - Local Emergency Actions (Production Only)

    private func performLocalEmergencyWipe(_ report: inout EmergencyWipeReport) async throws {
        // TODO: Week 2 - Implement local file wipe
        // - Zero memory (vault passphrase, cache)
        // - Clear NSPasteboard
        // - Clear URLSession cache
        print("⚠️ TODO: Local emergency wipe not implemented yet")
    }

    private func purgeKeychain(_ report: inout EmergencyWipeReport) async throws {
        // TODO: Week 2 - Implement keychain purge
        // - Delete all app-specific keychain entries
        // - Delete biometric credentials
        print("⚠️ TODO: Keychain purge not implemented yet")
    }

    private func performSelfUninstall(_ report: inout EmergencyWipeReport) async throws {
        // TODO: Week 2 - Implement self-uninstall
        // - Delete app bundle via LaunchServices
        // - Must be last action (app will terminate)
        print("⚠️ TODO: Self-uninstall not implemented yet")
    }

    // MARK: - Audit Logging

    private func logEmergencyTrigger(reason: String?, method: EmergencyTriggerMethod) async {
        await SecurityManager.shared.logSecurityEvent(SecurityEvent(
            type: .panicTriggered,
            level: .emergency,
            message: "Emergency mode triggered via \(method.rawValue)",
            details: [
                "reason": reason ?? "User-initiated",
                "simulation": isSimulationMode ? "true" : "false"
            ]
        ))
    }

    private func sendEmergencyLogToRemote(reason: String?) async throws {
        // TODO: Implement remote emergency log
        // Send to backend if network available
        // Don't block if network fails
        print("⚠️ TODO: Remote emergency log not implemented yet")
    }
}

// MARK: - Supporting Types

struct EmergencyWipeReport: Codable {
    var simulated: Bool
    var filesWiped: Int
    var passes: Int
    var durationSeconds: TimeInterval
    var errors: [String]
    var filesIdentified: [String] = []
}

struct BackendEmergencyResponse: Codable {
    let success: Bool
    let filesWiped: Int
    let passes: Int
    let durationSeconds: Double
    let errors: [String]

    enum CodingKeys: String, CodingKey {
        case success
        case filesWiped = "files_wiped"
        case passes
        case durationSeconds = "duration_seconds"
        case errors
    }
}

enum EmergencyTriggerMethod: String {
    case textConfirmation = "text_confirmation"  // "I UNDERSTAND"
    case keyCombo = "key_combo"                  // Cmd+Shift+Delete (5 sec)
}

enum EmergencyModeError: LocalizedError {
    case disabledInDebug
    case backendFailed
    case alreadyInProgress

    var errorDescription: String? {
        switch self {
        case .disabledInDebug:
            return "Emergency mode disabled in debug build (safety measure)"
        case .backendFailed:
            return "Backend emergency wipe failed"
        case .alreadyInProgress:
            return "Emergency mode already in progress"
        }
    }
}
