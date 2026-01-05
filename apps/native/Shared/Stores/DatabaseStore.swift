import Foundation
import Observation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "DatabaseStore")

/// Database workspace state and operations
@MainActor
@Observable
final class DatabaseStore {
    static let shared = DatabaseStore()

    // MARK: - Observable State

    private(set) var sessionId: String?
    private(set) var currentFile: FileUploadResponse?
    private(set) var currentQuery: QueryResponse?
    var contentType: ContentType = .sql
    private(set) var isExecuting: Bool = false
    private(set) var isUploading: Bool = false
    private(set) var isCreatingSession: Bool = false
    var error: String?

    // Session retry tracking
    private var sessionRetryCount: Int = 0
    private static let maxSessionRetries = 3

    // Editor state
    var editorText: String = ""
    var hasExecuted: Bool = false

    /// Whether session is active and ready for operations
    var hasActiveSession: Bool {
        sessionId != nil
    }

    /// Whether session creation failed and user should be notified
    var sessionCreationFailed: Bool {
        sessionId == nil && sessionRetryCount >= Self.maxSessionRetries
    }

    enum ContentType {
        case sql
        case json
    }

    private let service = DatabaseService.shared

    private init() {}

    // MARK: - Session Management

    /// Create a fresh session (call after auth)
    func createSession() async {
        guard !isCreatingSession else { return }

        isCreatingSession = true
        defer { isCreatingSession = false }

        do {
            let session = try await service.createSession()
            sessionId = session.sessionId
            sessionRetryCount = 0
            error = nil
            logger.info("Database session created: \(session.sessionId)")
        } catch {
            sessionRetryCount += 1
            self.error = "Failed to create session: \(error.localizedDescription)"
            logger.error("Session creation failed (attempt \(self.sessionRetryCount)/\(Self.maxSessionRetries)): \(error)")
        }
    }

    /// Ensure we have an active session, retrying if needed
    /// Call this before any operation that requires a session
    func ensureSession() async -> Bool {
        if sessionId != nil {
            return true
        }

        // Don't retry if we've exhausted attempts
        if sessionRetryCount >= Self.maxSessionRetries {
            logger.warning("Session creation failed after \(Self.maxSessionRetries) attempts")
            return false
        }

        await createSession()
        return sessionId != nil
    }

    /// Reset retry counter (e.g., after network comes back online)
    func resetSessionRetry() {
        sessionRetryCount = 0
        error = nil
    }

    func deleteSession() async {
        guard let id = sessionId else { return }
        await service.deleteSession(id: id)
        sessionId = nil
        sessionRetryCount = 0
        currentFile = nil
        currentQuery = nil
    }

    // MARK: - File Upload

    func uploadFile(url: URL) async {
        // Auto-retry session if needed
        guard await ensureSession(), let id = sessionId else {
            error = sessionCreationFailed
                ? "Session creation failed. Please try again or restart the app."
                : "No active session"
            return
        }

        isUploading = true
        defer { isUploading = false }

        do {
            let ext = url.pathExtension.lowercased()

            if ext == "json" {
                // Upload as JSON
                let jsonResp = try await service.uploadJson(sessionId: id, fileURL: url)

                // Normalize to FileUploadResponse shape
                currentFile = FileUploadResponse(
                    filename: jsonResp.filename,
                    sizeMb: jsonResp.sizeMb,
                    rowCount: jsonResp.objectCount,
                    columnCount: jsonResp.columns.count,
                    columns: jsonResp.columns.map { col in
                        FileColumn(
                            originalName: col,
                            cleanName: col,
                            dtype: "string",
                            nonNullCount: 0,
                            nullCount: 0
                        )
                    },
                    preview: jsonResp.preview
                )
                contentType = .json
            } else {
                // Upload as Excel/CSV
                currentFile = try await service.uploadFile(sessionId: id, fileURL: url)
                contentType = .sql
            }

            error = nil
        } catch {
            self.error = "Upload failed: \(error.localizedDescription)"
        }
    }

    // MARK: - Editor

    /// Load text into editor (e.g., from saved query)
    func loadEditorText(_ text: String, contentType: ContentType = .sql) {
        editorText = text
        self.contentType = contentType
        currentQuery = nil
        hasExecuted = false
    }

