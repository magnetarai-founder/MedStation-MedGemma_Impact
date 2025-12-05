//
//  SettingsView.swift
//  MagnetarStudio
//
//  Settings panel accessible via menu bar.
//

import SwiftUI
import AppKit
import ServiceManagement
import UserNotifications

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

            ModelManagementSettingsView()
                .tabItem {
                    Label("Models", systemImage: "cpu")
                }

            MagnetarCloudSettingsView()
                .tabItem {
                    Label("MagnetarCloud", systemImage: "cloud")
                }
        }
        .frame(minWidth: 600, idealWidth: 600, maxWidth: .infinity,
               minHeight: 500, idealHeight: 500, maxHeight: .infinity)
    }
}

// MARK: - General Settings

struct GeneralSettingsView: View {
    @StateObject private var settingsManager = SettingsManager.shared
    @StateObject private var settingsStore = SettingsStore.shared
    @AppStorage("autoSaveChatSessions") private var autoSaveChatSessions = true
    @AppStorage("showLineNumbers") private var showLineNumbers = true
    @AppStorage("wordWrap") private var wordWrap = false

    var body: some View {
        Form {
            Section("Application") {
                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Launch at Login", isOn: $settingsManager.launchAtLogin)
                        .disabled(settingsManager.launchAtLoginStatus == .loading)

                    statusLabel(settingsManager.launchAtLoginStatus)
                }

                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Show in Menu Bar", isOn: $settingsManager.showMenuBar)
                        .disabled(settingsManager.menuBarStatus == .loading)

                    statusLabel(settingsManager.menuBarStatus)
                }

                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Enable Notifications", isOn: $settingsManager.notificationsEnabled)
                        .disabled(settingsManager.notificationsStatus == .loading)

                    statusLabel(settingsManager.notificationsStatus)
                }
            }

            Section("Ollama") {
                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Auto-start Ollama on Launch", isOn: Binding(
                        get: { settingsStore.appSettings.ollamaAutoStart },
                        set: { newValue in
                            var updatedSettings = settingsStore.appSettings
                            updatedSettings.ollamaAutoStart = newValue
                            settingsStore.updateAppSettings(updatedSettings)
                        }
                    ))

                    Text("Automatically start Ollama server when MagnetarStudio launches")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Section("Editor") {
                Toggle("Auto-save Chat Sessions", isOn: $autoSaveChatSessions)
                Toggle("Show Line Numbers", isOn: $showLineNumbers)
                Toggle("Word Wrap", isOn: $wordWrap)
            }
        }
        .formStyle(.grouped)
        .padding()
        .onAppear {
            Task {
                await settingsManager.checkInitialStates()
            }
        }
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
    @AppStorage("autoLockEnabled") private var autoLockEnabled = true
    @AppStorage("autoLockTimeout") private var autoLockTimeout = 15
    @State private var cacheStatus: SimpleStatus = .idle
    @State private var keychainStatus: SimpleStatus = .idle
    @State private var biometricStatus: SimpleStatus = .idle

    private let biometricService = BiometricAuthService.shared
    private let keychainService = KeychainService.shared
    @ObservedObject private var securityManager = SecurityManager.shared

    var body: some View {
        Form {
            Section("Network Firewall") {
                VStack(alignment: .leading, spacing: 8) {
                    Toggle("Enable Network Firewall", isOn: Binding(
                        get: { securityManager.networkFirewallEnabled },
                        set: { securityManager.setNetworkFirewall(enabled: $0) }
                    ))

                    Text("Control all outgoing network connections with approval prompts (Little Snitch-style)")
                        .font(.caption)
                        .foregroundStyle(.secondary)

                    if securityManager.networkFirewallEnabled {
                        HStack {
                            Image(systemName: "shield.fill")
                                .foregroundColor(.green)
                            Text("Firewall active - all requests require approval")
                                .font(.caption)
                                .foregroundColor(.green)
                        }
                        .padding(.top, 4)
                    }
                }
            }

            Section("Biometric Authentication") {
                HStack {
                    Image(systemName: biometricService.biometricType().icon)
                        .foregroundColor(.blue)
                    Text(biometricService.biometricType().displayName)
                        .font(.headline)
                }

                Toggle("Enable Biometric Login", isOn: $enableBiometrics)
                    .disabled(!biometricService.isBiometricAvailable)

                Text("Sign in quickly and securely using \(biometricService.biometricType().displayName)")
                    .font(.caption)
                    .foregroundStyle(.secondary)

                if keychainService.hasBiometricCredentials() {
                    VStack(spacing: 8) {
                        HStack {
                            Image(systemName: "checkmark.shield.fill")
                                .foregroundColor(.green)
                            Text("Biometric credentials stored")
                                .font(.caption)
                            Spacer()
                        }

                        Button(role: .destructive) {
                            clearBiometricCredentials()
                        } label: {
                            HStack {
                                Image(systemName: "trash")
                                Text("Remove Biometric Credentials")
                            }
                        }
                        .disabled(biometricStatus == .loading)

                        statusLabel(biometricStatus)
                    }
                }
            }

            Section("Session") {
                Toggle("Auto-lock after Inactivity", isOn: $autoLockEnabled)

                Picker("Timeout", selection: $autoLockTimeout) {
                    Text("5 minutes").tag(5)
                    Text("15 minutes").tag(15)
                    Text("30 minutes").tag(30)
                    Text("1 hour").tag(60)
                }
                .disabled(!autoLockEnabled)
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

    private func clearBiometricCredentials() {
        biometricStatus = .loading

        do {
            try keychainService.deleteBiometricCredentials()
            biometricStatus = .success("Biometric credentials removed")
        } catch {
            biometricStatus = .failure(error.localizedDescription)
        }
    }
}

// MARK: - Appearance Settings

struct AppearanceSettingsView: View {
    @Binding var theme: String
    @AppStorage("enableBlurEffects") private var enableBlurEffects = true
    @AppStorage("reduceTransparency") private var reduceTransparency = false
    @AppStorage("glassOpacity") private var glassOpacity = 0.5
    @AppStorage("editorFontSize") private var editorFontSize = 14

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
                Toggle("Enable Blur Effects", isOn: $enableBlurEffects)
                Toggle("Reduce Transparency", isOn: $reduceTransparency)

                VStack(alignment: .leading, spacing: 8) {
                    Slider(value: $glassOpacity, in: 0...1) {
                        Text("Glass Opacity")
                    }
                    Text(String(format: "%.0f%%", glassOpacity * 100))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Section("Font") {
                Picker("Editor Font Size", selection: $editorFontSize) {
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
    @StateObject private var authManager = CloudAuthManager.shared
    @State private var syncEnabled: Bool = true
    private let subscriptionURL = URL(string: "https://billing.magnetar.studio")

    var body: some View {
        Form {
            if !authManager.isAuthenticated {
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
                            authManager.startAuthFlow()
                        } label: {
                            Label("Login to MagnetarCloud Account", systemImage: "person.circle")
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(.borderedProminent)
                        .controlSize(.large)
                        .disabled(authManager.authStatus == .loading)
                    }
                    .padding(.vertical, 8)

                    // Auth status
                    statusLabel(authManager.authStatus)
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
                        Text(authManager.cloudEmail)
                            .foregroundStyle(.secondary)
                    }

                    HStack {
                        Text("Plan")
                        Spacer()
                        Text(authManager.cloudPlan)
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
                        authManager.signOut()
                    }
                }
            }
        }
        .formStyle(.grouped)
        .padding()
        .onAppear {
            Task {
                await authManager.checkAuthStatus()
            }
        }
    }

    private func openExternal(_ url: URL?) {
        guard let url else { return }
        NSWorkspace.shared.open(url)
    }
}

// MARK: - Cloud Auth Manager

/// Manages MagnetarCloud authentication, token storage, and profile
@MainActor
final class CloudAuthManager: ObservableObject {
    static let shared = CloudAuthManager()

    @Published var isAuthenticated: Bool = false
    @Published var cloudEmail: String = ""
    @Published var cloudPlan: String = "Free"
    @Published var authStatus: SimpleStatus = .idle

    private let authBaseURL = "https://auth.magnetar.studio"
    private let redirectURI = "magnetarstudio://auth/callback"
    private let apiClient = ApiClient.shared
    private let keychain = KeychainService.shared

    // Keychain keys
    private let cloudTokenKey = "magnetar_cloud_token"

    private init() {}

    // MARK: - Auth Flow

    /// Start OAuth flow by opening browser
    func startAuthFlow() {
        authStatus = .idle

        guard var urlComponents = URLComponents(string: "\(authBaseURL)/login") else {
            authStatus = .failure("Invalid auth URL")
            return
        }

        urlComponents.queryItems = [
            URLQueryItem(name: "redirect_uri", value: redirectURI)
        ]

        guard let authURL = urlComponents.url else {
            authStatus = .failure("Failed to build auth URL")
            return
        }

        NSWorkspace.shared.open(authURL)
        authStatus = .loading
    }

    /// Handle OAuth callback with code
    func handleAuthCallback(url: URL) async {
        authStatus = .loading

        guard let components = URLComponents(url: url, resolvingAgainstBaseURL: false),
              let queryItems = components.queryItems else {
            authStatus = .failure("Invalid callback URL")
            return
        }

        // Extract code from query parameters
        guard let code = queryItems.first(where: { $0.name == "code" })?.value else {
            authStatus = .failure("Missing authorization code")
            return
        }

        // Exchange code for token
        await exchangeCodeForToken(code: code)
    }

    // MARK: - Token Exchange

    private func exchangeCodeForToken(code: String) async {
        do {
            struct TokenResponse: Decodable {
                let accessToken: String
                let email: String
                let plan: String
            }

            let response: TokenResponse = try await apiClient.request(
                path: "/v1/auth/exchange",
                method: .post,
                jsonBody: [
                    "code": code,
                    "redirect_uri": redirectURI
                ],
                authenticated: false
            )

            // Store token in keychain
            try keychain.saveToken(response.accessToken, forKey: cloudTokenKey)

            // Update state
            isAuthenticated = true
            cloudEmail = response.email
            cloudPlan = response.plan
            authStatus = .success("Signed in as \(response.email)")

        } catch let error as ApiError {
            authStatus = .failure(error.localizedDescription)
            isAuthenticated = false
        } catch {
            authStatus = .failure("Exchange failed: \(error.localizedDescription)")
            isAuthenticated = false
        }
    }

    // MARK: - Check Auth Status

    /// Check if user has valid token and fetch profile
    func checkAuthStatus() async {
        // Check for existing token
        guard let token = keychain.loadToken(forKey: cloudTokenKey), !token.isEmpty else {
            isAuthenticated = false
            cloudEmail = ""
            cloudPlan = "Free"
            return
        }

        // Token exists - fetch profile to verify it's valid
        await fetchProfile()
    }

    private func fetchProfile() async {
        do {
            struct ProfileResponse: Decodable {
                let email: String
                let plan: String
            }

            // Temporarily store token for this request
            let oldToken = keychain.loadToken()
            if let cloudToken = keychain.loadToken(forKey: cloudTokenKey) {
                try? keychain.saveToken(cloudToken)
            }

            let profile: ProfileResponse = try await apiClient.request(
                path: "/v1/auth/profile",
                method: .get,
                authenticated: true
            )

            // Restore old token
            if let oldToken = oldToken {
                try? keychain.saveToken(oldToken)
            }

            isAuthenticated = true
            cloudEmail = profile.email
            cloudPlan = profile.plan
            authStatus = .idle

        } catch {
            // Token invalid or expired
            isAuthenticated = false
            cloudEmail = ""
            cloudPlan = "Free"
            authStatus = .idle

            // Clear invalid token
            try? keychain.deleteToken(forKey: cloudTokenKey)
        }
    }

    // MARK: - Sign Out

    func signOut() {
        do {
            try keychain.deleteToken(forKey: cloudTokenKey)
            isAuthenticated = false
            cloudEmail = ""
            cloudPlan = "Free"
            authStatus = .idle
        } catch {
            authStatus = .failure("Sign out failed: \(error.localizedDescription)")
        }
    }
}

// MARK: - Settings Manager

@MainActor
final class SettingsManager: ObservableObject {
    static let shared = SettingsManager()

    // MARK: - Launch at Login
    @AppStorage("launchAtLogin") var launchAtLogin: Bool = false {
        didSet {
            if launchAtLogin != oldValue {
                Task {
                    await toggleLaunchAtLogin(enabled: launchAtLogin)
                }
            }
        }
    }
    @Published var launchAtLoginStatus: SimpleStatus = .idle

    // MARK: - Menu Bar
    @AppStorage("showMenuBar") var showMenuBar: Bool = false {
        didSet {
            if showMenuBar != oldValue {
                toggleMenuBar(enabled: showMenuBar)
            }
        }
    }
    @Published var menuBarStatus: SimpleStatus = .idle

    // MARK: - Notifications
    @AppStorage("notificationsEnabled") var notificationsEnabled: Bool = false {
        didSet {
            if notificationsEnabled != oldValue {
                Task {
                    await toggleNotifications(enabled: notificationsEnabled)
                }
            }
        }
    }
    @Published var notificationsStatus: SimpleStatus = .idle

    private init() {}

    // MARK: - Check Initial States

    func checkInitialStates() async {
        // Check launch at login status
        if #available(macOS 13.0, *) {
            let service = SMAppService.mainApp
            launchAtLogin = (service.status == .enabled)
        }

        // Check notification authorization
        let center = UNUserNotificationCenter.current()
        let settings = await center.notificationSettings()

        switch settings.authorizationStatus {
        case .authorized:
            notificationsEnabled = true
            notificationsStatus = .idle
        case .denied:
            notificationsEnabled = false
            notificationsStatus = .failure("Notifications denied in System Settings")
        case .notDetermined:
            notificationsStatus = .idle
        default:
            notificationsStatus = .idle
        }
    }

    // MARK: - Launch at Login

    private func toggleLaunchAtLogin(enabled: Bool) async {
        guard #available(macOS 13.0, *) else {
            launchAtLoginStatus = .failure("Requires macOS 13+")
            launchAtLogin = false
            return
        }

        launchAtLoginStatus = .loading

        do {
            let service = SMAppService.mainApp

            if enabled {
                try service.register()
                launchAtLoginStatus = .success("Enabled")
            } else {
                try await service.unregister()
                launchAtLoginStatus = .success("Disabled")
            }

            // Auto-clear success message
            try? await Task.sleep(for: .seconds(2))
            if launchAtLoginStatus.isSuccess {
                launchAtLoginStatus = .idle
            }
        } catch {
            launchAtLoginStatus = .failure(error.localizedDescription)
            launchAtLogin = !enabled // Revert toggle
        }
    }

    // MARK: - Menu Bar

    private func toggleMenuBar(enabled: Bool) {
        menuBarStatus = .loading

        if enabled {
            MenuBarManager.shared.show()
            menuBarStatus = .success("Menu bar icon enabled")
        } else {
            MenuBarManager.shared.hide()
            menuBarStatus = .success("Menu bar icon hidden")
        }

        // Auto-clear success message
        Task {
            try? await Task.sleep(for: .seconds(2))
            if menuBarStatus.isSuccess {
                menuBarStatus = .idle
            }
        }
    }

    // MARK: - Notifications

    private func toggleNotifications(enabled: Bool) async {
        notificationsStatus = .loading

        let center = UNUserNotificationCenter.current()

        if enabled {
            // Request authorization
            do {
                let granted = try await center.requestAuthorization(options: [.alert, .sound, .badge])

                if granted {
                    notificationsEnabled = true
                    notificationsStatus = .success("Notifications enabled")
                } else {
                    notificationsEnabled = false
                    notificationsStatus = .failure("Notifications denied")
                }
            } catch {
                notificationsEnabled = false
                notificationsStatus = .failure(error.localizedDescription)
            }
        } else {
            // Cannot programmatically revoke - user must do it in System Settings
            notificationsEnabled = false
            notificationsStatus = .success("Disabled (revoke in System Settings if needed)")
        }

        // Auto-clear success message
        try? await Task.sleep(for: .seconds(3))
        if notificationsStatus.isSuccess {
            notificationsStatus = .idle
        }
    }
}

