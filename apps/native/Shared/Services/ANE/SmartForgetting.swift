//
//  SmartForgetting.swift
//  MagnetarStudio
//
//  Learned compression that adapts to user patterns.
//  Unlike rule-based forgetting, this learns what each user considers important.
//

import Foundation
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "SmartForgetting")

// MARK: - Smart Forgetting

@MainActor
final class SmartForgetting: ObservableObject {

    // MARK: - Published State

    @Published private(set) var forgettingThresholds: ForgettingThresholds = ForgettingThresholds()
    @Published private(set) var compressionStats: CompressionStats = CompressionStats()

    // MARK: - Dependencies

    private let behaviorTracker: UserBehaviorTracker
    private let predictor: ANEPredictor

    // MARK: - Storage

    private let storageURL: URL
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    // MARK: - Singleton

    static let shared = SmartForgetting()

    // MARK: - Initialization

    init(
        behaviorTracker: UserBehaviorTracker? = nil,
        predictor: ANEPredictor? = nil
    ) {
        self.behaviorTracker = behaviorTracker ?? .shared
        self.predictor = predictor ?? .shared

        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        self.storageURL = documentsPath.appendingPathComponent(".magnetar_studio/user_model/forgetting_thresholds.json")

        loadThresholds()
    }

    // MARK: - Compression Decision

    /// Decide what to keep vs compress for a set of semantic nodes
    func decideCompression(
        nodes: [SemanticNode],
        currentQuery: String?,
        sessionId: UUID
    ) -> CompressionDecision {
        var toKeep: [UUID] = []
        var toCompress: [UUID] = []
        var toArchive: [UUID] = []

        // Get prediction for compression aggressiveness
        let prediction = predictor.predictContextNeeds(
            currentWorkspace: .chat,
            recentQuery: currentQuery,
            activeFileId: nil
        )

        let aggressiveness = prediction.compressionAggressiveness

        for node in nodes {
            let importance = calculateImportance(node: node)

            // Apply learned thresholds
            let threshold = forgettingThresholds.thresholdFor(tier: node.tier)
            let adjustedThreshold = threshold * (1.0 - aggressiveness * 0.3)

            if importance >= adjustedThreshold {
                toKeep.append(node.id)
            } else if importance >= adjustedThreshold * 0.5 {
                toCompress.append(node.id)
            } else {
                toArchive.append(node.id)
            }
        }

        // NEVER forget certain types of content
        for node in nodes {
            if shouldNeverForget(node) && !toKeep.contains(node.id) {
                toKeep.append(node.id)
                toCompress.removeAll { $0 == node.id }
                toArchive.removeAll { $0 == node.id }
            }
        }

        return CompressionDecision(
            toKeep: toKeep,
            toCompress: toCompress,
            toArchive: toArchive,
            aggressiveness: aggressiveness
        )
    }

    // MARK: - Importance Calculation

    /// Calculate importance score for a node (0.0 - 1.0)
    private func calculateImportance(node: SemanticNode) -> Float {
        var score: Float = 0.0
        let patterns = behaviorTracker.currentPatterns

        // Recency factor (more recent = more important)
        let hoursSinceAccess = Date().timeIntervalSince(node.lastAccessed) / 3600
        let recencyScore = Float(max(0, 1.0 - (hoursSinceAccess / 168)))  // Decay over 1 week
        score += recencyScore * 0.25

        // Has structured data (decisions, todos) = important
        if node.hasStructuredData {
            score += 0.3
        }

        // Has code references = important for developers
        if let codeRefs = node.codeRefs, !codeRefs.isEmpty {
            score += 0.2
        }

        // Has file references = might need to reference again
        if let fileRefs = node.fileRefs, !fileRefs.isEmpty {
            score += 0.1
        }

        // Topic matches user's frequent topics
        for topic in patterns.recentTopics.prefix(5) {
            if node.concept.lowercased().contains(topic.lowercased()) {
                score += 0.1
                break
            }
        }

        // Entity importance (entities user frequently mentions)
        for entity in node.entities {
            if patterns.recentTopics.contains(where: { $0.lowercased() == entity.lowercased() }) {
                score += 0.05
            }
        }

        return min(1.0, score)
    }

    // MARK: - Never Forget Rules

    /// Check if content should never be forgotten
    private func shouldNeverForget(_ node: SemanticNode) -> Bool {
        // Never forget outstanding TODOs
        if let todos = node.todos, todos.contains(where: { !$0.completed }) {
            return true
        }

        // Never forget recent decisions
        if let decisions = node.decisions,
           let recentDecision = decisions.first,
           Date().timeIntervalSince(recentDecision.madeAt) < 86400 * 7 {  // Within 1 week
            return true
        }

        // Never forget code snippets user was actively working on
        if let codeRefs = node.codeRefs,
           !codeRefs.isEmpty,
           Date().timeIntervalSince(node.lastAccessed) < 3600 * 24 {  // Within 24 hours
            return true
        }

        // Never forget workflow-related context
        if let workflowRefs = node.workflowRefs, !workflowRefs.isEmpty {
            return true
        }

        return false
    }

