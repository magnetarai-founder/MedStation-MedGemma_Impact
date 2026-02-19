import Foundation
#if canImport(UIKit)
import UIKit
#elseif canImport(AppKit)
import AppKit
#endif

/// Analysis layer types
enum AnalysisLayerType: String, Codable, CaseIterable, Sendable {
    case vision = "vision"
    case objectDetection = "object_detection"
    case segmentation = "segmentation"
    case depth = "depth"
    case structuredOutput = "structured_output"

    var displayName: String {
        switch self {
        case .vision: return "Vision Framework"
        case .objectDetection: return "Object Detection"
        case .segmentation: return "Segmentation"
        case .depth: return "Depth Estimation"
        case .structuredOutput: return "AI Description"
        }
    }

    var icon: String {
        switch self {
        case .vision: return "doc.text.viewfinder"
        case .objectDetection: return "viewfinder.rectangular"
        case .segmentation: return "square.on.square.dashed"
        case .depth: return "cube.transparent"
        case .structuredOutput: return "brain.head.profile"
        }
    }

    var estimatedDurationMs: Int {
        switch self {
        case .vision: return 50
        case .objectDetection: return 30
        case .segmentation: return 150
        case .depth: return 35
        case .structuredOutput: return 200
        }
    }
}

/// Comprehensive result from multi-layer image analysis
struct ImageAnalysisResult: Codable, Identifiable, Sendable {
    let id: UUID
    let imageHash: String
    let analyzedAt: Date
    let processingDuration: TimeInterval

    // Layer 1: Vision Framework Results
    let documentContent: DocumentAnalysisResult?
    let recognizedText: [RecognizedTextBlock]
    let detectedBarcodes: [BarcodeResult]

    // Layer 2: Object Detection Results
    let detectedObjects: [DetectedObject]

    // Layer 3: Segmentation Results
    let segmentationMasks: [SegmentationMask]?

    // Layer 4: Depth Estimation Results
    let depthMap: DepthMapResult?

    // Layer 5: Structured Output (Apple FM)
    let structuredDescription: StructuredImageDescription

    // Aggregated outputs for RAG
    let searchableText: String
    let tags: [String]
    let semanticEmbedding: [Float]?

    // Processing metadata
    let layersExecuted: [AnalysisLayerType]
    let failedLayers: [AnalysisLayerType]
    let layerTimings: [AnalysisLayerType: TimeInterval]
    let deviceThermalState: ThermalState

    /// Thermal state enum for Codable support
    enum ThermalState: String, Codable, Sendable {
        case nominal
        case fair
        case serious
        case critical

        init(from processInfo: ProcessInfo.ThermalState) {
            switch processInfo {
            case .nominal: self = .nominal
            case .fair: self = .fair
            case .serious: self = .serious
            case .critical: self = .critical
            @unknown default: self = .nominal
            }
        }
    }

    init(
        id: UUID = UUID(),
        imageHash: String,
        analyzedAt: Date = Date(),
        processingDuration: TimeInterval,
        documentContent: DocumentAnalysisResult? = nil,
        recognizedText: [RecognizedTextBlock] = [],
        detectedBarcodes: [BarcodeResult] = [],
        detectedObjects: [DetectedObject] = [],
        segmentationMasks: [SegmentationMask]? = nil,
        depthMap: DepthMapResult? = nil,
        structuredDescription: StructuredImageDescription,
        searchableText: String = "",
        tags: [String] = [],
        semanticEmbedding: [Float]? = nil,
        layersExecuted: [AnalysisLayerType] = [],
        failedLayers: [AnalysisLayerType] = [],
        layerTimings: [AnalysisLayerType: TimeInterval] = [:],
        deviceThermalState: ThermalState = .nominal
    ) {
        self.id = id
        self.imageHash = imageHash
        self.analyzedAt = analyzedAt
        self.processingDuration = processingDuration
        self.documentContent = documentContent
        self.recognizedText = recognizedText
        self.detectedBarcodes = detectedBarcodes
        self.detectedObjects = detectedObjects
        self.segmentationMasks = segmentationMasks
        self.depthMap = depthMap
        self.structuredDescription = structuredDescription
        self.searchableText = searchableText
        self.tags = tags
        self.semanticEmbedding = semanticEmbedding
        self.layersExecuted = layersExecuted
        self.failedLayers = failedLayers
        self.layerTimings = layerTimings
        self.deviceThermalState = deviceThermalState
    }

