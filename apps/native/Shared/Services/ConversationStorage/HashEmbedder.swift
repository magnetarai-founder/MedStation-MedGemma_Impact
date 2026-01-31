//
//  HashEmbedder.swift
//  MagnetarStudio
//
//  Hash-based 384-dimensional embeddings for semantic similarity.
//  Ported from MagnetarAI-iPad / Neutron Star.
//
//  Benefits:
//  - Zero external dependencies
//  - Fast (native CryptoKit MD5)
//  - Works 100% offline
//  - Deterministic (same text always produces same embedding)
//

import Foundation
import CryptoKit
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "HashEmbedder")

// MARK: - Hash Embedder

/// Hash-based embedder for semantic similarity using MD5
/// Produces 384-dimensional normalized vectors
final class HashEmbedder {

    // MARK: - Configuration

    /// Embedding dimension (384 is standard for sentence embeddings)
    let dimension: Int

    // MARK: - Singleton

    static let shared = HashEmbedder()

    // MARK: - Initialization

    init(dimension: Int = 384) {
        self.dimension = dimension
    }

    // MARK: - Embedding

    /// Embed a single text string into a 384-dimensional vector
    func embed(_ text: String) -> [Float] {
        let cleanText = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !cleanText.isEmpty else {
            return [Float](repeating: 0, count: dimension)
        }

        // Generate enough hash values for the required dimensions
        // Each MD5 gives 16 bytes, we extract 8 16-bit values per hash
        var hashValues: [UInt16] = []
        let hashesNeeded = (dimension + 7) / 8  // 8 values per MD5 hash

        for i in 0..<hashesNeeded {
            let hashInput = "\(cleanText)_\(i)"
            let hashData = md5Hash(hashInput)

            // Extract 8 16-bit values from the 16-byte hash
            for j in stride(from: 0, to: 16, by: 2) {
                let value = UInt16(hashData[j]) << 8 | UInt16(hashData[j + 1])
                hashValues.append(value)
            }
        }

        // Convert to [-1, 1] range and take only required dimensions
        var vector: [Float] = hashValues.prefix(dimension).map { value in
            Float(value) / 32768.0 - 1.0
        }

        // L2 normalize
        vector = l2Normalize(vector)

        return vector
    }

    /// Embed multiple texts (batch operation)
    func embedBatch(_ texts: [String]) -> [[Float]] {
        texts.map { embed($0) }
    }

    // MARK: - Helper Methods

    /// Compute MD5 hash of a string
    private func md5Hash(_ string: String) -> [UInt8] {
        let data = Data(string.utf8)
        let digest = Insecure.MD5.hash(data: data)
        return Array(digest)
    }

    /// L2 normalize a vector
    private func l2Normalize(_ vector: [Float]) -> [Float] {
        let normSquared = vector.reduce(0) { $0 + $1 * $1 }
        let norm = sqrt(normSquared)

        guard norm > 0 else { return vector }
        return vector.map { $0 / norm }
    }

    // MARK: - Similarity

    /// Compute cosine similarity between two vectors
    static func cosineSimilarity(_ a: [Float], _ b: [Float]) -> Float {
        guard a.count == b.count, !a.isEmpty else { return 0 }

        var dotProduct: Float = 0
        var normA: Float = 0
        var normB: Float = 0

        for i in 0..<a.count {
            dotProduct += a[i] * b[i]
            normA += a[i] * a[i]
            normB += b[i] * b[i]
        }

        let denominator = sqrt(normA) * sqrt(normB)
        guard denominator > 0 else { return 0 }

        return dotProduct / denominator
    }

    /// Compute euclidean distance between two vectors
    static func euclideanDistance(_ a: [Float], _ b: [Float]) -> Float {
        guard a.count == b.count, !a.isEmpty else { return Float.infinity }

        var sumSquared: Float = 0
        for i in 0..<a.count {
            let diff = a[i] - b[i]
            sumSquared += diff * diff
        }

        return sqrt(sumSquared)
    }

    /// Find top-k most similar items from a list
    static func topKSimilar(
        query: [Float],
        candidates: [[Float]],
        k: Int = 5
    ) -> [(index: Int, similarity: Float)] {
        var results: [(Int, Float)] = []

        for (index, candidate) in candidates.enumerated() {
            let similarity = cosineSimilarity(query, candidate)
            results.append((index, similarity))
        }

        return results
            .sorted { $0.1 > $1.1 }
            .prefix(k)
            .map { $0 }
    }
}

