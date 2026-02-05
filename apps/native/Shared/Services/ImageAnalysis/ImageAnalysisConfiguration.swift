import Foundation
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "ImageAnalysisConfig")

/// Configuration for image analysis pipeline
struct ImageAnalysisConfiguration: Codable, Sendable {
    var enabledLayers: Set<AnalysisLayerType>
    var maxConcurrentLayers: Int
    var preferAccuracyOverSpeed: Bool
    var cacheResults: Bool
    var generateEmbeddings: Bool
    var thermalThrottling: Bool

    /// Check if running on Simulator (CoreML may crash)
    private static var isSimulator: Bool {
        #if targetEnvironment(simulator)
        return true
        #else
        return false
        #endif
    }

    /// Default configuration - fast, essential layers
    /// Note: On Simulator, CoreML-based layers are disabled to prevent crashes
    static let `default`: ImageAnalysisConfiguration = {
        if isSimulator {
            // Simulator-safe: only Vision framework (no CoreML models)
            return ImageAnalysisConfiguration(
                enabledLayers: [.vision],
                maxConcurrentLayers: 2,
                preferAccuracyOverSpeed: false,
                cacheResults: true,
                generateEmbeddings: false,
                thermalThrottling: false
            )
        }
        return ImageAnalysisConfiguration(
            enabledLayers: [.vision, .objectDetection, .structuredOutput],
            maxConcurrentLayers: 3,
            preferAccuracyOverSpeed: false,
            cacheResults: true,
            generateEmbeddings: true,
            thermalThrottling: true
        )
    }()

    /// Comprehensive - all layers enabled (Simulator: Vision only)
    static let comprehensive: ImageAnalysisConfiguration = {
        if isSimulator {
            return ImageAnalysisConfiguration(
                enabledLayers: [.vision],
                maxConcurrentLayers: 2,
                preferAccuracyOverSpeed: false,
                cacheResults: true,
                generateEmbeddings: false,
                thermalThrottling: false
            )
        }
        return ImageAnalysisConfiguration(
            enabledLayers: Set(AnalysisLayerType.allCases),
            maxConcurrentLayers: 2,
            preferAccuracyOverSpeed: true,
            cacheResults: true,
            generateEmbeddings: true,
            thermalThrottling: true
        )
    }()

    /// Fast - minimal processing (Simulator: Vision only)
    static let fast: ImageAnalysisConfiguration = {
        if isSimulator {
            return ImageAnalysisConfiguration(
                enabledLayers: [.vision],
                maxConcurrentLayers: 2,
                preferAccuracyOverSpeed: false,
                cacheResults: true,
                generateEmbeddings: false,
                thermalThrottling: false
            )
        }
        return ImageAnalysisConfiguration(
            enabledLayers: [.vision, .objectDetection],
            maxConcurrentLayers: 4,
            preferAccuracyOverSpeed: false,
            cacheResults: true,
            generateEmbeddings: false,
            thermalThrottling: false
        )
    }()

    /// Document focused - optimized for documents and text (Simulator: Vision only)
    static let document: ImageAnalysisConfiguration = {
        if isSimulator {
            return ImageAnalysisConfiguration(
                enabledLayers: [.vision],
                maxConcurrentLayers: 2,
                preferAccuracyOverSpeed: false,
                cacheResults: true,
                generateEmbeddings: false,
                thermalThrottling: false
            )
        }
        return ImageAnalysisConfiguration(
            enabledLayers: [.vision, .structuredOutput],
            maxConcurrentLayers: 2,
            preferAccuracyOverSpeed: true,
            cacheResults: true,
            generateEmbeddings: true,
            thermalThrottling: true
        )
    }()

    /// Estimated total processing time in milliseconds
    var estimatedDurationMs: Int {
        enabledLayers.reduce(0) { $0 + $1.estimatedDurationMs }
    }

    /// Check if a specific layer is enabled
    func isEnabled(_ layer: AnalysisLayerType) -> Bool {
        enabledLayers.contains(layer)
    }

    /// Create a throttled configuration for high thermal states
    func throttled() -> ImageAnalysisConfiguration {
        ImageAnalysisConfiguration(
            enabledLayers: [.vision, .structuredOutput],
            maxConcurrentLayers: 1,
            preferAccuracyOverSpeed: false,
            cacheResults: cacheResults,
            generateEmbeddings: generateEmbeddings,
            thermalThrottling: true
        )
    }
}

// MARK: - UserDefaults Storage

extension ImageAnalysisConfiguration {
    private static let userDefaultsKey = "magnetar.imageAnalysisConfig"

    /// Load saved configuration from UserDefaults
    /// Note: On Simulator, CoreML layers are always stripped to prevent crashes
    static func loadSaved() -> ImageAnalysisConfiguration {
        guard let data = UserDefaults.standard.data(forKey: userDefaultsKey),
              var config = try? JSONDecoder().decode(ImageAnalysisConfiguration.self, from: data) else {
            return .default
        }

        // On Simulator, strip CoreML-dependent layers from saved config
        if isSimulator {
            config = config.simulatorSafe()
        }

        return config
    }

    /// CoreML-dependent layer types that don't work on Simulator
    private static let coreMLLayers: Set<AnalysisLayerType> = [
        .objectDetection, .segmentation, .depth, .structuredOutput
    ]

    /// Create a Simulator-safe version of this configuration
    func simulatorSafe() -> ImageAnalysisConfiguration {
        ImageAnalysisConfiguration(
            enabledLayers: enabledLayers.subtracting(Self.coreMLLayers),
            maxConcurrentLayers: min(maxConcurrentLayers, 2),
            preferAccuracyOverSpeed: false,
            cacheResults: cacheResults,
            generateEmbeddings: false,
            thermalThrottling: false
        )
    }

    /// Save configuration to UserDefaults
    func save() {
        do {
            let data = try JSONEncoder().encode(self)
            UserDefaults.standard.set(data, forKey: Self.userDefaultsKey)
        } catch {
            logger.error("[ImageConfig] Failed to save configuration: \(error.localizedDescription)")
        }
    }
}
