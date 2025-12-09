//
//  HubOllamaManager.swift
//  MagnetarStudio (macOS)
//
//  Ollama server management - Extracted from MagnetarHubWorkspace.swift (Phase 6.19)
//

import SwiftUI

@MainActor
@Observable
class HubOllamaManager {
    var ollamaServerRunning: Bool = false
    var isOllamaActionInProgress: Bool = false

    private let ollamaService = OllamaService.shared

    func checkStatus() async {
        ollamaServerRunning = await ollamaService.checkStatus()
    }

    func toggleOllama() async {
        isOllamaActionInProgress = true

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
            print("Failed to toggle Ollama: \(error)")
        }

        isOllamaActionInProgress = false
    }

    func restartOllama() async {
        isOllamaActionInProgress = true

        do {
            try await ollamaService.restart()
            ollamaServerRunning = true
        } catch {
            print("Failed to restart Ollama: \(error)")
            ollamaServerRunning = false
        }

        isOllamaActionInProgress = false
    }
}
