//
//  ImageAnalysisService.swift
//  MedStation
//
//  Complete 5-layer ML pipeline (Vision, Object Detection, Segmentation, Depth, Structured Output).
//  Wired: ChatStore.analyzeImageForContext() calls analyze() and generates AI context string.
//

import Foundation
import CryptoKit
import os

#if canImport(AppKit)
import AppKit
#endif

private let logger = Logger(subsystem: "com.medstation.app", category: "ImageAnalysis")

/// Main orchestrator for multi-layer image analysis
/// Coordinates Vision, Object Detection, Segmentation, Depth, and Structured Output layers
@MainActor
@Observable
final class ImageAnalysisService {

    // MARK: - Dependencies

    private let visionLayer = VisionAnalysisLayer()
    private let objectDetectionLayer = ObjectDetectionLayer()
    private let segmentationLayer = SegmentationLayer()
    private let depthLayer = DepthEstimationLayer()
    private let structuredOutputLayer = StructuredOutputLayer()

    private let cache = ImageAnalysisCache.shared

    // MARK: - State

    private(set) var isAnalyzing: Bool = false
    private(set) var currentProgress: Float = 0
    private(set) var currentLayer: AnalysisLayerType?
    private(set) var lastAnalysisResult: ImageAnalysisResult?

    var configuration: ImageAnalysisConfiguration = .loadSaved()

    // MARK: - Singleton

    static let shared = ImageAnalysisService()

    private init() {
        logger.info("[ImageAnalysis] Service initialized")
    }

    // MARK: - Analysis

    /// Check if running on Simulator (CoreML may crash)
    private static var isSimulator: Bool {
        #if targetEnvironment(simulator)
        return true
        #else
        return false
        #endif
    }

    /// Analyze an image with the configured layers
    func analyze(
        _ image: PlatformImage,
        configuration: ImageAnalysisConfiguration? = nil
    ) async throws -> ImageAnalysisResult {
        var config = configuration ?? self.configuration
        let startTime = Date()

        // On Simulator, force safe configuration to prevent CoreML crashes
        if Self.isSimulator {
            config = config.simulatorSafe()
            logger.debug("[ImageAnalysis] Running on Simulator - using Vision-only analysis")
        }

        guard !config.enabledLayers.isEmpty else {
            throw ImageAnalysisError.noLayersEnabled
        }

        // Generate image hash for caching
        let imageHash = generateImageHash(image)

        // Check cache
        if config.cacheResults, let cached = cache.get(hash: imageHash) {
            logger.debug("[ImageAnalysis] Cache hit for \(imageHash.prefix(8))")
            lastAnalysisResult = cached
            return cached
        }

        isAnalyzing = true
        currentProgress = 0

        defer {
            isAnalyzing = false
            currentProgress = 0
            currentLayer = nil
        }

        // Check thermal state and potentially throttle
        let thermalState = ProcessInfo.processInfo.thermalState
        var effectiveConfig = config

        // Thermal states: nominal=0, fair=1, serious=2, critical=3
        if config.thermalThrottling && thermalState.rawValue >= ProcessInfo.ThermalState.serious.rawValue {
            logger.warning("[ImageAnalysis] Thermal throttling active")
            effectiveConfig = config.throttled()
        }

        // Execute analysis layers
        let results = try await executeLayersInParallel(image: image, config: effectiveConfig)

        // Build final result
        let processingDuration = Date().timeIntervalSince(startTime)

        var result = ImageAnalysisResult(
            imageHash: imageHash,
            processingDuration: processingDuration,
            documentContent: results.documentContent,
            recognizedText: results.recognizedText,
            detectedBarcodes: results.barcodes,
            detectedObjects: results.detectedObjects,
            segmentationMasks: results.segmentationMasks,
            depthMap: results.depthMap,
            structuredDescription: results.structuredDescription ?? .empty,
            layersExecuted: results.executedLayers,
            failedLayers: results.failedLayers,
            layerTimings: results.timings,
            deviceThermalState: .init(from: thermalState)
        )

        // Generate searchable text and tags
        result = result.withSearchableText(result.generateSearchableText())
        result = result.withTags(result.generateTags())

        // Generate embedding if enabled
        if config.generateEmbeddings {
            let embedding = await generateEmbedding(for: result.searchableText)
            result = result.withEmbedding(embedding)
        }

        // Cache result
        if config.cacheResults {
            cache.store(result, hash: imageHash)
        }

        lastAnalysisResult = result

        logger.info("[ImageAnalysis] Completed in \(String(format: "%.2f", processingDuration))s with \(results.executedLayers.count) layers")

        return result
    }

