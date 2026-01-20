//
//  VaultListView.swift
//  MagnetarStudio (macOS)
//
//  Vault list layout with file rows - Extracted from VaultWorkspaceView.swift (Phase 6.11)
//

import SwiftUI
import UniformTypeIdentifiers

struct VaultListView: View {
    let files: [VaultFile]
    let onFileSelect: (VaultFile) -> Void
    let onFileDetach: (VaultFile) -> Void
    let onDownload: (VaultFile) -> Void
    let onDelete: (VaultFile) -> Void
    var onFilesDropped: (([URL]) -> Void)? = nil

    @State private var isDragging = false

    var body: some View {
        ZStack {
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
                    ForEach(files) { file in
                        VaultFileRow(file: file)
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

struct VaultFileRow: View {
    let file: VaultFile

    var body: some View {
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
}
