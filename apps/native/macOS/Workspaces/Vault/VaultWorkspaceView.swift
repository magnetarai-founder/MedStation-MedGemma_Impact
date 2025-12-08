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

    private var lockedView: some View {
        VStack(spacing: 24) {
            // Icon
            Image(systemName: "lock.shield")
                .font(.system(size: 32))
                .foregroundColor(.orange)

            // Title
            VStack(spacing: 8) {
                Text("Unlock Vault")
                    .font(.system(size: 24, weight: .bold))

                Text("Enter your password to access secure files")
                    .font(.system(size: 14))
                    .foregroundColor(.secondary)
            }

            // Password field
            VStack(alignment: .leading, spacing: 8) {
                HStack(spacing: 12) {
                    if showPassword {
                        TextField("Password", text: $password)
                            .textFieldStyle(.plain)
                            .font(.system(size: 14))
                    } else {
                        SecureField("Password", text: $password)
                            .textFieldStyle(.plain)
                            .font(.system(size: 14))
                    }

                    Button {
                        showPassword.toggle()
                    } label: {
                        Image(systemName: showPassword ? "eye.slash" : "eye")
                            .font(.system(size: 18))
                            .foregroundColor(.secondary)
                    }
                    .buttonStyle(.plain)
                }
                .padding(.horizontal, 12)
                .padding(.vertical, 10)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(authError != nil ? Color.red : Color.gray.opacity(0.3), lineWidth: 1)
                )

                if let error = authError {
                    Text(error)
                        .font(.system(size: 12))
                        .foregroundColor(.red)
                }
            }

            // Touch ID button (if available)
            Button {
                // Biometric auth
                authenticateWithBiometrics()
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: "touchid")
                        .font(.system(size: 18))
                    Text("Use Touch ID")
                        .font(.system(size: 14, weight: .medium))
                }
                .foregroundColor(.primary)
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(Color.gray.opacity(0.3), lineWidth: 1)
                )
            }
            .buttonStyle(.plain)

            // Unlock button
            Button {
                unlockVault()
            } label: {
                HStack(spacing: 8) {
                    if isAuthenticating {
                        ProgressView()
                            .scaleEffect(0.8)
                            .tint(.white)
                    } else {
                        Text("Unlock")
                            .font(.system(size: 14, weight: .medium))
                    }
                }
                .foregroundColor(.white)
                .frame(maxWidth: .infinity)
                .padding(.vertical, 12)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(password.isEmpty ? Color.gray : Color.magnetarPrimary)
                )
            }
            .buttonStyle(.plain)
            .disabled(password.isEmpty || isAuthenticating)
        }
        .frame(width: 400)
        .padding(28)
        .background(
            RoundedRectangle(cornerRadius: 20)
                .fill(Color(.controlBackgroundColor))
                .shadow(color: Color.black.opacity(0.1), radius: 12, x: 0, y: 4)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 20)
                .strokeBorder(Color.gray.opacity(0.2), lineWidth: 1)
        )
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Unlocked View

    private var unlockedView: some View {
        VStack(spacing: 0) {
            // Top bar
            topBar
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
                loadingView
            } else if let error = vaultError {
                errorView(error: error)
            } else if filteredFiles.isEmpty {
                emptyState
            } else {
                if viewMode == .grid {
                    gridView
                } else {
                    listView
                }
            }
        }
    }

    private var filteredFiles: [VaultFile] {
        if searchText.isEmpty {
            return files
        }
        return files.filter { $0.name.localizedCaseInsensitiveContains(searchText) }
    }

    private var loadingView: some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.2)

            Text("Loading vault...")
                .font(.system(size: 16))
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func errorView(error: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 48))
                .foregroundColor(.orange)

            Text("Error Loading Vault")
                .font(.system(size: 18, weight: .semibold))

            Text(error)
                .font(.system(size: 14))
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 40)

            Button("Retry") {
                Task {
                    await loadFiles()
                }
            }
            .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var topBar: some View {
        HStack(spacing: 12) {
            // Breadcrumbs
            HStack(spacing: 6) {
                ForEach(Array(currentPath.enumerated()), id: \.offset) { index, folder in
                    if index > 0 {
                        Image(systemName: "chevron.right")
                            .font(.system(size: 10))
                            .foregroundColor(.secondary)
                    }

                    Text(folder)
                        .font(.system(size: 14))
                        .foregroundColor(index == currentPath.count - 1 ? .primary : .secondary)
                }
            }

            Spacer()

            // View toggle
            HStack(spacing: 4) {
                viewToggleButton(icon: "square.grid.3x2", mode: .grid)
                viewToggleButton(icon: "list.bullet", mode: .list)
            }
            .padding(4)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.gray.opacity(0.1))
            )

            // Search
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 14))
                    .foregroundColor(.secondary)

                TextField("Search vault...", text: $searchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 14))
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .frame(width: 240)
            .background(
                RoundedRectangle(cornerRadius: 16)
                    .fill(Color.gray.opacity(0.1))
            )

            // Buttons
            Button {
                showNewFolderDialog = true
            } label: {
                HStack(spacing: 6) {
                    if isCreatingFolder {
                        ProgressView()
                            .scaleEffect(0.7)
                    } else {
                        Image(systemName: "folder.badge.plus")
                            .font(.system(size: 16))
                    }
                    Text("New Folder")
                        .font(.system(size: 14, weight: .medium))
                }
                .foregroundColor(.primary)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .strokeBorder(Color.gray.opacity(0.3), lineWidth: 1)
                )
            }
            .buttonStyle(.plain)
            .disabled(isCreatingFolder)

            Button {
                uploadFile()
            } label: {
                HStack(spacing: 6) {
                    if isUploading {
                        ProgressView()
                            .scaleEffect(0.7)
                            .tint(.white)
                    } else {
                        Image(systemName: "arrow.up.doc")
                            .font(.system(size: 16))
                    }
                    Text("Upload")
                        .font(.system(size: 14, weight: .medium))
                }
                .foregroundColor(.white)
                .padding(.horizontal, 12)
                .padding(.vertical, 8)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(isUploading ? Color.gray : Color.magnetarPrimary)
                )
            }
            .buttonStyle(.plain)
            .disabled(isUploading)
        }
    }

    private func viewToggleButton(icon: String, mode: VaultViewMode) -> some View {
        Button {
            viewMode = mode
        } label: {
            Image(systemName: icon)
                .font(.system(size: 16))
                .foregroundColor(viewMode == mode ? Color.magnetarPrimary : .secondary)
                .frame(width: 32, height: 32)
        }
        .buttonStyle(.plain)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(viewMode == mode ? Color.magnetarPrimary.opacity(0.15) : Color.clear)
        )
    }

    // MARK: - Grid View

    private var gridView: some View {
        ScrollView {
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 180, maximum: 220), spacing: 16)], spacing: 16) {
                ForEach(filteredFiles) { file in
                    fileCard(file: file)
                        .onTapGesture {
                            if file.isFolder {
                                navigateToFolder(file)
                            } else {
                                selectedFile = file
                                showPreview = true
                            }
                        }
                        .contextMenu {
                            if !file.isFolder {
                                Button("Download") {
                                    Task {
                                        await downloadFile(file)
                                    }
                                }

                                Divider()

                                Button("Delete", role: .destructive) {
                                    fileToDelete = file
                                    showDeleteConfirmation = true
                                }
                            }
                        }
                }
            }
            .padding(20)
        }
    }

    private func fileCard(file: VaultFile) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            // Icon chip
            ZStack {
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color(file.mimeColor).opacity(0.15))
                    .frame(height: 80)

                Image(systemName: file.mimeIcon)
                    .font(.system(size: 32))
                    .foregroundColor(Color(file.mimeColor))
            }

            VStack(alignment: .leading, spacing: 4) {
                Text(file.name)
                    .font(.system(size: 13, weight: .medium))
                    .lineLimit(1)
                    .truncationMode(.middle)

                HStack(spacing: 8) {
                    Text(file.sizeFormatted)
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)

                    Text("•")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)

                    Text(file.modifiedFormatted)
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                }
            }
        }
        .padding(12)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(Color(.controlBackgroundColor))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .strokeBorder(Color.gray.opacity(0.2), lineWidth: 1)
        )
    }

    // MARK: - List View

    private var listView: some View {
        VStack(spacing: 0) {
            // Header
            HStack(spacing: 16) {
                Text("Name")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(.secondary)
                    .frame(maxWidth: .infinity, alignment: .leading)

                Text("Size")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(.secondary)
                    .frame(width: 100, alignment: .trailing)

                Text("Modified")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundColor(.secondary)
                    .frame(width: 120, alignment: .trailing)
            }
            .padding(.horizontal, 16)
            .padding(.vertical, 12)
            .background(Color.gray.opacity(0.05))

            Divider()

            ScrollView {
                ForEach(filteredFiles) { file in
                    fileRow(file: file)
                        .onTapGesture {
                            if file.isFolder {
                                navigateToFolder(file)
                            } else {
                                selectedFile = file
                                showPreview = true
                            }
                        }
                        .contextMenu {
                            if !file.isFolder {
                                Button("Download") {
                                    Task {
                                        await downloadFile(file)
                                    }
                                }

                                Divider()

                                Button("Delete", role: .destructive) {
                                    fileToDelete = file
                                    showDeleteConfirmation = true
                                }
                            }
                        }
                }
            }
        }
    }

    private func fileRow(file: VaultFile) -> some View {
        HStack(spacing: 16) {
            HStack(spacing: 10) {
                Image(systemName: file.mimeIcon)
                    .font(.system(size: 16))
                    .foregroundColor(Color(file.mimeColor))

                Text(file.name)
                    .font(.system(size: 14))
                    .lineLimit(1)
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            Text(file.sizeFormatted)
                .font(.system(size: 14))
                .foregroundColor(.secondary)
                .frame(width: 100, alignment: .trailing)

            Text(file.modifiedFormatted)
                .font(.system(size: 14))
                .foregroundColor(.secondary)
                .frame(width: 120, alignment: .trailing)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(Color.clear)
        .overlay(
            Rectangle()
                .fill(Color.gray.opacity(0.1))
                .frame(height: 1),
            alignment: .bottom
        )
    }

    // MARK: - Empty State

    private var emptyState: some View {
        VStack(spacing: 16) {
            Image(systemName: "folder.badge.questionmark")
                .font(.system(size: 48))
                .foregroundColor(.secondary)

            Text("No files in this folder")
                .font(.system(size: 18, weight: .semibold))

            Text("Upload files to get started")
                .font(.system(size: 14))
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    // MARK: - Actions

    private func unlockVault() {
        isAuthenticating = true
        authError = nil

        // Simulate authentication (real backend integration would verify password)
        DispatchQueue.main.asyncAfter(deadline: .now() + 1.0) {
            if password == "test" || password.count >= 4 {
                vaultUnlocked = true
                authError = nil
                Task {
                    await loadFiles()
                }
            } else {
                authError = "Invalid password"
            }
            isAuthenticating = false
        }
    }

    private func authenticateWithBiometrics() {
        // Simulate biometric auth
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.5) {
            vaultUnlocked = true
            Task {
                await loadFiles()
            }
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