    /// Generate searchable text from all layers
    func generateSearchableText() -> String {
        var parts: [String] = []

        // Add recognized text
        parts.append(contentsOf: recognizedText.map { $0.text })

        // Add detected objects
        parts.append(contentsOf: detectedObjects.filter { $0.confidence > 0.5 }.map {
            "\($0.label) (\(Int($0.confidence * 100))%)"
        })

        // Add structured description
        parts.append(structuredDescription.caption)
        parts.append(contentsOf: structuredDescription.scenes)
        parts.append(contentsOf: structuredDescription.activities)

        // Add document content
        if let doc = documentContent {
            parts.append(contentsOf: doc.paragraphs)
        }

        // Add visible text from structured description
        if let textContent = structuredDescription.textContent {
            parts.append(textContent)
        }

        return parts.joined(separator: " ")
    }

    /// Generate tags from all layers
    func generateTags() -> [String] {
        var tagSet = Set<String>()

        // Add object labels
        for obj in detectedObjects where obj.confidence > 0.5 {
            tagSet.insert(obj.label)
        }

        // Add structured description tags
        tagSet.formUnion(structuredDescription.suggestedTags)
        tagSet.formUnion(structuredDescription.scenes)

        // Add document type if present
        if let doc = documentContent {
            tagSet.insert(doc.documentType.rawValue)
        }

        // Add mood
        if !structuredDescription.mood.isEmpty {
            tagSet.insert(structuredDescription.mood)
        }

        return Array(tagSet).sorted()
    }

    /// Create a copy with updated searchable text
    func withSearchableText(_ text: String) -> ImageAnalysisResult {
        ImageAnalysisResult(
            id: id,
            imageHash: imageHash,
            analyzedAt: analyzedAt,
            processingDuration: processingDuration,
            documentContent: documentContent,
            recognizedText: recognizedText,
            detectedBarcodes: detectedBarcodes,
            detectedObjects: detectedObjects,
            segmentationMasks: segmentationMasks,
            depthMap: depthMap,
            structuredDescription: structuredDescription,
            searchableText: text,
            tags: tags,
            semanticEmbedding: semanticEmbedding,
            layersExecuted: layersExecuted,
            failedLayers: failedLayers,
            layerTimings: layerTimings,
            deviceThermalState: deviceThermalState
        )
    }

    /// Create a copy with updated tags
    func withTags(_ newTags: [String]) -> ImageAnalysisResult {
        ImageAnalysisResult(
            id: id,
            imageHash: imageHash,
            analyzedAt: analyzedAt,
            processingDuration: processingDuration,
            documentContent: documentContent,
            recognizedText: recognizedText,
            detectedBarcodes: detectedBarcodes,
            detectedObjects: detectedObjects,
            segmentationMasks: segmentationMasks,
            depthMap: depthMap,
            structuredDescription: structuredDescription,
            searchableText: searchableText,
            tags: newTags,
            semanticEmbedding: semanticEmbedding,
            layersExecuted: layersExecuted,
            failedLayers: failedLayers,
            layerTimings: layerTimings,
            deviceThermalState: deviceThermalState
        )
    }

    /// Create a copy with updated embedding
    func withEmbedding(_ embedding: [Float]) -> ImageAnalysisResult {
        ImageAnalysisResult(
            id: id,
            imageHash: imageHash,
            analyzedAt: analyzedAt,
            processingDuration: processingDuration,
            documentContent: documentContent,
            recognizedText: recognizedText,
            detectedBarcodes: detectedBarcodes,
            detectedObjects: detectedObjects,
            segmentationMasks: segmentationMasks,
            depthMap: depthMap,
            structuredDescription: structuredDescription,
            searchableText: searchableText,
            tags: tags,
            semanticEmbedding: embedding,
            layersExecuted: layersExecuted,
            failedLayers: failedLayers,
            layerTimings: layerTimings,
            deviceThermalState: deviceThermalState
        )
    }

