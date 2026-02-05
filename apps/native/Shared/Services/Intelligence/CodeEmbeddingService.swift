//
//  CodeEmbeddingService.swift
//  MagnetarStudio
//
//  Language-aware code embedding service for the Coding workspace.
//  Chunks source code by structural boundaries (functions, classes, imports)
//  and generates embeddings via HashEmbedder for RAG indexing.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "CodeEmbeddingService")

// MARK: - Code Language

/// Supported languages for structural chunking
enum CodeLanguage: String, Sendable, CaseIterable {
    case swift
    case python
    case typescript
    case javascript
    case rust
    case go
    case c
    case cpp
    case java
    case ruby
    case unknown

    /// File extensions for detection
    var extensions: [String] {
        switch self {
        case .swift: return ["swift"]
        case .python: return ["py"]
        case .typescript: return ["ts", "tsx"]
        case .javascript: return ["js", "jsx", "mjs"]
        case .rust: return ["rs"]
        case .go: return ["go"]
        case .c: return ["c", "h"]
        case .cpp: return ["cpp", "cc", "cxx", "hpp", "hh"]
        case .java: return ["java"]
        case .ruby: return ["rb"]
        case .unknown: return []
        }
    }

    /// Detect language from file extension
    static func detect(from path: String) -> CodeLanguage {
        let ext = (path as NSString).pathExtension.lowercased()
        return allCases.first { $0.extensions.contains(ext) } ?? .unknown
    }

    /// Regex patterns for structural boundaries (function/class/struct definitions)
    var structuralPatterns: [String] {
        switch self {
        case .swift:
            return [
                "^\\s*(public |private |internal |open |fileprivate )?(@\\w+\\s+)*(func |class |struct |enum |protocol |actor |extension )",
                "^\\s*// MARK: -"
            ]
        case .python:
            return [
                "^(class |def |async def )",
                "^# -+"
            ]
        case .typescript, .javascript:
            return [
                "^\\s*(export )?(async )?(function |class |const \\w+ = )",
                "^\\s*// -+"
            ]
        case .rust:
            return [
                "^\\s*(pub )?(fn |struct |enum |trait |impl |mod )",
                "^\\s*// -+"
            ]
        case .go:
            return [
                "^\\s*(func |type )",
                "^\\s*// -+"
            ]
        case .c, .cpp:
            return [
                "^\\s*(static )?(void |int |char |float |double |bool |auto |class |struct |enum )",
                "^\\s*// -+"
            ]
        case .java:
            return [
                "^\\s*(public |private |protected )?(static )?(class |interface |enum |void |\\w+ \\w+\\()",
                "^\\s*// -+"
            ]
        case .ruby:
            return [
                "^\\s*(def |class |module )",
                "^\\s*# -+"
            ]
        case .unknown:
            return []
        }
    }
}

// MARK: - Code Chunk

/// A structural chunk of source code with metadata
struct CodeChunk: Sendable, Identifiable {
    let id: UUID
    let filePath: String
    let language: CodeLanguage
    let content: String
    let startLine: Int
    let endLine: Int
    let kind: ChunkKind
    let symbolName: String?

    enum ChunkKind: String, Sendable {
        case imports       // Import/include block
        case declaration   // Function, class, struct, etc.
        case comment       // Documentation block
        case body          // General code body
    }

    init(
        id: UUID = UUID(),
        filePath: String,
        language: CodeLanguage,
        content: String,
        startLine: Int,
        endLine: Int,
        kind: ChunkKind = .body,
        symbolName: String? = nil
    ) {
        self.id = id
        self.filePath = filePath
        self.language = language
        self.content = content
        self.startLine = startLine
        self.endLine = endLine
        self.kind = kind
        self.symbolName = symbolName
    }
}

// MARK: - Indexed File Record

/// Tracks which files have been indexed and when
struct IndexedFileRecord: Codable, Sendable {
    let filePath: String
    let lastModified: Date
    let lastIndexed: Date
    let chunkCount: Int
    let language: String
    let documentIds: [UUID]
}

// MARK: - Code Embedding Service

/// Service that indexes source code files with language-aware chunking
/// and stores embeddings in VectorStore for semantic code search.
@MainActor
final class CodeEmbeddingService {
    // MARK: - Singleton

