//
//  FileRelevanceScorer.swift
//  MagnetarStudio
//
//  Scores file relevance for context inclusion decisions.
//  Combines semantic similarity, usage patterns, and ANE predictions.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "FileRelevanceScorer")

// MARK: - File Relevance Scorer

@MainActor
final class FileRelevanceScorer: ObservableObject {

    // MARK: - Configuration

    struct ScoringWeights {
        var semanticSimilarity: Float = 0.35
        var recency: Float = 0.20
        var frequency: Float = 0.15
        var coAccess: Float = 0.10
        var anePrediction: Float = 0.10
        var typeMatch: Float = 0.05
        var contextualBonus: Float = 0.05

        static let `default` = ScoringWeights()

        static let semanticFocused = ScoringWeights(
            semanticSimilarity: 0.50,
            recency: 0.15,
            frequency: 0.10,
            coAccess: 0.10,
            anePrediction: 0.10,
            typeMatch: 0.025,
            contextualBonus: 0.025
        )

        static let patternFocused = ScoringWeights(
            semanticSimilarity: 0.25,
            recency: 0.25,
            frequency: 0.20,
            coAccess: 0.15,
            anePrediction: 0.10,
            typeMatch: 0.025,
            contextualBonus: 0.025
        )
    }

    // MARK: - Dependencies

    private let embedder: HashEmbedder
    private let predictor: ANEPredictor
    private let fileIndex: CrossConversationFileIndex

    // MARK: - State

    @Published private(set) var lastScoringDuration: TimeInterval = 0
    @Published var weights: ScoringWeights = .default

    // MARK: - Singleton

    static let shared = FileRelevanceScorer()

    // MARK: - Initialization

    init(
        embedder: HashEmbedder? = nil,
        predictor: ANEPredictor? = nil,
        fileIndex: CrossConversationFileIndex? = nil
    ) {
        self.embedder = embedder ?? .shared
        self.predictor = predictor ?? .shared
        self.fileIndex = fileIndex ?? .shared
    }

    // MARK: - Scoring

    /// Score a file's relevance to a query and context
    func scoreFile(
        _ file: FileReference,
        query: String,
        context: ScoringContext
    ) async -> FileRelevanceScore {
        let startTime = Date()

        // 1. Semantic similarity
        let semanticScore = calculateSemanticScore(file, query: query)

        // 2. Recency score
        let recencyScore = calculateRecencyScore(file.lastAccessed)

        // 3. Frequency score (from cross-conversation data)
        let frequencyScore = await calculateFrequencyScore(file.id)

        // 4. Co-access score
        let coAccessScore = await calculateCoAccessScore(file.id, context: context)

        // 5. ANE prediction score
        let aneScore = calculateANEScore(file, context: context)

        // 6. Type match score
        let typeScore = calculateTypeMatchScore(file.fileType, context: context)

        // 7. Contextual bonuses
        let contextualScore = calculateContextualScore(file, context: context)

        // Calculate weighted total
        let total = (semanticScore * weights.semanticSimilarity) +
                    (recencyScore * weights.recency) +
                    (frequencyScore * weights.frequency) +
                    (coAccessScore * weights.coAccess) +
                    (aneScore * weights.anePrediction) +
                    (typeScore * weights.typeMatch) +
                    (contextualScore * weights.contextualBonus)

        lastScoringDuration = Date().timeIntervalSince(startTime)

        return FileRelevanceScore(
            fileId: file.id,
            filename: file.filename,
            totalScore: min(1.0, total),
            semanticScore: semanticScore,
            recencyScore: recencyScore,
            frequencyScore: frequencyScore,
            coAccessScore: coAccessScore,
            aneScore: aneScore,
            typeMatchScore: typeScore,
            contextualScore: contextualScore,
            explanation: buildExplanation(
                semantic: semanticScore,
                recency: recencyScore,
                frequency: frequencyScore,
                coAccess: coAccessScore,
                ane: aneScore,
                typeMatch: typeScore,
                contextual: contextualScore
            )
        )
    }

