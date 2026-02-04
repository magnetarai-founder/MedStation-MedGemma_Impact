//
//  CodeRAGService.swift
//  MagnetarStudio
//
//  High-level code-specific semantic search for the Coding workspace.
//  Wraps VectorStore and SemanticSearchService with code-aware queries,
//  ANE-boosted relevance, and intelligent context assembly.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "CodeRAGService")

// MARK: - Code Search Query

/// A query for searching the code index
struct CodeSearchQuery: Sendable {
    let text: String
    let language: CodeLanguage?
    let searchScope: SearchScope
    let limit: Int
    let minSimilarity: Float

    enum SearchScope: String, Sendable {
        case all           // Search everything
        case functions     // Only function/method definitions
        case types         // Classes, structs, enums, protocols
        case imports       // Import statements
        case comments      // Documentation and comments
        case symbols       // Search by symbol name
    }

    init(
        text: String,
        language: CodeLanguage? = nil,
        searchScope: SearchScope = .all,
        limit: Int = 10,
        minSimilarity: Float = 0.25
    ) {
        self.text = text
        self.language = language
        self.searchScope = searchScope
        self.limit = limit
        self.minSimilarity = minSimilarity
    }
}

// MARK: - Code Search Result

/// A result from code semantic search
struct CodeRAGResult: Sendable, Identifiable {
    let id: UUID
    let filePath: String
    let fileName: String
    let language: CodeLanguage
    let content: String
    let startLine: Int
    let endLine: Int
    let similarity: Float
    let symbolName: String?
    let chunkKind: CodeChunk.ChunkKind
    let tags: [String]

    init(
        id: UUID = UUID(),
        filePath: String,
        content: String,
        startLine: Int = 0,
        endLine: Int = 0,
        similarity: Float,
        symbolName: String? = nil,
        chunkKind: CodeChunk.ChunkKind = .body,
        tags: [String] = []
    ) {
        self.id = id
        self.filePath = filePath
        self.fileName = (filePath as NSString).lastPathComponent
        self.language = CodeLanguage.detect(from: filePath)
        self.content = content
        self.startLine = startLine
        self.endLine = endLine
        self.similarity = similarity
        self.symbolName = symbolName
        self.chunkKind = chunkKind
        self.tags = tags
    }
}

// MARK: - Code Context

/// Assembled code context for AI prompt injection
struct CodeRAGContext: Sendable {
    let results: [CodeRAGResult]
    let formattedContext: String
    let tokenEstimate: Int
    let searchDuration: TimeInterval

    /// Whether this context has meaningful results
    var hasContent: Bool {
        !results.isEmpty
    }
}

// MARK: - Code RAG Service

/// High-level service for code-specific semantic search and context assembly
@MainActor
final class CodeRAGService {
    // MARK: - Singleton

    static let shared = CodeRAGService()

    // MARK: - Dependencies

    private let embeddingService = CodeEmbeddingService.shared
    private let vectorStore = VectorStore.shared
    private let embedder = HashEmbedder.shared

    // MARK: - State

    /// Search statistics
    private(set) var searchCount: Int = 0
    private(set) var averageSearchTimeMs: Float = 0

    // MARK: - Init

    private init() {}

    // MARK: - Search

    /// Search the code index with a natural language query
    func search(_ query: CodeSearchQuery) async throws -> [CodeRAGResult] {
        let startTime = Date()

        // Generate query embedding
        let queryEmbedding = embedder.embed(query.text)

        // Search vector store for code files only
        let results = try await vectorStore.search(
            query: queryEmbedding,
            limit: query.limit * 2,  // Over-fetch for filtering
            minSimilarity: query.minSimilarity,
            sources: [.codeFile]
        )

        // Convert to CodeRAGResults and filter by scope
        var codeResults = results.compactMap { result -> CodeRAGResult? in
            convertToCodeResult(result)
        }

        // Apply scope filter
        codeResults = filterByScope(codeResults, scope: query.searchScope)

        // Apply language filter
        if let language = query.language {
            codeResults = codeResults.filter { $0.language == language }
        }

        // Apply ANE relevance boost if available
        codeResults = applyRelevanceBoost(codeResults, query: query.text)

        // Sort by similarity and take limit
        codeResults.sort { $0.similarity > $1.similarity }
        codeResults = Array(codeResults.prefix(query.limit))

        // Update stats
        let duration = Date().timeIntervalSince(startTime)
        updateStats(duration: duration)

        logger.debug("[CodeRAG] Search '\(query.text)' returned \(codeResults.count) results in \(Int(duration * 1000))ms")

        return codeResults
    }

