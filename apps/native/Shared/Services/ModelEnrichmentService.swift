//
//  ModelEnrichmentService.swift
//  MagnetarStudio
//
//  Enriches local Ollama models with AI-generated metadata
//  Uses Apple FM orchestrator to analyze model names and generate
//  user-friendly descriptions, capabilities, and use cases
//
//  Part of Noah's Ark for the Digital Age - Intelligent model metadata
//  Foundation: Proverbs 2:6 - The Lord gives wisdom and knowledge
//

import Foundation

// MARK: - Enriched Model Metadata

struct EnrichedModelMetadata: Codable {
    let displayName: String
    let description: String
    let capability: String // chat, code, vision, reasoning, general
    let primaryUseCases: [String]
    let badges: [String]
    let isMultiPurpose: Bool
    let strengths: [String]
    let idealFor: String
    let parameterSize: String? // Extracted or inferred
    let estimatedMemoryGB: Double? // Calculated from size
}

// MARK: - Model Enrichment Service

@MainActor
class ModelEnrichmentService {
    static let shared = ModelEnrichmentService()

    // Cache enriched data (persists during app session)
    private var enrichmentCache: [String: EnrichedModelMetadata] = [:]

    // Loading states for UI feedback
    private var loadingStates: [String: Bool] = [:]

    private init() {}

    // MARK: - Public API

    /// Enrich a local Ollama model with AI-generated metadata
    func enrichModel(_ model: OllamaModel) async -> EnrichedModelMetadata {
        // Check cache first
        if let cached = enrichmentCache[model.name] {
            print("✓ Using cached enrichment for \(model.name)")
            return cached
        }

        // Avoid duplicate requests
        if loadingStates[model.name] == true {
            print("⏳ Enrichment already in progress for \(model.name)")
            // Wait a bit and check cache again
            try? await Task.sleep(nanoseconds: 500_000_000) // 0.5s
            return enrichmentCache[model.name] ?? fallbackEnrichment(model)
        }

        loadingStates[model.name] = true
        print("🔍 Enriching model: \(model.name)")

        // Try backend-powered enrichment
        if let enriched = await callBackendEnrichment(model) {
            enrichmentCache[model.name] = enriched
            loadingStates[model.name] = false
            print("✓ Backend enrichment successful for \(model.name)")
            return enriched
        }

        // Fallback to rule-based enrichment
        print("⚠️ Using fallback enrichment for \(model.name)")
        let fallback = fallbackEnrichment(model)
        enrichmentCache[model.name] = fallback
        loadingStates[model.name] = false
        return fallback
    }

    /// Clear enrichment cache (useful when models are updated)
    func clearCache() {
        enrichmentCache.removeAll()
        print("🗑️ Enrichment cache cleared")
    }

    /// Clear cache for specific model
    func clearCache(for modelName: String) {
        enrichmentCache.removeValue(forKey: modelName)
        print("🗑️ Cleared cache for \(modelName)")
    }

    // MARK: - Backend Enrichment

    private func callBackendEnrichment(_ model: OllamaModel) async -> EnrichedModelMetadata? {
        do {
            // Build enrichment request
            let request = ModelEnrichmentRequest(
                modelName: model.name,
                family: model.details?.family,
                parameterSize: model.details?.parameterSize,
                quantizationLevel: model.details?.quantizationLevel,
                sizeBytes: model.size,
                format: model.details?.format
            )

            // Call backend enrichment endpoint
            let response: ModelEnrichmentResponse = try await ApiClient.shared.request(
                "/v1/models/enrich",
                method: .post,
                body: request
            )

            // Map response to metadata
            return EnrichedModelMetadata(
                displayName: response.displayName,
                description: response.description,
                capability: response.capability,
                primaryUseCases: response.primaryUseCases,
                badges: response.badges,
                isMultiPurpose: response.isMultiPurpose,
                strengths: response.strengths,
                idealFor: response.idealFor,
                parameterSize: response.parameterSize ?? model.details?.parameterSize,
                estimatedMemoryGB: response.estimatedMemoryGB ?? estimateMemoryUsage(model)
            )

        } catch {
            print("⚠️ Backend enrichment failed: \(error)")
            return nil
        }
    }

    // MARK: - Fallback Enrichment (Rule-Based)

