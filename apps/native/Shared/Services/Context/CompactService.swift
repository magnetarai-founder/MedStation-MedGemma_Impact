//
//  CompactService.swift
//  MagnetarStudio
//
//  Orchestrates conversation compaction with Ollama-based summarization.
//  Ported from MagnetarAI-iPad with MagnetarStudio backend integration.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "CompactService")

// MARK: - Compact Service

@MainActor
final class CompactService: ObservableObject {

    // MARK: - Published State

    @Published private(set) var isCompacting: Bool = false
    @Published private(set) var lastCompactionAt: Date?
    @Published private(set) var compactionStats: CompactionStats = CompactionStats()

    // MARK: - Dependencies

    private let themeExtractor: ThemeExtractor
    private let storageService: ConversationStorageService
    private let contextTierManager: ContextTierManager
    private let apiClient: ApiClient

    // MARK: - Configuration

    /// Messages to keep in immediate tier (full fidelity)
    let immediateMessageCount = 15

    /// Threshold to trigger auto-compaction
    let autoCompactThreshold = 50

    /// Ollama model for summarization (prefer smaller, fast models)
    var summarizationModel: String = "llama3.2:3b"

    // MARK: - Singleton

    static let shared = CompactService()

    // MARK: - Initialization

    init(
        themeExtractor: ThemeExtractor? = nil,
        storageService: ConversationStorageService? = nil,
        contextTierManager: ContextTierManager? = nil,
        apiClient: ApiClient? = nil
    ) {
        self.themeExtractor = themeExtractor ?? .shared
        self.storageService = storageService ?? .shared
        self.contextTierManager = contextTierManager ?? .shared
        self.apiClient = apiClient ?? .shared
    }

    // MARK: - Compaction

    /// Compact a conversation, preserving context through history bridge
    func compact(
        sessionId: UUID,
        messages: [ChatMessage],
        forceCompact: Bool = false
    ) async throws -> CompactionResult {
        guard !isCompacting else {
            throw CompactError.alreadyCompacting
        }

        guard forceCompact || messages.count > autoCompactThreshold else {
            return CompactionResult.noCompactionNeeded
        }

        isCompacting = true
        defer { isCompacting = false }

        logger.info("[CompactService] Starting compaction for session \(sessionId)")
        let startTime = Date()

        // 1. Split messages: keep recent, compact older
        let recentMessages = Array(messages.suffix(immediateMessageCount))
        let messagesToCompact = Array(messages.dropLast(immediateMessageCount))

        guard !messagesToCompact.isEmpty else {
            return CompactionResult.noCompactionNeeded
        }

        // 2. Extract themes from older messages
        let themes = try await themeExtractor.extractThemes(
            from: messagesToCompact,
            conversationId: sessionId
        )

        // 3. Generate summary via Ollama
        let summary = try await generateSummary(from: messagesToCompact)

        // 4. Extract structured data (decisions, TODOs)
        let structuredData = extractStructuredData(from: messagesToCompact)

        // 5. Build history bridge
        let bridge = HistoryBridgeBuilder.build(
            summary: summary,
            themes: themes,
            recentMessages: recentMessages,
            structuredData: structuredData
        )

        // 6. Create compressed context
        let compressedContext = CompressedContext(
            summary: summary,
            entities: themes.flatMap { $0.entities }.unique(),
            decisions: structuredData.decisions,
            todos: structuredData.todos,
            originalMessageCount: messagesToCompact.count,
            historyBridge: bridge
        )

        // 7. Store compressed context
        do {
            try storageService.saveCompressedContext(compressedContext, conversationId: sessionId)
        } catch {
            logger.error("[CompactService] Failed to persist compressed context: \(error.localizedDescription)")
        }

        // 8. Store themes
        for theme in themes {
            do {
                try storageService.saveTheme(theme, conversationId: sessionId)
            } catch {
                logger.error("[CompactService] Failed to persist theme '\(theme.topic)': \(error.localizedDescription)")
            }
        }

        // 9. Generate REF tokens for themes
        var refTokens: [String] = []
        for theme in themes {
            let (refId, _) = themeExtractor.createReferencePointer(for: theme)
            refTokens.append(refId)
        }

        // 10. Update metadata
        if var metadata = storageService.loadMetadata(sessionId) {
            metadata.isCompacted = true
            metadata.compactedAt = Date()
            metadata.primaryTopics = themes.map { $0.topic }
            do {
                try storageService.saveMetadata(metadata)
            } catch {
                logger.error("[CompactService] Failed to persist updated metadata: \(error.localizedDescription)")
            }
        }

        // 11. Update stats
        let duration = Date().timeIntervalSince(startTime)
        compactionStats.totalCompactions += 1
        compactionStats.messagesCompacted += messagesToCompact.count
        compactionStats.averageDuration = (compactionStats.averageDuration + duration) / 2
        lastCompactionAt = Date()

        logger.info("[CompactService] Compaction complete: \(messagesToCompact.count) messages → \(themes.count) themes in \(String(format: "%.2f", duration))s")

        return CompactionResult(
            bridge: bridge,
            themes: themes,
            refTokens: refTokens,
            compressedContext: compressedContext,
            messagesCompacted: messagesToCompact.count,
            messagesRetained: recentMessages.count
        )
    }

