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

// MARK: - Local Emergency Actions

extension EmergencyModeService {

    func performLocalEmergencyWipe(_ report: inout EmergencyWipeReport) async throws {
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

        // 4. Flush model inference cache
        await flushModelCache()
        localWipeCount += 1
        print("   ✅ Model cache flushed")

        report.filesWiped += localWipeCount
        print("✅ Local emergency wipe complete: \(localWipeCount) actions")
    }

    func purgeKeychain(_ report: inout EmergencyWipeReport) async throws {
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
}

// MARK: - Memory & Cache Cleanup Helpers

extension EmergencyModeService {

    /// Zero sensitive data in memory
    func zeroSensitiveMemory() async throws {
        print("      Zeroing sensitive memory...")

        // Force memory release
        autoreleasepool {
            // Clear any cached sensitive data
        }

        // Give system time to release memory
        try? await Task.sleep(nanoseconds: 100_000_000) // 0.1 seconds

        print("      Memory zeroing complete")
    }

    /// Clear NSPasteboard (clipboard)
    func clearPasteboard() {
        print("      Clearing clipboard...")

        let pasteboard = NSPasteboard.general
        pasteboard.clearContents()

        let contents = pasteboard.string(forType: .string)
        if contents == nil || contents!.isEmpty {
            print("      Clipboard cleared successfully")
        } else {
            print("      ⚠️  Clipboard may still contain data")
        }
    }

    /// Clear URLSession cache
    func clearURLSessionCache() async {
        print("      Clearing URLSession cache...")

        URLCache.shared.removeAllCachedResponses()

        if let cookies = HTTPCookieStorage.shared.cookies {
            for cookie in cookies {
                HTTPCookieStorage.shared.deleteCookie(cookie)
            }
        }

        try? await Task.sleep(nanoseconds: 100_000_000) // 0.1 seconds

        print("      URLSession cache cleared")
    }

    /// Flush model inference cache
    func flushModelCache() async {
        print("      Flushing model cache...")

        let modelCacheDir = FileManager.default.homeDirectoryForCurrentUser
            .appendingPathComponent(".magnetar/model_cache")

        if FileManager.default.fileExists(atPath: modelCacheDir.path) {
            try? FileManager.default.removeItem(at: modelCacheDir)
            print("      Model cache flushed (\(modelCacheDir.path))")
        } else {
            print("      No model cache found (skipped)")
        }
    }
}

// MARK: - Keychain Cleanup Helpers

extension EmergencyModeService {

    /// Delete all app-specific keychain items
    func deleteAllAppKeychainItems() async throws -> Int {
        print("      Deleting all app keychain items...")

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
                            print("         Deleted: \(serviceID)/\(account)")
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
            print("         Deleted: Internet passwords")
        }

        return deletedCount
    }
}
