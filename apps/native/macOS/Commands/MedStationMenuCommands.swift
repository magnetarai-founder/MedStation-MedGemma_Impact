//
//  MedStationMenuCommands.swift
//  MedStation
//
//  Menu bar commands for MedStation.
//

import SwiftUI
import AppKit

extension Notification.Name {
    static let focusPanelSearch = Notification.Name("com.medstation.app.focusPanelSearch")
}

struct MedStationMenuCommands: Commands {
    let navigationStore: NavigationStore
    let chatStore: ChatStore

    var body: some Commands {
        // File menu
        CommandGroup(after: .newItem) {
            Button("New Chat Session") {
                Task { await createNewChatSession() }
            }
            .keyboardShortcut("n", modifiers: .command)
        }

        // Edit menu — Find in Panel
        CommandGroup(after: .textEditing) {
            Button("Find in Panel") {
                NotificationCenter.default.post(name: .focusPanelSearch, object: nil)
            }
            .keyboardShortcut("f", modifiers: .command)
        }

        // View menu
        CommandMenu("View") {
            Button("Medical AI") {
                navigationStore.navigate(to: .workspace)
            }
            .keyboardShortcut("1", modifiers: .command)

            Divider()

            Button("Toggle Sidebar") {
                navigationStore.toggleSidebar()
            }
            .keyboardShortcut("\\", modifiers: .command)
        }

        // Window menu
        CommandMenu("Window") {
            Button("AI Assistant") {
                WindowOpener.shared.openAIAssistant()
            }
            .keyboardShortcut("p", modifiers: [.command, .shift])
        }

        // Help menu
        CommandGroup(replacing: .help) {
            Button("About MedStation") {
                NSApp.orderFrontStandardAboutPanel(nil)
            }
        }
    }

    // MARK: - Handlers

    @MainActor
    private func createNewChatSession() async {
        await chatStore.createSession(title: "New Chat")
    }
}