    static let shared = CodeEmbeddingService()

    // MARK: - Dependencies

    private let embedder = HashEmbedder.shared
    private let vectorStore = VectorStore.shared

    // MARK: - State

    /// Files currently indexed (path → record)
    private(set) var indexedFiles: [String: IndexedFileRecord] = [:]

    /// Whether indexing is in progress
    private(set) var isIndexing: Bool = false

    /// Number of documents indexed
    var totalDocumentsIndexed: Int {
        indexedFiles.values.reduce(0) { $0 + $1.chunkCount }
    }

    // MARK: - Configuration

    /// Maximum chunk size in characters
    let maxChunkSize: Int = 800

    /// Overlap between chunks
    let chunkOverlap: Int = 100

    /// File size limit for indexing (skip very large files)
    let maxFileSizeBytes: Int = 500_000  // 500KB

    /// File patterns to skip
    private let skipPatterns: [String] = [
        ".build/", "DerivedData/", "node_modules/", ".git/",
        "Pods/", "Carthage/", ".swiftpm/", "__pycache__/",
        "dist/", "build/", ".next/", "target/"
    ]

    // MARK: - Init

    private init() {
        loadIndexState()
    }

    // MARK: - Indexing

    /// Index all code files in a workspace directory
    func indexWorkspace(at path: String) async throws -> IndexingStats {
        guard !isIndexing else {
            logger.warning("[CodeEmbedding] Indexing already in progress")
            return IndexingStats()
        }

        isIndexing = true
        defer { isIndexing = false }

        let startTime = Date()
        var stats = IndexingStats()

        // Ensure vector store is ready
        await vectorStore.initialize()

        // Discover code files
        let files = discoverCodeFiles(in: path)
        stats.filesDiscovered = files.count

        logger.info("[CodeEmbedding] Discovered \(files.count) code files in \(path)")

        for file in files {
            do {
                let indexed = try await indexFileIfNeeded(file)
                if indexed {
                    stats.filesIndexed += 1
                }
                stats.filesProcessed += 1
            } catch {
                logger.error("[CodeEmbedding] Failed to index \(file): \(error)")
                stats.errors += 1
            }
        }

        stats.duration = Date().timeIntervalSince(startTime)
        stats.totalDocuments = totalDocumentsIndexed

        saveIndexState()

        logger.info("[CodeEmbedding] Indexing complete: \(stats.filesIndexed) files, \(stats.totalDocuments) chunks in \(String(format: "%.1f", stats.duration))s")

        return stats
    }

    /// Index a single file (force re-index)
    func indexFile(at path: String) async throws {
        await vectorStore.initialize()
        try await indexFileInternal(path)
        saveIndexState()
    }

    /// Remove a file from the index
    func removeFile(at path: String) async throws {
        guard let record = indexedFiles[path] else { return }

        for docId in record.documentIds {
            try await vectorStore.delete(id: docId)
        }

        indexedFiles.removeValue(forKey: path)
        saveIndexState()

        logger.debug("[CodeEmbedding] Removed \(path) from index")
    }

    /// Clear the entire code index
    func clearIndex() async throws {
        for (_, record) in indexedFiles {
            for docId in record.documentIds {
                try await vectorStore.delete(id: docId)
            }
        }

        indexedFiles.removeAll()
        saveIndexState()

        logger.info("[CodeEmbedding] Index cleared")
    }

    // MARK: - File Discovery

    private func discoverCodeFiles(in directory: String) -> [String] {
        let fileManager = FileManager.default
        var codeFiles: [String] = []

        let allExtensions = CodeLanguage.allCases.flatMap { $0.extensions }

        guard let enumerator = fileManager.enumerator(
            at: URL(fileURLWithPath: directory),
            includingPropertiesForKeys: [.fileSizeKey, .contentModificationDateKey],
            options: [.skipsHiddenFiles]
        ) else {
            return []
        }

        while let url = enumerator.nextObject() as? URL {
            let path = url.path

            // Skip excluded directories
            if skipPatterns.contains(where: { path.contains($0) }) {
                continue
            }

            // Check file extension
            let ext = url.pathExtension.lowercased()
            guard allExtensions.contains(ext) else { continue }

            // Check file size
            if let size = try? url.resourceValues(forKeys: [.fileSizeKey]).fileSize,
               size > maxFileSizeBytes {
                continue
            }

            codeFiles.append(path)
        }

        return codeFiles
    }

