//
//  MedicalAIService.swift
//  MedStation
//
//  Singleton service managing MedGemma model lifecycle and medical inference.
//  Handles auto-download via Ollama, streaming/non-streaming inference,
//  and medical-specific prompt engineering.
//
//  MedGemma Impact Challenge (Kaggle 2026) — Edge AI on-device inference.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "MedicalAIService")

// MARK: - Medical AI Service

@MainActor
@Observable
final class MedicalAIService {
    static let shared = MedicalAIService()

    // MARK: - State

    var isGenerating: Bool = false
    var currentResponse: String = ""
    var error: String?
    var modelStatus: ModelStatus = .notInstalled

    enum ModelStatus: Equatable, Sendable {
        case notInstalled
        case downloading(progress: Double)
        case installed
        case ready
        case failed(String)
    }

    private let medgemmaModelId = "alibayram/medgemma:4b"
    private var activeTask: Task<Void, Never>?
    private var activeStreamingCancel: (() -> Void)?

    private init() {}

    // MARK: - Model Management

    func ensureModelReady() async {
        guard modelStatus != .ready && modelStatus != .installed else { return }

        logger.info("Checking MedGemma model status...")

        do {
            let models: [OllamaModelInfo] = try await ApiClient.shared.request(
                path: "/v1/chat/ollama/models",
                method: .get
            )

            let isInstalled = models.contains { $0.name.contains("medgemma") }

            if isInstalled {
                modelStatus = .ready
                logger.info("MedGemma model found locally")
                return
            }

            logger.info("MedGemma not found, starting download...")
            await downloadModel()

        } catch {
            // Model list endpoint may not return standard envelope — try Ollama directly
            logger.warning("Model check via API failed, attempting direct Ollama list: \(error.localizedDescription)")
            await downloadModel()
        }
    }

