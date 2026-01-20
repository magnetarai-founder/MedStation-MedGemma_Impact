//
//  VaultWorkspaceView.swift
//  MagnetarStudio (macOS)
//
//  Secure vault workspace with file management - Extracted from TeamWorkspace.swift
//

import SwiftUI

struct VaultWorkspace: View {
    @State private var vaultUnlocked: Bool = false
    @State private var password: String = ""
    @State private var showPassword: Bool = false
    @State private var authError: String? = nil
    @State private var isAuthenticating: Bool = false
    @State private var viewMode: VaultViewMode = .grid
    @State private var searchText: String = ""
    @State private var currentPath: [String] = ["/"]
    @State private var selectedFile: VaultFile? = nil
    @State private var showPreview: Bool = false

    // Real backend state
    @State private var files: [VaultFile] = []
    @State private var isLoadingFiles: Bool = false
    @State private var vaultError: String? = nil
    @State private var isUploading: Bool = false
    @State private var isCreatingFolder: Bool = false
    @State private var newFolderName: String = ""
    @State private var showNewFolderDialog: Bool = false
    @State private var fileToDelete: VaultFile? = nil
    @State private var showDeleteConfirmation: Bool = false

    @Environment(\.openWindow) private var openWindow

    private let vaultService = VaultService.shared

    var body: some View {
        Group {
            if vaultUnlocked {
                unlockedView
            } else {
                lockedView
            }
        }
        .sheet(isPresented: $showPreview) {
            if let file = selectedFile {
                FilePreviewModal(
                    file: file,
                    isPresented: $showPreview,
                    onDownload: {
                        Task {
                            await downloadFile(file)
                        }
                    },
                    onDelete: {
                        fileToDelete = file
                        showDeleteConfirmation = true
                    },
                    vaultPassword: password
                )
            }
        }
        .sheet(isPresented: $showNewFolderDialog) {
            NewFolderDialog(
                folderName: $newFolderName,
                isPresented: $showNewFolderDialog,
                onCreate: {
                    Task {
                        await createFolder()
                    }
                }
            )
        }
        .alert("Delete File", isPresented: $showDeleteConfirmation, presenting: fileToDelete) { file in
            Button("Cancel", role: .cancel) {
                showDeleteConfirmation = false
                fileToDelete = nil
            }
            Button("Delete", role: .destructive) {
                Task {
                    await deleteFile(file)
                }
                showDeleteConfirmation = false
                fileToDelete = nil
            }
        } message: { file in
            Text("Are you sure you want to delete '\(file.name)'? This action cannot be undone.")
        }
        .task {
            if vaultUnlocked {
                await loadFiles()
            }
        }
    }

    // MARK: - Locked View
    // Extracted to VaultLockScreen.swift (Phase 6.11)

    private var lockedView: some View {
        VaultLockScreen(
            password: $password,
            showPassword: $showPassword,
            authError: $authError,
            isAuthenticating: $isAuthenticating,
            onUnlock: unlockVault,
            onBiometricAuth: authenticateWithBiometrics
        )
    }

    // MARK: - Unlocked View

