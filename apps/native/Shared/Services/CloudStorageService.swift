//
//  CloudStorageService.swift
//  MagnetarStudio
//
//  Cloud storage service with chunked upload/download support
//  Handles large file transfers to MagnetarCloud
//

import Foundation
import Combine
import CryptoKit

// MARK: - Models

enum StorageClass: String, Codable {
    case standard
    case archive
    case cold
}

enum UploadStatus: String, Codable {
    case pending
    case uploading
    case processing
    case completed
    case failed
    case expired
}

struct CloudFile: Codable, Identifiable {
    let fileId: String
    let filename: String
    let sizeBytes: Int
    let contentType: String
    let storageClass: StorageClass
    let uploadedAt: String

    var id: String { fileId }

    var formattedSize: String {
        ByteCountFormatter.string(fromByteCount: Int64(sizeBytes), countStyle: .file)
    }
}

struct UploadSession: Codable {
    let uploadId: String
    let chunkSize: Int
    let totalChunks: Int
    let expiresAt: String
    let storageClass: StorageClass
}

struct UploadProgress: Codable {
    let uploadId: String
    let status: UploadStatus
    let filename: String
    let sizeBytes: Int
    let chunksUploaded: Int
    let totalChunks: Int
    let progressPercent: Double
    let fileId: String?
}

struct UploadResult: Codable {
    let fileId: String
    let filename: String
    let sizeBytes: Int
    let contentType: String
    let storageClass: StorageClass
    let sha256: String
    let uploadedAt: String
    let downloadUrl: String?
}

// MARK: - Errors

enum CloudStorageError: Error, LocalizedError {
    case invalidURL
    case invalidResponse
    case unauthorized
    case cloudUnavailable
    case uploadExpired
    case hashMismatch
    case serverError(Int)
    case networkError(Error)
    case fileReadError(Error)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid storage URL"
        case .invalidResponse:
            return "Invalid server response"
        case .unauthorized:
            return "Cloud authentication required"
        case .cloudUnavailable:
            return "Cloud storage unavailable (air-gap mode)"
        case .uploadExpired:
            return "Upload session expired"
        case .hashMismatch:
            return "File integrity check failed"
        case .serverError(let code):
            return "Server error: \(code)"
        case .networkError(let error):
            return "Network error: \(error.localizedDescription)"
        case .fileReadError(let error):
            return "Failed to read file: \(error.localizedDescription)"
        }
    }
}

// MARK: - CloudStorageService

final class CloudStorageService: ObservableObject {
    static let shared = CloudStorageService()

    private let baseURL: String
    private let chunkSize = 4 * 1024 * 1024 // 4 MB chunks

    // Active uploads tracking
    @Published private(set) var activeUploads: [String: UploadProgress] = [:]
    @Published private(set) var files: [CloudFile] = []

    private init() {
        self.baseURL = APIConfiguration.shared.cloudStorageURL
    }

    // MARK: - Upload

