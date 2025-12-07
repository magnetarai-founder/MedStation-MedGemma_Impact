//
//  SystemCapabilityService.swift
//  MagnetarStudio
//
//  Service for checking system capabilities and model compatibility
//

import Foundation
import os

class SystemCapabilityService {
    static let shared = SystemCapabilityService()

    // MARK: - System Info

    private(set) var totalMemoryGB: Double = 0
    private(set) var availableMemoryGB: Double = 0
    private(set) var cpuCores: Int = 0
    private(set) var hasMetalSupport: Bool = false

    init() {
        refreshSystemInfo()
    }

    func refreshSystemInfo() {
        // Get unified memory
        var size: UInt64 = 0
        var len: size_t = MemoryLayout<UInt64>.size
        sysctlbyname("hw.memsize", &size, &len, nil, 0)
        totalMemoryGB = Double(size) / 1_073_741_824.0 // Convert to GB

        // Get CPU cores
        var cores: Int = 0
        var coreLen: size_t = MemoryLayout<Int>.size
        sysctlbyname("hw.ncpu", &cores, &coreLen, nil, 0)
        cpuCores = cores

        // Check Metal support (Apple Silicon always has Metal)
        #if arch(arm64)
        hasMetalSupport = true
        #else
        hasMetalSupport = false
        #endif

        // Get available memory (rough estimate)
        availableMemoryGB = totalMemoryGB * 0.7 // Assume ~70% is available for models
    }

    // MARK: - Model Compatibility

    func canRunModel(parameterSize: String) -> ModelCompatibility {
        // Parse parameter size (e.g., "7B", "13B", "70B")
        guard let sizeGB = parseParameterSize(parameterSize) else {
            return ModelCompatibility(canRun: false, reason: "Unknown model size", performance: .unknown)
        }

        // Estimate memory requirements
        // Rule of thumb: Model needs ~1.2x its size in RAM (for quantized models)
        // Q4 quantization: ~0.5 bytes per parameter
        // Q8 quantization: ~1 byte per parameter
        // FP16: ~2 bytes per parameter

        let estimatedMemoryGB = sizeGB * 0.6 // Assuming Q4 quantization
        let recommendedMemoryGB = estimatedMemoryGB * 1.3 // Add 30% overhead

        // Check if model can run
        if availableMemoryGB >= recommendedMemoryGB {
            // Plenty of memory
            if availableMemoryGB >= recommendedMemoryGB * 1.5 {
                return ModelCompatibility(
                    canRun: true,
                    reason: "Perfect for your Mac - will run fast and smooth",
                    performance: .excellent,
                    estimatedMemoryUsage: estimatedMemoryGB,
                    friendlyExplanation: "This model size is ideal for your system. You'll get great performance with plenty of memory to spare."
                )
            } else {
                return ModelCompatibility(
                    canRun: true,
                    reason: "Works well on your Mac",
                    performance: .good,
                    estimatedMemoryUsage: estimatedMemoryGB,
                    friendlyExplanation: "This model will run smoothly on your system with good performance."
                )
            }
        } else if availableMemoryGB >= estimatedMemoryGB {
            // Tight fit
            return ModelCompatibility(
                canRun: true,
                reason: "Will work, but may be slower",
                performance: .fair,
                estimatedMemoryUsage: estimatedMemoryGB,
                friendlyExplanation: "This model can run on your Mac, but responses might be slower. Consider a smaller size for better performance."
            )
        } else {
            // Not enough memory
            let requiredGB = Int(ceil(recommendedMemoryGB))
            return ModelCompatibility(
                canRun: false,
                reason: "Not recommended - needs \(requiredGB)GB+ memory",
                performance: .insufficient,
                estimatedMemoryUsage: estimatedMemoryGB,
                friendlyExplanation: "This model needs more memory than your Mac has available. Try a smaller version instead."
            )
        }
    }

    private func parseParameterSize(_ sizeString: String) -> Double? {
        // Parse sizes like "7B", "13B", "70B", "1.5B"
        let cleanString = sizeString.uppercased().replacingOccurrences(of: "B", with: "").trimmingCharacters(in: .whitespaces)

        if let value = Double(cleanString) {
            return value
        }

        return nil
    }

    // MARK: - System Recommendations

    func getRecommendedModelSizes() -> [String] {
        // Based on available memory, recommend model sizes
        if availableMemoryGB >= 64 {
            return ["70B", "34B", "13B", "7B", "3B"]
        } else if availableMemoryGB >= 32 {
            return ["34B", "13B", "7B", "3B"]
        } else if availableMemoryGB >= 16 {
            return ["13B", "7B", "3B", "1.5B"]
        } else if availableMemoryGB >= 8 {
            return ["7B", "3B", "1.5B"]
        } else {
            return ["3B", "1.5B"]
        }
    }

    func getSystemSummary() -> String {
        """
        System: \(Int(totalMemoryGB))GB Unified Memory, \(cpuCores) CPU Cores
        Available: ~\(Int(availableMemoryGB))GB for models
        Metal: \(hasMetalSupport ? "✓" : "✗")
        """
    }
}

// MARK: - Models

struct ModelCompatibility {
    let canRun: Bool
    let reason: String
    let performance: PerformanceLevel
    var estimatedMemoryUsage: Double? = nil
    var friendlyExplanation: String? = nil

    enum PerformanceLevel {
        case excellent
        case good
        case fair
        case insufficient
        case unknown

        var color: String {
            switch self {
            case .excellent: return "green"
            case .good: return "blue"
            case .fair: return "orange"
            case .insufficient: return "red"
            case .unknown: return "gray"
            }
        }

        var icon: String {
            switch self {
            case .excellent: return "checkmark.seal.fill"
            case .good: return "checkmark.circle.fill"
            case .fair: return "exclamationmark.triangle.fill"
            case .insufficient: return "xmark.circle.fill"
            case .unknown: return "questionmark.circle.fill"
            }
        }
    }
}
