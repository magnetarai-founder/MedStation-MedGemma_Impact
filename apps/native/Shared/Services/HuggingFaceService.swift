import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "HuggingFaceService")

/// Service for managing HuggingFace GGUF model downloads
@MainActor
final class HuggingFaceService {
    static let shared = HuggingFaceService()

    private init() {}

    private var baseURL: String {
        APIConfiguration.shared.baseURL
    }

    // MARK: - Model Listing

    /// List available GGUF models from registry
    func listAvailableModels(capability: String? = nil, recommendedOnly: Bool = false) async throws -> [HuggingFaceModel] {
        var urlString = "\(baseURL)/v1/chat/huggingface/models"

        var queryItems: [URLQueryItem] = []
        if let capability = capability {
            queryItems.append(URLQueryItem(name: "capability", value: capability))
        }
        if recommendedOnly {
            queryItems.append(URLQueryItem(name: "recommended_only", value: "true"))
        }

        if !queryItems.isEmpty {
            guard var components = URLComponents(string: urlString) else {
                throw HuggingFaceError.invalidURL
            }
            components.queryItems = queryItems
            guard let composedURL = components.url else {
                throw HuggingFaceError.invalidURL
            }
            urlString = composedURL.absoluteString
        }

        guard let url = URL(string: urlString) else {
            throw HuggingFaceError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw HuggingFaceError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw HuggingFaceError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let envelope = try decoder.decode(SuccessEnvelope<[HuggingFaceModel]>.self, from: data)
        return envelope.data
    }

    /// List medical-specialized models
    func listMedicalModels() async throws -> [HuggingFaceModel] {
        guard let url = URL(string: "\(baseURL)/v1/chat/huggingface/models/medical") else {
            throw HuggingFaceError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw HuggingFaceError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw HuggingFaceError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let envelope = try decoder.decode(SuccessEnvelope<[HuggingFaceModel]>.self, from: data)
        return envelope.data
    }

    /// List downloaded local models
    func listLocalModels() async throws -> [DownloadedModel] {
        guard let url = URL(string: "\(baseURL)/v1/chat/huggingface/models/local") else {
            throw HuggingFaceError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        // Add auth token
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw HuggingFaceError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw HuggingFaceError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let envelope = try decoder.decode(SuccessEnvelope<[DownloadedModel]>.self, from: data)
        return envelope.data
    }

    // MARK: - Download Management

    /// Download a GGUF model with streaming progress
    func downloadModel(modelId: String) -> AsyncThrowingStream<DownloadProgress, Error> {
        AsyncThrowingStream { continuation in
            Task {
                do {
                    guard let url = URL(string: "\(baseURL)/v1/chat/huggingface/models/download") else {
                        continuation.finish(throwing: HuggingFaceError.invalidURL)
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
                    let body = ["model_id": modelId]
                    request.httpBody = try JSONEncoder().encode(body)

                    // Use async bytes for streaming SSE
                    let (bytes, response) = try await URLSession.shared.bytes(for: request)

                    guard let httpResponse = response as? HTTPURLResponse else {
                        continuation.finish(throwing: HuggingFaceError.invalidResponse)
                        return
                    }

                    guard httpResponse.statusCode == 200 else {
                        continuation.finish(throwing: HuggingFaceError.httpError(httpResponse.statusCode))
                        return
                    }

                    // Parse Server-Sent Events stream line by line
                    for try await line in bytes.lines {
                        if line.hasPrefix("data: ") {
                            let jsonString = String(line.dropFirst(6))
                            if let jsonData = jsonString.data(using: .utf8) {
                                let decoder = JSONDecoder()
                                decoder.keyDecodingStrategy = .convertFromSnakeCase
                                let progress = try decoder.decode(DownloadProgress.self, from: jsonData)
                                continuation.yield(progress)

                                // Finish on terminal status
                                if progress.status == "completed" {
                                    continuation.finish()
                                    return
                                } else if progress.status == "failed" || progress.status == "canceled" {
                                    continuation.finish(throwing: HuggingFaceError.downloadFailed(progress.error ?? progress.message))
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

    /// Delete a downloaded model
    func deleteModel(modelId: String) async throws {
        guard let encodedId = modelId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed),
              let url = URL(string: "\(baseURL)/v1/chat/huggingface/models/\(encodedId)") else {
            throw HuggingFaceError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "DELETE"
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        // Add auth token
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (_, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw HuggingFaceError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw HuggingFaceError.httpError(httpResponse.statusCode)
        }

        logger.info("Deleted model: \(modelId)")
    }

    // MARK: - Hardware Validation

    /// Get hardware info and recommended quantization
    func getHardwareInfo() async throws -> HardwareInfo {
        guard let url = URL(string: "\(baseURL)/v1/chat/huggingface/hardware") else {
            throw HuggingFaceError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw HuggingFaceError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw HuggingFaceError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let envelope = try decoder.decode(SuccessEnvelope<HardwareInfo>.self, from: data)
        return envelope.data
    }

    /// Validate if a model will fit in available VRAM
    func validateModel(modelId: String) async throws -> ModelValidation {
        guard let encodedId = modelId.addingPercentEncoding(withAllowedCharacters: .urlPathAllowed),
              let url = URL(string: "\(baseURL)/v1/chat/huggingface/models/\(encodedId)/validate") else {
            throw HuggingFaceError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw HuggingFaceError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw HuggingFaceError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let envelope = try decoder.decode(SuccessEnvelope<ModelValidation>.self, from: data)
        return envelope.data
    }

    /// Get storage summary
    func getStorageSummary() async throws -> StorageSummary {
        guard let url = URL(string: "\(baseURL)/v1/chat/huggingface/storage") else {
            throw HuggingFaceError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        // Add auth token
        if let token = KeychainService.shared.loadToken() {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw HuggingFaceError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw HuggingFaceError.httpError(httpResponse.statusCode)
        }

        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let envelope = try decoder.decode(SuccessEnvelope<StorageSummary>.self, from: data)
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

/// GGUF model from registry
struct HuggingFaceModel: Codable, Identifiable {
    let id: String
    let name: String
    let repoId: String
    let filename: String
    let sizeGb: Double
    let parameterCount: String
    let quantization: String
    let contextLength: Int
    let minVramGb: Double
    let recommendedVramGb: Double
    let capabilities: [String]
    let description: String
    let isDownloaded: Bool

    var sizeFormatted: String {
        if sizeGb >= 1.0 {
            return String(format: "%.1f GB", sizeGb)
        } else {
            return String(format: "%.0f MB", sizeGb * 1024)
        }
    }
}

/// Downloaded model info
struct DownloadedModel: Codable, Identifiable {
    var id: String { "\(repoId):\(filename)" }
    let repoId: String
    let filename: String
    let path: String
    let sizeBytes: Int
    let quantization: String?
    let downloadedAt: String

    var sizeFormatted: String {
        let gb = Double(sizeBytes) / (1024 * 1024 * 1024)
        if gb >= 1.0 {
            return String(format: "%.1f GB", gb)
        } else {
            let mb = Double(sizeBytes) / (1024 * 1024)
            return String(format: "%.0f MB", mb)
        }
    }
}

/// Download progress update
struct DownloadProgress: Codable {
    let jobId: String
    let status: String  // "starting", "downloading", "verifying", "completed", "failed", "canceled"
    let progress: Double  // 0-100
    let downloadedBytes: Int
    let totalBytes: Int
    let speedBps: Int
    let etaSeconds: Int?
    let message: String
    let modelId: String?
    let error: String?

    var speedFormatted: String {
        let mbps = Double(speedBps) / (1024 * 1024)
        if mbps >= 1.0 {
            return String(format: "%.1f MB/s", mbps)
        } else {
            let kbps = Double(speedBps) / 1024
            return String(format: "%.0f KB/s", kbps)
        }
    }

    var etaFormatted: String {
        guard let eta = etaSeconds else { return "—" }
        if eta < 60 {
            return "\(eta)s"
        } else if eta < 3600 {
            return "\(eta / 60)m"
        } else {
            let hours = eta / 3600
            let mins = (eta % 3600) / 60
            return "\(hours)h \(mins)m"
        }
    }
}

/// Hardware information
struct HardwareInfo: Codable {
    let platform: String
    let isAppleSilicon: Bool
    let totalMemoryGb: Double
    let availableMemoryGb: Double
    let gpuName: String?
    let gpuVramGb: Double?
    let hasMetal: Bool
    let hasCuda: Bool
    let recommendedQuantization: String
}

/// Model validation result
struct ModelValidation: Codable {
    let modelId: String
    let compatible: Bool
    let message: String
    let modelSizeGb: Double
    let minVramGb: Double
    let availableVramGb: Double?
}

/// Storage summary
struct StorageSummary: Codable {
    let modelCount: Int
    let totalBytes: Int
    let totalGb: Double
    let storagePath: String
}

// MARK: - Errors

enum HuggingFaceError: LocalizedError {
    case invalidURL
    case invalidResponse
    case httpError(Int)
    case downloadFailed(String)
    case modelNotFound
    case insufficientVRAM

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let code):
            return "HTTP error: \(code)"
        case .downloadFailed(let message):
            return "Download failed: \(message)"
        case .modelNotFound:
            return "Model not found"
        case .insufficientVRAM:
            return "Insufficient VRAM for this model"
        }
    }
}
