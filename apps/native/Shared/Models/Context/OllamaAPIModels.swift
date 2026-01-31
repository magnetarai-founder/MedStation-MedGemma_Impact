//
//  OllamaAPIModels.swift
//  MagnetarStudio
//
//  Ollama API response models extracted from ContextBundle.swift.
//  Part of Phase 7 refactoring for maintainability.
//

import Foundation

// MARK: - Ollama API Response Types

/// Response from Ollama /api/tags endpoint
struct OllamaTagsResponse: Codable {
    let models: [OllamaModelInfo]
}

/// Model info from Ollama API (distinct from UI model state)
struct OllamaModelInfo: Codable {
    let name: String
    let size: Int64
    let modifiedAt: String
    let details: OllamaModelInfoDetails?

    enum CodingKeys: String, CodingKey {
        case name, size
        case modifiedAt = "modified_at"
        case details
    }

    /// Size in GB for display
    var sizeGB: Double {
        return Double(size) / 1_073_741_824.0
    }

    /// Estimated parameter count (rough heuristic)
    var estimatedParameters: String {
        if let paramSize = details?.parameterSize {
            return paramSize
        }
        // Estimate from file size (very rough)
        let gbSize = sizeGB
        if gbSize > 40 { return "70B+" }
        if gbSize > 20 { return "30-40B" }
        if gbSize > 10 { return "13-20B" }
        if gbSize > 4 { return "7-8B" }
        if gbSize > 2 { return "3-4B" }
        return "1-2B"
    }

    /// Display name (cleaned up model name)
    var displayName: String {
        // Remove common suffixes for cleaner display
        var clean = name
        clean = clean.replacingOccurrences(of: ":latest", with: "")
        return clean
    }
}

/// Details about an Ollama model
struct OllamaModelInfoDetails: Codable {
    let parameterSize: String?
    let quantizationLevel: String?
    let format: String?
    let family: String?

    enum CodingKeys: String, CodingKey {
        case parameterSize = "parameter_size"
        case quantizationLevel = "quantization_level"
        case format, family
    }

    /// Human-readable quantization description
    var quantizationDescription: String {
        guard let quant = quantizationLevel else { return "Unknown" }
        switch quant.uppercased() {
        case "Q2_K": return "2-bit (smallest, lowest quality)"
        case "Q3_K_S", "Q3_K_M", "Q3_K_L": return "3-bit (small)"
        case "Q4_0", "Q4_K_S", "Q4_K_M": return "4-bit (balanced)"
        case "Q5_0", "Q5_K_S", "Q5_K_M": return "5-bit (high quality)"
        case "Q6_K": return "6-bit (very high quality)"
        case "Q8_0": return "8-bit (near lossless)"
        case "F16": return "16-bit (full precision)"
        case "F32": return "32-bit (maximum precision)"
        default: return quant
        }
    }
}

// MARK: - Ollama Generation Types

/// Request body for Ollama /api/generate
struct OllamaGenerateRequest: Codable {
    let model: String
    let prompt: String
    let stream: Bool
    let options: OllamaGenerateOptions?
    let system: String?
    let context: [Int]?  // Previous context for multi-turn

    init(
        model: String,
        prompt: String,
        stream: Bool = true,
        options: OllamaGenerateOptions? = nil,
        system: String? = nil,
        context: [Int]? = nil
    ) {
        self.model = model
        self.prompt = prompt
        self.stream = stream
        self.options = options
        self.system = system
        self.context = context
    }
}

/// Options for Ollama generation
struct OllamaGenerateOptions: Codable {
    var temperature: Float?
    var topK: Int?
    var topP: Float?
    var numPredict: Int?
    var numCtx: Int?
    var seed: Int?
    var repeatPenalty: Float?
    var stop: [String]?

    enum CodingKeys: String, CodingKey {
        case temperature
        case topK = "top_k"
        case topP = "top_p"
        case numPredict = "num_predict"
        case numCtx = "num_ctx"
        case seed
        case repeatPenalty = "repeat_penalty"
        case stop
    }

    static let `default` = OllamaGenerateOptions(
        temperature: 0.7,
        topK: 40,
        topP: 0.9,
        numPredict: 2048,
        numCtx: 4096
    )

    static let creative = OllamaGenerateOptions(
        temperature: 0.9,
        topK: 60,
        topP: 0.95,
        numPredict: 4096,
        numCtx: 8192
    )