    // MARK: - Ollama Summarization

    /// Generate a summary using Ollama
    private func generateSummary(from messages: [ChatMessage]) async throws -> String {
        let conversationText = formatMessagesForSummary(messages)

        // Build summarization prompt
        let prompt = """
        Summarize this conversation in 2-3 paragraphs. Focus on:
        1. Main topics discussed
        2. Key decisions made
        3. Outstanding questions or tasks
        4. Important context for future reference

        Conversation:
        \(conversationText)

        Summary:
        """

        // Try Ollama via backend, fall back to local summarization
        do {
            return try await callOllamaSummarize(prompt: prompt)
        } catch {
            logger.warning("[CompactService] Ollama unavailable, using local summarization: \(error)")
            return localSummarize(messages)
        }
    }

    /// Call Ollama for summarization via backend API
    private func callOllamaSummarize(prompt: String) async throws -> String {
        struct SummarizeRequest: Encodable {
            let model: String
            let prompt: String
            let stream: Bool
        }

        struct SummarizeResponse: Decodable {
            let response: String
        }

        let request = SummarizeRequest(
            model: summarizationModel,
            prompt: prompt,
            stream: false
        )

        // Use configured Ollama URL (respects OLLAMA_URL env var)
        guard let url = URL(string: "\(APIConfiguration.shared.ollamaURL)/api/generate") else {
            throw CompactError.summarizationFailed
        }
        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "POST"
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.httpBody = try JSONEncoder().encode(request)
        urlRequest.timeoutInterval = 60

        let (data, response) = try await URLSession.shared.data(for: urlRequest)

        guard let httpResponse = response as? HTTPURLResponse,
              httpResponse.statusCode == 200 else {
            throw CompactError.summarizationFailed
        }

        let decoded = try JSONDecoder().decode(SummarizeResponse.self, from: data)
        return decoded.response
    }

    /// Local fallback summarization (no AI)
    private func localSummarize(_ messages: [ChatMessage]) -> String {
        // Extract key information without AI
        let userMessages = messages.filter { $0.role == .user }
        let assistantMessages = messages.filter { $0.role == .assistant }

        var parts: [String] = []
        parts.append("Conversation with \(messages.count) exchanges (\(userMessages.count) user, \(assistantMessages.count) assistant).")

        // First user message preview
        if let first = userMessages.first {
            let preview = String(first.content.prefix(150))
            parts.append("Started discussing: \"\(preview)...\"")
        }

        // Last user message preview
        if userMessages.count > 1, let last = userMessages.last {
            let preview = String(last.content.prefix(150))
            parts.append("Most recently: \"\(preview)...\"")
        }

        // Count words to estimate complexity
        let totalWords = messages.reduce(0) { $0 + $1.content.split(separator: " ").count }
        parts.append("Total content: ~\(totalWords) words.")

        return parts.joined(separator: " ")
    }

    /// Format messages for summarization prompt
    private func formatMessagesForSummary(_ messages: [ChatMessage]) -> String {
        // Limit to prevent token overflow
        let truncated = messages.suffix(30)
        return truncated.map { msg in
            let role = msg.role == .user ? "User" : "Assistant"
            let content = String(msg.content.prefix(500))
            return "\(role): \(content)"
        }.joined(separator: "\n\n")
    }

    // MARK: - Structured Data Extraction

    /// Extract decisions and TODOs from messages
    private func extractStructuredData(from messages: [ChatMessage]) -> StructuredExtraction {
        var decisions: [String] = []
        var todos: [String] = []

        let decisionPatterns = [
            "decided to", "we'll go with", "let's use", "agreed on",
            "the plan is", "we should", "i'll", "i will"
        ]

        let todoPatterns = [
            "todo:", "to-do:", "task:", "need to", "don't forget",
            "remember to", "make sure to", "should follow up"
        ]

        for message in messages {
            let content = message.content.lowercased()

            // Extract decisions
            for pattern in decisionPatterns {
                if content.contains(pattern) {
                    let sentences = message.content.components(separatedBy: ".")
                    for sentence in sentences {
                        if sentence.lowercased().contains(pattern) {
                            decisions.append(sentence.trimmingCharacters(in: .whitespacesAndNewlines))
                        }
                    }
                }
            }

            // Extract TODOs
            for pattern in todoPatterns {
                if content.contains(pattern) {
                    let sentences = message.content.components(separatedBy: ".")
                    for sentence in sentences {
                        if sentence.lowercased().contains(pattern) {
                            todos.append(sentence.trimmingCharacters(in: .whitespacesAndNewlines))
                        }
                    }
                }
            }
        }

        return StructuredExtraction(
            decisions: decisions.unique().prefix(10).map { String($0) },
            todos: todos.unique().prefix(10).map { String($0) }
        )
    }

