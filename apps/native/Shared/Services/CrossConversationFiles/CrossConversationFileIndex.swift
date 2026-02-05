//
//  CrossConversationFileIndex.swift
//  MagnetarStudio
//
//  Cross-conversation file index for intelligent file memory.
//  Tracks file usage patterns across sessions for context-aware suggestions.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "CrossConversationFileIndex")

// MARK: - Cross-Conversation File Index

@MainActor
final class CrossConversationFileIndex: ObservableObject {

    // MARK: - Published State

    @Published private(set) var indexedFileCount: Int = 0
    @Published private(set) var lastIndexUpdate: Date?
    @Published private(set) var isRebuilding: Bool = false

    // MARK: - Dependencies

    private let storage: FileIndexStorage
    private let embedder: HashEmbedder
    private let predictor: ANEPredictor

    // MARK: - Configuration

    private let maxIndexSize: Int = 10000
    private let embeddingDimension: Int = 384

    // MARK: - Singleton

    static let shared = CrossConversationFileIndex()

    // MARK: - Task Management

    private var loadTask: Task<Void, Never>?

    // MARK: - Initialization

    init(
        storage: FileIndexStorage? = nil,
        embedder: HashEmbedder? = nil,
        predictor: ANEPredictor? = nil
    ) {
        self.storage = storage ?? FileIndexStorage()
        self.embedder = embedder ?? .shared
        self.predictor = predictor ?? .shared

        loadTask = Task {
            await loadIndex()
        }
    }

    // MARK: - Index Management

    /// Load index from persistent storage
    private func loadIndex() async {
        let count = await storage.getIndexedCount()
        indexedFileCount = count
        lastIndexUpdate = await storage.getLastUpdateTime()
        logger.info("[FileIndex] Loaded index with \(count) files")
    }

    /// Index a file reference from a conversation
    func indexFile(_ file: FileReference, conversationId: UUID, query: String? = nil) async {
        do {
            // Generate embedding from content or filename
            let textToEmbed = file.processedContent ?? file.filename
            let embedding = embedder.embed(textToEmbed)

            // Create or update indexed entry
            let entry = IndexedFileEntry(
                fileId: file.id,
                filename: file.filename,
                fileType: file.fileType,
                embedding: embedding,
                conversationIds: [conversationId],
                accessCount: 1,
                lastAccessed: Date(),
                firstIndexed: Date(),
                isVaultProtected: file.isVaultProtected,
                vaultFileId: file.vaultFileId,
                contentHash: hashContent(file.processedContent),
                queryContext: query
            )

            try await storage.upsert(entry)
            indexedFileCount = await storage.getIndexedCount()
            lastIndexUpdate = Date()

            logger.debug("[FileIndex] Indexed file: \(file.filename)")

        } catch {
            logger.error("[FileIndex] Failed to index file: \(error)")
        }
    }

    /// Record file access in a conversation
    func recordAccess(fileId: UUID, conversationId: UUID, context: FileAccessContext) async {
        do {
            try await storage.recordAccess(
                fileId: fileId,
                conversationId: conversationId,
                timestamp: Date(),
                context: context
            )

            logger.debug("[FileIndex] Recorded access for file: \(fileId)")

        } catch {
            logger.error("[FileIndex] Failed to record access: \(error)")
        }
    }

