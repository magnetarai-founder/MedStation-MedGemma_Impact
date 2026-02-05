//
//  WorkspaceAIService.swift
//  MagnetarStudio
//
//  Shared AI service for all Workspace Hub panels.
//  Streams responses from Ollama via the backend API.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "WorkspaceAIService")

// MARK: - AI Action

/// User-facing AI action that maps to a strategy + prompt
enum WorkspaceAIAction: String, CaseIterable, Identifiable, Sendable {
    // Text actions (Notes/Docs)
    case improveWriting = "Improve Writing"
    case makeShorter = "Make Shorter"
    case makeLonger = "Make Longer"
    case fixGrammar = "Fix Grammar"
    case toneProfessional = "Professional Tone"
    case toneCasual = "Casual Tone"
    case summarize = "Summarize"
    case askAI = "Ask AI"

    // Sheets actions
    case generateFormula = "Generate Formula"
    case explainFormula = "Explain Formula"

    // Voice actions
    case cleanTranscription = "Clean Up Transcription"
    case summarizeRecording = "Summarize Recording"

    var id: String { rawValue }

    var icon: String {
        switch self {
        case .improveWriting: return "wand.and.stars"
        case .makeShorter: return "arrow.down.right.and.arrow.up.left"
        case .makeLonger: return "arrow.up.left.and.arrow.down.right"
        case .fixGrammar: return "textformat.abc"
        case .toneProfessional: return "briefcase"
        case .toneCasual: return "face.smiling"
        case .summarize: return "text.justify.left"
        case .askAI: return "sparkles"
        case .generateFormula: return "function"
        case .explainFormula: return "questionmark.circle"
        case .cleanTranscription: return "waveform.badge.magnifyingglass"
        case .summarizeRecording: return "text.justify.left"
        }
    }

    /// Which panel categories this action belongs to
    var category: ActionCategory {
        switch self {
        case .improveWriting, .makeShorter, .makeLonger, .fixGrammar,
             .toneProfessional, .toneCasual, .summarize, .askAI:
            return .text
        case .generateFormula, .explainFormula:
            return .sheets
        case .cleanTranscription, .summarizeRecording:
            return .voice
        }
    }

    enum ActionCategory {
        case text
        case sheets
        case voice
    }
}

// MARK: - Workspace AI Service

/// Shared AI service for Workspace Hub panels.
/// Calls Ollama via the backend API and streams responses.
@MainActor
@Observable
final class WorkspaceAIService {
    static let shared = WorkspaceAIService()

    // MARK: - State

    var isGenerating: Bool = false
    var currentResponse: String = ""
    var error: String?

    /// Model to use for workspace AI (defaults to llama3.2)
    var modelId: String {
        get { UserDefaults.standard.string(forKey: "workspace.ai.modelId") ?? "llama3.2:latest" }
        set { UserDefaults.standard.set(newValue, forKey: "workspace.ai.modelId") }
    }

    private var activeTask: Task<Void, Never>?
    private var activeStreamingTask: ApiClient.StreamingTask?

    private init() {}

    // MARK: - Request Body

    private struct OllamaRequest: Encodable {
        let model: String
        let prompt: String
        let system: String
        let stream: Bool
        let options: Options

        struct Options: Encodable {
            let temperature: Float
        }
    }

    // MARK: - Generation

    /// Generate an AI response using a strategy, returning an AsyncStream of tokens.
    func generate(
        action: WorkspaceAIAction,
        input: String,
        context: String = "",
        strategy: WorkspaceAIStrategy
    ) -> AsyncStream<String> {
        cancel()
        isGenerating = true
        currentResponse = ""
        error = nil

        let prompt = strategy.formatPrompt(action: action, userInput: input, context: context)
        let systemPrompt = strategy.systemPrompt

        logger.debug("[WorkspaceAI] Starting generation: \(action.rawValue) with model \(self.modelId)")

        return AsyncStream { [weak self] continuation in
            guard let self else {
                continuation.finish()
                return
            }

            let task = Task { @MainActor [weak self] in
                guard let self else {
                    continuation.finish()
                    return
                }

                do {
                    try await self.streamFromOllama(
                        systemPrompt: systemPrompt,
                        prompt: prompt,
                        onToken: { token in
                            Task { @MainActor [weak self] in
                                self?.currentResponse += token
                            }
                            continuation.yield(token)
                        },
                        onDone: { [weak self] in
                            Task { @MainActor [weak self] in
                                self?.isGenerating = false
                                logger.debug("[WorkspaceAI] Generation complete (\(self?.currentResponse.count ?? 0) chars)")
                            }
                            continuation.finish()
                        }
                    )
                } catch {
                    Task { @MainActor [weak self] in
                        self?.isGenerating = false
                        self?.error = error.localizedDescription
                        logger.error("[WorkspaceAI] Generation failed: \(error)")
                    }
                    continuation.finish()
                }
            }

            self.activeTask = task

            continuation.onTermination = { _ in
                task.cancel()
            }
        }
    }

