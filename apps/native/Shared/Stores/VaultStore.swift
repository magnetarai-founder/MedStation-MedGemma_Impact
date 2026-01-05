import Foundation
import Observation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "VaultStore")

/// Vault workspace state and operations
/// SECURITY: Passphrase is stored in Keychain (OS-protected) not plain memory
@MainActor
@Observable
final class VaultStore {
    static let shared = VaultStore()

    // MARK: - State Persistence Keys
    private static let currentFolderKey = "vault.currentFolder"

    // MARK: - Observable State

    var unlocked: Bool = false
    var vaultType: String = "real"  // "real" | "decoy"
    var currentFolder: String = "/" {
        didSet { UserDefaults.standard.set(currentFolder, forKey: Self.currentFolderKey) }
    }
    var folders: [VaultFolder] = []
    var files: [VaultFile] = []
    var previewFile: VaultFile?
    var previewData: Data?
    var isLoading = false
    var isUploading = false
    var error: String?
    var isSyncing = false

    // SECURITY: Auto-lock timeout (15 minutes of inactivity)
    private static let autoLockTimeoutSeconds: TimeInterval = 15 * 60

    // Auto-lock timer - nonisolated(unsafe) for deinit access
    @ObservationIgnored
    private nonisolated(unsafe) var autoLockTimer: Timer?

    // Keychain service for secure passphrase storage
    @ObservationIgnored
    private let keychain = KeychainService.shared

    private let service = VaultService.shared
    private var syncService: SyncService { SyncService.shared }
    private var cloudSyncEnabled: Bool {
        UserDefaults.standard.bool(forKey: "cloudSyncEnabled")
    }

    private init() {
        // Restore persisted state
        if let savedFolder = UserDefaults.standard.string(forKey: Self.currentFolderKey) {
            self.currentFolder = savedFolder
        }
    }

    deinit {
        autoLockTimer?.invalidate()
        // Clear passphrase from Keychain on dealloc
        try? keychain.deleteToken(forKey: KeychainService.vaultSessionKey)
    }

    // MARK: - Passphrase Management (Keychain-backed)

    /// Store passphrase securely in Keychain
    private func storePassphrase(_ password: String) {
        do {
            try keychain.saveToken(password, forKey: KeychainService.vaultSessionKey)
        } catch {
            logger.error("Failed to store vault passphrase in Keychain: \(error.localizedDescription)")
        }
    }

    /// Retrieve passphrase from Keychain
    private var passphrase: String? {
        keychain.loadToken(forKey: KeychainService.vaultSessionKey)
    }

    /// Clear passphrase from Keychain
    private func clearPassphrase() {
        do {
            try keychain.deleteToken(forKey: KeychainService.vaultSessionKey)
        } catch {
            logger.error("Failed to clear vault passphrase from Keychain: \(error.localizedDescription)")
        }
    }

    /// Reset auto-lock timer (called on vault activity)
    private func resetAutoLockTimer() {
        autoLockTimer?.invalidate()
        autoLockTimer = Timer.scheduledTimer(
            withTimeInterval: Self.autoLockTimeoutSeconds,
            repeats: false
        ) { [weak self] _ in
            Task { @MainActor in
                self?.autoLock()
            }
        }
    }

    /// Auto-lock triggered by inactivity timeout
    private func autoLock() {
        guard unlocked else { return }
        logger.info("Vault auto-locked due to inactivity")
        lock()
    }

    // MARK: - Unlock

    func unlock(password: String, requireTouchId: Bool = false) async {
        isLoading = true
        defer { isLoading = false }

        do {
            let success = try await service.unlock(
                password: password,
                requireTouchId: requireTouchId
            )

            if success {
                unlocked = true
                // SECURITY: Store passphrase in Keychain, not plain memory
                storePassphrase(password)
                error = nil

                // Start auto-lock timer
                resetAutoLockTimer()

                // Load root folder
                await load(folderPath: "/")
            } else {
                error = "Unlock failed - incorrect password"
            }
        } catch {
            self.error = "Unlock failed: \(error.localizedDescription)"
        }
    }

    func lock() {
        unlocked = false
        // SECURITY: Clear passphrase from Keychain
        clearPassphrase()
        // Stop auto-lock timer
        autoLockTimer?.invalidate()
        autoLockTimer = nil

        currentFolder = "/"
        folders = []
        files = []
        previewFile = nil
        previewData = nil
        error = nil
    }

