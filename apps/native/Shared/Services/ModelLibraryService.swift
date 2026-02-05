//
//  ModelLibraryService.swift
//  MagnetarStudio
//
//  Service for browsing and discovering models from Ollama library
//

import Foundation

class ModelLibraryService {
    static let shared = ModelLibraryService()

    private let ollamaLibraryURL = "https://ollama.com/api/tags"

    init() {}

    // MARK: - Browse Library

    func browseLibrary(
        search: String? = nil,
        modelType: String? = nil,
        capability: String? = nil,
        sortBy: String = "pulls",
        order: String = "desc",
        limit: Int = 50,
        skip: Int = 0
    ) async throws -> LibraryResponse {
        // Fetch all models from Ollama library
        guard let url = URL(string: ollamaLibraryURL) else {
            throw ModelLibraryError.invalidURL
        }

        var request = URLRequest(url: url)
        request.httpMethod = "GET"
        request.setValue("application/json", forHTTPHeaderField: "Accept")
        request.timeoutInterval = 30

        let (data, response) = try await URLSession.shared.data(for: request)

        guard let httpResponse = response as? HTTPURLResponse else {
            throw ModelLibraryError.invalidResponse
        }

        guard httpResponse.statusCode == 200 else {
            throw ModelLibraryError.httpError(httpResponse.statusCode)
        }

        // Parse Ollama's response
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        let apiResponse = try decoder.decode(OllamaAPIResponse.self, from: data)
        let ollamaModels = apiResponse.models

        // Convert to our LibraryModel format
        var libraryModels = ollamaModels.map { model -> LibraryModel in
            // Extract base model name (e.g., "llama3:8b" -> "llama3")
            let baseName = model.name.components(separatedBy: ":").first ?? model.name

            // Extract parameter size from model name
            let labels = extractLabelsFromModelName(model.name)

            // Determine if official
            let isOfficial = isOfficialModel(baseName)

            // Generate friendly description
            let description = generateDescription(for: baseName)

            return LibraryModel(
                modelIdentifier: model.name,
                modelName: baseName,
                modelType: isOfficial ? "official" : "community",
                description: description,
                capability: inferCapability(from: baseName),
                labels: labels,
                pulls: 0, // API doesn't provide this
                tags: [model.name],
                lastUpdated: model.modifiedAt ?? "",
                url: "https://ollama.com/library/\(baseName)"
            )
        }

        // Apply filters
        if let search = search, !search.isEmpty {
            let searchLower = search.lowercased()
            libraryModels = libraryModels.filter {
                $0.modelName.lowercased().contains(searchLower) ||
                $0.description?.lowercased().contains(searchLower) == true
            }
        }

        if let modelType = modelType {
            libraryModels = libraryModels.filter { $0.modelType == modelType }
        }

        if let capability = capability {
            libraryModels = libraryModels.filter { $0.capability == capability }
        }

        // Sort
        switch sortBy {
        case "pulls":
            libraryModels.sort { $0.pulls > $1.pulls }
        case "last_updated":
            libraryModels.sort { $0.lastUpdated > $1.lastUpdated }
        default:
            break
        }

        if order == "asc" {
            libraryModels.reverse()
        }

        // Paginate
        let totalCount = libraryModels.count
        let start = skip
        let end = min(start + limit, totalCount)
        let paginatedModels = Array(libraryModels[start..<end])

        return LibraryResponse(
            models: paginatedModels,
            totalCount: totalCount,
            limit: limit,
            skip: skip,
            dataUpdated: ISO8601DateFormatter().string(from: Date())
        )
    }

    private func extractLabelsFromModelName(_ name: String) -> [String] {
        // Extract parameter size from model name (e.g., "llama3:8b" -> ["8B"])
        var labels: [String] = []

        if let match = name.range(of: "\\d+(\\.\\d+)?[bB]", options: .regularExpression) {
            let size = String(name[match]).uppercased()
            labels.append(size)
        }

        return labels
    }

