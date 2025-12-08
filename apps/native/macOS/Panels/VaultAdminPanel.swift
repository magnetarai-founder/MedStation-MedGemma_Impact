//
//  VaultAdminPanel.swift
//  MagnetarStudio (macOS)
//
//  CRITICAL: Vault security admin panel for monitoring and emergency revocation
//  Top bar modal (between Control Center and Panic)
//
//  Part of Noah's Ark for the Digital Age - Protecting God's people
//  Foundation: Matthew 7:24-25 - Built on the rock, not sand
//

import SwiftUI

struct VaultAdminPanel: View {
    @StateObject private var permissionManager = VaultPermissionManager.shared
    @StateObject private var hotSlotManager = HotSlotManager.shared
    private let capabilityService = SystemCapabilityService.shared

    @State private var selectedTab: AdminTab = .permissions
    @State private var showRevokeAllConfirmation: Bool = false

    enum AdminTab: String, CaseIterable {
        case permissions = "Active Permissions"
        case audit = "Audit Log"
        case resources = "Resource Usage"
        case security = "Security Audit"
    }

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack(spacing: 16) {
                Image(systemName: "lock.shield.fill")
                    .font(.system(size: 28))
                    .foregroundStyle(LinearGradient.magnetarGradient)

                VStack(alignment: .leading, spacing: 4) {
                    Text("Vault Security Admin")
                        .font(.title2)
                        .fontWeight(.bold)

                    Text("\(permissionManager.activePermissions.count) active permissions • \(permissionManager.auditLog.count) audit entries")
                        .font(.subheadline)
                        .foregroundColor(.secondary)
                }

                Spacer()

                // Emergency revoke all button
                Button {
                    showRevokeAllConfirmation = true
                } label: {
                    HStack(spacing: 6) {
                        Image(systemName: "exclamationmark.triangle.fill")
                        Text("Revoke All")
                    }
                    .font(.system(size: 12, weight: .semibold))
                    .foregroundColor(.white)
                    .padding(.horizontal, 12)
                    .padding(.vertical, 8)
                    .background(Color.red)
                    .cornerRadius(6)
                }
                .buttonStyle(.plain)
                .help("Emergency: Revoke all file permissions immediately")
            }
            .padding(20)

            Divider()

            // Tab selector
            HStack(spacing: 0) {
                ForEach(AdminTab.allCases, id: \.self) { tab in
                    Button {
                        selectedTab = tab
                    } label: {
                        Text(tab.rawValue)
                            .font(.system(size: 13, weight: selectedTab == tab ? .semibold : .regular))
                            .foregroundColor(selectedTab == tab ? .magnetarPrimary : .secondary)
                            .padding(.horizontal, 16)
                            .padding(.vertical, 10)
                            .background(
                                selectedTab == tab ?
                                Color.magnetarPrimary.opacity(0.1) : Color.clear
                            )
                            .cornerRadius(6)
                    }
                    .buttonStyle(.plain)
                }

                Spacer()
            }
            .padding(.horizontal, 20)
            .padding(.vertical, 8)
            .background(Color.surfaceSecondary.opacity(0.2))

            Divider()

