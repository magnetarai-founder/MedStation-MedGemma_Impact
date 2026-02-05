//
//  CoreMLModelManager.swift
//  MagnetarAI
//
//  STUB: Not currently wired — future CoreML model management infrastructure.
//  Manages on-demand downloading and caching of CoreML models (YOLO11, MobileSAM, DepthAnything).
//  Will be integrated when ImageAnalysisService is activated.
//

import Foundation
import CoreML
import os

private let logger = Logger(subsystem: "com.magnetarai", category: "CoreMLModelManager")

// MARK: - Model Definition

/// Available CoreML models for image analysis
enum CoreMLModelType: String, CaseIterable {
    case yolo11Nano = "YOLO11Nano"
    case mobileSAM = "MobileSAM"
    case depthAnythingV2 = "DepthAnythingV2Small"

    /// File size in bytes for progress estimation
    var estimatedSize: Int64 {
        switch self {
        case .yolo11Nano: return 6_000_000       // ~6MB
        case .mobileSAM: return 40_000_000       // ~40MB
        case .depthAnythingV2: return 50_000_000 // ~50MB
        }
    }

    /// Model filename with extension
    var filename: String {
        "\(rawValue).mlmodelc"
    }

    /// Human-readable name
    var displayName: String {
        switch self {
        case .yolo11Nano: return "Object Detection"
        case .mobileSAM: return "Image Segmentation"
        case .depthAnythingV2: return "Depth Estimation"
        }
    }

    /// Whether this model should be bundled with the app
    var isBundled: Bool {
        switch self {
        case .yolo11Nano: return true
        case .mobileSAM, .depthAnythingV2: return false
        }
    }

    /// Download URL for on-demand models
    /// Models hosted on Hugging Face Hub (CoreML converted versions)
    var downloadURL: URL? {
        switch self {
        case .yolo11Nano:
            return nil  // Bundled with app
        case .mobileSAM:
            // MobileSAM CoreML from Hugging Face
            return URL(string: "https://huggingface.co/apple/coreml-mobile-sam/resolve/main/MobileSAM.mlpackage.zip")
        case .depthAnythingV2:
            // Depth Anything V2 Small CoreML from Hugging Face
            return URL(string: "https://huggingface.co/apple/coreml-depth-anything-v2-small/resolve/main/DepthAnythingV2Small.mlpackage.zip")
        }
    }
}

// MARK: - Download Progress

/// Progress information for model downloads
struct ModelDownloadProgress: Identifiable {
    let id: CoreMLModelType
    var bytesDownloaded: Int64
    var totalBytes: Int64
    var status: DownloadStatus

    var progress: Double {
        guard totalBytes > 0 else { return 0 }
        return Double(bytesDownloaded) / Double(totalBytes)
    }

    enum DownloadStatus {
        case pending
        case downloading
        case extracting
        case compiling
        case completed
        case failed(Error)
    }
}

// MARK: - Model Manager

/// Manages CoreML model downloading, caching, and loading
@MainActor
@Observable
final class CoreMLModelManager {

    // MARK: - Properties

    /// Download progress for each model
    private(set) var downloadProgress: [CoreMLModelType: ModelDownloadProgress] = [:]

    /// Currently downloading models
    private(set) var activeDownloads: Set<CoreMLModelType> = []

    /// Cached model availability
    private var modelAvailability: [CoreMLModelType: Bool] = [:]

    /// Base directory for downloaded models
    private let modelsDirectory: URL

    /// URL session for downloads
    private let session: URLSession

    // MARK: - Singleton

    static let shared = CoreMLModelManager()

    // MARK: - Initialization

    private init() {
        let documentsPath = (FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory)
        self.modelsDirectory = documentsPath.appendingPathComponent(".magnetar_ai/models", isDirectory: true)

        // Create models directory
        try? FileManager.default.createDirectory(at: modelsDirectory, withIntermediateDirectories: true)

        // Configure URL session for background downloads
        let config = URLSessionConfiguration.default
        config.timeoutIntervalForResource = 600  // 10 minute timeout
        config.waitsForConnectivity = true
        self.session = URLSession(configuration: config)

        // Check initial model availability
        Task {
            await refreshModelAvailability()
        }

        logger.info("[CoreMLModelManager] Initialized at \(self.modelsDirectory.path)")
    }

    // MARK: - Model Availability

