import Foundation
import Observation

/// Vault workspace state and operations
@MainActor
@Observable
final class VaultStore {
    static let shared = VaultStore()

    // MARK: - Observable State

    var unlocked: Bool = false
    var vaultType: String = "real"  // "real" | "decoy"
    var currentFolder: String = "/"
    var folders: [VaultFolder] = []
    var files: [VaultFile] = []
    var previewFile: VaultFile?
    var previewData: Data?
    var isLoading = false
    var isUploading = false
    var error: String?

    // In-memory only (never persisted)
    private var passphrase: String?

    private let service = VaultService.shared

    private init() {}

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
                passphrase = password
                error = nil

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
        passphrase = nil
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

        isUploading = true
        defer { isUploading = false }

        do {
            _ = try await service.upload(
                fileURL: fileURL,
                folderPath: currentFolder,
                vaultType: vaultType,
                passphrase: passphrase
            )

            error = nil

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

        isLoading = true
        defer { isLoading = false }

        do {
            try await service.deleteFile(
                fileId: file.id,
                vaultType: vaultType,
                passphrase: passphrase
            )

            error = nil

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
        passphrase = nil
        vaultType = "real"
        currentFolder = "/"
        folders = []
        files = []
        previewFile = nil
        previewData = nil
        error = nil
    }
}
