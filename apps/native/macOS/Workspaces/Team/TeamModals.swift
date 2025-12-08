//
//  TeamModals.swift
//  MagnetarStudio (macOS)
//
//  Team workspace modal dialogs - Extracted from TeamWorkspace.swift
//

import SwiftUI

// MARK: - Placeholder Modals

struct DiagnosticsPanel: View {
    @Environment(\.dismiss) var dismiss
    @State private var isLoading: Bool = false
    @State private var errorMessage: String? = nil
    @State private var diagnostics: DiagnosticsStatus? = nil

    private let teamService = TeamService.shared

    var body: some View {
        VStack(spacing: 20) {
            // Header
            HStack {
                Text("Network Diagnostics")
                    .font(.title2.weight(.semibold))

                Spacer()

                Button(action: { Task { await loadDiagnostics() } }) {
                    HStack(spacing: 4) {
                        Image(systemName: "arrow.clockwise")
                        Text("Retry")
                    }
                }
                .disabled(isLoading)
            }

            if isLoading {
                VStack(spacing: 12) {
                    ProgressView()
                    Text("Loading diagnostics...")
                        .font(.caption)
                        .foregroundColor(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else if let diag = diagnostics {
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        // Overall Status
                        HStack {
                            Image(systemName: diag.status == "ok" ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                                .foregroundColor(diag.status == "ok" ? .green : .orange)
                            Text("Status: \(diag.status.uppercased())")
                                .font(.system(size: 14, weight: .medium))
                        }

                        Divider()

                        // Network Status
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Network")
                                .font(.system(size: 13, weight: .semibold))

                            statusRow("Connected", value: diag.network.connected ? "Yes" : "No", status: diag.network.connected)

                            if let latency = diag.network.latency {
                                statusRow("Latency", value: "\(latency)ms", status: latency < 100)
                            }

                            if let bandwidth = diag.network.bandwidth {
                                statusRow("Bandwidth", value: bandwidth, status: true)
                            }
                        }

                        Divider()

                        // Database Status
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Database")
                                .font(.system(size: 13, weight: .semibold))

                            statusRow("Connected", value: diag.database.connected ? "Yes" : "No", status: diag.database.connected)

                            if let queryTime = diag.database.queryTime {
                                statusRow("Query Time", value: "\(queryTime)ms", status: queryTime < 100)
                            }
                        }

                        Divider()

                        // Services
                        if !diag.services.isEmpty {
                            VStack(alignment: .leading, spacing: 8) {
                                Text("Services")
                                    .font(.system(size: 13, weight: .semibold))

                                ForEach(diag.services, id: \.name) { service in
                                    HStack {
                                        Image(systemName: service.status == "running" ? "checkmark.circle.fill" : "xmark.circle.fill")
                                            .foregroundColor(service.status == "running" ? .green : .red)
                                            .font(.system(size: 12))

                                        Text(service.name)
                                            .font(.system(size: 12))

                                        Spacer()

                                        if let uptime = service.uptime {
                                            Text(uptime)
                                                .font(.caption)
                                                .foregroundColor(.secondary)
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            } else if let error = errorMessage {
                VStack(spacing: 12) {
                    Image(systemName: "exclamationmark.triangle")
                        .font(.largeTitle)
                        .foregroundColor(.orange)

                    Text(error)
                        .font(.caption)
                        .foregroundColor(.red)
                        .multilineTextAlignment(.center)

                    Button("Retry") {
                        Task { await loadDiagnostics() }
                    }
                    .buttonStyle(.borderedProminent)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            }

            // Close button
            Button("Close") {
                dismiss()
            }
            .keyboardShortcut(.escape)
        }
        .frame(width: 600, height: 400)
        .padding(24)
        .onAppear {
            Task { await loadDiagnostics() }
        }
    }

    @ViewBuilder
    private func statusRow(_ label: String, value: String, status: Bool) -> some View {
        HStack {
            Image(systemName: status ? "checkmark.circle.fill" : "xmark.circle.fill")
                .foregroundColor(status ? .green : .red)
                .font(.system(size: 12))

            Text(label)
                .font(.system(size: 12))

            Spacer()

            Text(value)
                .font(.system(size: 12))
                .foregroundColor(.secondary)
        }
    }

    @MainActor
    private func loadDiagnostics() async {
        isLoading = true
        errorMessage = nil

        do {
            diagnostics = try await teamService.getDiagnostics()
        } catch {
            errorMessage = "Failed to load diagnostics: \(error.localizedDescription)"
        }

        isLoading = false
    }
}

struct CreateTeamModal: View {
    @Environment(\.dismiss) var dismiss
    @State private var teamName: String = ""
    @State private var teamDescription: String = ""
    @State private var isLoading: Bool = false
    @State private var errorMessage: String? = nil

    private let teamService = TeamService.shared

    var body: some View {
        VStack(spacing: 20) {
            // Header
            Text("Create Team")
                .font(.title2.weight(.semibold))

            // Form
            VStack(alignment: .leading, spacing: 16) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Team Name")
                        .font(.system(size: 13, weight: .medium))
                    TextField("Enter team name", text: $teamName)
                        .textFieldStyle(.roundedBorder)
                        .disabled(isLoading)
                }

                VStack(alignment: .leading, spacing: 6) {
                    Text("Description (Optional)")
                        .font(.system(size: 13, weight: .medium))
                    TextEditor(text: $teamDescription)
                        .frame(height: 80)
                        .border(Color.gray.opacity(0.3))
                        .disabled(isLoading)
                }
            }

            // Error message
            if let error = errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            // Actions
            HStack(spacing: 12) {
                Button("Cancel") {
                    dismiss()
                }
                .keyboardShortcut(.escape)
                .disabled(isLoading)

                Button("Create Team") {
                    Task { await createTeam() }
                }
                .keyboardShortcut(.return)
                .buttonStyle(.borderedProminent)
                .disabled(teamName.isEmpty || isLoading)
            }

            if isLoading {
                ProgressView()
                    .scaleEffect(0.8)
            }
        }
        .frame(width: 500)
        .padding(24)
    }

    @MainActor
    private func createTeam() async {
        isLoading = true
        errorMessage = nil

        do {
            _ = try await teamService.createTeam(
                name: teamName,
                description: teamDescription.isEmpty ? nil : teamDescription
            )
            dismiss()
        } catch {
            errorMessage = "Failed to create team: \(error.localizedDescription)"
        }

        isLoading = false
    }
}

struct JoinTeamModal: View {
    @Environment(\.dismiss) var dismiss
    @State private var teamCode: String = ""
    @State private var isLoading: Bool = false
    @State private var errorMessage: String? = nil

    private let teamService = TeamService.shared

    var body: some View {
        VStack(spacing: 20) {
            // Header
            Text("Join Team")
                .font(.title2.weight(.semibold))

            Text("Enter the team invitation code to join")
                .font(.system(size: 13))
                .foregroundColor(.secondary)

            // Form
            VStack(alignment: .leading, spacing: 6) {
                Text("Team Code")
                    .font(.system(size: 13, weight: .medium))
                TextField("Enter invitation code", text: $teamCode)
                    .textFieldStyle(.roundedBorder)
                    .disabled(isLoading)
                    .font(.system(.body, design: .monospaced))
            }

            // Error message
            if let error = errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            // Actions
            HStack(spacing: 12) {
                Button("Cancel") {
                    dismiss()
                }
                .keyboardShortcut(.escape)
                .disabled(isLoading)

                Button("Join Team") {
                    Task { await joinTeam() }
                }
                .keyboardShortcut(.return)
                .buttonStyle(.borderedProminent)
                .disabled(teamCode.isEmpty || isLoading)
            }

            if isLoading {
                ProgressView()
                    .scaleEffect(0.8)
            }
        }
        .frame(width: 450)
        .padding(24)
    }

    @MainActor
    private func joinTeam() async {
        isLoading = true
        errorMessage = nil

        do {
            _ = try await teamService.joinTeam(code: teamCode)
            dismiss()
        } catch {
            errorMessage = "Failed to join team: \(error.localizedDescription)"
        }

        isLoading = false
    }
}

struct VaultSetupModal: View {
    @Environment(\.dismiss) var dismiss
    @State private var password: String = ""
    @State private var confirmPassword: String = ""
    @State private var isLoading: Bool = false
    @State private var errorMessage: String? = nil
    @State private var setupStatus: String? = nil

    private let teamService = TeamService.shared

    var body: some View {
        VStack(spacing: 20) {
            // Header
            Text("Vault Setup")
                .font(.title2.weight(.semibold))

            Text("Set up encrypted vault for secure file storage")
                .font(.system(size: 13))
                .foregroundColor(.secondary)

            // Form
            VStack(alignment: .leading, spacing: 16) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Master Password")
                        .font(.system(size: 13, weight: .medium))
                    SecureField("Enter master password", text: $password)
                        .textFieldStyle(.roundedBorder)
                        .disabled(isLoading)
                }

                VStack(alignment: .leading, spacing: 6) {
                    Text("Confirm Password")
                        .font(.system(size: 13, weight: .medium))
                    SecureField("Re-enter password", text: $confirmPassword)
                        .textFieldStyle(.roundedBorder)
                        .disabled(isLoading)
                }

                Text("⚠️ Store this password securely. It cannot be recovered.")
                    .font(.caption)
                    .foregroundColor(.orange)
            }

            // Status/Error message
            if let status = setupStatus {
                Text(status)
                    .font(.caption)
                    .foregroundColor(.green)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            if let error = errorMessage {
                Text(error)
                    .font(.caption)
                    .foregroundColor(.red)
                    .frame(maxWidth: .infinity, alignment: .leading)
            }

            // Actions
            HStack(spacing: 12) {
                Button("Cancel") {
                    dismiss()
                }
                .keyboardShortcut(.escape)
                .disabled(isLoading)

                Button("Setup Vault") {
                    Task { await setupVault() }
                }
                .keyboardShortcut(.return)
                .buttonStyle(.borderedProminent)
                .disabled(!canSubmit || isLoading)
            }

            if isLoading {
                ProgressView()
                    .scaleEffect(0.8)
            }
        }
        .frame(width: 500)
        .padding(24)
    }

    private var canSubmit: Bool {
        !password.isEmpty && password == confirmPassword && password.count >= 8
    }

    @MainActor
    private func setupVault() async {
        isLoading = true
        errorMessage = nil
        setupStatus = nil

        do {
            let response = try await teamService.setupVault(password: password)
            setupStatus = response.message
            try? await Task.sleep(nanoseconds: 1_500_000_000)
            dismiss()
        } catch {
            errorMessage = "Setup failed: \(error.localizedDescription)"
        }

        isLoading = false
    }
}

// MARK: - Preview

#Preview {
    TeamWorkspace()
        .frame(width: 1200, height: 800)
}
