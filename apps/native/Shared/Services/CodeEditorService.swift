import Foundation

/// Service for Code Editor workspace operations
final class CodeEditorService {
    static let shared = CodeEditorService()
    private let apiClient = ApiClient.shared

    private init() {}

    // MARK: - Workspaces

    func listWorkspaces() async throws -> [CodeEditorWorkspace] {
        struct WorkspacesResponse: Codable {
            let workspaces: [CodeEditorWorkspace]
        }

        let response: WorkspacesResponse = try await apiClient.request(
            path: "/v1/code-editor/workspaces",
            method: .get
        )

        return response.workspaces
    }

    func createWorkspace(name: String, sourceType: String = "database") async throws -> CodeEditorWorkspace {
        try await apiClient.request(
            path: "/v1/code-editor/workspaces",
            method: .post,
            jsonBody: [
                "name": name,
                "source_type": sourceType
            ]
        )
    }

    func openDiskWorkspace(name: String, diskPath: String) async throws -> CodeEditorWorkspace {
        try await apiClient.request(
            path: "/v1/code-editor/workspaces/open-disk",
            method: .post,
            jsonBody: [
                "name": name,
                "disk_path": diskPath
            ]
        )
    }

    // MARK: - Files

    func getWorkspaceFiles(workspaceId: String) async throws -> [CodeFile] {
        struct FilesResponse: Codable {
            let files: [CodeFile]
        }

        let response: FilesResponse = try await apiClient.request(
            path: "/v1/code-editor/workspaces/\(workspaceId)/files",
            method: .get
        )

        return response.files
    }

    func getFile(fileId: String) async throws -> CodeFileContent {
        try await apiClient.request(
            path: "/v1/code-editor/files/\(fileId)",
            method: .get
        )
    }

    func createFile(workspaceId: String, name: String, path: String, content: String) async throws -> CodeFileContent {
        try await apiClient.request(
            path: "/v1/code-editor/files",
            method: .post,
            jsonBody: [
                "workspace_id": workspaceId,
                "name": name,
                "path": path,
                "content": content
            ]
        )
    }

    func updateFile(fileId: String, content: String) async throws -> CodeFileContent {
        try await apiClient.request(
            path: "/v1/code-editor/files/\(fileId)",
            method: .put,
            jsonBody: [
                "content": content
            ]
        )
    }

    func deleteFile(fileId: String) async throws {
        _ = try await apiClient.request(
            path: "/v1/code-editor/files/\(fileId)",
            method: .delete
        ) as EmptyResponse
    }

    func syncWorkspace(workspaceId: String) async throws {
        _ = try await apiClient.request(
            path: "/v1/code-editor/workspaces/\(workspaceId)/sync",
            method: .post
        ) as EmptyResponse
    }
}

// MARK: - Models

struct CodeEditorWorkspace: Codable, Identifiable {
    let id: String
    let name: String
    let sourceType: String
    let diskPath: String?
    let createdAt: String?
    let updatedAt: String?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case sourceType = "source_type"
        case diskPath = "disk_path"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

/// File tree node returned by backend for listing (matches FileTreeNode model)
struct CodeFile: Codable, Identifiable {
    let id: String
    let name: String
    let path: String
    let isDirectory: Bool
    let children: [CodeFile]?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case path
        case isDirectory = "is_directory"
        case children
    }
}

/// Full file content returned when fetching a single file (matches FileResponse model)
struct CodeFileContent: Codable, Identifiable {
    let id: String
    let workspaceId: String
    let name: String
    let path: String
    let content: String
    let language: String
    let createdAt: String
    let updatedAt: String

    enum CodingKeys: String, CodingKey {
        case id
        case workspaceId = "workspace_id"
        case name
        case path
        case content
        case language
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}