    /// Get files relevant to a query across all conversations
    func findRelevantFiles(
        query: String,
        limit: Int = 10,
        excludeConversation: UUID? = nil,
        minSimilarity: Float = 0.3
    ) async -> [CrossConversationFileResult] {
        let queryEmbedding = embedder.embed(query)

        // Get all indexed files
        var entries = await storage.getAllEntries()

            // Exclude current conversation if specified
            if let exclude = excludeConversation {
                entries = entries.filter { !$0.conversationIds.contains(exclude) }
            }

            // Score by similarity
            var results: [(IndexedFileEntry, Float)] = []

            for entry in entries {
                let similarity = HashEmbedder.cosineSimilarity(queryEmbedding, entry.embedding)

                if similarity >= minSimilarity {
                    results.append((entry, similarity))
                }
            }

            // Sort by similarity and take top results
            results.sort { $0.1 > $1.1 }
            let topResults = results.prefix(limit)

            return topResults.map { entry, similarity in
                CrossConversationFileResult(
                    fileId: entry.fileId,
                    filename: entry.filename,
                    fileType: entry.fileType,
                    similarity: similarity,
                    conversationCount: entry.conversationIds.count,
                    totalAccessCount: entry.accessCount,
                    lastAccessed: entry.lastAccessed,
                    isVaultProtected: entry.isVaultProtected,
                    relevanceBoost: calculateRelevanceBoost(entry)
                )
            }
    }

    /// Get files from related conversations
    func getFilesFromRelatedConversations(
        currentConversationId: UUID,
        topics: [String],
        limit: Int = 5
    ) async -> [CrossConversationFileResult] {
        // Get ANE predictions for likely file needs
        let prediction = predictor.predictContextNeeds(
                currentWorkspace: .chat,
                recentQuery: topics.joined(separator: " "),
                activeFileId: nil
            )

            // Combine topic-based and prediction-based search
            var allResults: [CrossConversationFileResult] = []

            // Search for each topic
            for topic in topics {
                let topicResults = await findRelevantFiles(
                    query: topic,
                    limit: 3,
                    excludeConversation: currentConversationId
                )
                allResults.append(contentsOf: topicResults)
            }

            // Search for predicted topics
            for predictedTopic in prediction.likelyTopics.prefix(3) {
                let predictedResults = await findRelevantFiles(
                    query: predictedTopic,
                    limit: 2,
                    excludeConversation: currentConversationId
                )
                allResults.append(contentsOf: predictedResults)
            }

            // Deduplicate and sort
            var seen = Set<UUID>()
            let unique = allResults.filter { result in
                if seen.contains(result.fileId) {
                    return false
                }
                seen.insert(result.fileId)
                return true
            }

        return Array(unique.sorted { $0.combinedScore > $1.combinedScore }.prefix(limit))
    }

    /// Get frequently co-accessed files
    func getCoAccessedFiles(with fileId: UUID, limit: Int = 5) async -> [CrossConversationFileResult] {
        // Get conversations that include this file
        guard let entry = await storage.getEntry(fileId: fileId) else {
            return []
        }

        let conversationIds = entry.conversationIds

        // Find other files in those conversations
        var coAccessCounts: [UUID: Int] = [:]

        for convId in conversationIds {
            let filesInConversation = await storage.getFilesInConversation(convId)
            for otherFile in filesInConversation where otherFile.fileId != fileId {
                coAccessCounts[otherFile.fileId, default: 0] += 1
            }
        }

        // Get full entries for top co-accessed files
        let topCoAccessed = coAccessCounts.sorted { $0.value > $1.value }.prefix(limit)
        var results: [CrossConversationFileResult] = []

        for (coFileId, coCount) in topCoAccessed {
            if let coEntry = await storage.getEntry(fileId: coFileId) {
                let result = CrossConversationFileResult(
                    fileId: coEntry.fileId,
                    filename: coEntry.filename,
                    fileType: coEntry.fileType,
                    similarity: 0,  // Not similarity-based
                    conversationCount: coEntry.conversationIds.count,
                    totalAccessCount: coEntry.accessCount,
                    lastAccessed: coEntry.lastAccessed,
                    isVaultProtected: coEntry.isVaultProtected,
                    relevanceBoost: Float(coCount) / Float(conversationIds.count),
                    coAccessScore: Float(coCount) / Float(conversationIds.count)
                )
                results.append(result)
            }
        }

        return results
    }

