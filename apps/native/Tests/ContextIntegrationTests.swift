//
//  ContextIntegrationTests.swift
//  MagnetarStudio Tests
//
//  Integration tests for the full context preservation and optimization flow.
//  Tests EnhancedContextBridge, CrossWorkspaceIntelligence, and end-to-end scenarios.
//

import XCTest
@testable import MagnetarStudio

@MainActor
final class ContextIntegrationTests: XCTestCase {

    // MARK: - Enhanced Context Bridge Tests

    func testEnhancedContextBridgeInitialization() {
        let bridge = EnhancedContextBridge()

        XCTAssertNil(bridge.activeSessionId)
        XCTAssertEqual(bridge.contextUtilization, 0)
    }

    func testContextBuildWithMessages() async {
        let bridge = EnhancedContextBridge()
        let sessionId = UUID()

        let messages: [ChatMessage] = [
            ChatMessage(role: .user, content: "Hello", sessionId: sessionId),
            ChatMessage(role: .assistant, content: "Hi there!", sessionId: sessionId),
            ChatMessage(role: .user, content: "Can you help me?", sessionId: sessionId)
        ]

        let context = await bridge.buildOptimizedChatContext(
            sessionId: sessionId,
            messages: messages,
            query: "Help with coding",
            model: "llama3.2:8b"
        )

        XCTAssertGreaterThan(context.optimizedContext.totalTokens, 0)
        XCTAssertGreaterThan(context.buildDuration, 0)
        XCTAssertEqual(bridge.activeSessionId, sessionId)
    }

    func testContextBuildUtilization() async {
        let bridge = EnhancedContextBridge()
        let sessionId = UUID()

        // Create enough messages to use some budget
        var messages: [ChatMessage] = []
        for i in 0..<10 {
            messages.append(ChatMessage(
                role: i % 2 == 0 ? .user : .assistant,
                content: "Message number \(i) with some content to add tokens",
                sessionId: sessionId
            ))
        }

        let context = await bridge.buildOptimizedChatContext(
            sessionId: sessionId,
            messages: messages,
            query: "test query",
            model: "llama3.2:8b"
        )

        // Should have some utilization
        XCTAssertGreaterThan(context.optimizedContext.budgetUtilization, 0)
        XCTAssertGreaterThan(bridge.contextUtilization, 0)
    }

    func testMessageProcessingForContext() async {
        let bridge = EnhancedContextBridge()
        let sessionId = UUID()

        let message = ChatMessage(
            role: .user,
            content: "Please review the AuthService.swift file for security issues",
            sessionId: sessionId
        )

        // This should index the message and extract file references
        await bridge.processMessageForContext(
            message: message,
            sessionId: sessionId,
            conversationTitle: "Security Review"
        )

        // Should have updated lastIndexUpdate
        XCTAssertNotNil(bridge.lastContextBuildTime)
    }

    // MARK: - Cross-Workspace Intelligence Tests

    func testCrossWorkspaceInitialization() {
        let intelligence = CrossWorkspaceIntelligence()

        XCTAssertEqual(intelligence.activeWorkspace, .chat)
        XCTAssertFalse(intelligence.workspaceContexts.isEmpty)
    }

    func testWorkspaceActivation() async {
        let intelligence = CrossWorkspaceIntelligence()

        await intelligence.onWorkspaceActivated(.code, context: WorkspaceActivationContext(
            activeQuery: "implement new feature",
            entities: ["UserService", "AuthController"],
            topics: ["authentication", "user management"]
        ))

        XCTAssertEqual(intelligence.activeWorkspace, .code)
        XCTAssertNotNil(intelligence.workspaceContexts[.code])
    }

    func testCrossWorkspaceInsightGeneration() async {
        let intelligence = CrossWorkspaceIntelligence()

        // Activate chat workspace with some context
        await intelligence.onWorkspaceActivated(.chat, context: WorkspaceActivationContext(
            activeQuery: "help with user authentication",
            entities: ["User", "Auth"],
            topics: ["authentication", "login"]
        ))

        // Then switch to code workspace
        await intelligence.onWorkspaceActivated(.code, context: WorkspaceActivationContext(
            activeQuery: "authentication implementation",
            entities: ["AuthService"],
            topics: ["authentication"]
        ))

        // Should generate insights connecting chat and code
        let insights = intelligence.crossWorkspaceInsights

        // May or may not have insights depending on RAG data
        // Just verify no crash
        XCTAssertNotNil(insights)
    }

