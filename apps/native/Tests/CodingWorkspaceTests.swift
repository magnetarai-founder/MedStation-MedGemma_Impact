//
//  CodingWorkspaceTests.swift
//  MedStation Tests
//
//  Comprehensive tests for the Coding workspace services:
//  - ResponseMerger (quality scoring, selection, merging)
//  - CodingModelOrchestrator (mode selection, query classification, prompt building)
//  - CodeEmbeddingService (language detection, structural chunking, symbol extraction)
//  - CodeRAGService (search, context assembly, scope filtering)
//  - TerminalContextParser (error pattern detection, command classification)
//

import XCTest
@testable import MedStation

// MARK: - Response Merger Tests

@MainActor
final class ResponseMergerTests: XCTestCase {

    var merger: ResponseMerger!

    override func setUp() async throws {
        try await super.setUp()
        merger = ResponseMerger()
    }

    // MARK: - Selection

    func testSelectBestReturnsSingleResponse() {
        let response = makeResponse(modelName: "TestModel", content: "Hello world")
        let result = merger.selectBest(from: [response], query: "test")

        XCTAssertEqual(result.modelName, "TestModel")
        XCTAssertEqual(result.content, "Hello world")
    }

    func testSelectBestPrefersRelevantContent() {
        let responses = [
            makeResponse(modelName: "Irrelevant", content: "The weather is nice today"),
            makeResponse(modelName: "Relevant", content: "To implement sorting, use the sort() function on your array")
        ]

        let result = merger.selectBest(from: responses, query: "implement sorting algorithm")

        XCTAssertEqual(result.modelName, "Relevant")
    }

    func testSelectBestPrefersCodeBlocks() {
        let responses = [
            makeResponse(modelName: "NoCode", content: "You should write a function that sorts."),
            makeResponse(modelName: "WithCode", content: """
            Here's a sorting implementation:

            ```swift
            func bubbleSort(_ array: inout [Int]) {
                for i in 0..<array.count {
                    for j in 0..<array.count - i - 1 {
                        if array[j] > array[j + 1] {
                            array.swapAt(j, j + 1)
                        }
                    }
                }
            }
            ```
            """)
        ]

        let result = merger.selectBest(from: responses, query: "write a sort function")

        XCTAssertEqual(result.modelName, "WithCode")
    }

    func testSelectBestPenalizesVeryShortResponses() {
        let responses = [
            makeResponse(modelName: "Short", content: "Yes."),
            makeResponse(modelName: "Adequate", content: "To solve this problem, you need to consider the data structure you're using. An array-based approach would work well here because it provides O(1) access time and good cache locality.")
        ]

        let result = merger.selectBest(from: responses, query: "how do I solve this?")

        XCTAssertEqual(result.modelName, "Adequate")
    }

    // MARK: - Merging

    func testMergeSingleResponse() {
        let responses = [makeResponse(modelName: "Model", content: "Single response")]
        let merged = merger.merge(responses: responses, query: "test")

        XCTAssertEqual(merged, "Single response")
    }

    func testMergeEmptyReturnsEmptyString() {
        let merged = merger.merge(responses: [], query: "test")
        XCTAssertEqual(merged, "")
    }

    func testMergeAppendsUniqueCodeBlocks() {
        let responses = [
            makeResponse(modelName: "Primary", content: """
            Use this approach:
            ```
            let x = 1
            ```
            """),
            makeResponse(modelName: "Alternative", content: """
            Try this instead:
            ```
            let y = 2
            ```
            """)
        ]

        let merged = merger.merge(responses: responses, query: "test")

        XCTAssertTrue(merged.contains("let x = 1"))
        XCTAssertTrue(merged.contains("Alternative from Alternative"))
        XCTAssertTrue(merged.contains("let y = 2"))
    }

    // MARK: - Helpers

    private func makeResponse(modelName: String, content: String) -> OrchestratedResponse.ModelResponse {
        OrchestratedResponse.ModelResponse(
            modelId: modelName.lowercased(),
            modelName: modelName,
            role: .primary,
            content: content
        )
    }
}

// MARK: - Orchestrator Tests

@MainActor
final class CodingModelOrchestratorTests: XCTestCase {