    /// Upload a file with chunked transfer
    /// - Parameters:
    ///   - fileURL: Local file URL
    ///   - contentType: MIME type (auto-detected if nil)
    ///   - storageClass: Storage tier (default: standard)
    ///   - encrypt: Whether to encrypt before upload
    ///   - progressHandler: Called with upload progress updates
    /// - Returns: Upload result with file ID
    func uploadFile(
        _ fileURL: URL,
        contentType: String? = nil,
        storageClass: StorageClass = .standard,
        encrypt: Bool = true,
        progressHandler: ((Double) -> Void)? = nil
    ) async throws -> UploadResult {
        // Get file attributes
        let attributes = try FileManager.default.attributesOfItem(atPath: fileURL.path)
        guard let fileSize = attributes[.size] as? Int else {
            throw CloudStorageError.fileReadError(NSError(domain: "CloudStorage", code: 1, userInfo: [NSLocalizedDescriptionKey: "Cannot determine file size"]))
        }

        let filename = fileURL.lastPathComponent
        let mimeType = contentType ?? mimeTypeForPath(fileURL.path)

        // 1. Initialize upload session
        let session = try await initUpload(
            filename: filename,
            sizeBytes: fileSize,
            contentType: mimeType,
            storageClass: storageClass,
            encrypt: encrypt
        )

        // 2. Open file handle for reading
        guard let fileHandle = FileHandle(forReadingAtPath: fileURL.path) else {
            throw CloudStorageError.fileReadError(NSError(domain: "CloudStorage", code: 2, userInfo: [NSLocalizedDescriptionKey: "Cannot open file for reading"]))
        }
        defer { try? fileHandle.close() }

        // 3. Upload chunks
        var fileHasher = SHA256()

        for chunkIndex in 0..<session.totalChunks {
            try fileHandle.seek(toOffset: UInt64(chunkIndex * session.chunkSize))
            guard let chunkData = try fileHandle.read(upToCount: session.chunkSize) else {
                throw CloudStorageError.fileReadError(NSError(domain: "CloudStorage", code: 3, userInfo: [NSLocalizedDescriptionKey: "Failed to read chunk \(chunkIndex)"]))
            }

            // Update file hash
            fileHasher.update(data: chunkData)

            // Compute chunk hash
            let chunkHash = SHA256.hash(data: chunkData)
            let chunkHashString = chunkHash.compactMap { String(format: "%02x", $0) }.joined()

            // Upload chunk
            try await uploadChunk(
                uploadId: session.uploadId,
                chunkIndex: chunkIndex,
                chunkData: chunkData,
                chunkHash: chunkHashString
            )

            // Report progress
            let progress = Double(chunkIndex + 1) / Double(session.totalChunks)
            progressHandler?(progress)

            await MainActor.run {
                self.activeUploads[session.uploadId] = UploadProgress(
                    uploadId: session.uploadId,
                    status: .uploading,
                    filename: filename,
                    sizeBytes: fileSize,
                    chunksUploaded: chunkIndex + 1,
                    totalChunks: session.totalChunks,
                    progressPercent: progress * 100,
                    fileId: nil
                )
            }
        }

        // 4. Commit upload with final hash
        let finalHash = fileHasher.finalize()
        let finalHashString = finalHash.compactMap { String(format: "%02x", $0) }.joined()

        let result = try await commitUpload(
            uploadId: session.uploadId,
            finalHash: finalHashString
        )

        // Update state
        await MainActor.run {
            self.activeUploads.removeValue(forKey: session.uploadId)
        }

        // Refresh file list
        try? await refreshFiles()

        return result
    }

    // MARK: - Upload Steps

    private func initUpload(
        filename: String,
        sizeBytes: Int,
        contentType: String,
        storageClass: StorageClass,
        encrypt: Bool
    ) async throws -> UploadSession {
        guard let url = URL(string: "\(baseURL)/upload/init") else {
            throw CloudStorageError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        addAuthHeaders(to: &request)

        let body: [String: Any] = [
            "filename": filename,
            "size_bytes": sizeBytes,
            "content_type": contentType,
            "storage_class": storageClass.rawValue,
            "encrypt": encrypt
        ]

        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)
        try handleHTTPResponse(response)

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(UploadSession.self, from: data)
    }

    private func uploadChunk(
        uploadId: String,
        chunkIndex: Int,
        chunkData: Data,
        chunkHash: String
    ) async throws {
        guard let url = URL(string: "\(baseURL)/upload/chunk") else {
            throw CloudStorageError.invalidURL
        }

        // Build multipart form data
        let boundary = UUID().uuidString
        var body = Data()

        // upload_id field
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"upload_id\"\r\n\r\n".data(using: .utf8)!)
        body.append("\(uploadId)\r\n".data(using: .utf8)!)