    // MARK: - Query Execution

    func previewQuery(sql: String) async {
        await runQuery(sql: sql, limit: 10, isPreview: true)
    }

    func runQuery(sql: String, limit: Int? = nil, isPreview: Bool = false) async {
        // Auto-retry session if needed
        guard await ensureSession(), let id = sessionId else {
            error = sessionCreationFailed
                ? "Session creation failed. Please try again or restart the app."
                : "No active session"
            return
        }

        guard currentFile != nil else {
            error = "Upload a file first"
            return
        }

        if isExecuting { return }

        isExecuting = true
        defer { isExecuting = false }

        do {
            currentQuery = try await service.executeQuery(
                sessionId: id,
                sql: sql,
                limit: limit,
                isPreview: isPreview
            )
            hasExecuted = true
            error = nil
        } catch {
            self.error = "Query failed: \(error.localizedDescription)"
        }
    }

    // MARK: - JSON Conversion

    func convertJson(jsonText: String) async {
        // Auto-retry session if needed
        guard await ensureSession(), let id = sessionId else {
            error = sessionCreationFailed
                ? "Session creation failed. Please try again or restart the app."
                : "No active session"
            return
        }

        if isExecuting { return }

        isExecuting = true
        defer { isExecuting = false }

        do {
            let resp = try await service.convertJson(sessionId: id, json: jsonText)

            // Normalize to QueryResponse shape
            currentQuery = QueryResponse(
                queryId: "json_\(Date().timeIntervalSince1970)",
                rowCount: resp.totalRows,
                columnCount: resp.columns?.count ?? 0,
                columns: resp.columns ?? [],
                executionTimeMs: 0,
                preview: resp.preview,
                hasMore: resp.totalRows > resp.preview.count,
                isPreviewOnly: resp.isPreviewOnly ?? true,
                originalTotalRows: resp.totalRows
            )

            // Update columns in sidebar
            currentFile = FileUploadResponse(
                filename: "json_data.json",
                sizeMb: 0,
                rowCount: resp.totalRows,
                columnCount: resp.columns?.count ?? 0,
                columns: (resp.columns ?? []).map { col in
                    FileColumn(
                        originalName: col,
                        cleanName: col,
                        dtype: "string",
                        nonNullCount: 0,
                        nullCount: 0
                    )
                },
                preview: resp.preview
            )

            contentType = .json
            error = nil
        } catch {
            self.error = "Convert failed: \(error.localizedDescription)"
        }
    }

    // MARK: - Export

    func exportResults(format: String, filename: String? = nil) async -> Data? {
        guard let id = sessionId,
              let query = currentQuery,
              query.isPreviewOnly != true else {
            error = "Cannot export preview-only results"
            return nil
        }

        do {
            let data = try await service.exportResults(
                sessionId: id,
                queryId: query.queryId,
                format: format,
                filename: filename
            )
            error = nil
            return data
        } catch {
            self.error = "Export failed: \(error.localizedDescription)"
            return nil
        }
    }

    func downloadJsonResult(format: String) async -> Data? {
        // Auto-retry session if needed
        guard await ensureSession(), let id = sessionId else {
            error = sessionCreationFailed
                ? "Session creation failed. Please try again or restart the app."
                : "No active session"
            return nil
        }

        do {
            let data = try await service.downloadJsonResult(sessionId: id, format: format)
            error = nil
            return data
        } catch {
            self.error = "Download failed: \(error.localizedDescription)"
            return nil
        }
    }

    // MARK: - Query History

    func fetchHistory() async -> [QueryHistoryItem] {
        guard let id = sessionId else { return [] }

        do {
            let items = try await service.fetchQueryHistory(sessionId: id)
            error = nil
            return items
        } catch {
            self.error = "History failed: \(error.localizedDescription)"
            return []
        }
    }

    func deleteHistoryItem(_ historyId: String) async {
        guard let id = sessionId else { return }

        do {
            try await service.deleteHistoryItem(sessionId: id, historyId: historyId)
            error = nil
        } catch {
            self.error = "Delete history failed: \(error.localizedDescription)"
        }
    }
}