    /// Score multiple files and return sorted results
    func scoreFiles(
        _ files: [FileReference],
        query: String,
        context: ScoringContext,
        minScore: Float = 0.2
    ) async -> [FileRelevanceScore] {
        var scores: [FileRelevanceScore] = []

        for file in files {
            let score = await scoreFile(file, query: query, context: context)
            if score.totalScore >= minScore {
                scores.append(score)
            }
        }

        return scores.sorted { $0.totalScore > $1.totalScore }
    }

    /// Quick relevance check without full scoring
    func isLikelyRelevant(
        _ file: FileReference,
        query: String,
        threshold: Float = 0.3
    ) -> Bool {
        // Quick semantic check
        let queryEmbedding = embedder.embed(query)
        let fileEmbedding: [Float]

        if let existing = file.embedding {
            fileEmbedding = existing
        } else {
            fileEmbedding = embedder.embed(file.processedContent ?? file.filename)
        }

        let similarity = HashEmbedder.cosineSimilarity(queryEmbedding, fileEmbedding)
        return similarity >= threshold
    }

    // MARK: - Score Components

    private func calculateSemanticScore(_ file: FileReference, query: String) -> Float {
        let queryEmbedding = embedder.embed(query)
        let fileEmbedding: [Float]

        if let existing = file.embedding {
            fileEmbedding = existing
        } else {
            let textToEmbed = file.processedContent ?? file.filename
            fileEmbedding = embedder.embed(textToEmbed)
        }

        return HashEmbedder.cosineSimilarity(queryEmbedding, fileEmbedding)
    }

    private func calculateRecencyScore(_ lastAccessed: Date) -> Float {
        let hoursSince = Date().timeIntervalSince(lastAccessed) / 3600

        // Exponential decay with half-life of 24 hours
        let decayRate: Float = 0.693 / 24  // ln(2) / half-life
        return exp(-decayRate * Float(hoursSince))
    }

    private func calculateFrequencyScore(_ fileId: UUID) async -> Float {
        // Get access count from cross-conversation index
        let results = await fileIndex.findRelevantFiles(query: "", limit: 1000)

        guard let fileResult = results.first(where: { $0.fileId == fileId }) else {
            return 0
        }

        // Normalize access count (log scale)
        let accessCount = Float(fileResult.totalAccessCount)
        return min(1.0, log(1 + accessCount) / log(20))  // Saturates at ~20 accesses
    }

    private func calculateCoAccessScore(_ fileId: UUID, context: ScoringContext) async -> Float {
        // If we have active files in context, check co-access patterns
        guard !context.activeFileIds.isEmpty else { return 0 }

        let coAccessedFiles = await fileIndex.getCoAccessedFiles(with: fileId, limit: 20)

        // Check if any actively used files are frequently co-accessed with this file
        var maxCoAccessScore: Float = 0

        for activeId in context.activeFileIds {
            if let coAccess = coAccessedFiles.first(where: { $0.fileId == activeId }) {
                maxCoAccessScore = max(maxCoAccessScore, coAccess.coAccessScore)
            }
        }

        return maxCoAccessScore
    }

    private func calculateANEScore(_ file: FileReference, context: ScoringContext) -> Float {
        let prediction = predictor.predictContextNeeds(
            currentWorkspace: context.currentWorkspace,
            recentQuery: context.recentQuery,
            activeFileId: context.activeFileIds.first
        )

        var score: Float = 0

        // Check if file matches predicted topics
        let fileText = (file.processedContent ?? file.filename).lowercased()

        for topic in prediction.likelyTopics {
            if fileText.contains(topic.lowercased()) {
                score += 0.2
            }
        }

        // Check if file type matches predicted needs
        if prediction.compressionAggressiveness < 0.5 {
            // Low compression = more context needed, boost file relevance
            score += 0.1
        }

        return min(1.0, score)
    }

