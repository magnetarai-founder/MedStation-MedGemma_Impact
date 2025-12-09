//
//  HubNetworkManager.swift
//  MagnetarStudio (macOS)
//
//  Network monitoring manager - Extracted from MagnetarHubWorkspace.swift (Phase 6.19)
//

import SwiftUI
import Network

@MainActor
@Observable
class HubNetworkManager {
    var isNetworkConnected: Bool = false

    private let networkMonitor = NWPathMonitor()

    func startNetworkMonitoring() {
        let queue = DispatchQueue(label: "NetworkMonitor")
        networkMonitor.pathUpdateHandler = { path in
            Task { @MainActor in
                self.isNetworkConnected = path.status == .satisfied
            }
        }
        networkMonitor.start(queue: queue)
    }

    func stopNetworkMonitoring() {
        networkMonitor.cancel()
    }

    func openOllamaWebsite() {
        if let url = URL(string: "https://ollama.com/library") {
            NSWorkspace.shared.open(url)
        }
    }

    deinit {
        networkMonitor.cancel()
    }
}
