//
//  MagnetarStudioApp.swift
//  MagnetarStudio (macOS)
//
//  Main app entry point for macOS 26.
//

import SwiftUI
import SwiftData
import AppKit
import UniformTypeIdentifiers

// MARK: - Import shared modules
// All shared code is in the Shared/ folder

@main
struct MagnetarStudioApp: App {
    @State private var navigationStore = NavigationStore()
    @State private var chatStore = ChatStore()
    @StateObject private var databaseStore = DatabaseStore.shared

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
        }
        .windowStyle(.hiddenTitleBar)
        .windowToolbarStyle(.unified)
        .defaultSize(width: 1400, height: 850)
        .environment(navigationStore)
        .environment(chatStore)
        .environmentObject(databaseStore)
        .commands {
            MagnetarCommands(
                navigationStore: navigationStore,
                chatStore: chatStore,
                databaseStore: databaseStore
            )
        }

        // Settings window
        Settings {
            SettingsView()
        }
    }
}

// MARK: - Menu Commands

struct MagnetarCommands: Commands {
    let navigationStore: NavigationStore
    let chatStore: ChatStore
    let databaseStore: DatabaseStore

    private let docsURL = URL(string: "https://docs.magnetar.studio") // replace if your docs live elsewhere
    private let issuesURL = URL(string: "https://github.com/MagnetarStudio/MagnetarStudio/issues") // replace if using another tracker

    var body: some Commands {
        // File menu
        CommandGroup(after: .newItem) {
            Button("New Chat Session") {
                Task { await createNewChatSession() }
            }
            .keyboardShortcut("n", modifiers: .command)

            Button("New Query Tab") {
                Task { await createNewQueryTab() }
            }
            .keyboardShortcut("t", modifiers: .command)

            Divider()

            Button("Upload File...") {
                handleFileUpload()
            }
            .keyboardShortcut("o", modifiers: .command)
        }

        // Edit menu (keep defaults)

        // View menu
        CommandMenu("View") {
            Button("Team Workspace") {
                navigationStore.navigate(to: .team)
            }
            .keyboardShortcut("1", modifiers: .command)

            Button("Chat Workspace") {
                navigationStore.navigate(to: .chat)
            }
            .keyboardShortcut("2", modifiers: .command)

            Button("Database Workspace") {
                navigationStore.navigate(to: .database)
            }
            .keyboardShortcut("3", modifiers: .command)

            Button("Kanban Workspace") {
                navigationStore.navigate(to: .kanban)
            }
            .keyboardShortcut("4", modifiers: .command)

            Button("MagnetarHub") {
                navigationStore.navigate(to: .magnetarHub)
            }
            .keyboardShortcut("5", modifiers: .command)

            Divider()

            Button("Toggle Sidebar") {
                navigationStore.toggleSidebar()
            }
            .keyboardShortcut("s", modifiers: [.command, .control])
        }

        // Tools menu
        CommandMenu("Tools") {
            Button("Agent Orchestrator") {
                navigationStore.navigate(to: .magnetarHub)
            }
            .keyboardShortcut("k", modifiers: [.command, .shift])

            Button("Workflow Designer") {
                navigationStore.navigate(to: .kanban)
            }

            Divider()

            Button("Command Palette...") {
                showComingSoonAlert(title: "Command Palette", message: "Command Palette is coming soon.")
            }
            .keyboardShortcut("k", modifiers: .command)
        }

        // Help menu
        CommandGroup(replacing: .help) {
            Button("MagnetarStudio Documentation") {
                openExternal(docsURL)
            }

            Button("Report an Issue") {
                openExternal(issuesURL)
            }

            Divider()

            Button("About MagnetarStudio") {
                NSApp.orderFrontStandardAboutPanel(nil)
            }
        }
    }

    // MARK: - Helpers

    @MainActor
    private func createNewChatSession() async {
        await chatStore.createSession(title: "New Chat", model: chatStore.selectedModel.isEmpty ? "mistral" : chatStore.selectedModel)
        navigationStore.navigate(to: .chat)
    }

    @MainActor
    private func createNewQueryTab() async {
        if databaseStore.sessionId == nil {
            await databaseStore.createSession()
        }
        databaseStore.loadEditorText("", contentType: .sql)
        navigationStore.navigate(to: .database)
    }

    private func handleFileUpload() {
        let panel = NSOpenPanel()
        panel.allowedContentTypes = [
            UTType.commaSeparatedText,
            UTType(filenameExtension: "xls"),
            UTType(filenameExtension: "xlsx"),
            UTType.json
        ].compactMap { $0 }
        panel.allowsMultipleSelection = false
        panel.canChooseDirectories = false

        if panel.runModal() == .OK, let url = panel.url {
            Task { await uploadSelectedFile(url: url) }
        }
    }

    @MainActor
    private func uploadSelectedFile(url: URL) async {
        if databaseStore.sessionId == nil {
            await databaseStore.createSession()
        }
        await databaseStore.uploadFile(url: url)
        navigationStore.navigate(to: .database)
    }

    private func openExternal(_ url: URL?) {
        guard let url else { return }
        NSWorkspace.shared.open(url)
    }

    private func showComingSoonAlert(title: String, message: String) {
        let alert = NSAlert()
        alert.messageText = title
        alert.informativeText = message
        alert.alertStyle = .informational
        alert.runModal()
    }
}
