import Foundation
#if canImport(UIKit)
import UIKit
#elseif canImport(AppKit)
import AppKit
#endif
import CoreML
import CoreVideo
import Vision
import os

private let logger = Logger(subsystem: "com.magnetarai", category: "DepthEstimation")

/// Depth Anything V2 depth estimation layer
/// Estimates depth from monocular images
actor DepthEstimationLayer {

    // MARK: - Properties

    private var model: VNCoreMLModel?
    private var isLoaded: Bool = false

    // MARK: - Model Loading

    /// Check if running on Simulator (CoreML crashes there)
    private static var isSimulator: Bool {
        #if targetEnvironment(simulator)
        return true
        #else
        return false
        #endif
    }

    /// Load the Depth Anything V2 model (on-demand download)
    func loadModel() async throws {
        // CoreML crashes on Simulator with espresso context error
        if Self.isSimulator {
            throw ImageAnalysisError.modelNotAvailable("CoreML not available on Simulator")
        }

        guard !isLoaded else { return }

        // Check for bundled model first
        if let modelURL = Bundle.main.url(forResource: "DepthAnythingV2Small", withExtension: "mlmodelc") {
            try await loadFromURL(modelURL)
            return
        }

        // Check for downloaded model
        let documentsPath = FileManager.default.urls(for: .documentDirectory, in: .userDomainMask)[0]
        let downloadedURL = documentsPath.appendingPathComponent(".magnetar_ai/models/DepthAnythingV2Small.mlmodelc")

        if FileManager.default.fileExists(atPath: downloadedURL.path) {
            try await loadFromURL(downloadedURL)
            return
        }

        // Model not available
        logger.warning("[DepthEstimation] Depth Anything V2 not available")
        throw ImageAnalysisError.modelNotAvailable("DepthAnythingV2Small")
    }

    private func loadFromURL(_ url: URL) async throws {
        let config = MLModelConfiguration()
        config.computeUnits = .all

        let mlModel = try await MLModel.load(contentsOf: url, configuration: config)
        self.model = try VNCoreMLModel(for: mlModel)
        self.isLoaded = true
        logger.info("[DepthEstimation] Depth Anything V2 loaded")
    }

    func isModelReady() -> Bool {
        return isLoaded && model != nil
    }

    // MARK: - Depth Estimation

    /// Estimate depth in an image
    func estimateDepth(in image: PlatformImage) async throws -> DepthMapResult {
        // Ensure model is loaded
        if !isLoaded {
            try await loadModel()
        }

        guard let model = model else {
            throw ImageAnalysisError.modelNotLoaded
        }

        guard let cgImage = image.cgImageCrossPlatform else {
            throw ImageAnalysisError.invalidImage
        }

        let startTime = Date()

        let result = try await performDepthEstimation(model: model, cgImage: cgImage)

        let processingTime = Date().timeIntervalSince(startTime)
        logger.info("[DepthEstimation] Completed in \(String(format: "%.2f", processingTime * 1000))ms")

        return result
    }

    private func performDepthEstimation(model: VNCoreMLModel, cgImage: CGImage) async throws -> DepthMapResult {
        try await withCheckedThrowingContinuation { continuation in
            let request = VNCoreMLRequest(model: model) { request, error in
                if let error = error {
                    continuation.resume(throwing: ImageAnalysisError.coreMLError(error))
                    return
                }

                // Parse depth output
                guard let observation = request.results?.first as? VNPixelBufferObservation else {
                    continuation.resume(throwing: ImageAnalysisError.coreMLError(
                        NSError(domain: "DepthEstimation", code: -1, userInfo: [NSLocalizedDescriptionKey: "No depth output"])
                    ))
                    return
                }

                let result = self.parseDepthBuffer(observation.pixelBuffer)
                continuation.resume(returning: result)
            }

            request.imageCropAndScaleOption = .scaleFill

            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])

            do {
                try handler.perform([request])
            } catch {
                continuation.resume(throwing: ImageAnalysisError.coreMLError(error))
            }
        }
    }

    private func parseDepthBuffer(_ pixelBuffer: CVPixelBuffer) -> DepthMapResult {
        let width = CVPixelBufferGetWidth(pixelBuffer)
        let height = CVPixelBufferGetHeight(pixelBuffer)

        CVPixelBufferLockBaseAddress(pixelBuffer, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(pixelBuffer, .readOnly) }

        guard let baseAddress = CVPixelBufferGetBaseAddress(pixelBuffer) else {
            return .empty
        }

        let bytesPerRow = CVPixelBufferGetBytesPerRow(pixelBuffer)
        let pixelFormat = CVPixelBufferGetPixelFormatType(pixelBuffer)

        // Determine data type based on pixel format
        var depthValues: [Float] = []
        var minDepth: Float = .greatestFiniteMagnitude
        var maxDepth: Float = -.greatestFiniteMagnitude
        var sumDepth: Float = 0

        if pixelFormat == kCVPixelFormatType_OneComponent32Float || pixelFormat == kCVPixelFormatType_DepthFloat32 {
            // Float32 depth values
            let ptr = baseAddress.assumingMemoryBound(to: Float.self)
            let floatsPerRow = bytesPerRow / MemoryLayout<Float>.size

            for y in 0..<height {
                for x in 0..<width {
                    let depth = ptr[y * floatsPerRow + x]
                    depthValues.append(depth)

                    if depth.isFinite {
                        minDepth = min(minDepth, depth)
                        maxDepth = max(maxDepth, depth)
                        sumDepth += depth
                    }
                }
            }
        } else {
            // Assume 8-bit grayscale, normalize to 0-1
            let ptr = baseAddress.assumingMemoryBound(to: UInt8.self)

            for y in 0..<height {
                for x in 0..<width {
                    let value = ptr[y * bytesPerRow + x]
                    let depth = Float(value) / 255.0
                    depthValues.append(depth)

                    minDepth = min(minDepth, depth)
                    maxDepth = max(maxDepth, depth)
                    sumDepth += depth
                }
            }
        }

        let totalPixels = width * height
        let averageDepth = totalPixels > 0 ? sumDepth / Float(totalPixels) : 0

        // Create histogram (10 bins)
        var histogram = [Float](repeating: 0, count: 10)
        let range = maxDepth - minDepth

        if range > 0 {
            for depth in depthValues {
                let normalizedDepth = (depth - minDepth) / range
                let bin = min(9, Int(normalizedDepth * 10))
                histogram[bin] += 1
            }
            // Normalize histogram
            let total = Float(depthValues.count)
            histogram = histogram.map { $0 / total }
        }

        // Convert to Data
        let depthData = depthValues.withUnsafeBufferPointer { buffer in
            Data(buffer: buffer)
        }

        return DepthMapResult(
            depthData: depthData,
            width: width,
            height: height,
            minDepth: minDepth == .greatestFiniteMagnitude ? 0 : minDepth,
            maxDepth: maxDepth == -.greatestFiniteMagnitude ? 1 : maxDepth,
            averageDepth: averageDepth,
            depthHistogram: histogram
        )
    }
}
