//
//  VaultGridView.swift
//  MagnetarStudio (macOS)
//
//  Vault grid layout with file cards - Extracted from VaultWorkspaceView.swift (Phase 6.11)
//

import SwiftUI

struct VaultGridView: View {
    let files: [VaultFile]
    let onFileSelect: (VaultFile) -> Void
    let onDownload: (VaultFile) -> Void
    let onDelete: (VaultFile) -> Void

    var body: some View {
        ScrollView {
            LazyVGrid(columns: [GridItem(.adaptive(minimum: 180, maximum: 220), spacing: 16)], spacing: 16) {
                ForEach(files) { file in
                    VaultFileCard(file: file)
                        .onTapGesture {
                            onFileSelect(file)
                        }
                        .contextMenu {
                            if !file.isFolder {
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
