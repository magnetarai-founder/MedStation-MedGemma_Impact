//
//  MedicalAIService.swift
//  MedStation
//
//  Singleton service managing MedGemma model lifecycle and medical inference.
//  Uses MLX Swift for native on-device inference on Apple Silicon.
//  No Python backend, no HTTP, App Sandbox compliant.
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
    var modelStatus: ModelStatus = .unknown

    enum ModelStatus: Equatable, Sendable {
        case unknown
        case loading
        case ready
        case failed(String)
    }

    private let engine = MLXInferenceEngine.shared
    private var activeStreamTask: Task<Void, Never>?

    private init() {}

    // MARK: - Model Management

    func ensureModelReady() async {
        if modelStatus == .ready { return }

        modelStatus = .loading
        logger.info("Loading MedGemma model via MLX...")

        do {
            try await engine.loadModel()
            modelStatus = .ready
            logger.info("MedGemma model loaded via MLX")
        } catch {
            let message = error.localizedDescription
            modelStatus = .failed(message)
            self.error = "Model load failed: \(message)"
            logger.error("MedGemma model load failed: \(error)")
        }
    }

    // MARK: - Non-Streaming Inference (for workflow steps)

    func generateWorkflowStep(stepPrompt: String, patientContext: String) async throws -> String {
        if modelStatus != .ready {
            await ensureModelReady()
            guard modelStatus == .ready else {
                throw MedicalAIError.modelNotReady
            }
        }

        isGenerating = true
        error = nil
        defer { isGenerating = false }

        let fullPrompt = """
        Patient Context:
        \(patientContext)

        Task:
        \(stepPrompt)
        """

        do {
            let response = try await engine.generate(
                prompt: fullPrompt,
                system: Self.systemPrompt,
                maxTokens: 384,
                temperature: 0.1
            )
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
        onDone: @escaping () -> Void,
        onError: @escaping (Error) -> Void = { _ in }
    ) async throws {
        if modelStatus != .ready {
            await ensureModelReady()
            guard modelStatus == .ready else {
                throw MedicalAIError.modelNotReady
            }
        }

        isGenerating = true
        currentResponse = ""
        error = nil

        let fullPrompt: String
        if patientContext.isEmpty {
            fullPrompt = prompt
        } else {
            fullPrompt = """
            \(patientContext)

            \(prompt)
            """
        }

        activeStreamTask = Task { [weak self] in
            do {
                try await MLXInferenceEngine.shared.stream(
                    prompt: fullPrompt,
                    system: Self.chatSystemPrompt,
                    maxTokens: 1024,
                    temperature: 0.3,
                    onToken: { token in
                        Task { @MainActor in
                            self?.currentResponse += token
                        }
                        onToken(token)
                    }
                )

                await MainActor.run {
                    self?.isGenerating = false
                }
                onDone()

            } catch {
                if !Task.isCancelled {
                    logger.error("Medical stream error: \(error)")
                    await MainActor.run {
                        self?.isGenerating = false
                        self?.error = error.localizedDescription
                    }
                    onError(error)
                }
            }
        }
    }

    func cancel() {
        activeStreamTask?.cancel()
        activeStreamTask = nil
        isGenerating = false
        currentResponse = ""
        error = nil
    }

    // MARK: - System Prompts

    static let systemPrompt = """
    You are a medical AI assistant powered by MedGemma. Provide concise, evidence-based medical reasoning.

    RULES:
    - Use bullet points and short sentences
    - No preambles or disclaimers in your response
    - Be direct and clinical
    - This is for educational purposes only, not medical advice
    """

    static let chatSystemPrompt = """
    You are a medical AI assistant powered by MedGemma. Provide clear, evidence-based medical information.

    DISCLAIMER: This is educational information only. Not medical advice. Consult healthcare professionals.
    """
}

// MARK: - Errors

enum MedicalAIError: LocalizedError {
    case modelNotReady
    case inferenceFailed(String)

    var errorDescription: String? {
        switch self {
        case .modelNotReady:
            return "MedGemma model is not ready. Please wait for it to load."
        case .inferenceFailed(let msg):
            return "Medical inference failed: \(msg)"
        }
    }
}
