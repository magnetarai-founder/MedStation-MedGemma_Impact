//
//  Header.swift
//  MagnetarStudio
//
//  Global header bar with a lighter, Xcode-like toolbar aesthetic
//  - Soft glass gradient background with subtle chroma
//  - Left: App glyph + title (no star/pill noise)
//  - Right: Condensed controls (terminal, activity, panic)
//

import SwiftUI
import Darwin
import Foundation
import SystemConfiguration

struct Header: View {
    @State private var showActivity = false
    @State private var showPanicMode = false

    var body: some View {
        ZStack(alignment: .center) {
            // Background: muted glass gradient with a faint chroma sweep
            LinearGradient(
                colors: [
                    Color(red: 0.11, green: 0.13, blue: 0.18).opacity(0.92),
                    Color(red: 0.08, green: 0.09, blue: 0.14).opacity(0.94)
                ],
                startPoint: .topLeading,
                endPoint: .bottomTrailing
            )
            .overlay(
                LinearGradient(
                    colors: [
                        Color.magnetarPrimary.opacity(0.18),
                        Color.magnetarSecondary.opacity(0.12)
                    ],
                    startPoint: .leading,
                    endPoint: .trailing
                )
                .blur(radius: 36)
            )
            .background(.regularMaterial)
            .ignoresSafeArea(edges: .top)

            // Content
            HStack(alignment: .center, spacing: 16) {
                ControlCluster(
                    showActivity: $showActivity,
                    showPanicMode: $showPanicMode
                )

                Spacer()

                BrandCluster()
            }
            .padding(.horizontal, 18)
            .padding(.vertical, 10)
            .sheet(isPresented: $showActivity) {
                ControlCenterSheet()
            }
            .sheet(isPresented: $showPanicMode) {
                PanicModeSheet()
            }
        }
        .frame(height: 54)
        .overlay(
            Rectangle()
                .fill(Color.white.opacity(0.12))
                .frame(height: 1),
            alignment: .bottom
        )
    }
}

// MARK: - Subcomponents

private struct BrandCluster: View {
    var body: some View {
        Text("MagnetarStudio")
            .font(.system(size: 22, weight: .bold))
            .foregroundColor(.primary)
    }
}

private struct ControlCluster: View {
    @Binding var showActivity: Bool
    @Binding var showPanicMode: Bool

    var body: some View {
        HStack(spacing: 10) {
            HeaderToolbarButton(icon: "switch.2") {
                showActivity = true
            }
            .help("Control Center")

            HeaderToolbarButton(
                icon: "exclamationmark.triangle.fill",
                tint: Color.red.opacity(0.9),
                background: Color.red.opacity(0.12)
            ) {
                showPanicMode = true
            }
            .help("Panic Mode")
        }
    }
}

private struct HeaderToolbarButton: View {
    let icon: String
    var label: String? = nil
    var tint: Color = .primary
    var background: Color = Color.white.opacity(0.12)
    let action: () -> Void

    @State private var isHovering = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                Image(systemName: icon)
                    .font(.system(size: 16, weight: .semibold))

                if let label {
                    Text(label)
                        .font(.system(size: 12, weight: .semibold))
                        .padding(.trailing, 2)
                }
            }
            .foregroundColor(tint.opacity(isHovering ? 1.0 : 0.85))
            .padding(.horizontal, label == nil ? 10 : 12)
            .padding(.vertical, 8)
            .background(
                RoundedRectangle(cornerRadius: 10, style: .continuous)
                    .fill(background.opacity(isHovering ? 1.0 : 0.8))
                    .overlay(
                        RoundedRectangle(cornerRadius: 10, style: .continuous)
                            .stroke(Color.white.opacity(0.18), lineWidth: 0.6)
                    )
            )
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.easeInOut(duration: 0.15)) {
                isHovering = hovering
            }
        }
    }
}

// MARK: - Sheet Views

// MARK: - Control Center Sheet

