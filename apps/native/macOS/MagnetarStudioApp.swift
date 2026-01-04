//
//  MagnetarStudioApp.swift
//  MagnetarStudio (macOS)
//
//  Main app entry point for macOS 26.
//  Refactored in Phase 6.15 - extracted backend management, lifecycle, commands, and palette
//

import SwiftUI
import SwiftData
import AppKit

// MARK: - Import shared modules
// All shared code is in the Shared/ folder

@main
struct MagnetarStudioApp: App {
    @State private var navigationStore = NavigationStore()
    @State private var chatStore = ChatStore()
    @State private var databaseStore = DatabaseStore.shared
    @State private var authStore = AuthStore.shared
    @State private var permissionManager = VaultPermissionManager.shared
    @NSApplicationDelegateAdaptor(AppLifecycleManager.self) var appDelegate
    @State private var commandPaletteManager = CommandPaletteManager()

    var body: some Scene {
        // Main window
        WindowGroup {
            ContentView()
                .frame(minWidth: 1300, minHeight: 750)
                .onAppear {
                    // Set window size constraints
                    if let window = NSApplication.shared.windows.first {
                        window.setContentSize(NSSize(width: 1400, height: 850))
                        window.minSize = NSSize(width: 1300, height: 750)
                        window.isMovableByWindowBackground = true
                    }
                }
                .sheet(isPresented: $commandPaletteManager.isPresented) {
                    CommandPaletteView(
                        manager: commandPaletteManager,
                        navigationStore: navigationStore,
                        chatStore: chatStore,
                        databaseStore: databaseStore
                    )
                }
        }
        .windowStyle(.hiddenTitleBar)
        .windowToolbarStyle(.unified)
        .defaultSize(width: 1400, height: 850)
        .environment(navigationStore)
        .environment(chatStore)
        .environment(databaseStore)
        .environment(authStore)
        .environment(permissionManager)
        .environment(commandPaletteManager)
        .commands {
            MagnetarMenuCommands(
                navigationStore: navigationStore,
                chatStore: chatStore,
                databaseStore: databaseStore,
                commandPaletteManager: commandPaletteManager
            )
        }

        // Settings window
        Settings {
            SettingsView()
        }

        // Model Manager window (floating, separate)
        WindowGroup("Model Manager", id: "model-manager") {
            ModelManagerWindow()
        }
        .windowStyle(.hiddenTitleBar)
        .windowResizability(.contentMinSize)  // Resizable but respects minimum size
        .defaultSize(width: 520, height: 580)  // Default matches ModelManagerWindow frame
    }
}