    private var unlockedView: some View {
        VStack(spacing: 0) {
            // Top bar - Extracted to VaultToolbar.swift (Phase 6.11)
            VaultToolbar(
                currentPath: currentPath,
                viewMode: $viewMode,
                searchText: $searchText,
                isCreatingFolder: $isCreatingFolder,
                isUploading: $isUploading,
                onNewFolder: { showNewFolderDialog = true },
                onUpload: uploadFile
            )
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color(.controlBackgroundColor))
            .overlay(
                Rectangle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(height: 1),
                alignment: .bottom
            )

            // Content
            if isLoadingFiles {
                VaultLoadingView()
            } else if let error = vaultError {
                VaultErrorView(error: error) {
                    Task {
                        await loadFiles()
                    }
                }
            } else if filteredFiles.isEmpty {
                VaultEmptyStateView()
            } else {
                if viewMode == .grid {
                    VaultGridView(
                        files: filteredFiles,
                        onFileSelect: handleFileSelect,
                        onFileDetach: handleFileDetach,
                        onDownload: { file in
                            Task {
                                await downloadFile(file)
                            }
                        },
                        onDelete: { file in
                            fileToDelete = file
                            showDeleteConfirmation = true
                        }
                    )
                } else {
                    VaultListView(
                        files: filteredFiles,
                        onFileSelect: handleFileSelect,
                        onFileDetach: handleFileDetach,
                        onDownload: { file in
                            Task {
                                await downloadFile(file)
                            }
                        },
                        onDelete: { file in
                            fileToDelete = file
                            showDeleteConfirmation = true
                        }
                    )
                }
            }
        }
    }

    // MARK: - Helper Methods

    private var filteredFiles: [VaultFile] {
        if searchText.isEmpty {
            return files
        }
        return files.filter { $0.name.localizedCaseInsensitiveContains(searchText) }
    }

    private func handleFileSelect(_ file: VaultFile) {
        if file.isFolder {
            navigateToFolder(file)
        } else {
            selectedFile = file
            showPreview = true
        }
    }

    private func handleFileDetach(_ file: VaultFile) {
        // Open file in a detached window
        let documentInfo = DetachedDocumentInfo(
            fileId: file.id,
            fileName: file.name,
            mimeType: file.mimeType,
            size: file.size,
            vaultType: "real"
        )
        openWindow(value: documentInfo)
    }

    // MARK: - Actions

    private func unlockVault() {
        isAuthenticating = true
        authError = nil

        // Simulate authentication (real backend integration would verify password)
        Task {
            try? await Task.sleep(for: .seconds(1))
            if password == "test" || password.count >= 4 {
                vaultUnlocked = true
                authError = nil
                await loadFiles()
            } else {
                authError = "Invalid password"
            }
            isAuthenticating = false
        }
    }

    private func authenticateWithBiometrics() {
        // Simulate biometric auth
        Task {
            try? await Task.sleep(for: .milliseconds(500))
            vaultUnlocked = true
            await loadFiles()
        }
    }

    // MARK: - Vault Operations

    @MainActor
    private func loadFiles() async {
        isLoadingFiles = true
        vaultError = nil

        do {
            let currentFolder = currentPath.last ?? "/"
            files = try await vaultService.listFiles(vaultType: "real", folderPath: currentFolder)
            vaultError = nil
        } catch let error as VaultError {
            if case .unauthorized = error {
                // Show setup modal
                vaultError = error.localizedDescription
                vaultUnlocked = false
            } else {
                vaultError = error.localizedDescription
            }
            files = []
        } catch {
            vaultError = "Failed to load vault: \(error.localizedDescription)"
            files = []
        }

        isLoadingFiles = false
    }

    private func uploadFile() {
        let panel = NSOpenPanel()
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false
        panel.canChooseFiles = true

        if panel.runModal() == .OK, let url = panel.url {
            Task {
                await performUpload(fileURL: url)
            }
        }
    }

    @MainActor
    private func performUpload(fileURL: URL) async {
        isUploading = true
        vaultError = nil

        do {
            let currentFolder = currentPath.last ?? "/"
            _ = try await vaultService.upload(
                fileURL: fileURL,
                folderPath: currentFolder,
                vaultType: "real",
                passphrase: password
            )

            // Refresh file list
            await loadFiles()
        } catch let error as VaultError {
            vaultError = "Upload failed: \(error.localizedDescription)"
        } catch {
            vaultError = "Upload failed: \(error.localizedDescription)"
        }

        isUploading = false
    }

    private func createFolder() async {
        guard !newFolderName.isEmpty else { return }

        isCreatingFolder = true
        vaultError = nil

        do {
            _ = try await vaultService.createFolder(
                name: newFolderName,
                folderPath: currentPath.last ?? "/",
                vaultType: "real",
                passphrase: password
            )

            // Refresh file list
            await loadFiles()
            newFolderName = ""
        } catch let error as VaultError {
            vaultError = "Failed to create folder: \(error.localizedDescription)"
        } catch {
            vaultError = "Failed to create folder: \(error.localizedDescription)"
        }

        isCreatingFolder = false
    }

    @MainActor
    private func downloadFile(_ file: VaultFile) async {
        let savePanel = NSSavePanel()
        savePanel.nameFieldStringValue = file.name

        if savePanel.runModal() == .OK, let destinationURL = savePanel.url {
            vaultError = nil

            do {
                let data = try await vaultService.download(
                    fileId: file.id,
                    vaultType: "real",
                    passphrase: password
                )
                try data.write(to: destinationURL)
            } catch let error as VaultError {
                vaultError = "Download failed: \(error.localizedDescription)"
            } catch {
                vaultError = "Download failed: \(error.localizedDescription)"
            }
        }
    }

    @MainActor
    private func deleteFile(_ file: VaultFile) async {
        // Optimistic delete
        let originalFiles = files
        files.removeAll { $0.id == file.id }

        do {
            try await vaultService.deleteFile(fileId: file.id)
            vaultError = nil
        } catch let error as VaultError {
            // Rollback on failure
            files = originalFiles
            vaultError = "Delete failed: \(error.localizedDescription)"
        } catch {
            // Rollback on failure
            files = originalFiles
            vaultError = "Delete failed: \(error.localizedDescription)"
        }
    }

    private func navigateToFolder(_ folder: VaultFile) {
        guard folder.isFolder else { return }

        if let folderPath = folder.folderPath {
            currentPath.append(folderPath)
        } else {
            currentPath.append(folder.name)
        }

        Task {
            await loadFiles()
        }
    }
}
