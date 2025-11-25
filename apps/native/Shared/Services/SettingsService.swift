import Foundation

/// Service layer for Settings endpoints
final class SettingsService {
    static let shared = SettingsService()
    private let apiClient = ApiClient.shared

    private init() {}

    // MARK: - Saved Queries

    func listSavedQueries() async throws -> [SavedQuery] {
        try await apiClient.request(
            path: "/v1/settings/saved-queries",
            method: .get
        )
    }

    func createSavedQuery(
        name: String,
        query: String,
        tags: [String]? = nil
    ) async throws -> SavedQuery {
        var body: [String: Any] = [
            "name": name,
            "query": query
        ]
        if let tags = tags {
            body["tags"] = tags
        }

        return try await apiClient.request(
            path: "/v1/settings/saved-queries",
            method: .post,
            jsonBody: body
        )
    }

    func updateSavedQuery(
        id: Int,
        name: String? = nil,
        query: String? = nil,
        tags: [String]? = nil
    ) async throws -> SavedQuery {
        var body: [String: Any] = [:]
        if let name = name {
            body["name"] = name
        }
        if let query = query {
            body["query"] = query
        }
        if let tags = tags {
            body["tags"] = tags
        }

        return try await apiClient.request(
            path: "/v1/settings/saved-queries/\(id)",
            method: .put,
            jsonBody: body
        )
    }

    func deleteSavedQuery(id: Int) async throws {
        _ = try await apiClient.request(
            path: "/v1/settings/saved-queries/\(id)",
            method: .delete
        ) as EmptyResponse
    }
}
