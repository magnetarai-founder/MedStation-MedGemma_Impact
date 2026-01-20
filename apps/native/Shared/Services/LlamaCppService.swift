import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "LlamaCppService")

/// Service for managing llama.cpp server lifecycle and inference
@MainActor
final class LlamaCppService {
    static let shared = LlamaCppService()

    private init() {}

    private var baseURL: String {
        APIConfiguration.shared.baseURL
    }

    // MARK: - Server Lifecycle

    /// Get server status
    func getStatus() async throws -> LlamaCppStatus {
        guard let url = URL(string: "\(baseURL)/v1/chat/llamacpp/status") else {
            throw LlamaCppError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw LlamaCppError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw LlamaCppError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let envelope = try decoder.decode(SuccessEnvelope<LlamaCppStatus>.self, from: data)
        return envelope.data
    }

    /// Start server with a specific model
    func startServer(modelId: String, timeout: Int = 120) async throws -> LlamaCppStatus {
        guard let url = URL(string: "\(baseURL)/v1/chat/llamacpp/start") else {
            throw LlamaCppError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        // Add auth token
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        // Request body
        let body: [String: Any] = [
            "model_id": modelId,
            "timeout": timeout
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        // Increase timeout for server startup
        request.timeoutInterval = TimeInterval(timeout + 10)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw LlamaCppError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            // Try to parse error message
            if let errorResponse = try? JSONDecoder().decode(ErrorEnvelope.self, from: data) {
                throw LlamaCppError.serverError(errorResponse.message ?? "Unknown error")
            }
            throw LlamaCppError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let envelope = try decoder.decode(SuccessEnvelope<LlamaCppStatus>.self, from: data)

        logger.info("Started llama.cpp with model: \(modelId)")
        return envelope.data
    }

    /// Stop the server
    func stopServer() async throws -> LlamaCppStatus {
        guard let url = URL(string: "\(baseURL)/v1/chat/llamacpp/stop") else {
            throw LlamaCppError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        // Add auth token
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw LlamaCppError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw LlamaCppError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let envelope = try decoder.decode(SuccessEnvelope<LlamaCppStatus>.self, from: data)

        logger.info("Stopped llama.cpp server")
        return envelope.data
    }

    /// Restart the server with same model
    func restartServer() async throws -> LlamaCppStatus {
        guard let url = URL(string: "\(baseURL)/v1/chat/llamacpp/restart") else {
            throw LlamaCppError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.timeoutInterval = 130  // Extra time for restart

        // Add auth token
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw LlamaCppError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw LlamaCppError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let envelope = try decoder.decode(SuccessEnvelope<LlamaCppStatus>.self, from: data)

        logger.info("Restarted llama.cpp server")
        return envelope.data
    }

    // MARK: - Chat Inference

    /// Send chat messages with streaming response
    func chat(messages: [LlamaCppMessage], temperature: Double = 0.7, maxTokens: Int = 2048) -> AsyncThrowingStream<LlamaCppChunk, Error> {
        AsyncThrowingStream { continuation in
            Task {
                do {
                    guard let url = URL(string: "\(baseURL)/v1/chat/llamacpp/chat") else {
                        continuation.finish(throwing: LlamaCppError.invalidURL)
                        return
                    }

                    var request = URLRequest(url: url)
                    request.httpMethod = "POST"
                    request.setValue("application/json", forHTTPHeaderField: "Content-Type")
                    request.setValue("text/event-stream", forHTTPHeaderField: "Accept")

                    // Add auth token
                    if let token = KeychainService.shared.loadToken() {
                        request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
                    }

                    // Request body
                    let body: [String: Any] = [
                        "messages": messages.map { ["role": $0.role, "content": $0.content] },
                        "temperature": temperature,
                        "max_tokens": maxTokens,
                        "stream": true
                    ]
                    request.httpBody = try JSONSerialization.data(withJSONObject: body)

                    // Use async bytes for streaming SSE
                    let (bytes, response) = try await URLSession.shared.bytes(for: request)

                    guard let httpResponse = response as? HTTPURLResponse else {
                        continuation.finish(throwing: LlamaCppError.invalidResponse)
                        return
                    }

                    guard httpResponse.statusCode == 200 else {
                        continuation.finish(throwing: LlamaCppError.httpError(httpResponse.statusCode))
                        return
                    }

                    // Parse Server-Sent Events stream line by line
                    for try await line in bytes.lines {
                        if line.hasPrefix("data: ") {
                            let data = String(line.dropFirst(6))

                            // Check for done marker
                            if data == "[DONE]" {
                                continuation.finish()
                                return
                            }

                            if let jsonData = data.data(using: .utf8) {
                                let decoder = JSONDecoder()
                                decoder.keyDecodingStrategy = .convertFromSnakeCase
                                let chunk = try decoder.decode(LlamaCppChunk.self, from: jsonData)
                                continuation.yield(chunk)

                                // Check for error or stop
                                if chunk.finishReason == "error" {
                                    continuation.finish(throwing: LlamaCppError.inferenceError(chunk.error ?? "Unknown error"))
                                    return
                                } else if chunk.finishReason == "stop" {
                                    continuation.finish()
                                    return
                                }
                            }
                        }
                    }

                    continuation.finish()

                } catch {
                    continuation.finish(throwing: error)
                }
            }
        }
    }

    /// Send chat messages and get full response (non-streaming)
    func chatSync(messages: [LlamaCppMessage], temperature: Double = 0.7, maxTokens: Int = 2048) async throws -> LlamaCppCompletion {
        guard let url = URL(string: "\(baseURL)/v1/chat/llamacpp/chat") else {
            throw LlamaCppError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.timeoutInterval = 300  // 5 minutes for long generations

        // Add auth token
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        // Request body
        let body: [String: Any] = [
            "messages": messages.map { ["role": $0.role, "content": $0.content] },
            "temperature": temperature,
            "max_tokens": maxTokens,
            "stream": false
        ]
        request.httpBody = try JSONSerialization.data(withJSONObject: body)

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw LlamaCppError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw LlamaCppError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let envelope = try decoder.decode(SuccessEnvelope<LlamaCppCompletion>.self, from: data)
        return envelope.data
    }

    // MARK: - Configuration

    /// Get llama.cpp configuration
    func getConfig() async throws -> LlamaCppConfig {
        guard let url = URL(string: "\(baseURL)/v1/chat/llamacpp/config") else {
            throw LlamaCppError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw LlamaCppError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw LlamaCppError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let envelope = try decoder.decode(SuccessEnvelope<LlamaCppConfig>.self, from: data)
        return envelope.data
    }
}

// MARK: - Models

/// Generic success envelope for API responses
private struct SuccessEnvelope<T: Decodable>: Decodable {
    let success: Bool
    let data: T
    let message: String?
}

/// Error envelope for error responses
private struct ErrorEnvelope: Decodable {
    let success: Bool
    let errorCode: String?
    let message: String?
}

/// Server status
struct LlamaCppStatus: Codable {
    let running: Bool
    let modelLoaded: String?
    let modelPath: String?
    let pid: Int?
    let startedAt: String?
    let healthOk: Bool
    let port: Int
    let error: String?
}

/// Chat message
struct LlamaCppMessage: Codable {
    let role: String  // "system", "user", "assistant"
    let content: String

    init(role: String, content: String) {
        self.role = role
        self.content = content
    }

    static func system(_ content: String) -> LlamaCppMessage {
        LlamaCppMessage(role: "system", content: content)
    }

    static func user(_ content: String) -> LlamaCppMessage {
        LlamaCppMessage(role: "user", content: content)
    }

    static func assistant(_ content: String) -> LlamaCppMessage {
        LlamaCppMessage(role: "assistant", content: content)
    }
}

/// Streaming chat chunk
struct LlamaCppChunk: Codable {
    let content: String
    let finishReason: String?
    let model: String?
    let error: String?
}

/// Complete chat response (non-streaming)
struct LlamaCppCompletion: Codable {
    let content: String
    let finishReason: String
    let model: String
    let usage: LlamaCppUsage?
}

/// Token usage info
struct LlamaCppUsage: Codable {
    let promptTokens: Int
    let completionTokens: Int
    let totalTokens: Int
}

/// Server configuration
struct LlamaCppConfig: Codable {
    let host: String
    let port: Int
    let contextSize: Int
    let batchSize: Int
    let nGpuLayers: Int
    let flashAttn: Bool
    let binaryPath: String?
    let binaryFound: Bool
}

// MARK: - Errors

enum LlamaCppError: LocalizedError {
    case invalidURL
    case invalidResponse
    case httpError(Int)
    case serverNotRunning
    case serverError(String)
    case inferenceError(String)
    case modelNotLoaded

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let code):
            return "HTTP error: \(code)"
        case .serverNotRunning:
            return "llama.cpp server is not running"
        case .serverError(let message):
            return "Server error: \(message)"
        case .inferenceError(let message):
            return "Inference error: \(message)"
        case .modelNotLoaded:
            return "No model loaded in llama.cpp server"
        }
    }
}
