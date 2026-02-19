//
//  AppLifecycleManager.swift
//  MedStation
//
//  App lifecycle and delegate handling.
//  Handles app startup, URL callbacks, and shutdown.
//

import SwiftUI
import AppKit
import os

private let logger = Logger(subsystem: "com.medstation.app", category: "AppLifecycleManager")

class AppLifecycleManager: NSObject, NSApplicationDelegate {
    @AppStorage("showMenuBar") private var showMenuBar: Bool = false

    // MARK: - Lifecycle

    func applicationDidFinishLaunching(_ notification: Notification) {
        // Initialize menu bar if enabled
        if showMenuBar {
            MenuBarManager.shared.show()
        }

        // Load MedGemma via MLX native inference (no backend needed)
        Task {
            await MedicalAIService.shared.ensureModelReady()
            logger.info("MedicalAIService initialized (MLX native)")
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
    }

    // MARK: - URL Handling

    func application(_ application: NSApplication, open urls: [URL]) {
        for url in urls {
            handleURL(url)
        }
    }

    private func handleURL(_ url: URL) {
        guard url.scheme == "medstation" else { return }
        // Future: handle deep links
    }

}
