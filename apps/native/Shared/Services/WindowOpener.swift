//
//  WindowOpener.swift
//  MagnetarStudio
//
//  Service to open windows from menu commands
//  Bridges the gap between Commands (no @Environment) and SwiftUI openWindow
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "WindowOpener")

/// Singleton service to open windows from anywhere in the app
/// Configure with closures in the main app, then call from Commands
@MainActor
final class WindowOpener {
    static let shared = WindowOpener()

    // MARK: - Window Opening Closures

    /// Opens a detached note window
    var openDetachedNote: (() -> Void)?

    /// Opens a detached chat window
    var openDetachedChat: (() -> Void)?

    /// Opens a detached document window
    var openDetachedDocument: ((DetachedDocumentInfo) -> Void)?

    /// Opens a detached doc editor window (workspace docs)
    var openDetachedDocEdit: ((DetachedDocEditInfo) -> Void)?

    /// Opens a detached spreadsheet window
    var openDetachedSheet: ((DetachedSheetInfo) -> Void)?

    /// Opens a detached PDF viewer window
    var openDetachedPDFView: ((DetachedPDFViewInfo) -> Void)?

    /// Opens a spawnable workspace window
    var openWorkspace: ((String) -> Void)?

    private init() {}

    // MARK: - Public Methods

    func openNewNote() {
        guard let opener = openDetachedNote else {
            logger.warning("openDetachedNote not configured")
            return
        }
        opener()
        logger.info("Opened new note window")
    }

    func openNewChat() {
        guard let opener = openDetachedChat else {
            logger.warning("openDetachedChat not configured")
            return
        }
        opener()
        logger.info("Opened new chat window")
    }

    func openDocument(_ info: DetachedDocumentInfo) {
        guard let opener = openDetachedDocument else {
            logger.warning("openDetachedDocument not configured")
            return
        }
        opener(info)
        logger.info("Opened document window: \(info.fileName)")
    }

    func openDocEditor(_ info: DetachedDocEditInfo) {
        guard let opener = openDetachedDocEdit else {
            logger.warning("openDetachedDocEdit not configured")
            return
        }
        opener(info)
        logger.info("Opened document editor: \(info.title)")
    }

    func openSheetEditor(_ info: DetachedSheetInfo) {
        guard let opener = openDetachedSheet else {
            logger.warning("openDetachedSheet not configured")
            return
        }
        opener(info)
        logger.info("Opened spreadsheet: \(info.title)")
    }

    func openPDFViewer(_ info: DetachedPDFViewInfo) {
        guard let opener = openDetachedPDFView else {
            logger.warning("openDetachedPDFView not configured")
            return
        }
        opener(info)
        logger.info("Opened PDF viewer: \(info.title)")
    }

    func openCodeWorkspace() {
        openWorkspace?("workspace-code")
        logger.info("Opened Code workspace")
    }

    func openDatabaseWorkspace() {
        openWorkspace?("workspace-database")
        logger.info("Opened Database workspace")
    }

    func openKanbanWorkspace() {
        openWorkspace?("workspace-kanban")
        logger.info("Opened Kanban workspace")
    }

    func openInsightsWorkspace() {
        openWorkspace?("workspace-insights")
        logger.info("Opened Insights workspace")
    }

    func openTrustWorkspace() {
        openWorkspace?("workspace-trust")
        logger.info("Opened Trust workspace")
    }

    func openHubWorkspace() {
        openWorkspace?("workspace-hub")
        logger.info("Opened Hub workspace")
    }

    func openModelManager() {
        openWorkspace?("model-manager")
        logger.info("Opened Model Manager")
    }
}

// MARK: - View Modifier to Configure WindowOpener

struct WindowOpenerConfigurator: ViewModifier {
    @Environment(\.openWindow) private var openWindow

    func body(content: Content) -> some View {
        content
            .onAppear {
                configureWindowOpener()
            }
    }

    private func configureWindowOpener() {
        let opener = WindowOpener.shared

        opener.openDetachedNote = {
            openWindow(id: "detached-note")
        }

        opener.openDetachedChat = {
            openWindow(id: "detached-chat")
        }

        opener.openDetachedDocument = { (info: DetachedDocumentInfo) in
            openWindow(value: info)
        }

        opener.openDetachedDocEdit = { (info: DetachedDocEditInfo) in
            openWindow(value: info)
        }

        opener.openDetachedSheet = { (info: DetachedSheetInfo) in
            openWindow(value: info)
        }

        opener.openDetachedPDFView = { (info: DetachedPDFViewInfo) in
            openWindow(value: info)
        }

        opener.openWorkspace = { windowId in
            openWindow(id: windowId)
        }

        logger.info("WindowOpener configured with openWindow closures")
    }
}

extension View {
    func windowOpenerConfigurator() -> some View {
        modifier(WindowOpenerConfigurator())
    }
}
