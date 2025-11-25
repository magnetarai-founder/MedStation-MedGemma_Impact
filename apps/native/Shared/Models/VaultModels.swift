import Foundation

// MARK: - Vault Folder

struct VaultFolder: Codable, Identifiable {
    let id: String
    let folderName: String
    let folderPath: String
    let parentPath: String
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case folderName = "folder_name"
        case folderPath = "folder_path"
        case parentPath = "parent_path"
        case createdAt = "created_at"
    }

    /// Path components for breadcrumb navigation
    var pathComponents: [String] {
        folderPath.split(separator: "/").map(String.init)
    }
}

// MARK: - Vault File

struct VaultFile: Codable, Identifiable {
    let id: String
    let filename: String
    let fileSize: Int
    let mimeType: String
    let folderPath: String
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case filename
        case fileSize = "file_size"
        case mimeType = "mime_type"
        case folderPath = "folder_path"
        case createdAt = "created_at"
    }

    /// File extension for icon display
    var fileExtension: String {
        (filename as NSString).pathExtension.lowercased()
    }

    /// Human-readable file size
    var formattedSize: String {
        let formatter = ByteCountFormatter()
        formatter.allowedUnits = [.useAll]
        formatter.countStyle = .file
        return formatter.string(fromByteCount: Int64(fileSize))
    }

    /// File type category for icon/preview
    var fileCategory: FileCategory {
        switch fileExtension {
        case "jpg", "jpeg", "png", "gif", "bmp", "tiff", "heic":
            return .image
        case "pdf":
            return .pdf
        case "doc", "docx", "txt", "rtf", "pages":
            return .document
        case "xls", "xlsx", "csv", "numbers":
            return .spreadsheet
        case "mp4", "mov", "avi", "mkv":
            return .video
        case "mp3", "wav", "aac", "m4a":
            return .audio
        case "zip", "rar", "7z", "tar", "gz":
            return .archive
        default:
            return .other
        }
    }

    enum FileCategory {
        case image, pdf, document, spreadsheet, video, audio, archive, other
    }
}

// MARK: - Vault List Response

struct VaultListResponse: Codable {
    let folders: [VaultFolder]
    let files: [VaultFile]
}

// MARK: - Unlock Response

struct UnlockResponse: Codable {
    let success: Bool
}

// MARK: - Vault Types

enum VaultType: String {
    case primary = "primary"
    case decoy = "decoy"
    case team = "team"
}
