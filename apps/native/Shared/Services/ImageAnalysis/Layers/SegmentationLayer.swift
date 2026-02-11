import Foundation
#if canImport(UIKit)
import UIKit
#elseif canImport(AppKit)
import AppKit
#endif
import CoreML
import Vision
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "Segmentation")

/// MobileSAM/SAM2 segmentation layer
/// Segments objects in images with precise masks
actor SegmentationLayer {

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

    /// Load the MobileSAM model (on-demand download)
    func loadModel() async throws {
        // CoreML crashes on Simulator with espresso context error
        if Self.isSimulator {
            throw ImageAnalysisError.modelNotAvailable("CoreML not available on Simulator")
        }

        guard !isLoaded else { return }

        // Check for bundled model first
        if let modelURL = Bundle.main.url(forResource: "MobileSAM", withExtension: "mlmodelc") {
            try await loadFromURL(modelURL)
            return
        }

        // Check for downloaded model
        let documentsPath = (FileManager.default.urls(for: .documentDirectory, in: .userDomainMask).first ?? FileManager.default.temporaryDirectory)
        let downloadedURL = documentsPath.appendingPathComponent(".medstation_ai/models/MobileSAM.mlmodelc")

        if FileManager.default.fileExists(atPath: downloadedURL.path) {
            try await loadFromURL(downloadedURL)
            return
        }

        // Model not available
        logger.warning("[Segmentation] MobileSAM not available")
        throw ImageAnalysisError.modelNotAvailable("MobileSAM")
    }

    private func loadFromURL(_ url: URL) async throws {
        let config = MLModelConfiguration()
        config.computeUnits = .all

        let mlModel = try await MLModel.load(contentsOf: url, configuration: config)
        self.model = try VNCoreMLModel(for: mlModel)
        self.isLoaded = true
        logger.info("[Segmentation] MobileSAM loaded")
    }

    func isModelReady() -> Bool {
        return isLoaded && model != nil
    }

    // MARK: - Segmentation

    /// Segment objects in an image
    /// - Parameters:
    ///   - image: The image to segment
    ///   - hints: Optional detected objects to guide segmentation
    func segment(_ image: PlatformImage, hints: [DetectedObject] = []) async throws -> [SegmentationMask] {
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

        // If we have object detection hints, segment those specific regions
        var masks: [SegmentationMask] = []

        if !hints.isEmpty {
            // Segment each detected object
            for object in hints.prefix(10) {  // Limit to 10 objects
                if let mask = try await segmentRegion(
                    model: model,
                    cgImage: cgImage,
                    region: object.boundingBox,
                    objectId: object.id
                ) {
                    masks.append(mask)
                }
            }
        } else {
            // Automatic segmentation without hints
            masks = try await autoSegment(model: model, cgImage: cgImage)
        }

        let processingTime = Date().timeIntervalSince(startTime)
        logger.info("[Segmentation] Created \(masks.count) masks in \(String(format: "%.2f", processingTime * 1000))ms")

        return masks
    }

    private func segmentRegion(
        model: VNCoreMLModel,
        cgImage: CGImage,
        region: CGRect,
        objectId: UUID
    ) async throws -> SegmentationMask? {
        try await withCheckedThrowingContinuation { continuation in
            let request = VNCoreMLRequest(model: model) { request, error in
                if let error = error {
                    continuation.resume(throwing: ImageAnalysisError.coreMLError(error))
                    return
                }

                // Parse segmentation output
                guard let observation = request.results?.first as? VNPixelBufferObservation else {
                    continuation.resume(returning: nil)
                    return
                }

                let mask = self.createMask(
                    from: observation.pixelBuffer,
                    boundingBox: region,
                    objectId: objectId
                )
                continuation.resume(returning: mask)
            }

            // Set region of interest
            request.regionOfInterest = region
            request.imageCropAndScaleOption = .scaleFill

            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])

            do {
                try handler.perform([request])
            } catch {
                continuation.resume(throwing: ImageAnalysisError.coreMLError(error))
            }
        }
    }

    private func autoSegment(model: VNCoreMLModel, cgImage: CGImage) async throws -> [SegmentationMask] {
        try await withCheckedThrowingContinuation { continuation in
            let request = VNCoreMLRequest(model: model) { request, error in
                if let error = error {
                    continuation.resume(throwing: ImageAnalysisError.coreMLError(error))
                    return
                }

                // Parse all segmentation outputs
                var masks: [SegmentationMask] = []

                for result in request.results ?? [] {
                    if let observation = result as? VNPixelBufferObservation {
                        if let mask = self.createMask(from: observation.pixelBuffer, boundingBox: .init(x: 0, y: 0, width: 1, height: 1), objectId: nil) {
                            masks.append(mask)
                        }
                    }
                }

                continuation.resume(returning: masks)
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

    private func createMask(
        from pixelBuffer: CVPixelBuffer,
        boundingBox: CGRect,
        objectId: UUID?
    ) -> SegmentationMask? {
        let width = CVPixelBufferGetWidth(pixelBuffer)
        let height = CVPixelBufferGetHeight(pixelBuffer)

        CVPixelBufferLockBaseAddress(pixelBuffer, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(pixelBuffer, .readOnly) }

        guard let baseAddress = CVPixelBufferGetBaseAddress(pixelBuffer) else {
            return nil
        }

        // Convert pixel buffer to Data
        let bytesPerRow = CVPixelBufferGetBytesPerRow(pixelBuffer)
        let dataSize = bytesPerRow * height
        let maskData = Data(bytes: baseAddress, count: dataSize)

        // Calculate mask properties
        let ptr = baseAddress.assumingMemoryBound(to: UInt8.self)
        var pixelCount = 0
        var sumX: Float = 0
        var sumY: Float = 0

        for y in 0..<height {
            for x in 0..<width {
                let pixel = ptr[y * bytesPerRow + x]
                if pixel > 127 {  // Threshold for mask
                    pixelCount += 1
                    sumX += Float(x)
                    sumY += Float(y)
                }
            }
        }

        let totalPixels = width * height
        let area = Float(pixelCount) / Float(totalPixels)

        let centroid = pixelCount > 0
            ? CGPoint(x: CGFloat(sumX / Float(pixelCount)) / CGFloat(width),
                      y: CGFloat(sumY / Float(pixelCount)) / CGFloat(height))
            : CGPoint(x: 0.5, y: 0.5)

        return SegmentationMask(
            maskData: maskData,
            boundingBox: boundingBox,
            area: area,
            centroid: centroid,
            associatedObjectId: objectId,
            confidence: 1.0
        )
    }
}
