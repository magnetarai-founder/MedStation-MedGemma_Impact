//
//  AppearanceSettingsView.swift
//  MagnetarStudio
//
//  Settings panel for appearance customization.
//

import SwiftUI

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
