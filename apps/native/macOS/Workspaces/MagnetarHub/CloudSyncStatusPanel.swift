//
//  CloudSyncStatusPanel.swift
//  MagnetarStudio (macOS)
//
//  Cloud sync status panel for MagnetarHub
//  Shows connection status, sync progress, and conflicts
//

import SwiftUI

struct CloudSyncStatusPanel: View {
    @Bindable var cloudManager: HubCloudManager

    @State private var showDevices = false
    @State private var showConflicts = false

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            // Header
            HStack {
                Image(systemName: "cloud")
                    .font(.title2)
                    .foregroundStyle(.secondary)

                Text("MagnetarCloud")
                    .font(.headline)

                Spacer()

                // Status indicator
                statusBadge
            }

            Divider()

            if cloudManager.isCloudAuthenticated {
                authenticatedContent
            } else {
                unauthenticatedContent
            }

            // Error message
            if let error = cloudManager.errorMessage {
                HStack {
                    Image(systemName: "exclamationmark.triangle.fill")
                        .foregroundStyle(.orange)
                    Text(error)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .padding()
        .background(.ultraThinMaterial)
        .clipShape(RoundedRectangle(cornerRadius: 12))
        .sheet(isPresented: $showDevices) {
            PairedDevicesSheet(devices: cloudManager.pairedDevices)
        }
        .sheet(isPresented: $showConflicts) {
            ConflictResolutionSheet(cloudManager: cloudManager)
        }
    }

    // MARK: - Status Badge

    private var statusBadge: some View {
        Group {
            if cloudManager.isSyncing {
                HStack(spacing: 4) {
                    ProgressView()
                        .scaleEffect(0.6)
                    Text("Syncing...")
                        .font(.caption)
                }
                .foregroundStyle(.blue)
            } else if let status = cloudManager.syncStatus {
                HStack(spacing: 4) {
                    Circle()
                        .fill(Color(nsColor: status.statusColor))
                        .frame(width: 8, height: 8)
                    Text(status.statusText)
                        .font(.caption)
                }
            } else if cloudManager.isCloudAuthenticated {
                HStack(spacing: 4) {
                    Circle()
                        .fill(.green)
                        .frame(width: 8, height: 8)
                    Text("Connected")
                        .font(.caption)
                }
            } else {
                HStack(spacing: 4) {
                    Circle()
                        .fill(.gray)
                        .frame(width: 8, height: 8)
                    Text("Disconnected")
                        .font(.caption)
                }
            }
        }
    }

    // MARK: - Authenticated Content

    private var authenticatedContent: some View {
        VStack(alignment: .leading, spacing: 10) {
            // User info
            if let username = cloudManager.cloudUsername {
                HStack {
                    Image(systemName: "person.circle.fill")
                        .foregroundStyle(.blue)
                    Text(username)
                        .font(.subheadline)
                    Spacer()
                }
            }

            // Sync status row
            HStack {
                VStack(alignment: .leading, spacing: 2) {
                    Text("Last Sync")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Text(cloudManager.syncStatus?.formattedLastSync ?? "Never")
                        .font(.subheadline)
                }

                Spacer()

                // Pending changes
                if cloudManager.pendingSyncChanges > 0 {
                    VStack(alignment: .trailing, spacing: 2) {
                        Text("Pending")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                        Text("\(cloudManager.pendingSyncChanges)")
                            .font(.subheadline)
                            .foregroundStyle(.orange)
                    }
                }

                // Conflicts
                if cloudManager.activeConflicts > 0 {
                    Button {
                        showConflicts = true
                    } label: {
                        HStack(spacing: 4) {
                            Image(systemName: "exclamationmark.triangle.fill")
                            Text("\(cloudManager.activeConflicts)")
                        }
                        .foregroundStyle(.orange)
                    }
                    .buttonStyle(.plain)
                }
            }

            // Paired devices
            if !cloudManager.pairedDevices.isEmpty {
                Button {
                    showDevices = true
                } label: {
                    HStack {
                        Image(systemName: "laptopcomputer.and.iphone")
                        Text("\(cloudManager.pairedDevices.count) device\(cloudManager.pairedDevices.count == 1 ? "" : "s")")
                            .font(.caption)
                    }
                    .foregroundStyle(.secondary)
                }
                .buttonStyle(.plain)
            }

            // Action buttons
            HStack(spacing: 8) {
                Button {
                    Task {
                        await cloudManager.triggerSync()
                    }
                } label: {
                    Label("Sync Now", systemImage: "arrow.triangle.2.circlepath")
                }
                .buttonStyle(.bordered)
                .disabled(cloudManager.isSyncing || cloudManager.isCloudActionInProgress)

                Spacer()

                Button {
                    Task {
                        await cloudManager.disconnectCloud()
                    }
                } label: {
                    Text("Disconnect")
                        .foregroundStyle(.red)
                }
                .buttonStyle(.plain)
                .disabled(cloudManager.isCloudActionInProgress)
            }
        }
    }

    // MARK: - Unauthenticated Content

    private var unauthenticatedContent: some View {
        VStack(spacing: 12) {
            Text("Connect to sync your vault, workflows, and settings across devices.")
                .font(.caption)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)

            Button {
                Task {
                    await cloudManager.connectCloud()
                }
            } label: {
                HStack {
                    Image(systemName: "link.circle.fill")
                    Text("Connect to MagnetarCloud")
                }
            }
            .buttonStyle(.borderedProminent)
            .disabled(cloudManager.isCloudActionInProgress)
        }
        .frame(maxWidth: .infinity)
        .padding(.vertical, 8)
    }
}

