//
//  VaultSecurityAuditTab.swift
//  MagnetarStudio (macOS)
//
//  Security audit tab - Extracted from VaultAdminPanel.swift (Phase 6.16)
//  Displays permission summaries and security recommendations
//

import SwiftUI

struct VaultSecurityAuditTab: View {
    var permissionManager: VaultPermissionManager

    var body: some View {
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
}
