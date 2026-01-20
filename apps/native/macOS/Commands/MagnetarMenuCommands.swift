//
//  MagnetarMenuCommands.swift
//  MagnetarStudio (macOS)
//
//  Menu bar commands - Extracted from MagnetarStudioApp.swift (Phase 6.15)
//  Defines File, View, Tools, and Help menu commands
//

import SwiftUI
import AppKit
import UniformTypeIdentifiers

struct MagnetarMenuCommands: Commands {
    let navigationStore: NavigationStore
    let chatStore: ChatStore
    let databaseStore: DatabaseStore
    let commandPaletteManager: CommandPaletteManager

    private let docsURL = URL(string: "https://docs.magnetar.studio")
    private let issuesURL = URL(string: "https://github.com/MagnetarStudio/MagnetarStudio/issues")

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

        // View menu - All workspaces with ⌘1-8 shortcuts matching NavigationStore.keyboardShortcut
        CommandMenu("View") {
            Button("Team Workspace") {
                navigationStore.navigate(to: .team)
            }
            .keyboardShortcut("1", modifiers: .command)

            Button("Chat Workspace") {
                navigationStore.navigate(to: .chat)
            }
            .keyboardShortcut("2", modifiers: .command)

            Button("Code Workspace") {
                navigationStore.navigate(to: .code)
            }
            .keyboardShortcut("3", modifiers: .command)

            Button("Database Workspace") {
                navigationStore.navigate(to: .database)
            }
            .keyboardShortcut("4", modifiers: .command)

            Button("Kanban Workspace") {
                navigationStore.navigate(to: .kanban)
            }
            .keyboardShortcut("5", modifiers: .command)

            Button("Insights Workspace") {
                navigationStore.navigate(to: .insights)
            }
            .keyboardShortcut("6", modifiers: .command)

            Button("Trust Network") {
                navigationStore.navigate(to: .trust)
            }
            .keyboardShortcut("7", modifiers: .command)

            Button("MagnetarHub") {
                navigationStore.navigate(to: .magnetarHub)
            }
            .keyboardShortcut("8", modifiers: .command)

            Divider()

            Button("Toggle Sidebar") {
                navigationStore.toggleSidebar()
            }
            .keyboardShortcut("s", modifiers: [.command, .control])
        }

        // Window menu additions
        // Note: Model Manager (⌘M) and Control Center (⌘.) can be added here
        // but require @Environment(\.openWindow) which isn't available in Commands.
        // For now, use the (+) Quick Action menu in the header to open these.

        // Tools menu
        CommandMenu("Tools") {
            Button("Command Palette...") {
                toggleCommandPalette()
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

    // MARK: - File Menu Handlers

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

    // MARK: - Tools Menu Handlers

    private func toggleCommandPalette() {
        commandPaletteManager.toggle()
    }

    // MARK: - Help Menu Handlers

    private func openExternal(_ url: URL?) {
        guard let url else { return }
        NSWorkspace.shared.open(url)
    }
}
