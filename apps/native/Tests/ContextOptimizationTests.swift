//
//  ContextOptimizationTests.swift
//  MedStation Tests
//
//  Comprehensive tests for the context optimization system.
//  Tests TokenCounter, ContextOptimizer, and related components.
//

import XCTest
@testable import MedStation

@MainActor
final class ContextOptimizationTests: XCTestCase {

    // MARK: - Token Counter Tests

    func testTokenCounterCharacterApprox() {
        // Test character-based approximation
        let text = "Hello world, this is a test message."
        let count = TokenCounter.count(text, strategy: .characterApprox)

        // ~4 chars per token, 37 chars -> ~10 tokens
        XCTAssertGreaterThan(count, 5)
        XCTAssertLessThan(count, 15)
    }

    func testTokenCounterWordApprox() {
        // Test word-based approximation
        let text = "Hello world this is a test message"
        let count = TokenCounter.count(text, strategy: .wordApprox)

        // 7 words * 1.33 -> ~10 tokens
        XCTAssertGreaterThan(count, 7)
        XCTAssertLessThan(count, 15)
    }

    func testTokenCounterBPEEstimate() {
        // Test BPE-style estimation
        let text = "The quick brown fox jumps over the lazy dog."
        let count = TokenCounter.count(text, strategy: .bpeEstimate)

        // Common words should be ~1 token each
        XCTAssertGreaterThan(count, 8)
        XCTAssertLessThan(count, 20)
    }

    func testTokenCounterEmptyString() {
        let count = TokenCounter.count("")
        XCTAssertEqual(count, 0)
    }

    func testTokenCounterLongWord() {
        // Long words should be split into multiple tokens
        let text = "supercalifragilisticexpialidocious"
        let count = TokenCounter.count(text, strategy: .bpeEstimate)

        // 34 chars / 4 = ~9 tokens
        XCTAssertGreaterThan(count, 5)
    }

    func testTokenCounterCommonWords() {
        // Common words should be single tokens
        let text = "the and for with from"
        let count = TokenCounter.count(text, strategy: .bpeEstimate)

        // 5 common words should be ~5 tokens
        XCTAssertLessThanOrEqual(count, 7)
    }

    // MARK: - Token Budget Tests

    func testTokenBudgetAllocation() {
        var budget = TokenBudget(total: 1000)

        XCTAssertEqual(budget.remaining, 1000)

        let success = budget.allocate(500, for: "messages")
        XCTAssertTrue(success)
        XCTAssertEqual(budget.remaining, 500)
        XCTAssertEqual(budget.allocation(for: "messages"), 500)
    }

    func testTokenBudgetOverAllocation() {
        var budget = TokenBudget(total: 100)

        let success = budget.allocate(150, for: "test")
        XCTAssertFalse(success)
        XCTAssertEqual(budget.remaining, 100)
    }

    func testTokenBudgetRelease() {
        var budget = TokenBudget(total: 1000)
        _ = budget.allocate(500, for: "test")

        budget.release(200, for: "test")
        XCTAssertEqual(budget.remaining, 700)
        XCTAssertEqual(budget.allocation(for: "test"), 300)
    }

    func testTokenBudgetForModel() {
        let claudeBudget = TokenBudget.forModel("claude-3-opus")
        XCTAssertEqual(claudeBudget.total, 200000)

        let ollamaBudget = TokenBudget.forModel("llama3.2:70b")
        XCTAssertEqual(ollamaBudget.total, 32000)

        let smallBudget = TokenBudget.forModel("llama3.2:3b")
        XCTAssertEqual(smallBudget.total, 16000)
    }

    // MARK: - Truncation Tests

    func testTruncateToFitUnderBudget() {
        let text = "Short text"
        let result = TokenCounter.truncateToFit(text, budget: 100)

        XCTAssertEqual(result, text) // Should not be truncated
    }