    // MARK: - Navigation

    func load(folderPath: String) async {
        guard unlocked else {
            error = "Vault is locked"
            return
        }

        // Reset auto-lock timer on activity
        resetAutoLockTimer()

        isLoading = true
        defer { isLoading = false }

        do {
            let response = try await service.list(
                folderPath: folderPath,
                vaultType: vaultType,
                passphrase: passphrase
            )

            currentFolder = folderPath
            folders = response.folders
            files = response.files
            error = nil
        } catch {
            self.error = "Failed to load folder: \(error.localizedDescription)"
        }
    }

    func setFolder(path: String) async {
        await load(folderPath: path)
    }

    func navigateUp() async {
        guard currentFolder != "/" else { return }

        let components = currentFolder.split(separator: "/")
        if components.isEmpty {
            await load(folderPath: "/")
        } else {
            let parentPath = "/" + components.dropLast().joined(separator: "/")
            await load(folderPath: parentPath)
        }
    }

    // MARK: - File Operations

    func download(file: VaultFile) async -> Data? {
        guard unlocked else {
            error = "Vault is locked"
            return nil
        }

        // Reset auto-lock timer on activity
        resetAutoLockTimer()

        isLoading = true
        defer { isLoading = false }

        do {
            let data = try await service.download(
                fileId: file.id,
                vaultType: vaultType,
                passphrase: passphrase
            )

            error = nil
            return data
        } catch {
            self.error = "Download failed: \(error.localizedDescription)"
            return nil
        }
    }

    func preview(file: VaultFile) async {
        previewFile = file
        previewData = await download(file: file)
    }

    func closePreview() {
        previewFile = nil
        previewData = nil
    }

    func upload(fileURL: URL) async {
        guard unlocked else {
            error = "Vault is locked"
            return
        }

        // Reset auto-lock timer on activity
        resetAutoLockTimer()

        isUploading = true
        defer { isUploading = false }

        do {
            let uploadedFile = try await service.upload(
                fileURL: fileURL,
                folderPath: currentFolder,
                vaultType: vaultType,
                passphrase: passphrase
            )

            error = nil

            // Queue sync for the new file
            queueFileChangeForSync(fileId: uploadedFile.id, action: "upload")

            // Reload current folder to show new file
            await load(folderPath: currentFolder)
        } catch {
            self.error = "Upload failed: \(error.localizedDescription)"
        }
    }

    func deleteFile(_ file: VaultFile) async {
        guard unlocked else {
            error = "Vault is locked"
            return
        }

        // Reset auto-lock timer on activity
        resetAutoLockTimer()

        isLoading = true
        defer { isLoading = false }

        do {
            try await service.deleteFile(
                fileId: file.id,
                vaultType: vaultType,
                passphrase: passphrase
            )

            error = nil

            // Queue sync for the deleted file
            queueFileChangeForSync(fileId: file.id, action: "delete")

            // Remove from local list
            files.removeAll { $0.id == file.id }
        } catch {
            self.error = "Delete failed: \(error.localizedDescription)"
        }
    }

    // MARK: - Folder Operations

    func createFolder(name: String) async {
        guard unlocked else {
            error = "Vault is locked"
            return
        }

        // Reset auto-lock timer on activity
        resetAutoLockTimer()

        isLoading = true
        defer { isLoading = false }

        do {
            // Build full path
            let newPath = currentFolder == "/" ? "/\(name)" : "\(currentFolder)/\(name)"

            _ = try await service.createFolder(
                folderPath: newPath,
                vaultType: vaultType,
                passphrase: passphrase
            )

            error = nil

            // Reload current folder to show new folder
            await load(folderPath: currentFolder)
        } catch {
            self.error = "Create folder failed: \(error.localizedDescription)"
        }
    }

    func deleteFolder(_ folder: VaultFolder) async {
        guard unlocked else {
            error = "Vault is locked"
            return
        }

        // Reset auto-lock timer on activity
        resetAutoLockTimer()

        isLoading = true
        defer { isLoading = false }

        do {
            try await service.deleteFolder(
                folderPath: folder.folderPath,
                vaultType: vaultType,
                passphrase: passphrase
            )

            error = nil

            // Remove from local list
            folders.removeAll { $0.id == folder.id }
        } catch {
            self.error = "Delete folder failed: \(error.localizedDescription)"
        }
    }

