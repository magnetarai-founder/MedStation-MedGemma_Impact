//
//  TeamWorkspace.swift
//  MagnetarStudio (macOS)
//
//  Team collaboration workspace matching React TeamWorkspace.tsx specs exactly
//  - Toolbar: NetworkSelector, Diagnostics, View tabs, Join/Create buttons
//  - Content: Switches between TeamChat, Docs, Workflows, Vault sub-workspaces
//

import SwiftUI
import Foundation

// MARK: - Team Service Models & Service
// All models (Team, TeamDocument, TeamMessage, DiagnosticsStatus, P2PNetworkStatus, UserPermissions, etc.)
// are imported from Shared/Services/TeamService.swift

struct TeamWorkspace: View {
    @State private var networkMode: NetworkMode = .local
    @State private var workspaceView: TeamView = .chat
    @State private var currentTeam: Team? = nil

    // Modals/Panels
    @State private var showDiagnostics = false
    @State private var showCreateTeam = false
    @State private var showJoinTeam = false
    @State private var showVaultSetup = false

    // Vault status
    @State private var vaultReady: Bool = false
    @State private var checkingVaultStatus: Bool = false
    @State private var vaultError: String? = nil

    // Permissions
    @State private var permissions: UserPermissions? = nil
    @State private var isLoadingPermissions: Bool = false

    var body: some View {
        VStack(spacing: 0) {
            // Toolbar
            toolbar
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .background(Color.gray.opacity(0.05))
                .overlay(
                    Rectangle()
                        .fill(Color.gray.opacity(0.2))
                        .frame(height: 1),
                    alignment: .bottom
                )

            // Content area
            contentArea
        }
        .sheet(isPresented: $showDiagnostics) {
            DiagnosticsPanel()
        }
        .sheet(isPresented: $showCreateTeam) {
            CreateTeamModal()
        }
        .sheet(isPresented: $showJoinTeam) {
            JoinTeamModal()
        }
        .sheet(isPresented: $showVaultSetup) {
            VaultSetupModal()
        }
        .task {
            await loadPermissions()
        }
    }

    // MARK: - Data Loading

    private func loadPermissions() async {
        isLoadingPermissions = true
        defer { isLoadingPermissions = false }

        do {
            permissions = try await TeamService.shared.getUserPermissions()
        } catch {
            // Keep default permissions on error
            print("Failed to load permissions: \(error.localizedDescription)")
        }
    }

    // MARK: - Toolbar

