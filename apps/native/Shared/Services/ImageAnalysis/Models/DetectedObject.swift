import Foundation
import CoreGraphics

/// Result from YOLO11-nano object detection
struct DetectedObject: Codable, Identifiable, Sendable {
    let id: UUID
    let label: String
    let classIndex: Int
    let confidence: Float
    let boundingBox: CGRect
    let attributes: [String: String]

    init(
        id: UUID = UUID(),
        label: String,
        classIndex: Int,
        confidence: Float,
        boundingBox: CGRect,
        attributes: [String: String] = [:]
    ) {
        self.id = id
        self.label = label
        self.classIndex = classIndex
        self.confidence = confidence
        self.boundingBox = boundingBox
        self.attributes = attributes
    }

    /// COCO 80-class labels
    static let cocoClasses: [String] = [
        "person", "bicycle", "car", "motorcycle", "airplane", "bus", "train",
        "truck", "boat", "traffic light", "fire hydrant", "stop sign",
        "parking meter", "bench", "bird", "cat", "dog", "horse", "sheep",
        "cow", "elephant", "bear", "zebra", "giraffe", "backpack", "umbrella",
        "handbag", "tie", "suitcase", "frisbee", "skis", "snowboard",
        "sports ball", "kite", "baseball bat", "baseball glove", "skateboard",
        "surfboard", "tennis racket", "bottle", "wine glass", "cup", "fork",
        "knife", "spoon", "bowl", "banana", "apple", "sandwich", "orange",
        "broccoli", "carrot", "hot dog", "pizza", "donut", "cake", "chair",
        "couch", "potted plant", "bed", "dining table", "toilet", "tv",
        "laptop", "mouse", "remote", "keyboard", "cell phone", "microwave",
        "oven", "toaster", "sink", "refrigerator", "book", "clock", "vase",
        "scissors", "teddy bear", "hair drier", "toothbrush"
    ]

    /// Get label from class index
    static func label(for index: Int) -> String {
        guard index >= 0 && index < cocoClasses.count else { return "unknown" }
        return cocoClasses[index]
    }
}
