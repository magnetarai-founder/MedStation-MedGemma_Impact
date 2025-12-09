//
//  HeaderModels.swift
//  MagnetarStudio
//
//  System stats model for Control Center - Extracted from Header.swift
//

import Foundation

// MARK: - System Stats Model

struct SystemStats: Equatable {
    var cpuUsage: Double = 0
    var memoryUsage: Double = 0
    var diskUsage: Double = 0
    var networkIn: String = "0 KB/s"
    var networkOut: String = "0 KB/s"

    // Check if values changed significantly (> 1% for percentages, any change for network)
    func hasSignificantChange(from other: SystemStats) -> Bool {
        let cpuChanged = abs(cpuUsage - other.cpuUsage) > 1.0
        let memoryChanged = abs(memoryUsage - other.memoryUsage) > 1.0
        let diskChanged = abs(diskUsage - other.diskUsage) > 1.0
        let networkChanged = networkIn != other.networkIn || networkOut != other.networkOut

        return cpuChanged || memoryChanged || diskChanged || networkChanged
    }
}
