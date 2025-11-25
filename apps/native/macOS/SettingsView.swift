//
//  SettingsView.swift
//  MagnetarStudio
//
//  Settings panel accessible via menu bar.
//

import SwiftUI
import AppKit

struct SettingsView: View {
    @AppStorage("apiBaseURL") private var apiBaseURL = "http://localhost:8000"
    @AppStorage("defaultModel") private var defaultModel = "mistral"
    @AppStorage("enableBiometrics") private var enableBiometrics = true
    @AppStorage("theme") private var theme = "system"

    var body: some View {
        TabView {
            GeneralSettingsView()
                .tabItem {
                    Label("General", systemImage: "gear")
                }

            APISettingsView(apiBaseURL: $apiBaseURL, defaultModel: $defaultModel)
                .tabItem {
                    Label("API", systemImage: "network")
                }

            SecuritySettingsView(enableBiometrics: $enableBiometrics)
                .tabItem {
                    Label("Security", systemImage: "lock.shield")
                }

            AppearanceSettingsView(theme: $theme)
                .tabItem {
                    Label("Appearance", systemImage: "paintbrush")
                }

            MagnetarCloudSettingsView()
                .tabItem {
                    Label("MagnetarCloud", systemImage: "cloud")
                }
        }
        .frame(width: 500, height: 400)
    }
}

// MARK: - General Settings

struct GeneralSettingsView: View {
    var body: some View {
        Form {
            Section("Application") {
                Toggle("Launch at Login", isOn: .constant(false))
                Toggle("Show in Menu Bar", isOn: .constant(true))
                Toggle("Enable Notifications", isOn: .constant(true))
            }

            Section("Editor") {
                Toggle("Auto-save Chat Sessions", isOn: .constant(true))
                Toggle("Show Line Numbers", isOn: .constant(true))
                Toggle("Word Wrap", isOn: .constant(false))
            }
        }
        .formStyle(.grouped)
        .padding()
    }
}

// MARK: - API Settings

struct APISettingsView: View {
    @Binding var apiBaseURL: String
    @Binding var defaultModel: String

    let availableModels = ["mistral", "llama3", "qwen", "codestral"]
    @State private var connectionStatus: SimpleStatus = .idle

    var body: some View {
        Form {
            Section("Backend API") {
                TextField("API Base URL", text: $apiBaseURL)
                    .textFieldStyle(.roundedBorder)

                Button("Test Connection") {
                    Task { await testConnection() }
                }
                statusLabel(connectionStatus)
            }

            Section("AI Models") {
                Picker("Default Model", selection: $defaultModel) {
                    ForEach(availableModels, id: \.self) { model in
                        Text(model.capitalized).tag(model)
                    }
                }

                Text("Default model for new chat sessions")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }
        }
        .formStyle(.grouped)
        .padding()
    }

    // MARK: - Actions

    private func testConnection() async {
        await MainActor.run { connectionStatus = .loading }

        let trimmedBase = apiBaseURL.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let baseURL = URL(string: trimmedBase) else {
            await MainActor.run {
                connectionStatus = .failure("Invalid base URL")
            }
            return
        }

        let healthURL = baseURL.appendingPathComponent("health")
        var request = URLRequest(url: healthURL)
        request.httpMethod = "GET"
        request.timeoutInterval = 8

        do {
            let (_, response) = try await URLSession.shared.data(for: request)
            guard let http = response as? HTTPURLResponse else {
                await MainActor.run {
                    connectionStatus = .failure("Invalid response")
                }
                return
            }

            if (200...299).contains(http.statusCode) {
                await MainActor.run {
                    connectionStatus = .success("Connected (\(http.statusCode))")
                }
            } else {
                await MainActor.run {
                    connectionStatus = .failure("Status \(http.statusCode)")
                }
            }
        } catch {
            await MainActor.run {
                connectionStatus = .failure(error.localizedDescription)
            }
        }
    }
}

// MARK: - Security Settings

struct SecuritySettingsView: View {
    @Binding var enableBiometrics: Bool
    @State private var cacheStatus: SimpleStatus = .idle
    @State private var keychainStatus: SimpleStatus = .idle

    var body: some View {
        Form {
            Section("Authentication") {
                Toggle("Require Face ID", isOn: $enableBiometrics)

                Text("Secure your authentication tokens with Face ID or Touch ID")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Section("Session") {
                Toggle("Auto-lock after Inactivity", isOn: .constant(true))

                Picker("Timeout", selection: .constant(15)) {
                    Text("5 minutes").tag(5)
                    Text("15 minutes").tag(15)
                    Text("30 minutes").tag(30)
                    Text("1 hour").tag(60)
                }
            }

            Section("Data") {
                Button("Clear Cache") {
                    Task { await clearCache() }
                }
                statusLabel(cacheStatus)

                Button("Reset Keychain", role: .destructive) {
                    Task { await resetKeychain() }
                }
                statusLabel(keychainStatus)
            }
        }
        .formStyle(.grouped)
        .padding()
    }

    // MARK: - Actions

    private func clearCache() async {
        await MainActor.run { cacheStatus = .loading }

        do {
            let fileManager = FileManager.default
            let cachesDir = try fileManager.url(
                for: .cachesDirectory,
                in: .userDomainMask,
                appropriateFor: nil,
                create: true
            )

            let bundleId = Bundle.main.bundleIdentifier ?? "com.magnetarstudio.app"
            let appCacheDir = cachesDir.appendingPathComponent(bundleId, isDirectory: true)

            if fileManager.fileExists(atPath: appCacheDir.path) {
                let contents = try fileManager.contentsOfDirectory(at: appCacheDir, includingPropertiesForKeys: nil)
                for item in contents {
                    try? fileManager.removeItem(at: item)
                }
            }

            await MainActor.run { cacheStatus = .success("Cache cleared") }
        } catch {
            await MainActor.run { cacheStatus = .failure(error.localizedDescription) }
        }
    }

    private func resetKeychain() async {
        await MainActor.run { keychainStatus = .loading }

        do {
            try KeychainService.shared.deleteToken()
            await MainActor.run { keychainStatus = .success("Keychain reset") }
        } catch {
            await MainActor.run { keychainStatus = .failure(error.localizedDescription) }
        }
    }
}

// MARK: - Appearance Settings

struct AppearanceSettingsView: View {
    @Binding var theme: String

