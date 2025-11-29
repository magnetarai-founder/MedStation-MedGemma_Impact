//
//  ResourceMonitor.swift
//  MagnetarStudio
//
//  Monitors system resources to prevent crashes and thermal throttling
//  Part of Noah's Ark for the Digital Age - Resource management
//
//  Foundation: Matthew 7:24-25 - Built on the rock, not sand
//

import Foundation
import Combine

// MARK: - Resource Monitor

/// Monitors system resources in real-time
@MainActor
class ResourceMonitor: ObservableObject {
    static let shared = ResourceMonitor()

    @Published var currentState: SystemResourceState?
    @Published var memoryWarning: Bool = false
    @Published var thermalWarning: Bool = false

    private var timer: Timer?
    private let updateInterval: TimeInterval = 5.0  // Update every 5 seconds

    private init() {
        startMonitoring()
    }

    // MARK: - Monitoring

    func startMonitoring() {
        // Initial update
        Task {
            await updateResourceState()
        }

        // Periodic updates
        timer = Timer.scheduledTimer(withTimeInterval: updateInterval, repeats: true) { [weak self] _ in
            Task { @MainActor in
                await self?.updateResourceState()
            }
        }
    }

    func stopMonitoring() {
        timer?.invalidate()
        timer = nil
    }

    private func updateResourceState() async {
        let state = await SystemResourceState.current()
        currentState = state

        // Update warnings
        memoryWarning = state.memoryPressure > 0.8
        thermalWarning = state.thermalState == .serious || state.thermalState == .critical

        // Log warnings
        if memoryWarning {
            print("⚠️ High memory pressure: \(Int(state.memoryPressure * 100))%")
        }
        if thermalWarning {
            print("⚠️ Thermal state: \(state.thermalState.rawValue)")
        }
    }

    // MARK: - Resource Checks

    /// Check if safe to load a model
    func canLoadModel(estimatedMemoryGB: Float) -> Bool {
        guard let state = currentState else { return true }

        // Check available memory
        if estimatedMemoryGB > state.availableMemoryGB {
            print("✗ Insufficient memory: Need \(estimatedMemoryGB)GB, have \(state.availableMemoryGB)GB")
            return false
        }

        // Check thermal state
        if state.thermalState == .critical {
            print("✗ Critical thermal state - blocking model load")
            return false
        }

        // Check memory pressure
        if state.memoryPressure > 0.9 {
            print("✗ Critical memory pressure - blocking model load")
            return false
        }

        return true
    }

    /// Get recommendation for model size based on current resources
    func getRecommendedModelSize() -> ModelSizeRecommendation {
        guard let state = currentState else {
            return .medium
        }

        // Check memory pressure
        if state.memoryPressure > 0.7 {
            return .small
        }

        // Check thermal state
        if state.thermalState == .serious || state.thermalState == .critical {
            return .small
        }

        // Check available memory
        if state.availableMemoryGB < 8 {
            return .small
        } else if state.availableMemoryGB < 16 {
            return .medium
        } else {
            return .large
        }
    }
}

// MARK: - Model Size Recommendation

enum ModelSizeRecommendation {
    case small   // < 5GB (3B models)
    case medium  // 5-10GB (7-8B models)
    case large   // > 10GB (30B+ models)

    var maxMemoryGB: Float {
        switch self {
        case .small: return 5
        case .medium: return 10
        case .large: return 50
        }
    }

    var description: String {
        switch self {
        case .small: return "Small models (< 5GB)"
        case .medium: return "Medium models (5-10GB)"
        case .large: return "Large models (> 10GB)"
        }
    }
}

// MARK: - CPU Usage (Future Enhancement)

extension ResourceMonitor {
    /// Get CPU usage percentage
    /// TODO: Implement proper CPU monitoring
    private func getCPUUsage() -> Float {
        // Simplified - return 0 for now
        // Real implementation would use host_processor_info or similar
        return 0.0
    }
}