// MARK: - Paired Devices Sheet

struct PairedDevicesSheet: View {
    let devices: [CloudDeviceInfo]
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Paired Devices")
                    .font(.headline)
                Spacer()
                Button("Done") { dismiss() }
                    .buttonStyle(.plain)
            }
            .padding()

            Divider()

            // Device list
            List(devices) { device in
                HStack {
                    Image(systemName: deviceIcon(for: device.devicePlatform))
                        .foregroundStyle(.blue)
                        .frame(width: 24)

                    VStack(alignment: .leading, spacing: 2) {
                        Text(device.deviceName ?? "Unknown Device")
                            .font(.subheadline)

                        if let lastSync = device.lastSyncAt {
                            Text("Last sync: \(formatDate(lastSync))")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }

                    Spacer()

                    if device.isActive {
                        Text("Active")
                            .font(.caption)
                            .padding(.horizontal, 6)
                            .padding(.vertical, 2)
                            .background(.green.opacity(0.2))
                            .foregroundStyle(.green)
                            .clipShape(Capsule())
                    }
                }
                .padding(.vertical, 4)
            }
        }
        .frame(width: 400, height: 300)
    }

    private func deviceIcon(for platform: String?) -> String {
        switch platform?.lowercased() {
        case "macos": return "laptopcomputer"
        case "ios": return "iphone"
        case "ipados": return "ipad"
        default: return "desktopcomputer"
        }
    }

    private func formatDate(_ isoString: String) -> String {
        guard let date = ISO8601DateFormatter().date(from: isoString) else {
            return isoString
        }
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: date, relativeTo: Date())
    }
}

// MARK: - Conflict Resolution Sheet

struct ConflictResolutionSheet: View {
    @Bindable var cloudManager: HubCloudManager
    @Environment(\.dismiss) private var dismiss

    @State private var conflicts: [ConflictInfo] = []
    @State private var isLoading = true

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Image(systemName: "exclamationmark.triangle.fill")
                    .foregroundStyle(.orange)
                Text("Sync Conflicts")
                    .font(.headline)
                Spacer()
                Button("Done") { dismiss() }
                    .buttonStyle(.plain)
            }
            .padding()

            Divider()

            if isLoading {
                Spacer()
                ProgressView("Loading conflicts...")
                Spacer()
            } else if conflicts.isEmpty {
                Spacer()
                VStack(spacing: 8) {
                    Image(systemName: "checkmark.circle.fill")
                        .font(.largeTitle)
                        .foregroundStyle(.green)
                    Text("No conflicts")
                        .font(.headline)
                    Text("All your data is synced successfully.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
                Spacer()
            } else {
                List(conflicts, id: \.conflictId) { conflict in
                    ConflictRow(conflict: conflict) { resolution in
                        await resolveConflict(conflict, with: resolution)
                    }
                }
            }
        }
        .frame(width: 500, height: 400)
        .task {
            await loadConflicts()
        }
    }

    private func loadConflicts() async {
        isLoading = true
        do {
            conflicts = try await SyncService.shared.getConflicts()
        } catch {
            print("Failed to load conflicts: \(error)")
        }
        isLoading = false
    }

    private func resolveConflict(_ conflict: ConflictInfo, with resolution: ConflictResolution) async {
        do {
            try await SyncService.shared.resolveConflict(
                conflictId: conflict.conflictId,
                resolution: resolution
            )
            // Remove from local list
            conflicts.removeAll { $0.conflictId == conflict.conflictId }
            await cloudManager.refreshSyncStatus()
        } catch {
            print("Failed to resolve conflict: \(error)")
        }
    }
}

// MARK: - Conflict Row

struct ConflictRow: View {
    let conflict: ConflictInfo
    let onResolve: (ConflictResolution) async -> Void

    @State private var isResolving = false

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Image(systemName: resourceIcon)
                    .foregroundStyle(.orange)
                Text(conflict.resourceType.capitalized)
                    .font(.subheadline.bold())
                Spacer()
                Text(formatDate(conflict.detectedAt))
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Text("Resource ID: \(conflict.resourceId)")
                .font(.caption)
                .foregroundStyle(.secondary)

            HStack(spacing: 8) {
                Button("Keep Local") {
                    Task {
                        isResolving = true
                        await onResolve(.localWins)
                        isResolving = false
                    }
                }
                .buttonStyle(.bordered)
                .disabled(isResolving)

                Button("Keep Remote") {
                    Task {
                        isResolving = true
                        await onResolve(.remoteWins)
                        isResolving = false
                    }
                }
                .buttonStyle(.bordered)
                .disabled(isResolving)

                if isResolving {
                    ProgressView()
                        .scaleEffect(0.6)
                }
            }
        }
        .padding(.vertical, 4)
    }

    private var resourceIcon: String {
        switch conflict.resourceType.lowercased() {
        case "vault": return "lock.shield"
        case "workflow": return "gearshape.2"
        case "team": return "person.3"
        default: return "doc"
        }
    }

    private func formatDate(_ isoString: String) -> String {
        guard let date = ISO8601DateFormatter().date(from: isoString) else {
            return isoString
        }
        let formatter = RelativeDateTimeFormatter()
        formatter.unitsStyle = .abbreviated
        return formatter.localizedString(for: date, relativeTo: Date())
    }
}

// MARK: - Preview

#Preview {
    CloudSyncStatusPanel(cloudManager: HubCloudManager())
        .frame(width: 300)
        .padding()
}
