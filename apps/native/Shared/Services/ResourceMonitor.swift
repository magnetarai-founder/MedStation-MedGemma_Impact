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
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "ResourceMonitor")

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
        Task { [weak self] in
            await self?.updateResourceState()
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
            logger.warning("High memory pressure: \(Int(state.memoryPressure * 100))%")
        }
        if thermalWarning {
            logger.warning("Thermal state: \(state.thermalState.rawValue)")
        }
    }

    // MARK: - Resource Checks

    /// Check if safe to load a model
    func canLoadModel(estimatedMemoryGB: Float) -> Bool {
        guard let state = currentState else { return true }

        // Check available memory
        if estimatedMemoryGB > state.availableMemoryGB {
            logger.warning("Insufficient memory: Need \(estimatedMemoryGB)GB, have \(state.availableMemoryGB)GB")
            return false
        }

        // Check thermal state
        if state.thermalState == .critical {
            logger.warning("Critical thermal state - blocking model load")
            return false
        }

        // Check memory pressure
        if state.memoryPressure > 0.9 {
            logger.warning("Critical memory pressure - blocking model load")
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

// MARK: - CPU Usage

extension ResourceMonitor {
    /// Get CPU usage percentage (0.0 - 1.0)
    func getCPUUsage() -> Float {
        var totalUsageOfCPU: Float = 0.0
        var threadsList: thread_act_array_t?
        var threadsCount = mach_msg_type_number_t(0)
        var threadInfo = thread_basic_info()
        var threadInfoCount = mach_msg_type_number_t(THREAD_INFO_MAX)

        let threadsResult = withUnsafeMutablePointer(to: &threadsList) {
            return $0.withMemoryRebound(to: thread_act_array_t?.self, capacity: 1) {
                task_threads(mach_task_self_, $0, &threadsCount)
            }
        }

        if threadsResult == KERN_SUCCESS, let threadsList = threadsList {
            for index in 0..<threadsCount {
                threadInfoCount = mach_msg_type_number_t(THREAD_INFO_MAX)

                let result = withUnsafeMutablePointer(to: &threadInfo) {
                    $0.withMemoryRebound(to: integer_t.self, capacity: 1) {
                        thread_info(threadsList[Int(index)], thread_flavor_t(THREAD_BASIC_INFO), $0, &threadInfoCount)
                    }
                }

                guard result == KERN_SUCCESS else {
                    break
                }

                let threadBasicInfo = threadInfo
                if threadBasicInfo.flags & TH_FLAGS_IDLE == 0 {
                    totalUsageOfCPU += Float(threadBasicInfo.cpu_usage) / Float(TH_USAGE_SCALE)
                }
            }

            // Deallocate thread list
            vm_deallocate(mach_task_self_, vm_address_t(UInt(bitPattern: threadsList)), vm_size_t(Int(threadsCount) * MemoryLayout<thread_t>.stride))
        }

        return totalUsageOfCPU
    }

    /// Get system-wide CPU usage (all processes)
    private func getSystemCPUUsage() -> Float {
        var cpuInfo: processor_info_array_t?
        var numCPUInfo: mach_msg_type_number_t = 0
        var numProcessors: natural_t = 0

        let result = host_processor_info(mach_host_self(), PROCESSOR_CPU_LOAD_INFO, &numProcessors, &cpuInfo, &numCPUInfo)

        guard result == KERN_SUCCESS, let cpuInfo = cpuInfo else {
            return 0.0
        }

        defer {
            vm_deallocate(mach_task_self_, vm_address_t(UInt(bitPattern: cpuInfo)), vm_size_t(Int(numCPUInfo) * MemoryLayout<integer_t>.stride))
        }

        // Calculate total CPU usage across all cores
        var totalUser: UInt32 = 0
        var totalSystem: UInt32 = 0
        var totalIdle: UInt32 = 0
        var totalNice: UInt32 = 0

        for i in 0..<Int(numProcessors) {
            let baseIndex = Int(CPU_STATE_MAX) * i
            totalUser += UInt32(cpuInfo[baseIndex + Int(CPU_STATE_USER)])
            totalSystem += UInt32(cpuInfo[baseIndex + Int(CPU_STATE_SYSTEM)])
            totalIdle += UInt32(cpuInfo[baseIndex + Int(CPU_STATE_IDLE)])
            totalNice += UInt32(cpuInfo[baseIndex + Int(CPU_STATE_NICE)])
        }

        let totalTicks = totalUser + totalSystem + totalIdle + totalNice
        let usedTicks = totalUser + totalSystem + totalNice

        guard totalTicks > 0 else {
            return 0.0
        }

        return Float(usedTicks) / Float(totalTicks)
    }

    /// Get per-core CPU usage
    func getPerCoreCPUUsage() -> [Float] {
        var cpuInfo: processor_info_array_t?
        var numCPUInfo: mach_msg_type_number_t = 0
        var numProcessors: natural_t = 0

        let result = host_processor_info(mach_host_self(), PROCESSOR_CPU_LOAD_INFO, &numProcessors, &cpuInfo, &numCPUInfo)

        guard result == KERN_SUCCESS, let cpuInfo = cpuInfo else {
            return []
        }

        defer {
            vm_deallocate(mach_task_self_, vm_address_t(UInt(bitPattern: cpuInfo)), vm_size_t(Int(numCPUInfo) * MemoryLayout<integer_t>.stride))
        }

        var coreUsages: [Float] = []

        for i in 0..<Int(numProcessors) {
            let baseIndex = Int(CPU_STATE_MAX) * i
            let user = cpuInfo[baseIndex + Int(CPU_STATE_USER)]
            let system = cpuInfo[baseIndex + Int(CPU_STATE_SYSTEM)]
            let idle = cpuInfo[baseIndex + Int(CPU_STATE_IDLE)]
            let nice = cpuInfo[baseIndex + Int(CPU_STATE_NICE)]

            let total = user + system + idle + nice
            let used = user + system + nice

            if total > 0 {
                coreUsages.append(Float(used) / Float(total))
            } else {
                coreUsages.append(0.0)
            }
        }

        return coreUsages
    }
}