    static let precise = OllamaGenerateOptions(
        temperature: 0.3,
        topK: 20,
        topP: 0.8,
        numPredict: 2048,
        numCtx: 4096
    )
}

/// Response chunk from Ollama streaming generation
struct OllamaGenerateResponse: Codable {
    let model: String
    let createdAt: String
    let response: String
    let done: Bool
    let context: [Int]?
    let totalDuration: Int64?
    let loadDuration: Int64?
    let promptEvalCount: Int?
    let evalCount: Int?
    let evalDuration: Int64?

    enum CodingKeys: String, CodingKey {
        case model
        case createdAt = "created_at"
        case response, done, context
        case totalDuration = "total_duration"
        case loadDuration = "load_duration"
        case promptEvalCount = "prompt_eval_count"
        case evalCount = "eval_count"
        case evalDuration = "eval_duration"
    }

    /// Tokens per second (if available)
    var tokensPerSecond: Double? {
        guard let evalCount = evalCount, evalCount > 0,
              let evalDuration = evalDuration, evalDuration > 0 else {
            return nil
        }
        return Double(evalCount) / (Double(evalDuration) / 1_000_000_000.0)
    }
}

// MARK: - Ollama Chat Types

/// Request body for Ollama /api/chat
struct OllamaChatRequest: Codable {
    let model: String
    let messages: [OllamaChatMessage]
    let stream: Bool
    let options: OllamaGenerateOptions?

    init(
        model: String,
        messages: [OllamaChatMessage],
        stream: Bool = true,
        options: OllamaGenerateOptions? = nil
    ) {
        self.model = model
        self.messages = messages
        self.stream = stream
        self.options = options
    }
}

/// A message in Ollama chat format
struct OllamaChatMessage: Codable {
    let role: String
    let content: String
    let images: [String]?  // Base64 encoded images for multimodal

    init(role: String, content: String, images: [String]? = nil) {
        self.role = role
        self.content = content
        self.images = images
    }

    static func system(_ content: String) -> OllamaChatMessage {
        OllamaChatMessage(role: "system", content: content)
    }

    static func user(_ content: String) -> OllamaChatMessage {
        OllamaChatMessage(role: "user", content: content)
    }

    static func assistant(_ content: String) -> OllamaChatMessage {
        OllamaChatMessage(role: "assistant", content: content)
    }
}

/// Response from Ollama /api/chat
struct OllamaChatResponse: Codable {
    let model: String
    let createdAt: String
    let message: OllamaChatMessage?
    let done: Bool
    let totalDuration: Int64?
    let loadDuration: Int64?
    let promptEvalCount: Int?
    let evalCount: Int?
    let evalDuration: Int64?

    enum CodingKeys: String, CodingKey {
        case model
        case createdAt = "created_at"
        case message, done
        case totalDuration = "total_duration"
        case loadDuration = "load_duration"
        case promptEvalCount = "prompt_eval_count"
        case evalCount = "eval_count"
        case evalDuration = "eval_duration"
    }
}

// MARK: - Ollama Embedding Types

/// Request for Ollama /api/embeddings
struct OllamaEmbeddingRequest: Codable {
    let model: String
    let prompt: String

    init(model: String = "nomic-embed-text", prompt: String) {
        self.model = model
        self.prompt = prompt
    }
}

/// Response from Ollama /api/embeddings
struct OllamaEmbeddingResponse: Codable {
    let embedding: [Float]
}

// MARK: - Ollama Show Types

/// Request for Ollama /api/show
struct OllamaShowRequest: Codable {
    let name: String
}

/// Response from Ollama /api/show
struct OllamaShowResponse: Codable {
    let modelfile: String?
    let parameters: String?
    let template: String?
    let details: OllamaModelInfoDetails?
    let modelInfo: [String: Any]?

    enum CodingKeys: String, CodingKey {
        case modelfile, parameters, template, details
        case modelInfo = "model_info"
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        modelfile = try container.decodeIfPresent(String.self, forKey: .modelfile)
        parameters = try container.decodeIfPresent(String.self, forKey: .parameters)
        template = try container.decodeIfPresent(String.self, forKey: .template)
        details = try container.decodeIfPresent(OllamaModelInfoDetails.self, forKey: .details)
        modelInfo = nil  // Can't easily decode [String: Any]
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encodeIfPresent(modelfile, forKey: .modelfile)
        try container.encodeIfPresent(parameters, forKey: .parameters)
        try container.encodeIfPresent(template, forKey: .template)
        try container.encodeIfPresent(details, forKey: .details)
    }
}
