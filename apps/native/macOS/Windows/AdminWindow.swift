//
//  AdminWindow.swift
//  MagnetarStudio (macOS)
//
//  Founder Admin pop-out window for user management, device overview, and audit logs.
//  Accessible from the + button in the header (role-gated to founder/admin).
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "AdminWindow")

struct AdminWindow: View {
    @State private var selectedTab: AdminTab = .users
    @State private var users: [AdminUser] = []
    @State private var deviceOverview: DeviceOverview?
    @State private var auditLogs: [AuditLogEntry] = []
    @State private var isLoading = false
    @State private var error: String?
    @State private var auditSearchText = ""

    private let adminService = AdminService.shared

    var body: some View {
        VStack(spacing: 0) {
            adminHeader
            Divider()
            tabBar
            Divider()
            tabContent
        }
        .frame(minWidth: 550, minHeight: 400)
        .background(Color(NSColor.windowBackgroundColor))
        .task {
            await loadUsers()
        }
    }

    // MARK: - Header

    private var adminHeader: some View {
        HStack(spacing: 12) {
            Image(systemName: "shield.lefthalf.filled")
                .font(.system(size: 18))
                .foregroundStyle(LinearGradient.magnetarGradient)

            Text("Founder Admin")
                .font(.system(size: 16, weight: .semibold))

            Spacer()

            if isLoading {
                ProgressView()
                    .scaleEffect(0.7)
            }

            Button {
                Task { await refreshCurrentTab() }
            } label: {
                Image(systemName: "arrow.clockwise")
                    .font(.system(size: 13))
                    .foregroundStyle(.secondary)
            }
            .buttonStyle(.plain)
            .disabled(isLoading)
            .help("Refresh")
            .accessibilityLabel("Refresh current tab")
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(Color.gray.opacity(0.03))
    }

    // MARK: - Tab Bar

    private var tabBar: some View {
        HStack(spacing: 0) {
            ForEach(AdminTab.allCases, id: \.self) { tab in
                AdminTabButton(
                    tab: tab,
                    isSelected: selectedTab == tab,
                    onSelect: {
                        selectedTab = tab
                        Task { await loadTabData(tab) }
                    }
                )
            }
            Spacer()
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
        .background(Color.gray.opacity(0.03))
    }

    // MARK: - Tab Content

    @ViewBuilder
    private var tabContent: some View {
        if let error {
            adminErrorView(error)
        } else {
            switch selectedTab {
            case .users:
                usersTab
            case .overview:
                overviewTab
            case .auditLog:
                auditLogTab
            }
        }
    }

    // MARK: - Users Tab

    private var usersTab: some View {
        ScrollView {
            LazyVStack(spacing: 1) {
                if users.isEmpty && !isLoading {
                    emptyState(icon: "person.2", message: "No users found")
                } else {
                    ForEach(users) { user in
                        AdminUserRow(
                            user: user,
                            onResetPassword: {
                                Task { await resetPassword(user) }
                            },
                            onUnlock: {
                                Task { await unlockAccount(user) }
                            }
                        )
                    }
                }
            }
            .padding(12)
        }
    }

    // MARK: - Overview Tab

    private var overviewTab: some View {
        ScrollView {
            if let overview = deviceOverview {
                LazyVGrid(columns: [
                    GridItem(.flexible()),
                    GridItem(.flexible())
                ], spacing: 12) {
                    AdminStatCard(
                        title: "Total Users",
                        value: "\(overview.totalUsers ?? 0)",
                        icon: "person.2.fill",
                        color: .blue
                    )
                    AdminStatCard(
                        title: "Chat Sessions",
                        value: "\(overview.totalChatSessions ?? 0)",
                        icon: "bubble.left.and.bubble.right.fill",
                        color: .purple
                    )
                    AdminStatCard(
                        title: "Documents",
                        value: "\(overview.totalDocuments ?? 0)",
                        icon: "doc.fill",
                        color: .orange
                    )
                    AdminStatCard(
                        title: "Data Size",
                        value: formatDataSize(overview.dataDirSizeMb),
                        icon: "internaldrive.fill",
                        color: .green
                    )
                    AdminStatCard(
                        title: "Workflows",
                        value: "\(overview.totalWorkflows ?? 0)",
                        icon: "gearshape.2.fill",
                        color: .indigo
                    )
                    AdminStatCard(
                        title: "Work Items",
                        value: "\(overview.totalWorkItems ?? 0)",
                        icon: "checklist",
                        color: .teal
                    )
                }
                .padding(16)
            } else if !isLoading {
                emptyState(icon: "chart.bar", message: "No overview data")
            }
        }
    }

    // MARK: - Audit Log Tab

    private var auditLogTab: some View {
        VStack(spacing: 0) {
            // Search bar
            HStack(spacing: 8) {
                Image(systemName: "magnifyingglass")
                    .font(.system(size: 12))
                    .foregroundStyle(.tertiary)
                TextField("Filter by action...", text: $auditSearchText)
                    .textFieldStyle(.plain)
                    .font(.system(size: 13))
                if !auditSearchText.isEmpty {
                    Button {
                        auditSearchText = ""
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .font(.system(size: 12))
                            .foregroundStyle(.tertiary)
                    }
                    .buttonStyle(.plain)
                    .accessibilityLabel("Clear search")
                }
            }
            .padding(.horizontal, 12)
            .padding(.vertical, 8)
            .background(Color.gray.opacity(0.05))

            Divider()

            ScrollView {
                LazyVStack(spacing: 1) {
                    if filteredAuditLogs.isEmpty && !isLoading {
                        emptyState(icon: "list.clipboard", message: "No audit logs")
                    } else {
                        ForEach(filteredAuditLogs) { entry in
                            AuditLogRow(entry: entry)
                        }
                    }
                }
                .padding(12)
            }
        }
    }

    private var filteredAuditLogs: [AuditLogEntry] {
        if auditSearchText.isEmpty { return auditLogs }
        return auditLogs.filter {
            $0.action.localizedCaseInsensitiveContains(auditSearchText) ||
            $0.resource.localizedCaseInsensitiveContains(auditSearchText)
        }
    }

    // MARK: - Shared Components

    private func emptyState(icon: String, message: String) -> some View {
        VStack(spacing: 12) {
            Image(systemName: icon)
                .font(.system(size: 32))
                .foregroundStyle(.tertiary)
            Text(message)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, minHeight: 200)
    }

    private func adminErrorView(_ message: String) -> some View {
        VStack(spacing: 12) {
            Image(systemName: "exclamationmark.triangle")
                .font(.system(size: 32))
                .foregroundStyle(.orange)
            Text(message)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
            Button("Retry") {
                Task { await refreshCurrentTab() }
            }
            .buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding()
    }

    // MARK: - Data Loading

    private func loadTabData(_ tab: AdminTab) async {
        switch tab {
        case .users:
            if users.isEmpty { await loadUsers() }
        case .overview:
            if deviceOverview == nil { await loadOverview() }
        case .auditLog:
            if auditLogs.isEmpty { await loadAuditLogs() }
        }
    }

    private func refreshCurrentTab() async {
        switch selectedTab {
        case .users: await loadUsers()
        case .overview: await loadOverview()
        case .auditLog: await loadAuditLogs()
        }
    }

    private func loadUsers() async {
        isLoading = true
        error = nil
        do {
            let response = try await adminService.fetchUsers()
            users = response.users
            logger.info("Loaded \(response.total) users")
        } catch {
            logger.error("Failed to load users: \(error)")
            self.error = "Failed to load users: \(error.localizedDescription)"
        }
        isLoading = false
    }

    private func loadOverview() async {
        isLoading = true
        error = nil
        do {
            let response = try await adminService.fetchDeviceOverview()
            deviceOverview = response.deviceOverview
        } catch {
            logger.error("Failed to load overview: \(error)")
            self.error = "Failed to load overview: \(error.localizedDescription)"
        }
        isLoading = false
    }

    private func loadAuditLogs() async {
        isLoading = true
        error = nil
        do {
            let response = try await adminService.fetchAuditLogs()
            auditLogs = response.logs
        } catch {
            logger.error("Failed to load audit logs: \(error)")
            self.error = "Failed to load audit logs: \(error.localizedDescription)"
        }
        isLoading = false
    }

    // MARK: - Actions

    private func resetPassword(_ user: AdminUser) async {
        do {
            try await adminService.resetPassword(userId: user.userId)
            logger.info("Password reset for \(user.username)")
            // Refresh user list to reflect changes
            await loadUsers()
        } catch {
            logger.error("Password reset failed for \(user.username): \(error)")
            self.error = "Password reset failed: \(error.localizedDescription)"
        }
    }

    private func unlockAccount(_ user: AdminUser) async {
        do {
            try await adminService.unlockAccount(userId: user.userId)
            logger.info("Account unlocked for \(user.username)")
            await loadUsers()
        } catch {
            logger.error("Account unlock failed for \(user.username): \(error)")
            self.error = "Account unlock failed: \(error.localizedDescription)"
        }
    }

    // MARK: - Helpers

    private func formatDataSize(_ mb: Double?) -> String {
        guard let mb else { return "—" }
        if mb >= 1024 {
            return String(format: "%.1f GB", mb / 1024)
        }
        return String(format: "%.0f MB", mb)
    }
}

// MARK: - Admin Tab

enum AdminTab: String, CaseIterable {
    case users = "Users"
    case overview = "Overview"
    case auditLog = "Audit Log"

    var icon: String {
        switch self {
        case .users: return "person.2"
        case .overview: return "chart.bar"
        case .auditLog: return "list.clipboard"
        }
    }
}

// MARK: - Tab Button

private struct AdminTabButton: View {
    let tab: AdminTab
    let isSelected: Bool
    let onSelect: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: onSelect) {
            HStack(spacing: 6) {
                Image(systemName: tab.icon)
                    .font(.system(size: 11))
                Text(tab.rawValue)
                    .font(.system(size: 12, weight: isSelected ? .semibold : .regular))
            }
            .foregroundStyle(isSelected ? Color.magnetarPrimary : .secondary)
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: 6)
                    .fill(isSelected ? Color.magnetarPrimary.opacity(0.1) : (isHovered ? Color.gray.opacity(0.08) : Color.clear))
            )
        }
        .buttonStyle(.plain)
        .onHover { hovering in isHovered = hovering }
    }
}