    private var toolbar: some View {
        HStack(spacing: 12) {
            // Left cluster: NetworkSelector + Diagnostics
            NetworkSelector(mode: $networkMode)

            Button {
                showDiagnostics = true
            } label: {
                HStack(spacing: 8) {
                    Image(systemName: "waveform.path.ecg")
                        .font(.system(size: 16))
                    Text("Diagnostics")
                        .font(.system(size: 14))
                }
                .foregroundColor(.secondary)
                .padding(.horizontal, 12)
                .padding(.vertical, 6)
                .background(
                    RoundedRectangle(cornerRadius: 8)
                        .fill(Color.gray.opacity(0.1))
                )
            }
            .buttonStyle(.plain)
            .help("Network Diagnostics")

            // Divider
            Rectangle()
                .fill(Color.gray.opacity(0.3))
                .frame(width: 1, height: 24)

            // View tabs
            HStack(spacing: 4) {
                // Chat
                TeamTabButton(
                    title: "Chat",
                    icon: "message",
                    isActive: workspaceView == .chat,
                    tintColor: Color.magnetarPrimary,
                    action: { workspaceView = .chat }
                )

                // Docs
                if permissions?.canAccessDocuments ?? true {
                    TeamTabButton(
                        title: "Docs",
                        icon: "doc.text",
                        isActive: workspaceView == .docs,
                        tintColor: Color.magnetarPrimary,
                        action: { workspaceView = .docs }
                    )
                }

                // Workflows
                if permissions?.canAccessAutomation ?? true {
                    TeamTabButton(
                        title: "Workflows",
                        icon: "arrow.triangle.branch",
                        isActive: workspaceView == .workflows,
                        tintColor: Color.magnetarPrimary,
                        action: { workspaceView = .workflows }
                    )
                }

                // Divider before Vault
                if permissions?.canAccessVault ?? true {
                    Rectangle()
                        .fill(Color.gray.opacity(0.3))
                        .frame(width: 1, height: 24)
                        .padding(.horizontal, 8)
                }

                // Vault (amber tint)
                if permissions?.canAccessVault ?? true {
                    TeamTabButton(
                        title: "Vault",
                        icon: "lock.shield",
                        isActive: workspaceView == .vault,
                        tintColor: .orange,
                        action: { handleVaultClick() }
                    )
                }
            }

            Spacer()

            // Right cluster: Join/Create buttons (only when no team)
            if currentTeam == nil {
                HStack(spacing: 8) {
                    Button {
                        showJoinTeam = true
                    } label: {
                        HStack(spacing: 8) {
                            Image(systemName: "person.badge.plus")
                                .font(.system(size: 16))
                            Text("Join Team")
                                .font(.system(size: 14, weight: .medium))
                        }
                        .foregroundColor(.white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(Color.green)
                        )
                    }
                    .buttonStyle(.plain)

                    Button {
                        showCreateTeam = true
                    } label: {
                        HStack(spacing: 8) {
                            Image(systemName: "plus")
                                .font(.system(size: 16))
                            Text("Create Team")
                                .font(.system(size: 14, weight: .medium))
                        }
                        .foregroundColor(.white)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 6)
                        .background(
                            RoundedRectangle(cornerRadius: 8)
                                .fill(Color.magnetarPrimary)
                        )
                    }
                    .buttonStyle(.plain)
                }
            }
        }
    }

    // MARK: - Content Area

    @ViewBuilder
    private var contentArea: some View {
        switch workspaceView {
        case .chat:
            TeamChatView(mode: networkMode)
        case .docs:
            DocsWorkspace()
        case .workflows:
            AutomationWorkspaceView()
        case .vault:
            VaultWorkspace()
        }
    }

    // MARK: - Actions

    private func handleVaultClick() {
        Task {
            await checkVaultStatus()
        }
    }

    @MainActor
    private func checkVaultStatus() async {
        checkingVaultStatus = true
        vaultError = nil

        do {
            // Try to access vault by checking folders endpoint
            let url = URL(string: "http://localhost:8000/api/v1/vault/folders?vault_type=real")!
            var request = URLRequest(url: url)
            request.httpMethod = "GET"

            // Get token if available (will be nil in DEBUG mode)
            if let token = KeychainService.shared.loadToken() {
                request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
            }

            let (_, response) = try await URLSession.shared.data(for: request)

            guard let httpResponse = response as? HTTPURLResponse else {
                throw NSError(domain: "VaultError", code: -1, userInfo: [NSLocalizedDescriptionKey: "Invalid response"])
            }

            if httpResponse.statusCode == 200 {
                // Vault is accessible
                vaultReady = true
                workspaceView = .vault
            } else if httpResponse.statusCode == 403 {
                // Vault needs setup or no permissions
                vaultError = "Vault access denied. Setup may be required."
                showVaultSetup = true
            } else {
                vaultError = "Vault returned status \(httpResponse.statusCode)"
            }

        } catch {
            vaultError = "Failed to check vault status: \(error.localizedDescription)"
            print("Vault status check error: \(error)")
        }

        checkingVaultStatus = false
    }
}

// MARK: - Team Tab Button Component

struct TeamTabButton: View {
    let title: String
    let icon: String
    let isActive: Bool
    let tintColor: Color
    let action: () -> Void

    @State private var isHovered = false

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                Image(systemName: icon)
                    .font(.system(size: 16))
                Text(title)
                    .font(.system(size: 14, weight: isActive ? .medium : .regular))
            }
            .foregroundColor(isActive ? tintColor : (isHovered ? .primary : .secondary))
            .padding(.horizontal, 12)
            .padding(.vertical, 6)
            .background(
                RoundedRectangle(cornerRadius: 8)
                    .fill(isActive ? tintColor.opacity(0.15) : (isHovered ? Color.gray.opacity(0.1) : Color.clear))
            )
        }
        .buttonStyle(.plain)
        .onHover { hovering in
            isHovered = hovering
        }
    }
}

// MARK: - Supporting Types