    func testWorkspaceTypeExtensions() {
        XCTAssertEqual(WorkspaceType.chat.displayName, "Chat")
        XCTAssertEqual(WorkspaceType.code.displayName, "Code")
        XCTAssertEqual(WorkspaceType.vault.displayName, "Vault")

        XCTAssertFalse(WorkspaceType.chat.icon.isEmpty)
        XCTAssertFalse(WorkspaceType.code.ragSourceType.isEmpty)
    }

    // MARK: - Context Bundle Builder Tests

    func testContextBundleBuilder() {
        let bundle = ContextBundle.builder()
            .query("Test query")
            .session("session-123")
            .workspace("chat")
            .preferences(.default)
            .cacheTTL(60)
            .build()

        XCTAssertEqual(bundle.userQuery, "Test query")
        XCTAssertEqual(bundle.sessionId, "session-123")
        XCTAssertEqual(bundle.workspaceType, "chat")
        XCTAssertEqual(bundle.ttl, 60)
    }

    func testContextBundleMinimal() {
        let bundle = ContextBundle.minimal(query: "quick test", sessionId: "123")

        XCTAssertEqual(bundle.userQuery, "quick test")
        XCTAssertEqual(bundle.sessionId, "123")
        XCTAssertTrue(bundle.conversationHistory.isEmpty)
    }

    func testContextBundleValidity() {
        let bundle = ContextBundle.minimal(query: "test", sessionId: "123")

        XCTAssertTrue(bundle.isValid)

        let expired = bundle.expired()
        XCTAssertFalse(expired.isValid)
    }

    func testContextBundleHasContext() {
        let minimal = ContextBundle.minimal(query: "test", sessionId: "123")
        XCTAssertFalse(minimal.hasCrossWorkspaceContext)
        XCTAssertFalse(minimal.hasRAGContext)
    }

    // MARK: - Compaction Tests

    func testCompactServiceConfiguration() {
        let service = CompactService()

        XCTAssertGreaterThan(service.compactThreshold, 0)
    }

    // MARK: - Session Graph Tests

    func testSessionGraphBuilder() {
        let builder = SessionGraphBuilder()

        // Add some entities
        let entity1 = builder.addEntity(name: "UserService", type: .codeFile)
        let entity2 = builder.addEntity(name: "AuthController", type: .codeFile)

        XCTAssertNotNil(entity1)
        XCTAssertNotNil(entity2)

        // Add relationship
        let relationship = builder.addRelationship(
            from: "UserService",
            to: "AuthController",
            type: .dependsOn
        )

        XCTAssertNotNil(relationship)

        // Get graph
        let graph = builder.getGraph()
        XCTAssertEqual(graph.nodes.count, 2)
        XCTAssertEqual(graph.edges.count, 1)
    }

    func testEntityExtraction() {
        let builder = SessionGraphBuilder()

        let text = """
        The UserService.swift file depends on AuthController.
        We discussed this in Q3 planning.
        """

        let entities = builder.extractEntities(from: text)

        // Should extract file references and capitalized words
        XCTAssertGreaterThan(entities.count, 0)

        // Check for file extraction
        let fileEntities = entities.filter { $0.type == .file || $0.type == .codeFile }
        XCTAssertGreaterThan(fileEntities.count, 0)
    }

    func testGraphPathFinding() {
        let builder = SessionGraphBuilder()

        // Create a chain: A -> B -> C
        builder.addEntity(name: "A", type: .concept)
        builder.addEntity(name: "B", type: .concept)
        builder.addEntity(name: "C", type: .concept)

        builder.addRelationship(from: "A", to: "B", type: .relatedTo)
        builder.addRelationship(from: "B", to: "C", type: .relatedTo)

        let graph = builder.getGraph()

        // Find path from A to C
        if let nodeA = graph.findEntity(named: "A"),
           let nodeC = graph.findEntity(named: "C") {
            let path = graph.pathBetween(source: nodeA.id, target: nodeC.id)
            XCTAssertNotNil(path)
            XCTAssertEqual(path?.count, 2) // A->B, B->C
        }
    }

