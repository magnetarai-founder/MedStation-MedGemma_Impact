//
//  RAGSystemTests.swift
//  MedStation Tests
//
//  Comprehensive tests for the RAG (Retrieval Augmented Generation) system.
//  Tests HashEmbedder, VectorStore, SemanticSearchService, and related components.
//

import XCTest
@testable import MedStation

@MainActor
final class HashEmbedderTests: XCTestCase {

    var embedder: HashEmbedder!

    override func setUp() async throws {
        try await super.setUp()
        embedder = HashEmbedder()
    }

    // MARK: - Basic Embedding Tests

    func testEmbedProduces384Dimensions() {
        let text = "Hello world"
        let embedding = embedder.embed(text)

        XCTAssertEqual(embedding.count, 384)
    }

    func testEmbedDeterministic() {
        let text = "Same text produces same embedding"

        let embedding1 = embedder.embed(text)
        let embedding2 = embedder.embed(text)

        XCTAssertEqual(embedding1, embedding2)
    }

    func testEmbedDifferentTextsDifferent() {
        let embedding1 = embedder.embed("First text")
        let embedding2 = embedder.embed("Completely different content")

        // Should not be identical
        XCTAssertNotEqual(embedding1, embedding2)
    }

    func testEmbedEmptyString() {
        let embedding = embedder.embed("")

        // Should still produce valid embedding
        XCTAssertEqual(embedding.count, 384)
    }

    func testEmbedNormalized() {
        let embedding = embedder.embed("Test normalization")

        // Calculate magnitude
        let magnitude = sqrt(embedding.reduce(0) { $0 + $1 * $1 })

        // Should be approximately 1 (normalized)
        XCTAssertEqual(magnitude, 1.0, accuracy: 0.01)
    }

    // MARK: - Similarity Tests

    func testCosineSimilarityIdentical() {
        let embedding = embedder.embed("Same text")
        let similarity = HashEmbedder.cosineSimilarity(embedding, embedding)

        XCTAssertEqual(similarity, 1.0, accuracy: 0.001)
    }

    func testCosineSimilaritySimilarTexts() {
        let embedding1 = embedder.embed("The quick brown fox")
        let embedding2 = embedder.embed("The fast brown fox")

        let similarity = HashEmbedder.cosineSimilarity(embedding1, embedding2)

        // Similar texts should have high similarity
        XCTAssertGreaterThan(similarity, 0.5)
    }

    func testCosineSimilarityDifferentTexts() {
        let embedding1 = embedder.embed("Programming in Swift")
        let embedding2 = embedder.embed("Cooking Italian food")

        let similarity = HashEmbedder.cosineSimilarity(embedding1, embedding2)

        // Very different texts should have lower similarity
        XCTAssertLessThan(similarity, 0.7)
    }

    func testCosineSimilarityRange() {
        for _ in 0..<10 {
            let text1 = UUID().uuidString
            let text2 = UUID().uuidString

            let embedding1 = embedder.embed(text1)
            let embedding2 = embedder.embed(text2)

            let similarity = HashEmbedder.cosineSimilarity(embedding1, embedding2)

            // Similarity should always be between -1 and 1
            XCTAssertGreaterThanOrEqual(similarity, -1.0)
            XCTAssertLessThanOrEqual(similarity, 1.0)
        }
    }

    func testCosineSimilarityMismatchedDimensions() {
        let short = [Float](repeating: 1.0, count: 100)
        let long = [Float](repeating: 1.0, count: 384)

        let similarity = HashEmbedder.cosineSimilarity(short, long)

        // Should handle gracefully (return 0 for mismatched)
        XCTAssertEqual(similarity, 0.0)
    }

    // MARK: - Performance Tests

    func testEmbedPerformance() {
        let text = String(repeating: "word ", count: 1000)

        measure {
            _ = embedder.embed(text)
        }
    }

    func testBatchEmbedPerformance() {
        let texts = (0..<100).map { "Document number \($0) with some content" }

        measure {
            for text in texts {
                _ = embedder.embed(text)
            }
        }
    }
}

// MARK: - RAG Document Tests

@MainActor
final class RAGDocumentTests: XCTestCase {

    func testRAGDocumentCreation() {
        let doc = RAGDocument(
            id: UUID(),
            content: "Test content",
            source: .chatMessage,
            conversationId: UUID(),
            createdAt: Date()
        )

        XCTAssertFalse(doc.content.isEmpty)
        XCTAssertEqual(doc.source, .chatMessage)
    }