private struct ControlCenterSheet: View {
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
                print("Failed to load terminal count: \(error.localizedDescription)")
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

// MARK: - Activity Monitor Tile

private struct ActivityMonitorTile: View {
    let stats: SystemStats

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            Text("System Resources")
                .font(.system(size: 15, weight: .semibold))

            VStack(spacing: 16) {
                ResourceRow(icon: "cpu", label: "CPU", percentage: stats.cpuUsage, color: .blue)
                ResourceRow(icon: "memorychip", label: "Memory", percentage: stats.memoryUsage, color: .green)
                ResourceRow(icon: "internaldrive", label: "Disk", percentage: stats.diskUsage, color: .orange)

                HStack(spacing: 12) {
                    Image(systemName: "network")
                        .font(.system(size: 18))
                        .foregroundColor(.purple)
                        .frame(width: 28)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Network")
                            .font(.system(size: 13, weight: .medium))

                        HStack(spacing: 12) {
                            HStack(spacing: 4) {
                                Image(systemName: "arrow.down")
                                    .font(.system(size: 10))
                                Text(stats.networkIn)
                                    .font(.system(size: 11))
                            }
                            HStack(spacing: 4) {
                                Image(systemName: "arrow.up")
                                    .font(.system(size: 10))
                                Text(stats.networkOut)
                                    .font(.system(size: 11))
                            }
                        }
                        .foregroundColor(.secondary)
                    }
                    Spacer()
                }
                .padding(.horizontal, 24)
            }
        }
        .padding(16)
        .background(Color.secondary.opacity(0.08))
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

// MARK: - Control Center Button

private struct ControlCenterButton: View {
    let icon: String
    let label: String
    let color: Color
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            VStack(spacing: 8) {
                ZStack {
                    Circle()
                        .fill(color.opacity(0.15))
                        .frame(width: 52, height: 52)

                    Image(systemName: icon)
                        .font(.system(size: 22))
                        .foregroundColor(color)
                }

                Text(label)
                    .font(.system(size: 11, weight: .medium))
                    .foregroundColor(.primary)
            }
            .frame(maxWidth: .infinity)
            .padding(.vertical, 12)
            .background(
                RoundedRectangle(cornerRadius: 12)
                    .fill(isHovered ? Color.secondary.opacity(0.08) : Color.clear)
            )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            withAnimation(.magnetarQuick) {
                isHovered = hovering
            }
        }
    }
}

// MARK: - Network Status Row

private struct NetworkStatusRow: View {
    let icon: String
    let label: String
    let status: String
    let isActive: Bool

    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 18))
                .foregroundColor(isActive ? .magnetarPrimary : .secondary)
                .frame(width: 28)

            VStack(alignment: .leading, spacing: 2) {
                Text(label)
                    .font(.system(size: 13, weight: .medium))
                    .foregroundColor(.primary)

                Text(status)
                    .font(.system(size: 11))
                    .foregroundColor(.secondary)
            }

            Spacer()

            if isActive {
                Circle()
                    .fill(Color.green)
                    .frame(width: 8, height: 8)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .background(
            RoundedRectangle(cornerRadius: 8)
                .fill(isHovered ? Color.secondary.opacity(0.08) : Color.clear)
        )
        .onHover { hovering in
            withAnimation(.magnetarQuick) {
                isHovered = hovering
            }
        }
    }
}

private struct ResourceRow: View {
    let icon: String
    let label: String
    let percentage: Double
    let color: Color

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 20))
                .foregroundColor(color)
                .frame(width: 32)

            VStack(alignment: .leading, spacing: 4) {
                HStack {
                    Text(label)
                        .font(.system(size: 14, weight: .medium))
                    Spacer()
                    Text("\(Int(percentage))%")
                        .font(.system(size: 13, weight: .medium))
                        .foregroundColor(.secondary)
                }

                GeometryReader { geometry in
                    ZStack(alignment: .leading) {
                        Rectangle()
                            .fill(Color.gray.opacity(0.2))
                            .frame(height: 6)
                            .cornerRadius(3)

                        Rectangle()
                            .fill(color)
                            .frame(width: geometry.size.width * (percentage / 100), height: 6)
                            .cornerRadius(3)
                    }
                }
                .frame(height: 6)
            }
            .frame(maxWidth: .infinity)
        }
        .padding(.horizontal, 24)
    }
}

