//
//  VaultGridView.swift
//  MagnetarStudio (macOS)
//
//  Vault grid layout with file cards - Extracted from VaultWorkspaceView.swift (Phase 6.11)
//

import SwiftUI
import UniformTypeIdentifiers

struct VaultGridView: View {
    let files: [VaultFile]
    let onFileSelect: (VaultFile) -> Void
    let onFileDetach: (VaultFile) -> Void
    let onDownload: (VaultFile) -> Void
    let onDelete: (VaultFile) -> Void
    var onFilesDropped: (([URL]) -> Void)? = nil

    @State private var isDragging = false

    var body: some View {
        ZStack {
            ScrollView {
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 180, maximum: 220), spacing: 16)], spacing: 16) {
                    ForEach(files) { file in
                        VaultFileCard(file: file)
                            .onTapGesture(count: 2) {
                                // Double-click: detach to separate window
                                if !file.isFolder {
                                    onFileDetach(file)
                                }
                            }
                            .onTapGesture(count: 1) {
                                // Single-click: open inline preview
                                onFileSelect(file)
                            }
                            .contextMenu {
                                if !file.isFolder {
                                    Button {
                                        onFileDetach(file)
                                    } label: {
                                        Label("Open in New Window", systemImage: "uiwindow.split.2x1")
                                    }

                                    Divider()

                                    Button("Download") {
                                        onDownload(file)
                                    }

                                    Divider()

                                    Button("Delete", role: .destructive) {
                                        onDelete(file)
                                    }
                                }
                            }
                    }
                }
                .padding(20)
            }

            // Drop overlay
            if isDragging {
                DropOverlayView()
            }
        }
        .onDrop(of: [.fileURL], isTargeted: $isDragging) { providers in
            handleDrop(providers)
        }
    }

    private func handleDrop(_ providers: [NSItemProvider]) -> Bool {
        guard let onFilesDropped = onFilesDropped else { return false }

        var urls: [URL] = []

        let group = DispatchGroup()

        for provider in providers {
            if provider.hasItemConformingToTypeIdentifier(UTType.fileURL.identifier) {
                group.enter()
                provider.loadItem(forTypeIdentifier: UTType.fileURL.identifier) { item, _ in
                    if let data = item as? Data,
                       let url = URL(dataRepresentation: data, relativeTo: nil) {
                        urls.append(url)
                    }
                    group.leave()
                }
            }
        }

        group.notify(queue: .main) {
            if !urls.isEmpty {
                onFilesDropped(urls)
            }
        }

        return true
    }
}

// MARK: - Drop Overlay

struct DropOverlayView: View {
    var body: some View {
        ZStack {
            Color.black.opacity(0.3)

            VStack(spacing: 16) {
                Image(systemName: "arrow.down.doc.fill")
                    .font(.system(size: 48))
                    .foregroundColor(.white)

                Text("Drop files to upload")
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundColor(.white)

                Text("Files will be encrypted and stored securely")
                    .font(.system(size: 13))
                    .foregroundColor(.white.opacity(0.8))
            }
            .padding(40)
            .background(
                RoundedRectangle(cornerRadius: 16)
                    .fill(Color.accentColor.opacity(0.9))
            )
        }
        .ignoresSafeArea()
    }
}

struct VaultFileCard: View {
    let file: VaultFile

    var body: some View {
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
}
