//
//  WorkspaceSettingsWindow.swift
//  MagnetarStudio (macOS)
//
//  Separate utility window for detailed workspace/connection settings
//  Opened from the popover in WorkspaceView
//

import SwiftUI

struct WorkspaceSettingsWindow: View {
    @AppStorage("workspace.teamEnabled") private var teamEnabled = false
    @AppStorage("workspace.connectionMode") private var connectionMode = "cloud"

    @State private var isConnecting = false
    @State private var reconnectTask: Task<Void, Never>?
    @State private var showDiagnostics = false

    var body: some View {
        VStack(spacing: 0) {
            // Header
            header

            Divider()

            // Content
            ScrollView {
                VStack(spacing: 20) {
                    teamModeSection
                    connectionSection
                    if teamEnabled {
                        teamManagementSection
                    }
                    advancedSection
                }
                .padding(20)
            }
        }
        .frame(width: 400, height: 500)
        .background(Color(nsColor: .windowBackgroundColor))
    }

    // MARK: - Header

    private var header: some View {
        HStack {
            VStack(alignment: .leading, spacing: 2) {
                Text("Workspace Settings")
                    .font(.headline)
                Text("Configure team and connection options")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
            Spacer()
        }
        .padding(16)
        .background(Color.gray.opacity(0.05))
    }

    // MARK: - Team Mode Section

    private var teamModeSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("TEAM MODE")
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(.secondary)

            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text("Enable Team Features")
                        .font(.system(size: 13, weight: .medium))
                    Text("Access channels, direct messages, and collaborative documents")
                        .font(.system(size: 11))
                        .foregroundStyle(.secondary)
                }
                Spacer()
                Toggle("", isOn: $teamEnabled)
                    .toggleStyle(.switch)
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.gray.opacity(0.08))
            )
        }
    }

    // MARK: - Connection Section

    private var connectionSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("CONNECTION")
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(.secondary)

            VStack(spacing: 8) {
                connectionOption(
                    title: "Cloud",
                    subtitle: "Connect through MagnetarCloud servers",
                    icon: "cloud",
                    value: "cloud"
                )

                connectionOption(
                    title: "WiFi Aware",
                    subtitle: "Direct device-to-device on same network (macOS 26+)",
                    icon: "wifi",
                    value: "wifi-aware"
                )

                connectionOption(
                    title: "Peer-to-Peer",
                    subtitle: "Direct connection without servers",
                    icon: "point.3.connected.trianglepath.dotted",
                    value: "p2p"
                )

                connectionOption(
                    title: "LAN Only",
                    subtitle: "Local network discovery only",
                    icon: "network",
                    value: "lan"
                )
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.gray.opacity(0.08))
            )

            // Connection status
            HStack(spacing: 8) {
                Circle()
                    .fill(teamEnabled ? Color.green : Color.gray)
                    .frame(width: 8, height: 8)
                Text(teamEnabled ? "Connected via \(connectionMode.capitalized)" : "Not connected")
                    .font(.system(size: 12))
                    .foregroundStyle(.secondary)
                Spacer()
                if teamEnabled {
                    Button("Reconnect") {
                        reconnect()
                    }
                    .buttonStyle(.bordered)
                    .controlSize(.small)
                }
            }
        }
    }

    private func connectionOption(title: String, subtitle: String, icon: String, value: String) -> some View {
        Button {
            connectionMode = value
        } label: {
            HStack(spacing: 12) {
                Image(systemName: icon)
                    .font(.system(size: 16))
                    .foregroundStyle(connectionMode == value ? Color.accentColor : .secondary)
                    .frame(width: 24)

                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(.primary)
                    Text(subtitle)
                        .font(.system(size: 10))
                        .foregroundStyle(.secondary)
                }

                Spacer()

                if connectionMode == value {
                    Image(systemName: "checkmark.circle.fill")
                        .foregroundStyle(Color.accentColor)
                }
            }
            .padding(.vertical, 8)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }

    // MARK: - Team Management Section

    private var teamManagementSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("TEAM")
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(.secondary)

            VStack(spacing: 8) {
                settingsRow(icon: "person.2", title: "Create Team", subtitle: "Start a new team workspace") {
                    // Create team action
                }

                settingsRow(icon: "person.badge.plus", title: "Join Team", subtitle: "Join an existing team") {
                    // Join team action
                }

                settingsRow(icon: "person.crop.circle.badge.questionmark", title: "Find People", subtitle: "Search for people to message") {
                    // Find people action
                }
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.gray.opacity(0.08))
            )
        }
    }

    // MARK: - Advanced Section

    private var advancedSection: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("ADVANCED")
                .font(.system(size: 11, weight: .semibold))
                .foregroundStyle(.secondary)

            VStack(spacing: 8) {
                settingsRow(icon: "waveform.path.ecg", title: "Diagnostics", subtitle: "View connection diagnostics") {
                    showDiagnostics = true
                }

                settingsRow(icon: "arrow.triangle.2.circlepath", title: "Sync Now", subtitle: "Force sync all data") {
                    // Sync action
                }

                settingsRow(icon: "trash", title: "Clear Cache", subtitle: "Remove cached team data") {
                    // Clear cache action
                }
            }
            .padding(12)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(Color.gray.opacity(0.08))
            )
        }
        .sheet(isPresented: $showDiagnostics) {
            DiagnosticsSheet()
        }
    }

    private func settingsRow(icon: String, title: String, subtitle: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            HStack(spacing: 12) {
                Image(systemName: icon)
                    .font(.system(size: 14))
                    .foregroundStyle(.secondary)
                    .frame(width: 24)

                VStack(alignment: .leading, spacing: 2) {
                    Text(title)
                        .font(.system(size: 13, weight: .medium))
                        .foregroundStyle(.primary)
                    Text(subtitle)
                        .font(.system(size: 10))
                        .foregroundStyle(.secondary)
                }

                Spacer()

                Image(systemName: "chevron.right")
                    .font(.system(size: 11))
                    .foregroundStyle(.secondary.opacity(0.5))
            }
            .padding(.vertical, 6)
            .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
    }

    // MARK: - Actions

    private func reconnect() {
        isConnecting = true
        reconnectTask?.cancel()
        reconnectTask = Task {
            try? await Task.sleep(for: .seconds(1))
            guard !Task.isCancelled else { return }
            isConnecting = false
        }
    }
}