// MARK: - User Row

private struct AdminUserRow: View {
    let user: AdminUser
    let onResetPassword: () -> Void
    let onUnlock: () -> Void

    @State private var isHovered = false

    var body: some View {
        HStack(spacing: 12) {
            // Status indicator
            Circle()
                .fill(user.isRecentlyActive ? Color.green : (user.isActive ? Color.gray.opacity(0.4) : Color.red.opacity(0.4)))
                .frame(width: 8, height: 8)

            // Username
            Text(user.username)
                .font(.system(size: 13, weight: .medium))
                .lineLimit(1)

            // Role badge
            Text(user.userRole?.displayName ?? user.role ?? "member")
                .font(.system(size: 10, weight: .semibold))
                .foregroundStyle(roleBadgeColor)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(
                    RoundedRectangle(cornerRadius: 4)
                        .fill(roleBadgeColor.opacity(0.12))
                )

            Spacer()

            // Last login
            Text(user.lastLoginRelative)
                .font(.system(size: 11))
                .foregroundStyle(.tertiary)

            // Device ID (truncated)
            Text(String(user.deviceId.prefix(8)))
                .font(.system(size: 10, design: .monospaced))
                .foregroundStyle(.quaternary)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 8)
        .background(
            RoundedRectangle(cornerRadius: 6)
                .fill(isHovered ? Color.gray.opacity(0.06) : Color.clear)
        )
        .onHover { hovering in isHovered = hovering }
        .contextMenu {
            Button {
                onResetPassword()
            } label: {
                Label("Reset Password", systemImage: "key.fill")
            }

            Button {
                onUnlock()
            } label: {
                Label("Unlock Account", systemImage: "lock.open.fill")
            }
        }
    }

