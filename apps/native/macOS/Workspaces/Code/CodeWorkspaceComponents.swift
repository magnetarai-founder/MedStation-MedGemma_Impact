//
//  CodeWorkspaceComponents.swift
//  MagnetarStudio (macOS)
//
//  Shared components and models - Extracted from CodeWorkspace.swift (Phase 6.18)
//

import SwiftUI

// MARK: - File Item Model

struct FileItem: Identifiable, Hashable {
    let id = UUID()
    let name: String
    let path: String
    let isDirectory: Bool
    let size: Int64?
    let modifiedAt: Date?
    let fileId: String?  // Backend file ID

    static let mockFiles = [
        FileItem(name: "README.md", path: "/README.md", isDirectory: false, size: 1024, modifiedAt: Date(), fileId: nil),
        FileItem(name: "src", path: "/src", isDirectory: true, size: nil, modifiedAt: Date(), fileId: nil),
        FileItem(name: "main.swift", path: "/src/main.swift", isDirectory: false, size: 2048, modifiedAt: Date(), fileId: nil),
        FileItem(name: "utils.swift", path: "/src/utils.swift", isDirectory: false, size: 512, modifiedAt: Date(), fileId: nil),
        FileItem(name: "package.json", path: "/package.json", isDirectory: false, size: 256, modifiedAt: Date(), fileId: nil),
    ]
}

// MARK: - File Row

struct CodeFileRow: View {
    let file: FileItem
    let isSelected: Bool
    let onSelect: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: onSelect) {
            HStack(spacing: 8) {
                Image(systemName: file.isDirectory ? "folder.fill" : "doc.text.fill")
                    .font(.system(size: 12))
                    .foregroundColor(file.isDirectory ? .blue : .secondary)

                Text(file.name)
                    .font(.system(size: 12))
                    .lineLimit(1)

                Spacer()
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                isSelected ? Color.magnetarPrimary.opacity(0.2) :
                isHovered ? Color.gray.opacity(0.1) : Color.clear
            )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            isHovered = hovering
        }
    }
}

// MARK: - File Tab

struct CodeFileTab: View {
    let file: FileItem
    let isSelected: Bool
    let onSelect: () -> Void
    let onClose: () -> Void

    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 6) {
            Image(systemName: "doc.text")
                .font(.system(size: 11))
                .foregroundColor(.secondary)

            Text(file.name)
                .font(.system(size: 12))
                .lineLimit(1)

            Button {
                onClose()
            } label: {
                Image(systemName: "xmark")
                    .font(.system(size: 9))
                    .foregroundColor(.secondary)
            }
            .buttonStyle(.plain)
            .opacity(isHovered || isSelected ? 1 : 0)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(
            isSelected ? Color.surfaceSecondary :
            isHovered ? Color.gray.opacity(0.1) : Color.clear
        )
        .onTapGesture {
            onSelect()
        }
        .onHover { hovering in
            isHovered = hovering
        }
    }
}
