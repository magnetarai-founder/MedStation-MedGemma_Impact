import Foundation
#if canImport(UIKit)
import UIKit
#elseif canImport(AppKit)
import AppKit
#endif
import Vision
import os

private let logger = Logger(subsystem: "com.magnetarai", category: "VisionAnalysis")

/// Vision Framework analysis layer
/// Handles OCR, barcode detection, and document boundary detection
actor VisionAnalysisLayer {

    /// Combined result from Vision framework analysis
    struct VisionResult: Sendable {
        let documentContent: DocumentAnalysisResult?
        let textBlocks: [RecognizedTextBlock]
        let barcodes: [BarcodeResult]
        let processingTime: TimeInterval
    }

    // MARK: - Analysis

    /// Analyze an image using Vision framework
    func analyze(_ image: PlatformImage) async throws -> VisionResult {
        let startTime = Date()

        guard let cgImage = image.cgImageCrossPlatform else {
            throw ImageAnalysisError.invalidImage
        }

        // Run text and barcode detection in parallel
        async let textResult = recognizeText(cgImage: cgImage)
        async let barcodeResult = detectBarcodes(cgImage: cgImage)

        let (textBlocks, barcodes) = try await (textResult, barcodeResult)

        // Try to infer document structure from text
        let documentContent = inferDocumentStructure(from: textBlocks)

        let processingTime = Date().timeIntervalSince(startTime)
        logger.info("[VisionAnalysis] Completed in \(String(format: "%.2f", processingTime * 1000))ms")

        return VisionResult(
            documentContent: documentContent,
            textBlocks: textBlocks,
            barcodes: barcodes,
            processingTime: processingTime
        )
    }

    // MARK: - Text Recognition (OCR)

    private func recognizeText(cgImage: CGImage) async throws -> [RecognizedTextBlock] {
        try await withCheckedThrowingContinuation { continuation in
            let request = VNRecognizeTextRequest { request, error in
                if let error = error {
                    continuation.resume(throwing: ImageAnalysisError.visionFrameworkError(error))
                    return
                }

                let observations = request.results as? [VNRecognizedTextObservation] ?? []
                let textBlocks = observations.compactMap { observation -> RecognizedTextBlock? in
                    guard let topCandidate = observation.topCandidates(1).first else { return nil }

                    return RecognizedTextBlock(
                        text: topCandidate.string,
                        boundingBox: observation.boundingBox,
                        confidence: topCandidate.confidence,
                        language: nil
                    )
                }

                continuation.resume(returning: textBlocks)
            }

            // Configure for accurate recognition
            request.recognitionLevel = .accurate
            request.usesLanguageCorrection = true
            request.recognitionLanguages = ["en-US", "es-ES", "fr-FR", "de-DE", "it-IT", "pt-BR", "zh-Hans", "ja-JP", "ko-KR"]

            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])

            do {
                try handler.perform([request])
            } catch {
                continuation.resume(throwing: ImageAnalysisError.visionFrameworkError(error))
            }
        }
    }

    // MARK: - Barcode Detection

    private func detectBarcodes(cgImage: CGImage) async throws -> [BarcodeResult] {
        try await withCheckedThrowingContinuation { continuation in
            let request = VNDetectBarcodesRequest { request, error in
                if let error = error {
                    continuation.resume(throwing: ImageAnalysisError.visionFrameworkError(error))
                    return
                }

                let observations = request.results as? [VNBarcodeObservation] ?? []
                let barcodes = observations.compactMap { observation -> BarcodeResult? in
                    guard let payload = observation.payloadStringValue else { return nil }

                    return BarcodeResult(
                        payload: payload,
                        symbology: observation.symbology.rawValue,
                        boundingBox: observation.boundingBox
                    )
                }

                continuation.resume(returning: barcodes)
            }

            let handler = VNImageRequestHandler(cgImage: cgImage, options: [:])

            do {
                try handler.perform([request])
            } catch {
                continuation.resume(throwing: ImageAnalysisError.visionFrameworkError(error))
            }
        }
    }

    // MARK: - Document Structure Inference

    /// Infer document structure from recognized text blocks
    private func inferDocumentStructure(from textBlocks: [RecognizedTextBlock]) -> DocumentAnalysisResult? {
        guard !textBlocks.isEmpty else { return nil }

        let allText = textBlocks.map { $0.text }.joined(separator: " ")
        let paragraphs = groupIntoParagraphs(textBlocks)

        // Detect QR codes in text (URLs, etc.)
        let qrCodes: [QRCodeResult] = []  // Already captured in barcode detection

        // Infer document type
        let documentType = inferDocumentType(from: allText)

        // Calculate overall bounding box
        var minX: CGFloat = 1
        var minY: CGFloat = 1
        var maxX: CGFloat = 0
        var maxY: CGFloat = 0

        for block in textBlocks {
            minX = min(minX, block.boundingBox.minX)
            minY = min(minY, block.boundingBox.minY)
            maxX = max(maxX, block.boundingBox.maxX)
            maxY = max(maxY, block.boundingBox.maxY)
        }

        let boundingBox = CGRect(
            x: minX,
            y: minY,
            width: maxX - minX,
            height: maxY - minY
        )

        // Calculate average confidence
        let avgConfidence = textBlocks.reduce(0) { $0 + $1.confidence } / Float(textBlocks.count)

        return DocumentAnalysisResult(
            documentType: documentType,
            boundingBox: boundingBox,
            paragraphs: paragraphs,
            lists: detectLists(from: paragraphs),
            tables: [],  // Table detection would require more sophisticated analysis
            qrCodes: qrCodes,
            confidence: avgConfidence
        )
    }

    private func groupIntoParagraphs(_ textBlocks: [RecognizedTextBlock]) -> [String] {
        // Sort by Y position (top to bottom)
        let sorted = textBlocks.sorted { $0.boundingBox.minY > $1.boundingBox.minY }

        var paragraphs: [String] = []
        var currentParagraph: [String] = []
        var lastY: CGFloat = -1

        for block in sorted {
            let y = block.boundingBox.minY

            // If there's a significant vertical gap, start new paragraph
            if lastY >= 0 && abs(y - lastY) > 0.03 {
                if !currentParagraph.isEmpty {
                    paragraphs.append(currentParagraph.joined(separator: " "))
                    currentParagraph = []
                }
            }

            currentParagraph.append(block.text)
            lastY = y
        }

        if !currentParagraph.isEmpty {
            paragraphs.append(currentParagraph.joined(separator: " "))
        }

        return paragraphs
    }

    private func detectLists(from paragraphs: [String]) -> [[String]] {
        var lists: [[String]] = []
        var currentList: [String] = []

        let bulletPatterns = ["• ", "- ", "* ", "◦ "]
        let numberRegex = try? NSRegularExpression(pattern: "^\\d+[.)]\\s")

        for paragraph in paragraphs {
            let isBullet = bulletPatterns.contains { paragraph.hasPrefix($0) }
            let isNumbered = numberRegex?.firstMatch(in: paragraph, range: NSRange(paragraph.startIndex..., in: paragraph)) != nil

            if isBullet || isNumbered {
                // Remove bullet/number prefix and add to list
                var item = paragraph
                if isBullet {
                    for prefix in bulletPatterns {
                        if item.hasPrefix(prefix) {
                            item = String(item.dropFirst(prefix.count))
                            break
                        }
                    }
                } else if let regex = numberRegex,
                          let match = regex.firstMatch(in: paragraph, range: NSRange(paragraph.startIndex..., in: paragraph)),
                          let range = Range(match.range, in: paragraph) {
                    item = String(paragraph[range.upperBound...])
                }
                currentList.append(item.trimmingCharacters(in: .whitespaces))
            } else if !currentList.isEmpty {
                // End of list
                lists.append(currentList)
                currentList = []
            }
        }

        if !currentList.isEmpty {
            lists.append(currentList)
        }

        return lists
    }

    private func inferDocumentType(from text: String) -> DocumentType {
        let lowercased = text.lowercased()

        // Receipt indicators
        if (lowercased.contains("total") && (lowercased.contains("$") || lowercased.contains("€"))) ||
           lowercased.contains("receipt") || lowercased.contains("invoice") ||
           lowercased.contains("subtotal") || lowercased.contains("tax") {
            return .receipt
        }

        // Business card indicators
        if text.count < 500 &&
           (lowercased.contains("@") || lowercased.contains("tel") ||
            lowercased.contains("phone") || lowercased.contains("email")) {
            return .businessCard
        }

        // Form indicators
        if lowercased.contains("form") || lowercased.contains("please fill") ||
           lowercased.contains("signature") || lowercased.contains("date:") {
            return .form
        }

        // Letter indicators
        if lowercased.contains("dear") || lowercased.contains("sincerely") ||
           lowercased.contains("regards") || lowercased.contains("to whom it may concern") {
            return .letter
        }

        // Article indicators (longer text with paragraphs)
        if text.count > 500 {
            return .article
        }

        return .unknown
    }
}
