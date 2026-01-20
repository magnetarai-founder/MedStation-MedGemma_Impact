//
//  VaultToolbar.swift
//  MagnetarStudio (macOS)
//
//  Vault toolbar with breadcrumbs, search, and actions - Extracted from VaultWorkspaceView.swift (Phase 6.11)
//

import SwiftUI

struct VaultToolbar: View {
    let currentPath: [String]
    @Binding var viewMode: VaultViewMode
    @Binding var searchText: String
    @Binding var isCreatingFolder: Bool
    @Binding var isUploading: Bool

    let onNavigateToPath: (Int) -> Void  // Navigate to path at index
    let onNewFolder: () -> Void
    let onUpload: () -> Void

    var body: some View {
        HStack(spacing: 12) {
            // Back button (if not at root)
            if currentPath.count > 1 {
                Button {
                    onNavigateToPath(currentPath.count - 2)
                } label: {
                    Image(systemName: "chevron.left")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(.secondary)
                        .frame(width: 28, height: 28)
                        .background(
                            Circle()
                                .fill(Color.gray.opacity(0.1))
                        )
                }
                .buttonStyle(.plain)
                .help("Go back")
            }

            // Breadcrumbs - clickable
            BreadcrumbView(
                path: currentPath,
                onNavigate: onNavigateToPath
            )

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
                onNewFolder()
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
                onUpload()
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
}

// MARK: - Breadcrumb View

struct BreadcrumbView: View {
    let path: [String]
    let onNavigate: (Int) -> Void

    var body: some View {
        HStack(spacing: 0) {
            ForEach(Array(path.enumerated()), id: \.offset) { index, folder in
                if index > 0 {
                    Image(systemName: "chevron.right")
                        .font(.system(size: 9, weight: .semibold))
                        .foregroundColor(.secondary.opacity(0.5))
                        .padding(.horizontal, 6)
                }

                BreadcrumbItem(
                    name: displayName(for: folder, at: index),
                    icon: iconName(for: folder, at: index),
                    isLast: index == path.count - 1,
                    onTap: {
                        if index < path.count - 1 {
                            onNavigate(index)
                        }
                    }
                )
            }
        }
    }

    private func displayName(for folder: String, at index: Int) -> String {
        if index == 0 && folder == "/" {
            return "Vault"
        }
        return folder
    }

    private func iconName(for folder: String, at index: Int) -> String? {
        if index == 0 {
            return "lock.shield"
        }
        return nil
    }
}

// MARK: - Breadcrumb Item

struct BreadcrumbItem: View {
    let name: String
    let icon: String?
    let isLast: Bool
    let onTap: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: onTap) {
            HStack(spacing: 5) {
                if let icon = icon {
                    Image(systemName: icon)
                        .font(.system(size: 12))
                        .foregroundColor(isLast ? .primary : .secondary)
                }

                Text(name)
                    .font(.system(size: 13, weight: isLast ? .semibold : .regular))
                    .foregroundColor(isLast ? .primary : .secondary)
            }
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .fill(isHovered && !isLast ? Color.gray.opacity(0.1) : Color.clear)
            )
        }
        .buttonStyle(.plain)
        .disabled(isLast)
        .onHover { hovering in
            isHovered = hovering
        }
    }
}
