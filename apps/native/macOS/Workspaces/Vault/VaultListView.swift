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
                        .foregroundStyle(.secondary)
                        .frame(maxWidth: .infinity, alignment: .leading)

                    Text("Size")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(.secondary)
                        .frame(width: 100, alignment: .trailing)

                    Text("Modified")
                        .font(.system(size: 13, weight: .semibold))
                        .foregroundStyle(.secondary)
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

    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 16) {
            HStack(spacing: 10) {
                // Icon with background
                ZStack {
                    RoundedRectangle(cornerRadius: 6)
                        .fill(Color(file.mimeColor).opacity(isHovered ? 0.2 : 0.1))
                        .frame(width: 28, height: 28)

                    Image(systemName: file.mimeIcon)
                        .font(.system(size: 14))
                        .foregroundStyle(Color(file.mimeColor))
                }

                VStack(alignment: .leading, spacing: 2) {
                    Text(file.name)
                        .font(.system(size: 14, weight: isHovered ? .medium : .regular))
                        .lineLimit(1)

                    // Show encrypted status on hover (all vault files are encrypted)
                    if isHovered && !file.isFolder {
                        HStack(spacing: 3) {
                            Image(systemName: "lock.fill")
                                .font(.system(size: 8))
                            Text("Encrypted")
                                .font(.system(size: 9))
                        }
                        .foregroundStyle(.green)
                        .transition(.opacity)
                    }
                }
            }
            .frame(maxWidth: .infinity, alignment: .leading)

            Text(file.sizeFormatted)
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
                .frame(width: 100, alignment: .trailing)

            Text(file.modifiedFormatted)
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
                .frame(width: 120, alignment: .trailing)

            // Hover actions
            if isHovered && !file.isFolder {
                Image(systemName: "chevron.right")
                    .font(.system(size: 11))
                    .foregroundStyle(.tertiary)
                    .transition(.opacity)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(isHovered ? Color(file.mimeColor).opacity(0.08) : Color.clear)
                .padding(.horizontal, 4)
        )
        .overlay(
            Rectangle()
                .fill(Color.gray.opacity(0.1))
                .frame(height: 1),
            alignment: .bottom
        )
        .contentShape(Rectangle())
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovered = hovering
            }
        }
    }
}
