//
//  VectorStore.swift
//  MagnetarStudio
//
//  SQLite-backed vector storage for RAG embeddings.
//  Provides persistent, queryable storage for semantic search.
//

import Foundation
import SQLite3
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "VectorStore")

// MARK: - Vector Store

@MainActor
final class VectorStore: ObservableObject {

    // MARK: - Published State

    @Published private(set) var isInitialized: Bool = false
    @Published private(set) var documentCount: Int = 0
    @Published private(set) var lastUpdated: Date?

    // MARK: - Database

    private var db: OpaquePointer?
    private let dbPath: URL

    // MARK: - Cache

    private var embeddingCache: [UUID: [Float]] = [:]
    private let maxCacheSize = 1000

    // MARK: - Singleton

    static let shared = VectorStore()

    // MARK: - Initialization

    init(dbPath: URL? = nil) {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        self.dbPath = dbPath ?? documentsPath.appendingPathComponent(".magnetar_studio/rag/vectors.sqlite")

        Task {
            await initialize()
        }
    }

    deinit {
        if let db = db {
            sqlite3_close(db)
        }
    }

    // MARK: - Database Setup

    func initialize() async {
        guard !isInitialized else { return }

        let directory = dbPath.deletingLastPathComponent()
        do {
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)
        } catch {
            logger.error("[VectorStore] Failed to create database directory: \(error)")
        }

        var dbPointer: OpaquePointer?
        let result = sqlite3_open(dbPath.path, &dbPointer)

        guard result == SQLITE_OK, let database = dbPointer else {
            logger.error("[VectorStore] Failed to open database: \(result)")
            return
        }

        db = database
        await createTables()
        self.documentCount = await countDocuments()