            // Tab content
            ScrollView {
                Group {
                    switch selectedTab {
                    case .permissions:
                        permissionsTab
                    case .audit:
                        auditLogTab
                    case .resources:
                        resourceUsageTab
                    case .security:
                        securityAuditTab
                    }
                }
                .padding(20)
            }
        }
        .frame(width: 800, height: 600)
        .alert("Revoke All Permissions?", isPresented: $showRevokeAllConfirmation) {
            Button("Cancel", role: .cancel) {}
            Button("Revoke All", role: .destructive) {
                permissionManager.revokeAllPermissions()
            }
        } message: {
            Text("This will immediately revoke ALL file permissions for ALL models. This action cannot be undone.")
        }
    }

    // MARK: - Permissions Tab

    private var permissionsTab: some View {
        VStack(alignment: .leading, spacing: 16) {
            if permissionManager.activePermissions.isEmpty {
                emptyState(
                    icon: "checkmark.shield.fill",
                    title: "No Active Permissions",
                    message: "No models currently have access to vault files"
                )
            } else {
                ForEach(permissionManager.activePermissions) { permission in
                    PermissionCard(
                        permission: permission,
                        onRevoke: {
                            permissionManager.revokePermission(permission)
                        }
                    )
                }
            }
        }
    }

    // MARK: - Audit Log Tab

    private var auditLogTab: some View {
        VStack(alignment: .leading, spacing: 12) {
            if permissionManager.auditLog.isEmpty {
                emptyState(
                    icon: "doc.text.fill",
                    title: "No Audit Entries",
                    message: "File access audit log is empty"
                )
            } else {
                ForEach(permissionManager.auditLog) { entry in
                    AuditEntryRow(entry: entry)
                }
            }
        }
    }

    // MARK: - Resource Usage Tab

    private var resourceUsageTab: some View {
        VStack(alignment: .leading, spacing: 20) {
            // Hot slot resource usage
            VStack(alignment: .leading, spacing: 12) {
                Text("Active Models (Hot Slots)")
                    .font(.headline)

                if hotSlotManager.hotSlots.filter({ !$0.isEmpty }).isEmpty {
                    emptyState(
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
                                .foregroundColor(.white)
                                .frame(width: 24, height: 24)
                                .background(Circle().fill(Color.magnetarPrimary))

                            VStack(alignment: .leading, spacing: 4) {
                                Text(slot.modelName ?? "Unknown")
                                    .font(.system(size: 13, weight: .medium))

                                if let memoryGB = slot.memoryUsageGB {
                                    Text("\(String(format: "%.1f", memoryGB)) GB")
                                        .font(.system(size: 11))
                                        .foregroundColor(.secondary)
                                }
                            }

                            Spacer()

                            if slot.isPinned {
                                Label("Pinned", systemImage: "pin.fill")
                                    .font(.system(size: 10))
                                    .foregroundColor(.orange)
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
                            .foregroundColor(.secondary)

                        HStack(spacing: 12) {
                            ForEach(hotSlotManager.hotSlots) { slot in
                                if !slot.isEmpty, let memoryGB = slot.memoryUsageGB {
                                    VStack(spacing: 4) {
                                        Text("Slot \(slot.slotNumber)")
                                            .font(.system(size: 10))
                                            .foregroundColor(.secondary)

                                        HStack(spacing: 4) {
                                            Image(systemName: "memorychip")
                                                .font(.system(size: 10))
                                            Text(String(format: "%.1f GB", memoryGB))
                                                .font(.system(size: 11, weight: .medium))
                                        }
                                        .foregroundColor(.magnetarPrimary)
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

    // MARK: - Security Audit Tab

    private var securityAuditTab: some View {
        VStack(alignment: .leading, spacing: 20) {
            // Permission summary
            VStack(alignment: .leading, spacing: 12) {
                Text("Permission Summary")
                    .font(.headline)

                HStack(spacing: 20) {
                    StatCard(
                        icon: "checkmark.shield.fill",
                        label: "Active",
                        value: "\(permissionManager.activePermissions.count)",
                        color: .green
                    )

                    StatCard(
                        icon: "clock.fill",
                        label: "Session-Scoped",
                        value: "\(permissionManager.activePermissions.filter { $0.expiresAt != nil }.count)",
                        color: .blue
                    )

                    StatCard(
                        icon: "exclamationmark.triangle.fill",
                        label: "Single-Use",
                        value: "\(permissionManager.activePermissions.filter { $0.expiresAt == nil }.count)",
                        color: .orange
                    )
                }
            }

            Divider()

            // Audit summary
            VStack(alignment: .leading, spacing: 12) {
                Text("Audit Summary (Last 24h)")
                    .font(.headline)

                let last24h = permissionManager.auditLog.filter {
                    $0.timestamp > Date().addingTimeInterval(-86400)
                }

                HStack(spacing: 20) {
                    StatCard(
                        icon: "checkmark.circle.fill",
                        label: "Granted",
                        value: "\(last24h.filter { $0.granted }.count)",
                        color: .green
                    )

                    StatCard(
                        icon: "xmark.circle.fill",
                        label: "Denied",
                        value: "\(last24h.filter { !$0.granted }.count)",
                        color: .red
                    )

                    StatCard(
                        icon: "doc.text.fill",
                        label: "Total",
                        value: "\(last24h.count)",
                        color: .secondary
                    )
                }
            }

            Divider()

            // Security recommendations
            VStack(alignment: .leading, spacing: 12) {
                Text("Security Recommendations")
                    .font(.headline)

                if permissionManager.activePermissions.count > 10 {
                    SecurityAlert(
                        icon: "exclamationmark.triangle.fill",
                        message: "High number of active permissions (\(permissionManager.activePermissions.count)). Consider revoking unused permissions.",
                        severity: .warning
                    )
                }

                if permissionManager.activePermissions.contains(where: { $0.vaultType == "real" }) {
                    SecurityAlert(
                        icon: "lock.shield.fill",
                        message: "Models have access to REAL vault files. Review permissions carefully.",
                        severity: .critical
                    )
                }

                if permissionManager.activePermissions.isEmpty {
                    SecurityAlert(
                        icon: "checkmark.shield.fill",
                        message: "No active permissions. Vault is fully secure.",
                        severity: .success
                    )
                }
            }
        }
    }

    // MARK: - Empty State

    private func emptyState(icon: String, title: String, message: String) -> some View {
        VStack(spacing: 16) {
            Image(systemName: icon)
                .font(.system(size: 48))
                .foregroundColor(.secondary)

            Text(title)
                .font(.headline)

            Text(message)
                .font(.subheadline)
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(40)
    }
}

// MARK: - Permission Card

struct PermissionCard: View {
    let permission: VaultFilePermission
    let onRevoke: () -> Void

    var body: some View {
        HStack(spacing: 16) {
            // File icon
            Image(systemName: "doc.fill")
                .font(.system(size: 24))
                .foregroundColor(.orange)

            // Info
            VStack(alignment: .leading, spacing: 6) {
                Text(permission.fileName)
                    .font(.system(size: 13, weight: .semibold))

                HStack(spacing: 12) {
                    Label(permission.modelName, systemImage: "cpu")
                    Label(permission.scope, systemImage: permission.expiresAt == nil ? "bolt.fill" : "clock.fill")
                    Label(permission.vaultType.capitalized, systemImage: "lock.fill")
                }
                .font(.system(size: 10))
                .foregroundColor(.secondary)
            }

            Spacer()

            // Revoke button
            Button {
                onRevoke()
            } label: {
                HStack(spacing: 4) {
                    Image(systemName: "xmark.circle.fill")
                    Text("Revoke")
                }
                .font(.system(size: 11, weight: .medium))
                .foregroundColor(.red)
            }
            .buttonStyle(.plain)
        }
        .padding(12)
        .background(Color.surfaceSecondary.opacity(0.3))
        .cornerRadius(8)
    }
}

// MARK: - Audit Entry Row

struct AuditEntryRow: View {
    let entry: FileAccessAudit

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: entry.granted ? "checkmark.circle.fill" : "xmark.circle.fill")
                .foregroundColor(entry.granted ? .green : .red)

            VStack(alignment: .leading, spacing: 4) {
                Text(entry.action)
                    .font(.system(size: 12, weight: .medium))

                Text("\(entry.fileName) • \(entry.modelId)")
                    .font(.system(size: 10))
                    .foregroundColor(.secondary)
            }

            Spacer()

            Text(entry.timestamp.formatted(date: .omitted, time: .shortened))
                .font(.system(size: 10))
                .foregroundColor(.secondary)
        }
        .padding(.vertical, 8)
    }
}

// MARK: - Stat Card

struct StatCard: View {
    let icon: String
    let label: String
    let value: String
    let color: Color

    var body: some View {
        VStack(spacing: 8) {
            Image(systemName: icon)
                .font(.system(size: 24))
                .foregroundColor(color)

            Text(value)
                .font(.system(size: 20, weight: .bold))

            Text(label)
                .font(.system(size: 10))
                .foregroundColor(.secondary)
                .textCase(.uppercase)
        }
        .frame(maxWidth: .infinity)
        .padding(16)
        .background(Color.surfaceSecondary.opacity(0.3))
        .cornerRadius(12)
    }
}

// MARK: - Resource Stat (Compact)

struct ResourceStat: View {
    let icon: String
    let label: String
    let value: String
    let color: Color

    var body: some View {
        VStack(spacing: 6) {
            Image(systemName: icon)
                .font(.system(size: 18))
                .foregroundColor(color)

            Text(value)
                .font(.system(size: 14, weight: .semibold))

            Text(label)
                .font(.system(size: 10))
                .foregroundColor(.secondary)
        }
        .frame(maxWidth: .infinity)
        .padding(12)
        .background(Color.surfaceSecondary.opacity(0.3))
        .cornerRadius(8)
    }
}

// MARK: - Security Alert

struct SecurityAlert: View {
    let icon: String
    let message: String
    let severity: Severity

    enum Severity {
        case success, warning, critical

        var color: Color {
            switch self {
            case .success: return .green
            case .warning: return .orange
            case .critical: return .red
            }
        }
    }

    var body: some View {
        HStack(spacing: 12) {
            Image(systemName: icon)
                .foregroundColor(severity.color)

            Text(message)
                .font(.system(size: 12))
                .foregroundColor(.primary)

            Spacer()
        }
        .padding(12)
        .background(severity.color.opacity(0.1))
        .cornerRadius(8)
    }
}

// MARK: - Preview

#Preview {
    VaultAdminPanel()
}