    private func calculateTypeMatchScore(_ fileType: String, context: ScoringContext) -> Float {
        guard !context.preferredFileTypes.isEmpty else { return 0.5 }

        let normalizedType = fileType.lowercased()

        // Exact match
        if context.preferredFileTypes.contains(normalizedType) {
            return 1.0
        }

        // Partial match (e.g., "swift" matches "text/x-swift")
        for preferred in context.preferredFileTypes {
            if normalizedType.contains(preferred) || preferred.contains(normalizedType) {
                return 0.7
            }
        }

        // Code files when looking for code
        let codeTypes = ["swift", "python", "javascript", "typescript", "java", "go", "rust", "c", "cpp"]
        if context.preferredFileTypes.contains("code") && codeTypes.contains(where: { normalizedType.contains($0) }) {
            return 0.8
        }

        // Document files when looking for docs
        let docTypes = ["md", "markdown", "txt", "doc", "pdf"]
        if context.preferredFileTypes.contains("document") && docTypes.contains(where: { normalizedType.contains($0) }) {
            return 0.8
        }

        return 0.2
    }

    private func calculateContextualScore(_ file: FileReference, context: ScoringContext) -> Float {
        var score: Float = 0

        // Boost if file is from the same conversation
        if let currentConversation = context.currentConversationId,
           file.conversationIds.contains(currentConversation) {
            score += 0.3
        }

        // Boost if file is vault-protected and we're in a security-sensitive context
        if file.isVaultProtected && context.isSecuritySensitive {
            score += 0.2
        }

        // Boost if filename matches context keywords
        let filenameWords = Set(file.filename.lowercased().components(separatedBy: CharacterSet.alphanumerics.inverted))
        let contextKeywords = Set(context.keywords.map { $0.lowercased() })
        let overlap = filenameWords.intersection(contextKeywords)

        if !overlap.isEmpty {
            score += Float(overlap.count) * 0.1
        }

        return min(1.0, score)
    }

    // MARK: - Explanation

    private func buildExplanation(
        semantic: Float,
        recency: Float,
        frequency: Float,
        coAccess: Float,
        ane: Float,
        typeMatch: Float,
        contextual: Float
    ) -> String {
        var reasons: [String] = []

        if semantic >= 0.6 {
            reasons.append("highly relevant to query")
        } else if semantic >= 0.4 {
            reasons.append("somewhat relevant to query")
        }

        if recency >= 0.7 {
            reasons.append("recently accessed")
        }

        if frequency >= 0.5 {
            reasons.append("frequently used")
        }

        if coAccess >= 0.5 {
            reasons.append("often used with active files")
        }

        if ane >= 0.3 {
            reasons.append("predicted to be useful")
        }

        if typeMatch >= 0.8 {
            reasons.append("matches preferred file type")
        }

        if contextual >= 0.3 {
            reasons.append("contextually relevant")
        }

        if reasons.isEmpty {
            return "Low overall relevance"
        }

        return reasons.joined(separator: "; ")
    }
}

// MARK: - Supporting Types

/// Context for scoring decisions
struct ScoringContext {
    var currentWorkspace: WorkspaceType = .chat
    var currentConversationId: UUID?
    var activeFileIds: [UUID] = []
    var recentQuery: String?
    var preferredFileTypes: [String] = []
    var keywords: [String] = []
    var isSecuritySensitive: Bool = false

    static func forChat(conversationId: UUID?, query: String?) -> ScoringContext {
        return ScoringContext(
            currentWorkspace: .chat,
            currentConversationId: conversationId,
            recentQuery: query
        )
    }

    static func forCode(activeFiles: [UUID], query: String?) -> ScoringContext {
        return ScoringContext(
            currentWorkspace: .code,
            activeFileIds: activeFiles,
            recentQuery: query,
            preferredFileTypes: ["swift", "python", "javascript", "typescript", "code"]
        )
    }

    static func forVault(query: String?) -> ScoringContext {
        return ScoringContext(
            currentWorkspace: .vault,
            recentQuery: query,
            isSecuritySensitive: true
        )
    }
}

