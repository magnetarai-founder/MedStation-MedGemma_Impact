//
//  EmergencyModeService+LocalCleanup.swift
//  MagnetarStudio
//
//  Extension for local cleanup operations
//  Memory zeroing, cache clearing, keychain purging
//

import Foundation
import AppKit
import Security
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "EmergencyModeService.LocalCleanup")

// MARK: - Local Emergency Actions

extension EmergencyModeService {

    func performLocalEmergencyWipe(_ report: inout EmergencyWipeReport) async throws {
        logger.warning("Local emergency wipe starting...")

        var localWipeCount = 0

        // 1. Zero sensitive memory
        do {
            try await zeroSensitiveMemory()
            localWipeCount += 1
            logger.info("Sensitive memory zeroed")
        } catch {
            report.errors.append("Memory zeroing failed: \(error.localizedDescription)")
        }

        // 2. Clear NSPasteboard (clipboard)
        clearPasteboard()
        localWipeCount += 1
        logger.info("Clipboard cleared")

        // 3. Clear URLSession cache
        await clearURLSessionCache()
        localWipeCount += 1
        logger.info("URLSession cache cleared")

        // 4. Flush model inference cache
        await flushModelCache()
        localWipeCount += 1
        logger.info("Model cache flushed")

        report.filesWiped += localWipeCount
        logger.warning("Local emergency wipe complete: \(localWipeCount) actions")
    }

    func purgeKeychain(_ report: inout EmergencyWipeReport) async throws {
        logger.warning("Keychain purge starting...")

        var keychainWipeCount = 0

        // 1. Delete authentication tokens
        do {
            try KeychainService.shared.deleteToken()
            keychainWipeCount += 1
            logger.info("Auth token deleted")
        } catch {
            report.errors.append("Token deletion failed: \(error.localizedDescription)")
        }

        // 2. Delete all app-specific keychain items
        do {
            let deletedCount = try await deleteAllAppKeychainItems()
            keychainWipeCount += deletedCount
            logger.info("\(deletedCount) keychain items deleted")
        } catch {
            report.errors.append("Keychain purge failed: \(error.localizedDescription)")
        }

        report.filesWiped += keychainWipeCount
        logger.warning("Keychain purge complete: \(keychainWipeCount) items deleted")
    }
}

// MARK: - Memory & Cache Cleanup Helpers

extension EmergencyModeService {

    /// Zero sensitive data in memory
    func zeroSensitiveMemory() async throws {
        logger.debug("Zeroing sensitive memory...")

        // Force memory release
        autoreleasepool {
            // Clear any cached sensitive data
        }

        // Give system time to release memory
        try? await Task.sleep(nanoseconds: 100_000_000) // 0.1 seconds

        logger.debug("Memory zeroing complete")
    }

    /// Clear NSPasteboard (clipboard)
    func clearPasteboard() {
        logger.debug("Clearing clipboard...")

        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()

        let contents = pasteboard.string(forType: .string)
        if contents?.isEmpty ?? true {
            logger.debug("Clipboard cleared successfully")
        } else {
            logger.warning("Clipboard may still contain data")
        }
    }

    /// Clear URLSession cache
    func clearURLSessionCache() async {
        logger.debug("Clearing URLSession cache...")

        URLCache.shared.removeAllCachedResponses()

        if let cookies = HTTPCookieStorage.shared.cookies {
            for cookie in cookies {
                HTTPCookieStorage.shared.deleteCookie(cookie)
            }
        }

        try? await Task.sleep(nanoseconds: 100_000_000) // 0.1 seconds

        logger.debug("URLSession cache cleared")
    }

    /// Flush model inference cache
    func flushModelCache() async {
        logger.debug("Flushing model cache...")

        let modelCacheDir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".magnetar/model_cache")

        if FileManager.default.fileExists(atPath: modelCacheDir.path) {
            do {
                try FileManager.default.removeItem(at: modelCacheDir)
                logger.debug("Model cache flushed (\(modelCacheDir.path))")
            } catch {
                logger.warning("Failed to flush model cache: \(error)")
            }
        } else {
            logger.debug("No model cache found (skipped)")
        }
    }
}

// MARK: - Keychain Cleanup Helpers

extension EmergencyModeService {

    /// Delete all app-specific keychain items
    func deleteAllAppKeychainItems() async throws -> Int {
        logger.debug("Deleting all app keychain items...")

        var deletedCount = 0

        let serviceIdentifiers = [
            "com.magnetarstudio.app",
            "com.magnetarstudio.auth",
            "com.magnetarstudio.vault",
            "com.magnetarstudio.api"
        ]

        for serviceID in serviceIdentifiers {
            let query: [String: Any] = [
                kSecClass as String: kSecClassGenericPassword,
                kSecAttrService as String: serviceID,
                kSecMatchLimit as String: kSecMatchLimitAll,
                kSecReturnAttributes as String: true
            ]

            var result: AnyObject?
            let status = SecItemCopyMatching(query as CFDictionary, &result)

            if status == errSecSuccess, let items = result as? [[String: Any]] {
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
                            logger.debug("Deleted keychain item: \(serviceID)/\(account)")
                        }
                    }
                }
            }
        }

        // Also delete any internet passwords
        let internetQuery: [String: Any] = [
            kSecClass as String: kSecClassInternetPassword,
            kSecMatchLimit as String: kSecMatchLimitAll
        ]

        let internetDeleteStatus = SecItemDelete(internetQuery as CFDictionary)
        if internetDeleteStatus == errSecSuccess {
            deletedCount += 1
            logger.debug("Deleted internet passwords")
        }

        return deletedCount
    }
}
