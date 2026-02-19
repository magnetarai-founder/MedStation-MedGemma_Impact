//
//  GeneralSettingsView.swift
//  MedStation
//
//  Settings panel for general application preferences.
//

import SwiftUI

// MARK: - General Settings

struct GeneralSettingsView: View {
    @State private var settingsManager = SettingsManager.shared
    @State private var settingsStore = SettingsStore.shared
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
