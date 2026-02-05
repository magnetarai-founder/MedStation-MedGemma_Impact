//
//  ControlCenterSheet.swift
//  MagnetarStudio
//
//  STUB: Not currently wired — future system monitoring panel.
//  Control Center modal with system stats - Extracted from Header.swift
//

import SwiftUI
import Darwin
import Foundation
import SystemConfiguration
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "ControlCenterSheet")

struct ControlCenterSheet: View {
    @Environment(\.dismiss) private var dismiss

    // System Stats
    @State private var stats = SystemStats()
    @State private var lastBytesIn: UInt64 = 0
    @State private var lastBytesOut: UInt64 = 0
    @State private var lastNetworkCheck: Date = Date()
    let timer = Timer.publish(every: 3, on: .main, in: .common).autoconnect()

    // Terminal Sessions
    @State private var terminalCount: Int = 0
    @State private var showTerminalMenu: Bool = false

    var body: some View {
        VStack(spacing: 0) {
            // Close button
            HStack {
                Spacer()
                Button(action: { dismiss() }) {
                    Image(systemName: "xmark")
                        .font(.system(size: 14, weight: .medium))
                        .foregroundColor(.secondary)
                        .padding(8)
                        .background(Color.secondary.opacity(0.1))
                        .clipShape(Circle())
                }
                .buttonStyle(.plain)
                .help("Close")
            }
            .padding(.horizontal, 24)
            .padding(.top, 16)

            // Header
            Text("Control Center")
                .font(.system(size: 20, weight: .bold))
                .padding(.top, 8)
                .padding(.bottom, 24)

            ScrollView {
                VStack(spacing: 16) {
                    // Terminal Button with Session Count
                    HStack(spacing: 8) {
                        Button {
                            openSystemTerminal()
                        } label: {
                            HStack(spacing: 6) {
                                Image(systemName: "terminal.fill")
                                    .font(.system(size: 14))
                                    .foregroundColor(.blue)
                                Text("Terminal")
                                    .font(.system(size: 12, weight: .medium))
                                    .foregroundColor(.primary)
                            }
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(Color.secondary.opacity(0.08))
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                        }
                        .buttonStyle(.plain)
                        .disabled(terminalCount >= 3)

                        // Session count badge - same size as button
                        Text("\(terminalCount)/3")
                            .font(.system(size: 12, weight: .medium))
                            .foregroundColor(terminalCount >= 3 ? .red : .secondary)
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(Color.secondary.opacity(0.08))
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                    }

                    // Activity Monitor - always visible
                    ActivityMonitorTile(stats: stats)
                }
                .padding(.horizontal, 24)
                .padding(.bottom, 24)
            }
        }
        .frame(width: 500, height: 450)
        .onAppear {
            updateSystemStats()
            loadTerminalCount()
        }
        .onReceive(timer) { _ in
            updateSystemStats()
            loadTerminalCount()
        }
    }

    private func loadTerminalCount() {
        Task {
            do {
                let response = try await TerminalService.shared.listSessions()
                await MainActor.run {
                    terminalCount = response.count
                }
            } catch {
                logger.debug("Failed to load terminal count: \(error.localizedDescription)")
                // Keep the current count (defaults to 0)
            }
        }
    }

