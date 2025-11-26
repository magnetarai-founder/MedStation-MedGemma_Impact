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

struct Header: View {
    @State private var showTerminals = false
    @State private var showActivity = false
    @State private var showPanicMode = false
    @State private var terminalCount = 0

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
                    terminalCount: terminalCount,
                    showTerminals: $showTerminals,
                    showActivity: $showActivity,
                    showPanicMode: $showPanicMode
                )

                Spacer()

                BrandCluster()
            }
            .padding(.horizontal, 18)
            .padding(.vertical, 10)
            .sheet(isPresented: $showActivity) {
                ActivitySheet()
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
    let terminalCount: Int
    @Binding var showTerminals: Bool
    @Binding var showActivity: Bool
    @Binding var showPanicMode: Bool

    var body: some View {
        HStack(spacing: 10) {
            HeaderToolbarButton(icon: "terminal", label: "\(terminalCount)") {
                openSystemTerminal()
            }
            .help("Open Terminal")

            HeaderToolbarButton(icon: "chart.bar.fill") {
                showActivity = true
            }
            .help("Activity")

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

    private func openSystemTerminal() {
        // Try to open iTerm2 first, then fall back to Terminal.app
        let iTerm = NSWorkspace.shared.urlForApplication(withBundleIdentifier: "com.googlecode.iterm2")
        let terminal = NSWorkspace.shared.urlForApplication(withBundleIdentifier: "com.apple.Terminal")

        if let iTermURL = iTerm {
            NSWorkspace.shared.open(iTermURL)
        } else if let terminalURL = terminal {
            NSWorkspace.shared.open(terminalURL)
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

private struct ActivitySheet: View {
    @State private var cpuUsage: Double = 0
    @State private var memoryUsage: Double = 0
    @State private var diskUsage: Double = 0
    @State private var networkIn: String = "0 KB/s"
    @State private var networkOut: String = "0 KB/s"

    let timer = Timer.publish(every: 2, on: .main, in: .common).autoconnect()

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Activity Monitor")
                    .font(.system(size: 18, weight: .bold))
                Spacer()
            }
            .padding(.horizontal, 24)
            .padding(.top, 24)
            .padding(.bottom, 20)

            // System Resources
            VStack(spacing: 20) {
                // CPU
                ResourceRow(
                    icon: "cpu",
                    label: "CPU",
                    percentage: cpuUsage,
                    color: .blue
                )

                // Memory
                ResourceRow(
                    icon: "memorychip",
                    label: "Memory",
                    percentage: memoryUsage,
                    color: .green
                )

                // Disk
                ResourceRow(
                    icon: "internaldrive",
                    label: "Disk",
                    percentage: diskUsage,
                    color: .orange
                )

                // Network
                HStack(spacing: 12) {
                    Image(systemName: "network")
                        .font(.system(size: 20))
                        .foregroundColor(.purple)
                        .frame(width: 32)

                    VStack(alignment: .leading, spacing: 4) {
                        Text("Network")
                            .font(.system(size: 14, weight: .medium))

                        HStack(spacing: 16) {
                            HStack(spacing: 4) {
                                Image(systemName: "arrow.down")
                                    .font(.system(size: 10))
                                Text(networkIn)
                                    .font(.system(size: 12))
                            }
                            .foregroundColor(.secondary)

                            HStack(spacing: 4) {
                                Image(systemName: "arrow.up")
                                    .font(.system(size: 10))
                                Text(networkOut)
                                    .font(.system(size: 12))
                            }
                            .foregroundColor(.secondary)
                        }
                    }

                    Spacer()
                }
                .padding(.horizontal, 24)
            }
            .padding(.bottom, 24)
        }
        .frame(width: 500, height: 400)
        .onAppear {
            updateSystemStats()
        }
        .onReceive(timer) { _ in
            updateSystemStats()
        }
    }

    private func updateSystemStats() {
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
            cpuUsage = total > 0 ? ((user + system + nice) / total) * 100 : 0
        }

        // Memory Usage
        var stats = vm_statistics64()
        var size = mach_msg_type_number_t(MemoryLayout<vm_statistics64>.size / MemoryLayout<integer_t>.size)
        let hostPort = mach_host_self()

        let memResult = withUnsafeMutablePointer(to: &stats) {
            $0.withMemoryRebound(to: integer_t.self, capacity: Int(size)) {
                host_statistics64(hostPort, HOST_VM_INFO64, $0, &size)
            }
        }

        if memResult == KERN_SUCCESS {
            let pageSize = vm_kernel_page_size
            let used = (UInt64(stats.active_count) + UInt64(stats.wire_count)) * UInt64(pageSize)
            let free = UInt64(stats.free_count) * UInt64(pageSize)
            let total = used + free
            memoryUsage = total > 0 ? (Double(used) / Double(total)) * 100 : 0
        }

        // Disk Usage
        if let home = FileManager.default.urls(for: .userDirectory, in: .userDomainMask).first {
            if let values = try? home.resourceValues(forKeys: [URLResourceKey.volumeTotalCapacityKey, URLResourceKey.volumeAvailableCapacityKey]),
               let total = values.volumeTotalCapacity,
               let available = values.volumeAvailableCapacity {
                let used = total - available
                diskUsage = total > 0 ? (Double(used) / Double(total)) * 100 : 0
            }
        }

        // Network (simplified - showing static placeholder)
        networkIn = "\(Int.random(in: 10...500)) KB/s"
        networkOut = "\(Int.random(in: 5...200)) KB/s"
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
    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 48))
                .foregroundColor(.red)

            Text("Panic Mode")
                .font(.system(size: 18, weight: .bold))

            Text("Emergency shutdown and security features coming soon")
                .font(.system(size: 14))
                .foregroundColor(.secondary)
                .multilineTextAlignment(.center)
        }
        .frame(width: 600, height: 400)
        .padding()
    }
}

// MARK: - Preview

#Preview {
    Header()
        .frame(width: 1200)
}
