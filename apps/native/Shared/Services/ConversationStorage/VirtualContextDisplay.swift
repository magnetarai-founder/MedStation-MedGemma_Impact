//
//  VirtualContextDisplay.swift
//  MagnetarStudio
//
//  Displays virtual context limit (280K+) while managing actual model limits.
//  Wired: ChatInputArea shows shortDisplayString as context usage indicator.
//  Addresses Gap 5: Show retrievable context, not actual model limit.
//

import Foundation

// MARK: - Virtual Context Display

/// Represents the virtual vs actual context limits
struct VirtualContextDisplay {

    /// What the model actually uses per request
    let actualModelLimit: Int

    /// What the user can reference (all stored context)
    let virtualLimit: Int

    /// Current usage in the virtual space
    let currentUsage: Int

    /// Current usage as a percentage of virtual limit
    var usagePercentage: Double {
        guard virtualLimit > 0 else { return 0 }
        return Double(currentUsage) / Double(virtualLimit) * 100
    }

    /// Formatted string for display
    var displayString: String {
        let formatter = NumberFormatter()
        formatter.numberStyle = .decimal
        formatter.maximumFractionDigits = 0

        let current = formatter.string(from: NSNumber(value: currentUsage)) ?? "\(currentUsage)"
        let virtual = formatter.string(from: NSNumber(value: virtualLimit)) ?? "\(virtualLimit)"

        return "\(current) / \(virtual) tokens"
    }

    /// Short display for compact UI
    var shortDisplayString: String {
        let currentK = currentUsage / 1000
        let virtualK = virtualLimit / 1000
        return "\(currentK)K / \(virtualK)K"
    }

    /// Color indicator based on usage
    var usageLevel: UsageLevel {
        let percentage = usagePercentage
        if percentage < 50 {
            return .low
        } else if percentage < 75 {
            return .medium
        } else if percentage < 90 {
            return .high
        } else {
            return .critical
        }
    }

    enum UsageLevel {
        case low
        case medium
        case high
        case critical

        var colorName: String {
            switch self {
            case .low: return "green"
            case .medium: return "yellow"
            case .high: return "orange"
            case .critical: return "red"
            }
        }
    }

    // MARK: - Factory Methods

    /// Create display for a specific model and conversation
    @MainActor
    static func forModel(
        _ modelId: String?,
        conversationId: UUID,
        storageService: ConversationStorageService
    ) -> VirtualContextDisplay {
        let actualLimit = actualLimitForModel(modelId)

        // Calculate virtual limit from stored content
        let storedTokens = storageService.estimateTotalStoredTokens(conversationId)

        // Minimum 280K virtual limit
        let virtualLimit = max(280_000, storedTokens)

        return VirtualContextDisplay(
            actualModelLimit: actualLimit,
            virtualLimit: virtualLimit,
            currentUsage: storedTokens
        )
    }

    /// Get actual context limit for a model
    static func actualLimitForModel(_ modelId: String?) -> Int {
        guard let modelId = modelId?.lowercased() else {
            return 8_000  // Default
        }

        // Apple Foundation Model
        if modelId.contains("apple") || modelId.contains("fm") || modelId.contains("foundation") {
            return 4_000
        }

        // Claude models
        if modelId.contains("claude") {
            if modelId.contains("opus") || modelId.contains("sonnet") {
                return 200_000
            }
            return 100_000
        }

        // Ollama models (varies widely)
        if modelId.contains("llama") {
            if modelId.contains("70b") {
                return 8_000
            } else if modelId.contains("13b") || modelId.contains("7b") {
                return 4_096
            }
            return 4_096
        }

        if modelId.contains("mistral") {
            return 32_000
        }

        if modelId.contains("codellama") {
            return 16_000
        }

        if modelId.contains("deepseek") {
            return 32_000
        }

        // HuggingFace GGUF models (assume conservative)
        if modelId.contains("gguf") {
            return 4_096
        }

        // Default
        return 8_000
    }

    // MARK: - Budget Calculation

    /// Calculate available budget for new content
    var availableBudget: Int {
        return virtualLimit - currentUsage
    }