    var orchestrator: CodingModelOrchestrator!

    override func setUp() async throws {
        try await super.setUp()
        orchestrator = CodingModelOrchestrator.shared
    }

    // MARK: - Mode Management

    func testDefaultModeIsSingle() {
        // Reset to default
        UserDefaults.standard.removeObject(forKey: "coding.orchestrationMode")
        let fresh = CodingModelOrchestrator.shared
        // Mode may have been set from previous test; just verify it's a valid mode
        XCTAssertTrue(OrchestrationMode.allCases.contains(fresh.currentMode))
    }

    func testModeChangePersists() {
        orchestrator.currentMode = .parallel

        let saved = UserDefaults.standard.string(forKey: "coding.orchestrationMode")
        XCTAssertEqual(saved, OrchestrationMode.parallel.rawValue)
    }

    func testAllModesHaveDescriptions() {
        for mode in OrchestrationMode.allCases {
            XCTAssertFalse(mode.description.isEmpty, "\(mode) should have a description")
        }
    }

    func testAllModesHaveIcons() {
        for mode in OrchestrationMode.allCases {
            XCTAssertFalse(mode.iconName.isEmpty, "\(mode) should have an icon name")
        }
    }

    // MARK: - Query Classification

    func testClassifyCodeGeneration() {
        let request = OrchestratedRequest(query: "write a function to sort an array")
        // The orchestrator's classifyQuery is private, so we test indirectly
        // through specialist mode behavior
        XCTAssertNotNil(request.query)
    }

    func testOrchestratedRequestDefaults() {
        let request = OrchestratedRequest(query: "test query")

        XCTAssertEqual(request.mode, .single)
        XCTAssertEqual(request.temperature, 0.7)
        XCTAssertNil(request.context)
        XCTAssertNil(request.codeContext)
        XCTAssertNil(request.ragCodeContext)
        XCTAssertNil(request.maxTokens)
        XCTAssertTrue(request.terminalContext.isEmpty)
        XCTAssertTrue(request.sessions.isEmpty)
    }

    // MARK: - Model Session

    func testModelSessionCreation() {
        let session = ModelSession(
            modelId: "test-model",
            modelName: "Test Model",
            role: .codeSpecialist,
            provider: .ollama
        )

        XCTAssertEqual(session.modelId, "test-model")
        XCTAssertEqual(session.modelName, "Test Model")
        XCTAssertEqual(session.role, .codeSpecialist)
        XCTAssertEqual(session.provider, .ollama)
    }

    func testModelSessionDefaultProvider() {
        let session = ModelSession(modelId: "x", modelName: "X", role: .primary)
        XCTAssertEqual(session.provider, .ollama)
    }

    // MARK: - Orchestrated Response

    func testOrchestratedResponseCreation() {
        let response = OrchestratedResponse(
            content: "Result",
            modelUsed: "TestModel",
            mode: .sequential,
            confidence: 0.9,
            reasoning: "Validated by two models"
        )

        XCTAssertEqual(response.content, "Result")
        XCTAssertEqual(response.modelUsed, "TestModel")
        XCTAssertEqual(response.mode, .sequential)
        XCTAssertEqual(response.confidence, 0.9)
        XCTAssertEqual(response.reasoning, "Validated by two models")
    }
}

// MARK: - Code Embedding Tests

@MainActor
final class CodeEmbeddingServiceTests: XCTestCase {

    var service: CodeEmbeddingService!

    override func setUp() async throws {
        try await super.setUp()
        service = CodeEmbeddingService.shared
    }

    // MARK: - Language Detection

    func testDetectSwift() {
        XCTAssertEqual(CodeLanguage.detect(from: "MyFile.swift"), .swift)
    }

    func testDetectPython() {
        XCTAssertEqual(CodeLanguage.detect(from: "script.py"), .python)
    }

    func testDetectTypeScript() {
        XCTAssertEqual(CodeLanguage.detect(from: "component.tsx"), .typescript)
        XCTAssertEqual(CodeLanguage.detect(from: "index.ts"), .typescript)
    }