    /// Quick analysis with only essential layers
    func quickAnalyze(_ image: PlatformImage) async throws -> ImageAnalysisResult {
        try await analyze(image, configuration: .fast)
    }

    /// Comprehensive analysis with all layers
    func comprehensiveAnalyze(_ image: PlatformImage) async throws -> ImageAnalysisResult {
        try await analyze(image, configuration: .comprehensive)
    }

    // MARK: - Parallel Execution

    private struct LayerResults: Sendable {
        var documentContent: DocumentAnalysisResult?
        var recognizedText: [RecognizedTextBlock] = []
        var barcodes: [BarcodeResult] = []
        var detectedObjects: [DetectedObject] = []
        var segmentationMasks: [SegmentationMask]?
        var depthMap: DepthMapResult?
        var structuredDescription: StructuredImageDescription?
        var executedLayers: [AnalysisLayerType] = []
        var failedLayers: [AnalysisLayerType] = []
        var timings: [AnalysisLayerType: TimeInterval] = [:]
    }

    /// Result from a single layer execution
    private enum LayerOutput: Sendable {
        case vision(DocumentAnalysisResult?, [RecognizedTextBlock], [BarcodeResult], TimeInterval)
        case objectDetection([DetectedObject], TimeInterval)
        case segmentation([SegmentationMask]?, TimeInterval)
        case depth(DepthMapResult?, TimeInterval)
        case structuredOutput(StructuredImageDescription?, TimeInterval)
        case failed(AnalysisLayerType)
    }

