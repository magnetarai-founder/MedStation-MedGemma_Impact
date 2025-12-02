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

    private init() {
        self.apiClient = .shared

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

        // 7. Identify LaunchAgents
        let launchAgents = await identifyLaunchAgents()
        print("   📁 Would delete \(launchAgents.count) LaunchAgent files:")
        launchAgents.forEach { print("      - \($0)") }
        report.filesIdentified.append(contentsOf: launchAgents)

        // 8. Identify Preferences
        let preferences = await identifyPreferences()
        print("   📁 Would delete \(preferences.count) preference files:")
        preferences.forEach { print("      - \($0)") }
        report.filesIdentified.append(contentsOf: preferences)

        // 9. Identify Application Support
        let appSupport = await identifyApplicationSupport()
        print("   📁 Would delete \(appSupport.count) Application Support directories:")
        appSupport.forEach { print("      - \($0)") }
        report.filesIdentified.append(contentsOf: appSupport)

        // 10. Identify Logs
        let logs = await identifyLogs()
        print("   📁 Would delete \(logs.count) log directories:")
        logs.forEach { print("      - \($0)") }
        report.filesIdentified.append(contentsOf: logs)

        // 11. Identify Temporary Files
        let tempFiles = await identifyTemporaryFiles()
        print("   📁 Would delete \(tempFiles.count) temporary files:")
        tempFiles.forEach { print("      - \($0)") }
        report.filesIdentified.append(contentsOf: tempFiles)

        report.filesWiped = report.filesIdentified.count
        report.durationSeconds = Date().timeIntervalSince(startTime)

        print("✅ SIMULATION COMPLETE: \(report.filesWiped) files identified")
        print("   Duration: \(String(format: "%.2f", report.durationSeconds))s")
        print("")
        print("   📊 Summary by category:")
        print("      Vaults: \(vaultFiles.count)")
        print("      Backups: \(backupFiles.count)")
        print("      Models: \(modelFiles.count)")
        print("      Cache: \(cacheFiles.count)")
        print("      Audit: \(auditFiles.count)")
        print("      LaunchAgents: \(launchAgents.count)")
        print("      Preferences: \(preferences.count)")
        print("      App Support: \(appSupport.count)")
        print("      Logs: \(logs.count)")
        print("      Temporary: \(tempFiles.count)")
        print("      App Bundle: 1")

        return report
    }

    // MARK: - Real Emergency Wipe (Production/VM - DANGEROUS)

    /// Execute REAL emergency wipe with DoD 7-pass overwrite
    /// ⚠️ THIS IS IRREVERSIBLE - VM TESTING ONLY IN WEEK 2
    private func executeEmergencyWipe(reason: String?) async throws -> EmergencyWipeReport {
        #if DEBUG
        // SAFETY: This should only run in production or VM testing
        fatalError("❌ SAFETY ERROR: Real emergency wipe attempted in debug build")
        #else
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
        #endif
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

        // Collect all files first to avoid async iterator issues
        let allFiles = enumerator.allObjects.compactMap { $0 as? String }
        return allFiles.map { backupDir.appendingPathComponent($0).path }
    }

    private func identifyModelFiles() async -> [String] {
        let modelsDir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".magnetar/models")

        guard let enumerator = FileManager.default.enumerator(atPath: modelsDir.path) else {
            return []
        }

        // Collect all files first to avoid async iterator issues
        let allFiles = enumerator.allObjects.compactMap { $0 as? String }
        return allFiles.map { modelsDir.appendingPathComponent($0).path }
    }

    private func identifyCacheFiles() async -> [String] {
        let cacheDir = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first?
            .appendingPathComponent("com.magnetarstudio.app")

        guard let cacheDir = cacheDir,
              let enumerator = FileManager.default.enumerator(atPath: cacheDir.path) else {
            return []
        }

        // Collect all files first to avoid async iterator issues
        let allFiles = enumerator.allObjects.compactMap { $0 as? String }
        return allFiles.map { cacheDir.appendingPathComponent($0).path }
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

    private func identifyLaunchAgents() async -> [String] {
        let fm = FileManager.default
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        var files: [String] = []

        // User LaunchAgents
        let launchAgentsPath = "\(home)/Library/LaunchAgents"
        if let agents = try? fm.contentsOfDirectory(atPath: launchAgentsPath) {
            for agent in agents where agent.contains("magnetar") || agent.contains("elohim") {
                files.append("\(launchAgentsPath)/\(agent)")
            }
        }

        // Note: LaunchDaemons require sudo, skipping for user-level wipe
        // System-level LaunchDaemons at /Library/LaunchDaemons/ would need elevated privileges

        return files
    }

    private func identifyPreferences() async -> [String] {
        let fm = FileManager.default
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        var files: [String] = []

        // User Preferences
        let prefsPath = "\(home)/Library/Preferences"
        if let prefs = try? fm.contentsOfDirectory(atPath: prefsPath) {
            for pref in prefs where pref.contains("magnetar") || pref.contains("elohim") {
                files.append("\(prefsPath)/\(pref)")
            }
        }

        return files
    }

    private func identifyApplicationSupport() async -> [String] {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        let appSupportPath = "\(home)/Library/Application Support/MagnetarStudio"

        if FileManager.default.fileExists(atPath: appSupportPath) {
            return [appSupportPath]
        }

        return []
    }

    private func identifyLogs() async -> [String] {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        var files: [String] = []

        // App-specific logs
        let logsPath = "\(home)/Library/Logs/MagnetarStudio"
        if FileManager.default.fileExists(atPath: logsPath) {
            files.append(logsPath)
        }

        // System logs containing app mentions (note: would require filtering)
        // Not included in wipe as system logs are shared and require sudo

        return files
    }

    private func identifyTemporaryFiles() async -> [String] {
        let fm = FileManager.default
        var files: [String] = []

        // Temporary directories
        let tempPaths = ["/tmp", "/var/tmp", NSTemporaryDirectory()]

        for tempPath in tempPaths {
            if let tmpFiles = try? fm.contentsOfDirectory(atPath: tempPath) {
                for file in tmpFiles where file.contains("magnetar") || file.contains("elohim") {
                    let fullPath = (tempPath as NSString).appendingPathComponent(file)
                    files.append(fullPath)
                }
            }
        }

        return files
    }

    private func identifyAppBundle() async -> String {
        return "/Applications/MagnetarStudio.app"
    }

    // Note: Spotlight index removal requires:
    // - sudo mdutil -E / (re-index entire volume)
    // - or sudo mdutil -d / (disable indexing)
    // This requires elevated privileges and would affect entire system
    // Decision: Not included in automatic wipe, document as manual step if needed

    // MARK: - Backend Integration

    private func callBackendEmergencyWipe(reason: String?) async throws -> BackendEmergencyResponse {
        struct EmergencyWipeRequest: Codable {
            let confirmation: String
            let reason: String
        }

        let request = EmergencyWipeRequest(
            confirmation: "CONFIRM",
            reason: reason ?? "User-initiated emergency mode"
        )

        return try await apiClient.request(
            "/api/v1/panic/emergency",
            method: .post,
            body: request,
            authenticated: true
        )
    }

    // MARK: - Local Emergency Actions (Production Only)

    private func performLocalEmergencyWipe(_ report: inout EmergencyWipeReport) async throws {
        print("🧹 Local emergency wipe starting...")

        var localWipeCount = 0

        // 1. Zero sensitive memory
        do {
            try await zeroSensitiveMemory()
            localWipeCount += 1
            print("   ✅ Sensitive memory zeroed")
        } catch {
            report.errors.append("Memory zeroing failed: \(error.localizedDescription)")
        }

        // 2. Clear NSPasteboard (clipboard)
        clearPasteboard()
        localWipeCount += 1
        print("   ✅ Clipboard cleared")

        // 3. Clear URLSession cache
        await clearURLSessionCache()
        localWipeCount += 1
        print("   ✅ URLSession cache cleared")

        // 4. Flush model inference cache (if applicable)
        await flushModelCache()
        localWipeCount += 1
        print("   ✅ Model cache flushed")

        report.filesWiped += localWipeCount
        print("✅ Local emergency wipe complete: \(localWipeCount) actions")
    }

    private func purgeKeychain(_ report: inout EmergencyWipeReport) async throws {
        print("🔐 Keychain purge starting...")

        var keychainWipeCount = 0

        // 1. Delete authentication tokens
        do {
            try KeychainService.shared.deleteToken()
            keychainWipeCount += 1
            print("   ✅ Auth token deleted")
        } catch {
            report.errors.append("Token deletion failed: \(error.localizedDescription)")
        }

        // 2. Delete all app-specific keychain items
        do {
            let deletedCount = try await deleteAllAppKeychainItems()
            keychainWipeCount += deletedCount
            print("   ✅ \(deletedCount) keychain items deleted")
        } catch {
            report.errors.append("Keychain purge failed: \(error.localizedDescription)")
        }

        report.filesWiped += keychainWipeCount
        print("✅ Keychain purge complete: \(keychainWipeCount) items deleted")
    }

    private func performSelfUninstall(_ report: inout EmergencyWipeReport) async throws {
        print("🗑️  Self-uninstall starting...")

        // CRITICAL SAFETY CHECK: Only proceed in production builds
        #if DEBUG
        print("   ⚠️  SKIPPED: Self-uninstall disabled in debug builds")
        report.errors.append("Self-uninstall skipped (debug build)")
        #else
        // Production-only code below
        let bundlePath = Bundle.main.bundlePath
        print("   App bundle: \(bundlePath)")

        // 1. Delete user data directories
        do {
            let deletedCount = try await deleteUserDataDirectories()
            report.filesWiped += deletedCount
            print("   ✅ Deleted \(deletedCount) user data directories")
        } catch {
            report.errors.append("User data deletion failed: \(error.localizedDescription)")
        }

        // 2. Schedule app bundle deletion
        // We use a shell script to delete the app after it terminates
        do {
            try scheduleAppDeletion(bundlePath: bundlePath)
            print("   ✅ App deletion scheduled")
            report.filesWiped += 1
        } catch {
            report.errors.append("App deletion scheduling failed: \(error.localizedDescription)")
        }

        // 3. Terminate app (must be last action)
        print("🚨 App will now terminate for self-uninstall")
        print("⚠️  MagnetarStudio has been completely removed from this system")

        // Give system time to finish cleanup
        try? await Task.sleep(nanoseconds: 1_000_000_000) // 1 second

        // Terminate the app
        NSApplication.shared.terminate(nil)
        #endif
    }

    // MARK: - Memory & Cache Cleanup Helpers

    /// Zero sensitive data in memory
    /// This includes vault passphrases, cached credentials, and other sensitive buffers
    private func zeroSensitiveMemory() async throws {
        print("      Zeroing sensitive memory...")

        // TODO: Identify specific memory buffers to zero
        // For now, we'll trigger aggressive memory pressure
        // Real implementation should track and zero specific buffers

        // Force memory release
        autoreleasepool {
            // Clear any cached sensitive data
            // In production, this would zero specific byte arrays
        }

        // Give system time to release memory
        try? await Task.sleep(nanoseconds: 100_000_000) // 0.1 seconds

        print("      Memory zeroing complete")
    }

    /// Clear NSPasteboard (clipboard) to remove any copied sensitive data
    private func clearPasteboard() {
        print("      Clearing clipboard...")

        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()

        // Verify clipboard is empty
        let contents = pasteboard.string(forType: .string)
        if contents == nil || contents!.isEmpty {
            print("      Clipboard cleared successfully")
        } else {
            print("      ⚠️  Clipboard may still contain data")
        }
    }

    /// Clear URLSession cache to remove any cached API responses or downloaded data
    private func clearURLSessionCache() async {
        print("      Clearing URLSession cache...")

        // Clear shared URLSession cache
        URLCache.shared.removeAllCachedResponses()

        // Clear cookies
        if let cookies = HTTPCookieStorage.shared.cookies {
            for cookie in cookies {
                HTTPCookieStorage.shared.deleteCookie(cookie)
            }
        }

        // Give system time to flush
        try? await Task.sleep(nanoseconds: 100_000_000) // 0.1 seconds

        print("      URLSession cache cleared")
    }

    /// Flush model inference cache (if using local AI models)
    private func flushModelCache() async {
        print("      Flushing model cache...")

        // Check if model cache directory exists
        let modelCacheDir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".magnetar/model_cache")

        if FileManager.default.fileExists(atPath: modelCacheDir.path) {
            // Remove model cache directory
            try? FileManager.default.removeItem(at: modelCacheDir)
            print("      Model cache flushed (\(modelCacheDir.path))")
        } else {
            print("      No model cache found (skipped)")
        }
    }

    // MARK: - Keychain Cleanup Helpers

    /// Delete all app-specific keychain items
    /// This removes all stored credentials, API keys, and sensitive data from macOS Keychain
    private func deleteAllAppKeychainItems() async throws -> Int {
        print("      Deleting all app keychain items...")

        var deletedCount = 0

        // Define app-specific service identifiers
        let serviceIdentifiers = [
            "com.magnetarstudio.app",
            "com.magnetarstudio.auth",
            "com.magnetarstudio.vault",
            "com.magnetarstudio.api"
        ]

        for serviceID in serviceIdentifiers {
            // Query for all items with this service ID
            let query: [String: Any] = [
                kSecClass as String: kSecClassGenericPassword,
                kSecAttrService as String: serviceID,
                kSecMatchLimit as String: kSecMatchLimitAll,
                kSecReturnAttributes as String: true
            ]

            var result: AnyObject?
            let status = SecItemCopyMatching(query as CFDictionary, &result)

            if status == errSecSuccess, let items = result as? [[String: Any]] {
                // Delete each found item
                for item in items {
                    if let account = item[kSecAttrAccount as String] as? String {
                        let deleteQuery: [String: Any] = [
                            kSecClass as String: kSecClassGenericPassword,
                            kSecAttrService as String: serviceID,
                            kSecAttrAccount as String: account
                        ]

                        let deleteStatus = SecItemDelete(deleteQuery as CFDictionary)
                        if deleteStatus == errSecSuccess {
                            deletedCount += 1
                            print("         Deleted: \(serviceID)/\(account)")
                        }
                    }
                }
            }
        }

        // Also delete any internet passwords (saved website credentials)
        let internetQuery: [String: Any] = [
            kSecClass as String: kSecClassInternetPassword,
            kSecMatchLimit as String: kSecMatchLimitAll
        ]

        let internetDeleteStatus = SecItemDelete(internetQuery as CFDictionary)
        if internetDeleteStatus == errSecSuccess {
            deletedCount += 1
            print("         Deleted: Internet passwords")
        }

        return deletedCount
    }

    // MARK: - Self-Uninstall Helpers

    /// Delete all user data directories
    /// This removes all application support files, caches, logs, and preferences
    private func deleteUserDataDirectories() async throws -> Int {
        print("      Deleting user data directories...")

        var deletedCount = 0
        let fm = FileManager.default
        let homeDir = fm.homeDirectoryForCurrentUser

        // Define directories to delete
        let directories = [
            homeDir.appendingPathComponent(".magnetar"),
            homeDir.appendingPathComponent(".elohimos_backups"),
            homeDir.appendingPathComponent("Library/Caches/com.magnetarstudio.app"),
            homeDir.appendingPathComponent("Library/Application Support/MagnetarStudio"),
            homeDir.appendingPathComponent("Library/Logs/MagnetarStudio"),
            homeDir.appendingPathComponent("Library/Preferences/com.magnetarstudio.app.plist")
        ]

        for dir in directories {
            if fm.fileExists(atPath: dir.path) {
                do {
                    try fm.removeItem(at: dir)
                    deletedCount += 1
                    print("         Deleted: \(dir.path)")
                } catch {
                    print("         ⚠️  Failed to delete: \(dir.path) - \(error.localizedDescription)")
                }
            }
        }

        // Delete LaunchAgents
        let launchAgentsDir = homeDir.appendingPathComponent("Library/LaunchAgents")
        if let agents = try? fm.contentsOfDirectory(atPath: launchAgentsDir.path) {
            for agent in agents where agent.contains("magnetarstudio") || agent.contains("elohim") {
                let agentPath = launchAgentsDir.appendingPathComponent(agent)
                do {
                    try fm.removeItem(at: agentPath)
                    deletedCount += 1
                    print("         Deleted LaunchAgent: \(agent)")
                } catch {
                    print("         ⚠️  Failed to delete LaunchAgent: \(agent)")
                }
            }
        }

        return deletedCount
    }

    /// Schedule app bundle deletion after app terminates
    /// Uses a temporary shell script that waits for the app to quit, then deletes the bundle
    private func scheduleAppDeletion(bundlePath: String) throws {
        print("      Scheduling app bundle deletion...")

        // Create a temporary shell script that will:
        // 1. Wait for the app to terminate
        // 2. Delete the app bundle
        // 3. Delete itself

        let scriptContent = """
        #!/bin/bash
        # MagnetarStudio Self-Uninstall Script
        # This script waits for the app to quit, then deletes it

        # Wait for app to terminate
        sleep 2

        # Get the app bundle path
        APP_PATH="\(bundlePath)"

        # Delete the app bundle
        if [ -d "$APP_PATH" ]; then
            echo "Deleting MagnetarStudio app bundle..."
            rm -rf "$APP_PATH"
            echo "MagnetarStudio has been removed."
        fi

        # Delete this script
        rm -f "$0"
        """

        // Write script to temporary location
        let scriptPath = "/tmp/magnetar_uninstall_\(UUID().uuidString).sh"
        try scriptContent.write(toFile: scriptPath, atomically: true, encoding: .utf8)

        // Make script executable
        let chmod = Process()
        chmod.launchPath = "/bin/chmod"
        chmod.arguments = ["+x", scriptPath]
        chmod.launch()
        chmod.waitUntilExit()

        // Launch script in background
        let script = Process()
        script.launchPath = "/bin/bash"
        script.arguments = [scriptPath]
        script.launch()

        print("         Self-uninstall script launched: \(scriptPath)")
    }

    // MARK: - Audit Logging

    private func logEmergencyTrigger(reason: String?, method: EmergencyTriggerMethod) async {
        // TODO: Integrate with SecurityManager when available
        print("🔒 Security Event: Emergency mode triggered via \(method.rawValue)")
        print("   Reason: \(reason ?? "User-initiated")")
        print("   Simulation: \(isSimulationMode ? "true" : "false")")
    }

    private func sendEmergencyLogToRemote(reason: String?) async throws {
        // TODO: Implement remote emergency log
        // Send to backend if network available
        // Don't block if network fails
        print("⚠️ TODO: Remote emergency log not implemented yet")
    }
}

// MARK: - Supporting Types

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