    /// Check if a model is available (bundled or downloaded)
    func isModelAvailable(_ model: CoreMLModelType) -> Bool {
        // Check cached value first
        if let cached = modelAvailability[model] {
            return cached
        }

        let available = checkModelAvailability(model)
        modelAvailability[model] = available
        return available
    }

    /// Get the URL for a model if available
    func modelURL(_ model: CoreMLModelType) -> URL? {
        // Check bundled first
        if let bundledURL = Bundle.main.url(forResource: model.rawValue, withExtension: "mlmodelc") {
            return bundledURL
        }

        // Check downloaded
        let downloadedURL = modelsDirectory.appendingPathComponent(model.filename)
        if FileManager.default.fileExists(atPath: downloadedURL.path) {
            return downloadedURL
        }

        return nil
    }

    /// Refresh model availability cache
    func refreshModelAvailability() async {
        for model in CoreMLModelType.allCases {
            modelAvailability[model] = checkModelAvailability(model)
        }
    }

    private func checkModelAvailability(_ model: CoreMLModelType) -> Bool {
        // Check bundled
        if Bundle.main.url(forResource: model.rawValue, withExtension: "mlmodelc") != nil {
            return true
        }

        // Check downloaded
        let downloadedURL = modelsDirectory.appendingPathComponent(model.filename)
        return FileManager.default.fileExists(atPath: downloadedURL.path)
    }

    // MARK: - Model Download

    /// Download a model if not already available
    func downloadModel(_ model: CoreMLModelType) async throws {
        // Already available
        if isModelAvailable(model) {
            logger.info("[CoreMLModelManager] Model \(model.rawValue) already available")
            return
        }

        // Already downloading
        if activeDownloads.contains(model) {
            logger.info("[CoreMLModelManager] Model \(model.rawValue) already downloading")
            return
        }

        guard let downloadURL = model.downloadURL else {
            throw CoreMLModelError.downloadURLNotConfigured(model)
        }

        activeDownloads.insert(model)
        downloadProgress[model] = ModelDownloadProgress(
            id: model,
            bytesDownloaded: 0,
            totalBytes: model.estimatedSize,
            status: .pending
        )

        defer {
            activeDownloads.remove(model)
        }

        do {
            // Download
            downloadProgress[model]?.status = .downloading
            logger.info("[CoreMLModelManager] Downloading \(model.rawValue)...")

            let (localURL, response) = try await session.download(from: downloadURL)

            if let httpResponse = response as? HTTPURLResponse {
                downloadProgress[model]?.totalBytes = httpResponse.expectedContentLength
            }

            // Extract if zip
            downloadProgress[model]?.status = .extracting
            let extractedURL = try await extractModel(from: localURL, model: model)

            // Move to models directory
            let destinationURL = modelsDirectory.appendingPathComponent(model.filename)
            try? FileManager.default.removeItem(at: destinationURL)
            try FileManager.default.moveItem(at: extractedURL, to: destinationURL)

            // Update availability
            modelAvailability[model] = true
            downloadProgress[model]?.status = .completed

            logger.info("[CoreMLModelManager] Model \(model.rawValue) downloaded and installed")

        } catch {
            downloadProgress[model]?.status = .failed(error)
            logger.error("[CoreMLModelManager] Failed to download \(model.rawValue): \(error.localizedDescription)")
            throw error
        }
    }

    /// Download all on-demand models
    func downloadAllModels() async {
        let onDemandModels = CoreMLModelType.allCases.filter { !$0.isBundled }

        await withTaskGroup(of: Void.self) { group in
            for model in onDemandModels {
                group.addTask {
                    try? await self.downloadModel(model)
                }
            }
        }
    }

    // MARK: - Model Loading

    /// Load a CoreML model
    func loadModel(_ model: CoreMLModelType, computeUnits: MLComputeUnits = .all) async throws -> MLModel {
        guard let modelURL = modelURL(model) else {
            throw CoreMLModelError.modelNotAvailable(model)
        }

        let config = MLModelConfiguration()
        config.computeUnits = computeUnits

        let mlModel = try await MLModel.load(contentsOf: modelURL, configuration: config)
        logger.info("[CoreMLModelManager] Loaded model \(model.rawValue)")

        return mlModel
    }

    // MARK: - Storage Management