// MARK: - Diagnostics Sheet

struct DiagnosticsSheet: View {
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Text("Connection Diagnostics")
                    .font(.headline)
                Spacer()
                Button("Done") {
                    dismiss()
                }
                .buttonStyle(.borderedProminent)
                .controlSize(.small)
            }
            .padding(16)

            Divider()

            // Content
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    diagnosticRow(label: "Cloud Server", value: "Connected", status: .good)
                    diagnosticRow(label: "WiFi Aware", value: "Available", status: .good)
                    diagnosticRow(label: "P2P Network", value: "2 peers", status: .good)
                    diagnosticRow(label: "LAN Discovery", value: "Scanning...", status: .neutral)
                    diagnosticRow(label: "Latency", value: "42ms", status: .good)
                    diagnosticRow(label: "Last Sync", value: "Just now", status: .good)
                }
                .padding(16)
            }
        }
        .frame(width: 350, height: 300)
    }

    private enum DiagnosticStatus {
        case good, warning, error, neutral

        var color: Color {
            switch self {
            case .good: return .green
            case .warning: return .orange
            case .error: return .red
            case .neutral: return .gray
            }
        }
    }

    private func diagnosticRow(label: String, value: String, status: DiagnosticStatus) -> some View {
        HStack {
            Circle()
                .fill(status.color)
                .frame(width: 8, height: 8)
            Text(label)
                .font(.system(size: 13))
            Spacer()
            Text(value)
                .font(.system(size: 13))
                .foregroundStyle(.secondary)
        }
    }
}

// MARK: - Preview

#Preview {
    WorkspaceSettingsWindow()
}