    private func fallbackEnrichment(_ model: OllamaModel) -> EnrichedModelMetadata {
        let name = model.name.lowercased()

        // Detect model family
        let (family, displayName) = detectFamily(name)

        // Detect capability
        let capability = detectCapability(name)

        // Generate description
        let description = generateDescription(family: family, capability: capability, model: model)

        // Detect use cases
        let useCases = detectUseCases(capability: capability)

        // Generate badges
        let badges = generateBadges(name: name, capability: capability)

        // Detect if multi-purpose
        let isMultiPurpose = detectMultiPurpose(name)

        // Generate strengths
        let strengths = generateStrengths(family: family, capability: capability)

        // Generate ideal use case
        let idealFor = generateIdealFor(capability: capability, family: family)

        return EnrichedModelMetadata(
            displayName: displayName,
            description: description,
            capability: capability,
            primaryUseCases: useCases,
            badges: badges,
            isMultiPurpose: isMultiPurpose,
            strengths: strengths,
            idealFor: idealFor,
            parameterSize: model.details?.parameterSize,
            estimatedMemoryGB: estimateMemoryUsage(model)
        )
    }

    // MARK: - Detection Helpers

    private func detectFamily(_ name: String) -> (String, String) {
        if name.contains("llama") {
            return ("llama", "Llama \(extractVersion(name))")
        } else if name.contains("mistral") || name.contains("ministral") {
            return ("mistral", "Mistral \(extractVersion(name))")
        } else if name.contains("mixtral") {
            return ("mixtral", "Mixtral \(extractVersion(name))")
        } else if name.contains("phi") {
            return ("phi", "Phi \(extractVersion(name))")
        } else if name.contains("qwen") {
            return ("qwen", "Qwen \(extractVersion(name))")
        } else if name.contains("gemma") {
            return ("gemma", "Gemma \(extractVersion(name))")
        } else if name.contains("deepseek") {
            return ("deepseek", "DeepSeek \(extractVersion(name))")
        } else if name.contains("command") {
            return ("command", "Command R \(extractVersion(name))")
        } else if name.contains("codestral") {
            return ("codestral", "Codestral \(extractVersion(name))")
        } else if name.contains("gpt") {
            return ("gpt", "GPT \(extractVersion(name))")
        } else if name.contains("sqlcoder") {
            return ("sqlcoder", "SQLCoder \(extractVersion(name))")
        } else {
            // Extract base name
            let baseName = name.components(separatedBy: ":").first ?? name
            return ("unknown", baseName.capitalized)
        }
    }

    private func extractVersion(_ name: String) -> String {
        // Try to extract version like "3.2", "7b", etc.
        if let colonIndex = name.firstIndex(of: ":") {
            let afterColon = String(name[name.index(after: colonIndex)...])
            return afterColon.uppercased()
        }

        // Try to find version in name (e.g., "llama3.2")
        let patterns = ["3.2", "3.1", "3", "2.5", "2", "7b", "13b", "70b"]
        for pattern in patterns {
            if name.contains(pattern) {
                return pattern.uppercased()
            }
        }

        return ""
    }

    private func detectCapability(_ name: String) -> String {
        if name.contains("code") || name.contains("coder") {
            return "code"
        } else if name.contains("vision") || name.contains("llava") || name.contains("bakllava") {
            return "vision"
        } else if name.contains("reason") || name.contains("think") {
            return "reasoning"
        } else if name.contains("chat") || name.contains("instruct") {
            return "chat"
        } else if name.contains("sql") {
            return "data"
        } else {
            return "general"
        }
    }

    private func detectUseCases(capability: String) -> [String] {
        switch capability {
        case "code":
            return ["Code generation", "Code review", "Debugging"]
        case "vision":
            return ["Image analysis", "Visual Q&A", "OCR"]
        case "reasoning":
            return ["Complex problem solving", "Chain-of-thought", "Math & logic"]
        case "chat":
            return ["Conversations", "Q&A", "General assistance"]
        case "data":
            return ["SQL generation", "Data analysis", "Query optimization"]
        default:
            return ["General tasks", "Conversational AI", "Text generation"]
        }
    }

    private func generateBadges(name: String, capability: String) -> [String] {
        var badges = ["installed"]

        if name.contains("instruct") {
            badges.append("instruct")
        }

        if capability == "code" {
            badges.append("code")
        } else if capability == "vision" {
            badges.append("vision")
        } else if capability == "reasoning" {
            badges.append("reasoning")
        }

        if name.contains("experimental") {
            badges.append("experimental")
        }

        return badges
    }

