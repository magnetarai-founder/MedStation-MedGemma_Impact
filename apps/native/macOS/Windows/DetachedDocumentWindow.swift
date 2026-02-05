//
//  DetachedDocumentWindow.swift
//  MagnetarStudio (macOS)
//
//  A standalone document window for viewing vault files
//  Opened via double-click from Files tab or Quick Action menu
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "DetachedDocumentWindow")

// MARK: - Document Info for Window

/// Lightweight struct to pass document info to detached windows
struct DetachedDocumentInfo: Codable, Hashable, Sendable {
    let fileId: String
    let fileName: String
    let mimeType: String?
    let size: Int
    let vaultType: String
}

// MARK: - Detached Document Window

struct DetachedDocumentWindow: View {
    let documentInfo: DetachedDocumentInfo

    @State private var isLoading = true
    @State private var fileData: Data?
    @State private var error: String?
    @State private var isDownloading = false

    @Environment(\.dismiss) private var dismiss

    private let vaultService = VaultService.shared

    var body: some View {
        VStack(spacing: 0) {
            // Header
            documentHeader

            Divider()

            // Content
            documentContent
        }
        .frame(minWidth: 600, minHeight: 500)
        .background(Color(NSColor.windowBackgroundColor))
        .task {
            await loadDocument()
        }
    }

    // MARK: - Header