    /// Generate context string for AI prompts
    func generateAIContext() -> String {
        var context = "Image Analysis:\n"

        context += "- Caption: \(structuredDescription.caption)\n"

        if !detectedObjects.isEmpty {
            let objects = detectedObjects.prefix(10).map { $0.label }.joined(separator: ", ")
            context += "- Objects detected: \(objects)\n"
        }

        if !recognizedText.isEmpty {
            let text = recognizedText.map { $0.text }.joined(separator: " ").prefix(500)
            context += "- Text visible: \(text)\n"
        }

        if let doc = documentContent {
            context += "- Document type: \(doc.documentType.rawValue)\n"
        }

        if let depthMap = depthMap {
            context += "- \(depthMap.depthDescription)\n"
        }

        if !structuredDescription.scenes.isEmpty {
            context += "- Scene: \(structuredDescription.scenes.joined(separator: ", "))\n"
        }

        if !failedLayers.isEmpty {
            let names = failedLayers.map(\.displayName).joined(separator: ", ")
            context += "- WARNING: Analysis incomplete — failed layers: \(names)\n"
        }

        return context
    }
}

// MARK: - Dictionary Codable Extension for layerTimings

extension ImageAnalysisResult {
    enum CodingKeys: String, CodingKey {
        case id, imageHash, analyzedAt, processingDuration
        case documentContent, recognizedText, detectedBarcodes
        case detectedObjects, segmentationMasks, depthMap
        case structuredDescription, searchableText, tags, semanticEmbedding
        case layersExecuted, failedLayers, layerTimings, deviceThermalState
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)

        id = try container.decode(UUID.self, forKey: .id)
        imageHash = try container.decode(String.self, forKey: .imageHash)
        analyzedAt = try container.decode(Date.self, forKey: .analyzedAt)
        processingDuration = try container.decode(TimeInterval.self, forKey: .processingDuration)
        documentContent = try container.decodeIfPresent(DocumentAnalysisResult.self, forKey: .documentContent)
        recognizedText = try container.decode([RecognizedTextBlock].self, forKey: .recognizedText)
        detectedBarcodes = try container.decode([BarcodeResult].self, forKey: .detectedBarcodes)
        detectedObjects = try container.decode([DetectedObject].self, forKey: .detectedObjects)
        segmentationMasks = try container.decodeIfPresent([SegmentationMask].self, forKey: .segmentationMasks)
        depthMap = try container.decodeIfPresent(DepthMapResult.self, forKey: .depthMap)
        structuredDescription = try container.decode(StructuredImageDescription.self, forKey: .structuredDescription)
        searchableText = try container.decode(String.self, forKey: .searchableText)
        tags = try container.decode([String].self, forKey: .tags)
        semanticEmbedding = try container.decodeIfPresent([Float].self, forKey: .semanticEmbedding)
        layersExecuted = try container.decode([AnalysisLayerType].self, forKey: .layersExecuted)
        failedLayers = try container.decodeIfPresent([AnalysisLayerType].self, forKey: .failedLayers) ?? []
        deviceThermalState = try container.decode(ThermalState.self, forKey: .deviceThermalState)

        // Decode layerTimings as dictionary with string keys
        let timingsDict = try container.decode([String: TimeInterval].self, forKey: .layerTimings)
        var timings: [AnalysisLayerType: TimeInterval] = [:]
        for (key, value) in timingsDict {
            if let layer = AnalysisLayerType(rawValue: key) {
                timings[layer] = value
            }
        }
        layerTimings = timings
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)

        try container.encode(id, forKey: .id)
        try container.encode(imageHash, forKey: .imageHash)
        try container.encode(analyzedAt, forKey: .analyzedAt)
        try container.encode(processingDuration, forKey: .processingDuration)
        try container.encodeIfPresent(documentContent, forKey: .documentContent)
        try container.encode(recognizedText, forKey: .recognizedText)
        try container.encode(detectedBarcodes, forKey: .detectedBarcodes)
        try container.encode(detectedObjects, forKey: .detectedObjects)
        try container.encodeIfPresent(segmentationMasks, forKey: .segmentationMasks)
        try container.encodeIfPresent(depthMap, forKey: .depthMap)
        try container.encode(structuredDescription, forKey: .structuredDescription)
        try container.encode(searchableText, forKey: .searchableText)
        try container.encode(tags, forKey: .tags)
        try container.encodeIfPresent(semanticEmbedding, forKey: .semanticEmbedding)
        try container.encode(layersExecuted, forKey: .layersExecuted)
        try container.encode(failedLayers, forKey: .failedLayers)
        try container.encode(deviceThermalState, forKey: .deviceThermalState)

        // Encode layerTimings as dictionary with string keys
        var timingsDict: [String: TimeInterval] = [:]
        for (layer, time) in layerTimings {
            timingsDict[layer.rawValue] = time
        }
        try container.encode(timingsDict, forKey: .layerTimings)
    }
}