    /// Rebuild the entire index
    func rebuildIndex() async {
        guard !isRebuilding else { return }

        isRebuilding = true
        defer { isRebuilding = false }

        logger.info("[FileIndex] Starting index rebuild")

        do {
            // Re-embed all entries
            let entries = await storage.getAllEntries()

            for entry in entries {
                let textToEmbed = entry.filename
                let newEmbedding = embedder.embed(textToEmbed)

                var updated = entry
                updated.embedding = newEmbedding

                try await storage.upsert(updated)
            }

            lastIndexUpdate = Date()
            logger.info("[FileIndex] Rebuild complete, processed \(entries.count) files")

        } catch {
            logger.error("[FileIndex] Rebuild failed: \(error)")
        }
    }

    /// Prune old entries beyond max size
    func pruneIndex() async {
        do {
            let pruned = try await storage.pruneOldEntries(keepCount: maxIndexSize)
            if pruned > 0 {
                indexedFileCount = await storage.getIndexedCount()
                logger.info("[FileIndex] Pruned \(pruned) old entries")
            }
        } catch {
            logger.error("[FileIndex] Prune failed: \(error)")
        }
    }

    // MARK: - Helpers

    private func hashContent(_ content: String?) -> String? {
        guard let content = content else { return nil }
        return content.data(using: .utf8)?.base64EncodedString()
    }

    private func calculateRelevanceBoost(_ entry: IndexedFileEntry) -> Float {
        var boost: Float = 0

        // Recency boost (files accessed recently get a boost)
        let hoursSinceAccess = Date().timeIntervalSince(entry.lastAccessed) / 3600
        if hoursSinceAccess < 24 {
            boost += 0.2
        } else if hoursSinceAccess < 168 {  // 1 week
            boost += 0.1
        }

        // Frequency boost (frequently accessed files get a boost)
        if entry.accessCount >= 10 {
            boost += 0.15
        } else if entry.accessCount >= 5 {
            boost += 0.1
        } else if entry.accessCount >= 2 {
            boost += 0.05
        }

        // Cross-conversation boost (files used in multiple conversations)
        if entry.conversationIds.count >= 5 {
            boost += 0.15
        } else if entry.conversationIds.count >= 2 {
            boost += 0.1
        }

        return min(0.5, boost)  // Cap at 0.5
    }
}

// MARK: - Supporting Types

/// An indexed file entry with cross-conversation tracking
struct IndexedFileEntry: Codable, Identifiable {
    var id: UUID { fileId }

    let fileId: UUID
    var filename: String
    var fileType: String
    var embedding: [Float]
    var conversationIds: [UUID]
    var accessCount: Int
    var lastAccessed: Date
    var firstIndexed: Date
    var isVaultProtected: Bool
    var vaultFileId: UUID?
    var contentHash: String?
    var queryContext: String?  // Query that led to this file being accessed
}

/// Result from cross-conversation file search
struct CrossConversationFileResult: Identifiable {
    var id: UUID { fileId }

    let fileId: UUID
    let filename: String
    let fileType: String
    let similarity: Float
    let conversationCount: Int
    let totalAccessCount: Int
    let lastAccessed: Date
    let isVaultProtected: Bool
    let relevanceBoost: Float
    var coAccessScore: Float = 0

    /// Combined score for ranking
    var combinedScore: Float {
        return (similarity * 0.6) + (relevanceBoost * 0.3) + (coAccessScore * 0.1)
    }

    /// Human-readable description
    var description: String {
        var parts: [String] = [filename]

        if conversationCount > 1 {
            parts.append("used in \(conversationCount) conversations")
        }

        if totalAccessCount > 1 {
            parts.append("accessed \(totalAccessCount) times")
        }

        return parts.joined(separator: ", ")
    }
}

/// Context about a file access
struct FileAccessContext: Codable {
    let query: String?
    let workspace: String
    let action: FileAccessAction

    enum FileAccessAction: String, Codable {
        case opened
        case mentioned
        case searched
        case attached
        case summarized
    }
}

// MARK: - File Index Storage

