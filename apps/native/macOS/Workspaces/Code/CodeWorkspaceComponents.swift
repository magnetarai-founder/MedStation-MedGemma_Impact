//
//  CodeWorkspaceComponents.swift
//  MagnetarStudio (macOS)
//
//  Shared components and models - Extracted from CodeWorkspace.swift (Phase 6.18)
//  Enhanced with file metadata formatting and visual polish
//

import SwiftUI
import AppKit

// MARK: - File Item Model

struct FileItem: Identifiable, Hashable {
    let id = UUID()
    let name: String
    let path: String
    let isDirectory: Bool
    let size: Int64?
    let modifiedAt: Date?
    let fileId: String?  // Backend file ID
    var children: [FileItem]?  // Non-nil for expanded directories

    var hasChildren: Bool {
        isDirectory && (children == nil || !(children?.isEmpty ?? true))
    }

    /// File extension
    var fileExtension: String {
        (name as NSString).pathExtension.lowercased()
    }

    /// Formatted file size
    var formattedSize: String? {
        guard let size = size else { return nil }
        if size < 1024 {
            return "\(size) B"
        } else if size < 1024 * 1024 {
            return String(format: "%.1f KB", Double(size) / 1024)
        } else {
            return String(format: "%.1f MB", Double(size) / (1024 * 1024))
        }
    }

    /// Relative modified date
    var relativeModifiedDate: String? {
        guard let date = modifiedAt else { return nil }

        let now = Date()
        let diff = now.timeIntervalSince(date)

        if diff < 60 {
            return "just now"
        } else if diff < 3600 {
            let mins = Int(diff / 60)
            return "\(mins)m ago"
        } else if diff < 86400 {
            let hours = Int(diff / 3600)
            return "\(hours)h ago"
        } else if diff < 172800 {
            return "yesterday"
        } else if diff < 604800 {
            let days = Int(diff / 86400)
            return "\(days)d ago"
        } else {
            let formatter = DateFormatter()
            formatter.dateStyle = .short
            return formatter.string(from: date)
        }
    }

    /// Icon name based on file type
    var iconName: String {
        if isDirectory {
            return "folder.fill"
        }
        switch fileExtension {
        case "swift": return "swift"
        case "js", "ts", "jsx", "tsx": return "doc.text.fill"
        case "py": return "doc.text.fill"
        case "json": return "curlybraces"
        case "md", "markdown": return "doc.richtext"
        case "html", "htm": return "globe"
        case "css", "scss", "sass": return "paintbrush"
        case "yml", "yaml": return "list.bullet.rectangle"
        case "sh", "bash", "zsh": return "terminal"
        case "png", "jpg", "jpeg", "gif", "svg": return "photo"
        case "pdf": return "doc.fill"
        default: return "doc.text.fill"
        }
    }

    /// Icon color based on file type
    var iconColor: Color {
        if isDirectory {
            return .blue
        }
        switch fileExtension {
        case "swift": return .orange
        case "js", "jsx": return .yellow
        case "ts", "tsx": return .blue
        case "py": return .green
        case "json": return .purple
        case "md", "markdown": return .cyan
        case "html", "htm": return .red
        case "css", "scss", "sass": return .pink
        case "yml", "yaml": return .mint
        case "sh", "bash", "zsh": return .green
        default: return .secondary
        }
    }

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
    var onRevealInFinder: (() -> Void)? = nil

    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 8) {
            // File icon with type-specific color
            Image(systemName: file.iconName)
                .font(.system(size: 12))
                .foregroundStyle(isSelected ? .white : file.iconColor)
                .frame(width: 16)

            // File name
            Text(file.name)
                .font(.system(size: 12))
                .lineLimit(1)
                .foregroundStyle(isSelected ? .white : .primary)

            Spacer()

            // Metadata on hover
            if isHovered && !isSelected {
                HStack(spacing: 8) {
                    if let size = file.formattedSize {
                        Text(size)
                            .font(.system(size: 10))
                            .foregroundStyle(.tertiary)
                    }

                    if let date = file.relativeModifiedDate {
                        Text(date)
                            .font(.system(size: 10))
                            .foregroundStyle(.tertiary)
                    }
                }
                .transition(.opacity)
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 5)
        .frame(height: 28)
        .background(
            RoundedRectangle(cornerRadius: 5)
                .fill(isSelected ? Color.accentColor : (isHovered ? Color.primary.opacity(0.06) : Color.clear))
        )
        .padding(.horizontal, 4)
        .contentShape(Rectangle())
        .onTapGesture {
            onSelect()
        }
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.1)) {
                isHovered = hovering
            }
        }
        .contextMenu {
            Button("Reveal in Finder") {
                onRevealInFinder?()
            }
            Button("Copy Path") {
                NSPasteboard.general.clearContents()
                NSPasteboard.general.setString(file.path, forType: .string)
            }
        }
    }
}

// MARK: - File Tab

struct CodeFileTab: View {
    let file: FileItem
    let isSelected: Bool
    var isModified: Bool = false
    let onSelect: () -> Void
    let onClose: () -> Void

    @State private var isHovered = false
    @State private var isCloseHovered = false

    var body: some View {
        HStack(spacing: 5) {
            // File icon with type color
            Image(systemName: file.iconName)
                .font(.system(size: 10))
                .foregroundStyle(isSelected ? file.iconColor : .secondary)

            // File name
            Text(file.name)
                .font(.system(size: 11, weight: isSelected ? .medium : .regular))
                .lineLimit(1)
                .foregroundStyle(isSelected ? .primary : .secondary)

            // Modified indicator or close button
            Button {
                onClose()
            } label: {
                ZStack {
                    if isModified && !isCloseHovered && !isHovered {
                        Circle()
                            .fill(Color.orange)
                            .frame(width: 6, height: 6)
                    } else {
                        Image(systemName: "xmark")
                            .font(.system(size: 8, weight: .medium))
                            .foregroundStyle(isCloseHovered ? .primary : Color(nsColor: .tertiaryLabelColor))
                    }
                }
                .frame(width: 14, height: 14)
                .background(
                    Circle()
                        .fill(isCloseHovered ? Color.primary.opacity(0.1) : Color.clear)
                )
            }
            .buttonStyle(.plain)
            .opacity(isHovered || isSelected || isModified ? 1 : 0)
            .onHover { hovering in
                isCloseHovered = hovering
            }
        }
        .padding(.horizontal, 10)
        .padding(.vertical, 6)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(isSelected ? Color.primary.opacity(0.08) : (isHovered ? Color.primary.opacity(0.04) : Color.clear))
        )
        .overlay(
            RoundedRectangle(cornerRadius: 6)
                .stroke(isSelected ? Color.primary.opacity(0.1) : Color.clear, lineWidth: 0.5)
        )
        .onTapGesture {
            onSelect()
        }
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.1)) {
                isHovered = hovering
            }
        }
    }
}