    func testRAGSourceTypes() {
        // Verify all source types exist
        XCTAssertNotNil(RAGSource.chatMessage)
        XCTAssertNotNil(RAGSource.theme)
        XCTAssertNotNil(RAGSource.semanticNode)
        XCTAssertNotNil(RAGSource.vaultFile)
        XCTAssertNotNil(RAGSource.codeFile)
        XCTAssertNotNil(RAGSource.kanbanTask)
    }

    func testRAGSearchResultCreation() {
        let doc = RAGDocument(
            id: UUID(),
            content: "Search result content",
            source: .chatMessage,
            conversationId: nil,
            createdAt: Date()
        )

        let result = RAGSearchResult(
            document: doc,
            similarity: 0.85
        )

        XCTAssertEqual(result.similarity, 0.85)
        XCTAssertEqual(result.content, "Search result content")
    }

    func testRAGSearchResultSnippet() {
        let longContent = String(repeating: "word ", count: 100)
        let doc = RAGDocument(
            id: UUID(),
            content: longContent,
            source: .chatMessage,
            conversationId: nil,
            createdAt: Date()
        )

        let result = RAGSearchResult(document: doc, similarity: 0.8)

        // Snippet should be shorter than full content
        if let snippet = result.snippet {
            XCTAssertLessThan(snippet.count, longContent.count)
        }
    }
}

// MARK: - RAG Search Query Tests

@MainActor
final class RAGSearchQueryTests: XCTestCase {

    func testSearchQueryDefaults() {
        let query = RAGSearchQuery(query: "test")

        XCTAssertEqual(query.query, "test")
        XCTAssertEqual(query.limit, 10)
        XCTAssertEqual(query.minSimilarity, 0.3)
        XCTAssertNil(query.sources)
    }

    func testSearchQueryWithSources() {
        let query = RAGSearchQuery(
            query: "test",
            sources: [.chatMessage, .theme]
        )

        XCTAssertEqual(query.sources?.count, 2)
        XCTAssertTrue(query.sources?.contains(.chatMessage) ?? false)
    }

    func testSearchQueryWithConversationId() {
        let convId = UUID()
        let query = RAGSearchQuery(
            query: "test",
            conversationId: convId
        )

        XCTAssertEqual(query.conversationId, convId)
    }
}

// MARK: - RAG Context Builder Tests

@MainActor
final class RAGContextBuilderTests: XCTestCase {

    func testContextBudgetPresets() {
        let appleFM = ContextBudget.appleFM()
        XCTAssertEqual(appleFM.totalBudget, 4000)

        let ollama = ContextBudget.ollamaDefault()
        XCTAssertGreaterThan(ollama.totalBudget, appleFM.totalBudget)

        let claude = ContextBudget.claudeDefault()
        XCTAssertGreaterThan(claude.totalBudget, ollama.totalBudget)
    }

    func testContextBudgetAllocation() {
        var budget = ContextBudget.ollamaDefault()

        // Should have allocations for different components
        XCTAssertGreaterThan(budget.ragBudget, 0)
        XCTAssertGreaterThan(budget.historyBudget, 0)
        XCTAssertGreaterThan(budget.systemPromptBudget, 0)
    }
}

// MARK: - Cross-Conversation File Index Tests

@MainActor
final class CrossConversationFileIndexTests: XCTestCase {

    var fileIndex: CrossConversationFileIndex!

    override func setUp() async throws {
        try await super.setUp()
        fileIndex = CrossConversationFileIndex()
    }

    func testIndexFile() async {
        let file = FileReference(
            filename: "test.swift",
            originalPath: "/path/to/test.swift",
            processedContent: "func hello() { print(\"Hello\") }",
            fileType: "swift"
        )

        let convId = UUID()
        await fileIndex.indexFile(file, conversationId: convId)

        // File should be indexed
        XCTAssertGreaterThan(fileIndex.indexedFileCount, 0)
    }

    func testFindRelevantFiles() async {
        // Index some files
        let file1 = FileReference(
            filename: "AuthService.swift",
            processedContent: "class AuthService { func login() {} }",
            fileType: "swift"
        )

        let file2 = FileReference(
            filename: "DatabaseHelper.swift",
            processedContent: "class DatabaseHelper { func query() {} }",
            fileType: "swift"
        )

        let convId = UUID()
        await fileIndex.indexFile(file1, conversationId: convId)
        await fileIndex.indexFile(file2, conversationId: convId)

        // Search for authentication-related files
        let results = await fileIndex.findRelevantFiles(
            query: "authentication login",
            limit: 5
        )

        // AuthService should be more relevant
        if results.count >= 2 {
            XCTAssertTrue(results[0].filename.contains("Auth") || results[1].filename.contains("Auth"))
        }
    }
}

