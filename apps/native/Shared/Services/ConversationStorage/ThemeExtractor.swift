//
//  ThemeExtractor.swift
//  MagnetarStudio
//
//  Extracts semantic themes from conversation messages.
//  Ported from MagnetarAI-iPad with MagnetarStudio enhancements.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "ThemeExtractor")

// MARK: - Theme Extractor

@MainActor
final class ThemeExtractor {

    // MARK: - Dependencies

    private let embedder: HashEmbedder
    private let graphBuilder: SessionGraphBuilder

    // MARK: - Configuration

    /// Minimum messages to form a theme
    let minMessagesForTheme = 3

    /// Maximum messages per theme
    let maxMessagesPerTheme = 10

    /// Similarity threshold for clustering
    let similarityThreshold: Float = 0.5

    // MARK: - Singleton

    static let shared = ThemeExtractor()

    // MARK: - Initialization

    init(
        embedder: HashEmbedder? = nil,
        graphBuilder: SessionGraphBuilder? = nil
    ) {
        self.embedder = embedder ?? .shared
        self.graphBuilder = graphBuilder ?? .shared
    }

    // MARK: - Extraction

    /// Extract themes from a set of messages
    func extractThemes(
        from messages: [ChatMessage],
        conversationId: UUID
    ) async throws -> [ConversationTheme] {
        guard messages.count >= minMessagesForTheme else { return [] }

        // Group messages by similarity
        let clusters = clusterMessages(messages)

        var themes: [ConversationTheme] = []

        for cluster in clusters where cluster.count >= minMessagesForTheme {
            // Generate theme from cluster
            let theme = generateTheme(from: cluster, conversationId: conversationId)
            themes.append(theme)

            // Update session graph with entities from this theme
            for entity in theme.entities {
                graphBuilder.addEntity(name: entity, type: .concept)
            }
        }

        logger.info("[ThemeExtractor] Extracted \(themes.count) themes from \(messages.count) messages")
        return themes
    }

    /// Cluster messages by semantic similarity
    private func clusterMessages(_ messages: [ChatMessage]) -> [[ChatMessage]] {
        guard !messages.isEmpty else { return [] }

        // Embed all messages
        let embeddings = messages.map { embedder.embed($0.content) }

        // Simple clustering: group consecutive similar messages
        var clusters: [[ChatMessage]] = []
        var currentCluster: [ChatMessage] = [messages[0]]

        for i in 1..<messages.count {
            let similarity = HashEmbedder.cosineSimilarity(embeddings[i], embeddings[i - 1])

            if similarity > similarityThreshold && currentCluster.count < maxMessagesPerTheme {
                // Similar to previous - add to current cluster
                currentCluster.append(messages[i])
            } else {
                // Start new cluster
                if currentCluster.count >= minMessagesForTheme {
                    clusters.append(currentCluster)
                }
                currentCluster = [messages[i]]
            }
        }

        // Add final cluster
        if currentCluster.count >= minMessagesForTheme {
            clusters.append(currentCluster)
        }

        return clusters
    }

    /// Generate a theme from a cluster of messages
    private func generateTheme(
        from messages: [ChatMessage],
        conversationId: UUID
    ) -> ConversationTheme {
        // Combine message content
        let combinedContent = messages.map { $0.content }.joined(separator: "\n\n")

        // Extract entities
        let entities = extractEntities(from: combinedContent)

        // Extract key points (first sentence of each message)
        let keyPoints = messages.prefix(5).compactMap { message -> String? in
            let firstSentence = message.content.components(separatedBy: ".").first
            return firstSentence?.trimmingCharacters(in: .whitespacesAndNewlines)
        }

        // Generate topic
        let topic = generateTopic(from: messages)

        // Create embedding for the combined content
        let embedding = embedder.embed(combinedContent)

        // Create summary content
        let summaryContent = createSummary(messages: messages, entities: entities)

        return ConversationTheme(
            topic: topic,
            content: summaryContent,
            entities: entities,
            keyPoints: keyPoints,
            embedding: embedding,
            messageIds: messages.map { $0.id },
            relevanceScore: 1.0
        )
    }

    /// Extract named entities from text
    private func extractEntities(from text: String) -> [String] {
        // Simple heuristic: find capitalized words that appear multiple times
        let words = text.components(separatedBy: .whitespacesAndNewlines)
        var wordCounts: [String: Int] = [:]

        for word in words {
            let cleaned = word.trimmingCharacters(in: .punctuationCharacters)
            guard cleaned.count > 2, cleaned.first?.isUppercase == true else { continue }
            wordCounts[cleaned, default: 0] += 1
        }

        // Return words that appear multiple times
        return wordCounts
            .filter { $0.value >= 2 }
            .sorted { $0.value > $1.value }
            .prefix(10)
            .map { $0.key }
    }

    /// Generate a topic title from messages
    private func generateTopic(from messages: [ChatMessage]) -> String {
        guard let firstMessage = messages.first else { return "Unknown Topic" }

        // Take first meaningful words
        let words = firstMessage.content.components(separatedBy: .whitespacesAndNewlines)
        let topic = words.prefix(5).joined(separator: " ")

        if topic.count > 50 {
            return String(topic.prefix(47)) + "..."
        }
        return topic
    }

    /// Create a summary from messages
    private func createSummary(messages: [ChatMessage], entities: [String]) -> String {
        var parts: [String] = []

        // Add message count
        parts.append("Discussion with \(messages.count) exchanges.")

        // Add entities
        if !entities.isEmpty {
            parts.append("Key topics: \(entities.prefix(5).joined(separator: ", ")).")
        }

        // Add brief content summary (first and last user messages)
        let userMessages = messages.filter { $0.role == .user }
        if let first = userMessages.first {
            let preview = String(first.content.prefix(100))
            parts.append("Started with: \"\(preview)...\"")
        }
        if userMessages.count > 1, let last = userMessages.last {
            let preview = String(last.content.prefix(100))
            parts.append("Ended with: \"\(preview)...\"")
        }

        return parts.joined(separator: " ")
    }

    // MARK: - Semantic Node Generation

    /// Convert a theme to a semantic node
    func themeToSemanticNode(_ theme: ConversationTheme) -> SemanticNode {
        return SemanticNode(
            concept: theme.topic,
            content: theme.content,
            embedding: theme.embedding,
            entities: theme.entities,
            originalMessageCount: theme.messageIds.count,
            relevanceScore: theme.relevanceScore,
            sourceMessageIds: theme.messageIds,
            tier: .themes
        )
    }

    // MARK: - REF Token Generation

    /// Generate a REF token for a theme
    func generateRefToken(for theme: ConversationTheme) -> String {
        let shortId = String(theme.id.uuidString.prefix(8))
        let safeTopic = theme.topic
            .lowercased()
            .replacingOccurrences(of: " ", with: "_")
            .prefix(20)
        return "[REF:\(safeTopic)_\(shortId)]"
    }

    /// Create reference index entry for a theme
    func createReferencePointer(for theme: ConversationTheme) -> (String, ReferencePointer) {
        let refId = generateRefToken(for: theme)
        let preview = String(theme.content.prefix(100))
        let pointer = ReferencePointer(type: .theme, targetId: theme.id, preview: preview)
        return (refId, pointer)
    }
}