    func testTruncateToFitOverBudget() {
        let text = String(repeating: "word ", count: 100)
        let result = TokenCounter.truncateToFit(text, budget: 20, addEllipsis: true)

        let tokenCount = TokenCounter.count(result)
        XCTAssertLessThanOrEqual(tokenCount, 25) // Allow some margin
        XCTAssertTrue(result.hasSuffix("...") || result.hasSuffix(".."))
    }

    func testTruncateAtSentenceBoundary() {
        let text = "First sentence. Second sentence. Third sentence."
        let result = TokenCounter.truncateToFit(text, budget: 10, addEllipsis: true)

        // Should try to break at sentence boundary
        XCTAssertTrue(result.contains("."))
    }

    // MARK: - Token Estimation Tests

    func testTokenEstimationForMessage() {
        let message = ChatMessage(
            role: .user,
            content: "Hello, can you help me with something?",
            sessionId: UUID()
        )

        let tokens = TokenEstimation.forMessage(message)

        // Content + role overhead (~4 tokens)
        XCTAssertGreaterThan(tokens, 10)
        XCTAssertLessThan(tokens, 30)
    }

    // MARK: - Context Item Tests

    func testContextItemCombinedScore() {
        let item = ContextItem(
            type: .recentMessage,
            content: "Test content",
            relevanceScore: 0.8,
            recencyScore: 0.6
        )

        // Combined: (0.8 * 0.5) + (0.6 * 0.2) + (priorityWeight * 0.3)
        // For recentMessage, priorityWeight = 0.95
        // = 0.4 + 0.12 + 0.285 = 0.805
        let score = item.combinedScore
        XCTAssertGreaterThan(score, 0.7)
        XCTAssertLessThan(score, 0.9)
    }

    func testContextItemPriorityWithRequired() {
        let required = ContextItem(
            type: .systemPrompt,
            content: "System prompt",
            metadata: ContextItemMetadata(isRequired: true)
        )

        let optional = ContextItem(
            type: .systemPrompt,
            content: "System prompt",
            metadata: ContextItemMetadata(isRequired: false)
        )

        // Required items should have 2x priority
        XCTAssertGreaterThan(required.priority, optional.priority * 1.5)
    }

    func testContextItemTypeWeights() {
        XCTAssertEqual(ContextItemType.systemPrompt.priorityWeight, 1.0)
        XCTAssertGreaterThan(ContextItemType.recentMessage.priorityWeight, 0.9)
        XCTAssertGreaterThan(ContextItemType.historyBridge.priorityWeight, 0.8)
    }

    // MARK: - Context Item Collection Tests

    func testContextItemCollectionTotalTokens() {
        var collection = ContextItemCollection()

        collection.add(ContextItem(
            type: .recentMessage,
            content: "First message",
            tokens: 10
        ))

        collection.add(ContextItem(
            type: .recentMessage,
            content: "Second message",
            tokens: 15
        ))

        XCTAssertEqual(collection.totalTokens, 25)
    }

    func testContextItemCollectionSortedByPriority() {
        var collection = ContextItemCollection()

        // Add in reverse priority order
        collection.add(ContextItem(
            type: .teamContext,
            content: "Team",
            relevanceScore: 0.5
        ))

        collection.add(ContextItem(
            type: .systemPrompt,
            content: "System",
            relevanceScore: 1.0,
            metadata: ContextItemMetadata(isRequired: true)
        ))

        collection.add(ContextItem(
            type: .recentMessage,
            content: "Message",
            relevanceScore: 0.8
        ))

        let sorted = collection.sortedByPriority()

        // System prompt should be first (highest priority)
        XCTAssertEqual(sorted[0].type, .systemPrompt)
    }

    // MARK: - Optimizer Configuration Tests

    func testOptimizerConfigurationDefault() {
        let config = OptimizerConfiguration.default

        XCTAssertEqual(config.reservePercent, 0.1)
        XCTAssertTrue(config.allowTruncation)
    }

