//
//  TokenCounter.swift
//  MagnetarStudio
//
//  Token counting utilities for context budget management.
//  Supports multiple tokenization strategies for different models.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "TokenCounter")

// MARK: - Token Counter

/// Utility for counting tokens in text
struct TokenCounter {

    // MARK: - Tokenization Strategy

    enum Strategy {
        /// Character-based approximation (~4 chars per token)
        case characterApprox

        /// Word-based approximation (~0.75 tokens per word)
        case wordApprox

        /// BPE-style estimation (more accurate for GPT-style models)
        case bpeEstimate

        /// Exact count using tiktoken (if available)
        case tiktoken
    }

    // MARK: - Configuration

    /// Default strategy
    static var defaultStrategy: Strategy = .bpeEstimate

    /// Chars per token for character approximation
    static let charsPerToken: Float = 4.0

    /// Words to tokens ratio
    static let tokensPerWord: Float = 1.33

    // MARK: - Counting

    /// Count tokens in text using default strategy
    static func count(_ text: String) -> Int {
        return count(text, strategy: defaultStrategy)
    }

    /// Count tokens in text using specified strategy
    static func count(_ text: String, strategy: Strategy) -> Int {
        guard !text.isEmpty else { return 0 }

        switch strategy {
        case .characterApprox:
            return countCharacterApprox(text)

        case .wordApprox:
            return countWordApprox(text)

        case .bpeEstimate:
            return countBPEEstimate(text)

        case .tiktoken:
            // Fallback to BPE estimate (tiktoken not available in Swift)
            return countBPEEstimate(text)
        }
    }

    /// Count tokens for multiple texts
    static func countBatch(_ texts: [String], strategy: Strategy = defaultStrategy) -> Int {
        return texts.reduce(0) { $0 + count($1, strategy: strategy) }
    }

    // MARK: - Strategy Implementations

    /// Simple character-based approximation
    private static func countCharacterApprox(_ text: String) -> Int {
        return Int(ceil(Float(text.count) / charsPerToken))
    }

    /// Word-based approximation
    private static func countWordApprox(_ text: String) -> Int {
        let words = text.components(separatedBy: .whitespacesAndNewlines)
            .filter { !$0.isEmpty }
        return Int(ceil(Float(words.count) * tokensPerWord))
    }

    /// BPE-style estimation (more accurate for GPT-style models)
    private static func countBPEEstimate(_ text: String) -> Int {
        var tokens = 0

        // Split by whitespace first
        let words = text.components(separatedBy: .whitespacesAndNewlines)
            .filter { !$0.isEmpty }

        for word in words {
            // Common words are usually 1 token
            if commonTokens.contains(word.lowercased()) {
                tokens += 1
                continue
            }

            // Estimate based on character patterns
            let length = word.count

            if length <= 3 {
                tokens += 1
            } else if length <= 6 {
                // Short words: 1-2 tokens
                tokens += word.contains(where: { $0.isUppercase }) ? 2 : 1
            } else if length <= 10 {
                // Medium words: 2-3 tokens
                tokens += 2
            } else {
                // Long words: roughly 1 token per 4 chars
                tokens += max(2, Int(ceil(Float(length) / 4.0)))
            }

            // Add extra for punctuation attached to words
            let punctuation = word.filter { $0.isPunctuation }
            tokens += punctuation.count > 0 ? 1 : 0
        }

        // Account for newlines and special characters
        let newlines = text.components(separatedBy: "\n").count - 1
        tokens += newlines

        return max(1, tokens)
    }

    // MARK: - Common Tokens

    /// Common English words that are typically single tokens
    private static let commonTokens: Set<String> = [
        "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
        "have", "has", "had", "do", "does", "did", "will", "would", "could",
        "should", "may", "might", "must", "can", "this", "that", "these",
        "those", "i", "you", "he", "she", "it", "we", "they", "what", "which",
        "who", "when", "where", "why", "how", "all", "each", "every", "both",
        "few", "more", "some", "any", "no", "not", "only", "same", "so",
        "than", "too", "very", "just", "also", "now", "here", "there", "then",
        "if", "or", "and", "but", "for", "with", "from", "to", "of", "in",
        "on", "at", "by", "as", "up", "out", "into", "over", "after", "before"
    ]

    // MARK: - Budget Utilities

    /// Check if text fits within token budget
    static func fitsInBudget(_ text: String, budget: Int) -> Bool {
        return count(text) <= budget
    }

    /// Truncate text to fit within token budget
    static func truncateToFit(_ text: String, budget: Int, addEllipsis: Bool = true) -> String {
        let currentCount = count(text)
        guard currentCount > budget else { return text }

        // Estimate characters to keep
        let ratio = Float(budget) / Float(currentCount)
        var targetChars = Int(Float(text.count) * ratio * 0.95)  // 5% buffer

        // Try to break at sentence boundary
        let truncated = String(text.prefix(targetChars))
        if let lastPeriod = truncated.lastIndex(of: ".") {
            let atSentence = String(truncated[...lastPeriod])
            if count(atSentence) <= budget {
                return addEllipsis && atSentence.count < text.count
                    ? atSentence + ".."
                    : atSentence
            }
        }

        // Break at word boundary
        if let lastSpace = truncated.lastIndex(of: " ") {
            let atWord = String(truncated[..<lastSpace])
            return addEllipsis ? atWord + "..." : atWord
        }

        return addEllipsis ? truncated + "..." : truncated
    }