private struct PanicModeSheet: View {
    @Environment(\.dismiss) private var dismiss
    @EnvironmentObject private var authStore: AuthStore
    @StateObject private var vaultStore = VaultStore.shared

    @State private var isExecuting = false
    @State private var shouldQuitApp = false

    var body: some View {
        VStack(spacing: 24) {
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

            // Warning Icon
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 64))
                .foregroundColor(.red)

            // Title
            Text("Panic Mode")
                .font(.system(size: 24, weight: .bold))

            // Description
            VStack(spacing: 12) {
                Text("Emergency Security Protocol")
                    .font(.system(size: 16, weight: .semibold))

                Text("This will immediately:")
                    .font(.system(size: 14))
                    .foregroundColor(.secondary)

                VStack(alignment: .leading, spacing: 8) {
                    SecurityActionRow(icon: "lock.fill", text: "Lock all vaults")
                    SecurityActionRow(icon: "arrow.right.square.fill", text: "Log out of your account")
                    SecurityActionRow(icon: "trash.fill", text: "Clear sensitive data from memory")
                    SecurityActionRow(icon: "xmark.circle.fill", text: "Optionally quit the application")
                }
                .padding()
                .background(Color.red.opacity(0.1))
                .cornerRadius(12)
            }

            // Quit App Option
            Toggle(isOn: $shouldQuitApp) {
                HStack {
                    Image(systemName: "power")
                        .foregroundColor(.red)
                    Text("Quit application after panic")
                        .font(.system(size: 14, weight: .medium))
                }
            }
            .toggleStyle(.checkbox)
            .padding(.horizontal, 40)

            Spacer()

            // Action Buttons
            HStack(spacing: 12) {
                Button("Cancel") {
                    dismiss()
                }
                .buttonStyle(.bordered)
                .keyboardShortcut(.cancelAction)

                Button(action: executePanicMode) {
                    HStack {
                        if isExecuting {
                            ProgressView()
                                .scaleEffect(0.7)
                                .frame(width: 14, height: 14)
                        } else {
                            Image(systemName: "exclamationmark.triangle.fill")
                        }
                        Text(isExecuting ? "Executing..." : "Execute Panic Mode")
                    }
                    .frame(minWidth: 180)
                }
                .buttonStyle(.borderedProminent)
                .tint(.red)
                .disabled(isExecuting)
                .keyboardShortcut(.defaultAction)
            }
            .padding(.bottom, 24)
        }
        .frame(width: 480, height: 560)
    }

    private func executePanicMode() {
        isExecuting = true

        Task { @MainActor in
            // 1. Lock all vaults
            vaultStore.lock()

            // 2. Clear database sessions (if DatabaseStore becomes observable)
            NotificationCenter.default.post(name: .init("DatabaseWorkspaceClearWorkspace"), object: nil)

            // Small delay for visual feedback
            try? await Task.sleep(nanoseconds: 500_000_000) // 0.5 seconds

            // 3. Logout (clears token and sensitive data)
            await authStore.logout()

            // 4. Quit app if requested
            if shouldQuitApp {
                try? await Task.sleep(nanoseconds: 300_000_000) // 0.3 seconds
                NSApplication.shared.terminate(nil)
            }

            dismiss()
        }
    }
}

private struct SecurityActionRow: View {
    let icon: String
    let text: String

    var body: some View {
        HStack(spacing: 10) {
            Image(systemName: icon)
                .font(.system(size: 14))
                .foregroundColor(.red)
                .frame(width: 20)

            Text(text)
                .font(.system(size: 13))
                .foregroundColor(.primary)

            Spacer()
        }
    }
}

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

// MARK: - Preview

#Preview {
    Header()
        .frame(width: 1200)
}
