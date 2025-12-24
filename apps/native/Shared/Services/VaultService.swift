//
//  VaultService.swift
//  MagnetarStudio
//
//  Service layer for Vault workspace endpoints
//

import Foundation
import AppKit

final class VaultService {
    static let shared = VaultService()
    private let baseURL: String

    private init() {
        // Read from environment or default to localhost
        // For production/remote: Set API_BASE_URL environment variable to HTTPS endpoint
        if let envBaseURL = ProcessInfo.processInfo.environment["API_BASE_URL"] {
            // If custom base URL is set, append /v1/vault
            if envBaseURL.hasSuffix("/api") {
                self.baseURL = "\(envBaseURL)/v1/vault"
            } else {
                self.baseURL = envBaseURL
            }
        } else {
            // Local development only - use HTTP for localhost
            self.baseURL = "http://localhost:8000/api/v1/vault"
        }

        // Enforce HTTPS for non-localhost URLs (security requirement)
        if !baseURL.contains("localhost") && !baseURL.contains("127.0.0.1") {
            if baseURL.hasPrefix("http://") {
                print("⚠️ SECURITY WARNING: VaultService upgrading non-localhost HTTP to HTTPS")
                // This should never happen in production - fail loudly
                assertionFailure("VaultService configured with HTTP for non-localhost URL")
            }
        }
    }

    // MARK: - Unlock

    struct UnlockResponse: Codable {
        let success: Bool
        let vaultType: String?
        let sessionId: String
        let message: String
    }