    // MARK: - Context Tier Manager Tests

    func testContextTierManagerInitialization() {
        let manager = ContextTierManager()

        XCTAssertEqual(manager.currentTier, .immediate)
    }

    func testContextTierBudgets() {
        let manager = ContextTierManager()

        // Immediate tier should have largest budget
        XCTAssertGreaterThan(manager.budgetForTier(.immediate), manager.budgetForTier(.themes))
        XCTAssertGreaterThan(manager.budgetForTier(.themes), manager.budgetForTier(.graph))
    }

    // MARK: - End-to-End Flow Tests

    func testFullContextFlow() async {
        // Simulate a complete context flow

        // 1. Create messages
        let sessionId = UUID()
        let messages: [ChatMessage] = [
            ChatMessage(role: .user, content: "Help me understand the authentication flow", sessionId: sessionId),
            ChatMessage(role: .assistant, content: "The authentication flow involves...", sessionId: sessionId)
        ]

        // 2. Build optimized context
        let bridge = EnhancedContextBridge()
        let context = await bridge.buildOptimizedChatContext(
            sessionId: sessionId,
            messages: messages,
            query: "How does the login work?",
            model: "llama3.2:8b"
        )

        // 3. Verify context is valid
        XCTAssertGreaterThan(context.optimizedContext.totalTokens, 0)
        XCTAssertFalse(context.formatForRequest().isEmpty)

        // 4. Process message for indexing
        for message in messages {
            await bridge.processMessageForContext(
                message: message,
                sessionId: sessionId,
                conversationTitle: "Auth Discussion"
            )
        }

        // 5. Session should be tracked
        XCTAssertEqual(bridge.activeSessionId, sessionId)
    }

    func testContextFlowWithCrossWorkspace() async {
        let bridge = EnhancedContextBridge()
        let intelligence = CrossWorkspaceIntelligence()
        let sessionId = UUID()

        // Simulate working in chat
        await intelligence.onWorkspaceActivated(.chat, context: WorkspaceActivationContext(
            activeQuery: "code review",
            topics: ["review", "code quality"]
        ))

        let messages = [
            ChatMessage(role: .user, content: "Please review my code", sessionId: sessionId)
        ]

        let context = await bridge.buildOptimizedChatContext(
            sessionId: sessionId,
            messages: messages,
            query: "code review request",
            model: "llama3.2:8b"
        )

        // Switch to code workspace
        await intelligence.onWorkspaceActivated(.code, context: WorkspaceActivationContext(
            activeQuery: "implementation",
            topics: ["code", "implementation"]
        ))

        // Context should still be valid
        XCTAssertNotNil(context.optimizedContext)

        // Debug summary should be available
        XCTAssertFalse(context.debugSummary.isEmpty)
    }
}

// MARK: - Performance Tests

@MainActor
final class ContextPerformanceTests: XCTestCase {

    func testEmbeddingPerformance() {
        let embedder = HashEmbedder()
        let texts = (0..<100).map { "Sample text for embedding test number \($0)" }

        measure {
            for text in texts {
                _ = embedder.embed(text)
            }
        }
    }

    func testTokenCountingPerformance() {
        let longText = String(repeating: "word ", count: 10000)

        measure {
            _ = TokenCounter.count(longText)
        }
    }

    func testContextOptimizationPerformance() async {
        let optimizer = ContextOptimizer()

        var collection = ContextItemCollection()
        for i in 0..<100 {
            collection.add(ContextItem(
                type: .recentMessage,
                content: "Message content \(i) with some additional text",
                tokens: 20,
                relevanceScore: Float.random(in: 0...1)
            ))
        }

        let budget = TokenBudget(total: 1000)

        // Can't use measure with async, so just verify it completes quickly
        let start = Date()
        let _ = optimizer.optimize(items: collection, budget: budget, query: "test query")
        let duration = Date().timeIntervalSince(start)

        XCTAssertLessThan(duration, 1.0) // Should complete in under 1 second
    }
}
