//
//  EmergencyModeService+SelfUninstall.swift
//  MagnetarStudio
//
//  Extension for self-uninstall operations
//  Handles app bundle deletion and user data cleanup
//

import Foundation
import AppKit

// MARK: - Self-Uninstall

extension EmergencyModeService {

    func performSelfUninstall(_ report: inout EmergencyWipeReport) async throws {
        print("🗑️  Self-uninstall starting...")

        // CRITICAL SAFETY CHECK: Only proceed in production builds
        #if DEBUG
        print("   ⚠️  SKIPPED: Self-uninstall disabled in debug builds")
        report.errors.append("Self-uninstall skipped (debug build)")
        #else
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

    /// Delete all user data directories
    func deleteUserDataDirectories() async throws -> Int {
        print("      Deleting user data directories...")

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
    func scheduleAppDeletion(bundlePath: String) throws {
        print("      Scheduling app bundle deletion...")

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
}
