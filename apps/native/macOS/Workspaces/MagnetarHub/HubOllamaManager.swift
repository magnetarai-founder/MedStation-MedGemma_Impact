//
//  HubOllamaManager.swift
//  MagnetarStudio (macOS)
//
//  Ollama server management - Extracted from MagnetarHubWorkspace.swift (Phase 6.19)
//

import SwiftUI
import os

private let logger = Logger(subsystem: "com.magnetar.studio", category: "HubOllamaManager")

@MainActor
@Observable
class HubOllamaManager {
    var ollamaServerRunning: Bool = false
    var isOllamaActionInProgress: Bool = false
    var errorMessage: String?

    private let ollamaService = OllamaService.shared

    func checkStatus() async {
        ollamaServerRunning = await ollamaService.checkStatus()
    }

    func toggleOllama() async {
        isOllamaActionInProgress = true
        errorMessage = nil

        do {
            if ollamaServerRunning {
                // Stop Ollama
                try await ollamaService.stop()
                ollamaServerRunning = false
            } else {
                // Start Ollama
                try await ollamaService.start()
                ollamaServerRunning = true
            }
        } catch {
            errorMessage = "Failed to \(ollamaServerRunning ? "stop" : "start") Ollama: \(error.localizedDescription)"
            logger.error("Failed to toggle Ollama: \(error)")
        }

        isOllamaActionInProgress = false
    }

    func restartOllama() async {
        isOllamaActionInProgress = true
        errorMessage = nil

        do {
            try await ollamaService.restart()
            ollamaServerRunning = true
        } catch {
            errorMessage = "Failed to restart Ollama: \(error.localizedDescription)"
            logger.error("Failed to restart Ollama: \(error)")
            ollamaServerRunning = false
        }

        isOllamaActionInProgress = false
    }
}