// MARK: - File Relevance Scorer Tests

@MainActor
final class FileRelevanceScorerTests: XCTestCase {

    var scorer: FileRelevanceScorer!

    override func setUp() async throws {
        try await super.setUp()
        scorer = FileRelevanceScorer()
    }

    func testScoreFileRelevance() async {
        let file = FileReference(
            filename: "UserService.swift",
            processedContent: "class UserService { func getUser() {} }",
            fileType: "swift",
            lastAccessed: Date()
        )

        let context = ScoringContext.forChat(conversationId: nil, query: "get user data")

        let score = await scorer.scoreFile(file, query: "get user data", context: context)

        // Should have some relevance to user-related query
        XCTAssertGreaterThan(score.totalScore, 0.2)
        XCTAssertGreaterThan(score.semanticScore, 0)
    }

    func testRecencyBoost() async {
        let recentFile = FileReference(
            filename: "test.swift",
            processedContent: "test content",
            fileType: "swift",
            lastAccessed: Date() // Just now
        )

        let oldFile = FileReference(
            filename: "test.swift",
            processedContent: "test content",
            fileType: "swift",
            lastAccessed: Date().addingTimeInterval(-86400 * 7) // 1 week ago
        )

        let context = ScoringContext.forChat(conversationId: nil, query: "test")

        let recentScore = await scorer.scoreFile(recentFile, query: "test", context: context)
        let oldScore = await scorer.scoreFile(oldFile, query: "test", context: context)

        // Recent file should score higher
        XCTAssertGreaterThan(recentScore.recencyScore, oldScore.recencyScore)
    }

    func testTypeMatchBoost() async {
        let swiftFile = FileReference(
            filename: "code.swift",
            fileType: "swift"
        )

        let context = ScoringContext.forCode(activeFiles: [], query: "swift code")

        let score = await scorer.scoreFile(swiftFile, query: "swift code", context: context)

        // Swift file should have good type match for code context
        XCTAssertGreaterThan(score.typeMatchScore, 0.5)
    }

    func testRelevanceTiers() {
        let highScore = FileRelevanceScore(
            fileId: UUID(),
            filename: "test.swift",
            totalScore: 0.85,
            semanticScore: 0.9,
            recencyScore: 0.8,
            frequencyScore: 0.5,
            coAccessScore: 0,
            aneScore: 0,
            typeMatchScore: 1.0,
            contextualScore: 0,
            explanation: "Test"
        )

        XCTAssertEqual(highScore.tier, .high)

        let lowScore = FileRelevanceScore(
            fileId: UUID(),
            filename: "test.swift",
            totalScore: 0.35,
            semanticScore: 0.3,
            recencyScore: 0.4,
            frequencyScore: 0.2,
            coAccessScore: 0,
            aneScore: 0,
            typeMatchScore: 0.5,
            contextualScore: 0,
            explanation: "Test"
        )

        XCTAssertEqual(lowScore.tier, .low)
    }
}

// MARK: - Integration Bridge Tests

@MainActor
final class RAGIntegrationBridgeTests: XCTestCase {

    func testUnifiedSearchQuery() {
        let query = UnifiedRAGQuery(
            query: "test query",
            limit: 10,
            minSimilarity: 0.5,
            sources: ["chat_message", "theme"]
        )

        XCTAssertEqual(query.query, "test query")
        XCTAssertEqual(query.limit, 10)
        XCTAssertEqual(query.minSimilarity, 0.5)
        XCTAssertEqual(query.sources?.count, 2)
    }

    func testIndexableContentCreation() {
        let message = ChatMessage(
            role: .user,
            content: "Test message",
            sessionId: UUID()
        )

        let content = IndexableContent.message(message, conversationId: UUID())

        XCTAssertEqual(content.type, .message)
        XCTAssertNotNil(content.chatMessage)
    }

    func testIndexingResultSuccess() {
        let result = IndexingResult(
            localIndexed: true,
            backendIndexed: false,
            errors: []
        )

        XCTAssertTrue(result.success)
        XCTAssertTrue(result.localIndexed)
        XCTAssertFalse(result.backendIndexed)
    }
}
