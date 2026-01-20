//
//  VaultListView.swift
//  MagnetarStudio (macOS)
//
//  Vault list layout with file rows - Extracted from VaultWorkspaceView.swift (Phase 6.11)
//

import SwiftUI

struct VaultListView: View {
    let files: [VaultFile]
    let onFileSelect: (VaultFile) -> Void
    let onFileDetach: (VaultFile) -> Void
    let onDownload: (VaultFile) -> Void
    let onDelete: (VaultFile) -> Void

    var body: some View {
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