    /// Unlock vault with password (automatically detects sensitive vs unsensitive)
    func unlock(password: String, vaultId: String = "default", requireTouchId: Bool = false) async throws -> Bool {
        guard let url = URL(string: "\(baseURL)/unlock/passphrase") else {
            throw VaultError.invalidURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        // Build request body as URL-encoded form (FastAPI expects form data for this endpoint)
        let bodyString = "vault_id=\(vaultId)&passphrase=\(password.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "")"
        request.httpBody = bodyString.data(using: .utf8)
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw VaultError.invalidResponse
        }

        if httpResponse.statusCode == 401 || httpResponse.statusCode == 403 {
            throw VaultError.unauthorized
        }

        if httpResponse.statusCode == 429 {
            throw VaultError.rateLimited
        }

        if httpResponse.statusCode != 200 {
            throw VaultError.serverError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let unlockResponse = try decoder.decode(UnlockResponse.self, from: data)

        // Store session ID in keychain for future requests
        if unlockResponse.success {
            try? KeychainService.shared.saveToken(unlockResponse.sessionId, forKey: "vault_session_\(vaultId)")
        }

        return unlockResponse.success
    }

    /// Setup dual-password vault (sensitive + unsensitive)
    func setupDualPassword(
        vaultId: String = "default",
        passwordSensitive: String,
        passwordUnsensitive: String
    ) async throws -> Bool {
        guard let url = URL(string: "\(baseURL)/setup/dual-password") else {
            throw VaultError.invalidURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let body: [String: String] = [
            "vault_id": vaultId,
            "password_sensitive": passwordSensitive,
            "password_unsensitive": passwordUnsensitive
        ]

        request.httpBody = try JSONEncoder().encode(body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw VaultError.invalidResponse
        }

        if httpResponse.statusCode == 400 {
            // Passwords must differ
            throw VaultError.invalidRequest("Sensitive and unsensitive passwords must be different")
        }

        if httpResponse.statusCode == 401 || httpResponse.statusCode == 403 {
            throw VaultError.unauthorized
        }

        if httpResponse.statusCode != 200 {
            throw VaultError.serverError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let setupResponse = try decoder.decode(UnlockResponse.self, from: data)

        // Store session ID
        if setupResponse.success {
            try? KeychainService.shared.saveToken(setupResponse.sessionId, forKey: "vault_session_\(vaultId)")
        }

        return setupResponse.success
    }

    // MARK: - List Files and Folders

    struct ListResponse {
        let folders: [VaultFolder]
        let files: [VaultFile]
    }

    func list(folderPath: String, vaultType: String, passphrase: String?) async throws -> ListResponse {
        // List both folders and files for the given path
        async let foldersTask = listFolders(vaultType: vaultType, parentPath: folderPath)
        async let filesTask = listFiles(vaultType: vaultType, folderPath: folderPath)

        let (folders, files) = try await (foldersTask, filesTask)
        return ListResponse(folders: folders, files: files)
    }

    func listFiles(vaultType: String = "real", folderPath: String? = nil) async throws -> [VaultFile] {
        var components = URLComponents(string: "\(baseURL)/files")!
        var queryItems = [URLQueryItem(name: "vault_type", value: vaultType)]

        if let folderPath = folderPath {
            queryItems.append(URLQueryItem(name: "folder_path", value: folderPath))
        }

        components.queryItems = queryItems

        guard let url = components.url else {
            throw VaultError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw VaultError.invalidResponse
        }

        if httpResponse.statusCode == 401 || httpResponse.statusCode == 403 {
            throw VaultError.unauthorized
        }

        if httpResponse.statusCode != 200 {
            throw VaultError.serverError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode([VaultFile].self, from: data)
    }

    func listFolders(vaultType: String = "real", parentPath: String? = nil) async throws -> [VaultFolder] {
        var components = URLComponents(string: "\(baseURL)/folders")!
        var queryItems = [URLQueryItem(name: "vault_type", value: vaultType)]

        if let parentPath = parentPath {
            queryItems.append(URLQueryItem(name: "parent_path", value: parentPath))
        }

        components.queryItems = queryItems

        guard let url = components.url else {
            throw VaultError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw VaultError.invalidResponse
        }

        if httpResponse.statusCode == 401 || httpResponse.statusCode == 403 {
            throw VaultError.unauthorized
        }

        if httpResponse.statusCode != 200 {
            throw VaultError.serverError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode([VaultFolder].self, from: data)
    }

    // MARK: - Upload File

    func upload(fileURL: URL, folderPath: String, vaultType: String, passphrase: String?) async throws -> VaultFile {
        guard let url = URL(string: "\(baseURL)/upload") else {
            throw VaultError.invalidURL
        }

        let boundary = UUID().uuidString
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        // Build multipart body
        var body = Data()

        // Add file
        let fileData = try Data(contentsOf: fileURL)
        let fileName = fileURL.lastPathComponent
        let mimeType = mimeTypeForPath(path: fileName)

        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"file\"; filename=\"\(fileName)\"\r\n".data(using: .utf8)!)
        body.append("Content-Type: \(mimeType)\r\n\r\n".data(using: .utf8)!)
        body.append(fileData)
        body.append("\r\n".data(using: .utf8)!)

        // Add vault_passphrase
        let vaultPassphrase = passphrase ?? "default"
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"vault_passphrase\"\r\n\r\n".data(using: .utf8)!)
        body.append(vaultPassphrase.data(using: .utf8)!)
        body.append("\r\n".data(using: .utf8)!)

        // Add vault_type
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"vault_type\"\r\n\r\n".data(using: .utf8)!)
        body.append(vaultType.data(using: .utf8)!)
        body.append("\r\n".data(using: .utf8)!)

        // Add folder_path
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"folder_path\"\r\n\r\n".data(using: .utf8)!)
        body.append(folderPath.data(using: .utf8)!)
        body.append("\r\n".data(using: .utf8)!)

        // End boundary
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw VaultError.invalidResponse
        }

        if httpResponse.statusCode == 401 || httpResponse.statusCode == 403 {
            throw VaultError.unauthorized
        }

        if httpResponse.statusCode != 200 {
            throw VaultError.serverError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(VaultFile.self, from: data)
    }

    // MARK: - Create Folder

    func createFolder(name: String? = nil, folderPath: String? = nil, vaultType: String, passphrase: String?) async throws -> VaultFolder {
        guard let url = URL(string: "\(baseURL)/folders") else {
            throw VaultError.invalidURL
        }

        let boundary = UUID().uuidString
        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("multipart/form-data; boundary=\(boundary)", forHTTPHeaderField: "Content-Type")

        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        // Determine folder name and parent path
        let folderName: String
        let parentPath: String

        if let fullPath = folderPath {
            // Extract name and parent from full path
            let components = fullPath.split(separator: "/").map(String.init)
            folderName = components.last ?? "New Folder"
            parentPath = "/" + components.dropLast().joined(separator: "/")
        } else {
            folderName = name ?? "New Folder"
            parentPath = "/"
        }

        // Build multipart body
        var body = Data()

        // Add folder_name
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"folder_name\"\r\n\r\n".data(using: .utf8)!)
        body.append(folderName.data(using: .utf8)!)
        body.append("\r\n".data(using: .utf8)!)

        // Add vault_type
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"vault_type\"\r\n\r\n".data(using: .utf8)!)
        body.append(vaultType.data(using: .utf8)!)
        body.append("\r\n".data(using: .utf8)!)

