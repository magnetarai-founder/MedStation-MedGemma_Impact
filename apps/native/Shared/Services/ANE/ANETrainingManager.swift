//
//  ANETrainingManager.swift
//  MagnetarStudio
//
//  STUB: Not currently wired — future on-device ML training infrastructure.
//  Real on-device CoreML training using CreateML.
//  Addresses Gap 4: MLUpdateTask for incremental model updates.
//

import Foundation
import CoreML
import os

private let logger = Logger(subsystem: "com.magnetarstudio", category: "ANETraining")

// MARK: - ANE Training Manager

@MainActor
final class ANETrainingManager: ObservableObject {

    // MARK: - Published State

    @Published private(set) var isTraining: Bool = false
    @Published private(set) var trainingProgress: Float = 0.0
    @Published private(set) var lastTrainingAt: Date?
    @Published private(set) var exampleCount: Int = 0

    // MARK: - Training Data

    private var trainingExamples: [BehaviorTrainingExample] = []
    private let maxExamples = 500  // Keep last 500 examples
    private let minExamplesForTraining = 50

    // MARK: - Storage

    private let dataURL: URL
    private let modelURL: URL
    private let encoder = JSONEncoder()
    private let decoder = JSONDecoder()

    // MARK: - Singleton

    static let shared = ANETrainingManager()

    // MARK: - Initialization

    init() {
        let documentsPath = (FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory)
        let basePath = documentsPath.appendingPathComponent(".magnetar_studio/user_model")
        self.dataURL = basePath.appendingPathComponent("training_data.json")
        self.modelURL = basePath.appendingPathComponent("UserBehavior.mlmodelc")

        encoder.dateEncodingStrategy = .iso8601
        decoder.dateDecodingStrategy = .iso8601

        loadTrainingData()
    }

    // MARK: - Example Recording

    /// Record a training example from user interaction
    func recordExample(
        features: UserBehaviorFeatures,
        actualOutcome: ContextPredictionOutcome
    ) {
        let example = BehaviorTrainingExample(
            features: features,
            outcome: actualOutcome,
            timestamp: Date()
        )

        trainingExamples.append(example)
        exampleCount = trainingExamples.count

        // Prune old examples
        if trainingExamples.count > maxExamples {
            trainingExamples.removeFirst(trainingExamples.count - maxExamples)
        }

        // Save periodically
        if trainingExamples.count % 10 == 0 {
            saveTrainingData()
        }

        // Train if we have enough examples
        if trainingExamples.count >= minExamplesForTraining &&
           shouldTrain() {
            Task {
                await trainModel()
            }
        }

        logger.debug("[ANETraining] Recorded example, total: \(self.exampleCount)")
    }

    /// Check if we should train (not trained recently)
    private func shouldTrain() -> Bool {
        guard let lastTraining = lastTrainingAt else { return true }
        // Train at most once per hour
        return Date().timeIntervalSince(lastTraining) > 3600
    }

    // MARK: - Feature Extraction

    /// Extract features from current context for training
    func extractFeatures(
        workspace: WorkspaceType,
        query: String?,
        patterns: UserBehaviorPatterns
    ) -> UserBehaviorFeatures {
        let hour = Calendar.current.component(.hour, from: Date())
        let weekday = Calendar.current.component(.weekday, from: Date())

        return UserBehaviorFeatures(
            hourOfDay: hour,
            dayOfWeek: weekday,
            workspace: workspace.rawValue,
            queryLength: query?.count ?? 0,
            recentTopicCount: patterns.recentTopics.count,
            totalEventCount: patterns.totalEvents,
            fileTypeAffinity: patterns.fileTypeAffinities.max(by: { $0.value < $1.value })?.key ?? "unknown"
        )
    }

    // MARK: - Model Training

    /// Train the model using collected examples
    func trainModel() async {
        guard !isTraining else {
            logger.warning("[ANETraining] Already training")
            return
        }

        guard trainingExamples.count >= minExamplesForTraining else {
            logger.info("[ANETraining] Not enough examples: \(self.trainingExamples.count)")
            return
        }

        isTraining = true
        trainingProgress = 0.0

        logger.info("[ANETraining] Starting training with \(self.trainingExamples.count) examples")

        do {
            // Convert examples to training format
            let trainingData = try createTrainingData()
            trainingProgress = 0.2

            // Create or update model
            // Note: Full CreateML training requires macOS
            // For iOS, we use MLUpdateTask for incremental updates
            if FileManager.default.fileExists(atPath: modelURL.path) {
                // Incremental update
                try await incrementalUpdate(with: trainingData)
            } else {
                // Create simple heuristic model (full training requires macOS)
                try await createBaseModel()
            }

            trainingProgress = 1.0
            lastTrainingAt = Date()

            // Notify predictor to reload
            ANEPredictor.shared.reloadModel(from: modelURL)

            logger.info("[ANETraining] Training complete")

        } catch {
            logger.error("[ANETraining] Training failed: \(error)")
        }

        isTraining = false
    }

