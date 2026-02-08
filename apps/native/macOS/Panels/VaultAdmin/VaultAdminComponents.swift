//
//  VaultAdminComponents.swift
//  MagnetarStudio (macOS)
//
//  Vault admin UI components - Extracted from VaultAdminPanel.swift (Phase 6.16)
//  Reusable components for permission cards, stats, and alerts
//

import SwiftUI

// MARK: - Permission Card

struct PermissionCard: View {
    let permission: VaultFilePermission
    let onRevoke: () -> Void

    var body: some View {
        HStack(spacing: 16) {
            // File icon
            Image(systemName: "doc.fill")
                .font(.system(size: 24))
                .foregroundStyle(.orange)

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
                .foregroundStyle(.secondary)
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
                .foregroundStyle(.red)
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
                .foregroundStyle(entry.granted ? .green : .red)

            VStack(alignment: .leading, spacing: 4) {
                Text(entry.action)
                    .font(.system(size: 12, weight: .medium))

                Text("\(entry.fileName) • \(entry.modelId)")
                    .font(.system(size: 10))
                    .foregroundStyle(.secondary)
            }

            Spacer()

            Text(entry.timestamp.formatted(date: .omitted, time: .shortened))
                .font(.system(size: 10))
                .foregroundStyle(.secondary)
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
                .foregroundStyle(color)

            Text(value)
                .font(.system(size: 20, weight: .bold))

            Text(label)
                .font(.system(size: 10))
                .foregroundStyle(.secondary)
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
                .foregroundStyle(color)

            Text(value)
                .font(.system(size: 14, weight: .semibold))

            Text(label)
                .font(.system(size: 10))
                .foregroundStyle(.secondary)
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
                .foregroundStyle(severity.color)

            Text(message)
                .font(.system(size: 12))
                .foregroundStyle(.primary)

            Spacer()
        }
        .padding(12)
        .background(severity.color.opacity(0.1))
        .cornerRadius(8)
    }
}

// MARK: - Empty State

struct VaultAdminEmptyState: View {
    let icon: String
    let title: String
    let message: String

    var body: some View {
        VStack(spacing: 16) {
            Image(systemName: icon)
                .font(.system(size: 48))
                .foregroundStyle(.secondary)

            Text(title)
                .font(.headline)

            Text(message)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(40)
    }
}
