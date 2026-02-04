import Foundation
import SQLite3
import os

private let logger = Logger(subsystem: "com.magnetarai", category: "ImageAnalysisCache")

/// Cache for image analysis results using SQLite
@MainActor
final class ImageAnalysisCache {

    // MARK: - Properties

    nonisolated(unsafe) private var db: OpaquePointer?
    private let dbPath: URL
    private let maxCacheSize: Int = 100
    private let maxCacheAge: TimeInterval = 7 * 24 * 60 * 60  // 7 days

    // MARK: - Singleton

    static let shared = ImageAnalysisCache()

    // MARK: - Initialization

    private init() {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let cacheDir = documentsPath.appendingPathComponent(".magnetar_ai/cache", isDirectory: true)

        // Create directory if needed
        try? FileManager.default.createDirectory(at: cacheDir, withIntermediateDirectories: true)

        dbPath = cacheDir.appendingPathComponent("image_analysis.sqlite")

        openDatabase()
        createTables()
        pruneOldEntries()

        logger.info("[ImageAnalysisCache] Initialized at \(self.dbPath.path)")
    }

    deinit {
        if let db = db {
            sqlite3_close(db)
        }
    }

    // MARK: - Database Setup

    private func openDatabase() {
        let result = sqlite3_open(dbPath.path, &db)

        if result != SQLITE_OK {
            logger.error("[ImageAnalysisCache] Failed to open database: \(result)")
            db = nil
        }
    }

    private func createTables() {
        let sql = """
            CREATE TABLE IF NOT EXISTS image_analysis_cache (
                image_hash TEXT PRIMARY KEY,
                result_json TEXT NOT NULL,
                created_at REAL NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_cache_created
            ON image_analysis_cache(created_at);
        """

        var errMsg: UnsafeMutablePointer<CChar>?
        let result = sqlite3_exec(db, sql, nil, nil, &errMsg)

        if result != SQLITE_OK {
            if let errMsg = errMsg {
                logger.error("[ImageAnalysisCache] Table creation failed: \(String(cString: errMsg))")
                sqlite3_free(errMsg)
            }
        }
    }

    // MARK: - Cache Operations

    /// Get cached result by image hash
    func get(hash: String) -> ImageAnalysisResult? {
        guard let db = db else { return nil }

        let sql = "SELECT result_json FROM image_analysis_cache WHERE image_hash = ?"
        var statement: OpaquePointer?

        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            return nil
        }
        defer { sqlite3_finalize(statement) }

        sqlite3_bind_text(statement, 1, hash, -1, SQLITE_TRANSIENT)

        guard sqlite3_step(statement) == SQLITE_ROW else {
            return nil
        }

        guard let jsonPtr = sqlite3_column_text(statement, 0) else {
            return nil
        }

        let jsonString = String(cString: jsonPtr)