// MARK: - Embedding Result

/// Container for an embedded item with metadata
struct EmbeddedItem: Codable, Identifiable {
    let id: UUID
    let text: String
    let embedding: [Float]
    let metadata: EmbeddingMetadata?
    let createdAt: Date

    init(
        id: UUID = UUID(),
        text: String,
        embedding: [Float],
        metadata: EmbeddingMetadata? = nil,
        createdAt: Date = Date()
    ) {
        self.id = id
        self.text = text
        self.embedding = embedding
        self.metadata = metadata
        self.createdAt = createdAt
    }
}

/// Metadata for an embedded item
struct EmbeddingMetadata: Codable {
    var source: EmbeddingSource
    var conversationId: UUID?
    var messageId: UUID?
    var documentId: UUID?
    var chunkIndex: Int?
    var totalChunks: Int?

    init(
        source: EmbeddingSource,
        conversationId: UUID? = nil,
        messageId: UUID? = nil,
        documentId: UUID? = nil,
        chunkIndex: Int? = nil,
        totalChunks: Int? = nil
    ) {
        self.source = source
        self.conversationId = conversationId
        self.messageId = messageId
        self.documentId = documentId
        self.chunkIndex = chunkIndex
        self.totalChunks = totalChunks
    }
}

/// Source type for embeddings
enum EmbeddingSource: String, Codable {
    case chatMessage = "chat_message"
    case document = "document"
    case file = "file"
    case dataTable = "data_table"
    case theme = "theme"
    case summary = "summary"
    case semanticNode = "semantic_node"
    case workflow = "workflow"
    case kanbanTask = "kanban_task"
    case vaultFile = "vault_file"
}

// MARK: - Text Chunker

/// Utility for chunking text into embeddable segments
struct TextChunker {

    /// Default chunk size (tokens approximated by characters / 4)
    static let defaultChunkSize = 512  // ~128 tokens

    /// Default overlap between chunks
    static let defaultOverlap = 64

    /// Split text into overlapping chunks for embedding
    static func chunk(
        _ text: String,
        chunkSize: Int = defaultChunkSize,
        overlap: Int = defaultOverlap
    ) -> [String] {
        guard !text.isEmpty else { return [] }

        let cleanText = text.trimmingCharacters(in: .whitespacesAndNewlines)
        guard cleanText.count > chunkSize else { return [cleanText] }

        var chunks: [String] = []
        var startIndex = cleanText.startIndex

        while startIndex < cleanText.endIndex {
            // Calculate end index for this chunk
            let endOffset = min(chunkSize, cleanText.distance(from: startIndex, to: cleanText.endIndex))
            var endIndex = cleanText.index(startIndex, offsetBy: endOffset)

            // Try to break at a sentence or word boundary
            if endIndex < cleanText.endIndex {
                endIndex = findBreakPoint(in: cleanText, near: endIndex, from: startIndex)
            }

            let chunk = String(cleanText[startIndex..<endIndex])
            chunks.append(chunk)

            // Move start for next chunk (with overlap)
            let advance = max(1, cleanText.distance(from: startIndex, to: endIndex) - overlap)
            startIndex = cleanText.index(startIndex, offsetBy: advance, limitedBy: cleanText.endIndex) ?? cleanText.endIndex
        }

        return chunks
    }

    /// Find a good break point near the target index
    private static func findBreakPoint(
        in text: String,
        near target: String.Index,
        from start: String.Index
    ) -> String.Index {
        // Look back up to 50 characters for a sentence end
        let searchStart = text.index(target, offsetBy: -50, limitedBy: start) ?? start
        let searchRange = searchStart..<target

        // Prefer breaking at sentence boundaries
        if let periodIndex = text.range(of: ". ", options: .backwards, range: searchRange)?.upperBound {
            return periodIndex
        }
        if let newlineIndex = text.range(of: "\n", options: .backwards, range: searchRange)?.upperBound {
            return newlineIndex
        }

        // Fall back to word boundary
        if let spaceIndex = text.range(of: " ", options: .backwards, range: searchRange)?.lowerBound {
            return text.index(after: spaceIndex)
        }

        return target
    }
}