    private func updateSystemStats() {
        // Create new stats struct with updated values
        var newStats = SystemStats()

        // CPU Usage
        var cpuInfo = host_cpu_load_info()
        var count = mach_msg_type_number_t(MemoryLayout<host_cpu_load_info>.size / MemoryLayout<integer_t>.size)
        let result = withUnsafeMutablePointer(to: &cpuInfo) {
            $0.withMemoryRebound(to: integer_t.self, capacity: Int(count)) {
                host_statistics(mach_host_self(), HOST_CPU_LOAD_INFO, $0, &count)
            }
        }

        if result == KERN_SUCCESS {
            let user = Double(cpuInfo.cpu_ticks.0)
            let system = Double(cpuInfo.cpu_ticks.1)
            let idle = Double(cpuInfo.cpu_ticks.2)
            let nice = Double(cpuInfo.cpu_ticks.3)
            let total = user + system + idle + nice
            newStats.cpuUsage = total > 0 ? ((user + system + nice) / total) * 100 : 0
        }

        // Memory Usage
        var vmStats = vm_statistics64()
        var size = mach_msg_type_number_t(MemoryLayout<vm_statistics64>.size / MemoryLayout<integer_t>.size)
        let hostPort = mach_host_self()

        let memResult = withUnsafeMutablePointer(to: &vmStats) {
            $0.withMemoryRebound(to: integer_t.self, capacity: Int(size)) {
                host_statistics64(hostPort, HOST_VM_INFO64, $0, &size)
            }
        }

        if memResult == KERN_SUCCESS {
            let pageSize = vm_kernel_page_size
            let used = (UInt64(vmStats.active_count) + UInt64(vmStats.wire_count)) * UInt64(pageSize)
            let free = UInt64(vmStats.free_count) * UInt64(pageSize)
            let total = used + free
            newStats.memoryUsage = total > 0 ? (Double(used) / Double(total)) * 100 : 0
        }

        // Disk Usage
        if let home = FileManager.default.urls(for: .userDirectory, in: .userDomainMask).first {
            if let values = try? home.resourceValues(forKeys: [URLResourceKey.volumeTotalCapacityKey, URLResourceKey.volumeAvailableCapacityKey]),
               let total = values.volumeTotalCapacity,
               let available = values.volumeAvailableCapacity {
                let used = total - available
                newStats.diskUsage = total > 0 ? (Double(used) / Double(total)) * 100 : 0
            }
        }

        // Network - Real network statistics
        updateNetworkStats(into: &newStats)

        // Only update if values changed significantly (reduces unnecessary re-renders)
        if stats.hasSignificantChange(from: newStats) {
            stats = newStats
        }
    }

    @MainActor
    private func updateNetworkStats(into stats: inout SystemStats) {
        var ifaddr: UnsafeMutablePointer<ifaddrs>?
        guard getifaddrs(&ifaddr) == 0 else { return }
        defer { freeifaddrs(ifaddr) }

        var currentBytesIn: UInt64 = 0
        var currentBytesOut: UInt64 = 0

        var ptr = ifaddr
        while let interface = ptr {
            defer { ptr = interface.pointee.ifa_next }

            // Get interface name
            let name = String(cString: interface.pointee.ifa_name)

            // Skip loopback
            guard !name.hasPrefix("lo") else { continue }

            // Get interface data
            if let data = interface.pointee.ifa_data {
                let networkData = data.assumingMemoryBound(to: if_data.self)
                currentBytesIn += UInt64(networkData.pointee.ifi_ibytes)
                currentBytesOut += UInt64(networkData.pointee.ifi_obytes)
            }
        }

        // Calculate speed if we have previous measurements
        let now = Date()
        let timeDelta = now.timeIntervalSince(lastNetworkCheck)

        if lastBytesIn > 0 && lastBytesOut > 0 && timeDelta > 0 {
            let bytesInDelta = currentBytesIn > lastBytesIn ? currentBytesIn - lastBytesIn : 0
            let bytesOutDelta = currentBytesOut > lastBytesOut ? currentBytesOut - lastBytesOut : 0

            let speedIn = Double(bytesInDelta) / timeDelta
            let speedOut = Double(bytesOutDelta) / timeDelta

            stats.networkIn = formatBytes(speedIn) + "/s"
            stats.networkOut = formatBytes(speedOut) + "/s"
        }

        lastBytesIn = currentBytesIn
        lastBytesOut = currentBytesOut
        lastNetworkCheck = now
    }

    private func formatBytes(_ bytes: Double) -> String {
        if bytes < 1024 {
            return String(format: "%.0f B", bytes)
        } else if bytes < 1024 * 1024 {
            return String(format: "%.1f KB", bytes / 1024)
        } else if bytes < 1024 * 1024 * 1024 {
            return String(format: "%.1f MB", bytes / (1024 * 1024))
        } else {
            return String(format: "%.1f GB", bytes / (1024 * 1024 * 1024))
        }
    }

    private func openSystemTerminal() {
        let workspace = NSWorkspace.shared
        let terminalURL = URL(fileURLWithPath: "/System/Applications/Utilities/Terminal.app")
        workspace.open(terminalURL)
    }
}