    // MARK: - Learning

    /// Record a forgetting outcome for learning
    func recordForgettingOutcome(
        nodeId: UUID,
        wasRetrieved: Bool,
        retrievalDelay: TimeInterval?
    ) {
        compressionStats.totalCompressions += 1

        if wasRetrieved {
            compressionStats.retrievalsAfterCompression += 1

            // User needed this content - adjust thresholds
            adjustThresholds(direction: .lessAggressive)
        }

        saveThresholds()
    }

    /// Adjust thresholds based on feedback
    private func adjustThresholds(direction: ThresholdAdjustment) {
        let delta: Float = 0.02

        switch direction {
        case .moreAggressive:
            forgettingThresholds.immediateThreshold = max(0.3, forgettingThresholds.immediateThreshold - delta)
            forgettingThresholds.themeThreshold = max(0.2, forgettingThresholds.themeThreshold - delta)
            forgettingThresholds.compressedThreshold = max(0.1, forgettingThresholds.compressedThreshold - delta)

        case .lessAggressive:
            forgettingThresholds.immediateThreshold = min(0.9, forgettingThresholds.immediateThreshold + delta)
            forgettingThresholds.themeThreshold = min(0.8, forgettingThresholds.themeThreshold + delta)
            forgettingThresholds.compressedThreshold = min(0.7, forgettingThresholds.compressedThreshold + delta)
        }

        logger.debug("[SmartForgetting] Adjusted thresholds: \(direction)")
    }

    enum ThresholdAdjustment: CustomStringConvertible {
        case moreAggressive
        case lessAggressive

        var description: String {
            switch self {
            case .moreAggressive: return "more aggressive"
            case .lessAggressive: return "less aggressive"
            }
        }
    }

    // MARK: - Persistence

    private func saveThresholds() {
        do {
            let directory = storageURL.deletingLastPathComponent()
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)

            let data = try encoder.encode(forgettingThresholds)
            try data.write(to: storageURL)
        } catch {
            logger.error("[SmartForgetting] Failed to save: \(error)")
        }
    }

    private func loadThresholds() {
        guard let data = try? Data(contentsOf: storageURL),
              let thresholds = try? decoder.decode(ForgettingThresholds.self, from: data) else {
            return
        }
        forgettingThresholds = thresholds
    }

    /// Reset to default thresholds
    func resetThresholds() {
        forgettingThresholds = ForgettingThresholds()
        compressionStats = CompressionStats()
        try? FileManager.default.removeItem(at: storageURL)
        logger.info("[SmartForgetting] Reset to defaults")
    }
}

// MARK: - Compression Decision

struct CompressionDecision {
    let toKeep: [UUID]
    let toCompress: [UUID]
    let toArchive: [UUID]
    let aggressiveness: Float

    var totalNodes: Int {
        return toKeep.count + toCompress.count + toArchive.count
    }

    var keepPercentage: Float {
        guard totalNodes > 0 else { return 0 }
        return Float(toKeep.count) / Float(totalNodes) * 100
    }
}

// MARK: - Forgetting Thresholds

struct ForgettingThresholds: Codable {
    /// Threshold for keeping in immediate tier (default 0.6)
    var immediateThreshold: Float = 0.6

    /// Threshold for keeping as theme (default 0.4)
    var themeThreshold: Float = 0.4

    /// Threshold for compressed vs archived (default 0.2)
    var compressedThreshold: Float = 0.2

    /// Never forget content newer than this (hours)
    var minAgeHours: Int = 2

    /// Per-topic thresholds (learned)
    var topicThresholds: [String: Float] = [:]

    func thresholdFor(tier: ContextTier) -> Float {
        switch tier {
        case .immediate:
            return immediateThreshold
        case .themes:
            return themeThreshold
        case .graph, .compressed:
            return compressedThreshold
        case .archived:
            return 0.1
        }
    }
}

// MARK: - Compression Stats

struct CompressionStats: Codable {
    var totalCompressions: Int = 0
    var retrievalsAfterCompression: Int = 0
    var tokensCompressed: Int = 0
    var tokensSaved: Int = 0

    var retrievalRate: Float {
        guard totalCompressions > 0 else { return 0 }
        return Float(retrievalsAfterCompression) / Float(totalCompressions)
    }
}