    // MARK: - Incremental Indexing

    private func indexFileIfNeeded(_ path: String) async throws -> Bool {
        let attrs = try FileManager.default.attributesOfItem(atPath: path)
        let modified = attrs[.modificationDate] as? Date ?? Date.distantPast

        // Check if already indexed and up to date
        if let existing = indexedFiles[path], existing.lastModified >= modified {
            return false
        }

        // Remove old index entries if re-indexing
        if let existing = indexedFiles[path] {
            for docId in existing.documentIds {
                try await vectorStore.delete(id: docId)
            }
        }

        try await indexFileInternal(path)
        return true
    }

    private func indexFileInternal(_ path: String) async throws {
        let content = try String(contentsOfFile: path, encoding: .utf8)
        let language = CodeLanguage.detect(from: path)

        // Chunk the file
        let chunks = chunkCode(content: content, filePath: path, language: language)

        guard !chunks.isEmpty else { return }

        // Generate embeddings and create RAG documents
        var documentIds: [UUID] = []

        for (index, chunk) in chunks.enumerated() {
            // Build embedding text: include file path and symbol name for context
            let embeddingText = buildEmbeddingText(chunk: chunk)
            let embedding = embedder.embed(embeddingText)

            let document = RAGDocument(
                content: chunk.content,
                embedding: embedding,
                source: .codeFile,
                metadata: RAGDocumentMetadata(
                    fileId: chunk.id,
                    title: (path as NSString).lastPathComponent,
                    contentType: language.rawValue,
                    chunkIndex: index,
                    totalChunks: chunks.count,
                    tags: buildTags(chunk: chunk)
                )
            )

            try await vectorStore.insert(document)
            documentIds.append(document.id)
        }

        // Record indexed file
        let attrs = try FileManager.default.attributesOfItem(atPath: path)
        let modified = attrs[.modificationDate] as? Date ?? Date()

        indexedFiles[path] = IndexedFileRecord(
            filePath: path,
            lastModified: modified,
            lastIndexed: Date(),
            chunkCount: chunks.count,
            language: language.rawValue,
            documentIds: documentIds
        )

        logger.debug("[CodeEmbedding] Indexed \(path): \(chunks.count) chunks")
    }

    // MARK: - Language-Aware Chunking

    /// Chunk source code by structural boundaries
    func chunkCode(content: String, filePath: String, language: CodeLanguage) -> [CodeChunk] {
        let lines = content.components(separatedBy: "\n")
        guard !lines.isEmpty else { return [] }

        // If language is unknown or file is small, use simple chunking
        if language == .unknown || content.count <= maxChunkSize {
            return [CodeChunk(
                filePath: filePath,
                language: language,
                content: content,
                startLine: 1,
                endLine: lines.count,
                kind: .body
            )]
        }

        // Build structural boundary regex patterns
        let patterns = language.structuralPatterns.compactMap { pattern in
            try? NSRegularExpression(pattern: pattern, options: [.anchorsMatchLines])
        }

        // Find structural boundaries
        var boundaries: [(line: Int, name: String?)] = [(line: 0, name: nil)]

        for (lineIndex, line) in lines.enumerated() {
            let nsLine = line as NSString
            let range = NSRange(location: 0, length: nsLine.length)

            for pattern in patterns {
                if pattern.firstMatch(in: line, options: [], range: range) != nil {
                    let symbolName = extractSymbolName(from: line, language: language)
                    boundaries.append((line: lineIndex, name: symbolName))
                    break
                }
            }
        }

        // Create chunks from boundaries
        var chunks: [CodeChunk] = []

        for i in 0..<boundaries.count {
            let start = boundaries[i].line
            let end = (i + 1 < boundaries.count) ? boundaries[i + 1].line : lines.count
            let chunkLines = Array(lines[start..<end])
            let chunkContent = chunkLines.joined(separator: "\n").trimmingCharacters(in: .whitespacesAndNewlines)

            guard !chunkContent.isEmpty else { continue }

            // If chunk is too large, split it further
            if chunkContent.count > maxChunkSize {
                let subChunks = splitLargeChunk(
                    content: chunkContent,
                    filePath: filePath,
                    language: language,
                    startLine: start + 1,
                    symbolName: boundaries[i].name
                )
                chunks.append(contentsOf: subChunks)
            } else {
                let kind = classifyChunk(chunkContent, language: language)
                chunks.append(CodeChunk(
                    filePath: filePath,
                    language: language,
                    content: chunkContent,
                    startLine: start + 1,
                    endLine: end,
                    kind: kind,
                    symbolName: boundaries[i].name
                ))
            }
        }

        return chunks
    }