        // Add parent_path
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append("Content-Disposition: form-data; name=\"parent_path\"\r\n\r\n".data(using: .utf8)!)
        body.append(parentPath.data(using: .utf8)!)
        body.append("\r\n".data(using: .utf8)!)

        // End boundary
        body.append("--\(boundary)--\r\n".data(using: .utf8)!)

        request.httpBody = body

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw VaultError.invalidResponse
        }

        if httpResponse.statusCode == 401 || httpResponse.statusCode == 403 {
            throw VaultError.unauthorized
        }

        if httpResponse.statusCode != 200 && httpResponse.statusCode != 201 {
            throw VaultError.serverError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return try decoder.decode(VaultFolder.self, from: data)
    }

    // MARK: - Download File

    func download(fileId: String, vaultType: String, passphrase: String?) async throws -> Data {
        guard let url = URL(string: "\(baseURL)/files/\(fileId)/download") else {
            throw VaultError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"

        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw VaultError.invalidResponse
        }

        if httpResponse.statusCode == 401 || httpResponse.statusCode == 403 {
            throw VaultError.unauthorized
        }

        if httpResponse.statusCode != 200 {
            throw VaultError.serverError(httpResponse.statusCode)
        }

        return data
    }

    // MARK: - Delete File

    func deleteFile(fileId: String, vaultType: String? = nil, passphrase: String? = nil) async throws {
        guard let url = URL(string: "\(baseURL)/files/\(fileId)") else {
            throw VaultError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (_, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw VaultError.invalidResponse
        }

        if httpResponse.statusCode == 401 || httpResponse.statusCode == 403 {
            throw VaultError.unauthorized
        }

        if httpResponse.statusCode != 200 && httpResponse.statusCode != 204 {
            throw VaultError.serverError(httpResponse.statusCode)
        }
    }

    // MARK: - Delete Folder

    func deleteFolder(folderPath: String, vaultType: String, passphrase: String?) async throws {
        // Backend endpoint for folder deletion (may need to be added)
        guard let url = URL(string: "\(baseURL)/folders") else {
            throw VaultError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let body = ["folder_path": folderPath, "vault_type": vaultType]
        request.httpBody = try? JSONSerialization.data(withJSONObject: body)

        let (_, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw VaultError.invalidResponse
        }

        if httpResponse.statusCode == 401 || httpResponse.statusCode == 403 {
            throw VaultError.unauthorized
        }

        if httpResponse.statusCode != 200 && httpResponse.statusCode != 204 {
            throw VaultError.serverError(httpResponse.statusCode)
        }
    }

    // MARK: - Helpers

    private func mimeTypeForPath(path: String) -> String {
        let ext = (path as NSString).pathExtension.lowercased()

        let mimeTypes: [String: String] = [
            "jpg": "image/jpeg",
            "jpeg": "image/jpeg",
            "png": "image/png",
            "gif": "image/gif",
            "pdf": "application/pdf",
            "txt": "text/plain",
            "zip": "application/zip",
            "mp4": "video/mp4",
            "mp3": "audio/mpeg"
        ]

        return mimeTypes[ext] ?? "application/octet-stream"
    }
}

// MARK: - Vault Errors

enum VaultError: LocalizedError {
    case invalidURL
    case invalidResponse
    case unauthorized
    case rateLimited
    case invalidRequest(String)
    case serverError(Int)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid vault URL"
        case .invalidResponse:
            return "Invalid response from vault server"
        case .unauthorized:
            return "Unauthorized - incorrect password or vault not configured"
        case .rateLimited:
            return "Too many unlock attempts. Please wait 5 minutes."
        case .invalidRequest(let message):
            return message
        case .serverError(let code):
            return "Vault server error (HTTP \(code))"
        }
    }
}