    /// Quick search for the most relevant code snippet
    func quickSearch(_ text: String, limit: Int = 5) async throws -> [CodeRAGResult] {
        return try await search(CodeSearchQuery(text: text, limit: limit))
    }

    /// Find functions related to a query
    func findFunctions(_ query: String, language: CodeLanguage? = nil) async throws -> [CodeRAGResult] {
        return try await search(CodeSearchQuery(
            text: query,
            language: language,
            searchScope: .functions,
            limit: 10
        ))
    }

    /// Find types (classes, structs, enums) related to a query
    func findTypes(_ query: String, language: CodeLanguage? = nil) async throws -> [CodeRAGResult] {
        return try await search(CodeSearchQuery(
            text: query,
            language: language,
            searchScope: .types,
            limit: 10
        ))
    }

    /// Find code by symbol name
    func findSymbol(_ name: String) async throws -> [CodeRAGResult] {
        return try await search(CodeSearchQuery(
            text: name,
            searchScope: .symbols,
            limit: 5,
            minSimilarity: 0.2
        ))
    }

    // MARK: - Context Assembly

    /// Build code context for AI prompt injection based on a user query
    func buildContext(
        for query: String,
        maxTokens: Int = 4000,
        language: CodeLanguage? = nil
    ) async throws -> CodeRAGContext {
        let startTime = Date()

        // Search for relevant code
        let results = try await search(CodeSearchQuery(
            text: query,
            language: language,
            limit: 15,
            minSimilarity: 0.2
        ))

        // Assemble context within token budget
        var contextParts: [String] = []
        var tokenCount = 0
        var includedResults: [CodeRAGResult] = []

        for result in results {
            let snippet = formatSnippet(result)
            let snippetTokens = estimateTokens(snippet)

            if tokenCount + snippetTokens > maxTokens {
                break
            }

            contextParts.append(snippet)
            tokenCount += snippetTokens
            includedResults.append(result)
        }

        let formatted: String
        if contextParts.isEmpty {
            formatted = ""
        } else {
            formatted = "Relevant code from the workspace:\n\n" + contextParts.joined(separator: "\n\n---\n\n")
        }

        let duration = Date().timeIntervalSince(startTime)

        return CodeRAGContext(
            results: includedResults,
            formattedContext: formatted,
            tokenEstimate: tokenCount,
            searchDuration: duration
        )
    }

    // MARK: - Indexing Delegation

    /// Index a workspace directory (delegates to CodeEmbeddingService)
    func indexWorkspace(at path: String) async throws -> IndexingStats {
        return try await embeddingService.indexWorkspace(at: path)
    }

    /// Get indexing status
    var isIndexing: Bool {
        embeddingService.isIndexing
    }

    /// Number of indexed files
    var indexedFileCount: Int {
        embeddingService.indexedFiles.count
    }

    /// Total indexed chunks
    var indexedChunkCount: Int {
        embeddingService.totalDocumentsIndexed
    }

    // MARK: - Private Helpers

    /// Convert RAGSearchResult to CodeRAGResult
    private func convertToCodeResult(_ ragResult: RAGSearchResult) -> CodeRAGResult? {
        let doc = ragResult.document
        guard doc.source == .codeFile else { return nil }

        let filePath = doc.metadata.title ?? "unknown"
        let tags = doc.metadata.tags ?? []

        // Extract line numbers from metadata if available
        // (stored in tags as "L123-L456" format)
        let startLine = doc.metadata.chunkIndex ?? 0
        let endLine = doc.metadata.totalChunks ?? 0

        // Extract symbol name from tags
        let symbolName = tags.first { tag in
            !CodeLanguage.allCases.map(\.rawValue).contains(tag) &&
            !CodeChunk.ChunkKind.allCases.contains(where: { $0.rawValue == tag }) &&
            tag != filePath
        }

        // Determine chunk kind from tags
        let kind: CodeChunk.ChunkKind = {
            if tags.contains("declaration") { return .declaration }
            if tags.contains("imports") { return .imports }
            if tags.contains("comment") { return .comment }
            return .body
        }()

        return CodeRAGResult(
            id: doc.id,
            filePath: filePath,
            content: doc.content,
            startLine: startLine,
            endLine: endLine,
            similarity: ragResult.similarity,
            symbolName: symbolName,
            chunkKind: kind,
            tags: tags
        )
    }