/// Detailed relevance score with component breakdown
struct FileRelevanceScore: Identifiable {
    var id: UUID { fileId }

    let fileId: UUID
    let filename: String
    let totalScore: Float
    let semanticScore: Float
    let recencyScore: Float
    let frequencyScore: Float
    let coAccessScore: Float
    let aneScore: Float
    let typeMatchScore: Float
    let contextualScore: Float
    let explanation: String

    /// Quick relevance tier
    var tier: RelevanceTier {
        switch totalScore {
        case 0.8...: return .high
        case 0.5..<0.8: return .medium
        case 0.3..<0.5: return .low
        default: return .minimal
        }
    }

    /// Human-readable summary
    var summary: String {
        return "\(filename): \(String(format: "%.0f", totalScore * 100))% - \(explanation)"
    }
}

/// Relevance tiers for UI display
enum RelevanceTier: String, CaseIterable {
    case high = "High"
    case medium = "Medium"
    case low = "Low"
    case minimal = "Minimal"

    var color: String {
        switch self {
        case .high: return "green"
        case .medium: return "yellow"
        case .low: return "orange"
        case .minimal: return "gray"
        }
    }

    var icon: String {
        switch self {
        case .high: return "star.fill"
        case .medium: return "star.leadinghalf.filled"
        case .low: return "star"
        case .minimal: return "star.slash"
        }
    }
}

// MARK: - Batch Scoring

extension FileRelevanceScorer {

    /// Score files in batches for better performance
    func scoreBatch(
        _ files: [FileReference],
        query: String,
        context: ScoringContext,
        batchSize: Int = 20
    ) async -> [FileRelevanceScore] {
        var allScores: [FileRelevanceScore] = []

        // Pre-compute query embedding once
        let queryEmbedding = embedder.embed(query)

        // Process in batches
        for batchStart in stride(from: 0, to: files.count, by: batchSize) {
            let batchEnd = min(batchStart + batchSize, files.count)
            let batch = Array(files[batchStart..<batchEnd])

            // Score batch concurrently using pre-computed embedding
            for file in batch {
                let score = await scoreFile(file, query: query, context: context)
                allScores.append(score)
            }
        }

        return allScores.sorted { $0.totalScore > $1.totalScore }
    }

    /// Get top N relevant files quickly
    func topRelevantFiles(
        from files: [FileReference],
        query: String,
        context: ScoringContext,
        count: Int = 5
    ) async -> [FileRelevanceScore] {
        // Quick filter first
        let likelyRelevant = files.filter { isLikelyRelevant($0, query: query, threshold: 0.2) }

        // Full scoring on filtered set
        let scores = await scoreFiles(likelyRelevant, query: query, context: context)

        return Array(scores.prefix(count))
    }
}

// MARK: - Score Aggregation

struct FileRelevanceReport {
    let query: String
    let scoredFiles: [FileRelevanceScore]
    let generatedAt: Date

    var highRelevanceCount: Int {
        scoredFiles.filter { $0.tier == .high }.count
    }

    var mediumRelevanceCount: Int {
        scoredFiles.filter { $0.tier == .medium }.count
    }

    var topFiles: [FileRelevanceScore] {
        Array(scoredFiles.prefix(5))
    }

    var averageScore: Float {
        guard !scoredFiles.isEmpty else { return 0 }
        return scoredFiles.reduce(0) { $0 + $1.totalScore } / Float(scoredFiles.count)
    }

    func formatted() -> String {
        var output = "File Relevance Report for: \"\(query)\"\n"
        output += "Generated: \(generatedAt)\n\n"
        output += "Summary: \(highRelevanceCount) high, \(mediumRelevanceCount) medium relevance\n\n"
        output += "Top Files:\n"

        for (index, score) in topFiles.enumerated() {
            output += "\(index + 1). \(score.summary)\n"
        }

        return output
    }
}
