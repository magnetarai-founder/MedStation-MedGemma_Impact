//
//  MedicalAIService.swift
//  MedStation
//
//  Singleton service managing MedGemma model lifecycle and medical inference.
//  Calls the local Python backend which runs MedGemma 1.5 4B via HuggingFace
//  Transformers on Apple Silicon (MPS).
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
    var modelStatus: ModelStatus = .unknown

    enum ModelStatus: Equatable, Sendable {
        case unknown
        case loading
        case ready
        case failed(String)
    }

    private let modelName = "google/medgemma-1.5-4b-it"
    private var activeStreamTask: Task<Void, Never>?

    private init() {}

    // MARK: - Model Management

    func ensureModelReady() async {
        if modelStatus == .ready { return }

        modelStatus = .loading
        logger.info("Checking MedGemma model status...")

        // Retry status check — backend may still be starting
        var lastError: Error?
        for attempt in 1...5 {
            do {
                // Check if model is already loaded
                let statusData = try await medgemmaRequest(
                    path: "/v1/chat/medgemma/status",
                    method: "GET",
                    timeout: 10
                )
                let status = try JSONDecoder().decode(MedGemmaStatusResponse.self, from: statusData)

                if status.loaded {
                    modelStatus = .ready
                    logger.info("MedGemma model already loaded on \(status.device ?? "unknown")")
                    return
                }

                // Model not loaded — trigger load (blocks until model is in memory)
                logger.info("Loading MedGemma into memory (this takes ~30s on M1, ~15s on M3+)...")
                let loadData = try await medgemmaRequest(
                    path: "/v1/chat/medgemma/load",
                    method: "POST",
                    timeout: 120
                )
                let loadResult = try JSONDecoder().decode(MedGemmaLoadResponse.self, from: loadData)

                if loadResult.status == "loaded" {
                    modelStatus = .ready
                    logger.info("MedGemma loaded on \(loadResult.device ?? "unknown")")
                } else {
                    modelStatus = .failed(loadResult.message ?? "Unknown error")
                    self.error = loadResult.message
                }
                return

            } catch {
                lastError = error
                if attempt < 5 {
                    logger.debug("MedGemma status check failed (attempt \(attempt)/5), retrying in 2s...")
                    try? await Task.sleep(nanoseconds: 2_000_000_000)
                }
            }
        }

        // All retries exhausted
        modelStatus = .failed(lastError?.localizedDescription ?? "Backend not reachable")
        self.error = "Model load failed: \(lastError?.localizedDescription ?? "Backend not reachable")"
        logger.error("MedGemma model check/load failed after 5 attempts: \(String(describing: lastError))")
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

        let request = MedGemmaGenerateRequest(
            prompt: fullPrompt,
            system: Self.systemPrompt,
            maxTokens: 384,
            temperature: 0.1,
            stream: false
        )

        do {
            let encoder = JSONEncoder()
            let body = try encoder.encode(request)

            let responseData = try await medgemmaRequest(
                path: "/v1/chat/medgemma/generate",
                method: "POST",
                body: body,
                timeout: 300
            )

            let result = try JSONDecoder().decode(MedGemmaGenerateResponse.self, from: responseData)
            return result.response

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

        let request = MedGemmaGenerateRequest(
            prompt: fullPrompt,
            system: Self.chatSystemPrompt,
            maxTokens: 1024,
            temperature: 0.3,
            stream: true
        )

        // Build URL request manually for streaming with longer timeout
        let baseURL = APIConfiguration.shared.baseURL
        guard let url = URL(string: "\(baseURL)/v1/chat/medgemma/generate") else {
            isGenerating = false
            throw MedicalAIError.inferenceFailed("Invalid URL")
        }

        var urlRequest = URLRequest(url: url)
        urlRequest.httpMethod = "POST"
        urlRequest.timeoutInterval = 300
        urlRequest.setValue("application/json", forHTTPHeaderField: "Content-Type")
        urlRequest.httpBody = try JSONEncoder().encode(request)

        // Stream using URLSession async bytes (ndjson format)
        activeStreamTask = Task { [weak self] in
            do {
                let (bytes, response) = try await URLSession.shared.bytes(for: urlRequest)

                guard let httpResponse = response as? HTTPURLResponse,
                      (200...299).contains(httpResponse.statusCode) else {
                    throw MedicalAIError.inferenceFailed("Server returned error")
                }

                for try await line in bytes.lines {
                    guard !Task.isCancelled else { break }
                    guard !line.isEmpty,
                          let lineData = line.data(using: .utf8) else { continue }

                    if let json = try? JSONSerialization.jsonObject(with: lineData) as? [String: Any] {
                        if let token = json["token"] as? String {
                            await MainActor.run {
                                self?.currentResponse += token
                            }
                            onToken(token)
                        }
                        if let done = json["done"] as? Bool, done {
                            break
                        }
                    }
                }

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
                    onDone()
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

    // MARK: - HTTP Helper

    private func medgemmaRequest(
        path: String,
        method: String = "POST",
        body: Data? = nil,
        timeout: TimeInterval = 300
    ) async throws -> Data {
        let baseURL = APIConfiguration.shared.baseURL
        guard let url = URL(string: "\(baseURL)\(path)") else {
            throw MedicalAIError.inferenceFailed("Invalid URL: \(baseURL)\(path)")
        }

        var request = URLRequest(url: url)
        request.httpMethod = method
        request.timeoutInterval = timeout
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")

        if let body = body {
            request.httpBody = body
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw MedicalAIError.inferenceFailed("Invalid response")
        }

        guard (200...299).contains(httpResponse.statusCode) else {
            let message = String(data: data, encoding: .utf8) ?? "HTTP \(httpResponse.statusCode)"
            throw MedicalAIError.inferenceFailed(message)
        }

        return data
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

// MARK: - Request/Response Types

private struct MedGemmaGenerateRequest: Encodable {
    let prompt: String
    let system: String
    let maxTokens: Int
    let temperature: Float
    let stream: Bool

    enum CodingKeys: String, CodingKey {
        case prompt, system, stream, temperature
        case maxTokens = "max_tokens"
    }
}

private struct MedGemmaGenerateResponse: Decodable {
    let response: String
    let model: String?
}

private struct MedGemmaStatusResponse: Decodable {
    let loaded: Bool
    let device: String?
    let model: String?
}

private struct MedGemmaLoadResponse: Decodable {
    let status: String
    let device: String?
    let message: String?
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
