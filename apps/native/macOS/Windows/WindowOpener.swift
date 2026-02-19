//
//  WindowOpener.swift
//  MedStation
//
//  Utility for opening app windows by ID.
//

import SwiftUI
import AppKit

@MainActor
final class WindowOpener {
    static let shared = WindowOpener()
    private init() {}

    func openModelManager() {
        openWindow(id: "model-manager")
    }

    func openAIAssistant() {
        openWindow(id: "detached-ai")
    }

    private func openWindow(id: String) {
        if let url = URL(string: "medstation://open-window/\(id)") {
            NSWorkspace.shared.open(url)
        }
    }
}
