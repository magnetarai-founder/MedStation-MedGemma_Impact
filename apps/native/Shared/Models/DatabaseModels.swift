import Foundation

// MARK: - Session

struct SessionResponse: Codable {
    let sessionId: String
    let createdAt: String

    enum CodingKeys: String, CodingKey {
        case sessionId = "session_id"
        case createdAt = "created_at"
    }
}

// MARK: - File Upload

struct FileColumn: Codable {
    let originalName: String
    let cleanName: String
    let dtype: String
    let nonNullCount: Int
    let nullCount: Int

    enum CodingKeys: String, CodingKey {
        case originalName = "original_name"
        case cleanName = "clean_name"
        case dtype
        case nonNullCount = "non_null_count"
        case nullCount = "null_count"
    }
}

struct FileUploadResponse: Codable {
    let filename: String
    let sizeMb: Double
    let rowCount: Int
    let columnCount: Int
    let columns: [FileColumn]
    let preview: [[String: AnyCodable]]?

    enum CodingKeys: String, CodingKey {
        case filename
        case sizeMb = "size_mb"
        case rowCount = "row_count"
        case columnCount = "column_count"
        case columns
        case preview
    }
}

struct JsonUploadResponse: Codable {
    let filename: String
    let sizeMb: Double
    let objectCount: Int
    let columns: [String]
    let preview: [[String: AnyCodable]]

    enum CodingKeys: String, CodingKey {
        case filename
        case sizeMb = "size_mb"
        case objectCount = "object_count"
        case columns
        case preview
    }
}

// MARK: - Query

struct QueryResponse: Codable {
    let queryId: String
    let rowCount: Int
    let columnCount: Int
    let columns: [String]
    let executionTimeMs: Int
    let preview: [[String: AnyCodable]]
    let hasMore: Bool
    var isPreviewOnly: Bool?
    let originalTotalRows: Int?

    enum CodingKeys: String, CodingKey {
        case queryId = "query_id"
        case rowCount = "row_count"
        case columnCount = "column_count"
        case columns
        case executionTimeMs = "execution_time_ms"
        case preview
        case hasMore = "has_more"
        case isPreviewOnly = "is_preview_only"
        case originalTotalRows = "original_total_rows"
    }
}

// MARK: - Query History

struct QueryHistoryItem: Codable, Identifiable {
    let id: String
    let query: String
    let timestamp: String
    let executionTime: Int?
    let rowCount: Int?
    let status: String // "success" | "error"

    enum CodingKeys: String, CodingKey {
        case id
        case query
        case timestamp
        case executionTime
        case rowCount
        case status
    }
}

struct QueryHistoryResponse: Codable {
    let history: [QueryHistoryItem]
}

// MARK: - JSON Convert

struct JsonConvertResponse: Codable {
    let filename: String
    let success: Bool
    let outputFile: String?
    let totalRows: Int
    let sheets: [String]?
    let columns: [String]?
    let preview: [[String: AnyCodable]]
    let isPreviewOnly: Bool?

    enum CodingKeys: String, CodingKey {
        case filename
        case success
        case outputFile = "output_file"
        case totalRows = "total_rows"
        case sheets
        case columns
        case preview
        case isPreviewOnly = "is_preview_only"
    }
}

// MARK: - Saved Queries

struct SavedQueriesResponse: Codable {
    let queries: [SavedQuery]
}

struct SaveQueryResponse: Codable {
    let id: Int
    let success: Bool
}

// MARK: - Empty Types

struct EmptyBody: Codable {}
struct EmptyResponse: Codable {}