    // MARK: - Vault Mode

    func switchVaultType(_ type: String) async {
        vaultType = type
        currentFolder = "/"
        folders = []
        files = []

        if unlocked {
            await load(folderPath: "/")
        }
    }

    // MARK: - Helpers

    /// Breadcrumb components for navigation
    var breadcrumbComponents: [String] {
        guard currentFolder != "/" else { return [] }
        return currentFolder.split(separator: "/").map(String.init)
    }

    /// Get full path for breadcrumb index
    func pathForBreadcrumb(index: Int) -> String {
        let components = breadcrumbComponents
        guard index < components.count else { return "/" }

        if index == -1 {
            return "/"
        }

        return "/" + components.prefix(index + 1).joined(separator: "/")
    }

    /// Clear all state (call on logout)
    func clear() {
        unlocked = false
        // SECURITY: Clear passphrase from Keychain
        clearPassphrase()
        // Stop auto-lock timer
        autoLockTimer?.invalidate()
        autoLockTimer = nil

        vaultType = "real"
        currentFolder = "/"
        folders = []
        files = []
        previewFile = nil
        previewData = nil
        error = nil
    }

    // MARK: - Cloud Sync

    /// Sync vault to cloud
    func syncToCloud() async {
        guard cloudSyncEnabled else {
            logger.debug("Cloud sync disabled, skipping")
            return
        }

        isSyncing = true
        defer { isSyncing = false }

        do {
            // Prepare vault changes for sync
            let changes = buildVaultChanges()

            if !changes.isEmpty {
                _ = try await syncService.syncVault(
                    changes: changes,
                    direction: .upload
                )
                logger.info("Vault synced to cloud: \(changes.count) items")
            }
        } catch SyncError.offlineMode {
            logger.info("Offline - vault changes queued for later sync")
        } catch {
            logger.error("Vault sync failed: \(error)")
        }
    }

    /// Sync vault from cloud (download)
    func syncFromCloud() async {
        guard cloudSyncEnabled else {
            logger.debug("Cloud sync disabled, skipping")
            return
        }

        isSyncing = true
        defer { isSyncing = false }

        do {
            let response = try await syncService.syncVault(
                changes: [],
                direction: .download
            )

            // Apply server changes to local vault
            for change in response.serverChanges {
                await applyRemoteChange(change)
            }

            if !response.conflicts.isEmpty {
                logger.warning("Vault sync has \(response.conflicts.count) conflicts")
            }

            // Refresh current folder to show changes
            await load(folderPath: currentFolder)
            logger.info("Vault synced from cloud: \(response.serverChanges.count) items")
        } catch SyncError.offlineMode {
            logger.info("Offline - cannot sync from cloud")
        } catch {
            logger.error("Vault download sync failed: \(error)")
            self.error = "Cloud sync failed: \(error.localizedDescription)"
        }
    }

    /// Build vault changes for sync
    private func buildVaultChanges() -> [SyncChange] {
        var changes: [SyncChange] = []

        // Create change entries for current folder contents
        for file in files {
            let change = SyncChange(
                resourceId: file.id,
                data: [
                    "name": AnyCodable(file.name),
                    "folder_path": AnyCodable(currentFolder),
                    "mime_type": AnyCodable(file.mimeType ?? "application/octet-stream"),
                    "size": AnyCodable(file.size ?? 0),
                    "vault_type": AnyCodable(vaultType)
                ],
                modifiedAt: file.uploadedAt,  // VaultFile.uploadedAt is already ISO8601 string
                vectorClock: nil
            )
            changes.append(change)
        }

        return changes
    }

    /// Apply a remote change to local vault
    private func applyRemoteChange(_ change: SyncChange) async {
        // For now, just refresh - in production, would merge changes
        logger.debug("Applying remote change: \(change.resourceId)")
    }

    /// Queue a file change for sync
    private func queueFileChangeForSync(fileId: String, action: String) {
        guard cloudSyncEnabled else { return }

        let change = SyncChange(
            resourceId: fileId,
            data: [
                "action": AnyCodable(action),
                "folder_path": AnyCodable(currentFolder),
                "vault_type": AnyCodable(vaultType)
            ],
            modifiedAt: ISO8601DateFormatter().string(from: Date()),
            vectorClock: nil
        )

        syncService.queueOfflineOperation(
            resource: "vault",
            changes: [change],
            direction: .upload
        )
    }
}
