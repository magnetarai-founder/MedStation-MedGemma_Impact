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
                Text("System Diagnostics")
                    .font(.title2.weight(.semibold))

                Spacer()

                Button(action: { Task { await loadDiagnostics() } }) {
                    HStack(spacing: 4) {
                        Image(systemName: "arrow.clockwise")
                        Text("Refresh")
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
                            let isHealthy = diag.database.status == "healthy" && diag.metal.available
                            Image(systemName: isHealthy ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                                .foregroundColor(isHealthy ? .green : .orange)
                            Text(diag.partial == true ? "PARTIAL" : "OK")
                                .font(.system(size: 14, weight: .medium))
                        }

                        Divider()

                        // System Status
                        VStack(alignment: .leading, spacing: 8) {
                            Text("System")
                                .font(.system(size: 13, weight: .semibold))

                            if let os = diag.system.os {
                                statusRow("OS", value: os, status: true)
                            }
                            if let cpu = diag.system.cpuPercent {
                                statusRow("CPU", value: "\(String(format: "%.1f", cpu))%", status: cpu < 80)
                            }
                            if let ram = diag.system.ram {
                                let used = ram.usedGb ?? 0
                                let total = ram.totalGb ?? 1
                                statusRow("RAM", value: "\(String(format: "%.1f", used))/\(String(format: "%.1f", total)) GB", status: used / total < 0.9)
                            }
                            if let disk = diag.system.disk {
                                let used = disk.usedGb ?? 0
                                let total = disk.totalGb ?? 1
                                statusRow("Disk", value: "\(String(format: "%.1f", used))/\(String(format: "%.1f", total)) GB", status: used / total < 0.9)
                            }
                        }

                        Divider()

                        // Metal Status
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Metal GPU")
                                .font(.system(size: 13, weight: .semibold))

                            statusRow("Available", value: diag.metal.available ? "Yes" : "No", status: diag.metal.available)
                            if let device = diag.metal.device {
                                statusRow("Device", value: device, status: true)
                            }
                            if let workingSet = diag.metal.recommendedWorkingSetGb {
                                statusRow("Working Set", value: "\(String(format: "%.1f", workingSet)) GB", status: true)
                            }
                            if let error = diag.metal.error {
                                statusRow("Error", value: error, status: false)
                            }
                        }

                        Divider()

                        // Ollama Status
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Ollama")
                                .font(.system(size: 13, weight: .semibold))

                            statusRow("Available", value: diag.ollama.available ? "Yes" : "No", status: diag.ollama.available)
                            if let status = diag.ollama.status {
                                statusRow("Status", value: status, status: status == "running")
                            }
                            if let count = diag.ollama.modelCount {
                                statusRow("Models", value: "\(count)", status: count > 0)
                            }
                            if let error = diag.ollama.error {
                                statusRow("Error", value: error, status: false)
                            }
                        }

                        Divider()

                        // P2P Status
                        VStack(alignment: .leading, spacing: 8) {
                            Text("P2P Network")
                                .font(.system(size: 13, weight: .semibold))

                            if let status = diag.p2p.status {
                                statusRow("Status", value: status, status: status != "unavailable" && status != "error")
                            }
                            if let peers = diag.p2p.peers {
                                statusRow("Peers", value: "\(peers)", status: true)
                            }
                            if let error = diag.p2p.error {
                                statusRow("Error", value: error, status: false)
                            }
                        }

                        Divider()

                        // Database Status
                        VStack(alignment: .leading, spacing: 8) {
                            Text("Database")
                                .font(.system(size: 13, weight: .semibold))

                            if let status = diag.database.status {
                                statusRow("Status", value: status, status: status == "healthy")
                            }
                            if let size = diag.database.sizeMb {
                                statusRow("Size", value: "\(String(format: "%.2f", size)) MB", status: true)
                            }
                            if let tables = diag.database.tableCount {
                                statusRow("Tables", value: "\(tables)", status: tables > 0)
                            }
                            if let error = diag.database.error {
                                statusRow("Error", value: error, status: false)
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
        .frame(width: 600, height: 500)
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
                .lineLimit(1)
                .truncationMode(.tail)
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