    private var documentHeader: some View {
        HStack(spacing: 12) {
            // File icon
            ZStack {
                RoundedRectangle(cornerRadius: 8, style: .continuous)
                    .fill(Color(mimeColor).opacity(0.15))
                    .frame(width: 40, height: 40)

                Image(systemName: mimeIcon)
                    .font(.system(size: 18))
                    .foregroundColor(Color(mimeColor))
            }

            // File info
            VStack(alignment: .leading, spacing: 2) {
                Text(documentInfo.fileName)
                    .font(.system(size: 15, weight: .semibold))
                    .lineLimit(1)

                HStack(spacing: 6) {
                    Text(documentInfo.mimeType?.uppercased() ?? "FILE")
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)

                    Text("•")
                        .foregroundColor(.secondary.opacity(0.5))

                    Text(formattedSize)
                        .font(.system(size: 11))
                        .foregroundColor(.secondary)
                }
            }

            Spacer()

            // Actions
            HStack(spacing: 8) {
                Button {
                    Task { await downloadFile() }
                } label: {
                    Label("Download", systemImage: isDownloading ? "arrow.down.circle" : "arrow.down.to.line")
                }
                .disabled(isDownloading || fileData == nil)

                Button {
                    dismiss()
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 12, weight: .medium))
                }
                .buttonStyle(.bordered)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color.gray.opacity(0.03))
    }

    // MARK: - Content

    @ViewBuilder
    private var documentContent: some View {
        if isLoading {
            loadingView
        } else if let error = error {
            errorView(error)
        } else if let data = fileData {
            documentPreview(data: data)
        } else {
            placeholderView
        }
    }

    private var loadingView: some View {
        VStack(spacing: 16) {
            ProgressView()
                .scaleEffect(1.2)
            Text("Loading document...")
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private func errorView(_ message: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 48))
                .foregroundColor(.orange)

            Text("Could not load document")
                .font(.headline)

            Text(message)
                .font(.subheadline)
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)

            Button("Try Again") {
                Task { await loadDocument() }
            }
            .buttonStyle(.borderedProminent)
        }
        .padding()
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    private var placeholderView: some View {
        VStack(spacing: 20) {
            Image(systemName: mimeIcon)
                .font(.system(size: 64))
                .foregroundColor(Color(mimeColor))

            Text(documentInfo.fileName)
                .font(.title2.bold())

            Text("Preview not available for this file type")
                .font(.subheadline)
                .foregroundColor(.secondary)

            Button("Download to View") {
                Task { await downloadFile() }
            }
            .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }

    @ViewBuilder
    private func documentPreview(data: Data) -> some View {
        let mimeType = documentInfo.mimeType ?? ""

        if mimeType.hasPrefix("image/") {
            // Image preview
            if let nsImage = NSImage(data: data) {
                ScrollView([.horizontal, .vertical]) {
                    Image(nsImage: nsImage)
                        .resizable()
                        .aspectRatio(contentMode: .fit)
                        .frame(maxWidth: .infinity, maxHeight: .infinity)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                placeholderView
            }
        } else if mimeType.hasPrefix("text/") || isTextFile {
            // Text preview
            if let text = String(data: data, encoding: .utf8) {
                ScrollView {
                    Text(text)
                        .font(.system(.body, design: .monospaced))
                        .textSelection(.enabled)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .padding()
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                placeholderView
            }
        } else if mimeType == "application/pdf" {
            // PDF preview placeholder
            VStack(spacing: 20) {
                Image(systemName: "doc.text.fill")
                    .font(.system(size: 64))
                    .foregroundColor(.red)

                Text("PDF Preview")
                    .font(.title2.bold())

                Text("PDF rendering coming soon")
                    .font(.subheadline)
                    .foregroundColor(.secondary)

                Button("Open in Preview") {
                    openInDefaultApp(data: data)
                }
                .buttonStyle(.borderedProminent)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
        } else {
            // Generic file - show info and download option
            placeholderView
        }
    }

    // MARK: - Helpers

    private var isTextFile: Bool {
        let ext = (documentInfo.fileName as NSString).pathExtension.lowercased()
        return ["txt", "md", "json", "xml", "html", "css", "js", "ts", "swift", "py", "rb", "go", "rs", "c", "cpp", "h", "java", "kt", "yaml", "yml", "toml", "ini", "conf", "sh", "bash", "zsh"].contains(ext)
    }

    private var mimeIcon: String {
        guard let mime = documentInfo.mimeType else { return "doc" }

        if mime.hasPrefix("image/") { return "photo" }
        if mime.hasPrefix("video/") { return "video" }
        if mime.hasPrefix("audio/") { return "music.note" }
        if mime == "application/pdf" { return "doc.text.fill" }
        if mime.contains("zip") || mime.contains("archive") { return "archivebox" }
        if mime.hasPrefix("text/") || isTextFile { return "doc.plaintext" }
        return "doc"
    }

    private var mimeColor: NSColor {
        guard let mime = documentInfo.mimeType else { return .gray }

        if mime.hasPrefix("image/") { return .systemPurple }
        if mime.hasPrefix("video/") { return .systemPink }
        if mime.hasPrefix("audio/") { return .systemGreen }
        if mime == "application/pdf" { return .systemRed }
        if mime.contains("zip") || mime.contains("archive") { return .systemYellow }
        if mime.hasPrefix("text/") || isTextFile { return .systemBlue }
        return .gray
    }

    private var formattedSize: String {
        let formatter = ByteCountFormatter()
        formatter.countStyle = .file
        return formatter.string(fromByteCount: Int64(documentInfo.size))
    }

    // MARK: - Actions

    @MainActor
    private func loadDocument() async {
        isLoading = true
        error = nil

        do {
            // For now, we'll load the file data
            // In production, you might want lazy loading or streaming for large files
            fileData = try await vaultService.download(
                fileId: documentInfo.fileId,
                vaultType: documentInfo.vaultType,
                passphrase: "" // Would need secure handling
            )
            logger.info("Loaded document: \(documentInfo.fileName)")
        } catch {
            self.error = error.localizedDescription
            logger.error("Failed to load document: \(error.localizedDescription)")
        }

        isLoading = false
    }

    @MainActor
    private func downloadFile() async {
        let savePanel = NSSavePanel()
        savePanel.nameFieldStringValue = documentInfo.fileName
        savePanel.canCreateDirectories = true

        guard savePanel.runModal() == .OK, let url = savePanel.url else { return }

        isDownloading = true

        do {
            let data: Data
            if let existingData = fileData {
                data = existingData
            } else {
                data = try await vaultService.download(
                    fileId: documentInfo.fileId,
                    vaultType: documentInfo.vaultType,
                    passphrase: ""
                )
            }
            try data.write(to: url)
            logger.info("Downloaded document to: \(url.path)")
        } catch {
            logger.error("Download failed: \(error.localizedDescription)")
        }

        isDownloading = false
    }

    private func openInDefaultApp(data: Data) {
        // Save to temp and open
        let tempURL = FileManager.default.temporaryDirectory.appendingPathComponent(documentInfo.fileName)
        do {
            try data.write(to: tempURL)
            NSWorkspace.shared.open(tempURL)
        } catch {
            logger.error("Failed to open in default app: \(error.localizedDescription)")
        }
    }
}

// MARK: - Preview

#Preview {
    DetachedDocumentWindow(
        documentInfo: DetachedDocumentInfo(
            fileId: "test-123",
            fileName: "Example Document.pdf",
            mimeType: "application/pdf",
            size: 1024 * 1024 * 2,
            vaultType: "real"
        )
    )
    .frame(width: 800, height: 600)
}
