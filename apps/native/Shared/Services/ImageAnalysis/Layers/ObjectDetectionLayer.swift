import Foundation
#if canImport(UIKit)
import UIKit
#elseif canImport(AppKit)
import AppKit
#endif
import CoreML
import Vision
import os

private let logger = Logger(subsystem: "com.magnetarai", category: "ObjectDetection")

/// YOLO11-nano object detection layer
/// Detects 80 COCO object classes with bounding boxes
actor ObjectDetectionLayer {

    // MARK: - Properties

    private var model: VNCoreMLModel?
    private var isLoaded: Bool = false

    // Static thresholds allow nonisolated parsing methods
    private static let confidenceThreshold: Float = 0.3
    private static let iouThreshold: Float = 0.45

    // MARK: - Model Loading

    /// Check if running on Simulator (CoreML crashes there)
    private static var isSimulator: Bool {
        #if targetEnvironment(simulator)
        return true
        #else
        return false
        #endif
    }

    /// Load the YOLO11-nano model
    func loadModel() async throws {
        // CoreML crashes on Simulator with espresso context error
        if Self.isSimulator {
            throw ImageAnalysisError.modelNotAvailable("CoreML not available on Simulator")
        }

        guard !isLoaded else { return }

        do {
            // Try to load bundled model first
            if let modelURL = Bundle.main.url(forResource: "YOLO11Nano", withExtension: "mlmodelc") {
                let config = MLModelConfiguration()
                config.computeUnits = .all  // Use ANE when available

                let mlModel = try await MLModel.load(contentsOf: modelURL, configuration: config)
                self.model = try VNCoreMLModel(for: mlModel)
                self.isLoaded = true
                logger.info("[ObjectDetection] YOLO11-nano loaded from bundle")
            } else {
                // Model not bundled - would need to download
                logger.warning("[ObjectDetection] YOLO11-nano not found in bundle")
                throw ImageAnalysisError.modelNotAvailable("YOLO11Nano")
            }
        } catch {
            logger.error("[ObjectDetection] Failed to load model: \(error.localizedDescription)")
            throw ImageAnalysisError.coreMLError(error)
        }
    }

    /// Check if model is ready
    func isModelReady() -> Bool {
        return isLoaded && model != nil
    }

    // MARK: - Object Detection

    /// Detect objects in an image
    func detect(in image: PlatformImage) async throws -> [DetectedObject] {
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

        let detections = try await performDetection(model: model, cgImage: cgImage)

        let processingTime = Date().timeIntervalSince(startTime)
        logger.info("[ObjectDetection] Detected \(detections.count) objects in \(String(format: "%.2f", processingTime * 1000))ms")

        return detections
    }

    private func performDetection(model: VNCoreMLModel, cgImage: CGImage) async throws -> [DetectedObject] {
        try await withCheckedThrowingContinuation { continuation in
            let request = VNCoreMLRequest(model: model) { [weak self] request, error in
                guard let self = self else {
                    continuation.resume(returning: [])
                    return
                }

                if let error = error {
                    continuation.resume(throwing: ImageAnalysisError.coreMLError(error))
                    return
                }

                let detections = self.parseDetections(from: request.results)
                continuation.resume(returning: detections)
            }

            // Configure request
            request.imageCropAndScaleOption = .scaleFill

            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])

            do {
                try handler.perform([request])
            } catch {
                continuation.resume(throwing: ImageAnalysisError.coreMLError(error))
            }
        }
    }

    // MARK: - Parsing (nonisolated for callback safety)

    /// Parse detections from Vision request results
    /// Marked nonisolated to allow calling from VNCoreMLRequest callback
    nonisolated private func parseDetections(from results: [Any]?) -> [DetectedObject] {
        // Handle VNRecognizedObjectObservation (standard Vision output)
        if let observations = results as? [VNRecognizedObjectObservation] {
            return parseRecognizedObjects(observations)
        }

        // Handle VNCoreMLFeatureValueObservation (raw YOLO output)
        if let observations = results as? [VNCoreMLFeatureValueObservation] {
            return parseYOLOOutput(observations)
        }

        return []
    }

    nonisolated private func parseRecognizedObjects(_ observations: [VNRecognizedObjectObservation]) -> [DetectedObject] {
        observations
            .filter { $0.confidence >= Self.confidenceThreshold }
            .compactMap { observation -> DetectedObject? in
                guard let topLabel = observation.labels.first else { return nil }

                let classIndex = DetectedObject.cocoClasses.firstIndex(of: topLabel.identifier) ?? -1

                return DetectedObject(
                    label: topLabel.identifier,
                    classIndex: classIndex,
                    confidence: topLabel.confidence,
                    boundingBox: observation.boundingBox
                )
            }
    }

    nonisolated private func parseYOLOOutput(_ observations: [VNCoreMLFeatureValueObservation]) -> [DetectedObject] {
        // Parse raw YOLO output format
        // This handles the case where the model outputs raw tensors instead of VNRecognizedObjectObservation

        var detections: [DetectedObject] = []

        for observation in observations {
            guard let multiArray = observation.featureValue.multiArrayValue else { continue }

            // YOLO output format: [batch, num_detections, 85] or [batch, 85, num_detections]
            // 85 = 4 (bbox) + 1 (objectness) + 80 (class probabilities)

            let shape = multiArray.shape.map { $0.intValue }
            guard shape.count >= 2 else { continue }

            let numDetections = shape.last == 85 ? shape[shape.count - 2] : shape.last!
            let channelsLast = shape.last == 85

            for i in 0..<min(numDetections, 1000) {  // Cap at 1000 detections
                let detection = extractDetection(
                    from: multiArray,
                    index: i,
                    channelsLast: channelsLast
                )

                if let detection = detection, detection.confidence >= Self.confidenceThreshold {
                    detections.append(detection)
                }
            }
        }

        // Apply Non-Maximum Suppression
        return applyNMS(detections: detections, threshold: Self.iouThreshold)
    }

    nonisolated private func extractDetection(from array: MLMultiArray, index: Int, channelsLast: Bool) -> DetectedObject? {
        // Extract bounding box and class probabilities from YOLO output

        let ptr = array.dataPointer.assumingMemoryBound(to: Float.self)
        let stride = channelsLast ? 85 : 1
        let offset = channelsLast ? index * 85 : index

        // Extract bbox: [cx, cy, w, h]
        let cx = ptr[offset + 0 * stride]
        let cy = ptr[offset + 1 * stride]
        let w = ptr[offset + 2 * stride]
        let h = ptr[offset + 3 * stride]

        // Extract objectness (for YOLOv5-style models)
        let objectness = ptr[offset + 4 * stride]

        // Find best class
        var bestClass = 0
        var bestScore: Float = 0

        for c in 0..<80 {
            let score = ptr[offset + (5 + c) * stride] * objectness
            if score > bestScore {
                bestScore = score
                bestClass = c
            }
        }

        guard bestScore >= Self.confidenceThreshold else { return nil }

        // Convert to normalized bounding box
        let boundingBox = CGRect(
            x: CGFloat(cx - w / 2),
            y: CGFloat(cy - h / 2),
            width: CGFloat(w),
            height: CGFloat(h)
        )

        return DetectedObject(
            label: DetectedObject.label(for: bestClass),
            classIndex: bestClass,
            confidence: bestScore,
            boundingBox: boundingBox
        )
    }

    // MARK: - Non-Maximum Suppression

    nonisolated private func applyNMS(detections: [DetectedObject], threshold: Float) -> [DetectedObject] {
        guard !detections.isEmpty else { return [] }

        // Sort by confidence (highest first)
        var sorted = detections.sorted { $0.confidence > $1.confidence }
        var kept: [DetectedObject] = []

        while !sorted.isEmpty {
            let best = sorted.removeFirst()
            kept.append(best)

            // Remove overlapping detections of the same class
            sorted = sorted.filter { detection in
                guard detection.classIndex == best.classIndex else { return true }
                return iou(best.boundingBox, detection.boundingBox) < threshold
            }
        }

        return kept
    }

    nonisolated private func iou(_ a: CGRect, _ b: CGRect) -> Float {
        let intersection = a.intersection(b)
        guard !intersection.isNull else { return 0 }

        let intersectionArea = intersection.width * intersection.height
        let unionArea = (a.width * a.height) + (b.width * b.height) - intersectionArea

        return Float(intersectionArea / unionArea)
    }
}