    private func downloadModel() async {
        modelStatus = .downloading(progress: 0)

        do {
            for try await progress in OllamaService.shared.pullModel(modelName: medgemmaModelId) {
                switch progress.status {
                case "progress":
                    // Parse percentage from message if available (e.g. "pulling layer 45%")
                    let pct: Double
                    if let range = progress.message.range(of: #"\d+"#, options: .regularExpression),
                       let parsed = Double(progress.message[range]), parsed > 0, parsed <= 100 {
                        pct = parsed / 100.0
                    } else {
                        pct = 0.5
                    }
                    modelStatus = .downloading(progress: pct)
                    logger.debug("MedGemma download: \(progress.message)")
                case "completed":
                    modelStatus = .ready
                    logger.info("MedGemma download completed")
                    return
                case "error":
                    throw MedicalAIError.downloadFailed(progress.message)
                default:
                    logger.debug("MedGemma download status: \(progress.status) — \(progress.message)")
                }
            }
            // Stream finished without explicit "completed" — assume success
            if modelStatus != .ready {
                modelStatus = .ready
            }
        } catch {
            modelStatus = .failed(error.localizedDescription)
            self.error = "Download failed: \(error.localizedDescription)"
            logger.error("MedGemma download failed: \(error)")
        }
    }

    // MARK: - Non-Streaming Inference (for workflow steps)

    func generateWorkflowStep(stepPrompt: String, patientContext: String) async throws -> String {
        guard modelStatus == .ready || modelStatus == .installed else {
            throw MedicalAIError.modelNotReady
        }

        isGenerating = true
        error = nil

        defer { isGenerating = false }

        let systemPrompt = """
        You are a medical AI assistant powered by MedGemma. You provide evidence-based medical reasoning \
        for triage, symptom analysis, and differential diagnosis.

        CRITICAL DISCLAIMERS:
        - This is for educational and informational purposes only
        - Not a substitute for professional medical advice, diagnosis, or treatment
        - Always seek advice from qualified healthcare providers for medical concerns
        - In emergency situations, call 911 or local emergency services immediately

        Output Format: Provide structured, clear medical reasoning with supporting evidence.
        """

        let fullPrompt = """
        Patient Context:
        \(patientContext)

        Task:
        \(stepPrompt)
        """

        do {
            let response = try await callOllama(systemPrompt: systemPrompt, prompt: fullPrompt)
            return response
        } catch {
            self.error = error.localizedDescription
            logger.error("Medical inference failed: \(error)")
            throw error
        }
    }

    // MARK: - Streaming Inference (for interactive chat)

    func streamMedicalResponse(
        prompt: String,
        patientContext: String,
        onToken: @escaping (String) -> Void,
        onDone: @escaping () -> Void
    ) async throws {
        guard modelStatus == .ready || modelStatus == .installed else {
            throw MedicalAIError.modelNotReady
        }

        isGenerating = true
        currentResponse = ""
        error = nil

        let systemPrompt = """
        You are a medical AI assistant powered by MedGemma. Provide clear, evidence-based medical information.

        DISCLAIMER: This is educational information only. Not medical advice. Consult healthcare professionals.
        """

        let fullPrompt: String
        if patientContext.isEmpty {
            fullPrompt = prompt
        } else {
            fullPrompt = """
            \(patientContext)

            \(prompt)
            """
        }

        let body = OllamaStreamRequest(
            model: medgemmaModelId,
            prompt: fullPrompt,
            system: systemPrompt,
            stream: true,
            options: .init(temperature: 0.3, numCtx: 8192)
        )

        do {
            let streamingTask = try ApiClient.shared.makeStreamingTask(
                path: "/v1/chat/ollama/generate",
                method: .post,
                jsonBody: body,
                onContent: { [weak self] content in
                    guard let data = content.data(using: .utf8) else { return }
                    do {
                        if let json = try JSONSerialization.jsonObject(with: data) as? [String: Any],
                           let token = json["response"] as? String {
                            Task { @MainActor [weak self] in
                                self?.currentResponse += token
                            }
                            onToken(token)
                        }
                    } catch {
                        logger.debug("Skipped unparseable medical stream chunk: \(error.localizedDescription)")
                    }
                },
                onDone: { [weak self] in
                    Task { @MainActor [weak self] in
                        self?.isGenerating = false
                        if let err = self?.error {
                            logger.debug("Medical stream done with error: \(err)")
                        }
                    }
                    onDone()
                },
                onError: { error in
                    logger.error("Medical stream error: \(error)")
                    onDone()
                }
            )

            // Store cancel handle for cancellation support
            activeStreamingCancel = streamingTask.cancel
            streamingTask.task.resume()

        } catch {
            isGenerating = false
            self.error = error.localizedDescription
            throw error
        }
    }

    func cancel() {
        activeTask?.cancel()
        activeTask = nil
        activeStreamingCancel?()
        activeStreamingCancel = nil
        isGenerating = false
        currentResponse = ""
        error = nil
    }

    // MARK: - Ollama Non-Streaming

    private func callOllama(systemPrompt: String, prompt: String) async throws -> String {
        struct OllamaGenerateResponse: Codable, Sendable {
            let response: String
        }

        let body: [String: Any] = [
            "model": medgemmaModelId,
            "prompt": prompt,
            "system": systemPrompt,
            "stream": false,
            "options": [
                "temperature": 0.3,
                "num_ctx": 8192
            ]
        ]

        let response: OllamaGenerateResponse = try await ApiClient.shared.request(
            path: "/v1/chat/ollama/generate",
            method: .post,
            jsonBody: body
        )

        return response.response
    }
}

// MARK: - Request Types

private struct OllamaStreamRequest: Encodable, Sendable {
    let model: String
    let prompt: String
    let system: String
    let stream: Bool
    let options: Options

    struct Options: Encodable, Sendable {
        let temperature: Float
        let numCtx: Int

        enum CodingKeys: String, CodingKey {
            case temperature
            case numCtx = "num_ctx"
        }
    }
}

// MARK: - Errors

enum MedicalAIError: LocalizedError {
    case modelNotReady
    case downloadFailed(String)
    case inferenceFailed(String)

    var errorDescription: String? {
        switch self {
        case .modelNotReady:
            return "MedGemma model is not ready. Please wait for download to complete."
        case .downloadFailed(let msg):
            return "Model download failed: \(msg)"
        case .inferenceFailed(let msg):
            return "Medical inference failed: \(msg)"
        }
    }
}
