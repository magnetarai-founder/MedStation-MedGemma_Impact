//
//  EmergencyModeService+SelfUninstall.swift
//  MagnetarStudio
//
//  Extension for self-uninstall operations
//  Handles app bundle deletion and user data cleanup
//

import Foundation
import AppKit
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "EmergencyModeService.SelfUninstall")

// MARK: - Self-Uninstall

extension EmergencyModeService {

    func performSelfUninstall(_ report: inout EmergencyWipeReport) async throws {
        logger.critical("Self-uninstall starting...")

        // CRITICAL SAFETY CHECK: Only proceed in production builds
        #if DEBUG
        logger.warning("SKIPPED: Self-uninstall disabled in debug builds")
        report.errors.append("Self-uninstall skipped (debug build)")
        #else
        let bundlePath = Bundle.main.bundlePath
        logger.info("App bundle: \(bundlePath)")

        // 1. Delete user data directories
        do {
            let deletedCount = try await deleteUserDataDirectories()
            report.filesWiped += deletedCount
            logger.info("Deleted \(deletedCount) user data directories")
        } catch {
            report.errors.append("User data deletion failed: \(error.localizedDescription)")
        }

        // 2. Schedule app bundle deletion
        do {
            try scheduleAppDeletion(bundlePath: bundlePath)
            logger.info("App deletion scheduled")
            report.filesWiped += 1
        } catch {
            report.errors.append("App deletion scheduling failed: \(error.localizedDescription)")
        }

        // 3. Terminate app (must be last action)
        logger.critical("App will now terminate for self-uninstall - MagnetarStudio has been completely removed from this system")

        // Give system time to finish cleanup
        try? await Task.sleep(nanoseconds: 1_000_000_000) // 1 second

        // Terminate the app
        NSApplication.shared.terminate(nil)
        #endif
    }

    /// Delete all user data directories
    func deleteUserDataDirectories() async throws -> Int {
        logger.debug("Deleting user data directories...")

        var deletedCount = 0
        let fm = FileManager.default
        let homeDir = fm.homeDirectoryForCurrentUser

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
                    logger.debug("Deleted: \(dir.path)")
                } catch {
                    logger.warning("Failed to delete: \(dir.path) - \(error.localizedDescription)")
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
                    logger.debug("Deleted LaunchAgent: \(agent)")
                } catch {
                    logger.warning("Failed to delete LaunchAgent: \(agent)")
                }
            }
        }

        return deletedCount
    }

    /// Schedule app bundle deletion after app terminates
    func scheduleAppDeletion(bundlePath: String) throws {
        logger.debug("Scheduling app bundle deletion...")

        // Shell-escape the bundle path to prevent injection via metacharacters
        let escapedBundlePath = bundlePath.replacingOccurrences(of: "'", with: "'\\''")

        let scriptContent = """
        #!/bin/bash
        # MagnetarStudio Self-Uninstall Script
        # This script waits for the app to quit, then deletes it

        # Wait for app to terminate
        sleep 2

        # Get the app bundle path
        APP_PATH='\(escapedBundlePath)'

        # Delete the app bundle
        if [ -d "$APP_PATH" ]; then
            echo "Deleting MagnetarStudio app bundle..."
            rm -rf "$APP_PATH"
            echo "MagnetarStudio has been removed."
        fi

        # Delete this script
        rm -f "$0"
        """

        // Use NSTemporaryDirectory (per-user, not world-writable /tmp)
        let scriptPath = NSTemporaryDirectory() + "magnetar_uninstall_\(UUID().uuidString).sh"
        try scriptContent.write(toFile: scriptPath, atomically: true, encoding: .utf8)

        // Restrict permissions to owner only (700)
        try FileManager.default.setAttributes([.posixPermissions: 0o700], ofItemAtPath: scriptPath)

        // Launch script in background — intentionally no waitUntilExit() because
        // the script deletes the app bundle; the app must exit before it completes
        let script = Process()
        script.launchPath = "/bin/bash"
        script.arguments = [scriptPath]
        script.launch()

        logger.debug("Self-uninstall script launched: \(scriptPath)")
    }
}
