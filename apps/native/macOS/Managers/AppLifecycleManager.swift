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
        // SECURITY: Register network firewall protocol globally
        URLProtocol.registerClass(NetworkFirewallProtocol.self)
        logger.info("NetworkFirewallProtocol registered globally")

        // Initialize menu bar if enabled
        if showMenuBar {
            MenuBarManager.shared.show()
        }

        // Auto-start backend server
        Task {
            await BackendManager.shared.autoStartBackend()
            await BackendManager.shared.monitorBackendHealth()
        }

        // Auto-start Ollama if enabled in settings
        Task {
            await autoStartOllama()
        }

        // Initialize model memory tracker
        Task {
            try? await Task.sleep(nanoseconds: 3_000_000_000)
            await ModelMemoryTracker.shared.refresh()
            ModelMemoryTracker.shared.startAutoRefresh(intervalMinutes: 5)
            logger.info("Model memory tracker initialized")
        }

        // Initialize MedicalAI service
        Task { @MainActor in
            await MedicalAIService.shared.ensureModelReady()
            logger.info("MedicalAIService initialized")
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        URLProtocol.unregisterClass(NetworkFirewallProtocol.self)
        BackendManager.shared.terminateBackend()
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

    // MARK: - Ollama Auto-start

    @MainActor
    private func autoStartOllama() async {
        let settings = SettingsStore.shared.appSettings
        guard settings.ollamaAutoStart else {
            logger.debug("Ollama auto-start disabled in settings")
            return
        }

        let ollamaService = OllamaService.shared
        let isRunning = await ollamaService.checkStatus()

        if !isRunning {
            do {
                logger.info("Starting Ollama server (auto-start enabled)...")
                try await ollamaService.start()
                logger.info("Ollama server started successfully")
            } catch {
                logger.error("Failed to auto-start Ollama: \(error)")
            }
        } else {
            logger.debug("Ollama server already running")
        }
    }
}