    /// Generate without streaming — returns complete response.
    func generateSync(
        action: WorkspaceAIAction,
        input: String,
        context: String = "",
        strategy: WorkspaceAIStrategy
    ) async -> String {
        cancel()
        isGenerating = true
        currentResponse = ""
        error = nil

        let prompt = strategy.formatPrompt(action: action, userInput: input, context: context)
        let systemPrompt = strategy.systemPrompt

        do {
            let response = try await callOllama(systemPrompt: systemPrompt, prompt: prompt)
            currentResponse = response
            isGenerating = false
            return response
        } catch {
            self.error = error.localizedDescription
            isGenerating = false
            logger.error("[WorkspaceAI] Sync generation failed: \(error)")
            return ""
        }
    }

    /// Cancel any active generation
    func cancel() {
        activeTask?.cancel()
        activeTask = nil
        activeStreamingTask?.cancel()
        activeStreamingTask = nil
        isGenerating = false
        currentResponse = ""
        error = nil
    }

    // MARK: - Workspace Content Indexing

    /// Index all workspace content for semantic search.
    /// Call on app launch and after document saves.
    func indexWorkspaceContent() async {
        let searchService = SemanticSearchService.shared
        let storageBase = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
            .appendingPathComponent("MagnetarStudio/workspace", isDirectory: true)

        // Index notes
        await indexDirectory(
            storageBase.appendingPathComponent("notes"),
            source: .document,
            contentType: "note",
            searchService: searchService
        )

        // Index docs
        await indexDirectory(
            storageBase.appendingPathComponent("docs"),
            source: .document,
            contentType: "doc",
            searchService: searchService
        )

        // Index voice transcriptions
        await indexDirectory(
            storageBase.appendingPathComponent("voice"),
            source: .document,
            contentType: "voice_transcription",
            searchService: searchService
        )

        logger.debug("[WorkspaceAI] Workspace content indexing complete")
    }

    private func indexDirectory(
        _ dir: URL,
        source: RAGSource,
        contentType: String,
        searchService: SemanticSearchService
    ) async {
        let files: [URL]
        do {
            files = try FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)
                .filter({ $0.pathExtension == "json" && !$0.lastPathComponent.hasPrefix("_") })
        } catch {
            logger.error("Failed to list directory for indexing: \(error.localizedDescription)")
            return
        }

        for file in files {
            let data: Data
            do {
                data = try Data(contentsOf: file)
            } catch {
                logger.debug("Failed to read \(file.lastPathComponent) for indexing: \(error.localizedDescription)")
                continue
            }

            guard let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any],
                  let title = json["title"] as? String,
                  let content = json["content"] as? String,
                  !content.isEmpty else { continue }

            let request = RAGIndexRequest(
                content: content,
                source: source,
                metadata: RAGDocumentMetadata(
                    documentId: UUID(),
                    title: title,
                    contentType: contentType
                )
            )

            do {
                _ = try await searchService.index(request: request)
            } catch {
                logger.debug("Failed to index \(file.lastPathComponent): \(error.localizedDescription)")
            }
        }
    }

    // MARK: - Ollama Integration

    private func streamFromOllama(
        systemPrompt: String,
        prompt: String,
        onToken: @escaping (String) -> Void,
        onDone: @escaping () -> Void
    ) async throws {
        let body = OllamaRequest(
            model: modelId,
            prompt: prompt,
            system: systemPrompt,
            stream: true,
            options: .init(temperature: 0.7)
        )

        let streamingTask = try ApiClient.shared.makeStreamingTask(
            path: "/v1/chat/ollama/generate",
            method: .post,
            jsonBody: body,
            onContent: { content in
                // Ollama streams JSON objects with "response" field
                guard let data = content.data(using: .utf8) else { return }
                do {
                    if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                       let token = json["response"] as? String {
                        onToken(token)
                    }
                } catch {
                    logger.debug("Skipped unparseable stream chunk: \(error.localizedDescription)")
                }
            },
            onDone: {
                onDone()
            },
            onError: { error in
                logger.error("[WorkspaceAI] Stream error: \(error)")
                onDone()
            }
        )

        self.activeStreamingTask = streamingTask
    }

    private func callOllama(systemPrompt: String, prompt: String) async throws -> String {
        struct OllamaGenerateResponse: Codable {
            let response: String
        }

        let body: [String: Any] = [
            "model": modelId,
            "prompt": prompt,
            "system": systemPrompt,
            "stream": false,
            "options": ["temperature": 0.7]
        ]

        let response: OllamaGenerateResponse = try await ApiClient.shared.request(
            path: "/v1/chat/ollama/generate",
            method: .post,
            jsonBody: body
        )

        return response.response
    }
}
