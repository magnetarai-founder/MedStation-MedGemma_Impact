//
//  EmergencyModeService.swift
//  MagnetarStudio
//
//  CRITICAL: Emergency mode with DoD 7-pass wipe and self-uninstall
//  FOR PERSECUTION SCENARIOS ONLY
//
//  Safety: Week 1 is SIMULATION MODE ONLY - no actual file deletion
//
//  Structure:
//  - EmergencyModeService.swift (this file) - Core service and trigger logic
//  - EmergencyModeService+FileIdentification.swift - File identification helpers
//  - EmergencyModeService+LocalCleanup.swift - Memory/cache/keychain cleanup
//  - EmergencyModeService+SelfUninstall.swift - Self-uninstall operations
//  - EmergencyModeService+Backend.swift - Backend API integration
//  - EmergencyModeModels.swift - Supporting types
//

import Foundation
import AppKit

// MARK: - Emergency Mode Safety Configuration

/// CRITICAL SAFETY: Debug kill switch for emergency mode
/// Must be manually enabled for testing, disabled by default in debug builds
#if DEBUG
private let EMERGENCY_MODE_ENABLED = false  // SET TO true ONLY FOR VM TESTING
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

    // MARK: - Internal State (accessible to extensions)

    let apiClient: ApiClient

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

        // Identify all files that would be deleted
        let vaultFiles = await identifyVaultFiles()
        print("   📁 Would delete \(vaultFiles.count) vault files:")
        vaultFiles.forEach { print("      - \($0)") }
        report.filesIdentified.append(contentsOf: vaultFiles)

        let backupFiles = await identifyBackupFiles()
        print("   📁 Would delete \(backupFiles.count) backup files:")
        backupFiles.forEach { print("      - \($0)") }
        report.filesIdentified.append(contentsOf: backupFiles)

        let modelFiles = await identifyModelFiles()
        print("   📁 Would delete \(modelFiles.count) model files:")
        modelFiles.forEach { print("      - \($0)") }
        report.filesIdentified.append(contentsOf: modelFiles)

        let cacheFiles = await identifyCacheFiles()
        print("   📁 Would delete \(cacheFiles.count) cache files:")
        cacheFiles.forEach { print("      - \($0)") }
        report.filesIdentified.append(contentsOf: cacheFiles)

        let auditFiles = await identifyAuditFiles()
        print("   📁 Would delete \(auditFiles.count) audit log files:")
        auditFiles.forEach { print("      - \($0)") }
        report.filesIdentified.append(contentsOf: auditFiles)

        let appBundle = await identifyAppBundle()
        print("   📁 Would delete app bundle: \(appBundle)")
        report.filesIdentified.append(appBundle)

        let launchAgents = await identifyLaunchAgents()
        print("   📁 Would delete \(launchAgents.count) LaunchAgent files:")
        launchAgents.forEach { print("      - \($0)") }
        report.filesIdentified.append(contentsOf: launchAgents)

        let preferences = await identifyPreferences()
        print("   📁 Would delete \(preferences.count) preference files:")
        preferences.forEach { print("      - \($0)") }
        report.filesIdentified.append(contentsOf: preferences)

        let appSupport = await identifyApplicationSupport()
        print("   📁 Would delete \(appSupport.count) Application Support directories:")
        appSupport.forEach { print("      - \($0)") }
        report.filesIdentified.append(contentsOf: appSupport)

        let logs = await identifyLogs()
        print("   📁 Would delete \(logs.count) log directories:")
        logs.forEach { print("      - \($0)") }
        report.filesIdentified.append(contentsOf: logs)

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
    /// THIS IS IRREVERSIBLE - VM TESTING ONLY IN WEEK 2
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
}