enum TeamView {
    case chat
    case docs
    case workflows
    case vault
}

// AutomationWorkspace moved to Shared/Components/AutomationWorkspace.swift


// MARK: - Supporting Types

enum VaultViewMode {
    case grid
    case list
}

// Legacy mock file model for the UI preview; renamed to avoid clashing with real VaultFile model.
struct LegacyVaultFile: Identifiable {
    let id = UUID()
    let name: String
    let size: String
    let modified: String
    let mimeType: String

    var mimeIcon: String {
        switch mimeType {
        case "image": return "photo"
        case "video": return "video"
        case "audio": return "music.note"
        case "pdf": return "doc.text"
        case "zip": return "archivebox"
        case "code": return "chevron.left.forwardslash.chevron.right"
        default: return "doc"
        }
    }

    var mimeColor: Color {
        switch mimeType {
        case "image": return .purple
        case "video": return .pink
        case "audio": return .green
        case "pdf": return .red
        case "zip": return .yellow
        case "code": return .indigo
        default: return .gray
        }
    }

    static let mockFiles = [
        LegacyVaultFile(name: "Confidential Report.pdf", size: "2.4 MB", modified: "2 hours ago", mimeType: "pdf"),
        LegacyVaultFile(name: "Team Photo.jpg", size: "1.8 MB", modified: "Yesterday", mimeType: "image"),
        LegacyVaultFile(name: "Project Source.zip", size: "15.2 MB", modified: "3 days ago", mimeType: "zip"),
        LegacyVaultFile(name: "Meeting Recording.mp4", size: "45.6 MB", modified: "Last week", mimeType: "video"),
        LegacyVaultFile(name: "Secret Keys.txt", size: "12 KB", modified: "2 weeks ago", mimeType: "code")
    ]
}

// MARK: - New Folder Dialog

struct NewFolderDialog: View {
    @Binding var folderName: String
    @Binding var isPresented: Bool
    let onCreate: () -> Void

    var body: some View {
        VStack(spacing: 24) {
            // Header
            HStack {
                Text("New Folder")
                    .font(.system(size: 20, weight: .semibold))

                Spacer()

                Button {
                    isPresented = false
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 16))
                        .foregroundColor(.secondary)
                        .frame(width: 28, height: 28)
                }
                .buttonStyle(.plain)
            }

            Divider()

            // Form
            VStack(alignment: .leading, spacing: 12) {
                Text("Folder Name")
                    .font(.headline)

                TextField("Enter folder name", text: $folderName)
                    .textFieldStyle(.roundedBorder)
                    .onSubmit {
                        onCreate()
                        isPresented = false
                    }
            }

            Spacer()

            // Footer buttons
            HStack {
                Spacer()

                Button("Cancel") {
                    isPresented = false
                }
                .keyboardShortcut(.cancelAction)

                Button("Create") {
                    onCreate()
                    isPresented = false
                }
                .keyboardShortcut(.defaultAction)
                .disabled(folderName.isEmpty)
            }
        }
        .padding(24)
        .frame(width: 400, height: 250)
        .background(Color(nsColor: .windowBackgroundColor))
    }
}

// MARK: - File Preview Modal

struct FilePreviewModal: View {
    let file: VaultFile
    @Binding var isPresented: Bool
    let onDownload: () -> Void
    let onDelete: () -> Void
    let vaultPassword: String

    @State private var isDownloading: Bool = false
    @State private var downloadError: String? = nil
    @State private var downloadSuccess: Bool = false

    private let vaultService = VaultService.shared

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                VStack(alignment: .leading, spacing: 4) {
                    Text(file.name)
                        .font(.system(size: 16, weight: .semibold))

                    HStack(spacing: 8) {
                        Text(file.mimeType?.uppercased() ?? "FILE")
                            .font(.system(size: 12))
                            .foregroundColor(.secondary)

                        Text("•")
                            .font(.system(size: 12))
                            .foregroundColor(.secondary)

                        Text(file.sizeFormatted)
                            .font(.system(size: 12))
                            .foregroundColor(.secondary)
                    }
                }

                Spacer()