    private func isOfficialModel(_ baseName: String) -> Bool {
        // List of known official Ollama models
        let officialModels = [
            "llama3", "llama2", "mistral", "mixtral", "gemma", "phi", "qwen",
            "codellama", "deepseek", "yi", "solar", "dolphin", "orca", "vicuna",
            "starling", "openhermes", "neural-chat", "zephyr", "nous-hermes"
        ]
        return officialModels.contains(baseName.lowercased())
    }

    private func generateDescription(for baseName: String) -> String {
        // Provide friendly descriptions for known models
        switch baseName.lowercased() {
        case "llama3", "llama2":
            return "Meta's powerful open-source language model, great for general tasks"
        case "mistral", "mixtral":
            return "High-performance model from Mistral AI, excellent for coding and reasoning"
        case "gemma", "gemma2", "gemma3":
            return "Google's efficient language model, optimized for on-device use"
        case "phi", "phi3":
            return "Microsoft's small but capable model, perfect for resource-constrained environments"
        case "qwen", "qwen2", "qwen3":
            return "Alibaba's multilingual model with strong capabilities across languages"
        case "codellama":
            return "Specialized for code generation and programming tasks"
        case "deepseek":
            return "Advanced model with strong reasoning and coding abilities"
        case "yi":
            return "01.AI's bilingual model with excellent performance"
        default:
            return "Language model available through Ollama"
        }
    }

    private func inferCapability(from baseName: String) -> String? {
        // Infer capability from model name
        if baseName.lowercased().contains("code") {
            return "code"
        } else if baseName.lowercased().contains("vision") || baseName.lowercased().contains("vl") {
            return "vision"
        } else if baseName.lowercased().contains("embed") {
            return "embedding"
        }
        return "chat"
    }
}

// MARK: - Ollama API Models

private struct OllamaAPIResponse: Codable {
    let models: [OllamaAPIModel]
}

private struct OllamaAPIModel: Codable {
    let name: String
    let model: String
    let modifiedAt: String?
    let size: Int64?
    let digest: String?
    let details: OllamaModelDetails?

    enum CodingKeys: String, CodingKey {
        case name, model, size, digest, details
        case modifiedAt = "modified_at"
    }
}

private struct OllamaModelDetails: Codable {
    let parentModel: String?
    let format: String?
    let family: String?
    let families: [String]?
    let parameterSize: String?
    let quantizationLevel: String?

    enum CodingKeys: String, CodingKey {
        case format, family, families
        case parentModel = "parent_model"
        case parameterSize = "parameter_size"
        case quantizationLevel = "quantization_level"
    }
}

// MARK: - Models

struct LibraryResponse: Codable {
    let models: [LibraryModel]
    let totalCount: Int
    let limit: Int
    let skip: Int
    let dataUpdated: String?
}

struct LibraryModel: Codable, Identifiable {
    let modelIdentifier: String
    let modelName: String
    let modelType: String  // "official" or "community"
    let description: String?
    let capability: String?
    let labels: [String]?  // Parameter sizes like ["3B", "7B"]
    let pulls: Int
    let tags: [String]
    let lastUpdated: String
    let url: String

    var id: String { modelIdentifier }

    var isOfficial: Bool {
        modelType == "official"
    }

    var pullsFormatted: String {
        if pulls >= 1_000_000 {
            return String(format: "%.1fM", Double(pulls) / 1_000_000.0)
        } else if pulls >= 1_000 {
            return String(format: "%.1fK", Double(pulls) / 1_000.0)
        } else {
            return "\(pulls)"
        }
    }

    var labelsText: String {
        labels?.joined(separator: ", ") ?? ""
    }
}

// MARK: - Errors

enum ModelLibraryError: LocalizedError {
    case invalidURL
    case invalidResponse
    case httpError(Int)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid URL"
        case .invalidResponse:
            return "Invalid response from server"
        case .httpError(let code):
            return "HTTP error: \(code)"
        }
    }
}