    /// Split a large chunk into smaller pieces with overlap
    private func splitLargeChunk(
        content: String,
        filePath: String,
        language: CodeLanguage,
        startLine: Int,
        symbolName: String?
    ) -> [CodeChunk] {
        let lines = content.components(separatedBy: "\n")
        var chunks: [CodeChunk] = []
        var currentStart = 0

        while currentStart < lines.count {
            let end = min(currentStart + (maxChunkSize / 40), lines.count)  // ~40 chars per line average
            let chunkLines = Array(lines[currentStart..<end])
            let chunkContent = chunkLines.joined(separator: "\n")

            if !chunkContent.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty {
                chunks.append(CodeChunk(
                    filePath: filePath,
                    language: language,
                    content: chunkContent,
                    startLine: startLine + currentStart,
                    endLine: startLine + end - 1,
                    kind: .body,
                    symbolName: symbolName
                ))
            }

            // Advance with overlap
            let overlapLines = max(2, chunkOverlap / 40)
            currentStart = end - overlapLines
            if currentStart <= (chunks.last.map { _ in end - overlapLines - 1 } ?? -1) {
                currentStart = end  // Prevent infinite loop
            }
        }

        return chunks
    }

    // MARK: - Symbol Extraction

    /// Extract the symbol name (function/class/struct name) from a declaration line
    private func extractSymbolName(from line: String, language: CodeLanguage) -> String? {
        let trimmed = line.trimmingCharacters(in: .whitespaces)

        switch language {
        case .swift:
            // Match: func name(, class Name, struct Name, enum Name, etc.
            let patterns = [
                "(?:func|class|struct|enum|protocol|actor|extension)\\s+(\\w+)",
                "// MARK: - (.+)"
            ]
            return firstMatch(in: trimmed, patterns: patterns)

        case .python:
            let patterns = [
                "(?:def|class|async def)\\s+(\\w+)",
                "# (.+)"
            ]
            return firstMatch(in: trimmed, patterns: patterns)

        case .typescript, .javascript:
            let patterns = [
                "(?:function|class)\\s+(\\w+)",
                "(?:const|let|var)\\s+(\\w+)\\s*="
            ]
            return firstMatch(in: trimmed, patterns: patterns)

        case .rust:
            let patterns = [
                "(?:fn|struct|enum|trait|impl|mod)\\s+(\\w+)"
            ]
            return firstMatch(in: trimmed, patterns: patterns)

        case .go:
            let patterns = [
                "(?:func|type)\\s+(?:\\([^)]+\\)\\s+)?(\\w+)"
            ]
            return firstMatch(in: trimmed, patterns: patterns)

        case .java:
            let patterns = [
                "(?:class|interface|enum)\\s+(\\w+)",
                "(?:void|\\w+)\\s+(\\w+)\\s*\\("
            ]
            return firstMatch(in: trimmed, patterns: patterns)

        case .c, .cpp:
            let patterns = [
                "(?:class|struct|enum)\\s+(\\w+)",
                "\\w+\\s+(\\w+)\\s*\\("
            ]
            return firstMatch(in: trimmed, patterns: patterns)

        case .ruby:
            let patterns = [
                "(?:def|class|module)\\s+(\\w+)"
            ]
            return firstMatch(in: trimmed, patterns: patterns)

        case .unknown:
            return nil
        }
    }