        do {
            let decoder = JSONDecoder()
            decoder.dateDecodingStrategy = .iso8601
            let result = try decoder.decode(ImageAnalysisResult.self, from: Data(jsonString.utf8))
            logger.debug("[ImageAnalysisCache] Cache hit for \(hash.prefix(8))")
            return result
        } catch {
            logger.error("[ImageAnalysisCache] Failed to decode cached result: \(error.localizedDescription)")
            return nil
        }
    }

    /// Get cached result by analysis result ID
    func get(id: UUID) -> ImageAnalysisResult? {
        guard let db = db else { return nil }

        // Since ID is stored in the JSON, we need to scan for it
        // For better performance in production, add a result_id column
        let sql = "SELECT result_json FROM image_analysis_cache"
        var statement: OpaquePointer?

        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            return nil
        }
        defer { sqlite3_finalize(statement) }

        let decoder = JSONDecoder()
        decoder.dateDecodingStrategy = .iso8601

        while sqlite3_step(statement) == SQLITE_ROW {
            guard let jsonPtr = sqlite3_column_text(statement, 0) else {
                continue
            }

            let jsonString = String(cString: jsonPtr)

            do {
                let result = try decoder.decode(ImageAnalysisResult.self, from: Data(jsonString.utf8))
                if result.id == id {
                    logger.debug("[ImageAnalysisCache] Found result by ID: \(id)")
                    return result
                }
            } catch {
                continue
            }
        }

        return nil
    }

    /// Store analysis result in cache
    func store(_ result: ImageAnalysisResult, hash: String) {
        guard let db = db else { return }

        do {
            let encoder = JSONEncoder()
            encoder.dateEncodingStrategy = .iso8601
            let jsonData = try encoder.encode(result)
            guard let jsonString = String(data: jsonData, encoding: .utf8) else { return }

            let sql = """
                INSERT OR REPLACE INTO image_analysis_cache
                (image_hash, result_json, created_at)
                VALUES (?, ?, ?)
            """
            var statement: OpaquePointer?

            guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
                return
            }
            defer { sqlite3_finalize(statement) }

            sqlite3_bind_text(statement, 1, hash, -1, SQLITE_TRANSIENT)
            sqlite3_bind_text(statement, 2, jsonString, -1, SQLITE_TRANSIENT)
            sqlite3_bind_double(statement, 3, Date().timeIntervalSince1970)

            if sqlite3_step(statement) != SQLITE_DONE {
                logger.error("[ImageAnalysisCache] Failed to store result")
            } else {
                logger.debug("[ImageAnalysisCache] Stored result for \(hash.prefix(8))")
            }

            // Prune if needed
            pruneIfNeeded()

        } catch {
            logger.error("[ImageAnalysisCache] Failed to encode result: \(error.localizedDescription)")
        }
    }

    /// Remove cached result
    func remove(hash: String) {
        guard let db = db else { return }

        let sql = "DELETE FROM image_analysis_cache WHERE image_hash = ?"
        var statement: OpaquePointer?

        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            return
        }
        defer { sqlite3_finalize(statement) }

        sqlite3_bind_text(statement, 1, hash, -1, SQLITE_TRANSIENT)
        sqlite3_step(statement)
    }

    /// Clear all cached results
    func clear() {
        guard let db = db else { return }

        let sql = "DELETE FROM image_analysis_cache"
        sqlite3_exec(db, sql, nil, nil, nil)
        logger.info("[ImageAnalysisCache] Cache cleared")
    }

    // MARK: - Cache Management

    /// Get number of cached entries
    func count() -> Int {
        guard let db = db else { return 0 }

        let sql = "SELECT COUNT(*) FROM image_analysis_cache"
        var statement: OpaquePointer?

        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            return 0
        }
        defer { sqlite3_finalize(statement) }

        guard sqlite3_step(statement) == SQLITE_ROW else {
            return 0
        }

        return Int(sqlite3_column_int(statement, 0))
    }

    /// Get cache size in bytes
    func sizeBytes() -> Int64 {
        guard let attributes = try? FileManager.default.attributesOfItem(atPath: dbPath.path),
              let size = attributes[.size] as? Int64 else {
            return 0
        }
        return size
    }

    private func pruneOldEntries() {
        guard let db = db else { return }

        let cutoff = Date().timeIntervalSince1970 - maxCacheAge
        let sql = "DELETE FROM image_analysis_cache WHERE created_at < ?"
        var statement: OpaquePointer?

        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            return
        }
        defer { sqlite3_finalize(statement) }

        sqlite3_bind_double(statement, 1, cutoff)

        if sqlite3_step(statement) == SQLITE_DONE {
            let deleted = sqlite3_changes(db)
            if deleted > 0 {
                logger.info("[ImageAnalysisCache] Pruned \(deleted) old entries")
            }
        }
    }

    private func pruneIfNeeded() {
        let currentCount = count()
        guard currentCount > maxCacheSize else { return }

        guard let db = db else { return }

        // Delete oldest entries to get back under limit
        let toDelete = currentCount - maxCacheSize + 10

        let sql = """
            DELETE FROM image_analysis_cache
            WHERE image_hash IN (
                SELECT image_hash FROM image_analysis_cache
                ORDER BY created_at ASC
                LIMIT ?
            )
        """
        var statement: OpaquePointer?

        guard sqlite3_prepare_v2(db, sql, -1, &statement, nil) == SQLITE_OK else {
            return
        }
        defer { sqlite3_finalize(statement) }

        sqlite3_bind_int(statement, 1, Int32(toDelete))

        if sqlite3_step(statement) == SQLITE_DONE {
            logger.info("[ImageAnalysisCache] Pruned \(toDelete) entries for size limit")
        }
    }
}

// MARK: - SQLITE_TRANSIENT Helper

private let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)
