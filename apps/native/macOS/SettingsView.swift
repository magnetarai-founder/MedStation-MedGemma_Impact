//
//  SettingsView.swift
//  MagnetarStudio
//
//  Settings panel accessible via menu bar.
//

import SwiftUI

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

    var body: some View {
        Form {
            Section("Backend API") {
                TextField("API Base URL", text: $apiBaseURL)
                    .textFieldStyle(.roundedBorder)

                Button("Test Connection") {
                    // TODO: Test API connection
                }
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
}

// MARK: - Security Settings

struct SecuritySettingsView: View {
    @Binding var enableBiometrics: Bool

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
                    // TODO: Clear cache
                }

                Button("Reset Keychain", role: .destructive) {
                    // TODO: Reset keychain
                }
            }
        }
        .formStyle(.grouped)
        .padding()
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

// MARK: - Preview

#Preview {
    SettingsView()
}
