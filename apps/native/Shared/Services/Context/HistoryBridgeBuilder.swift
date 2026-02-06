//
//  HistoryBridgeBuilder.swift
//  MagnetarStudio
//
//  Builds history bridges for maintaining context across compaction.
//  Bridges preserve essential context while staying within token limits.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "HistoryBridgeBuilder")

// MARK: - History Bridge Builder

/// Static builder for constructing history bridges from conversation data
enum HistoryBridgeBuilder {

    // MARK: - Configuration

    /// Maximum length for bridge summary
    static let maxSummaryLength = 2000

    /// Maximum number of key topics
    static let maxKeyTopics = 10

    /// Default recent message count
    static let defaultRecentMessageCount = 15

    // MARK: - Building

    /// Build a history bridge from compaction components
    static func build(
        summary: String,
        themes: [ConversationTheme],
        recentMessages: [ChatMessage],
        structuredData: StructuredExtraction
    ) -> HistoryBridge {
        // Truncate summary if needed
        let truncatedSummary = truncateSummary(summary)

        // Extract key topics from themes
        let keyTopics = extractKeyTopics(from: themes, limit: maxKeyTopics)

        return HistoryBridge(
            summary: truncatedSummary,
            keyTopics: keyTopics,
            recentMessageCount: recentMessages.count
        )
    }

    /// Build a minimal history bridge from just messages
    static func buildMinimal(from messages: [ChatMessage]) -> HistoryBridge {
        let summary = generateMinimalSummary(from: messages)
        let topics = extractTopicsFromMessages(messages)

        return HistoryBridge(
            summary: summary,
            keyTopics: topics,
            recentMessageCount: min(messages.count, defaultRecentMessageCount)
        )
    }

    /// Build an enhanced history bridge with structured data
    static func buildEnhanced(
        summary: String,
        themes: [ConversationTheme],
        recentMessages: [ChatMessage],
        structuredData: StructuredExtraction,
        sessionGraph: SessionGraph?
    ) -> EnhancedHistoryBridge {
        let baseBridge = build(
            summary: summary,
            themes: themes,
            recentMessages: recentMessages,
            structuredData: structuredData
        )

        // Extract entity mentions from graph
        let entityMentions = extractEntityMentions(from: sessionGraph)

        // Build enhanced version
        return EnhancedHistoryBridge(
            base: baseBridge,
            decisions: structuredData.decisions,
            todos: structuredData.todos,
            entityMentions: entityMentions,
            themeIds: themes.map { $0.id }
        )
    }

    // MARK: - Summary Helpers

    /// Truncate summary to fit within limits
    private static func truncateSummary(_ summary: String) -> String {
        if summary.count <= maxSummaryLength {
            return summary
        }

        // Truncate at sentence boundary
        let truncated = String(summary.prefix(maxSummaryLength))
        if let lastPeriod = truncated.lastIndex(of: ".") {
            return String(truncated[...lastPeriod])
        }

        return truncated + "..."
    }

    /// Generate minimal summary without AI
    private static func generateMinimalSummary(from messages: [ChatMessage]) -> String {
        let userMessages = messages.filter { $0.role == .user }
        let assistantMessages = messages.filter { $0.role == .assistant }

        var parts: [String] = []
        parts.append("Conversation: \(userMessages.count) user messages, \(assistantMessages.count) assistant responses.")

        // First user message preview
        if let first = userMessages.first {
            let preview = String(first.content.prefix(200))
            parts.append("Started with: \"\(preview)\"")
        }

        // Last exchange preview
        if let lastUser = userMessages.last {
            let preview = String(lastUser.content.prefix(150))
            parts.append("Most recent topic: \"\(preview)\"")
        }

        return parts.joined(separator: " ")
    }

    // MARK: - Topic Extraction

    /// Extract key topics from themes
    private static func extractKeyTopics(from themes: [ConversationTheme], limit: Int) -> [String] {
        // Sort themes by relevance
        let sorted = themes.sorted { $0.relevanceScore > $1.relevanceScore }

        // Take top topics
        return sorted.prefix(limit).map { $0.topic }
    }

    /// Extract topics directly from messages (fallback)
    private static func extractTopicsFromMessages(_ messages: [ChatMessage]) -> [String] {
        var wordFrequency: [String: Int] = [:]

        for message in messages {
            let words = message.content
                .components(separatedBy: .whitespacesAndNewlines)
                .map { $0.lowercased().trimmingCharacters(in: .punctuationCharacters) }
                .filter { $0.count > 4 && !stopWords.contains($0) }

            for word in words {
                wordFrequency[word, default: 0] += 1
            }
        }

        // Return most frequent non-stop words
        return wordFrequency
            .sorted { $0.value > $1.value }
            .prefix(maxKeyTopics)
            .map { $0.key.capitalized }
    }

    /// Extract entity mentions from session graph
    private static func extractEntityMentions(from graph: SessionGraph?) -> [String: Int] {
        guard let graph = graph else { return [:] }

        var mentions: [String: Int] = [:]
        for node in graph.nodes {
            mentions[node.name] = node.mentionCount
        }
        return mentions
    }

    // MARK: - Stop Words

