//
//  EmergencyModeService+FileIdentification.swift
//  MagnetarStudio
//
//  Extension for file identification helpers (simulation mode)
//  Identifies what WOULD be deleted without actually deleting
//

import Foundation

// MARK: - File Identification (Simulation Mode)

extension EmergencyModeService {

    func identifyVaultFiles() async -> [String] {
        let magnetarDir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".magnetar")

        var files: [String] = []

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

    func identifyBackupFiles() async -> [String] {
        let backupDir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".elohimos_backups")

        guard let enumerator = FileManager.default.enumerator(atPath: backupDir.path) else {
            return []
        }

        let allFiles = enumerator.allObjects.compactMap { $0 as? String }
        return allFiles.map { backupDir.appendingPathComponent($0).path }
    }

    func identifyModelFiles() async -> [String] {
        let modelsDir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".magnetar/models")

        guard let enumerator = FileManager.default.enumerator(atPath: modelsDir.path) else {
            return []
        }

        let allFiles = enumerator.allObjects.compactMap { $0 as? String }
        return allFiles.map { modelsDir.appendingPathComponent($0).path }
    }

    func identifyCacheFiles() async -> [String] {
        let cacheDir = FileManager.default.urls(for: .cachesDirectory, in: .userDomainMask).first?
            .appendingPathComponent("com.magnetarstudio.app")

        guard let cacheDir = cacheDir,
              let enumerator = FileManager.default.enumerator(atPath: cacheDir.path) else {
            return []
        }

        let allFiles = enumerator.allObjects.compactMap { $0 as? String }
        return allFiles.map { cacheDir.appendingPathComponent($0).path }
    }

    func identifyAuditFiles() async -> [String] {
        let magnetarDir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".magnetar")

        let auditDB = magnetarDir.appendingPathComponent("audit.db")

        if FileManager.default.fileExists(atPath: auditDB.path) {
            return [auditDB.path]
        }

        return []
    }

    func identifyLaunchAgents() async -> [String] {
        let fm = FileManager.default
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        var files: [String] = []

        let launchAgentsPath = "\(home)/Library/LaunchAgents"
        if let agents = try? fm.contentsOfDirectory(atPath: launchAgentsPath) {
            for agent in agents where agent.contains("magnetar") || agent.contains("elohim") {
                files.append("\(launchAgentsPath)/\(agent)")
            }
        }

        return files
    }

    func identifyPreferences() async -> [String] {
        let fm = FileManager.default
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        var files: [String] = []

        let prefsPath = "\(home)/Library/Preferences"
        if let prefs = try? fm.contentsOfDirectory(atPath: prefsPath) {
            for pref in prefs where pref.contains("magnetar") || pref.contains("elohim") {
                files.append("\(prefsPath)/\(pref)")
            }
        }

        return files
    }

    func identifyApplicationSupport() async -> [String] {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        let appSupportPath = "\(home)/Library/Application Support/MagnetarStudio"

        if FileManager.default.fileExists(atPath: appSupportPath) {
            return [appSupportPath]
        }

        return []
    }

    func identifyLogs() async -> [String] {
        let home = FileManager.default.homeDirectoryForCurrentUser.path
        var files: [String] = []

        let logsPath = "\(home)/Library/Logs/MagnetarStudio"
        if FileManager.default.fileExists(atPath: logsPath) {
            files.append(logsPath)
        }

        return files
    }

    func identifyTemporaryFiles() async -> [String] {
        let fm = FileManager.default
        var files: [String] = []

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

    func identifyAppBundle() async -> String {
        return "/Applications/MagnetarStudio.app"
    }
}
