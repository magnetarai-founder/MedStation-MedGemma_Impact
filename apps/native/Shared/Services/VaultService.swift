import Foundation

/// Service layer for Vault endpoints
final class VaultService {
    static let shared = VaultService()
    private let apiClient = ApiClient.shared

    private init() {}

    // MARK: - Unlock

    func unlock(password: String, requireTouchId: Bool = false) async throws -> Bool {
        let body: [String: Any] = [
            "password": password,
            "require_touch_id": requireTouchId
        ]

        let response: UnlockResponse = try await apiClient.request(
            path: "/v1/vault/unlock",
            method: .post,
            jsonBody: body
        )

        return response.success
    }

    // MARK: - List Files/Folders

    func list(
        folderPath: String = "/",
        vaultType: String = "primary",
        passphrase: String? = nil
    ) async throws -> VaultListResponse {
        let encodedPath = folderPath.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "/"
        let path = "/v1/vault/files?folder_path=\(encodedPath)&vault_type=\(vaultType)"

        return try await apiClient.request(
            path: path,
            method: .get,
            extraHeaders: passphraseHeader(passphrase)
        )
    }

    // MARK: - Download

    func download(
        fileId: String,
        vaultType: String = "primary",
        passphrase: String? = nil
    ) async throws -> Data {
        let path = "/v1/vault/files/\(fileId)/download?vault_type=\(vaultType)"

        return try await apiClient.requestRaw(
            path: path,
            method: .get,
            extraHeaders: passphraseHeader(passphrase)
        )
    }

    // MARK: - Upload

    func upload(
        fileURL: URL,
        folderPath: String = "/",
        vaultType: String = "primary",
        passphrase: String? = nil
    ) async throws -> VaultFile {
        let encodedPath = folderPath.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? "/"
        let path = "/v1/vault/files?vault_type=\(vaultType)&folder_path=\(encodedPath)"

        return try await apiClient.multipart(
            path: path,
            fileField: "file",
            fileURL: fileURL,
            extraHeaders: passphraseHeader(passphrase)
        )
    }

    // MARK: - Create Folder

    func createFolder(
        folderPath: String,
        vaultType: String = "primary",
        passphrase: String? = nil
    ) async throws {
        _ = try await apiClient.request(
            path: "/v1/vault/folders",
            method: .post,
            jsonBody: [
                "folder_path": folderPath,
                "vault_type": vaultType
            ],
            extraHeaders: passphraseHeader(passphrase)
        ) as EmptyResponse
    }

    // MARK: - Delete

    func deleteFile(
        fileId: String,
        vaultType: String = "primary",
        passphrase: String? = nil
    ) async throws {
        let path = "/v1/vault/files/\(fileId)?vault_type=\(vaultType)"

        _ = try await apiClient.request(
            path: path,
            method: .delete,
            extraHeaders: passphraseHeader(passphrase)
        ) as EmptyResponse
    }

    func deleteFolder(
        folderPath: String,
        vaultType: String = "primary",
        passphrase: String? = nil
    ) async throws {
        _ = try await apiClient.request(
            path: "/v1/vault/folders",
            method: .delete,
            jsonBody: [
                "folder_path": folderPath,
                "vault_type": vaultType
            ],
            extraHeaders: passphraseHeader(passphrase)
        ) as EmptyResponse
    }

    // MARK: - Helpers

    private func passphraseHeader(_ passphrase: String?) -> [String: String]? {
        guard let passphrase = passphrase else { return nil }
        return ["X-Vault-Passphrase": passphrase]
    }
}
