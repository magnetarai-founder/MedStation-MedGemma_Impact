//
//  MagnetarStudioApp.swift
//  MagnetarStudio (macOS)
//
//  Main app entry point for macOS 26.
//

import SwiftUI
import SwiftData
import AppKit

// MARK: - Import shared modules
// All shared code is in the Shared/ folder

@main
struct MagnetarStudioApp: App {
    @State private var userStore = UserStore()

    // SwiftData model container
    let modelContainer: ModelContainer

    init() {
        do {
            modelContainer = try ModelContainer(
                for: User.self, ChatMessage.self, ChatSession.self,
                configurations: ModelConfiguration(isStoredInMemoryOnly: false)
            )
        } catch {
            fatalError("Failed to create ModelContainer: \(error)")
        }
    }

    var body: some Scene {
        // Main window
        WindowGroup {
            ContentView()
                .environment(userStore)
                .modelContainer(modelContainer)
                .frame(minWidth: 1300, minHeight: 750)
                .onAppear {
                    // Set window size constraints
                    if let window = NSApplication.shared.windows.first {
                        window.setContentSize(NSSize(width: 1400, height: 850))
                        window.minSize = NSSize(width: 1300, height: 750)
                    }
                }
        }
        .windowStyle(.hiddenTitleBar)
        .windowToolbarStyle(.unified)
        .defaultSize(width: 1400, height: 850)
        .commands {
            MagnetarCommands()
        }

        // Settings window
        Settings {
            SettingsView()
                .environment(userStore)
        }
    }
}

// MARK: - Menu Commands

struct MagnetarCommands: Commands {
    var body: some Commands {
        // File menu
        CommandGroup(after: .newItem) {
            Button("New Chat Session") {
                // TODO: Implement
            }
            .keyboardShortcut("n", modifiers: .command)

            Button("New Query Tab") {
                // TODO: Implement
            }
            .keyboardShortcut("t", modifiers: .command)

            Divider()

            Button("Upload File...") {
                // TODO: Implement
            }
            .keyboardShortcut("o", modifiers: .command)
        }

        // Edit menu (keep defaults)

        // View menu
        CommandMenu("View") {
            Button("Team Workspace") {
                // TODO: Switch to team tab
            }
            .keyboardShortcut("1", modifiers: .command)

            Button("Chat Workspace") {
                // TODO: Switch to chat tab
            }
            .keyboardShortcut("2", modifiers: .command)

            Button("Database Workspace") {
                // TODO: Switch to database tab
            }
            .keyboardShortcut("3", modifiers: .command)

            Button("Kanban Workspace") {
                // TODO: Switch to kanban tab
            }
            .keyboardShortcut("4", modifiers: .command)

            Divider()

            Button("Toggle Sidebar") {
                // TODO: Implement
            }
            .keyboardShortcut("s", modifiers: [.command, .control])
        }

        // Tools menu
        CommandMenu("Tools") {
            Button("Agent Orchestrator") {
                // TODO: Open agent workspace
            }
            .keyboardShortcut("k", modifiers: [.command, .shift])

            Button("Workflow Designer") {
                // TODO: Open workflow designer
            }

            Divider()

            Button("Command Palette...") {
                // TODO: Open command palette
            }
            .keyboardShortcut("k", modifiers: .command)
        }

        // Help menu
        CommandGroup(replacing: .help) {
            Button("MagnetarStudio Documentation") {
                // TODO: Open docs
            }

            Button("Report an Issue") {
                // TODO: Open issue reporter
            }

            Divider()

            Button("About MagnetarStudio") {
                // TODO: Show about window
            }
        }
    }
}
