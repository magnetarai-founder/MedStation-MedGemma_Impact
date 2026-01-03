//
//  AppLifecycleManager.swift
//  MagnetarStudio (macOS)
//
//  App lifecycle and delegate handling - Extracted from MagnetarStudioApp.swift (Phase 6.15)
//  Handles app startup, URL callbacks, and shutdown
//

import SwiftUI
import AppKit
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "AppLifecycleManager")

class AppLifecycleManager: NSObject, NSApplicationDelegate, ObservableObject {
    @AppStorage("showMenuBar") private var showMenuBar: Bool = false

    // MARK: - Lifecycle

    func applicationDidFinishLaunching(_ notification: Notification) {
        // SECURITY: Register network firewall protocol globally
        // This intercepts ALL URLSession requests (including URLSession.shared)
        // and validates them against SecurityManager rules
        URLProtocol.registerClass(NetworkFirewallProtocol.self)
        logger.info("NetworkFirewallProtocol registered globally")

        // Initialize menu bar if enabled
        if showMenuBar {
            MenuBarManager.shared.show()
        }

        // Auto-start backend server (CRITICAL: Must start before everything else)
        Task {
            await BackendManager.shared.autoStartBackend()

            // Start backend health monitor
            await BackendManager.shared.monitorBackendHealth()
        }

        // Initialize orchestrators (Phase 4)
        Task {
            await OrchestratorInitializer.initialize()
        }

        // Auto-start Ollama if enabled in settings
        Task {
            await autoStartOllama()
        }

        // Initialize model memory tracker (wait for Ollama to start)
        Task {
            // Wait a bit for Ollama to be ready
            try? await Task.sleep(nanoseconds: 3_000_000_000)  // 3 seconds

            await ModelMemoryTracker.shared.refresh()
            ModelMemoryTracker.shared.startAutoRefresh(intervalMinutes: 5)
            logger.info("Model memory tracker initialized")
        }
    }

    func applicationWillTerminate(_ notification: Notification) {
        // Unregister network firewall protocol
        URLProtocol.unregisterClass(NetworkFirewallProtocol.self)

        // Clean shutdown of backend server
        BackendManager.shared.terminateBackend()
    }

    // MARK: - URL Handling

    func application(_ application: NSApplication, open urls: [URL]) {
        for url in urls {
            handleURL(url)
        }
    }

    private func handleURL(_ url: URL) {
        guard url.scheme == "magnetarstudio" else { return }

        // Handle auth callback
        if url.host == "auth", url.path == "/callback" {
            Task { @MainActor in
                await CloudAuthManager.shared.handleAuthCallback(url: url)
            }
        }
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