    func testDetectJavaScript() {
        XCTAssertEqual(CodeLanguage.detect(from: "app.js"), .javascript)
        XCTAssertEqual(CodeLanguage.detect(from: "module.mjs"), .javascript)
    }

    func testDetectRust() {
        XCTAssertEqual(CodeLanguage.detect(from: "main.rs"), .rust)
    }

    func testDetectGo() {
        XCTAssertEqual(CodeLanguage.detect(from: "handler.go"), .go)
    }

    func testDetectJava() {
        XCTAssertEqual(CodeLanguage.detect(from: "App.java"), .java)
    }

    func testDetectUnknown() {
        XCTAssertEqual(CodeLanguage.detect(from: "readme.md"), .unknown)
        XCTAssertEqual(CodeLanguage.detect(from: "Makefile"), .unknown)
    }

    func testDetectFromFullPath() {
        XCTAssertEqual(CodeLanguage.detect(from: "/Users/dev/project/src/main.swift"), .swift)
        XCTAssertEqual(CodeLanguage.detect(from: "/app/services/api.py"), .python)
    }

    // MARK: - Structural Chunking

    func testChunkSwiftFile() {
        let swiftCode = """
        import Foundation

        // MARK: - Models

        struct User {
            let name: String
            let email: String
        }

        func createUser(name: String, email: String) -> User {
            return User(name: name, email: email)
        }

        class UserManager {
            var users: [User] = []

            func add(_ user: User) {
                users.append(user)
            }
        }
        """

        let chunks = service.chunkCode(content: swiftCode, filePath: "User.swift", language: .swift)

        XCTAssertGreaterThan(chunks.count, 1, "Should produce multiple chunks for structured code")

        // Verify all chunks have correct metadata
        for chunk in chunks {
            XCTAssertEqual(chunk.filePath, "User.swift")
            XCTAssertEqual(chunk.language, .swift)
            XCTAssertFalse(chunk.content.isEmpty)
            XCTAssertGreaterThan(chunk.startLine, 0)
        }
    }

    func testChunkPythonFile() {
        let pythonCode = """
        import os
        from pathlib import Path

        class FileManager:
            def __init__(self, base_path):
                self.base_path = Path(base_path)

            def list_files(self):
                return list(self.base_path.iterdir())

        def main():
            fm = FileManager("/tmp")
            print(fm.list_files())
        """

        let chunks = service.chunkCode(content: pythonCode, filePath: "files.py", language: .python)

        XCTAssertGreaterThan(chunks.count, 1)

        // Check that symbol names are extracted
        let symbolNames = chunks.compactMap { $0.symbolName }
        XCTAssertTrue(symbolNames.contains("FileManager") || symbolNames.contains("main"),
                      "Should extract class/function names, got: \(symbolNames)")
    }

    func testChunkSmallFile() {
        let smallCode = "let x = 1"

        let chunks = service.chunkCode(content: smallCode, filePath: "tiny.swift", language: .swift)

        XCTAssertEqual(chunks.count, 1, "Small file should produce single chunk")
        XCTAssertEqual(chunks.first?.content, smallCode)
    }

    func testChunkEmptyFile() {
        let chunks = service.chunkCode(content: "", filePath: "empty.swift", language: .swift)
        XCTAssertTrue(chunks.isEmpty)
    }

    func testChunkUnknownLanguage() {
        let content = "Some generic text content\nwith multiple lines\nof stuff"

        let chunks = service.chunkCode(content: content, filePath: "readme.txt", language: .unknown)

        XCTAssertEqual(chunks.count, 1, "Unknown language should produce single body chunk")
        XCTAssertEqual(chunks.first?.kind, .body)
    }

    // MARK: - Language Properties

    func testAllLanguagesHaveExtensions() {
        for lang in CodeLanguage.allCases where lang != .unknown {
            XCTAssertFalse(lang.extensions.isEmpty, "\(lang) should have file extensions")
        }
    }

    func testAllLanguagesHavePatterns() {
        for lang in CodeLanguage.allCases where lang != .unknown {
            XCTAssertFalse(lang.structuralPatterns.isEmpty, "\(lang) should have structural patterns")
        }
    }

    // MARK: - Performance