    /// Split text into chunks that fit within budget
    static func splitIntoBudgetedChunks(_ text: String, chunkBudget: Int) -> [String] {
        var chunks: [String] = []
        var remaining = text

        while !remaining.isEmpty {
            let chunk = truncateToFit(remaining, budget: chunkBudget, addEllipsis: false)
            chunks.append(chunk)

            // Remove processed portion
            if chunk.count >= remaining.count {
                break
            }
            remaining = String(remaining.dropFirst(chunk.count)).trimmingCharacters(in: .whitespaces)
        }

        return chunks
    }
}

// MARK: - Token Budget

/// Represents a token budget with allocation tracking
struct TokenBudget {
    let total: Int
    private(set) var used: Int = 0
    private(set) var allocations: [String: Int] = [:]

    var remaining: Int { total - used }
    var utilizationPercent: Float { Float(used) / Float(total) * 100 }
    var isExhausted: Bool { remaining <= 0 }

    init(total: Int) {
        self.total = total
    }

    /// Try to allocate tokens for a category
    mutating func allocate(_ tokens: Int, for category: String) -> Bool {
        guard tokens <= remaining else { return false }
        used += tokens
        allocations[category, default: 0] += tokens
        return true
    }

    /// Reserve tokens (subtract from remaining but don't track)
    mutating func reserve(_ tokens: Int) -> Bool {
        guard tokens <= remaining else { return false }
        used += tokens
        return true
    }

    /// Release previously allocated tokens
    mutating func release(_ tokens: Int, for category: String) {
        let released = min(tokens, allocations[category] ?? 0)
        allocations[category, default: 0] -= released
        used -= released
    }

    /// Get allocation for a category
    func allocation(for category: String) -> Int {
        return allocations[category] ?? 0
    }

    /// Reset budget
    mutating func reset() {
        used = 0
        allocations.removeAll()
    }

    // MARK: - Presets

    static func appleFM() -> TokenBudget { TokenBudget(total: 4000) }
    static func ollamaSmall() -> TokenBudget { TokenBudget(total: 8000) }
    static func ollamaMedium() -> TokenBudget { TokenBudget(total: 16000) }
    static func ollamaLarge() -> TokenBudget { TokenBudget(total: 32000) }
    static func huggingFace() -> TokenBudget { TokenBudget(total: 128000) }
    static func claude() -> TokenBudget { TokenBudget(total: 200000) }

    static func forModel(_ modelName: String) -> TokenBudget {
        let name = modelName.lowercased()

        if name.contains("claude") {
            return .claude()
        } else if name.contains("70b") || name.contains("72b") || name.contains("65b") {
            return .ollamaLarge()
        } else if name.contains("13b") || name.contains("14b") || name.contains("7b") || name.contains("8b") {
            return .ollamaMedium()
        } else if name.contains("gguf") {
            return .huggingFace()
        } else if name.contains("apple") || name.contains("fm") {
            return .appleFM()
        }

        return .ollamaSmall()
    }
}

// MARK: - Token Estimation

/// Detailed token estimation for different content types
struct TokenEstimation {

    /// Estimate tokens for a chat message
    static func forMessage(_ message: ChatMessage) -> Int {
        // Base content tokens
        var tokens = TokenCounter.count(message.content)

        // Role token overhead (~4 tokens for role label)
        tokens += 4

        return tokens
    }

    /// Estimate tokens for messages array
    static func forMessages(_ messages: [ChatMessage]) -> Int {
        return messages.reduce(0) { $0 + forMessage($1) }
    }

    /// Estimate tokens for a theme
    static func forTheme(_ theme: ConversationTheme) -> Int {
        var tokens = TokenCounter.count(theme.content)
        tokens += TokenCounter.count(theme.topic)
        tokens += theme.keyPoints.reduce(0) { $0 + TokenCounter.count($1) }
        tokens += theme.entities.count * 2  // ~2 tokens per entity name
        return tokens
    }

    /// Estimate tokens for a semantic node
    static func forSemanticNode(_ node: SemanticNode) -> Int {
        var tokens = TokenCounter.count(node.content)
        tokens += TokenCounter.count(node.concept)
        tokens += node.entities.count * 2

        // Structured data
        if let decisions = node.decisions {
            tokens += decisions.reduce(0) { $0 + TokenCounter.count($1.summary) }
        }
        if let todos = node.todos {
            tokens += todos.reduce(0) { $0 + TokenCounter.count($1.description) }
        }

        return tokens
    }

    /// Estimate tokens for history bridge
    static func forHistoryBridge(_ bridge: HistoryBridge) -> Int {
        var tokens = TokenCounter.count(bridge.summary)
        tokens += bridge.keyTopics.reduce(0) { $0 + TokenCounter.count($1) }
        tokens += 20  // Formatting overhead
        return tokens
    }

    /// Estimate tokens for RAG results
    static func forRAGResults(_ results: [RAGSearchResult]) -> Int {
        return results.reduce(0) { total, result in
            var tokens = TokenCounter.count(result.document.content)
            tokens += 10  // Source label and formatting
            return total + tokens
        }
    }

    /// Estimate tokens for system prompt
    static func forSystemPrompt(basePrompt: String, contextSections: Int) -> Int {
        var tokens = TokenCounter.count(basePrompt)
        tokens += contextSections * 15  // Header overhead per section
        return tokens
    }
}
