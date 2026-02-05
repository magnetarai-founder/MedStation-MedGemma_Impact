//
//  ANEPredictor.swift
//  MagnetarStudio
//
//  CoreML-based predictions for context needs using Apple Neural Engine.
//  Falls back to heuristics when model isn't trained.
//

import Foundation
import CoreML
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "ANEPredictor")

// MARK: - ANE Predictor

@MainActor
final class ANEPredictor: ObservableObject {

    // MARK: - Published State

    @Published private(set) var isModelLoaded: Bool = false
    @Published private(set) var predictionCount: Int = 0
    @Published private(set) var lastPredictionAt: Date?

    // MARK: - Dependencies

    private let behaviorTracker: UserBehaviorTracker
    private var mlModel: MLModel?

    // MARK: - Configuration

    /// Minimum confidence for predictions
    let minConfidence: Float = 0.5

    /// Use heuristics when model unavailable
    let useHeuristicFallback = true

    // MARK: - Singleton

    static let shared = ANEPredictor()

    // MARK: - Initialization

    init(behaviorTracker: UserBehaviorTracker? = nil) {
        self.behaviorTracker = behaviorTracker ?? .shared
        loadModel()
    }

    // MARK: - Model Loading

    private func loadModel() {
        // Try to load trained model
        let modelURL = getModelURL()

        if FileManager.default.fileExists(atPath: modelURL.path) {
            do {
                let config = MLModelConfiguration()
                config.computeUnits = .all  // Use ANE when available
                mlModel = try MLModel(contentsOf: modelURL, configuration: config)
                isModelLoaded = true
                logger.info("[ANEPredictor] Loaded trained model")
            } catch {
                logger.warning("[ANEPredictor] Failed to load model: \(error)")
                isModelLoaded = false
            }
        } else {
            logger.info("[ANEPredictor] No trained model, using heuristics")
            isModelLoaded = false
        }
    }

    /// Reload model (after training update)
    func reloadModel(from url: URL? = nil) {
        let modelURL = url ?? getModelURL()

        do {
            let config = MLModelConfiguration()
            config.computeUnits = .all
            mlModel = try MLModel(contentsOf: modelURL, configuration: config)
            isModelLoaded = true
            logger.info("[ANEPredictor] Reloaded model")
        } catch {
            logger.error("[ANEPredictor] Failed to reload: \(error)")
        }
    }

    private func getModelURL() -> URL {
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        return documentsPath.appendingPathComponent(".magnetar_studio/user_model/UserBehavior.mlmodelc")
    }

    // MARK: - Predictions

    /// Predict context needs for current situation
    func predictContextNeeds(
        currentWorkspace: WorkspaceType,
        recentQuery: String?,
        activeFileId: UUID?
    ) -> ContextPrediction {
        predictionCount += 1
        lastPredictionAt = Date()

        if isModelLoaded, let model = mlModel {
            return predictWithModel(
                model: model,
                workspace: currentWorkspace,
                query: recentQuery,
                fileId: activeFileId
            )
        } else if useHeuristicFallback {
            return predictWithHeuristics(
                workspace: currentWorkspace,
                query: recentQuery,
                fileId: activeFileId
            )
        } else {
            return ContextPrediction.empty
        }
    }

    // MARK: - ML Model Prediction

    private func predictWithModel(
        model: MLModel,
        workspace: WorkspaceType,
        query: String?,
        fileId: UUID?
    ) -> ContextPrediction {
        do {
            // Build feature provider
            let features = try buildFeatures(workspace: workspace, query: query, fileId: fileId)
            let prediction = try model.prediction(from: features)

            // Parse prediction outputs
            return parseModelOutput(prediction)
        } catch {
            logger.warning("[ANEPredictor] Model prediction failed: \(error)")
            return predictWithHeuristics(workspace: workspace, query: query, fileId: fileId)
        }
    }

    private func buildFeatures(
        workspace: WorkspaceType,
        query: String?,
        fileId: UUID?
    ) throws -> MLFeatureProvider {
        let patterns = behaviorTracker.currentPatterns
        let hour = Calendar.current.component(.hour, from: Date())
        let weekday = Calendar.current.component(.weekday, from: Date())

        // Simple feature dictionary
        let features: [String: MLFeatureValue] = [
            "hour_of_day": MLFeatureValue(double: Double(hour)),
            "day_of_week": MLFeatureValue(double: Double(weekday)),
            "workspace": MLFeatureValue(string: workspace.rawValue),
            "total_events": MLFeatureValue(double: Double(patterns.totalEvents)),
            "query_length": MLFeatureValue(double: Double(query?.count ?? 0)),
            "has_active_file": MLFeatureValue(double: fileId != nil ? 1.0 : 0.0)
        ]

        return try MLDictionaryFeatureProvider(dictionary: features)
    }

