//
//  MLXInferenceEngine.swift
//  MedStation
//
//  On-device LLM inference via MLX Swift. Replaces the Python FastAPI backend
//  with native Apple Silicon inference — no HTTP, no child processes, App Sandbox safe.
//

import Foundation
import MLXLMCommon
import MLXLLM
import MLXVLM
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "MLXInferenceEngine")

@MainActor
@Observable
final class MLXInferenceEngine {

    static let shared = MLXInferenceEngine()

    // MARK: - State

    enum Status: Equatable {
        case idle
        case downloading(Double)
        case loading
        case ready
        case failed(String)
    }

    var status: Status = .idle

    // MARK: - Private

    private var modelContainer: ModelContainer?
    private static let modelId = "mlx-community/medgemma-4b-it-4bit"

    private init() {}

    // MARK: - Model Lifecycle

    func loadModel() async throws {
        if case .ready = status { return }

        status = .downloading(0)
        logger.info("Loading MLX model: \(Self.modelId)")

        // Prefer locally-cached model (e.g. downloaded via `huggingface_hub` Python CLI)
        // before attempting Hub download (which has a 10s timeout — too short for ~3GB).
        let config: ModelConfiguration
        if let localDir = Self.resolveHFCacheDirectory() {
            logger.info("Found cached model at: \(localDir.path)")
            config = ModelConfiguration(
                directory: localDir,
                extraEOSTokens: ["<end_of_turn>"]
            )
        } else {
            config = ModelConfiguration(
                id: Self.modelId,
                extraEOSTokens: ["<end_of_turn>"]
            )
        }

        do {
            // MedGemma uses Gemma3ForConditionalGeneration (VLM architecture)
            let container = try await VLMModelFactory.shared.loadContainer(
                configuration: config
            ) { progress in
                Task { @MainActor in
                    self.status = .downloading(progress.fractionCompleted)
                }
            }

            status = .loading
            self.modelContainer = container
            status = .ready
            logger.info("MLX model loaded successfully")
        } catch {
            let description = String(describing: error)
            status = .failed(description)
            logger.error("MLX model load failed — see stderr for details")
            // os.Logger redacts strings; print to stderr for full diagnostics
            print("[MLXInferenceEngine] Model load error: \(description)", to: &StandardError.shared)
            throw error
        }
    }

    /// Resolve model directory from Python huggingface_hub cache (~/.cache/huggingface/hub/).
    /// Returns the snapshot directory URL if the model is fully downloaded, nil otherwise.
    private static func resolveHFCacheDirectory() -> URL? {
        let home = FileManager.default.homeDirectoryForCurrentUser
        let slug = modelId.replacingOccurrences(of: "/", with: "--")
        let modelDir = home
            .appendingPathComponent(".cache/huggingface/hub")
            .appendingPathComponent("models--\(slug)")

        // refs/main contains the snapshot hash
        let refsMain = modelDir.appendingPathComponent("refs/main")
        guard let hash = try? String(contentsOf: refsMain, encoding: .utf8)
            .trimmingCharacters(in: .whitespacesAndNewlines) else {
            return nil
        }

        let snapshotDir = modelDir.appendingPathComponent("snapshots/\(hash)")

        // Sanity check: config.json must exist
        guard FileManager.default.fileExists(
            atPath: snapshotDir.appendingPathComponent("config.json").path
        ) else {
            return nil
        }

        return snapshotDir
    }

    func unload() {
        modelContainer = nil
        status = .idle
        logger.info("MLX model unloaded")
    }

    // MARK: - Non-Streaming Generation

    func generate(
        prompt: String,
        system: String,
        maxTokens: Int,
        temperature: Float
    ) async throws -> String {
        guard let container = modelContainer else {
            throw MedicalAIError.modelNotReady
        }

        let result = try await container.perform { context in
            let input = try await context.processor.prepare(
                input: UserInput(chat: [
                    .system(system),
                    .user(prompt),
                ])
            )

            let parameters = GenerateParameters(
                maxTokens: maxTokens,
                temperature: temperature
            )

            var fullText = ""

            let stream = try MLXLMCommon.generate(
                input: input,
                parameters: parameters,
                context: context
            )

            for await generation in stream {
                switch generation {
                case .chunk(let text):
                    fullText += text
                case .info, .toolCall:
                    break
                }
            }

            return fullText
        }

        return result
    }

    // MARK: - Streaming Generation

    func stream(
        prompt: String,
        system: String,
        maxTokens: Int,
        temperature: Float,
        onToken: @escaping @Sendable (String) -> Void
    ) async throws {
        guard let container = modelContainer else {
            throw MedicalAIError.modelNotReady
        }

        try await container.perform { context in
            let input = try await context.processor.prepare(
                input: UserInput(chat: [
                    .system(system),
                    .user(prompt),
                ])
            )

            let parameters = GenerateParameters(
                maxTokens: maxTokens,
                temperature: temperature
            )

            let stream = try MLXLMCommon.generate(
                input: input,
                parameters: parameters,
                context: context
            )

            for await generation in stream {
                if Task.isCancelled { break }
                switch generation {
                case .chunk(let text):
                    onToken(text)
                case .info, .toolCall:
                    break
                }
            }
        }
    }
}

// stderr helper — os.Logger redacts dynamic strings
private struct StandardError: TextOutputStream {
    static var shared = StandardError()
    mutating func write(_ string: String) {
        FileHandle.standardError.write(Data(string.utf8))
    }
}