                Button {
                    isPresented = false
                } label: {
                    Image(systemName: "xmark")
                        .font(.system(size: 16))
                        .foregroundColor(.secondary)
                        .frame(width: 32, height: 32)
                }
                .buttonStyle(.plain)
            }
            .padding(24)
            .background(Color(.controlBackgroundColor))
            .overlay(
                Rectangle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(height: 1),
                alignment: .bottom
            )

            // Body
            VStack(spacing: 16) {
                Image(systemName: file.mimeIcon)
                    .font(.system(size: 64))
                    .foregroundColor(Color(file.mimeColor))

                Text("Preview for \(file.mimeType ?? "unknown") files")
                    .font(.title2)

                Text("File preview rendering will appear here")
                    .font(.subheadline)
                    .foregroundColor(.secondary)

                // Download status messages
                if downloadSuccess {
                    HStack(spacing: 8) {
                        Image(systemName: "checkmark.circle.fill")
                            .foregroundColor(.green)
                        Text("File downloaded successfully")
                            .font(.system(size: 14))
                            .foregroundColor(.green)
                    }
                    .padding(.top, 8)
                }

                if let error = downloadError {
                    HStack(spacing: 8) {
                        Image(systemName: "exclamationmark.triangle.fill")
                            .foregroundColor(.red)
                        Text(error)
                            .font(.system(size: 14))
                            .foregroundColor(.red)
                    }
                    .padding(.top, 8)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .padding(24)

            // Footer
            HStack(spacing: 12) {
                Button {
                    onDelete()
                    isPresented = false
                } label: {
                    HStack(spacing: 8) {
                        Image(systemName: "trash")
                            .font(.system(size: 16))
                        Text("Delete")
                            .font(.system(size: 14, weight: .medium))
                    }
                    .foregroundColor(.red)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .strokeBorder(Color.red, lineWidth: 1)
                    )
                }
                .buttonStyle(.plain)
                .disabled(isDownloading)

                Spacer()

                Button {
                    Task {
                        await handleDownload()
                    }
                } label: {
                    HStack(spacing: 8) {
                        if isDownloading {
                            ProgressView()
                                .scaleEffect(0.8)
                                .frame(width: 16, height: 16)
                        } else {
                            Image(systemName: downloadSuccess ? "checkmark.circle" : "arrow.down.circle")
                                .font(.system(size: 16))
                        }
                        Text(isDownloading ? "Downloading..." : (downloadSuccess ? "Downloaded" : "Download"))
                            .font(.system(size: 14, weight: .medium))
                    }
                    .foregroundColor(.white)
                    .padding(.horizontal, 16)
                    .padding(.vertical, 10)
                    .background(
                        RoundedRectangle(cornerRadius: 8)
                            .fill(downloadSuccess ? Color.green : Color.magnetarPrimary)
                    )
                }
                .buttonStyle(.plain)
                .disabled(isDownloading || downloadSuccess)
            }
            .padding(24)
            .background(Color(.controlBackgroundColor))
            .overlay(
                Rectangle()
                    .fill(Color.gray.opacity(0.2))
                    .frame(height: 1),
                alignment: .top
            )
        }
        .frame(width: 700, height: 600)
        .background(Color(.windowBackgroundColor))
    }

    // MARK: - Download Handler

    @MainActor
    private func handleDownload() async {
        // Reset states
        downloadError = nil
        downloadSuccess = false

        // Show save panel
        let savePanel = NSSavePanel()
        savePanel.nameFieldStringValue = file.name
        savePanel.canCreateDirectories = true
        savePanel.showsTagField = false

        let response = savePanel.runModal()

        // User cancelled
        guard response == .OK, let destinationURL = savePanel.url else {
            return
        }

        // Start download
        isDownloading = true

        do {
            let data = try await vaultService.download(
                fileId: file.id,
                vaultType: "real",
                passphrase: vaultPassword
            )

            try data.write(to: destinationURL)

            downloadSuccess = true
            isDownloading = false

            // Auto-close after success (optional)
            DispatchQueue.main.asyncAfter(deadline: .now() + 1.5) {
                isPresented = false
            }
        } catch let error as VaultError {
            downloadError = error.localizedDescription
            isDownloading = false
        } catch {
            downloadError = "Download failed: \(error.localizedDescription)"
            isDownloading = false
        }
    }
}

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