// MARK: - Menu Bar Manager

final class MenuBarManager {
    static let shared = MenuBarManager()

    private var statusItem: NSStatusItem?

    private init() {}

    func show() {
        guard statusItem == nil else { return }

        let item = NSStatusBar.system.statusItem(withLength: NSStatusItem.squareLength)

        if let button = item.button {
            button.image = NSImage(systemSymbolName: "cube.box.fill", accessibilityDescription: "MagnetarStudio")
            button.action = #selector(handleMenuBarClick)
            button.target = self
        }

        // Create menu
        let menu = NSMenu()

        menu.addItem(NSMenuItem(title: "Open MagnetarStudio", action: #selector(openMainWindow), keyEquivalent: "o"))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Settings...", action: #selector(openSettings), keyEquivalent: ","))
        menu.addItem(NSMenuItem.separator())
        menu.addItem(NSMenuItem(title: "Quit", action: #selector(NSApplication.terminate(_:)), keyEquivalent: "q"))

        item.menu = menu
        statusItem = item
    }

    func hide() {
        guard let item = statusItem else { return }
        NSStatusBar.system.removeStatusItem(item)
        statusItem = nil
    }

    @objc private func handleMenuBarClick() {
        // Menu is shown automatically
    }

    @objc private func openMainWindow() {
        NSApp.activate(ignoringOtherApps: true)
        if let window = NSApp.windows.first {
            window.makeKeyAndOrderFront(nil)
        }
    }

    @objc private func openSettings() {
        NSApp.sendAction(Selector(("showSettingsWindow:")), to: nil, from: nil)
    }
}

// MARK: - Preview

#Preview {
    SettingsView()
}

// MARK: - Helpers

enum SimpleStatus: Equatable {
    case idle
    case loading
    case success(String)
    case failure(String)

    var isSuccess: Bool {
        if case .success = self {
            return true
        }
        return false
    }
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
// MARK: - Model Management Settings

struct ModelManagementSettingsView: View {
    // Intelligent Routing
    @AppStorage("enableAppleFM") private var enableAppleFM = true
    @AppStorage("orchestratorModel") private var orchestratorModel = "apple_fm"

    // Default Model Parameters
    @AppStorage("defaultTemperature") private var defaultTemperature = 0.7
    @AppStorage("defaultTopP") private var defaultTopP = 0.9
    @AppStorage("defaultTopK") private var defaultTopK = 40
    @AppStorage("defaultRepeatPenalty") private var defaultRepeatPenalty = 1.1

    // Model Behavior Presets
    @AppStorage("modelPreset") private var modelPreset = "balanced"

    // Global Prompts
    @AppStorage("globalSystemPrompt") private var globalSystemPrompt = ""
    @AppStorage("enableGlobalPrompt") private var enableGlobalPrompt = false

    // Model Routing Rules
    @AppStorage("dataQueryModel") private var dataQueryModel = "sqlcoder:7b"
    @AppStorage("chatModel") private var chatModel = "llama3.2:3b"
    @AppStorage("codeModel") private var codeModel = "qwen2.5-coder:3b"

    @State private var availableModels: [String] = []
    @State private var orchestratorModels: [OllamaModelWithTags] = []
    @State private var isLoadingModels: Bool = false

    var body: some View {
        Form {
            // Intelligent Routing Section
            Section("Intelligent Routing (Apple FM)") {
                Toggle("Enable Intelligent Model Router", isOn: $enableAppleFM)
                    .help("Automatically selects the best model based on query type")

                if enableAppleFM {
                    VStack(alignment: .leading, spacing: 8) {
                        Text("Orchestrator Model")
                            .font(.caption)
                            .foregroundStyle(.secondary)

                        if isLoadingModels {
                            HStack(spacing: 8) {
                                ProgressView()
                                    .controlSize(.small)
                                Text("Loading orchestrator-capable models...")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            .padding(.vertical, 4)
                        } else {
                            Picker("", selection: $orchestratorModel) {
                                // Apple FM option (default)
                                Text("Apple FM (Intelligent Router)")
                                    .tag("apple_fm")

                                if !orchestratorModels.isEmpty {
                                    Divider()

                                    // Models tagged with "orchestration" capability
                                    ForEach(orchestratorModels, id: \.name) { model in
                                        Text(model.name)
                                            .tag(model.name)
                                    }
                                }
                            }
                            .labelsHidden()
                            .disabled(orchestratorModels.isEmpty && orchestratorModel != "apple_fm")
                        }

                        if orchestratorModel == "apple_fm" {
                            Text("Apple FM analyzes your query and intelligently routes to the best model")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        } else {
                            Text("Using \(orchestratorModel) as the orchestrator for all queries")
                                .font(.caption2)
                                .foregroundStyle(.secondary)
                        }
                    }
                }
            }

            // Model Behavior Presets
            Section("Default Behavior") {
                Picker("Preset", selection: $modelPreset) {
                    Text("Creative").tag("creative")
                    Text("Balanced").tag("balanced")
                    Text("Precise").tag("precise")
                    Text("Custom").tag("custom")
                }
                .onChange(of: modelPreset) { _, newValue in
                    applyPreset(newValue)
                }

                if modelPreset == "custom" {
                    VStack(alignment: .leading, spacing: 12) {
                        // Temperature
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text("Temperature")
                                    .font(.caption)
                                Spacer()
                                Text(String(format: "%.2f", defaultTemperature))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Slider(value: $defaultTemperature, in: 0...2, step: 0.1)
                        }

                        // Top P
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text("Top P")
                                    .font(.caption)
                                Spacer()
                                Text(String(format: "%.2f", defaultTopP))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Slider(value: $defaultTopP, in: 0...1, step: 0.05)
                        }

                        // Top K
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text("Top K")
                                    .font(.caption)
                                Spacer()
                                Text("\(defaultTopK)")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Slider(value: Binding(
                                get: { Double(defaultTopK) },
                                set: { defaultTopK = Int($0) }
                            ), in: 1...100, step: 1)
                        }

                        // Repeat Penalty
                        VStack(alignment: .leading, spacing: 4) {
                            HStack {
                                Text("Repeat Penalty")
                                    .font(.caption)
                                Spacer()
                                Text(String(format: "%.2f", defaultRepeatPenalty))
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                            Slider(value: $defaultRepeatPenalty, in: 1...2, step: 0.1)
                        }
                    }
                }
            }

            // Model Routing Rules
            Section("Model Routing Rules") {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Data Queries")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Picker("", selection: $dataQueryModel) {
                        Text("sqlcoder:7b").tag("sqlcoder:7b")
                        Text("qwen2.5-coder:3b").tag("qwen2.5-coder:3b")
                    }
                    .labelsHidden()
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text("General Chat")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Picker("", selection: $chatModel) {
                        Text("llama3.2:3b").tag("llama3.2:3b")
                        Text("phi3.5:3.8b").tag("phi3.5:3.8b")
                        Text("magnetar32:3b").tag("magnetar32:3b")
                    }
                    .labelsHidden()
                }

                VStack(alignment: .leading, spacing: 8) {
                    Text("Code Generation")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                    Picker("", selection: $codeModel) {
                        Text("qwen2.5-coder:3b").tag("qwen2.5-coder:3b")
                        Text("qwen3-coder:30b").tag("qwen3-coder:30b")
                        Text("deepseek-r1:8b").tag("deepseek-r1:8b")
                    }
                    .labelsHidden()
                }
            }

            // Global System Prompt
            Section("Global System Prompt") {
                Toggle("Enable Global Prompt", isOn: $enableGlobalPrompt)
                    .help("Applies this prompt to all model conversations")

                if enableGlobalPrompt {
                    VStack(alignment: .leading, spacing: 8) {
                        TextEditor(text: $globalSystemPrompt)
                            .frame(height: 100)
                            .font(.system(size: 12, design: .monospaced))
                            .padding(4)
                            .background(Color.surfaceSecondary)
                            .cornerRadius(6)

                        Text("This prompt will be prepended to all conversations")
                            .font(.caption2)
                            .foregroundStyle(.secondary)
                    }
                }
            }
        }
        .formStyle(.grouped)
        .task {
            await loadAvailableModels()
        }
    }

    private func applyPreset(_ preset: String) {
        switch preset {
        case "creative":
            defaultTemperature = 1.2
            defaultTopP = 0.95
            defaultTopK = 50
            defaultRepeatPenalty = 1.0
        case "balanced":
            defaultTemperature = 0.7
            defaultTopP = 0.9
            defaultTopK = 40
            defaultRepeatPenalty = 1.1
        case "precise":
            defaultTemperature = 0.3
            defaultTopP = 0.85
            defaultTopK = 20
            defaultRepeatPenalty = 1.2
        default:
            break
        }
    }

    private func loadAvailableModels() async {
        await MainActor.run {
            isLoadingModels = true
        }

        do {
            // Load models with tags
            let url = URL(string: "http://localhost:8000/api/v1/chat/models/with-tags")!
            let (data, _) = try await URLSession.shared.data(from: url)

            let decoder = JSONDecoder()
            decoder.keyDecodingStrategy = .convertFromSnakeCase
            let models = try decoder.decode([OllamaModelWithTags].self, from: data)

            // Filter for orchestration-capable models
            let orchestrators = models.filter { model in
                model.tags.contains("orchestration")
            }

            await MainActor.run {
                self.orchestratorModels = orchestrators
                self.availableModels = models.map { $0.name }
                self.isLoadingModels = false
            }
        } catch {
            print("Failed to load models: \(error)")
            await MainActor.run {
                self.isLoadingModels = false
            }
        }
    }
}

// MARK: - Supporting Models

struct OllamaModelWithTags: Codable, Identifiable {
    let id: String
    let name: String
    let size: Int64
    let tags: [String]

    enum CodingKeys: String, CodingKey {
        case id, name, size, tags
    }
}
