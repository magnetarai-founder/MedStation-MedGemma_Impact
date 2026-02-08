//
//  VaultResourcesTab.swift
//  MagnetarStudio (macOS)
//
//  Resource usage tab - Extracted from VaultAdminPanel.swift (Phase 6.16)
//  Displays hot slot memory usage and system resources
//

import SwiftUI

struct VaultResourcesTab: View {
    var hotSlotManager: HotSlotManager
    private let capabilityService = SystemCapabilityService.shared

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            // Hot slot resource usage
            VStack(alignment: .leading, spacing: 12) {
                Text("Active Models (Hot Slots)")
                    .font(.headline)

                if hotSlotManager.hotSlots.filter({ !$0.isEmpty }).isEmpty {
                    VaultAdminEmptyState(
                        icon: "memorychip",
                        title: "No Models Loaded",
                        message: "No models are currently loaded in hot slots"
                    )
                } else {
                    ForEach(hotSlotManager.hotSlots.filter { !$0.isEmpty }) { slot in
                        HStack(spacing: 12) {
                            // Slot badge
                            Text("\(slot.slotNumber)")
                                .font(.system(size: 12, weight: .bold))
                                .foregroundStyle(.white)
                                .frame(width: 24, height: 24)
                                .background(Circle().fill(Color.magnetarPrimary))

                            VStack(alignment: .leading, spacing: 4) {
                                Text(slot.modelName ?? "Unknown")
                                    .font(.system(size: 13, weight: .medium))

                                if let memoryGB = slot.memoryUsageGB {
                                    Text("\(String(format: "%.1f", memoryGB)) GB")
                                        .font(.system(size: 11))
                                        .foregroundStyle(.secondary)
                                }
                            }

                            Spacer()

                            if slot.isPinned {
                                Label("Pinned", systemImage: "pin.fill")
                                    .font(.system(size: 10))
                                    .foregroundStyle(.orange)
                            }
                        }
                        .padding(12)
                        .background(Color.surfaceSecondary.opacity(0.3))
                        .cornerRadius(8)
                    }
                }
            }

            Divider()

            // System resource state
            VStack(alignment: .leading, spacing: 12) {
                Text("System Resources")
                    .font(.headline)

                HStack(spacing: 16) {
                    // Memory
                    ResourceStat(
                        icon: "memorychip.fill",
                        label: "Total Memory",
                        value: String(format: "%.0f GB", capabilityService.totalMemoryGB),
                        color: .blue
                    )

                    // CPU Cores
                    ResourceStat(
                        icon: "cpu.fill",
                        label: "CPU Cores",
                        value: "\(capabilityService.cpuCores)",
                        color: .green
                    )

                    // Metal Support
                    ResourceStat(
                        icon: capabilityService.hasMetalSupport ? "checkmark.circle.fill" : "xmark.circle.fill",
                        label: "Metal GPU",
                        value: capabilityService.hasMetalSupport ? "Available" : "N/A",
                        color: capabilityService.hasMetalSupport ? .green : .secondary
                    )
                }

                // Hot Slots Memory Usage
                if hotSlotManager.hotSlots.contains(where: { !$0.isEmpty }) {
                    Divider()
                        .padding(.vertical, 8)

                    VStack(alignment: .leading, spacing: 8) {
                        Text("Hot Slots Memory Usage")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)

                        HStack(spacing: 12) {
                            ForEach(hotSlotManager.hotSlots) { slot in
                                if !slot.isEmpty, let memoryGB = slot.memoryUsageGB {
                                    VStack(spacing: 4) {
                                        Text("Slot \(slot.slotNumber)")
                                            .font(.system(size: 10))
                                            .foregroundStyle(.secondary)

                                        HStack(spacing: 4) {
                                            Image(systemName: "memorychip")
                                                .font(.system(size: 10))
                                            Text(String(format: "%.1f GB", memoryGB))
                                                .font(.system(size: 11, weight: .medium))
                                        }
                                        .foregroundStyle(Color.magnetarPrimary)
                                    }
                                    .padding(.horizontal, 8)
                                    .padding(.vertical, 6)
                                    .background(Color.surfaceSecondary.opacity(0.3))
                                    .cornerRadius(6)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
