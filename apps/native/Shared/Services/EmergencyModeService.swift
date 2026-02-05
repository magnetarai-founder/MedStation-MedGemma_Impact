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
import Observation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "EmergencyModeService")

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
@Observable
final class EmergencyModeService {
    static let shared = EmergencyModeService()

    // MARK: - Observable State

    private(set) var isSimulationMode: Bool = true
    private(set) var emergencyInProgress: Bool = false
    private(set) var lastEmergencyReport: EmergencyWipeReport?

    // MARK: - Internal State (accessible to extensions)

    let apiClient: ApiClient

    private init() {
        self.apiClient = .shared

        #if DEBUG
        self.isSimulationMode = true  // Always simulate in debug
        logger.warning("EmergencyModeService: DEBUG MODE - Simulation only")
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
        do {
            try await sendEmergencyLogToRemote(reason: reason)
        } catch {
            logger.warning("Emergency log transmission failed (may be offline): \(error)")
        }

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
        logger.warning("SIMULATION MODE: Emergency wipe started")
        logger.warning("Reason: \(reason ?? "User-initiated")")

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
        logger.info("Would delete \(vaultFiles.count) vault files: \(vaultFiles.joined(separator: ", "))")
        report.filesIdentified.append(contentsOf: vaultFiles)

        let backupFiles = await identifyBackupFiles()
        logger.info("Would delete \(backupFiles.count) backup files: \(backupFiles.joined(separator: ", "))")
        report.filesIdentified.append(contentsOf: backupFiles)

        let modelFiles = await identifyModelFiles()
        logger.info("Would delete \(modelFiles.count) model files: \(modelFiles.joined(separator: ", "))")
        report.filesIdentified.append(contentsOf: modelFiles)

        let cacheFiles = await identifyCacheFiles()
        logger.info("Would delete \(cacheFiles.count) cache files: \(cacheFiles.joined(separator: ", "))")
        report.filesIdentified.append(contentsOf: cacheFiles)

        let auditFiles = await identifyAuditFiles()
        logger.info("Would delete \(auditFiles.count) audit log files: \(auditFiles.joined(separator: ", "))")
        report.filesIdentified.append(contentsOf: auditFiles)

        let appBundle = await identifyAppBundle()
        logger.info("Would delete app bundle: \(appBundle)")
        report.filesIdentified.append(appBundle)

        let launchAgents = await identifyLaunchAgents()
        logger.info("Would delete \(launchAgents.count) LaunchAgent files: \(launchAgents.joined(separator: ", "))")
        report.filesIdentified.append(contentsOf: launchAgents)

        let preferences = await identifyPreferences()
        logger.info("Would delete \(preferences.count) preference files: \(preferences.joined(separator: ", "))")
        report.filesIdentified.append(contentsOf: preferences)

        let appSupport = await identifyApplicationSupport()
        logger.info("Would delete \(appSupport.count) Application Support directories: \(appSupport.joined(separator: ", "))")
        report.filesIdentified.append(contentsOf: appSupport)

        let logs = await identifyLogs()
        logger.info("Would delete \(logs.count) log directories: \(logs.joined(separator: ", "))")
        report.filesIdentified.append(contentsOf: logs)

        let tempFiles = await identifyTemporaryFiles()
        logger.info("Would delete \(tempFiles.count) temporary files: \(tempFiles.joined(separator: ", "))")
        report.filesIdentified.append(contentsOf: tempFiles)

        report.filesWiped = report.filesIdentified.count
        report.durationSeconds = Date().timeIntervalSince(startTime)

        logger.warning("SIMULATION COMPLETE: \(report.filesWiped) files identified in \(String(format: "%.2f", report.durationSeconds))s")
        logger.info("Summary - Vaults: \(vaultFiles.count), Backups: \(backupFiles.count), Models: \(modelFiles.count), Cache: \(cacheFiles.count), Audit: \(auditFiles.count), LaunchAgents: \(launchAgents.count), Preferences: \(preferences.count), App Support: \(appSupport.count), Logs: \(logs.count), Temporary: \(tempFiles.count), App Bundle: 1")

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
        logger.critical("EMERGENCY MODE: Real DoD 7-pass wipe starting - THIS IS IRREVERSIBLE")

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