    private func detectMultiPurpose(_ name: String) -> Bool {
        // Models that are known to be multi-purpose
        let multiPurposeIndicators = ["command-r", "gpt", "llama-3", "qwen2.5", "mistral"]
        return multiPurposeIndicators.contains { name.contains($0) }
    }

    private func generateStrengths(family: String, capability: String) -> [String] {
        var strengths: [String] = []

        switch family {
        case "llama":
            strengths = ["Open source", "Well-optimized", "Strong general performance"]
        case "mistral", "mixtral":
            strengths = ["Fast inference", "Excellent reasoning", "Multilingual support"]
        case "phi":
            strengths = ["Compact size", "Low memory footprint", "Fast responses"]
        case "qwen":
            strengths = ["Multilingual", "Strong coding ability", "Versatile"]
        case "deepseek":
            strengths = ["Advanced reasoning", "Code expertise", "Chain-of-thought"]
        case "gemma":
            strengths = ["Lightweight", "Efficient", "Google-backed"]
        default:
            strengths = ["Locally installed", "Privacy-focused", "Offline capable"]
        }

        return strengths
    }

    private func generateDescription(family: String, capability: String, model: OllamaModel) -> String {
        let sizeDesc = model.details?.parameterSize ?? "Unknown size"
        let familyDesc = familyDescription(family)
        let capabilityDesc = capabilityDescription(capability)

        return "\(familyDesc) (\(sizeDesc)). \(capabilityDesc) Runs locally on your Mac with full privacy."
    }

    private func familyDescription(_ family: String) -> String {
        switch family {
        case "llama":
            return "Meta's powerful open-source language model"
        case "mistral", "ministral":
            return "High-performance model with excellent reasoning capabilities"
        case "mixtral":
            return "Mixture-of-experts model with superior performance"
        case "phi":
            return "Microsoft's efficient small language model"
        case "qwen":
            return "Multilingual model with strong capabilities across tasks"
        case "gemma":
            return "Google's lightweight and efficient open model"
        case "deepseek":
            return "Advanced model specializing in reasoning and code"
        case "command":
            return "Cohere's enterprise-grade language model"
        case "codestral":
            return "Mistral AI's specialized coding model"
        case "gpt":
            return "GPT-style open-source language model"
        case "sqlcoder":
            return "Specialized model for SQL generation and database tasks"
        default:
            return "Locally installed language model"
        }
    }

    private func capabilityDescription(_ capability: String) -> String {
        switch capability {
        case "code":
            return "Optimized for code generation, review, and debugging."
        case "vision":
            return "Capable of analyzing images and answering visual questions."
        case "reasoning":
            return "Excels at complex problem-solving with chain-of-thought reasoning."
        case "chat":
            return "Fine-tuned for natural conversations and general assistance."
        case "data":
            return "Specialized in SQL generation and data analysis tasks."
        default:
            return "Versatile general-purpose model for various tasks."
        }
    }

    private func generateIdealFor(capability: String, family: String) -> String {
        switch capability {
        case "code":
            return "Developers needing code assistance, refactoring, or debugging help"
        case "vision":
            return "Tasks requiring image understanding, OCR, or visual analysis"
        case "reasoning":
            return "Complex problem-solving, mathematical reasoning, or logical analysis"
        case "chat":
            return "General conversations, Q&A, and day-to-day assistance"
        case "data":
            return "Database work, SQL query generation, and data analysis"
        default:
            if family == "phi" {
                return "Quick responses with low resource usage"
            } else if family.contains("mistral") {
                return "Fast, accurate responses across multiple languages"
            } else {
                return "General-purpose tasks requiring balanced performance"
            }
        }
    }

    private func estimateMemoryUsage(_ model: OllamaModel) -> Double {
        // Rough estimation: model size + overhead (usually 1.2-1.5x)
        let sizeGB = Double(model.size) / 1_073_741_824.0
        return sizeGB * 1.3 // 30% overhead for runtime
    }
}

// MARK: - API Request/Response Models

struct ModelEnrichmentRequest: Codable {
    let modelName: String
    let family: String?
    let parameterSize: String?
    let quantizationLevel: String?
    let sizeBytes: Int64
    let format: String?
}

struct ModelEnrichmentResponse: Codable {
    let displayName: String
    let description: String
    let capability: String
    let primaryUseCases: [String]
    let badges: [String]
    let isMultiPurpose: Bool
    let strengths: [String]
    let idealFor: String
    let parameterSize: String?
    let estimatedMemoryGB: Double?
}