    // MARK: - Auto-Compact Check

    /// Check if a session needs compaction
    func needsCompaction(messageCount: Int) -> Bool {
        return messageCount > autoCompactThreshold
    }

    /// Get compaction recommendation
    func getCompactionRecommendation(messageCount: Int) -> CompactionRecommendation {
        if messageCount < autoCompactThreshold / 2 {
            return .notNeeded
        } else if messageCount < autoCompactThreshold {
            return .soon(messagesUntil: autoCompactThreshold - messageCount)
        } else {
            return .recommended(excessMessages: messageCount - autoCompactThreshold)
        }
    }

    // MARK: - History Bridge Access

    /// Get history bridge for a session (for AI context)
    func getHistoryBridge(for sessionId: UUID) -> HistoryBridge? {
        let compressedContext = storageService.loadCompressedContext(sessionId)
        return compressedContext?.historyBridge
    }

    /// Build AI context from history bridge + recent messages
    func buildAIContext(
        sessionId: UUID,
        recentMessages: [ChatMessage],
        maxTokens: Int = 3000
    ) -> AIContextBundle {
        let bridge = getHistoryBridge(for: sessionId)
        let themes = storageService.loadThemes(sessionId)

        return AIContextBundle(
            historyBridge: bridge,
            recentMessages: recentMessages,
            relevantThemes: themes.prefix(5).map { $0 },
            estimatedTokens: estimateTokens(
                bridge: bridge,
                messages: recentMessages,
                themes: Array(themes.prefix(5))
            )
        )
    }

    /// Estimate token count for context bundle
    private func estimateTokens(
        bridge: HistoryBridge?,
        messages: [ChatMessage],
        themes: [ConversationTheme]
    ) -> Int {
        var count = 0

        // Rough estimate: 1 token ≈ 4 characters
        if let bridge = bridge {
            count += bridge.summary.count / 4
        }

        for message in messages {
            count += message.content.count / 4
        }

        for theme in themes {
            count += theme.content.count / 4
        }

        return count
    }
}

// MARK: - Compaction Result

struct CompactionResult {
    let bridge: HistoryBridge?
    let themes: [ConversationTheme]
    let refTokens: [String]
    let compressedContext: CompressedContext?
    let messagesCompacted: Int
    let messagesRetained: Int

    var wasCompacted: Bool { messagesCompacted > 0 }

    static let noCompactionNeeded = CompactionResult(
        bridge: nil,
        themes: [],
        refTokens: [],
        compressedContext: nil,
        messagesCompacted: 0,
        messagesRetained: 0
    )
}

// MARK: - Compaction Stats

struct CompactionStats {
    var totalCompactions: Int = 0
    var messagesCompacted: Int = 0
    var averageDuration: TimeInterval = 0
}

// MARK: - Compaction Recommendation

enum CompactionRecommendation {
    case notNeeded
    case soon(messagesUntil: Int)
    case recommended(excessMessages: Int)

    var message: String {
        switch self {
        case .notNeeded:
            return "Context is healthy"
        case .soon(let count):
            return "Compaction recommended in \(count) messages"
        case .recommended(let excess):
            return "Compaction recommended (\(excess) messages over threshold)"
        }
    }
}

// MARK: - Structured Extraction

struct StructuredExtraction {
    let decisions: [String]
    let todos: [String]
}

// MARK: - AI Context Bundle

struct AIContextBundle {
    let historyBridge: HistoryBridge?
    let recentMessages: [ChatMessage]
    let relevantThemes: [ConversationTheme]
    let estimatedTokens: Int

    /// Format for inclusion in AI prompt
    func formatForPrompt() -> String {
        var parts: [String] = []

        // History bridge summary
        if let bridge = historyBridge {
            parts.append("## Previous Context Summary\n\(bridge.summary)")

            if !bridge.keyTopics.isEmpty {
                parts.append("Key topics: \(bridge.keyTopics.joined(separator: ", "))")
            }
        }

        // Relevant themes
        if !relevantThemes.isEmpty {
            parts.append("\n## Relevant Background")
            for theme in relevantThemes {
                parts.append("- **\(theme.topic)**: \(theme.content)")
            }
        }

        return parts.joined(separator: "\n\n")
    }
}

// MARK: - Errors

enum CompactError: LocalizedError {
    case alreadyCompacting
    case summarizationFailed
    case storageFailed

    var errorDescription: String? {
        switch self {
        case .alreadyCompacting:
            return "Compaction already in progress"
        case .summarizationFailed:
            return "Failed to generate summary"
        case .storageFailed:
            return "Failed to store compressed context"
        }
    }
}

// MARK: - Array Extension

private extension Array where Element: Hashable {
    func unique() -> [Element] {
        var seen = Set<Element>()
        return filter { seen.insert($0).inserted }
    }
}