        // chunk_index field
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"chunk_index\"\r\n\r\n".data(using: .utf8)!)
        body.append("\(chunkIndex)\r\n".data(using: .utf8)!)

        // chunk_hash field
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"chunk_hash\"\r\n\r\n".data(using: .utf8)!)
        body.append("\(chunkHash)\r\n".data(using: .utf8)!)

        // chunk_data file
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"chunk_data\"; filename=\"chunk_\(chunkIndex)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: application/octet-stream\r\n\r\n".data(using: .utf8)!)
        body.append(chunkData)
        body.append("\r\n".data(using: .utf8)!)

        body.append("--\(boundary)--\r\n".data(using: .utf8)!)

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        addAuthHeaders(to: &request)
        request.httpBody = body

        let (_, response) = try await URLSession.shared.data(for: request)
        try handleHTTPResponse(response)
    }

    private func commitUpload(
        uploadId: String,
        finalHash: String
    ) async throws -> UploadResult {
        guard let url = URL(string: "\(baseURL)/upload/commit") else {
            throw CloudStorageError.invalidURL
        }

        // Build form data
        let boundary = UUID().uuidString
        var body = Data()

        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"upload_id\"\r\n\r\n".data(using: .utf8)!)
        body.append("\(uploadId)\r\n".data(using: .utf8)!)

        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"final_hash\"\r\n\r\n".data(using: .utf8)!)
        body.append("\(finalHash)\r\n".data(using: .utf8)!)

        body.append("--\(boundary)--\r\n".data(using: .utf8)!)

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")
        addAuthHeaders(to: &request)
        request.httpBody = body

        let (data, response) = try await URLSession.shared.data(for: request)
        try handleHTTPResponse(response)

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(UploadResult.self, from: data)
    }

    // MARK: - Download

    /// Get download URL for a file
    func getDownloadURL(fileId: String, expiresMinutes: Int = 60) async throws -> URL {
        guard let url = URL(string: "\(baseURL)/download/init") else {
            throw CloudStorageError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        addAuthHeaders(to: &request)

        let body: [String: Any] = [
            "file_id": fileId,
            "expires_minutes": expiresMinutes
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)
        try handleHTTPResponse(response)

        struct DownloadResponse: Codable {
            let downloadUrl: String
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let downloadResponse = try decoder.decode(DownloadResponse.self, from: data)

        // Build full URL
        let downloadURLString = downloadResponse.downloadUrl.hasPrefix("http")
            ? downloadResponse.downloadUrl
            : "\(APIConfiguration.shared.baseURL.replacingOccurrences(of: "/api", with: ""))\(downloadResponse.downloadUrl)"

        guard let downloadURL = URL(string: downloadURLString) else {
            throw CloudStorageError.invalidURL
        }

        return downloadURL
    }

    // MARK: - File Management

    /// Refresh list of user's cloud files
    func refreshFiles() async throws {
        guard let url = URL(string: "\(baseURL)/files") else {
            throw CloudStorageError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        addAuthHeaders(to: &request)

        let (data, response) = try await URLSession.shared.data(for: request)
        try handleHTTPResponse(response)

        struct FilesResponse: Codable {
            let files: [CloudFile]
            let total: Int
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let filesResponse = try decoder.decode(FilesResponse.self, from: data)

        await MainActor.run {
            self.files = filesResponse.files
        }
    }

    /// Delete a cloud file
    func deleteFile(_ fileId: String) async throws {
        guard let url = URL(string: "\(baseURL)/files/\(fileId)") else {
            throw CloudStorageError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        addAuthHeaders(to: &request)

        let (_, response) = try await URLSession.shared.data(for: request)
        try handleHTTPResponse(response)

        // Refresh file list
        try? await refreshFiles()
    }

    // MARK: - Helpers

    private func addAuthHeaders(to request: inout URLRequest) {
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let cloudToken = KeychainService.shared.loadToken(forKey: "cloud_access_token") {
            request.setValue("Bearer \(cloudToken)", forHTTPHeaderField: "X-Cloud-Token")
        }
    }

    private func handleHTTPResponse(_ response: URLResponse) throws {
        guard let httpResponse = response as? HTTPURLResponse else {
            throw CloudStorageError.invalidResponse
        }

        switch httpResponse.statusCode {
        case 200...299:
            return
        case 401, 403:
            throw CloudStorageError.unauthorized
        case 410:
            throw CloudStorageError.uploadExpired
        case 503:
            throw CloudStorageError.cloudUnavailable
        default:
            throw CloudStorageError.serverError(httpResponse.statusCode)
        }
    }

    private func mimeTypeForPath(_ path: String) -> String {
        let ext = (path as NSString).pathExtension.lowercased()
        let mimeTypes: [String: String] = [
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "pdf": "application/pdf",
            "doc": "application/msword",
            "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "txt": "text/plain",
            "json": "application/json",
            "zip": "application/zip",
            "mp4": "video/mp4",
            "mp3": "audio/mpeg"
        ]
        return mimeTypes[ext] ?? "application/octet-stream"
    }
}