    /// Get total size of downloaded models
    func downloadedModelsSize() -> Int64 {
        var totalSize: Int64 = 0

        let fm = FileManager.default
        guard let enumerator = fm.enumerator(at: modelsDirectory, includingPropertiesForKeys: [.fileSizeKey]) else {
            return 0
        }

        for case let fileURL as URL in enumerator {
            if let size = try? fileURL.resourceValues(forKeys: [.fileSizeKey]).fileSize {
                totalSize += Int64(size)
            }
        }

        return totalSize
    }

    /// Delete a downloaded model
    func deleteModel(_ model: CoreMLModelType) throws {
        // Don't delete bundled models
        guard !model.isBundled else { return }

        let modelPath = modelsDirectory.appendingPathComponent(model.filename)
        try FileManager.default.removeItem(at: modelPath)
        modelAvailability[model] = false

        logger.info("[CoreMLModelManager] Deleted model \(model.rawValue)")
    }

    /// Delete all downloaded models
    func deleteAllDownloadedModels() throws {
        for model in CoreMLModelType.allCases where !model.isBundled {
            do {
                try deleteModel(model)
            } catch {
                logger.warning("[CoreMLModelManager] Failed to delete model \(model.rawValue): \(error)")
            }
        }
    }

    // MARK: - Helpers

    private func extractModel(from downloadedURL: URL, model: CoreMLModelType) async throws -> URL {
        let fm = FileManager.default

        // If it's already a .mlmodelc directory or package, just return it
        if downloadedURL.pathExtension == "mlmodelc" {
            return downloadedURL
        }

        // Check if it's a directory (compiled model package)
        var isDir: ObjCBool = false
        if fm.fileExists(atPath: downloadedURL.path, isDirectory: &isDir), isDir.boolValue {
            // It's already a directory, check for mlmodelc inside
            let contents = try fm.contentsOfDirectory(at: downloadedURL, includingPropertiesForKeys: nil)
            for item in contents {
                if item.pathExtension == "mlmodelc" {
                    return item
                }
            }
            // Might be the model directory itself
            return downloadedURL
        }

        // For ZIP files, we need to use compression framework
        // Note: iOS doesn't have a built-in unzip API, so we expect pre-compiled .mlmodelc files
        // If you need ZIP support, add a library like ZIPFoundation

        // Try treating the downloaded file as the model directly
        let extractDir = fm.temporaryDirectory.appendingPathComponent(UUID().uuidString)
        try fm.createDirectory(at: extractDir, withIntermediateDirectories: true)

        let destinationURL = extractDir.appendingPathComponent(model.filename)
        try fm.copyItem(at: downloadedURL, to: destinationURL)

        if fm.fileExists(atPath: destinationURL.path) {
            return destinationURL
        }

        throw CoreMLModelError.extractionFailed(model)
    }
}

// MARK: - Errors

enum CoreMLModelError: Error, LocalizedError {
    case modelNotAvailable(CoreMLModelType)
    case downloadURLNotConfigured(CoreMLModelType)
    case downloadFailed(CoreMLModelType, Error)
    case extractionFailed(CoreMLModelType)
    case compilationFailed(CoreMLModelType, Error)

    var errorDescription: String? {
        switch self {
        case .modelNotAvailable(let model):
            return "\(model.displayName) model is not available"
        case .downloadURLNotConfigured(let model):
            return "Download URL not configured for \(model.displayName)"
        case .downloadFailed(let model, let error):
            return "Failed to download \(model.displayName): \(error.localizedDescription)"
        case .extractionFailed(let model):
            return "Failed to extract \(model.displayName) model"
        case .compilationFailed(let model, let error):
            return "Failed to compile \(model.displayName): \(error.localizedDescription)"
        }
    }
}

// MARK: - Convenience Extensions

extension CoreMLModelManager {
    /// Check which models need to be downloaded
    var pendingDownloads: [CoreMLModelType] {
        CoreMLModelType.allCases.filter { !$0.isBundled && !isModelAvailable($0) }
    }

    /// Total size of pending downloads
    var pendingDownloadSize: Int64 {
        pendingDownloads.reduce(0) { $0 + $1.estimatedSize }
    }

    /// Formatted string for pending download size
    var pendingDownloadSizeString: String {
        ByteCountFormatter.string(fromByteCount: pendingDownloadSize, countStyle: .file)
    }
}
