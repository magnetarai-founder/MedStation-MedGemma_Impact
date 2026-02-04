import Foundation
import CoreGraphics

/// Result from SAM2/MobileSAM segmentation
struct SegmentationMask: Codable, Identifiable, Sendable {
    let id: UUID
    let maskData: Data
    let boundingBox: CGRect
    let area: Float
    let centroid: CGPoint
    let associatedObjectId: UUID?
    let confidence: Float

    init(
        id: UUID = UUID(),
        maskData: Data,
        boundingBox: CGRect,
        area: Float,
        centroid: CGPoint,
        associatedObjectId: UUID? = nil,
        confidence: Float = 1.0
    ) {
        self.id = id
        self.maskData = maskData
        self.boundingBox = boundingBox
        self.area = area
        self.centroid = centroid
        self.associatedObjectId = associatedObjectId
        self.confidence = confidence
    }

    /// Check if this mask covers a significant portion of the image
    var isSignificant: Bool {
        area > 0.01  // More than 1% of image
    }

    /// Check if this mask is likely the main subject
    var isMainSubject: Bool {
        area > 0.1 && area < 0.9  // Between 10-90% of image
    }
}

/// Collection of segmentation masks for an image
struct SegmentationResult: Codable, Sendable {
    let masks: [SegmentationMask]
    let processingTime: TimeInterval

    init(masks: [SegmentationMask] = [], processingTime: TimeInterval = 0) {
        self.masks = masks
        self.processingTime = processingTime
    }

    /// Get the largest mask (likely main subject)
    var largestMask: SegmentationMask? {
        masks.max(by: { $0.area < $1.area })
    }

    /// Get masks sorted by area (largest first)
    var sortedByArea: [SegmentationMask] {
        masks.sorted(by: { $0.area > $1.area })
    }
}
