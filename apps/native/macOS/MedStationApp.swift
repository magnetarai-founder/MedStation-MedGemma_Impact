//
//  MedStationApp.swift
//  MedStation
//
//  Main app entry point for macOS.
//

import SwiftUI
import SwiftData
import AppKit

@main
struct MedStationApp: App {
    @State private var navigationStore = NavigationStore()
    @State private var chatStore = ChatStore()
    @State private var authStore = AuthStore.shared
    @NSApplicationDelegateAdaptor(AppLifecycleManager.self) var appDelegate
    @AppStorage("theme") private var theme = "system"

    init() {
        UserDefaults.standard.register(defaults: [
            "enableAppleFM": true,
            "defaultTemperature": 0.7,
            "defaultTopP": 0.9,
            "defaultTopK": 40,
            "defaultRepeatPenalty": 1.1,
            "enableBlurEffects": true,
            "autoLockEnabled": true,
            "autoLockTimeout": 15,
        ])
    }

    var body: some Scene {
        // Main window — opens directly into Medical AI
        WindowGroup {
            ContentView()
                .frame(minWidth: 960, minHeight: 580)
                .onAppear {
                    applyTheme()
                    if let window = NSApplication.shared.windows.first {
                        window.setContentSize(NSSize(width: 1080, height: 720))
                        window.minSize = NSSize(width: 960, height: 580)
                        window.isMovableByWindowBackground = true
                    }
                }
                .onChange(of: theme) {
                    applyTheme()
                }
        }
        .windowStyle(.hiddenTitleBar)
        .windowToolbarStyle(.unified)
        .defaultSize(width: 1080, height: 720)
        .environment(navigationStore)
        .environment(chatStore)
        .environment(authStore)
        .commands {
            MedStationMenuCommands(
                navigationStore: navigationStore,
                chatStore: chatStore
            )
        }

        // Settings window
        Settings {
            SettingsView()
        }

        // Model Manager window (for managing MedGemma and other models)
        WindowGroup("Model Manager", id: "model-manager") {
            ModelManagerWindow()
        }
        .windowStyle(.hiddenTitleBar)
        .windowResizability(.contentMinSize)
        .defaultSize(width: 520, height: 580)

        // AI Assistant window (⇧⌘P) — floating, usable from any context
        WindowGroup("AI Assistant", id: "detached-ai") {
            DetachedAIWindow()
                .environment(chatStore)
        }
        .windowStyle(.titleBar)
        .windowResizability(.contentMinSize)
        .defaultSize(width: 650, height: 750)
    }

    // MARK: - Theme

    private func applyTheme() {
        switch theme {
        case "light":
            NSApp.appearance = NSAppearance(named: .aqua)
        case "dark":
            NSApp.appearance = NSAppearance(named: .darkAqua)
        default:
            NSApp.appearance = nil
        }
    }
}