    /// Check if there's room for more content
    func canAccommodate(tokens: Int) -> Bool {
        return currentUsage + tokens <= virtualLimit
    }

    /// Estimate tokens from text
    static func estimateTokens(from text: String) -> Int {
        // Rough estimate: ~4 characters per token
        return text.count / 4
    }
}

// MARK: - Virtual Context Budget

/// Token budget allocation for different context components (for virtual context display)
struct VirtualContextBudget {
    let total: Int
    let systemPrompt: Int
    let history: Int
    let ragResults: Int
    let fileContext: Int
    let reserve: Int

    /// Percentage-based initialization
    init(
        total: Int,
        systemPromptPercent: Double = 0.10,
        historyPercent: Double = 0.25,
        ragPercent: Double = 0.30,
        filePercent: Double = 0.25,
        reservePercent: Double = 0.10
    ) {
        self.total = total
        self.systemPrompt = Int(Double(total) * systemPromptPercent)
        self.history = Int(Double(total) * historyPercent)
        self.ragResults = Int(Double(total) * ragPercent)
        self.fileContext = Int(Double(total) * filePercent)
        self.reserve = Int(Double(total) * reservePercent)
    }

    // MARK: - Presets

    /// Budget for Apple Foundation Model (4K context)
    static let appleFM = VirtualContextBudget(total: 4_000)

    /// Budget for small Ollama models (4K-8K context)
    static let ollamaSmall = VirtualContextBudget(total: 8_000)

    /// Budget for medium Ollama models (16K-32K context)
    static let ollamaMedium = VirtualContextBudget(total: 32_000)

    /// Budget for large models (128K context)
    static let ollamaLarge = VirtualContextBudget(total: 128_000)

    /// Budget for HuggingFace GGUF models
    static let huggingFace = VirtualContextBudget(total: 4_096)

    /// Budget for Claude models
    static let claude = VirtualContextBudget(total: 200_000)

    /// Get appropriate budget for a model
    static func forModel(_ modelId: String?) -> VirtualContextBudget {
        let limit = VirtualContextDisplay.actualLimitForModel(modelId)
        return VirtualContextBudget(total: limit)
    }

    // MARK: - Allocation Check

    /// Check if content fits in a specific allocation
    func fits(systemTokens: Int, historyTokens: Int, ragTokens: Int, fileTokens: Int) -> Bool {
        return systemTokens <= systemPrompt &&
               historyTokens <= history &&
               ragTokens <= ragResults &&
               fileTokens <= fileContext
    }

    /// Get remaining space in each allocation
    func remaining(usedSystem: Int, usedHistory: Int, usedRag: Int, usedFile: Int) -> (system: Int, history: Int, rag: Int, file: Int) {
        return (
            system: max(0, systemPrompt - usedSystem),
            history: max(0, history - usedHistory),
            rag: max(0, ragResults - usedRag),
            file: max(0, fileContext - usedFile)
        )
    }
}

// MARK: - Context Stats

/// Statistics about context usage
struct ContextStats {
    let conversationId: UUID
    let totalStoredTokens: Int
    let themeCount: Int
    let semanticNodeCount: Int
    let fileCount: Int
    let hasCompressedContext: Bool
    let lastCompactionAt: Date?

    /// Create stats from storage
    @MainActor
    static func from(
        conversationId: UUID,
        storageService: ConversationStorageService
    ) -> ContextStats {
        let themes = storageService.loadThemes(conversationId)
        let nodes = storageService.loadSemanticNodes(conversationId)
        let files = storageService.loadFileReferences(conversationId)
        let compressed = storageService.loadCompressedContext(conversationId)
        let metadata = storageService.loadMetadata(conversationId)

        return ContextStats(
            conversationId: conversationId,
            totalStoredTokens: storageService.estimateTotalStoredTokens(conversationId),
            themeCount: themes.count,
            semanticNodeCount: nodes.count,
            fileCount: files.count,
            hasCompressedContext: compressed != nil,
            lastCompactionAt: metadata?.compactedAt
        )
    }
}
