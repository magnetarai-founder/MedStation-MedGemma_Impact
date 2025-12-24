//
//  VaultComponents.swift
//  MagnetarStudio (macOS)
//
//  Vault supporting components and modals - Extracted from TeamWorkspace.swift
//

import SwiftUI

// MARK: - Supporting Types

enum VaultViewMode {
    case grid
    case list
}

// Legacy mock file model for the UI preview; renamed to avoid clashing with real VaultFile model.
struct LegacyVaultFile: Identifiable {
    let id = UUID()
    let name: String
    let size: String
    let modified: String
    let mimeType: String

    var mimeIcon: String {
        switch mimeType {
        case "image": return "photo"
        case "video": return "video"
        case "audio": return "music.note"
        case "pdf": return "doc.text"
        case "zip": return "archivebox"
        case "code": return "chevron.left.forwardslash.chevron.right"
        default: return "doc"
        }
    }

    var mimeColor: Color {
        switch mimeType {
        case "image": return .purple
        case "video": return .pink
        case "audio": return .green
        case "pdf": return .red
        case "zip": return .yellow
        case "code": return .indigo
        default: return .gray
        }
    }

    static let mockFiles = [
        LegacyVaultFile(name: "Confidential Report.pdf", size: "2.4 MB", modified: "2 hours ago", mimeType: "pdf"),
        LegacyVaultFile(name: "Team Photo.jpg", size: "1.8 MB", modified: "Yesterday", mimeType: "image"),
        LegacyVaultFile(name: "Project Source.zip", size: "15.2 MB", modified: "3 days ago", mimeType: "zip"),
        LegacyVaultFile(name: "Meeting Recording.mp4", size: "45.6 MB", modified: "Last week", mimeType: "video"),
        LegacyVaultFile(name: "Secret Keys.txt", size: "12 KB", modified: "2 weeks ago", mimeType: "code")
    ]
}

// MARK: - New Folder Dialog

struct NewFolderDialog: View {
    @Binding var folderName: String
    @Binding var isPresented: Bool
    let onCreate: () -> Void

    var body: some View {
        VStack(spacing: 24) {
            // Header
            HStack {
                Text("New Folder")
                    .font(.system(size: 20, weight: .semibold))

                Spacer()

                Button {
                    isPresented = false
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 16))
                        .foregroundColor(.secondary)
                        .frame(width: 28, height: 28)
                }
                .buttonStyle(.plain)
            }

            Divider()

            // Form
            VStack(alignment: .leading, spacing: 12) {
                Text("Folder Name")
                    .font(.headline)

                TextField("Enter folder name", text: $folderName)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit {
                        onCreate()
                        isPresented = false
                    }
            }

            Spacer()

            // Footer buttons
            HStack {
                Spacer()

                Button("Cancel") {
                    isPresented = false
                }
                .keyboardShortcut(.cancelAction)

                Button("Create") {
                    onCreate()
                    isPresented = false
                }
                .keyboardShortcut(.defaultAction)
                .disabled(folderName.isEmpty)
            }
        }
        .padding(24)
        .frame(width: 400, height: 250)
        .background(Color(nsColor: .windowBackgroundColor))
    }
}

// MARK: - File Preview Modal

struct FilePreviewModal: View {
    let file: VaultFile
    @Binding var isPresented: Bool
    let onDownload: () -> Void
    let onDelete: () -> Void
    let vaultPassword: String

    @State private var isDownloading: Bool = false
    @State private var downloadError: String? = nil
    @State private var downloadSuccess: Bool = false

    private let vaultService = VaultService.shared

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(file.name)
                        .font(.system(size: 16, weight: .semibold))