    private func firstMatch(in text: String, patterns: [String]) -> String? {
        for pattern in patterns {
            guard let regex = try? NSRegularExpression(pattern: pattern, options: []) else { continue }
            let range = NSRange(text.startIndex..., in: text)
            if let match = regex.firstMatch(in: text, options: [], range: range),
               match.numberOfRanges > 1,
               let captureRange = Range(match.range(at: 1), in: text) {
                return String(text[captureRange])
            }
        }
        return nil
    }

    // MARK: - Chunk Classification

    private func classifyChunk(_ content: String, language: CodeLanguage) -> CodeChunk.ChunkKind {
        let trimmed = content.trimmingCharacters(in: .whitespacesAndNewlines)

        // Check for import block
        switch language {
        case .swift:
            if trimmed.hasPrefix("import ") { return .imports }
        case .python:
            if trimmed.hasPrefix("import ") || trimmed.hasPrefix("from ") { return .imports }
        case .typescript, .javascript:
            if trimmed.hasPrefix("import ") || trimmed.hasPrefix("require(") { return .imports }
        case .rust:
            if trimmed.hasPrefix("use ") || trimmed.hasPrefix("extern crate ") { return .imports }
        case .go:
            if trimmed.hasPrefix("import ") { return .imports }
        case .java:
            if trimmed.hasPrefix("import ") || trimmed.hasPrefix("package ") { return .imports }
        default:
            break
        }

        // Check for documentation comment
        if trimmed.hasPrefix("///") || trimmed.hasPrefix("/**") ||
           trimmed.hasPrefix("\"\"\"") || trimmed.hasPrefix("# ") {
            return .comment
        }

        // Check for declaration
        let declarationKeywords = ["func ", "def ", "class ", "struct ", "enum ", "trait ",
                                    "impl ", "fn ", "type ", "interface ", "protocol "]
        if declarationKeywords.contains(where: { trimmed.contains($0) }) {
            return .declaration
        }

        return .body
    }

    // MARK: - Embedding Text Construction

    /// Build text for embedding that includes structural context
    private func buildEmbeddingText(chunk: CodeChunk) -> String {
        var parts: [String] = []

        // Include file name for context
        let fileName = (chunk.filePath as NSString).lastPathComponent
        parts.append("File: \(fileName)")

        // Include symbol name if available
        if let symbol = chunk.symbolName {
            parts.append("Symbol: \(symbol)")
        }

        // Include language
        parts.append("Language: \(chunk.language.rawValue)")

        // Include the actual code
        parts.append(chunk.content)

        return parts.joined(separator: "\n")
    }

    /// Build searchable tags from a chunk
    private func buildTags(chunk: CodeChunk) -> [String] {
        var tags: [String] = [
            chunk.language.rawValue,
            chunk.kind.rawValue,
            (chunk.filePath as NSString).lastPathComponent
        ]

        if let symbol = chunk.symbolName {
            tags.append(symbol)
        }

        return tags
    }

    // MARK: - Persistence

    private var indexStatePath: URL {
        let dir = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("MagnetarStudio")
            .appendingPathComponent("code_index")
        do {
            try FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        } catch {
            logger.warning("[CodeEmbedding] Failed to create index directory: \(error)")
        }
        return dir.appendingPathComponent("index_state.json")
    }

    private func saveIndexState() {
        do {
            let data = try JSONEncoder().encode(Array(indexedFiles.values))
            try data.write(to: indexStatePath)
        } catch {
            logger.error("[CodeEmbedding] Failed to save index state: \(error)")
        }
    }

    private func loadIndexState() {
        guard let data = try? Data(contentsOf: indexStatePath),
              let records = try? JSONDecoder().decode([IndexedFileRecord].self, from: data) else {
            return
        }

        indexedFiles = Dictionary(uniqueKeysWithValues: records.map { ($0.filePath, $0) })
        logger.debug("[CodeEmbedding] Loaded index state: \(self.indexedFiles.count) files")
    }
}

// MARK: - Indexing Statistics

struct IndexingStats: Sendable {
    var filesDiscovered: Int = 0
    var filesProcessed: Int = 0
    var filesIndexed: Int = 0
    var totalDocuments: Int = 0
    var errors: Int = 0
    var duration: TimeInterval = 0
}
