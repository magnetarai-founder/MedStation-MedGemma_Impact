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

        // View menu - Core tabs ⌘1-3 + sidebar toggle
        CommandMenu("View") {
            // Core workspace tabs
            Button("Workspace") {
                navigationStore.navigate(to: .workspace)
            }
            .keyboardShortcut("1", modifiers: .command)

            Button("Files") {
                navigationStore.navigate(to: .files)
            }
            .keyboardShortcut("2", modifiers: .command)

            Button("Chat") {
                navigationStore.navigate(to: .chat)
            }
            .keyboardShortcut("3", modifiers: .command)

            Divider()

            Button("Toggle Sidebar") {
                navigationStore.toggleSidebar()
            }
            .keyboardShortcut("\\", modifiers: .command)
        }

        // Window menu - Create + spawnable workspaces
        CommandMenu("Window") {
            // Create new documents
            Section("Create") {
                Button("New Note") {
                    WindowOpener.shared.openNewNote()
                }
                .keyboardShortcut("n", modifiers: [.command, .shift])

                Button("New Document") {
                    let info = DetachedDocEditInfo(title: "Untitled Document")
                    WindowOpener.shared.openDocEditor(info)
                }

                Button("New Spreadsheet") {
                    let info = DetachedSheetInfo(title: "Untitled Spreadsheet")
                    WindowOpener.shared.openSheetEditor(info)
                }

                Button("New Chat Window") {
                    WindowOpener.shared.openNewChat()
                }
                .keyboardShortcut("c", modifiers: [.command, .shift])
            }

            Divider()

            // Spawnable workspaces
            Section("Open Workspace") {
                Button("Open Code IDE") {
                    WindowOpener.shared.openCodeWorkspace()
                }
                .keyboardShortcut("4", modifiers: .command)

                Button("Open Data Workspace") {
                    WindowOpener.shared.openDatabaseWorkspace()
                }
                .keyboardShortcut("5", modifiers: .command)

                Button("Open Kanban Board") {
                    WindowOpener.shared.openKanbanWorkspace()
                }
                .keyboardShortcut("6", modifiers: .command)

                Button("Open Insights") {
                    WindowOpener.shared.openInsightsWorkspace()
                }
                .keyboardShortcut("7", modifiers: .command)
            }

            Divider()

            // Utilities
            Button("Model Manager") {
                WindowOpener.shared.openModelManager()
            }
            .keyboardShortcut("m", modifiers: .command)
        }

        // Tools menu
        CommandMenu("Tools") {
            Button("Command Palette...") {
                toggleCommandPalette()
            }
            .keyboardShortcut("k", modifiers: .command)

            Divider()

            Button("AI Assist") {
                navigationStore.navigate(to: .workspace)
            }
            .keyboardShortcut("i", modifiers: [.command, .shift])
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
