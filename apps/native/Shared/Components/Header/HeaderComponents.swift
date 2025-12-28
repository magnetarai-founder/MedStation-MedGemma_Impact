//
//  HeaderComponents.swift
//  MagnetarStudio
//
//  Reusable header UI components - Extracted from Header.swift
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "HeaderComponents")

// MARK: - Brand Cluster

struct BrandCluster: View {
    var body: some View {
        Text("MagnetarStudio")
            .font(.system(size: 22, weight: .bold))
            .foregroundColor(.primary)
    }
}

// MARK: - Control Cluster

struct ControlCluster: View {
    @Binding var showActivity: Bool
    @Binding var showPanicMode: Bool
    @Binding var showEmergencyMode: Bool
    @Environment(\.openWindow) private var openWindow

    @State private var clickCount: Int = 0
    @State private var lastClickTime: Date = Date.distantPast

    var body: some View {
        HStack(spacing: 10) {
            // Model Manager button
            HeaderToolbarButton(icon: "bolt.fill") {
                openWindow(id: "model-manager")
            }
            .help("Model Manager (⌘M)")

            HeaderToolbarButton(icon: "switch.2") {
                showActivity = true
            }
            .help("Control Center")

            HeaderToolbarButton(
                icon: "exclamationmark.triangle.fill",
                tint: Color.red.opacity(0.9),
                background: Color.red.opacity(0.12)
            ) {
                handlePanicButtonClick()
            }
            .help("Panic Mode (Double-click) / Emergency Mode (Triple-click)")
        }
    }

    // MARK: - Triple-Click Detection

    private func handlePanicButtonClick() {
        let now = Date()
        let timeSinceLastClick = now.timeIntervalSince(lastClickTime)

        // Reset if more than 1 second since last click
        if timeSinceLastClick > 1.0 {
            clickCount = 1
        } else {
            clickCount += 1
        }

        lastClickTime = now

        logger.debug("Panic button clicked (\(clickCount) clicks)")

        // Double-click: Standard panic mode
        if clickCount == 2 {
            logger.info("Opening standard panic mode")
            showPanicMode = true
            clickCount = 0  // Reset
        }
        // Triple-click: Emergency mode
        else if clickCount >= 3 {
            logger.warning("Opening EMERGENCY MODE")
            showEmergencyMode = true
            clickCount = 0  // Reset
        }
    }
}

// MARK: - Header Toolbar Button

struct HeaderToolbarButton: View {
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

// MARK: - Activity Monitor Tile

struct ActivityMonitorTile: View {
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

struct ControlCenterButton: View {
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

struct NetworkStatusRow: View {
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

// MARK: - Resource Row

struct ResourceRow: View {
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

// MARK: - Security Action Row

struct SecurityActionRow: View {
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