    var body: some View {
        Form {
            Section("Theme") {
                Picker("Appearance", selection: $theme) {
                    Text("System").tag("system")
                    Text("Light").tag("light")
                    Text("Dark").tag("dark")
                }
                .pickerStyle(.segmented)

                Text("Follow system appearance settings or choose a specific theme")
                    .font(.caption)
                    .foregroundStyle(.secondary)
            }

            Section("Liquid Glass") {
                Toggle("Enable Blur Effects", isOn: .constant(true))
                Toggle("Reduce Transparency", isOn: .constant(false))

                Slider(value: .constant(0.5), in: 0...1) {
                    Text("Glass Opacity")
                }
            }

            Section("Font") {
                Picker("Editor Font Size", selection: .constant(14)) {
                    Text("12pt").tag(12)
                    Text("14pt").tag(14)
                    Text("16pt").tag(16)
                    Text("18pt").tag(18)
                }
            }
        }
        .formStyle(.grouped)
        .padding()
    }
}

// MARK: - MagnetarCloud Settings

struct MagnetarCloudSettingsView: View {
    @State private var isAuthenticated: Bool = false
    @State private var cloudEmail: String = ""
    @State private var cloudPlan: String = "Free"
    @State private var syncEnabled: Bool = true
    private let supabaseAuthURL = URL(string: "https://auth.magnetar.studio/login")
    private let subscriptionURL = URL(string: "https://billing.magnetar.studio")

    var body: some View {
        Form {
            if !isAuthenticated {
                // Not authenticated
                Section {
                    VStack(alignment: .leading, spacing: 16) {
                        HStack(spacing: 12) {
                            Image(systemName: "cloud.fill")
                                .font(.system(size: 32))
                                .foregroundStyle(LinearGradient.magnetarGradient)

                            VStack(alignment: .leading, spacing: 4) {
                                Text("MagnetarCloud")
                                    .font(.headline)

                                Text("Sign in to sync across devices and access your models")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }

                        Button {
                            triggerAuth()
                        } label: {
                            Label("Login to MagnetarCloud Account", systemImage: "person.circle")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.large)
                    }
                    .padding(.vertical, 8)
                }

                Section("Features") {
                    Label("Sync chat sessions across devices", systemImage: "arrow.triangle.2.circlepath")
                    Label("Access your fine-tuned models", systemImage: "cube.box")
                    Label("Download model updates", systemImage: "arrow.down.circle")
                    Label("Priority support", systemImage: "headphones")
                }
                .foregroundStyle(.secondary)
                .font(.caption)
            } else {
                // Authenticated
                Section("Account") {
                    HStack {
                        Text("Email")
                        Spacer()
                        Text(cloudEmail)
                            .foregroundStyle(.secondary)
                    }

                    HStack {
                        Text("Plan")
                        Spacer()
                        Text(cloudPlan)
                            .foregroundStyle(Color.magnetarPrimary)
                    }

                    Button("Manage Subscription") {
                        openExternal(subscriptionURL)
                    }
                }

                Section("Sync") {
                    Toggle("Enable Cloud Sync", isOn: $syncEnabled)

                    Text("Sync chat sessions, settings, and models across all your devices")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    if syncEnabled {
                        HStack {
                            Image(systemName: "checkmark.circle.fill")
                                .foregroundColor(.green)
                            Text("Last sync: Just now")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                }

                Section("Connected Devices") {
                    Label("MacBook Pro", systemImage: "laptopcomputer")
                    Label("iPad Pro", systemImage: "ipad")

                    Text("2 devices connected")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }

                Section {
                    Button("Sign Out", role: .destructive) {
                        isAuthenticated = false
                        cloudEmail = ""
                        cloudPlan = "Free"
                    }
                }
            }
        }
        .formStyle(.grouped)
        .padding()
    }

    private func triggerAuth() {
        openExternal(supabaseAuthURL)
        // Keep optimistic UI for now; replace with real auth callback when available.
        isAuthenticated = true
        cloudEmail = "user@example.com"
        cloudPlan = "Pro"
    }

    private func openExternal(_ url: URL?) {
        guard let url else { return }
        NSWorkspace.shared.open(url)
    }
}

// MARK: - Preview

#Preview {
    SettingsView()
}

// MARK: - Helpers

private enum SimpleStatus: Equatable {
    case idle
    case loading
    case success(String)
    case failure(String)
}

@ViewBuilder
private func statusLabel(_ status: SimpleStatus) -> some View {
    switch status {
    case .idle:
        EmptyView()
    case .loading:
        HStack(spacing: 6) {
            ProgressView()
                .controlSize(.small)
            Text("Working...")
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    case .success(let message):
        HStack(spacing: 6) {
            Image(systemName: "checkmark.circle.fill")
                .foregroundStyle(.green)
            Text(message)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    case .failure(let message):
        HStack(spacing: 6) {
            Image(systemName: "exclamationmark.triangle.fill")
                .foregroundStyle(.orange)
            Text(message)
                .font(.caption)
                .foregroundStyle(.secondary)
        }
    }
}