    private var roleBadgeColor: Color {
        switch user.userRole {
        case .founderRights: return .orange
        case .superAdmin: return .red
        case .admin: return .purple
        case .member: return .blue
        case .none: return .gray
        }
    }
}

// MARK: - Stat Card

private struct AdminStatCard: View {
    let title: String
    let value: String
    let icon: String
    let color: Color

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                Image(systemName: icon)
                    .font(.system(size: 14))
                    .foregroundStyle(color)
                Text(title)
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary)
            }
            Text(value)
                .font(.system(size: 22, weight: .bold, design: .rounded))
                .foregroundStyle(.primary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(16)
        .background(
            RoundedRectangle(cornerRadius: 10)
                .fill(Color.gray.opacity(0.05))
                .overlay(
                    RoundedRectangle(cornerRadius: 10)
                        .strokeBorder(Color.gray.opacity(0.1), lineWidth: 1)
                )
        )
    }
}

// MARK: - Audit Log Row

private struct AuditLogRow: View {
    let entry: AuditLogEntry

    var body: some View {
        HStack(spacing: 10) {
            // Action badge
            Text(entry.action)
                .font(.system(size: 10, weight: .semibold, design: .monospaced))
                .foregroundStyle(actionColor)
                .padding(.horizontal, 6)
                .padding(.vertical, 2)
                .background(
                    RoundedRectangle(cornerRadius: 4)
                        .fill(actionColor.opacity(0.1))
                )

            // Resource
            VStack(alignment: .leading, spacing: 2) {
                Text(entry.resource)
                    .font(.system(size: 12))
                    .lineLimit(1)
                if let details = entry.details, !details.isEmpty {
                    Text(details)
                        .font(.system(size: 10))
                        .foregroundStyle(.tertiary)
                        .lineLimit(1)
                }
            }

            Spacer()

            // Timestamp
            Text(formatTimestamp(entry.timestamp))
                .font(.system(size: 10))
                .foregroundStyle(.tertiary)
        }
        .padding(.horizontal, 12)
        .padding(.vertical, 6)
    }

    private var actionColor: Color {
        let action = entry.action.lowercased()
        if action.contains("delete") || action.contains("reset") || action.contains("uninstall") {
            return .red
        }
        if action.contains("create") || action.contains("unlock") {
            return .green
        }
        if action.contains("view") || action.contains("list") {
            return .blue
        }
        return .secondary
    }

    private func formatTimestamp(_ iso: String) -> String {
        let formatter = ISO8601DateFormatter()
        formatter.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        let date = formatter.date(from: iso) ?? {
            formatter.formatOptions = [.withInternetDateTime]
            return formatter.date(from: iso)
        }()
        guard let date else { return iso }

        let display = DateFormatter()
        display.dateStyle = .short
        display.timeStyle = .short
        return display.string(from: date)
    }
}

// MARK: - Preview

#Preview {
    AdminWindow()
        .frame(width: 600, height: 500)
}