                    HStack(spacing: 8) {
                        Text(file.mimeType?.uppercased() ?? "FILE")
                            .font(.system(size: 12))
                            .foregroundColor(.secondary)

                        Text("•")
                            .font(.system(size: 12))
                            .foregroundColor(.secondary)

                        Text(file.sizeFormatted)
                            .font(.system(size: 12))
                            .foregroundColor(.secondary)
                    }
                }

                Spacer()

                Button {
                    isPresented = false
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 16))
                        .foregroundColor(.secondary)
                        .frame(width: 32, height: 32)
                }
                .buttonStyle(.plain)
            }
            .padding(24)
            .background(Color(.controlBackgroundColor))
            .overlay(
                Rectangle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(height: 1),
                alignment: .bottom
            )

            // Body
            VStack(spacing: 16) {
                Image(systemName: file.mimeIcon)
                    .font(.system(size: 64))
                    .foregroundColor(Color(file.mimeColor))

                Text("Preview for \(file.mimeType ?? "unknown") files")
                    .font(.title2)

                Text("File preview rendering will appear here")
                    .font(.subheadline)
                    .foregroundColor(.secondary)

                // Download status messages
                if downloadSuccess {
                    HStack(spacing: 8) {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(.green)
                        Text("File downloaded successfully")
                            .font(.system(size: 14))
                            .foregroundColor(.green)
                    }
                    .padding(.top, 8)
                }

                if let error = downloadError {
                    HStack(spacing: 8) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(.red)
                        Text(error)
                            .font(.system(size: 14))
                            .foregroundColor(.red)
                    }
                    .padding(.top, 8)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding(24)

            // Footer
            HStack(spacing: 12) {
                Button {
                    onDelete()
                    isPresented = false
                } label: {
                    HStack(spacing: 8) {
                        Image(systemName: "trash")
                            .font(.system(size: 16))
                        Text("Delete")
                            .font(.system(size: 14, weight: .medium))
                    }
                    .foregroundColor(.red)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .strokeBorder(Color.red, lineWidth: 1)
                    )
                }
                .buttonStyle(.plain)
                .disabled(isDownloading)

                Spacer()

                Button {
                    Task {
                        await handleDownload()
                    }
                } label: {
                    HStack(spacing: 8) {
                        if isDownloading {
                            ProgressView()
                                .scaleEffect(0.8)
                                .frame(width: 16, height: 16)
                        } else {
                            Image(systemName: downloadSuccess ? "checkmark.circle" : "arrow.down.circle")
                                .font(.system(size: 16))
                        }
                        Text(isDownloading ? "Downloading..." : (downloadSuccess ? "Downloaded" : "Download"))
                            .font(.system(size: 14, weight: .medium))
                    }
                    .foregroundColor(.white)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(downloadSuccess ? Color.green : Color.magnetarPrimary)
                    )
                }
                .buttonStyle(.plain)
                .disabled(isDownloading || downloadSuccess)
            }
            .padding(24)
            .background(Color(.controlBackgroundColor))
            .overlay(
                Rectangle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(height: 1),
                alignment: .top
            )
        }
        .frame(width: 700, height: 600)
        .background(Color(.windowBackgroundColor))
    }

    // MARK: - Download Handler

    @MainActor
    private func handleDownload() async {
        // Reset states
        downloadError = nil
        downloadSuccess = false

        // Show save panel
        let savePanel = NSSavePanel()
        savePanel.nameFieldStringValue = file.name
        savePanel.canCreateDirectories = true
        savePanel.showsTagField = false

        let response = savePanel.runModal()

        // User cancelled
        guard response == .OK, let destinationURL = savePanel.url else {
            return
        }

        // Start download
        isDownloading = true

        do {
            let data = try await vaultService.download(
                fileId: file.id,
                vaultType: "real",
                passphrase: vaultPassword
            )

            try data.write(to: destinationURL)

            downloadSuccess = true
            isDownloading = false

            // Auto-close after success (optional)
            Task {
                try? await Task.sleep(for: .milliseconds(1500))
                isPresented = false
            }
        } catch let error as VaultError {
            downloadError = error.localizedDescription
            isDownloading = false
        } catch {
            downloadError = "Download failed: \(error.localizedDescription)"
            isDownloading = false
        }
    }
}