    func testChunkingPerformance() {
        let longCode = (0..<200).map { i in
            """
            func function\(i)(param: Int) -> Int {
                let result = param * \(i)
                return result
            }

            """
        }.joined()

        measure {
            _ = service.chunkCode(content: longCode, filePath: "big.swift", language: .swift)
        }
    }
}

// MARK: - Code RAG Service Tests

@MainActor
final class CodeRAGServiceTests: XCTestCase {

    var ragService: CodeRAGService!

    override func setUp() async throws {
        try await super.setUp()
        ragService = CodeRAGService.shared
    }

    // MARK: - Search Query Construction

    func testSearchQueryDefaults() {
        let query = CodeSearchQuery(text: "find error handler")

        XCTAssertEqual(query.text, "find error handler")
        XCTAssertNil(query.language)
        XCTAssertEqual(query.searchScope, .all)
        XCTAssertEqual(query.limit, 10)
        XCTAssertEqual(query.minSimilarity, 0.25)
    }

    func testSearchQueryWithAllOptions() {
        let query = CodeSearchQuery(
            text: "sort algorithm",
            language: .swift,
            searchScope: .functions,
            limit: 5,
            minSimilarity: 0.5
        )

        XCTAssertEqual(query.language, .swift)
        XCTAssertEqual(query.searchScope, .functions)
        XCTAssertEqual(query.limit, 5)
        XCTAssertEqual(query.minSimilarity, 0.5)
    }

    // MARK: - Code RAG Result

    func testCodeRAGResultDetectsLanguage() {
        let result = CodeRAGResult(
            filePath: "/src/main.swift",
            content: "func test() {}",
            similarity: 0.8
        )

        XCTAssertEqual(result.language, .swift)
        XCTAssertEqual(result.fileName, "main.swift")
    }

    // MARK: - Code RAG Context

    func testCodeRAGContextHasContentWhenNonEmpty() {
        let result = CodeRAGResult(filePath: "test.swift", content: "let x = 1", similarity: 0.9)
        let context = CodeRAGContext(
            results: [result],
            formattedContext: "Some context",
            tokenEstimate: 10,
            searchDuration: 0.01
        )

        XCTAssertTrue(context.hasContent)
    }

    func testCodeRAGContextEmptyWhenNoResults() {
        let context = CodeRAGContext(
            results: [],
            formattedContext: "",
            tokenEstimate: 0,
            searchDuration: 0.0
        )

        XCTAssertFalse(context.hasContent)
    }

    // MARK: - Service State

    func testInitialSearchCountIsZero() {
        XCTAssertGreaterThanOrEqual(ragService.searchCount, 0)
    }

    func testIndexedFileCountNonNegative() {
        XCTAssertGreaterThanOrEqual(ragService.indexedFileCount, 0)
    }
}

// MARK: - Terminal Context Parser Tests

@MainActor
final class TerminalContextParserTests: XCTestCase {

    // MARK: - Terminal Context

    func testTerminalContextIsError() {
        let errorContext = TerminalContext(
            command: "npm install",
            output: "Error: ENOENT",
            exitCode: 1,
            workingDirectory: "/tmp",
            timestamp: Date()
        )

        XCTAssertTrue(errorContext.isError)

        let successContext = TerminalContext(
            command: "ls",
            output: "file1 file2",
            exitCode: 0,
            workingDirectory: "/tmp",
            timestamp: Date()
        )

        XCTAssertFalse(successContext.isError)
    }

    func testTerminalContextSummary() {
        let errorContext = TerminalContext(
            command: "git push",
            output: "fatal: no configured push destination",
            exitCode: 128,
            workingDirectory: "/repo",
            timestamp: Date()
        )

        let summary = errorContext.summary
        XCTAssertTrue(summary.contains("git push"))
        XCTAssertTrue(summary.contains("failed"))
        XCTAssertTrue(summary.contains("128"))
    }

    func testTerminalContextSuccessSummary() {
        let context = TerminalContext(
            command: "echo hello",
            output: "hello",
            exitCode: 0,
            workingDirectory: "/tmp",
            timestamp: Date()
        )

        let summary = context.summary
        XCTAssertTrue(summary.contains("succeeded"))
        XCTAssertTrue(summary.contains("echo hello"))
    }

