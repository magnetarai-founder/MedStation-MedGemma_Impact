//
//  VaultModels.swift
//  MagnetarStudio
//
//  Vault data models matching backend API
//

import Foundation
import AppKit

// MARK: - Vault File

struct VaultFile: Identifiable, Codable, Sendable {
    let id: String
    let name: String
    let size: Int
    let mimeType: String?
    let folderPath: String?
    let uploadedAt: String
    let isFolder: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case size
        case mimeType = "mime_type"
        case folderPath = "folder_path"
        case uploadedAt = "uploaded_at"
        case isFolder = "is_folder"
    }

    var sizeFormatted: String {
        let formatter = ByteCountFormatter()
        formatter.countStyle = .file
        return formatter.string(fromByteCount: Int64(size))
    }

    var modifiedFormatted: String {
        // Parse uploadedAt ISO8601 string and format relative time
        let formatter = ISO8601DateFormatter()
        if let date = formatter.date(from: uploadedAt) {
            return date.timeAgoDisplay()
        }
        return uploadedAt
    }

    var mimeIcon: String {
        if isFolder { return "folder.fill" }
        guard let mime = mimeType else { return "doc" }

        if mime.starts(with: "image/") { return "photo" }
        if mime.starts(with: "video/") { return "video" }
        if mime.starts(with: "audio/") { return "music.note" }
        if mime.contains("pdf") { return "doc.text" }
        if mime.contains("zip") || mime.contains("archive") { return "archivebox" }
        if mime.contains("text/") || mime.contains("code") { return "chevron.left.forwardslash.chevron.right" }

        return "doc"
    }

    var mimeColor: NSColor {
        if isFolder { return .systemBlue }
        guard let mime = mimeType else { return .gray }

        if mime.starts(with: "image/") { return .systemPurple }
        if mime.starts(with: "video/") { return .systemPink }
        if mime.starts(with: "audio/") { return .systemGreen }
        if mime.contains("pdf") { return .systemRed }
        if mime.contains("zip") || mime.contains("archive") { return .systemYellow }
        if mime.contains("text/") || mime.contains("code") { return .systemIndigo }

        return .gray
    }
}

// MARK: - Vault Folder

struct VaultFolder: Identifiable, Codable, Sendable {
    let id: String
    let name: String
    let path: String
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case path
        case createdAt = "created_at"
    }

    // Alias for compatibility with VaultStore
    var folderPath: String {
        return path
    }
}

// MARK: - Date Extension

extension Date {
    func timeAgoDisplay() -> String {
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .full
        return formatter.localizedString(for: self, relativeTo: Date())
    }
}
