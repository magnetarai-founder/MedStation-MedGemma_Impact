import Foundation
import CoreGraphics

/// Result from Depth Anything V2
struct DepthMapResult: Codable, Sendable {
    let depthData: Data
    let width: Int
    let height: Int
    let minDepth: Float
    let maxDepth: Float
    let averageDepth: Float
    let depthHistogram: [Float]

    init(
        depthData: Data,
        width: Int,
        height: Int,
        minDepth: Float,
        maxDepth: Float,
        averageDepth: Float,
        depthHistogram: [Float] = []
    ) {
        self.depthData = depthData
        self.width = width
        self.height = height
        self.minDepth = minDepth
        self.maxDepth = maxDepth
        self.averageDepth = averageDepth
        self.depthHistogram = depthHistogram.isEmpty ? Array(repeating: 0, count: 10) : depthHistogram
    }

    /// Get depth at normalized coordinates (0-1)
    func depthAt(x: Float, y: Float) -> Float? {
        guard x >= 0, x <= 1, y >= 0, y <= 1 else { return nil }

        let pixelX = Int(x * Float(width - 1))
        let pixelY = Int(y * Float(height - 1))
        let index = pixelY * width + pixelX

        guard index * MemoryLayout<Float>.size < depthData.count else { return nil }

        return depthData.withUnsafeBytes { buffer in
            buffer.load(fromByteOffset: index * MemoryLayout<Float>.size, as: Float.self)
        }
    }

    /// Get depth for a bounding box region
    func averageDepthInRegion(_ rect: CGRect) -> Float? {
        var sum: Float = 0
        var count = 0

        let startX = Int(rect.minX * CGFloat(width))
        let endX = Int(rect.maxX * CGFloat(width))
        let startY = Int(rect.minY * CGFloat(height))
        let endY = Int(rect.maxY * CGFloat(height))

        for y in startY..<endY {
            for x in startX..<endX {
                if let depth = depthAt(x: Float(x) / Float(width), y: Float(y) / Float(height)) {
                    sum += depth
                    count += 1
                }
            }
        }

        return count > 0 ? sum / Float(count) : nil
    }

    /// Depth range category
    var depthCategory: DepthCategory {
        switch averageDepth {
        case 0..<0.3: return .closeUp
        case 0.3..<0.6: return .medium
        default: return .far
        }
    }

    enum DepthCategory: String, Codable, Sendable {
        case closeUp = "close-up"
        case medium = "medium distance"
        case far = "far distance"
    }

    /// Generate a depth description for AI context
    var depthDescription: String {
        "Depth analysis: \(depthCategory.rawValue) shot, depth range \(String(format: "%.2f", minDepth))-\(String(format: "%.2f", maxDepth))"
    }
}

/// Empty depth result for when depth estimation is skipped
extension DepthMapResult {
    static let empty = DepthMapResult(
        depthData: Data(),
        width: 0,
        height: 0,
        minDepth: 0,
        maxDepth: 0,
        averageDepth: 0
    )
}