/// Persistent storage for the file index
actor FileIndexStorage {

    private var entries: [UUID: IndexedFileEntry] = [:]
    private var accessLog: [FileAccessLogEntry] = []
    private let storageURL: URL
    private var saveTask: Task<Void, Never>?

    init() {
        let documentsPath = (FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory)
        self.storageURL = documentsPath.appendingPathComponent(".magnetar_studio/file_index")

        Task {
            await loadFromDisk()
        }
    }

    func getIndexedCount() -> Int {
        return entries.count
    }

    func getLastUpdateTime() -> Date? {
        return entries.values.map { $0.lastAccessed }.max()
    }

    func getAllEntries() -> [IndexedFileEntry] {
        return Array(entries.values)
    }

    func getEntry(fileId: UUID) -> IndexedFileEntry? {
        return entries[fileId]
    }

    func getFilesInConversation(_ conversationId: UUID) -> [IndexedFileEntry] {
        return entries.values.filter { $0.conversationIds.contains(conversationId) }
    }

    func upsert(_ entry: IndexedFileEntry) throws {
        if var existing = entries[entry.fileId] {
            // Merge conversation IDs
            var allConversations = Set(existing.conversationIds)
            allConversations.formUnion(entry.conversationIds)
            existing.conversationIds = Array(allConversations)

            // Update counts and timestamps
            existing.accessCount += 1
            existing.lastAccessed = entry.lastAccessed
            existing.embedding = entry.embedding

            entries[entry.fileId] = existing
        } else {
            entries[entry.fileId] = entry
        }

        saveTask = Task { self.saveToDisk() }
    }

    func recordAccess(
        fileId: UUID,
        conversationId: UUID,
        timestamp: Date,
        context: FileAccessContext
    ) throws {
        // Update entry
        if var entry = entries[fileId] {
            entry.accessCount += 1
            entry.lastAccessed = timestamp

            if !entry.conversationIds.contains(conversationId) {
                entry.conversationIds.append(conversationId)
            }

            entries[fileId] = entry
        }

        // Log access
        let logEntry = FileAccessLogEntry(
            fileId: fileId,
            conversationId: conversationId,
            timestamp: timestamp,
            context: context
        )
        accessLog.append(logEntry)

        // Trim log if too large
        if accessLog.count > 10000 {
            accessLog = Array(accessLog.suffix(5000))
        }

        saveTask = Task { self.saveToDisk() }
    }

    func pruneOldEntries(keepCount: Int) throws -> Int {
        guard entries.count > keepCount else { return 0 }

        // Sort by last accessed and keep most recent
        let sorted = entries.values.sorted { $0.lastAccessed > $1.lastAccessed }
        let toKeep = Array(sorted.prefix(keepCount))

        let pruneCount = entries.count - toKeep.count
        entries = Dictionary(uniqueKeysWithValues: toKeep.map { ($0.fileId, $0) })

        saveTask = Task { self.saveToDisk() }
        return pruneCount
    }

    // MARK: - Persistence

    private func loadFromDisk() {
        let entriesURL = storageURL.appendingPathComponent("entries.json")

        guard FileManager.default.fileExists(atPath: entriesURL.path) else { return }

        do {
            let data = try Data(contentsOf: entriesURL)
            let decoded = try JSONDecoder().decode([IndexedFileEntry].self, from: data)
            entries = Dictionary(uniqueKeysWithValues: decoded.map { ($0.fileId, $0) })
        } catch {
            logger.error("[FileIndexStorage] Failed to load: \(error)")
        }
    }

    private func saveToDisk() {
        do {
            try FileManager.default.createDirectory(at: storageURL, withIntermediateDirectories: true)

            let entriesURL = storageURL.appendingPathComponent("entries.json")
            let data = try JSONEncoder().encode(Array(entries.values))
            try data.write(to: entriesURL)
        } catch {
            logger.error("[FileIndexStorage] Failed to save: \(error)")
        }
    }
}

/// Log entry for file access tracking
struct FileAccessLogEntry: Codable {
    let fileId: UUID
    let conversationId: UUID
    let timestamp: Date
    let context: FileAccessContext
}