    private func parseModelOutput(_ output: MLFeatureProvider) -> ContextPrediction {
        // Extract predictions from model output
        let likelyTopics: [String] = []
        let likelyFileNeeds: [UUID] = []
        var compressionAggressiveness: Float = 0.5
        let preloadSuggestions: [UUID] = []

        // Parse based on model output schema
        if output.featureValue(for: "likely_topics")?.multiArrayValue != nil {
            // Parse topics from multiarray - currently a placeholder
        }

        if let compression = output.featureValue(for: "compression_aggressiveness")?.doubleValue {
            compressionAggressiveness = Float(compression)
        }

        return ContextPrediction(
            likelyTopics: likelyTopics,
            likelyFileNeeds: likelyFileNeeds,
            compressionAggressiveness: compressionAggressiveness,
            preloadSuggestions: preloadSuggestions,
            confidence: 0.8,
            source: .mlModel
        )
    }

    // MARK: - Heuristic Prediction

    private func predictWithHeuristics(
        workspace: WorkspaceType,
        query: String?,
        fileId: UUID?
    ) -> ContextPrediction {
        let patterns = behaviorTracker.currentPatterns

        var likelyTopics: [String] = []
        var compressionAggressiveness: Float = 0.5

        // Use recent topics
        likelyTopics = Array(patterns.recentTopics.prefix(5))

        // Adjust compression based on activity patterns
        if behaviorTracker.isCurrentlyPeakTime() {
            // Less aggressive during peak times - user is active
            compressionAggressiveness = 0.3
        } else {
            // More aggressive during off-peak
            compressionAggressiveness = 0.7
        }

        // Workspace-specific predictions
        switch workspace {
        case .chat:
            // In chat, likely to need recent conversation context
            compressionAggressiveness = 0.4

        case .data:
            // In data tab, likely to discuss datasets
            likelyTopics.append("data analysis")
            likelyTopics.append("query")

        case .code:
            // In code, preserve code-related context
            likelyTopics.append("code")
            likelyTopics.append("function")
            compressionAggressiveness = 0.3  // Don't forget code discussions

        case .vault:
            // In vault, file context is important
            compressionAggressiveness = 0.4

        case .workflow:
            likelyTopics.append("automation")
            likelyTopics.append("workflow")

        case .kanban:
            likelyTopics.append("task")
            likelyTopics.append("project")

        default:
            break
        }

        return ContextPrediction(
            likelyTopics: likelyTopics,
            likelyFileNeeds: [],
            compressionAggressiveness: compressionAggressiveness,
            preloadSuggestions: [],
            confidence: 0.6,
            source: .heuristics
        )
    }

    // MARK: - Relevance Scoring

    /// Score relevance of a semantic node for current context
    func scoreRelevance(
        node: SemanticNode,
        query: String,
        queryEmbedding: [Float]
    ) -> Float {
        let patterns = behaviorTracker.currentPatterns

        // Base similarity score
        let similarity = HashEmbedder.cosineSimilarity(node.embedding, queryEmbedding)

        // Recency score (decay over time)
        let hoursSinceAccess = Date().timeIntervalSince(node.lastAccessed) / 3600
        let recencyScore = Float(max(0, 1.0 - (hoursSinceAccess / 168)))  // Decay over 1 week

        // Entity overlap score
        let queryWords = Set(query.lowercased().components(separatedBy: .whitespacesAndNewlines))
        let nodeEntities = Set(node.entities.map { $0.lowercased() })
        let entityOverlap = Float(queryWords.intersection(nodeEntities).count) / Float(max(1, nodeEntities.count))

        // User pattern score (boost topics user frequently discusses)
        var patternScore: Float = 0.0
        for topic in patterns.recentTopics.prefix(10) {
            if node.concept.lowercased().contains(topic.lowercased()) {
                patternScore += 0.1
            }
        }
        patternScore = min(1.0, patternScore)

        // Weighted combination
        return (similarity * 0.4) +
               (recencyScore * 0.3) +
               (entityOverlap * 0.2) +
               (patternScore * 0.1)
    }
}

// MARK: - Context Prediction

struct ContextPrediction {
    let likelyTopics: [String]
    let likelyFileNeeds: [UUID]
    let compressionAggressiveness: Float  // 0.0 = keep everything, 1.0 = compress hard
    let preloadSuggestions: [UUID]
    let confidence: Float
    let source: PredictionSource

    enum PredictionSource {
        case mlModel
        case heuristics
        case none
    }

    static let empty = ContextPrediction(
        likelyTopics: [],
        likelyFileNeeds: [],
        compressionAggressiveness: 0.5,
        preloadSuggestions: [],
        confidence: 0.0,
        source: .none
    )
}

// MARK: - Workspace Type

enum WorkspaceType: String, Codable, CaseIterable {
    case chat
    case data
    case code
    case vault
    case workflow
    case kanban
    case team
    case docs
    case insights
    case settings
    case hub  // MagnetarHub (model management)

    var displayName: String {
        switch self {
        case .chat: return "AI Chat"
        case .data: return "Data"
        case .code: return "Code"
        case .vault: return "Vault"
        case .workflow: return "Workflow"
        case .kanban: return "Kanban"
        case .team: return "Team"
        case .docs: return "Docs"
        case .insights: return "Insights"
        case .settings: return "Settings"
        case .hub: return "MagnetarHub"
        }
    }
}