    private static let stopWords: Set<String> = [
        "the", "and", "for", "are", "but", "not", "you", "all", "can",
        "her", "was", "one", "our", "out", "has", "have", "been", "were",
        "said", "this", "that", "with", "they", "from", "will", "would",
        "there", "their", "what", "about", "which", "when", "make", "like",
        "time", "just", "know", "take", "people", "into", "year", "your",
        "good", "some", "could", "them", "than", "then", "look", "only"
    ]
}

// MARK: - Enhanced History Bridge

/// Extended history bridge with additional structured data
struct EnhancedHistoryBridge: Codable, Sendable {
    let base: HistoryBridge
    let decisions: [String]
    let todos: [String]
    let entityMentions: [String: Int]
    let themeIds: [UUID]

    /// Format for AI context inclusion
    func formatForAI() -> String {
        var sections: [String] = []

        // Base summary
        sections.append("## Conversation History\n\(base.summary)")

        // Key topics
        if !base.keyTopics.isEmpty {
            sections.append("**Topics discussed:** \(base.keyTopics.joined(separator: ", "))")
        }

        // Decisions
        if !decisions.isEmpty {
            sections.append("**Key decisions:**\n" + decisions.map { "- \($0)" }.joined(separator: "\n"))
        }

        // Outstanding TODOs
        if !todos.isEmpty {
            sections.append("**Outstanding items:**\n" + todos.map { "- \($0)" }.joined(separator: "\n"))
        }

        // Top entities
        let topEntities = entityMentions
            .sorted { $0.value > $1.value }
            .prefix(5)
            .map { $0.key }

        if !topEntities.isEmpty {
            sections.append("**Key entities:** \(topEntities.joined(separator: ", "))")
        }

        return sections.joined(separator: "\n\n")
    }

    /// Token estimate for this bridge
    var estimatedTokens: Int {
        let totalChars = base.summary.count +
            decisions.joined().count +
            todos.joined().count +
            entityMentions.keys.joined().count

        return totalChars / 4  // Rough estimate: 1 token ≈ 4 chars
    }
}

// MARK: - History Bridge Extension

extension HistoryBridge {
    /// Format for inclusion in AI prompt
    func formatForPrompt() -> String {
        var parts: [String] = []

        parts.append("## Previous Context\n\(summary)")

        if !keyTopics.isEmpty {
            parts.append("Topics: \(keyTopics.joined(separator: ", "))")
        }

        parts.append("(Based on \(recentMessageCount) recent messages)")

        return parts.joined(separator: "\n")
    }

    /// Token estimate
    var estimatedTokens: Int {
        return (summary.count + keyTopics.joined().count) / 4
    }

    /// Check if bridge is stale (older than threshold)
    func isStale(threshold: TimeInterval = 3600) -> Bool {
        return Date().timeIntervalSince(createdAt) > threshold
    }
}

// MARK: - Bridge Merger

/// Utility for merging multiple history bridges (e.g., from branched conversations)
enum HistoryBridgeMerger {

    /// Merge multiple bridges into one
    static func merge(_ bridges: [HistoryBridge]) -> HistoryBridge {
        guard !bridges.isEmpty else {
            return HistoryBridge(summary: "", keyTopics: [], recentMessageCount: 0)
        }

        if bridges.count == 1 {
            return bridges[0]
        }

        // Combine summaries
        let combinedSummary = bridges.map { $0.summary }.joined(separator: "\n\n---\n\n")

        // Merge topics (deduplicated)
        var allTopics: [String] = []
        var seenTopics: Set<String> = []
        for bridge in bridges {
            for topic in bridge.keyTopics {
                let normalized = topic.lowercased()
                if !seenTopics.contains(normalized) {
                    seenTopics.insert(normalized)
                    allTopics.append(topic)
                }
            }
        }

        // Sum message counts
        let totalMessages = bridges.reduce(0) { $0 + $1.recentMessageCount }

        return HistoryBridge(
            summary: String(combinedSummary.prefix(HistoryBridgeBuilder.maxSummaryLength)),
            keyTopics: Array(allTopics.prefix(HistoryBridgeBuilder.maxKeyTopics)),
            recentMessageCount: totalMessages
        )
    }

    /// Merge enhanced bridges
    static func mergeEnhanced(_ bridges: [EnhancedHistoryBridge]) -> EnhancedHistoryBridge {
        let baseBridges = bridges.map { $0.base }
        let mergedBase = merge(baseBridges)

        // Combine decisions and todos (deduplicated)
        var allDecisions: [String] = []
        var allTodos: [String] = []
        var allEntities: [String: Int] = [:]
        var allThemeIds: [UUID] = []

        for bridge in bridges {
            for decision in bridge.decisions where !allDecisions.contains(decision) {
                allDecisions.append(decision)
            }
            for todo in bridge.todos where !allTodos.contains(todo) {
                allTodos.append(todo)
            }
            for (entity, count) in bridge.entityMentions {
                allEntities[entity, default: 0] += count
            }
            allThemeIds.append(contentsOf: bridge.themeIds)
        }

        return EnhancedHistoryBridge(
            base: mergedBase,
            decisions: Array(allDecisions.prefix(15)),
            todos: Array(allTodos.prefix(15)),
            entityMentions: allEntities,
            themeIds: allThemeIds.unique()
        )
    }
}

// MARK: - Array Extension

private extension Array where Element: Hashable {
    func unique() -> [Element] {
        var seen = Set<Element>()
        return filter { seen.insert($0).inserted }
    }
}
