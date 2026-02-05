//
//  PluginSettingsView.swift
//  MagnetarStudio (macOS)
//
//  Per-plugin settings form with type-aware inputs.
//  Settings are defined in the plugin manifest.
//

import SwiftUI

struct PluginSettingsView: View {
    let plugin: InstalledPlugin
    @State private var pluginManager = PluginManager.shared
    @State private var localValues: [String: String] = [:]
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        VStack(spacing: 0) {
            // Header
            HStack {
                Image(systemName: plugin.icon)
                    .font(.system(size: 14))
                    .foregroundStyle(Color.accentColor)
                Text("\(plugin.name) Settings")
                    .font(.system(size: 14, weight: .semibold))
                Spacer()
            }
            .padding(16)

            Divider()

            // Settings form
            if plugin.manifest.settings.isEmpty {
                VStack(spacing: 8) {
                    Image(systemName: "gearshape")
                        .font(.system(size: 24))
                        .foregroundStyle(.tertiary)
                    Text("No configurable settings")
                        .font(.system(size: 13))
                        .foregroundStyle(.secondary)
                }
                .frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                ScrollView {
                    VStack(alignment: .leading, spacing: 16) {
                        ForEach(plugin.manifest.settings) { setting in
                            settingRow(setting)
                        }
                    }
                    .padding(16)
                }
            }

            Divider()

            // Footer
            HStack {
                Button("Reset to Defaults") {
                    resetToDefaults()
                }
                .controlSize(.small)

                Spacer()

                Button("Cancel") {
                    dismiss()
                }
                .keyboardShortcut(.cancelAction)

                Button("Save") {
                    saveSettings()
                    dismiss()
                }
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.defaultAction)
            }
            .padding(16)
        }
        .frame(width: 420, height: 380)
        .onAppear {
            // Load current values
            for setting in plugin.manifest.settings {
                localValues[setting.id] = plugin.settingValue(for: setting.id)
            }
        }
    }

    // MARK: - Setting Row

    @ViewBuilder
    private func settingRow(_ setting: PluginSetting) -> some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(setting.label)
                .font(.system(size: 12, weight: .medium))

            Text(setting.description)
                .font(.system(size: 10))
                .foregroundStyle(.secondary)

            switch setting.type {
            case .text:
                TextField(setting.label, text: binding(for: setting.id))
                    .textFieldStyle(.roundedBorder)
                    .font(.system(size: 12))

            case .number:
                TextField(setting.label, text: binding(for: setting.id))
                    .textFieldStyle(.roundedBorder)
                    .font(.system(size: 12, design: .monospaced))

            case .boolean:
                Toggle(isOn: Binding(
                    get: { localValues[setting.id] == "true" },
                    set: { localValues[setting.id] = $0 ? "true" : "false" }
                )) {
                    EmptyView()
                }
                .toggleStyle(.switch)
                .controlSize(.small)

            case .choice:
                Picker("", selection: binding(for: setting.id)) {
                    ForEach(setting.choices ?? [], id: \.self) { choice in
                        Text(choice).tag(choice)
                    }
                }
                .frame(width: 200)
            }
        }
    }

    // MARK: - Helpers

    private func binding(for key: String) -> Binding<String> {
        Binding(
            get: { localValues[key] ?? "" },
            set: { localValues[key] = $0 }
        )
    }

    private func resetToDefaults() {
        for setting in plugin.manifest.settings {
            localValues[setting.id] = setting.defaultValue
        }
    }

    private func saveSettings() {
        for (key, value) in localValues {
            pluginManager.updateSetting(pluginId: plugin.id, key: key, value: value)
        }
    }
}
