import Foundation
#if canImport(AppKit)
import AppKit
#endif
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "StructuredOutput")

/// Context from previous layers to guide structured output generation
struct StructuredOutputContext: Sendable {
    let detectedObjects: [DetectedObject]
    let recognizedText: [RecognizedTextBlock]
    let documentContent: DocumentAnalysisResult?

    init(
        detectedObjects: [DetectedObject] = [],
        recognizedText: [RecognizedTextBlock] = [],
        documentContent: DocumentAnalysisResult? = nil
    ) {
        self.detectedObjects = detectedObjects
        self.recognizedText = recognizedText
        self.documentContent = documentContent
    }

    /// Generate a context string for the AI prompt
    var contextString: String {
        var parts: [String] = []

        if !detectedObjects.isEmpty {
            let objects = detectedObjects.prefix(10).map {
                "\($0.label) (\(Int($0.confidence * 100))% confidence)"
            }.joined(separator: ", ")
            parts.append("Detected objects: \(objects)")
        }

        if !recognizedText.isEmpty {
            let text = recognizedText.map { $0.text }.joined(separator: " ").prefix(500)
            parts.append("Visible text: \(text)")
        }

        if let doc = documentContent {
            parts.append("Document type: \(doc.documentType.rawValue)")
            if !doc.paragraphs.isEmpty {
                parts.append("Document content preview: \(doc.paragraphs.prefix(3).joined(separator: " ").prefix(300))")
            }
        }

        return parts.isEmpty ? "" : parts.joined(separator: "\n")
    }
}