    /// Filter results by search scope
    private func filterByScope(_ results: [CodeRAGResult], scope: CodeSearchQuery.SearchScope) -> [CodeRAGResult] {
        switch scope {
        case .all:
            return results
        case .functions:
            return results.filter { $0.chunkKind == .declaration && isFunctionDeclaration($0.content) }
        case .types:
            return results.filter { $0.chunkKind == .declaration && isTypeDeclaration($0.content) }
        case .imports:
            return results.filter { $0.chunkKind == .imports }
        case .comments:
            return results.filter { $0.chunkKind == .comment }
        case .symbols:
            return results.filter { $0.symbolName != nil }
        }
    }

    private func isFunctionDeclaration(_ content: String) -> Bool {
        let patterns = ["func ", "def ", "function ", "fn "]
        return patterns.contains { content.contains($0) }
    }

    private func isTypeDeclaration(_ content: String) -> Bool {
        let patterns = ["class ", "struct ", "enum ", "protocol ", "interface ", "trait ", "type "]
        return patterns.contains { content.contains($0) }
    }

    /// Apply relevance boosting based on query analysis
    private func applyRelevanceBoost(_ results: [CodeRAGResult], query: String) -> [CodeRAGResult] {
        let queryLower = query.lowercased()

        return results.map { result in
            var boostedSimilarity = result.similarity

            // Boost if symbol name matches query words
            if let symbol = result.symbolName?.lowercased() {
                let queryWords = queryLower.split(separator: " ").map(String.init)
                for word in queryWords where word.count > 3 {
                    if symbol.contains(word) {
                        boostedSimilarity += 0.15
                    }
                }
            }

            // Boost declarations over body chunks for definition queries
            if queryLower.contains("function") || queryLower.contains("method") ||
               queryLower.contains("class") || queryLower.contains("implement") {
                if result.chunkKind == .declaration {
                    boostedSimilarity += 0.1
                }
            }

            // Boost for error/debugging queries on error-related code
            if queryLower.contains("error") || queryLower.contains("fix") || queryLower.contains("bug") {
                if result.content.lowercased().contains("error") ||
                   result.content.lowercased().contains("catch") ||
                   result.content.lowercased().contains("throw") {
                    boostedSimilarity += 0.1
                }
            }

            return CodeRAGResult(
                id: result.id,
                filePath: result.filePath,
                content: result.content,
                startLine: result.startLine,
                endLine: result.endLine,
                similarity: min(1.0, boostedSimilarity),
                symbolName: result.symbolName,
                chunkKind: result.chunkKind,
                tags: result.tags
            )
        }
    }

    // MARK: - Formatting

    /// Format a code snippet for context injection
    private func formatSnippet(_ result: CodeRAGResult) -> String {
        var parts: [String] = []

        // Header with file path and symbol
        var header = "**\(result.fileName)"
        if let symbol = result.symbolName {
            header += " > \(symbol)"
        }
        if result.startLine > 0 {
            header += ":\(result.startLine)"
        }
        header += "** (\(result.language.rawValue))"
        parts.append(header)

        // Code block
        parts.append("```\(result.language.rawValue)")
        parts.append(result.content)
        parts.append("```")

        return parts.joined(separator: "\n")
    }

    /// Estimate token count (~4 chars per token)
    private func estimateTokens(_ text: String) -> Int {
        (text.count + 3) / 4
    }

    /// Update search statistics
    private func updateStats(duration: TimeInterval) {
        searchCount += 1
        let durationMs = Float(duration * 1000)
        averageSearchTimeMs = ((averageSearchTimeMs * Float(searchCount - 1)) + durationMs) / Float(searchCount)
    }
}

// MARK: - CodeChunk.ChunkKind CaseIterable

extension CodeChunk.ChunkKind: CaseIterable {
    static var allCases: [CodeChunk.ChunkKind] {
        [.imports, .declaration, .comment, .body]
    }
}