    func testOptimizerConfigurationTypeLimits() {
        let config = OptimizerConfiguration.default

        let limit = config.maxTokensForType(.recentMessage, totalBudget: 10000)
        // Default limit for recentMessage is 0.4 (40%)
        XCTAssertEqual(limit, 4000)
    }

    func testOptimizerConfigurationAggressive() {
        let config = OptimizerConfiguration.aggressive

        XCTAssertEqual(config.reservePercent, 0.05) // Lower reserve
        XCTAssertTrue(config.allowTruncation)
    }

    func testOptimizerConfigurationConservative() {
        let config = OptimizerConfiguration.conservative

        XCTAssertEqual(config.reservePercent, 0.15) // Higher reserve
        XCTAssertFalse(config.allowTruncation)
    }
}

// MARK: - Context Optimizer Integration Tests

@MainActor
final class ContextOptimizerIntegrationTests: XCTestCase {

    var optimizer: ContextOptimizer!

    override func setUp() async throws {
        try await super.setUp()
        optimizer = ContextOptimizer()
    }

    func testOptimizeWithinBudget() {
        var collection = ContextItemCollection()

        // Add items that fit within budget
        collection.add(ContextItem(
            type: .systemPrompt,
            content: "You are a helpful assistant.",
            tokens: 10,
            metadata: ContextItemMetadata(isRequired: true)
        ))

        collection.add(ContextItem(
            type: .recentMessage,
            content: "User message",
            tokens: 20
        ))

        let budget = TokenBudget(total: 100)
        let result = optimizer.optimize(items: collection, budget: budget, query: "test")

        XCTAssertEqual(result.included.count, 2)
        XCTAssertEqual(result.excluded.count, 0)
        XCTAssertLessThanOrEqual(result.usedBudget, 100)
    }

    func testOptimizeExceedsbudget() {
        var collection = ContextItemCollection()

        // Add required item
        collection.add(ContextItem(
            type: .systemPrompt,
            content: "System",
            tokens: 30,
            metadata: ContextItemMetadata(isRequired: true)
        ))

        // Add optional items that exceed budget
        for i in 0..<5 {
            collection.add(ContextItem(
                type: .recentMessage,
                content: "Message \(i)",
                tokens: 20,
                relevanceScore: Float(5 - i) / 5.0 // Higher score for earlier messages
            ))
        }

        let budget = TokenBudget(total: 80) // Can't fit all
        let result = optimizer.optimize(items: collection, budget: budget, query: "test")

        // System prompt should always be included
        XCTAssertTrue(result.included.contains { $0.type == .systemPrompt })

        // Some messages should be excluded
        XCTAssertGreaterThan(result.excluded.count, 0)

        // Should be within budget (with reserve)
        XCTAssertLessThanOrEqual(result.usedBudget, 80)
    }

    func testOptimizeAppliesTypeLimits() {
        var collection = ContextItemCollection()

        // Add many RAG results
        for i in 0..<10 {
            collection.add(ContextItem(
                type: .ragResult,
                content: "RAG result \(i)",
                tokens: 50,
                relevanceScore: 0.9
            ))
        }

        let budget = TokenBudget(total: 1000)
        let result = optimizer.optimize(items: collection, budget: budget, query: "test")

        // RAG results are limited to 20% of budget (200 tokens)
        // With 50 tokens each, max 4 should be included
        let ragCount = result.included.filter { $0.type == .ragResult }.count
        XCTAssertLessThanOrEqual(ragCount, 5) // Allow some margin
    }

    func testOptimizationResultMetrics() {
        var collection = ContextItemCollection()

        collection.add(ContextItem(
            type: .recentMessage,
            content: "Test",
            tokens: 50
        ))

        let budget = TokenBudget(total: 100)
        let result = optimizer.optimize(items: collection, budget: budget, query: "test")

        XCTAssertEqual(result.totalBudget, 100)
        XCTAssertGreaterThan(result.usedBudget, 0)
        XCTAssertGreaterThan(result.remainingBudget, 0)
        XCTAssertGreaterThan(result.utilizationPercent, 0)
    }
}