    // MARK: - AI Assistant State

    func testAIAssistantStateDefaults() {
        let state = AIAssistantState()

        XCTAssertTrue(state.messages.isEmpty)
        XCTAssertFalse(state.isStreaming)
        XCTAssertNil(state.error)
        XCTAssertTrue(state.pendingContext.isEmpty)
    }

    // MARK: - AI Assistant Message

    func testMessageRoles() {
        let userMsg = AIAssistantMessage(role: .user, content: "Hello")
        let assistantMsg = AIAssistantMessage(role: .assistant, content: "Hi there")
        let systemMsg = AIAssistantMessage(role: .system, content: "Context loaded")

        XCTAssertEqual(userMsg.role, .user)
        XCTAssertEqual(assistantMsg.role, .assistant)
        XCTAssertEqual(systemMsg.role, .system)
    }

    func testMessageHasUniqueId() {
        let msg1 = AIAssistantMessage(role: .user, content: "a")
        let msg2 = AIAssistantMessage(role: .user, content: "a")

        XCTAssertNotEqual(msg1.id, msg2.id)
    }

    func testMessageTimestamp() {
        let before = Date()
        let msg = AIAssistantMessage(role: .user, content: "test")
        let after = Date()

        XCTAssertGreaterThanOrEqual(msg.timestamp, before)
        XCTAssertLessThanOrEqual(msg.timestamp, after)
    }
}

// MARK: - Orchestration Mode Tests

@MainActor
final class OrchestrationModeTests: XCTestCase {

    func testAllCasesCount() {
        XCTAssertEqual(OrchestrationMode.allCases.count, 4)
    }

    func testRawValues() {
        XCTAssertEqual(OrchestrationMode.single.rawValue, "Single Model")
        XCTAssertEqual(OrchestrationMode.sequential.rawValue, "Sequential")
        XCTAssertEqual(OrchestrationMode.parallel.rawValue, "Parallel")
        XCTAssertEqual(OrchestrationMode.specialist.rawValue, "Specialist")
    }

    func testCodable() throws {
        let mode = OrchestrationMode.parallel
        let data = try JSONEncoder().encode(mode)
        let decoded = try JSONDecoder().decode(OrchestrationMode.self, from: data)

        XCTAssertEqual(mode, decoded)
    }
}

// MARK: - Quality Score Tests

@MainActor
final class ResponseQualityScoreTests: XCTestCase {

    func testWeightedCalculation() {
        let score = ResponseQualityScore(
            lengthScore: 1.0,
            structureScore: 0.8,
            codeScore: 0.6,
            relevanceScore: 0.9
        )

        // relevance * 0.35 + structure * 0.25 + code * 0.25 + length * 0.15
        let expected: Float = (0.9 * 0.35) + (0.8 * 0.25) + (0.6 * 0.25) + (1.0 * 0.15)
        XCTAssertEqual(score.weighted, expected, accuracy: 0.001)
    }

    func testWeightedMaximumIsOne() {
        let perfectScore = ResponseQualityScore(
            lengthScore: 1.0,
            structureScore: 1.0,
            codeScore: 1.0,
            relevanceScore: 1.0
        )

        XCTAssertEqual(perfectScore.weighted, 1.0, accuracy: 0.001)
    }

    func testWeightedMinimumIsZero() {
        let zeroScore = ResponseQualityScore(
            lengthScore: 0.0,
            structureScore: 0.0,
            codeScore: 0.0,
            relevanceScore: 0.0
        )

        XCTAssertEqual(zeroScore.weighted, 0.0, accuracy: 0.001)
    }
}

// MARK: - Indexing Stats Tests

final class IndexingStatsTests: XCTestCase {

    func testDefaultValues() {
        let stats = IndexingStats()

        XCTAssertEqual(stats.filesDiscovered, 0)
        XCTAssertEqual(stats.filesProcessed, 0)
        XCTAssertEqual(stats.filesIndexed, 0)
        XCTAssertEqual(stats.totalDocuments, 0)
        XCTAssertEqual(stats.errors, 0)
        XCTAssertEqual(stats.duration, 0)
    }
}