        isInitialized = true
        logger.info("[VectorStore] Initialized with \(self.documentCount) documents")
    }

    private func createTables() async {
        let createSQL = """
        CREATE TABLE IF NOT EXISTS documents (
            id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            embedding BLOB NOT NULL,
            source TEXT NOT NULL,
            metadata TEXT,
            created_at REAL NOT NULL,
            last_accessed_at REAL NOT NULL,
            conversation_id TEXT,
            session_id TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_documents_source ON documents(source);
        CREATE INDEX IF NOT EXISTS idx_documents_conversation ON documents(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_documents_session ON documents(session_id);
        CREATE INDEX IF NOT EXISTS idx_documents_created ON documents(created_at);
        """
        executeSQL(createSQL)
    }

    // MARK: - Document Operations

    func insert(_ document: RAGDocument) async throws {
        guard isInitialized, let db = db else {
            throw VectorStoreError.notInitialized
        }

        let sql = """
        INSERT OR REPLACE INTO documents
        (id, content, embedding, source, metadata, created_at, last_accessed_at, conversation_id, session_id)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        var statement: OpaquePointer?
        defer { sqlite3_finalize(statement) }

        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw VectorStoreError.prepareFailed(String(cString: sqlite3_errmsg(db)))
        }

        sqlite3_bind_text(statement, 1, document.id.uuidString, -1, SQLITE_TRANSIENT)
        sqlite3_bind_text(statement, 2, document.content, -1, SQLITE_TRANSIENT)
        sqlite3_bind_blob(statement, 3, document.embedding, Int32(document.embedding.count * MemoryLayout<Float>.size), SQLITE_TRANSIENT)
        sqlite3_bind_text(statement, 4, document.source.rawValue, -1, SQLITE_TRANSIENT)

        let metadataJSON = try JSONEncoder().encode(document.metadata)
        sqlite3_bind_text(statement, 5, String(data: metadataJSON, encoding: .utf8), -1, SQLITE_TRANSIENT)
        sqlite3_bind_double(statement, 6, document.createdAt.timeIntervalSince1970)
        sqlite3_bind_double(statement, 7, document.lastAccessedAt.timeIntervalSince1970)

        if let convId = document.metadata.conversationId {
            sqlite3_bind_text(statement, 8, convId.uuidString, -1, SQLITE_TRANSIENT)
        } else {
            sqlite3_bind_null(statement, 8)
        }

        if let sessionId = document.metadata.sessionId {
            sqlite3_bind_text(statement, 9, sessionId.uuidString, -1, SQLITE_TRANSIENT)
        } else {
            sqlite3_bind_null(statement, 9)
        }

        guard sqlite3_step(statement) == SQLITE_DONE else {
            throw VectorStoreError.insertFailed(String(cString: sqlite3_errmsg(db)))
        }

        embeddingCache[document.id] = document.embedding
        pruneCache()

        documentCount += 1
        lastUpdated = Date()
    }

    func insertBatch(_ documents: [RAGDocument]) async throws {
        for document in documents {
            try await insert(document)
        }
    }

    func delete(id: UUID) async throws {
        guard isInitialized, let db = db else {
            throw VectorStoreError.notInitialized
        }

        let sql = "DELETE FROM documents WHERE id = ?"
        var statement: OpaquePointer?
        defer { sqlite3_finalize(statement) }

        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw VectorStoreError.prepareFailed(String(cString: sqlite3_errmsg(db)))
        }

        sqlite3_bind_text(statement, 1, id.uuidString, -1, SQLITE_TRANSIENT)

        guard sqlite3_step(statement) == SQLITE_DONE else {
            throw VectorStoreError.deleteFailed(String(cString: sqlite3_errmsg(db)))
        }

        embeddingCache.removeValue(forKey: id)
        documentCount = max(0, documentCount - 1)
    }

    func deleteForConversation(_ conversationId: UUID) async throws {
        guard isInitialized, let db = db else {
            throw VectorStoreError.notInitialized
        }

        let sql = "DELETE FROM documents WHERE conversation_id = ?"
        var statement: OpaquePointer?
        defer { sqlite3_finalize(statement) }

        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw VectorStoreError.prepareFailed(String(cString: sqlite3_errmsg(db)))
        }

        sqlite3_bind_text(statement, 1, conversationId.uuidString, -1, SQLITE_TRANSIENT)

        guard sqlite3_step(statement) == SQLITE_DONE else {
            throw VectorStoreError.deleteFailed(String(cString: sqlite3_errmsg(db)))
        }

        documentCount = await countDocuments()
    }

    // MARK: - Search

    func search(
        query: [Float],
        limit: Int = 10,
        minSimilarity: Float = 0.3,
        sources: [RAGSource]? = nil,
        conversationId: UUID? = nil
    ) async throws -> [RAGSearchResult] {
        guard isInitialized, let db = db else {
            throw VectorStoreError.notInitialized
        }

        var sql = "SELECT id, content, embedding, source, metadata, created_at, last_accessed_at FROM documents"
        var conditions: [String] = []
        var params: [Any] = []

        if let sources = sources, !sources.isEmpty {
            let placeholders = sources.map { _ in "?" }.joined(separator: ", ")
            conditions.append("source IN (\(placeholders))")
            params.append(contentsOf: sources.map { $0.rawValue })
        }

        if let convId = conversationId {
            conditions.append("conversation_id = ?")
            params.append(convId.uuidString)
        }

        if !conditions.isEmpty {
            sql += " WHERE " + conditions.joined(separator: " AND ")
        }

        var statement: OpaquePointer?
        defer { sqlite3_finalize(statement) }

        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw VectorStoreError.prepareFailed(String(cString: sqlite3_errmsg(db)))
        }

        for (index, param) in params.enumerated() {
            if let stringParam = param as? String {
                sqlite3_bind_text(statement, Int32(index + 1), stringParam, -1, SQLITE_TRANSIENT)
            }
        }

        var results: [(RAGDocument, Float)] = []

        while sqlite3_step(statement) == SQLITE_ROW {
            guard let document = parseDocument(from: statement) else { continue }
            let similarity = HashEmbedder.cosineSimilarity(query, document.embedding)

            if similarity >= minSimilarity {
                results.append((document, similarity))
            }
        }

        results.sort { $0.1 > $1.1 }
        let topResults = results.prefix(limit)

        return topResults.enumerated().map { index, item in
            RAGSearchResult(
                document: item.0,
                similarity: item.1,
                rank: index + 1,
                snippet: String(item.0.content.prefix(200))
            )
        }
    }

    func searchText(
        _ text: String,
        limit: Int = 10,
        minSimilarity: Float = 0.3,
        sources: [RAGSource]? = nil,
        conversationId: UUID? = nil
    ) async throws -> [RAGSearchResult] {
        let embedding = HashEmbedder.shared.embed(text)
        return try await search(
            query: embedding,
            limit: limit,
            minSimilarity: minSimilarity,
            sources: sources,
            conversationId: conversationId
        )
    }

    // MARK: - Retrieval

    func get(id: UUID) async throws -> RAGDocument? {
        guard isInitialized, let db = db else {
            throw VectorStoreError.notInitialized
        }

        let sql = "SELECT id, content, embedding, source, metadata, created_at, last_accessed_at FROM documents WHERE id = ?"
        var statement: OpaquePointer?
        defer { sqlite3_finalize(statement) }

        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw VectorStoreError.prepareFailed(String(cString: sqlite3_errmsg(db)))
        }

        sqlite3_bind_text(statement, 1, id.uuidString, -1, SQLITE_TRANSIENT)

        guard sqlite3_step(statement) == SQLITE_ROW else {
            return nil
        }

        return parseDocument(from: statement)
    }

    func getBySource(_ source: RAGSource, limit: Int = 100) async throws -> [RAGDocument] {
        guard isInitialized, let db = db else {
            throw VectorStoreError.notInitialized
        }

        let sql = "SELECT id, content, embedding, source, metadata, created_at, last_accessed_at FROM documents WHERE source = ? ORDER BY created_at DESC LIMIT ?"
        var statement: OpaquePointer?
        defer { sqlite3_finalize(statement) }

        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            throw VectorStoreError.prepareFailed(String(cString: sqlite3_errmsg(db)))
        }

        sqlite3_bind_text(statement, 1, source.rawValue, -1, SQLITE_TRANSIENT)
        sqlite3_bind_int(statement, 2, Int32(limit))

        var documents: [RAGDocument] = []
        while sqlite3_step(statement) == SQLITE_ROW {
            if let doc = parseDocument(from: statement) {
                documents.append(doc)
            }
        }

        return documents
    }

    // MARK: - Statistics

    func countDocuments() async -> Int {
        guard let db = db else { return 0 }

        let sql = "SELECT COUNT(*) FROM documents"
        var statement: OpaquePointer?
        defer { sqlite3_finalize(statement) }

        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK,
              sqlite3_step(statement) == SQLITE_ROW else {
            return 0
        }

        return Int(sqlite3_column_int(statement, 0))
    }

    func getStatistics() async -> RAGIndexStatistics {
        guard let db = db else {
            return RAGIndexStatistics()
        }

        var stats = RAGIndexStatistics(
            totalDocuments: documentCount,
            lastUpdated: lastUpdated ?? Date()
        )

        let sql = "SELECT source, COUNT(*) FROM documents GROUP BY source"
        var statement: OpaquePointer?
        defer { sqlite3_finalize(statement) }

        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            return stats
        }

        while sqlite3_step(statement) == SQLITE_ROW {
            if let sourcePtr = sqlite3_column_text(statement, 0) {
                let source = String(cString: sourcePtr)
                let count = Int(sqlite3_column_int(statement, 1))
                stats.documentsBySource[source] = count
            }
        }

        return stats
    }

    // MARK: - Private Helpers

    private func parseDocument(from statement: OpaquePointer?) -> RAGDocument? {
        guard let statement = statement else { return nil }

        guard let idPtr = sqlite3_column_text(statement, 0),
              let contentPtr = sqlite3_column_text(statement, 1),
              let embeddingPtr = sqlite3_column_blob(statement, 2),
              let sourcePtr = sqlite3_column_text(statement, 3) else {
            return nil
        }

        let id = UUID(uuidString: String(cString: idPtr)) ?? UUID()
        let content = String(cString: contentPtr)

        let embeddingSize = Int(sqlite3_column_bytes(statement, 2))
        let embeddingCount = embeddingSize / MemoryLayout<Float>.size
        let embedding = Array(UnsafeBufferPointer(start: embeddingPtr.assumingMemoryBound(to: Float.self), count: embeddingCount))

        let sourceString = String(cString: sourcePtr)
        let source = RAGSource(rawValue: sourceString) ?? .chatMessage

        var metadata = RAGDocumentMetadata()
        if let metadataPtr = sqlite3_column_text(statement, 4) {
            let metadataString = String(cString: metadataPtr)
            if let metadataData = metadataString.data(using: .utf8) {
                metadata = (try? JSONDecoder().decode(RAGDocumentMetadata.self, from: metadataData)) ?? metadata
            }
        }

        let createdAt = Date(timeIntervalSince1970: sqlite3_column_double(statement, 5))
        let lastAccessedAt = Date(timeIntervalSince1970: sqlite3_column_double(statement, 6))

        return RAGDocument(
            id: id,
            content: content,
            embedding: embedding,
            source: source,
            metadata: metadata,
            createdAt: createdAt,
            lastAccessedAt: lastAccessedAt
        )
    }

    private func executeSQL(_ sql: String) {
        guard let db = db else { return }

        var errMsg: UnsafeMutablePointer<CChar>?
        let result = sqlite3_exec(db, sql, nil, nil, &errMsg)

        if result != SQLITE_OK {
            let error = errMsg.map { String(cString: $0) } ?? "Unknown error"
            logger.error("[VectorStore] SQL error: \(error)")
            sqlite3_free(errMsg)
        }
    }

    private func pruneCache() {
        if embeddingCache.count > maxCacheSize {
            let keysToRemove = Array(embeddingCache.keys.prefix(maxCacheSize / 2))
            for key in keysToRemove {
                embeddingCache.removeValue(forKey: key)
            }
        }
    }

    func clear() async throws {
        guard isInitialized, db != nil else {
            throw VectorStoreError.notInitialized
        }

        executeSQL("DELETE FROM documents")
        embeddingCache.removeAll()
        documentCount = 0
        lastUpdated = Date()
    }
}

// MARK: - Errors

enum VectorStoreError: LocalizedError {
    case notInitialized
    case prepareFailed(String)
    case insertFailed(String)
    case deleteFailed(String)
    case queryFailed(String)

    var errorDescription: String? {
        switch self {
        case .notInitialized:
            return "Vector store not initialized"
        case .prepareFailed(let msg):
            return "SQL prepare failed: \(msg)"
        case .insertFailed(let msg):
            return "Insert failed: \(msg)"
        case .deleteFailed(let msg):
            return "Delete failed: \(msg)"
        case .queryFailed(let msg):
            return "Query failed: \(msg)"
        }
    }
}

private let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)