    /// Create training data from examples
    private func createTrainingData() throws -> [[String: Any]] {
        return trainingExamples.map { example in
            return [
                "hour_of_day": example.features.hourOfDay,
                "day_of_week": example.features.dayOfWeek,
                "workspace": example.features.workspace,
                "query_length": example.features.queryLength,
                "recent_topic_count": example.features.recentTopicCount,
                "total_events": example.features.totalEventCount,
                "compression_aggressiveness": example.outcome.compressionAggressiveness,
                "was_relevant": example.outcome.wasRelevant
            ]
        }
    }

    /// Incremental model update using MLUpdateTask
    private func incrementalUpdate(with data: [[String: Any]]) async throws {
        trainingProgress = 0.4

        // Create batch provider from data
        guard let _ = createBatchProvider(from: data) else {
            throw TrainingError.invalidData
        }

        trainingProgress = 0.6

        // Note: MLUpdateTask requires an updatable model
        // For production, you'd use a properly configured updatable model
        // This is a simplified version

        // Simulate training progress
        for progress in stride(from: 0.6, through: 0.9, by: 0.1) {
            trainingProgress = Float(progress)
            try await Task.sleep(nanoseconds: 100_000_000)  // 0.1 seconds
        }

        logger.info("[ANETraining] Incremental update complete")
    }

    /// Create base model (placeholder for full training)
    private func createBaseModel() async throws {
        trainingProgress = 0.4

        // In production, this would use CreateML to train a real model
        // For now, create a placeholder that the predictor can use

        // Ensure directory exists
        let directory = modelURL.deletingLastPathComponent()
        try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)

        trainingProgress = 0.8

        logger.info("[ANETraining] Base model created (using heuristics)")
    }

    /// Create batch provider for MLUpdateTask
    private func createBatchProvider(from data: [[String: Any]]) -> MLBatchProvider? {
        var featureProviders: [MLFeatureProvider] = []

        for row in data {
            do {
                let features = try MLDictionaryFeatureProvider(dictionary: row.compactMapValues { value -> MLFeatureValue? in
                    if let intValue = value as? Int {
                        return MLFeatureValue(double: Double(intValue))
                    } else if let doubleValue = value as? Double {
                        return MLFeatureValue(double: doubleValue)
                    } else if let floatValue = value as? Float {
                        return MLFeatureValue(double: Double(floatValue))
                    } else if let stringValue = value as? String {
                        return MLFeatureValue(string: stringValue)
                    } else if let boolValue = value as? Bool {
                        return MLFeatureValue(double: boolValue ? 1.0 : 0.0)
                    }
                    return nil
                })
                featureProviders.append(features)
            } catch {
                continue
            }
        }

        guard !featureProviders.isEmpty else { return nil }
        return MLArrayBatchProvider(array: featureProviders)
    }

    // MARK: - Persistence

    private func saveTrainingData() {
        do {
            let directory = dataURL.deletingLastPathComponent()
            try FileManager.default.createDirectory(at: directory, withIntermediateDirectories: true)

            let data = try encoder.encode(trainingExamples)
            try data.write(to: dataURL)
        } catch {
            logger.error("[ANETraining] Failed to save: \(error)")
        }
    }

    private func loadTrainingData() {
        guard let data = try? Data(contentsOf: dataURL) else { return }
        do {
            let examples = try decoder.decode([BehaviorTrainingExample].self, from: data)
            trainingExamples = examples
            exampleCount = examples.count
            logger.info("[ANETraining] Loaded \(examples.count) training examples")
        } catch {
            logger.warning("[ANETraining] Failed to decode training data: \(error)")
        }
    }

    /// Clear all training data
    func clearTrainingData() {
        trainingExamples.removeAll()
        exampleCount = 0
        try? FileManager.default.removeItem(at: dataURL)
        try? FileManager.default.removeItem(at: modelURL)
        lastTrainingAt = nil
        logger.info("[ANETraining] Cleared all training data")
    }

    // MARK: - Errors

    enum TrainingError: LocalizedError {
        case invalidData
        case trainingFailed
        case modelNotUpdatable

        var errorDescription: String? {
            switch self {
            case .invalidData: return "Training data is invalid or insufficient"
            case .trainingFailed: return "Model training failed"
            case .modelNotUpdatable: return "Model does not support on-device updates"
            }
        }
    }
}

// MARK: - Training Models

struct BehaviorTrainingExample: Codable, Sendable {
    let id: UUID
    let features: UserBehaviorFeatures
    let outcome: ContextPredictionOutcome
    let timestamp: Date

    init(
        id: UUID = UUID(),
        features: UserBehaviorFeatures,
        outcome: ContextPredictionOutcome,
        timestamp: Date = Date()
    ) {
        self.id = id
        self.features = features
        self.outcome = outcome
        self.timestamp = timestamp
    }
}

struct UserBehaviorFeatures: Codable, Sendable {
    let hourOfDay: Int
    let dayOfWeek: Int
    let workspace: String
    let queryLength: Int
    let recentTopicCount: Int
    let totalEventCount: Int
    let fileTypeAffinity: String
}

struct ContextPredictionOutcome: Codable, Sendable {
    let compressionAggressiveness: Float
    let wasRelevant: Bool
    let contextUsed: Int  // Tokens of context actually used
    let responseQuality: Float?  // User feedback if available
}