    private func executeLayersInParallel(
        image: PlatformImage,
        config: ImageAnalysisConfiguration
    ) async throws -> LayerResults {
        var results = LayerResults()
        let enabledLayers = Array(config.enabledLayers)
        let totalLayers = Float(enabledLayers.count)
        var completedCount = 0

        // Group 1: Vision + Object Detection (can run in parallel - different hardware)
        // Each task returns its result; we merge after completion
        let group1Results = await withTaskGroup(of: LayerOutput.self) { group -> [LayerOutput] in
            // Vision Framework layer
            if config.isEnabled(.vision) {
                group.addTask {
                    let start = Date()
                    do {
                        let visionResult = try await self.visionLayer.analyze(image)
                        return .vision(
                            visionResult.documentContent,
                            visionResult.textBlocks,
                            visionResult.barcodes,
                            Date().timeIntervalSince(start)
                        )
                    } catch {
                        logger.error("[ImageAnalysis] Vision layer failed: \(error.localizedDescription)")
                        return .failed(.vision)
                    }
                }
            }

            // Object Detection layer
            if config.isEnabled(.objectDetection) {
                group.addTask {
                    let start = Date()
                    do {
                        let objects = try await self.objectDetectionLayer.detect(in: image)
                        return .objectDetection(objects, Date().timeIntervalSince(start))
                    } catch {
                        logger.error("[ImageAnalysis] Object detection failed: \(error.localizedDescription)")
                        return .failed(.objectDetection)
                    }
                }
            }

            // Collect all results
            var outputs: [LayerOutput] = []
            for await output in group {
                outputs.append(output)
            }
            return outputs
        }

        // Merge Group 1 results
        for output in group1Results {
            switch output {
            case .vision(let doc, let text, let barcodes, let timing):
                results.documentContent = doc
                results.recognizedText = text
                results.barcodes = barcodes
                results.executedLayers.append(.vision)
                results.timings[.vision] = timing
                completedCount += 1
                currentLayer = .vision
                currentProgress = Float(completedCount) / totalLayers

            case .objectDetection(let objects, let timing):
                results.detectedObjects = objects
                results.executedLayers.append(.objectDetection)
                results.timings[.objectDetection] = timing
                completedCount += 1
                currentLayer = .objectDetection
                currentProgress = Float(completedCount) / totalLayers

            case .failed(let layer):
                results.failedLayers.append(layer)
                completedCount += 1
                currentProgress = Float(completedCount) / totalLayers
                logger.warning("[ImageAnalysis] Layer \(layer.rawValue) failed, continuing")

            default:
                break
            }
        }

        // Group 2: Segmentation + Depth (sequential - compete for ANE)
        if config.isEnabled(.segmentation) {
            let start = Date()
            currentLayer = .segmentation

            do {
                let masks = try await segmentationLayer.segment(image, hints: results.detectedObjects)
                results.segmentationMasks = masks
                results.executedLayers.append(.segmentation)
                results.timings[.segmentation] = Date().timeIntervalSince(start)
            } catch {
                results.failedLayers.append(.segmentation)
                logger.error("[ImageAnalysis] Segmentation failed: \(error.localizedDescription)")
            }

            completedCount += 1
            currentProgress = Float(completedCount) / totalLayers
        }

        if config.isEnabled(.depth) {
            let start = Date()
            currentLayer = .depth

            do {
                let depth = try await depthLayer.estimateDepth(in: image)
                results.depthMap = depth
                results.executedLayers.append(.depth)
                results.timings[.depth] = Date().timeIntervalSince(start)
            } catch {
                results.failedLayers.append(.depth)
                logger.error("[ImageAnalysis] Depth estimation failed: \(error.localizedDescription)")
            }

            completedCount += 1
            currentProgress = Float(completedCount) / totalLayers
        }

        // Group 3: Structured Output (last - uses results from other layers)
        if config.isEnabled(.structuredOutput) {
            let start = Date()
            currentLayer = .structuredOutput

            do {
                let context = StructuredOutputContext(
                    detectedObjects: results.detectedObjects,
                    recognizedText: results.recognizedText,
                    documentContent: results.documentContent
                )

                let structured = try await structuredOutputLayer.generate(for: image, context: context)
                results.structuredDescription = structured
                results.executedLayers.append(.structuredOutput)
                results.timings[.structuredOutput] = Date().timeIntervalSince(start)
            } catch {
                results.failedLayers.append(.structuredOutput)
                logger.error("[ImageAnalysis] Structured output failed: \(error.localizedDescription)")
            }

            completedCount += 1
            currentProgress = Float(completedCount) / totalLayers
        }

        return results
    }

    // MARK: - Helpers

    private func generateImageHash(_ image: PlatformImage) -> String {
        guard let data = image.jpegDataCrossPlatform(compressionQuality: 0.5) else {
            return UUID().uuidString
        }

        let hash = SHA256.hash(data: data)
        return hash.compactMap { String(format: "%02x", $0) }.joined()
    }

    private func generateEmbedding(for text: String) async -> [Float] {
        // Use the existing HashEmbedder from the RAG system
        // This will be integrated with the actual embedder in the RAG integration phase
        return []
    }

    // MARK: - Model Management

    /// Preload models for faster first analysis
    func preloadModels() async {
        logger.info("[ImageAnalysis] Preloading models...")

        do {
            try await objectDetectionLayer.loadModel()
        } catch {
            logger.warning("[ImageAnalysis] Failed to preload object detection: \(error.localizedDescription)")
        }

        // Segmentation and depth models are loaded on-demand
    }

    /// Check which models are available
    func availableModels() async -> [AnalysisLayerType: Bool] {
        var availability: [AnalysisLayerType: Bool] = [:]

        availability[.vision] = true  // Always available on iOS
        availability[.objectDetection] = await objectDetectionLayer.isModelReady()
        availability[.segmentation] = await segmentationLayer.isModelReady()
        availability[.depth] = await depthLayer.isModelReady()
        availability[.structuredOutput] = true  // Uses Apple FM, always available

        return availability
    }
}

// MARK: - Convenience Extensions

extension ImageAnalysisService {
    /// Get a text summary of the last analysis for chat context
    func lastAnalysisContext() -> String? {
        lastAnalysisResult?.generateAIContext()
    }

    /// Get tags from the last analysis
    func lastAnalysisTags() -> [String] {
        lastAnalysisResult?.tags ?? []
    }
}