/// Structured output layer for generating rich image descriptions
/// Uses rule-based generation (Foundation Models available on macOS 26+ only)
actor StructuredOutputLayer {

    // MARK: - Generation

    /// Generate a structured description of an image
    func generate(for image: PlatformImage, context: StructuredOutputContext) async throws -> StructuredImageDescription {
        let startTime = Date()

        // Use rule-based generation (Foundation Models require macOS 26+)
        let result = createFallbackDescription(context: context)
        let processingTime = Date().timeIntervalSince(startTime)
        logger.info("[StructuredOutput] Generated description in \(String(format: "%.2f", processingTime * 1000))ms")
        return result
    }

    // MARK: - Rule-Based Generation

    private func createFallbackDescription(context: StructuredOutputContext) -> StructuredImageDescription {
        var caption = "An image"
        var detailedDescription = ""
        var objects: [DescribedObject] = []
        var scenes: [String] = []
        var activities: [String] = []
        var tags: [String] = []

        // Build description from detected objects
        if !context.detectedObjects.isEmpty {
            let mainObjects = context.detectedObjects
                .filter { $0.confidence > 0.5 }
                .prefix(5)
                .map { $0.label }

            if !mainObjects.isEmpty {
                caption = "An image containing \(mainObjects.joined(separator: ", "))"

                // Infer scene from objects
                scenes = inferScenes(from: Array(mainObjects))

                // Infer activities from objects
                activities = inferActivities(from: Array(mainObjects))
            }

            objects = context.detectedObjects.prefix(10).map { obj in
                DescribedObject(
                    name: obj.label,
                    objectDescription: "",
                    position: positionFromBoundingBox(obj.boundingBox),
                    prominence: obj.confidence > 0.7 ? "main subject" : "background"
                )
            }

            tags.append(contentsOf: mainObjects)
        }

        // Enhance with document content
        if let doc = context.documentContent {
            switch doc.documentType {
            case .receipt:
                caption = "A receipt document"
                scenes = ["indoor", "commercial"]
                activities = ["transaction", "shopping"]
            case .businessCard:
                caption = "A business card"
                scenes = ["professional"]
            case .letter:
                caption = "A letter or correspondence"
                scenes = ["document"]
            case .form:
                caption = "A form document"
                scenes = ["document", "official"]
            case .article:
                caption = "An article or printed text"
                scenes = ["document", "reading material"]
            case .unknown:
                if !doc.paragraphs.isEmpty {
                    caption = "A document with text"
                }
            }
            tags.append(doc.documentType.rawValue)
        }

        // Add recognized text
        var textContent: String?
        if !context.recognizedText.isEmpty {
            let allText = context.recognizedText.map { $0.text }.joined(separator: " ")
            textContent = String(allText.prefix(500))

            // Extract potential tags from text
            let extractedTags = extractTagsFromText(allText)
            tags.append(contentsOf: extractedTags)
        }

        // Build detailed description
        var descParts: [String] = [caption]
        if !objects.isEmpty {
            descParts.append("Contains \(objects.count) detected objects.")
        }
        if let text = textContent, !text.isEmpty {
            descParts.append("Visible text includes: \"\(text.prefix(100))...\"")
        }
        detailedDescription = descParts.joined(separator: " ")

        return StructuredImageDescription(
            caption: caption,
            detailedDescription: detailedDescription,
            scenes: scenes,
            activities: activities,
            objects: objects,
            colors: [],  // Would need actual image analysis
            mood: "neutral",
            timeOfDay: nil,
            textContent: textContent,
            suggestedTags: Array(Set(tags)).sorted(),
            safetyFlags: []
        )
    }

    // MARK: - Inference Helpers

    private func inferScenes(from objects: [String]) -> [String] {
        var scenes: [String] = []

        let indoorObjects = ["couch", "chair", "bed", "tv", "refrigerator", "oven", "sink", "toilet", "dining table"]
        let outdoorObjects = ["car", "truck", "bus", "airplane", "boat", "bicycle", "motorcycle", "traffic light", "fire hydrant", "stop sign"]
        let natureObjects = ["bird", "cat", "dog", "horse", "sheep", "cow", "elephant", "bear", "zebra", "giraffe"]
        let officeObjects = ["laptop", "keyboard", "mouse", "cell phone", "book"]
        let foodObjects = ["banana", "apple", "sandwich", "orange", "broccoli", "carrot", "pizza", "donut", "cake"]

        if objects.contains(where: { indoorObjects.contains($0) }) {
            scenes.append("indoor")
        }
        if objects.contains(where: { outdoorObjects.contains($0) }) {
            scenes.append("outdoor")
        }
        if objects.contains(where: { natureObjects.contains($0) }) {
            scenes.append("nature")
        }
        if objects.contains(where: { officeObjects.contains($0) }) {
            scenes.append("office")
        }
        if objects.contains(where: { foodObjects.contains($0) }) {
            scenes.append("food")
        }
        if objects.contains("person") {
            scenes.append("people")
        }

        return scenes
    }

    private func inferActivities(from objects: [String]) -> [String] {
        var activities: [String] = []

        if objects.contains("laptop") || objects.contains("keyboard") {
            activities.append("working")
        }
        if objects.contains("sports ball") || objects.contains("tennis racket") {
            activities.append("sports")
        }
        if objects.contains(where: { ["banana", "apple", "pizza", "sandwich"].contains($0) }) {
            activities.append("eating")
        }
        if objects.contains("book") {
            activities.append("reading")
        }
        if objects.contains("bicycle") || objects.contains("motorcycle") {
            activities.append("transportation")
        }

        return activities
    }

    private func extractTagsFromText(_ text: String) -> [String] {
        var tags: [String] = []
        let lowercased = text.lowercased()

        // Extract common entity types
        if lowercased.contains("@") {
            tags.append("contact")
        }
        if lowercased.contains("http") || lowercased.contains("www") {
            tags.append("link")
        }
        if lowercased.contains("$") || lowercased.contains("€") || lowercased.contains("price") {
            tags.append("price")
        }
        if lowercased.contains("date") || text.contains(where: { $0.isNumber }) {
            tags.append("date")
        }

        return tags
    }

    private func positionFromBoundingBox(_ box: CGRect) -> String {
        let centerX = box.midX
        let centerY = box.midY

        let horizontal: String
        if centerX < 0.33 {
            horizontal = "left"
        } else if centerX > 0.66 {
            horizontal = "right"
        } else {
            horizontal = "center"
        }

        let vertical: String
        if centerY < 0.33 {
            vertical = "top"
        } else if centerY > 0.66 {
            vertical = "bottom"
        } else {
            vertical = "center"
        }

        if horizontal == "center" && vertical == "center" {
            return "center"
        } else if horizontal == "center" {
            return vertical
        } else if vertical == "center" {
            return horizontal
        } else {
            return "\(vertical)-\(horizontal)"
        }
    }
}
